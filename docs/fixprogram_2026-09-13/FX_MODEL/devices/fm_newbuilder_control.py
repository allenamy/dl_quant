#!/usr/bin/env python3
"""fm_newbuilder_control.py -- FX-MODEL queue item 3 control: does the new builder's LEGACY arm reproduce the base?

Three things, in this order, because the later ones are only meaningful if the first passes:

  C1 SOURCE DIFF     fm_dlw_features_fund.py vs its base retrain_2026-09/pod_dlw_features_ext.py: report every changed
                     hunk, so "one changed region" is auditable rather than asserted. Recorded, not gated -- the gate
                     is C2, because identical behaviour is what matters, not a line count.
  C2 LEGACY BITWISE  base builder and new builder with FMF_FUND_FILL=legacy_zero, SAME fixture and SAME panel:
                     X / pair_a / pair_s / names must be BITWISE identical. X is compared through a uint16 view, so
                     this is true bit equality and not float equality with NaN leniency.
                     Scope of "bitwise": the ARRAYS. The .npz FILE differs and must, because meta_json carries
                     self_sha256 and therefore names whichever device wrote it. File-level equality is not claimed.
  C3 EFFECT AT THE INPUT LAYER  with the legacy arm certified, vary ONE thing at a time and count what moves:
                     C3a same panel, FMF_FUND_FILL=nan_preserve   -> how many cells stop being a hard 0.0
                     C3b full-coverage panel, FMF_FUND_FILL=legacy_zero -> how many funding cells change VALUE
                     This is an input-layer count only. It is NOT a model or book effect and must not be quoted as one;
                     that is what the prereg's three arms are for.

Safety: no subprocess / os.system / bash / requests; no network, no venue; nothing under ~/wide_shadow or
~/dl_quant_live is read or written. Outside the FIXPROGRAM 14.1 battery rule.

Usage: FM_CTL_OUT=<receipt.json> FM_CTL_TMP=<scratchdir> python3 fm_newbuilder_control.py
"""
import os, sys, json, time, hashlib, difflib, traceback
import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
RETRAIN = os.path.join(REPO, "multi_asset", "exports", "research", "retrain_2026-09")
BASE = os.path.join(RETRAIN, "pod_dlw_features_ext.py")
NEW = os.path.join(HERE, "fm_dlw_features_fund.py")
OUT = os.environ["FM_CTL_OUT"]
TMP = os.environ["FM_CTL_TMP"]
os.makedirs(TMP, exist_ok=True)

# The fixture lives in fm_red_builders so there is ONE definition of it; that module reads two env vars at import time.
os.environ.setdefault("FM_RED_OUT", os.path.join(TMP, "_unused_red_receipt.json"))
os.environ.setdefault("FM_RED_TMP", TMP)
sys.path.insert(0, HERE)
import fm_red_builders as FX   # noqa: E402


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def arrays(npz):
    z = np.load(npz, allow_pickle=True)
    return {"X": z["X"], "pair_a": z["pair_a"], "pair_s": z["pair_s"], "names": np.array([str(x) for x in z["names"]])}


def bitwise_equal(a, b):
    """True bit equality. For float16 compare the uint16 view so NaN payloads must match too."""
    if a.shape != b.shape or a.dtype != b.dtype:
        return False, {"shape_a": list(a.shape), "shape_b": list(b.shape), "dtype_a": str(a.dtype), "dtype_b": str(b.dtype)}
    if a.dtype == np.float16:
        ua, ub = a.view(np.uint16), b.view(np.uint16)
        d = int((ua != ub).sum())
        return d == 0, {"differing_cells": d, "total_cells": int(a.size), "compared_as": "uint16 view (true bitwise)"}
    d = int((a != b).sum())
    return d == 0, {"differing_cells": d, "total_cells": int(a.size), "compared_as": str(a.dtype)}


def make_inputs(tag, fund_nan_names, seed):
    """One cache; two panels that differ ONLY in funding coverage (the FEA-01 contrast)."""
    d = os.path.join(TMP, tag)
    os.makedirs(d, exist_ok=True)
    c = os.path.join(d, "cache.npz")
    ts, syms, data = FX.make_cache(c, seed=seed)
    p_narrow = os.path.join(d, "panel_narrow.npz")   # funding missing for some names  == the v3splice 450-name prefix
    p_full = os.path.join(d, "panel_full.npz")       # funding present for every name  == the 829-name panel
    FX.make_panel(p_narrow, ts, syms, data, fund_nan_names=fund_nan_names)
    FX.make_panel(p_full, ts, syms, data, fund_nan_names=())
    return d, c, p_narrow, p_full, ts, syms, data


def run_base(outdir, cache, panel):
    return FX.run_builder(BASE, {"F171_CACHE": cache, "F171_PANEL": panel, "F171_OUT": outdir})


def run_new(outdir, cache, panel, fill):
    return FX.run_builder(NEW, {"FMF_CACHE": cache, "FMF_PANEL": panel, "FMF_OUT": outdir, "FMF_FUND_FILL": fill})


def fresh_out(d, tag, ts, syms, data):
    o = FX.targets_fixture(d, tag, ts, syms, data)
    return o, os.path.join(o, "data", "dlw_fea82.npz")


def main():
    rc = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)),
          "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "python": sys.version.split()[0], "numpy": np.__version__,
          "base": {"path": os.path.relpath(BASE, REPO), "sha256": sha(BASE)},
          "new": {"path": os.path.relpath(NEW, REPO), "sha256": sha(NEW)},
          "fixture_device": {"path": os.path.relpath(FX.__file__, REPO), "sha256": sha(FX.__file__)},
          "shells_out": False, "network": False}

    # ---- C1 source diff -------------------------------------------------------------------------------------
    a = open(BASE).read().splitlines()
    b = open(NEW).read().splitlines()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    hunks = [{"tag": t, "base_lines": [i1 + 1, i2], "new_lines": [j1 + 1, j2]}
             for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
    rc["C1_source_diff"] = {"n_changed_hunks": len(hunks), "hunks": hunks,
                            "note": "recorded, not gated: identical BEHAVIOUR is the gate (C2), not a line count"}
    print("C1 changed hunks: %d" % len(hunks), flush=True)

    # ---- C2 legacy arm must reproduce the base bitwise ------------------------------------------------------
    d, cache, p_narrow, p_full, ts, syms, data = make_inputs("ctl", fund_nan_names=(7, 8, 9), seed=11)
    o_base, f_base = fresh_out(d, "base", ts, syms, data)
    ok1, so1, e1 = run_base(o_base, cache, p_narrow)
    o_leg, f_leg = fresh_out(d, "leg", ts, syms, data)
    ok2, so2, e2 = run_new(o_leg, cache, p_narrow, "legacy_zero")
    if not (ok1 and ok2) or not (os.path.exists(f_base) and os.path.exists(f_leg)):
        rc["C2_legacy_bitwise"] = {"outcome": "INVALID", "base_ok": ok1, "new_ok": ok2,
                                   "error": e1 or e2, "stdout_tail": (so1 + so2)[-800:]}
        rc["gate_C2_pass"] = False
    else:
        A, B = arrays(f_base), arrays(f_leg)
        per = {}
        allok = True
        for k in ("X", "pair_a", "pair_s", "names"):
            eq, det = bitwise_equal(A[k], B[k])
            per[k] = {"bitwise_equal": eq, **det}
            allok = allok and eq
        rc["C2_legacy_bitwise"] = {"outcome": "PASS" if allok else "FAIL", "per_array": per,
                                   "npz_file_sha_base": sha(f_base), "npz_file_sha_new": sha(f_leg),
                                   "file_sha_differs_by_design": sha(f_base) != sha(f_leg),
                                   "why_file_differs": "meta_json carries self_sha256, so the file necessarily names "
                                                       "the device that wrote it; only the ARRAYS can be bitwise equal"}
        rc["gate_C2_pass"] = allok
        print("C2 legacy bitwise: %s" % ("PASS" if allok else "FAIL"), flush=True)

    # ---- C3 one-at-a-time input-layer effect ---------------------------------------------------------------
    rc["C3_effect_input_layer"] = {"note": "input-layer cell counts ONLY; not a model effect and not a book effect"}
    if rc.get("gate_C2_pass"):
        base_X = arrays(f_base)["X"]
        o_np, f_np = fresh_out(d, "nanp", ts, syms, data)
        ok3, so3, e3 = run_new(o_np, cache, p_narrow, "nan_preserve")
        if ok3 and os.path.exists(f_np):
            Xn = arrays(f_np)["X"]
            c80_base, c80_new = base_X[:, 80], Xn[:, 80]
            rc["C3_effect_input_layer"]["C3a_nan_preserve_same_panel"] = {
                "cells_total": int(c80_base.size),
                "cells_that_were_hard_zero": int((c80_base == 0).sum()),
                "cells_now_nan": int(np.isnan(c80_new).sum()),
                "cells_unchanged_bitwise": int((c80_base.view(np.uint16) == c80_new.view(np.uint16)).sum()),
                "meaning": "unknown funding stops being asserted as 0.0; the trainer will impute it at the column mean"}
        else:
            rc["C3_effect_input_layer"]["C3a_nan_preserve_same_panel"] = {"outcome": "INVALID", "error": e3,
                                                                          "stdout_tail": so3[-500:]}
        o_fp, f_fp = fresh_out(d, "full", ts, syms, data)
        ok4, so4, e4 = run_new(o_fp, cache, p_full, "legacy_zero")
        if ok4 and os.path.exists(f_fp):
            Xf = arrays(f_fp)["X"]
            c80_base, c80_full = base_X[:, 80], Xf[:, 80]
            changed = int((c80_base.view(np.uint16) != c80_full.view(np.uint16)).sum())
            was_zero_now_value = int(((c80_base == 0) & (c80_full != 0)).sum())
            rc["C3_effect_input_layer"]["C3b_full_coverage_panel"] = {
                "cells_total": int(c80_base.size), "cells_changed_bitwise": changed,
                "cells_that_were_zero_and_now_carry_a_value": was_zero_now_value,
                "meaning": "this is the FEA-01 fix at the input layer: the same builder, the same fill rule, a panel "
                           "whose funding support is not the later live list"}
        else:
            rc["C3_effect_input_layer"]["C3b_full_coverage_panel"] = {"outcome": "INVALID", "error": e4,
                                                                      "stdout_tail": so4[-500:]}
    else:
        rc["C3_effect_input_layer"]["skipped"] = "C2 did not pass; an uncertified builder's effect measurement is meaningless"

    rc["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rc["wall_s"] = round(time.time() - T0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(rc, open(OUT, "w"), indent=1, default=float)
    print("SUMMARY C2=%s hunks=%d wall=%.1fs" % (rc.get("gate_C2_pass"), len(hunks), rc["wall_s"]), flush=True)
    return 0


if __name__ == "__main__":
    # NOTE: `except BaseException` here would swallow the SystemExit(0) raised by sys.exit(main()) and re-exit 1, i.e.
    # a PASSING run would report failure to anyone reading the exit code. Catch Exception only.
    try:
        rc_ = main()
    except Exception:
        traceback.print_exc()
        rc_ = 1
    sys.exit(rc_)

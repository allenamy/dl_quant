#!/usr/bin/env python3
"""fm_king_control.py -- queue item 3 control for fm_king_fea_asof.py against its base pod_fea_ext_clamp.py.

  K1 SOURCE DIFF     recorded, not gated (behaviour is the gate).
  K2 LEGACY BITWISE  base vs new with FMK_CLOCK=legacy_Em1, FMK_MEMBER_CLAMP=legacy_unclamped, FMK_COVR_DIV=const2016:
                     FEA / E_ts / y4 / qvk / names / members must be BITWISE identical. FEA is compared through a
                     uint16 view so NaN payloads must match too -- FEA is mostly NaN by construction (non-members), so
                     a float comparison with NaN leniency would be far too weak here.
                     Extra meta keys the new builder adds (fm_knobs, fm_base_sha256) are not compared: the gate is that
                     every key the BASE writes is reproduced.
  K3 ONE KNOB AT A TIME  with the legacy arm certified, flip exactly one knob per run and report what moves. Counts
                     only -- an anchor/member/label delta, never a model or book claim.

Safety: no subprocess / os.system / bash / requests; no network, no venue; nothing under ~/wide_shadow or
~/dl_quant_live. Outside the FIXPROGRAM 14.1 battery rule.

Usage: FM_KCTL_OUT=<receipt.json> FM_KCTL_TMP=<scratchdir> python3 fm_king_control.py
"""
import os, sys, json, time, hashlib, difflib, traceback
import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CHAIN = os.path.join(REPO, "multi_asset", "exports", "research", "retrain_2026-09", "v4_chain_2026-09-09")
BASE = os.path.join(CHAIN, "pod_fea_ext_clamp.py")
NEW = os.path.join(HERE, "fm_king_fea_asof.py")
OUT = os.environ["FM_KCTL_OUT"]
TMP = os.environ["FM_KCTL_TMP"]
os.makedirs(TMP, exist_ok=True)
os.environ.setdefault("FM_RED_OUT", os.path.join(TMP, "_unused.json"))
os.environ.setdefault("FM_RED_TMP", TMP)
sys.path.insert(0, HERE)
import fm_red_builders as FX   # noqa: E402

BASE_META_KEYS = ("E_ts", "members", "y4", "qvk", "names")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def bitwise(a, b):
    if a.shape != b.shape or a.dtype != b.dtype:
        return False, {"shape_a": list(a.shape), "shape_b": list(b.shape),
                       "dtype_a": str(a.dtype), "dtype_b": str(b.dtype)}
    if a.dtype == np.float16:
        d = int((a.view(np.uint16) != b.view(np.uint16)).sum())
        return d == 0, {"differing": d, "total": int(a.size), "as": "uint16 view (true bitwise)"}
    if a.dtype == object:                      # members: ragged arrays of int64
        bad = sum(0 if (np.array_equal(x, y)) else 1 for x, y in zip(a, b))
        return bad == 0 and len(a) == len(b), {"differing_rows": bad, "rows_a": len(a), "rows_b": len(b),
                                               "as": "per-row np.array_equal on int64 member lists"}
    if a.dtype == np.float32:
        d = int((a.view(np.uint32) != b.view(np.uint32)).sum())
        return d == 0, {"differing": d, "total": int(a.size), "as": "uint32 view (true bitwise)"}
    d = int((a != b).sum())
    return d == 0, {"differing": d, "total": int(a.size), "as": str(a.dtype)}


def run_base(cache, panel, fea, meta):
    return FX.run_builder(BASE, {"CACHE_IN": cache, "PANEL_IN": panel, "FEA_OUT": fea, "META_OUT": meta})


def run_new(cache, panel, fea, meta, clock, mclamp, covrdiv):
    return FX.run_builder(NEW, {"FMK_CACHE": cache, "FMK_PANEL": panel, "FMK_FEA_OUT": fea, "FMK_META_OUT": meta,
                                "FMK_CLOCK": clock, "FMK_MEMBER_CLAMP": mclamp, "FMK_COVR_DIV": covrdiv})


def summarise(fea, meta):
    F = np.load(fea)
    M = np.load(meta, allow_pickle=True)
    return {"n_anchors": int(len(M["E_ts"])), "first_anchor_ts": int(M["E_ts"][0]), "last_anchor_ts": int(M["E_ts"][-1]),
            "mean_members": float(np.mean([len(x) for x in M["members"]])), "fea_shape": list(F.shape)}


def main():
    rc = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)),
          "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "python": sys.version.split()[0], "numpy": np.__version__,
          "base": {"path": os.path.relpath(BASE, REPO), "sha256": sha(BASE)},
          "new": {"path": os.path.relpath(NEW, REPO), "sha256": sha(NEW)},
          "fixture_device_sha256": sha(FX.__file__), "shells_out": False, "network": False}

    a, b = open(BASE).read().splitlines(), open(NEW).read().splitlines()
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    hunks = [{"tag": t, "base": [i1 + 1, i2], "new": [j1 + 1, j2]} for t, i1, i2, j1, j2 in ops if t != "equal"]
    rc["K1_source_diff"] = {"n_changed_hunks": len(hunks), "hunks": hunks,
                            "note": "recorded, not gated: identical BEHAVIOUR is the gate (K2)"}
    print("K1 changed hunks: %d" % len(hunks), flush=True)

    d = os.path.join(TMP, "k")
    os.makedirs(d, exist_ok=True)
    cache = os.path.join(d, "cache.npz")
    ts, syms, data = FX.make_cache(cache, seed=21)
    panel = os.path.join(d, "panel.npz")
    FX.make_panel(panel, ts, syms, data)

    fb, mb = os.path.join(d, "base.npy"), os.path.join(d, "base_meta.npz")
    okb, sob, eb = run_base(cache, panel, fb, mb)
    fl, ml = os.path.join(d, "leg.npy"), os.path.join(d, "leg_meta.npz")
    okl, sol, el = run_new(cache, panel, fl, ml, "legacy_Em1", "legacy_unclamped", "const2016")
    if not (okb and okl) or not all(os.path.exists(p) for p in (fb, mb, fl, ml)):
        rc["K2_legacy_bitwise"] = {"outcome": "INVALID", "base_ok": okb, "new_ok": okl,
                                   "error": eb or el, "stdout_tail": (sob + sol)[-900:]}
        rc["gate_K2_pass"] = False
    else:
        FB, FL = np.load(fb), np.load(fl)
        MB, ML = np.load(mb, allow_pickle=True), np.load(ml, allow_pickle=True)
        per = {}
        allok, det = bitwise(FB, FL)
        per["FEA"] = {"bitwise_equal": allok, **det}
        for k in BASE_META_KEYS:
            eq, dd = bitwise(MB[k], ML[k])
            per[k] = {"bitwise_equal": eq, **dd}
            allok = allok and eq
        rc["K2_legacy_bitwise"] = {"outcome": "PASS" if allok else "FAIL", "per_array": per,
                                   "base_meta_keys_compared": list(BASE_META_KEYS),
                                   "new_extra_meta_keys_not_compared": [k for k in ML.files if k not in MB.files]}
        rc["gate_K2_pass"] = allok
        print("K2 legacy bitwise: %s" % ("PASS" if allok else "FAIL"), flush=True)

    rc["K3_one_knob_at_a_time"] = {"note": "anchor/member/label counts only; NOT a model or book claim",
                                   "legacy": summarise(fb, mb) if os.path.exists(mb) else None}
    if rc.get("gate_K2_pass"):
        for tag, knobs in (("clock_serve_E", ("serve_E", "legacy_unclamped", "const2016")),
                           ("member_clamped", ("legacy_Em1", "clamped", "const2016")),
                           ("covr_actual_window", ("legacy_Em1", "legacy_unclamped", "actual_window")),
                           ("clamped_and_actual_window", ("legacy_Em1", "clamped", "actual_window"))):
            f2, m2 = os.path.join(d, "%s.npy" % tag), os.path.join(d, "%s_meta.npz" % tag)
            ok2, so2, e2 = run_new(cache, panel, f2, m2, *knobs)
            if ok2 and os.path.exists(m2):
                s = summarise(f2, m2)
                base_ts = set(int(x) for x in np.load(mb, allow_pickle=True)["E_ts"])
                new_ts = set(int(x) for x in np.load(m2, allow_pickle=True)["E_ts"])
                s["anchors_gained_vs_legacy"] = len(new_ts - base_ts)
                s["anchors_lost_vs_legacy"] = len(base_ts - new_ts)
                s["knobs"] = dict(zip(("clock", "member_clamp", "covr_div"), knobs))
                rc["K3_one_knob_at_a_time"][tag] = s
                print("K3 %-26s anchors %d (+%d/-%d)" % (tag, s["n_anchors"], s["anchors_gained_vs_legacy"],
                                                         s["anchors_lost_vs_legacy"]), flush=True)
            else:
                rc["K3_one_knob_at_a_time"][tag] = {"outcome": "INVALID", "error": e2, "stdout_tail": so2[-500:]}
                print("K3 %-26s INVALID" % tag, flush=True)
    else:
        rc["K3_one_knob_at_a_time"]["skipped"] = "K2 did not pass; an uncertified builder's readings are meaningless"

    rc["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rc["wall_s"] = round(time.time() - T0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(rc, open(OUT, "w"), indent=1, default=float)
    print("SUMMARY K2=%s hunks=%d wall=%.1fs" % (rc.get("gate_K2_pass"), len(hunks), rc["wall_s"]), flush=True)
    return 0


if __name__ == "__main__":
    try:
        _rc = main()
    except Exception:
        traceback.print_exc()
        _rc = 1
    sys.exit(_rc)

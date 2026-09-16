#!/usr/bin/env python3
"""fx_trd01_inject.py — FX-DATA TRD-01 step C (pod2, CPU, read-only on every input). Committed before it is run.

Builds the four injection artifacts SPEC_TRADABILITY_2026-09-13 section 7 needs, so the A0 effect measurement can run on the
UNMODIFIED device `/workspace/uplift_2026-09-11/w10_sleeve.py` (sha b88e35a4). Nothing existing is edited; four new files.

  TU arm   UMASK_NPZ = U-PIT/CRYPTO AND tradable(A)        -> shrinks the member set and the trade set
  TB arm   FEMAT_NPZ = f_fund_ema_v1 with non-tradable cells set to NaN   -> shrinks the fund rank base only
  TF arm   both
  TF4 arm  both, built with W = 4 h (sensitivity; never sets a label)

The device reads the injected files as (symbols, ts, mask) and (symbols, ts, mat) on the A0 panel's own ts, and asserts the symbol
and ts axes match, so both artifacts are written on `/workspace/data/wide_panel_4h_v2ext.npz`'s 10,039-anchor axis.

Positive controls, all before anything is written:
  P1  the base mask re-read from the committed `umask_UPIT_CRYPTO.npz` is used as-is; the tradable variant must be a strict SUBSET
      of it (a mask that ever ADDS a name would mean the flag is not being intersected).
  P2  the base FEMAT matrix must equal the panel's `f_fund_ema_v1` BITWISE before masking; the masked variant must differ only by
      cells becoming NaN, never by a value change.
  P3  every anchor of the panel axis must be on the tradability artifact's 4h grid; a missing anchor is a hard failure, never a
      silently carried-forward row.

Usage: python3 fx_trd01_inject.py <artifact.npz> <artifact_sha256> <out_dir> <out_receipt.json>
Exit 0 only if every control passed.
"""
import os, sys, json, time, zipfile
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
ART, ART_SHA, OUT_DIR, OUT = sys.argv[1:5]
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T
assert T.SPEC_SHA256 == "99ae35e01ec3dd06ba7bf69ea62de8f36cfd2695492ccf53757d985b8a0946b2"

W = "/workspace"
PANEL = f"{W}/data/wide_panel_4h_v2ext.npz"
UMASK = f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
FAILS = []; CHECKS = []
def check(name, ok, detail=None):
    CHECKS.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail is not None else {})})
    if not ok: FAILS.append(name)
    return ok

rec = {"device": "fx_trd01_inject.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "spec_sha256": T.SPEC_SHA256, "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)},
       "inputs": {p: T.guarded_sha256(p) for p in (PANEL, UMASK)}, "utc_start": utc(time.time())}
A = T.Artifact.load(ART, expected_sha256=ART_SHA)
rec["artifact"] = {"path": ART, "sha256": A.sha256}

P = np.load(PANEL, allow_pickle=True); pts = P["ts"].astype(np.int64); psym = [str(s) for s in P["symbols"]]
FE1 = np.asarray(P["f_fund_ema_v1"])
U = np.load(UMASK, allow_pickle=True); uts = U["ts"].astype(np.int64); UM = np.asarray(U["mask"])
assert [str(s) for s in U["symbols"]] == psym, "umask symbols != panel symbols"
assert np.array_equal(uts, pts), "umask ts != panel ts"
assert psym == A.symbols, "panel symbols != tradability artifact symbols"
missing = [int(t) for t in pts if int(t) not in A._row]
check("P3.every_panel_anchor_on_the_tradability_grid", not missing,
      {"panel_anchors": int(len(pts)), "missing": missing[:10], "n_missing": len(missing)})
rec["axes"] = {"panel_anchors": int(len(pts)), "first": utc(pts[0]), "last": utc(pts[-1]), "symbols": len(psym)}
log("axes ok", json.dumps(rec["axes"]))

def det_npz(path, arrays):
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for k in sorted(arrays):
            zi = zipfile.ZipInfo(k + ".npy", date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            a = np.asarray(arrays[k]); a = a if a.ndim == 0 else np.ascontiguousarray(a)
            with zf.open(zi, "w", force_zip64=True) as fh: np.lib.format.write_array(fh, a, allow_pickle=False)
    os.replace(tmp, path)

os.makedirs(OUT_DIR, exist_ok=True)
outs = {}; stats = {}
if not FAILS:
    rows = A.rows(pts)
    for wnd in ("W24H", "W4H"):
        TR = A._z["state_" + wnd][rows] == T.TRADABLE
        um2 = UM & TR
        check("P1.%s.mask_is_a_strict_subset" % wnd, bool((um2 & ~UM).sum() == 0),
              {"added_cells": int((um2 & ~UM).sum())})
        fe2 = np.array(FE1, copy=True); fe2[~TR] = np.nan
        base_eq = bool(np.array_equal(np.asarray(FE1, np.float64), np.asarray(FE1, np.float64), equal_nan=True))
        changed = np.isfinite(FE1) & np.isfinite(fe2) & (np.asarray(FE1, np.float64) != np.asarray(fe2, np.float64))
        check("P2.%s.femat_only_loses_cells_never_changes_a_value" % wnd, bool(changed.sum() == 0 and base_eq),
              {"value_changed_cells": int(changed.sum()),
               "cells_made_nan": int((np.isfinite(FE1) & ~np.isfinite(fe2)).sum())})
        pm = os.path.join(OUT_DIR, "umask_UPIT_CRYPTO_tradable_%s.npz" % wnd)
        pf = os.path.join(OUT_DIR, "femat_f_fund_ema_v1_tradable_%s.npz" % wnd)
        det_npz(pm, {"ts": pts, "symbols": np.array(psym), "mask": um2,
                     "spec_sha256": np.array(T.SPEC_SHA256), "tradability_sha256": np.array(A.sha256),
                     "definition": np.array("umask_UPIT_CRYPTO AND tradable(A) with window " + wnd)})
        det_npz(pf, {"ts": pts, "symbols": np.array(psym), "mat": np.asarray(fe2, FE1.dtype),
                     "spec_sha256": np.array(T.SPEC_SHA256), "tradability_sha256": np.array(A.sha256),
                     "definition": np.array("panel f_fund_ema_v1 with non-tradable cells set to NaN, window " + wnd)})
        outs["umask_" + wnd] = {"path": pm, "sha256": T.guarded_sha256(pm), "bytes": os.path.getsize(pm)}
        outs["femat_" + wnd] = {"path": pf, "sha256": T.guarded_sha256(pf), "bytes": os.path.getsize(pf)}
        stats[wnd] = {"umask_true_before": int(UM.sum()), "umask_true_after": int(um2.sum()),
                      "umask_cells_dropped": int((UM & ~TR).sum()),
                      "umask_dropped_share": round(float((UM & ~TR).sum()) / max(int(UM.sum()), 1), 6),
                      "femat_finite_before": int(np.isfinite(FE1).sum()), "femat_finite_after": int(np.isfinite(fe2).sum()),
                      "femat_cells_made_nan": int((np.isfinite(FE1) & ~np.isfinite(fe2)).sum()),
                      "femat_dropped_share": round(float((np.isfinite(FE1) & ~np.isfinite(fe2)).sum()) / max(int(np.isfinite(FE1).sum()), 1), 6)}
        log(wnd, json.dumps(stats[wnd]))
rec["outputs"] = outs; rec["stats"] = stats
rec["checks"] = CHECKS; rec["n_checks"] = len(CHECKS); rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_TRD01_INJECT_DONE", json.dumps({"failed": len(FAILS), "outputs": {k: v["sha256"][:16] for k, v in outs.items()}}), flush=True)
sys.exit(1 if FAILS else 0)

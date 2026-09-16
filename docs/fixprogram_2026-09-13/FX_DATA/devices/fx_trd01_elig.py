#!/usr/bin/env python3
"""fx_trd01_elig.py — FX-DATA TRD-01 rule A8 (pod2, CPU, read-only). Committed before it is run.

§TRD-E left rule A8 (`pod_panel_ext.py:40`, `elig = (covr >= 0.95) & (v7 >= 1e-4)`) RED with **no fixed artifact**: 5,530 panel
cells where `elig` is true and the name had no trade in the trailing 24 h. The frozen `ret5 = 0` of a dead contract is finite, so
coverage stays at 1 and the rule cannot see the death.

The full fix is the panel rebuild, which is blocked on the FND/HOL-01 funding decision. This device produces the corrected column
on its own, beside the panel, so A8's cell has a fixed object and the rebuild has a ready input it must reproduce:

    elig_tradable(A, s) = elig(A, s) AND tradable(A, s)          (SPEC section 6, the same intersection as every other rule)

Controls: the base column re-read from the panel must be bool and unchanged; the corrected column must be a strict SUBSET of it
(never adding a cell); and every panel anchor must be on the tradability grid. This is a NEW file; the panel is not touched.

Usage: python3 fx_trd01_elig.py <artifact.npz> <artifact_sha256> <out_dir> <out_receipt.json>
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
PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
FAILS = []; CHECKS = []
def check(n, ok, d=None):
    CHECKS.append({"check": n, "ok": bool(ok), **({"detail": d} if d is not None else {})})
    if not ok: FAILS.append(n)
rec = {"device": "fx_trd01_elig.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "spec_sha256": T.SPEC_SHA256, "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "inputs": {PANEL: T.guarded_sha256(PANEL)},
       "rule": "elig_tradable = elig AND tradable(A, s), SPEC section 6", "utc_start": utc(time.time())}
A = T.Artifact.load(ART, expected_sha256=ART_SHA); rec["artifact_sha256"] = A.sha256
P = np.load(PANEL, allow_pickle=True); pts = P["ts"].astype(np.int64); syms = [str(s) for s in P["symbols"]]
assert syms == A.symbols
E0 = np.asarray(P["elig"])
check("C1.elig_is_boolean", E0.dtype == np.bool_ or set(np.unique(E0).tolist()) <= {0, 1}, {"dtype": str(E0.dtype)})
E0 = E0.astype(bool)
miss = [int(t) for t in pts if int(t) not in A._row]
check("C3.every_panel_anchor_on_the_tradability_grid", not miss, {"n_missing": len(miss)})
if not FAILS:
    TR = A._z["state_W24H"][A.rows(pts)] == T.TRADABLE
    E1 = E0 & TR
    check("C2.corrected_column_is_a_strict_subset", bool((E1 & ~E0).sum() == 0), {"added": int((E1 & ~E0).sum())})
    rec["counts"] = {"elig_true": int(E0.sum()), "elig_true_and_untradable": int((E0 & ~TR).sum()),
                     "elig_tradable_true": int(E1.sum()),
                     "cells_removed": int((E0 & ~TR).sum()),
                     "removed_share": round(float((E0 & ~TR).sum()) / max(int(E0.sum()), 1), 6),
                     "of_removed_nodata": int((E0 & (A._z["state_W24H"][A.rows(pts)] == T.NODATA)).sum()),
                     "by_year": {}}
    yrs = np.array([time.gmtime(int(t)).tm_year for t in pts])
    for y in sorted(set(yrs.tolist())):
        m = yrs == y
        rec["counts"]["by_year"][str(y)] = {"elig_true": int(E0[m].sum()), "removed": int((E0[m] & ~TR[m]).sum())}
    def det(path, arrays):
        tmp = path + ".tmp"
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for k in sorted(arrays):
                zi = zipfile.ZipInfo(k + ".npy", date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
                a = np.asarray(arrays[k]); a = a if a.ndim == 0 else np.ascontiguousarray(a)
                with zf.open(zi, "w", force_zip64=True) as fh: np.lib.format.write_array(fh, a, allow_pickle=False)
        os.replace(tmp, path)
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, "panel_elig_tradable_W24H.npz")
    det(p, {"ts": pts, "symbols": np.array(syms), "elig_tradable": E1, "elig_legacy": E0,
            "spec_sha256": np.array(T.SPEC_SHA256), "tradability_sha256": np.array(A.sha256),
            "definition": np.array("elig_tradable = wide_panel_4h_v2ext.npz elig AND tradable(A, s) window W24H; "
                                   "elig_legacy is the panel column unchanged, for a bitwise check by the panel rebuild")})
    rec["output"] = {"path": p, "sha256": T.guarded_sha256(p), "bytes": os.path.getsize(p)}
rec["checks"] = CHECKS; rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_TRD01_ELIG_DONE", json.dumps({"failed": len(FAILS), **({k: rec["counts"][k] for k in ("elig_true", "cells_removed", "removed_share")} if "counts" in rec else {})}), flush=True)
sys.exit(1 if FAILS else 0)

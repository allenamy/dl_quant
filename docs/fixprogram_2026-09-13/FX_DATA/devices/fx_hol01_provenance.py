#!/usr/bin/env python3
"""fx_hol01_provenance.py — FX-DATA HOL-01 (pod2, CPU, read-only). Committed before it is run.

HOL-01 (AUDIT_DATA bb8a2806, P2): the panels every replay and the v4 chain read were built on the pre-holefix cache. Before building
anything, two things about the existing tree have to be settled, because both change what HOL-01's remaining work actually is.

  R  `wide_panel_4h_rawbuild_x0910.npz` — the reference AD_D compared against — IS the hole-fixed rebuild. The r6 chain's step S4
     (`r6_chain.sh:32-34`, committed by LIN-01) runs `/workspace/pod_panel_ext.py` UNMODIFIED with CACHE_IN = the holefix2 x0910 cache
     and PANEL_OUT = that file. **It has no receipt of its own**; only the chain log. This device records its sha, shape, axis and the
     chain step that produced it, so the one existing hole-fixed panel stops being an unreceipted file on pod2.
  B  AD_D's positive control PASSES for v2ext and v2holefix (0 kline cells differ away from a hole run) and FAILS for v3splice, with
     **136** cells differing away from every hole. The receipt localises them to `f_mom_30d` at ONE anchor, 2022-01-31T00:00Z, the
     first common anchor. This device tests whether that is a 30-day-lookback boundary effect of the splice rather than a hole: it
     compares v3splice, v2ext and the rebuild cell by cell at that anchor, and reports how many of the 136 names have v3splice equal
     to v2ext (both from the older lineage) against the rebuild.
  F  the funding keys of v3splice differ from the rebuild on ~1.03M cells by PATTERN with max |value difference| 0.0 on f_fund_now.
     Reported as a coverage difference, separately from the value differences on the EMA keys, so the two are never merged.

Usage: python3 fx_hol01_provenance.py <out_receipt.json>
"""
import os, sys, json, time
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
OUT = sys.argv[1]
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[0])
import tradability as T

W = "/workspace"
REF = f"{W}/uplift_2026-09-11/r6/out/wide_panel_4h_rawbuild_x0910.npz"
V2 = f"{W}/data/wide_panel_4h_v2ext.npz"; V3 = f"{W}/data/wide_panel_4h_v3splice.npz"
CHAIN = f"{W}/uplift_2026-09-11/r6/r6_chain.sh"; BUILDER = f"{W}/pod_panel_ext.py"
CACHE_X = f"{W}/data/dlnative_5m_wide829_f16_holefix2_x0910.npz"
T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)

rec = {"device": "fx_hol01_provenance.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "numpy": np.__version__, "argv": sys.argv, "env": {k: os.environ[k] for k in sorted(os.environ)},
       "inputs": {p: T.guarded_sha256(p) for p in (REF, V2, V3, CHAIN, BUILDER, CACHE_X)}, "utc_start": utc(time.time())}

R = np.load(REF, allow_pickle=True); A2 = np.load(V2, allow_pickle=True); A3 = np.load(V3, allow_pickle=True)
rts = R["ts"].astype(np.int64); rsym = [str(s) for s in R["symbols"]]
rec["R_reference_panel"] = {
    "path": REF, "sha256": rec["inputs"][REF], "bytes": os.path.getsize(REF),
    "anchors": int(len(rts)), "first": utc(rts[0]), "last": utc(rts[-1]), "symbols": len(rsym), "keys": sorted(R.files),
    "produced_by": "r6_chain.sh step S4 (committed at uplift_2026-09-11/r6_devices/r6_chain.sh): "
                   "CACHE_IN=<holefix2 x0910> PANEL_OUT=<this file> python /workspace/pod_panel_ext.py, builder UNMODIFIED",
    "builder_sha256": rec["inputs"][BUILDER], "cache_sha256": rec["inputs"][CACHE_X], "chain_sha256": rec["inputs"][CHAIN],
    "receipt_of_its_own": False,
    "note": "this is the one hole-fixed full-history 4h panel that exists; AD_D used it as its reference"}
log("R", json.dumps({k: v for k, v in rec["R_reference_panel"].items() if k != "keys"})[:400])

# ---------------- B. the 136 away-from-hole cells ----------------
t0a = 1643587200                      # 2022-01-31T00:00Z, the first common anchor
r2 = {int(t): j for j, t in enumerate(A2["ts"].astype(np.int64))}
r3 = {int(t): j for j, t in enumerate(A3["ts"].astype(np.int64))}
rr = {int(t): j for j, t in enumerate(rts)}
assert [str(s) for s in A2["symbols"]] == rsym == [str(s) for s in A3["symbols"]]
K = "f_mom_30d"
a = np.asarray(A3[K][r3[t0a]], np.float64); b = np.asarray(R[K][rr[t0a]], np.float64); c = np.asarray(A2[K][r2[t0a]], np.float64)
def diffcells(x, y):
    fx, fy = np.isfinite(x), np.isfinite(y)
    pat = fx != fy
    val = fx & fy & (np.abs(x - y) > 1e-6 * np.maximum(1.0, np.abs(y)))
    return pat, val
p_ab, v_ab = diffcells(a, b); p_cb, v_cb = diffcells(c, b); p_ac, v_ac = diffcells(a, c)
idx = np.where(p_ab | v_ab)[0]
rec["B_away_from_hole_cells"] = {
    "anchor": utc(t0a), "key": K,
    "v3splice_vs_rebuild_diff_cells": int(len(idx)),
    "v2ext_vs_rebuild_diff_cells": int((p_cb | v_cb).sum()),
    "v3splice_vs_v2ext_diff_cells": int((p_ac | v_ac).sum()),
    "of_the_v3splice_diff_cells_how_many_have_v3splice_equal_to_v2ext": int((~(p_ac | v_ac))[idx].sum()),
    "max_abs_diff_v3_vs_rebuild": float(np.abs(a[idx] - b[idx])[np.isfinite(a[idx] - b[idx])].max()) if len(idx) else 0.0,
    "examples": [{"symbol": rsym[int(j)], "v3splice": float(a[j]), "v2ext": float(c[j]), "rebuild": float(b[j])} for j in idx[:12]],
    "reading": ("f_mom_30d looks back 30 days. 2022-01-31T00:00Z is the first common anchor and the rebuild's cache starts "
                "2022-01-01, so the rebuild has exactly the minimum history there while the older lineage carried more. "
                "If v3splice equals v2ext on these cells and both differ from the rebuild, the difference is a lookback boundary "
                "of the splice, not a hole; the counts above decide it rather than the wording.")}
log("B", json.dumps({k: v for k, v in rec["B_away_from_hole_cells"].items() if k not in ("examples", "reading")}))

# ---------------- F. funding keys: pattern vs value ----------------
com = np.array(sorted(set(r3) & set(rr)), np.int64)
i3 = np.array([r3[int(t)] for t in com]); ir = np.array([rr[int(t)] for t in com])
F = {}
for k in ("f_fund_now", "f_fund_iv", "f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2"):
    x = np.asarray(A3[k][i3], np.float64); y = np.asarray(R[k][ir], np.float64)
    fx, fy = np.isfinite(x), np.isfinite(y)
    pat = int((fx != fy).sum()); both = fx & fy
    d = np.abs(x[both] - y[both])
    F[k] = {"cells": int(x.size), "pattern_diff": pat, "only_v3splice_finite": int((fx & ~fy).sum()),
            "only_rebuild_finite": int((~fx & fy).sum()),
            "value_diff_cells_gt_1e-6_rel": int((d > 1e-6 * np.maximum(1.0, np.abs(y[both]))).sum()),
            "max_abs_value_diff": float(d.max()) if d.size else 0.0}
rec["F_funding_keys_v3splice_vs_rebuild"] = F
rec["F_note"] = ("a pattern difference means one panel has a funding value where the other has none — a coverage difference from the "
                 "canonical EMA continuation, not a disagreement about a value. It must not be added to the value-difference counts.")
log("F", json.dumps(F)[:400])
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
print("FX_HOL01_DONE", json.dumps({"ref_sha256": rec["inputs"][REF][:16],
                                   "away_cells": rec["B_away_from_hole_cells"]["v3splice_vs_rebuild_diff_cells"],
                                   "v3_equals_v2ext_on": rec["B_away_from_hole_cells"]["of_the_v3splice_diff_cells_how_many_have_v3splice_equal_to_v2ext"]}), flush=True)

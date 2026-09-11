"""KLASS SURVEY -- independence SCREEN (NOT a judge verdict, NOT a candidate).

ENV WHITELIST (E-0826-D) = EMPTY SET. This script reads NO environment variable.
Purpose: measure rho-to-A0 of structurally-different standalone objectives on the PINNED v4
accounting matrix, so the survey ranks on MEASURED independence instead of inferred independence.

Pins (CALIBER_PIN_v4_2026-09-11):
  meta  = /workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz   (RAW accounting, y4)
  A0    = dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz      (d30_n2_c42_rec)
  g     = net_ex / gross_total, bps per 4h anchor per unit gross
  window= drop first 900 device anchors (E-0911-A), cap 2026-08-30 20:00Z (E-0911-D)
"""
import os, sys, json, hashlib
_FORBIDDEN = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED",
              "COSTB_JSON","MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
_bad = [k for k in _FORBIDDEN if k in os.environ]
assert not _bad, f"ENV WHITELIST VIOLATION (E-0826-D): {_bad}"
import numpy as np

def sha16(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<22), b''): h.update(b)
    return h.hexdigest()[:16]

META = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0P  = "/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
print("PIN meta sha16", sha16(META))
print("PIN A0   sha16", sha16(A0P))

m = np.load(META, allow_pickle=True)
E_ts = m["E_ts"].astype(np.int64); Y = m["y4"].astype(np.float64); QV = m["qvk"].astype(np.float64)
members = m["members"]
T, N = Y.shape
print("meta T,N", T, N, "E_ts[0]", E_ts[0], "E_ts[-1]", E_ts[-1])

a = np.load(A0P, allow_pickle=True)
cols = list(a["cols"]); rec = a["d30_n2_c42_rec"]
ci = {c:i for i,c in enumerate(cols)}
a_ts = rec[:, ci["ts"]].astype(np.int64)
g_a0 = rec[:, ci["net_ex"]] / rec[:, ci["gross_total"]]
# sanity: A0 turnover / cost per unit turnover
tv = rec[:, ci["turnover"]]; cst = rec[:, ci["cost_ex"]]/rec[:, ci["gross_total"]]
print("A0 anchors", len(a_ts), "ts0", a_ts[0], "tsN", a_ts[-1])

# ---- window: post-warm 900 + E-0911-D cap
CAP = 1788120000  # 2026-08-30T20:00:00Z (computed, asserted below)
import datetime
assert datetime.datetime.utcfromtimestamp(CAP).strftime("%Y-%m-%dT%H:%M:%SZ") == "2026-08-30T20:00:00Z", "cap ts wrong"
keep_a = np.arange(len(a_ts)) >= 900
keep_a &= (a_ts <= CAP)
a_ts_k = a_ts[keep_a]; g_a0_k = g_a0[keep_a]
print("A0 post-warm+cap n =", len(a_ts_k))
print("A0 mean g bps", round(float(np.nanmean(g_a0_k)),4),
      "Sharpe ann", round(float(np.nanmean(g_a0_k)/np.nanstd(g_a0_k,ddof=1)*np.sqrt(2190)),4))
print("A0 turnover mean", round(float(tv[keep_a].mean()),5),
      "bps/unit turnover", round(float(cst[keep_a].sum()/tv[keep_a].sum()),4))

# ---- align meta rows to A0 anchors
pos = {int(t):i for i,t in enumerate(E_ts)}
idx = np.array([pos.get(int(t), -1) for t in a_ts_k])
assert (idx >= 0).all(), f"unmapped anchors: {(idx<0).sum()}"
print("alignment OK, all", len(idx), "A0 anchors found in meta")
np.save("/workspace/uplift_2026-09-11/klass_idx.npy", idx)
np.save("/workspace/uplift_2026-09-11/klass_g_a0.npy", g_a0_k)
np.save("/workspace/uplift_2026-09-11/klass_ts.npy", a_ts_k)
print("QV stats: median", np.nanmedian(QV[QV>0]), "p99", np.nanpercentile(QV[QV>0],99))
print("y4 finite frac", float(np.isfinite(Y).mean()))
print("members[0] type", type(members[0]), "len", len(members[0]) if hasattr(members[0],'__len__') else None)

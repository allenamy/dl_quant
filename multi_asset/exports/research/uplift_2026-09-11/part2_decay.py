#!/usr/bin/env python3
"""Part 2: invert the EMA to recover the pre-smoothing target tgt_t, validate (gross must be 1.0),
then build the lagged-target return matrix L[k] = tgt_{t-k} . y4_{t+1}, which prices ANY alpha."""
import os, json, glob, time
import numpy as np
exec(open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/smooth_latency_core.py").read().split("# ---- 1.")[0])

def invert(SM, anchors):
    """sm_t = H + a*(tgt-H), band: |sm-H|<band => sm=H ; forced exit: sm==0 exactly with H!=0.
    Returns dict A -> (tgt_est, diag)."""
    T = {}
    for i, A in enumerate(anchors):
        if i == 0: continue
        Ap = A - 14400
        if Ap not in SM: continue
        sm = SM[A]; H = SM[Ap]
        d = sm - H
        forced = (sm == 0.0) & (np.abs(H) > 1e-12)
        moved = (np.abs(d) > 1e-12) & (~forced)
        tgt = H.copy()                      # banded names: best estimate is H (|tgt-H| < band/a)
        tgt[moved] = H[moved] + d[moved] / ALPHA
        tgt[forced] = 0.0                   # forced-exit names are out of sel => target is 0
        T[A] = (tgt, {"n_moved": int(moved.sum()), "n_forced": int(forced.sum()),
                      "n_banded_held": int(((np.abs(d) <= 1e-12) & (np.abs(H) > 1e-12)).sum()),
                      "gross_tgt": float(np.abs(tgt).sum()), "gross_sm": float(np.abs(sm).sum()),
                      "turnover": float(np.abs(d).sum())})
    return T

TK = invert(SMK, kw)
gt = np.array([v[1]["gross_tgt"] for v in TK.values()])
gs = np.array([v[1]["gross_sm"] for v in TK.values()])
tv = np.array([v[1]["turnover"] for v in TK.values()])
nb = np.array([v[1]["n_banded_held"] for v in TK.values()])
nm = np.array([v[1]["n_moved"] for v in TK.values()])
nf = np.array([v[1]["n_forced"] for v in TK.values()])
print(f"\n[INVERT king] n={len(TK)}")
print(f"  recovered gross(tgt) : mean {gt.mean():.4f} sd {gt.std():.4f} min {gt.min():.4f} max {gt.max():.4f}   <-- TRUTH IS 1.0000 (chain L-normalises)")
print(f"  book  gross(sm)      : mean {gs.mean():.4f} sd {gs.std():.4f}")
print(f"  turnover |dw| /anchor: mean {tv.mean():.5f} median {np.median(tv):.5f}  (unit-gross caliber)")
print(f"  names moved {nm.mean():.1f} | held-by-band {nb.mean():.1f} | forced-exit {nf.mean():.2f}")

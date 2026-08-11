#!/usr/bin/env python3
"""Build the S2-pred strictly-OOS panel (king_pred_panel recipe) from wideA_s2_y24_5yr.

Each ts uses ONLY its own test-fold's honest-ensemble composite (per-ts z-mean of the 6
factor heads over member&CL&finite cells). Format aligned to king_pred_panel.npz.
"""
import numpy as np, pandas as pd, glob, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
XK = MA + "/exports/train/wideA_s2_y24_5yr"
OUT = MA + "/exports/eda/s2_pred_panel.npz"


def comp_panel(scores, member, CL, YR):
    T, N, K = scores.shape
    C = np.full((T, N), np.nan)
    for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk:
            C[t, base] = comp / nk
    return C


pr = np.load(XK + "/panel_ref.npz", allow_pickle=True)
member, CL = pr["member"].astype(bool), pr["CL"].astype(bool)
YR, Yraw = pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
ts = pr["ts"].astype(np.int64); day = pr["day"]
yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
T, N = Yraw.shape

S2 = np.full((T, N), np.nan, np.float32)
overlap = 0; fold_cover = {}
for f in sorted(glob.glob(XK + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
    z = np.load(f)
    te = z["te_rows"]
    Y = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min())
    C = comp_panel(z["scores"], member, CL, YR)
    m = np.isfinite(C)
    overlap += int((m & np.isfinite(S2)).sum())
    S2[m] = C[m].astype(np.float32)
    fold_cover[Y] = int(m.any(1).sum())

np.savez(OUT, ts=ts, s2_pred=S2, member=member, CL=CL,
         YR=YR.astype(np.float32), Yraw=Yraw.astype(np.float32), day=day, year=yr)
cov_rows = int(np.isfinite(S2).any(1).sum())
rep = {"out": OUT, "s2_pred_finite_frac": round(float(np.isfinite(S2).mean()), 4),
       "cov_rows": cov_rows, "cross_fold_overlap_cells": overlap,
       "fold_cover_ts": fold_cover, "CL_horizon": int(pr["horizon"]),
       "note": "S2 at CL24 anchors (horizon=24); king at CL4"}
json.dump(rep, open(MA + "/exports/eda/s2_pred_panel_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1))

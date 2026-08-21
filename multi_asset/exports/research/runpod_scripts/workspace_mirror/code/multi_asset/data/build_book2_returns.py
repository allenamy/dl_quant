#!/usr/bin/env python3
"""Phase-0b/A — export Book-2 (wide slow-premia) per-rebalance net-return series for 0C's cross-book corr.

> **created:** 2026-07-08 | **Session:** multi-asset-v2 consolidation (0B) | **状态:** in-progress

0C needs the wide L/S PnL per hourly rebalance WITH timestamps to align to Book-1's return series and
compute the cross-book correlation (the diversification claim: ~0 corr between mega-cap funding+M0 and
wide slow premia). Exports the SIZE sleeve (the cost-immune deployable leg) + the COMBINED slow-premia
book net-return series at the hourly rebalance, per-coin cost by DVOL tercile (2/5/10 bps base).
Output: exports/eda/book2_returns.npz + .csv {ts, size_net, size_gross, combined_net, combined_gross}.
"""
from __future__ import annotations
import csv, os.path as p
import numpy as np, pandas as pd

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
PANEL = E + "/wide_panel.npz"


def oriented_z(factor, Y, MEM):
    T, N = Y.shape; Z = np.zeros((T, N))
    for t in range(T):
        v = MEM[t] & np.isfinite(factor[t]) & np.isfinite(Y[t])
        if v.sum() >= 8:
            f = factor[t, v]; Z[t, np.where(v)[0]] = (f - f.mean()) / (f.std() + 1e-12)
    g = np.nansum((Z / (np.abs(Z).sum(1, keepdims=True) + 1e-12)) * np.nan_to_num(Y), axis=1)
    if np.nanmean(g) < 0:
        Z = -Z
    return Z


def series(Z, Y, tier, illiq_bps=10.0):
    s = np.abs(Z).sum(1, keepdims=True); W = np.where(s > 0, Z / s, 0.0)
    gross = np.nansum(W * np.nan_to_num(Y), axis=1)
    dW = np.abs(np.diff(W, axis=0, prepend=0.0)); tb = np.array([2.0, 5.0, illiq_bps]) / 1e4
    net = gross - (dW * tb[tier]).sum(1)
    return gross, net


def main():
    z = np.load(PANEL, allow_pickle=True)
    ts = z["ts"].astype(np.int64); Y = z["Y"].astype(np.float64); MEM = z["MEMBER"]; DV = z["DVOL30"].astype(np.float64)
    C = z["CLOSE"].astype(np.float64); logc = np.log(np.where(C > 0, C, np.nan))
    def shift(A, n):
        o = np.full_like(A, np.nan); o[n:] = A[:-n]; return o
    def roll(A, w, fn):
        return getattr(pd.DataFrame(A).rolling(w, min_periods=max(3, w // 2)), fn)().values
    ret = logc - shift(logc, 1)
    tier = np.zeros(Y.shape, np.int8)
    for t in range(Y.shape[0]):
        v = MEM[t] & np.isfinite(DV[t])
        if v.sum() >= 8:
            q = np.argsort(np.argsort(-DV[t, v])); nv = v.sum()
            tier[t, np.where(v)[0]] = np.where(q < nv / 3, 0, np.where(q < 2 * nv / 3, 1, 2))
    Z_size = oriented_z(-np.log(np.where(DV > 0, DV, np.nan)), Y, MEM)
    Z_lv = oriented_z(roll(ret, 24, "std"), Y, MEM)
    Z_max = oriented_z(roll(ret, 24, "max"), Y, MEM)
    Zc = np.nanmean(np.stack([Z_size, Z_lv, Z_max]), axis=0)
    sg, sn = series(Z_size, Y, tier)
    cg, cn = series(Zc, Y, tier)
    np.savez(p.join(E, "eda/book2_returns.npz"), ts=ts, size_net=sn, size_gross=sg,
             combined_net=cn, combined_gross=cg)
    with open(p.join(E, "eda/book2_returns.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ts_ms", "size_net", "size_gross", "combined_net", "combined_gross"])
        for i in range(len(ts)):
            if np.isfinite(sn[i]) or np.isfinite(cn[i]):
                w.writerow([int(ts[i]), f"{sn[i]:.8f}", f"{sg[i]:.8f}", f"{cn[i]:.8f}", f"{cg[i]:.8f}"])
    print(f"[book2] {int(np.isfinite(sn).sum())} hourly-rebalance return rows -> eda/book2_returns.{{npz,csv}}", flush=True)
    print(f"  size    mean_net/hr={np.nanmean(sn):+.2e}  combined mean_net/hr={np.nanmean(cn):+.2e}", flush=True)


if __name__ == "__main__":
    main()

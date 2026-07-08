#!/usr/bin/env python3
"""Phase-0b/A — WIDE net-cost L/S gate (does the revival trade net of cost? by liquidity tercile).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

The wide scorecard showed 14/20 factors REVIVE in IC at N=110 — but they're commoditized and small
coins have wide spreads. THIS is the north-star test: for each reviving factor, build the hourly
xsec z-weighted dollar-neutral L/S over the point-in-time active universe, and compute GROSS Sharpe/
IC vs NET-of-cost with PER-COIN cost by LIQUIDITY TERCILE (top-DVOL tercile = maker ~2bps, mid ~5,
bottom ~10 taker). Report break-even bps/side, net-Sharpe at tiers, turnover, and WHERE the signal
lives (gross Sharpe by tercile). Reversal = fast turnover × small coins = the cost trap to expose.
Usage: PYTHONPATH=. python multi_asset/data/wide_lsgate.py
"""
from __future__ import annotations
import json, os.path as p
import numpy as np, pandas as pd

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
PANEL = E + "/wide_panel.npz"
HOUR_MS = 3_600_000
ANN = np.sqrt(24 * 365)                     # hourly -> annual Sharpe
TIER_BPS = np.array([2.0, 5.0, 10.0])       # top / mid / bottom DVOL tercile cost per side


def _sh(x):
    x = x[np.isfinite(x)]
    return float(x.mean() / (x.std() + 1e-12) * ANN) if len(x) > 10 and x.std() > 0 else np.nan


def ls_series(factor, sign, Y, MEM, DV):
    """Hourly z-weighted dollar-neutral L/S. Returns gross_ret, turnover, per-coin-cost net_ret, tercile grosses."""
    T, N = Y.shape
    W = np.zeros((T, N)); tier = np.zeros((T, N), np.int8)
    for t in range(T):
        v = MEM[t] & np.isfinite(factor[t]) & np.isfinite(Y[t])
        if v.sum() < 8:
            continue
        f = sign * factor[t, v]
        z = (f - f.mean()) / (f.std() + 1e-12)
        z = z - z.mean()
        s = np.abs(z).sum()
        if s > 0:
            W[t, np.where(v)[0]] = z / s          # gross 1, net 0
        # liquidity terciles by DVOL30 among active
        dv = DV[t, v]
        q = np.argsort(np.argsort(-dv))            # 0=most liquid
        nv = v.sum()
        tt = np.where(q < nv / 3, 0, np.where(q < 2 * nv / 3, 1, 2))
        tier[t, np.where(v)[0]] = tt
    gross = np.nansum(W * np.nan_to_num(Y), axis=1)
    if np.nanmean(gross) < 0:                 # orient to the PROFITABLE direction (turnover is sign-agnostic)
        W = -W; gross = -gross
    dW = np.abs(np.diff(W, axis=0, prepend=0.0))
    turn = dW.sum(axis=1)
    cost_bps = TIER_BPS[tier] / 1e4
    net = gross - (dW * cost_bps).sum(axis=1)
    # gross Sharpe by tercile membership (signal location): L/S restricted to each tercile
    tgross = []
    for tt in range(3):
        Wt = np.where(tier == tt, W, 0.0)
        # renormalize per row
        s = np.abs(Wt).sum(1, keepdims=True)
        Wt = np.where(s > 0, Wt / s, 0.0)
        tgross.append(_sh(np.nansum(Wt * np.nan_to_num(Y), axis=1)))
    be = float(np.nanmean(gross) / (np.nanmean(turn) + 1e-12) * 1e4) if np.nanmean(turn) > 0 else np.nan
    return dict(gross_sharpe=round(_sh(gross), 2), net_sharpe=round(_sh(net), 2),
                turnover=round(float(np.nanmean(turn)), 3), be_bps_side=round(be, 2),
                tercile_gross_sharpe=[round(x, 2) if np.isfinite(x) else None for x in tgross])


def main():
    z = np.load(PANEL, allow_pickle=True)
    Y = z["Y"].astype(np.float64); MEM = z["MEMBER"]; DV = z["DVOL30"].astype(np.float64)
    C = z["CLOSE"].astype(np.float64); H = z["HIGH"].astype(np.float64); V = z["VOL"].astype(np.float64)
    logc = np.log(np.where(C > 0, C, np.nan))

    def shift(A, n):
        o = np.full_like(A, np.nan); o[n:] = A[:-n] if n < len(A) else o[n:]; return o
    def roll(A, w, fn):
        return getattr(pd.DataFrame(A).rolling(w, min_periods=max(3, w // 2)), fn)().values

    # cluster representatives from the scorecard (strongest per cluster + a slow one)
    F = {
        "rev_1h": (-(logc - shift(logc, 1)), +1),                 # reversal (fast)
        "mom_168h_rev": (logc - shift(logc, 168), +1),            # slow reversal (168h, low turnover)
        "gtja_046": ((roll(C, 3, "mean") + roll(C, 6, "mean") + roll(C, 12, "mean") + roll(C, 24, "mean")) / (4 * C), +1),
        "max_ret_24h": (roll(logc - shift(logc, 1), 24, "max"), -1),
        "rvol_24h": (roll(logc - shift(logc, 1), 24, "std"), -1),   # low-vol (slow)
        "size_dvol": (-np.log(np.where(DV > 0, DV, np.nan)), +1),   # size (very slow)
    }
    out = {}
    for nm, (f, sgn) in F.items():
        out[nm] = ls_series(np.asarray(f, np.float64), sgn, Y, MEM, DV)
        r = out[nm]
        print(f"{nm:14s} gross_Sh={r['gross_sharpe']:>5} net_Sh={r['net_sharpe']:>6} "
              f"BE={r['be_bps_side']:>6}bps/side turn={r['turnover']:>5} "
              f"tercile_gross(liq/mid/illiq)={r['tercile_gross_sharpe']}", flush=True)
    json.dump(out, open(p.join(E, "eda/wide_lsgate.json"), "w"), indent=2)
    print(f"\n-> {E}/eda/wide_lsgate.json  (cost tiers: top/mid/bottom DVOL tercile = {TIER_BPS} bps/side)")


if __name__ == "__main__":
    main()

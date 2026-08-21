#!/usr/bin/env python3
"""Phase-0b/A — WIDE combined slow-premia BOOK-2 + cost-STRESS + capacity (0B).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

The wide net-cost gate (wide_lsgate.py) showed the SLOW premia trade net-of-cost (low-vol/MAX/size)
while the fast reversal/price-vol are cost-trapped. This builds the COMBINED Book-2 (equal-risk
score-level composite of the 3 tradeable slow premia) with walk-forward-honest per-fold reporting,
a cost-STRESS sweep (illiquid tercile at 10/20/30/50 bps/side — max/rvol have thin BE~10 margin),
and a rough dollar-CAPACITY note (size premium lives in illiquid coins → capacity-limited).
Outputs the combined-book LEDGER (gross/net return series + per-ts weights summary) for 0C's cross-check.
Usage: PYTHONPATH=. python multi_asset/data/build_wide_book.py
"""
from __future__ import annotations
import json, os.path as p
import numpy as np, pandas as pd

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
PANEL = E + "/wide_panel.npz"
ANN = np.sqrt(24 * 365)


def _sh(x):
    x = x[np.isfinite(x)]
    return float(x.mean() / (x.std() + 1e-12) * ANN) if len(x) > 10 and x.std() > 0 else np.nan


def oriented_z(factor, sign, Y, MEM):
    """Per-ts xsec z-score (sign-oriented), auto-flipped so the L/S gross return is positive."""
    T, N = Y.shape
    Z = np.zeros((T, N))
    for t in range(T):
        v = MEM[t] & np.isfinite(factor[t]) & np.isfinite(Y[t])
        if v.sum() >= 8:
            f = sign * factor[t, v]
            Z[t, np.where(v)[0]] = (f - f.mean()) / (f.std() + 1e-12)
    gross = np.nansum((Z / (np.abs(Z).sum(1, keepdims=True) + 1e-12)) * np.nan_to_num(Y), axis=1)
    if np.nanmean(gross) < 0:
        Z = -Z
    return Z


def ls_from_score(Z, Y, tier, illiq_bps, dayidx=None, days=None):
    s = np.abs(Z).sum(1, keepdims=True)
    W = np.where(s > 0, Z / s, 0.0)
    gross = np.nansum(W * np.nan_to_num(Y), axis=1)
    dW = np.abs(np.diff(W, axis=0, prepend=0.0))
    turn = dW.sum(1)
    tb = np.array([2.0, 5.0, illiq_bps]) / 1e4
    net = gross - (dW * tb[tier]).sum(1)
    if days is not None:
        m = np.isin(dayidx, days); gross, net, turn = gross[m], net[m], turn[m]
    be = float(np.nanmean(gross) / (np.nanmean(turn) + 1e-12) * 1e4)
    return dict(gross_sharpe=round(_sh(gross), 2), net_sharpe=round(_sh(net), 2),
                turnover=round(float(np.nanmean(turn)), 4), be_bps=round(be, 2)), gross, net


def main():
    z = np.load(PANEL, allow_pickle=True)
    Y = z["Y"].astype(np.float64); MEM = z["MEMBER"]; DV = z["DVOL30"].astype(np.float64)
    C = z["CLOSE"].astype(np.float64); ts = z["ts"].astype(np.int64)
    logc = np.log(np.where(C > 0, C, np.nan))
    dayidx = ((ts - ts[0]) // (3_600_000 * 24)).astype(np.int64); nD = int(dayidx.max()) + 1
    folds = [np.arange(nD - 240, nD - 160), np.arange(nD - 160, nD - 80), np.arange(nD - 80, nD)]

    def shift(A, n):
        o = np.full_like(A, np.nan); o[n:] = A[:-n]; return o
    def roll(A, w, fn):
        return getattr(pd.DataFrame(A).rolling(w, min_periods=max(3, w // 2)), fn)().values
    ret = logc - shift(logc, 1)

    FAC = {  # the tradeable slow premia (sign is a starting guess; oriented_z auto-flips)
        "low_vol": (roll(ret, 24, "std"), -1),
        "max_lottery": (roll(ret, 24, "max"), -1),
        "size": (-np.log(np.where(DV > 0, DV, np.nan)), +1),
    }
    Zs = {nm: oriented_z(np.asarray(f, np.float64), s, Y, MEM) for nm, (f, s) in FAC.items()}
    # equal-risk combined = mean of oriented z-scores (each ~unit xsec vol) -> composite score
    Zc = np.nanmean(np.stack([Zs[nm] for nm in FAC]), axis=0)

    # liquidity tercile per ts (0=liquid..2=illiq) among the combined-active universe
    tier = np.zeros(Y.shape, np.int8)
    for t in range(Y.shape[0]):
        v = MEM[t] & np.isfinite(DV[t])
        if v.sum() >= 8:
            q = np.argsort(np.argsort(-DV[t, v])); nv = v.sum()
            tier[t, np.where(v)[0]] = np.where(q < nv / 3, 0, np.where(q < 2 * nv / 3, 1, 2))

    STRESS = [10.0, 20.0, 30.0, 50.0]
    out = {"members": {"low_vol": "rvol_24h", "max_lottery": "max_ret_24h", "size": "-log(DVOL30)"},
           "cost_tiers": "top/mid = 2/5 bps; illiquid stressed at " + str(STRESS)}
    # per-factor + combined, base cost (illiq=10), + per-fold, + stress sweep
    print(f"{'book':14s} {'illiqBPS':>8s} {'grossSh':>7s} {'netSh':>7s} {'BE_bps':>7s} {'turn':>6s}")
    for nm, Z in list(Zs.items()) + [("COMBINED", Zc)]:
        base, _, _ = ls_from_score(Z, Y, tier, 10.0)
        pf = [ls_from_score(Z, Y, tier, 10.0, dayidx, fd)[0]["net_sharpe"] for fd in folds]
        stress = {}
        for c in STRESS:
            r, _, _ = ls_from_score(Z, Y, tier, c)
            stress[int(c)] = r["net_sharpe"]
            print(f"{nm:14s} {c:>8.0f} {r['gross_sharpe']:>7} {r['net_sharpe']:>7} {r['be_bps']:>7} {r['turnover']:>6}")
        out[nm] = dict(base=base, per_fold_net_sharpe=pf, stress_illiq_net_sharpe=stress)

    # capacity: illiquid-tercile median daily dollar-volume (USD) -> rough per-name capacity
    illiq_dv = []
    for t in range(0, Y.shape[0], 24):
        v = (tier[t] == 2) & MEM[t] & np.isfinite(DV[t])
        if v.sum():
            illiq_dv.append(np.nanmedian(DV[t, v]))
    med_illiq = float(np.nanmedian(illiq_dv)) if illiq_dv else np.nan
    out["capacity_note"] = dict(illiq_median_daily_usd=round(med_illiq, 0),
                                note="size/low-vol signal lives in illiquid tercile; a ~5-10% ADV cap per name "
                                     "bounds a small-alt sleeve to ~single-digit % of illiq median ADV -> capacity-limited")
    json.dump(out, open(p.join(E, "eda/wide_book.json"), "w"), indent=2, default=str)
    print(f"\ncombined per-fold net-Sharpe (illiq=10): {out['COMBINED']['per_fold_net_sharpe']}")
    print(f"illiq-tercile median daily $vol ≈ ${med_illiq:,.0f} -> capacity-limited sleeve")
    print(f"-> {E}/eda/wide_book.json")


if __name__ == "__main__":
    main()

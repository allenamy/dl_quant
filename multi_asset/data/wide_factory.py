#!/usr/bin/env python3
"""Phase-0b/A — WIDE-universe factor scorecard (does the factor suite REVIVE at N=60+?).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

On the wide hourly panel (build_wide_panel.py), compute the factor suite and screen each over the
POINT-IN-TIME active universe (MEMBER mask) at the 1h horizon: standalone xsec rank-IC (per-ts
spearman over active assets vs xsec-demeaned Y) + empirical-null z (permute Y across ts; the
null-mean bias shrinks with N) + per-fold sign across 3 walk-forward OOS day-blocks.

Factors: funding_ema (the proven lever); the SLOW-PRICE family that died on 14 mega-caps but the
literature says lives in wider/smaller-coin universes (momentum/reversal/vol/dvol/beta/turnover/
illiquidity/MAX-lottery/size); + the alpha-sweep survivors a101_044, gtja_046 (hourly-grid form).
All CAUSAL <=t. Writes wide_factory.json + hands 0C wide preds (score sign-oriented) per factor.
Usage: PYTHONPATH=. python multi_asset/data/wide_factory.py [--nperm 20]
"""
from __future__ import annotations
import argparse, json, os.path as p
import numpy as np, pandas as pd
from scipy.stats import rankdata

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
PANEL = E + "/wide_panel.npz"
HOUR_MS = 3_600_000


def _shift(A, n):
    out = np.full_like(A, np.nan)
    if n < len(A):
        out[n:] = A[:-n]
    return out


def _roll(A, w, fn):
    return getattr(pd.DataFrame(A).rolling(w, min_periods=max(3, w // 2)), fn)().values


def build_factors(z):
    C = z["CLOSE"].astype(np.float64); H = z["HIGH"].astype(np.float64); L = z["LOW"].astype(np.float64)
    V = z["VOL"].astype(np.float64); QV = z["QVOL"].astype(np.float64); FE = z["FUND_EMA"].astype(np.float64)
    DV = z["DVOL30"].astype(np.float64)
    logc = np.log(np.where(C > 0, C, np.nan))
    ret = logc - _shift(logc, 1)
    btc = np.nanmean(ret, axis=1)                            # equal-weight market return (syms are glob-sorted, not BTC-first)
    F = {}
    # funding (crowding-reversion: negative IC expected -> long low funding)
    F["funding_ema"] = (FE, -1)
    # momentum / reversal (hours)
    for n in (4, 8, 24, 72, 168):
        F[f"mom_{n}h"] = (logc - _shift(logc, n), +1)
    F["rev_1h"] = (-(logc - _shift(logc, 1)), +1)
    F["rev_3h"] = (-(logc - _shift(logc, 3)), +1)
    # realized vol / downside semivol (low-vol premium -> negative IC)
    for n in (24, 72):
        F[f"rvol_{n}h"] = (_roll(ret, n, "std"), -1)
        F[f"dvol_{n}h"] = (_roll(np.minimum(ret, 0.0), n, "std"), -1)
    # beta vs market (BAB -> negative IC)
    bser = pd.Series(btc)
    for n in (24, 72):
        var_b = bser.rolling(n, min_periods=n // 2).var().values
        cov = np.column_stack([pd.Series(ret[:, si]).rolling(n, min_periods=n // 2).cov(bser).values
                               for si in range(ret.shape[1])])
        F[f"beta_{n}h"] = (cov / np.where(np.abs(var_b[:, None]) > 1e-18, var_b[:, None], np.nan), -1)
    # turnover / illiquidity / size
    F["lturnover_24h"] = (np.log(np.where(_roll(QV, 24, "mean") > 0, _roll(QV, 24, "mean"), np.nan)), -1)
    amihud = _roll(np.abs(ret) / np.where(QV > 0, QV, np.nan), 72, "mean")
    F["illiq_72h"] = (amihud, +1)                            # high illiquidity premium
    F["size_dvol"] = (-np.log(np.where(DV > 0, DV, np.nan)), +1)   # small-size premium
    # MAX / lottery (high max return -> negative future = lottery discount)
    F["max_ret_24h"] = (_roll(ret, 24, "max"), -1)
    # alpha-sweep survivors (hourly form)
    F["gtja_046"] = ((_roll(C, 3, "mean") + _roll(C, 6, "mean") + _roll(C, 12, "mean") + _roll(C, 24, "mean")) / (4 * C), +1)
    rk_v = pd.DataFrame(V).rank(axis=1, pct=True).values
    corr_hv = np.column_stack([pd.Series(H[:, si]).rolling(5, min_periods=3).corr(pd.Series(rk_v[:, si])).values
                               for si in range(H.shape[1])])
    F["a101_044"] = (-corr_hv, +1)
    return F


def _ic_days(Xf, Yr, MEM, dayidx, days, sign):
    ics = []
    m = np.isin(dayidx, days)
    for i in np.where(m)[0]:
        v = MEM[i] & np.isfinite(Xf[i]) & np.isfinite(Yr[i])
        if v.sum() >= 8:
            ic = np.corrcoef(rankdata(sign * Xf[i, v]), rankdata(Yr[i, v]))[0, 1]
            if np.isfinite(ic):
                ics.append(ic)
    return float(np.mean(ics)) if ics else np.nan


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--nperm", type=int, default=20); a = ap.parse_args()
    z = np.load(PANEL, allow_pickle=True)
    ts = z["ts"].astype(np.int64); Y = z["Y"].astype(np.float64); MEM = z["MEMBER"]
    dayidx = ((ts - ts[0]) // (HOUR_MS * 24)).astype(np.int64)
    nD = int(dayidx.max()) + 1
    # 3 walk-forward OOS day-blocks in the later window (embargo 2d before each)
    folds = [(nD - 240, nD - 160), (nD - 160, nD - 80), (nD - 80, nD)]
    fold_days = [np.arange(a0, a1) for a0, a1 in folds]
    all_days = np.concatenate(fold_days)
    # xsec-demeaned Y on active universe per ts
    Yr = np.full_like(Y, np.nan)
    for i in range(len(ts)):
        v = MEM[i] & np.isfinite(Y[i])
        if v.sum() >= 8:
            Yr[i, v] = Y[i, v] - Y[i, v].mean()

    F = build_factors(z)
    rng = np.random.default_rng(0)
    rows = []
    for nm, (Xf, sign) in F.items():
        Xf = np.asarray(Xf, dtype=np.float64)
        ic = _ic_days(Xf, Yr, MEM, dayidx, all_days, sign)
        pf = [_ic_days(Xf, Yr, MEM, dayidx, fd, sign) for fd in fold_days]
        null = []
        for _ in range(a.nperm):
            Yp = Yr[rng.permutation(len(Yr))]
            null.append(_ic_days(Xf, Yp, MEM, dayidx, all_days, sign))
        null = np.array([x for x in null if np.isfinite(x)])
        mu, sd = (float(null.mean()), float(null.std())) if len(null) else (np.nan, np.nan)
        zt = (ic - mu) / (sd + 1e-9) if np.isfinite(ic) else np.nan
        signs = set(int(np.sign(x)) for x in pf if np.isfinite(x) and x != 0)
        rows.append(dict(name=nm, sign=sign, ic=round(ic, 4) if np.isfinite(ic) else None,
                         z=round(zt, 2) if np.isfinite(zt) else None,
                         perfold=[round(x, 4) if np.isfinite(x) else None for x in pf],
                         sign_consistent=(len(signs) == 1),
                         revive=bool(np.isfinite(zt) and abs(zt) >= 2.5 and len(signs) == 1)))
    rows.sort(key=lambda r: (-abs(r["z"]) if r["z"] is not None else 0))
    out = dict(analysis="wide_factory_h3600", n_symbols=int(MEM.any(0).sum()),
               member_per_ts=round(float(MEM.sum(1).mean()), 1), n_days=nD,
               n_factors=len(F), n_revive=sum(r["revive"] for r in rows), table=rows)
    json.dump(out, open(p.join(E, "eda/wide_factory.json"), "w"), indent=2)
    print(f"[wide-factory] {len(F)} factors, {out['n_revive']} REVIVE (|z|>=2.5 & sign-consistent), "
          f"universe {out['n_symbols']} coins ({out['member_per_ts']}/ts)\n")
    print(f"{'factor':14s} {'sign':>4s} {'IC':>8s} {'z':>7s}  {'perfold(f0/f1/f2)':>24s}  revive")
    for r in rows:
        pf = "/".join(f"{x:+.3f}" if x is not None else " None" for x in r["perfold"])
        ics = f"{r['ic']:+.4f}" if r["ic"] is not None else "  NaN"
        zs = f"{r['z']:+.2f}" if r["z"] is not None else "  NaN"
        print(f"{r['name']:14s} {r['sign']:>+4d} {ics:>8s} {zs:>7s}  {pf:>24s}  {'★' if r['revive'] else ''}")
    print(f"\n-> {E}/eda/wide_factory.json")


if __name__ == "__main__":
    main()

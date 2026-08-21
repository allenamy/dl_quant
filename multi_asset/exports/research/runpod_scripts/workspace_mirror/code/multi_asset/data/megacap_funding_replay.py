#!/usr/bin/env python3
"""Phase hardening — PER-YEAR funding_ema replay on 14 mega-caps, full history (2020→2026).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 hardening (0B) | **状态:** in-progress

Attacks the #1 limit (short OOS) on the primary factor. Builds funding_ema (24h EMA, xsec-z per ts,
causal ffill≤t) on the 14-mega-cap full-history hourly panel, then a WALK-FORWARD per-YEAR replay:
xsec rank-IC + empirical-null z + net-cost L/S (1h & 2h rebalance) each calendar year. Does the
crowding-reversion premium hold across 2020 bull / 2021 mania / 2022 crash / 2023 chop / 2024-25 /
2026? funding_ema sign is −1 (long low / short high funding). Mega-caps → flat 2 bps/side maker cost.
Output: exports/eda/megacap_funding_replay.json + printed per-year table.
"""
from __future__ import annotations
import glob, json, os.path as p
import numpy as np, pandas as pd
from scipy.stats import rankdata

WIDE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/megacap_hist"
E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
HOUR_MS = 3_600_000
ANN = np.sqrt(24 * 365)
COST = 2.0 / 1e4          # mega-cap maker ~2 bps/side


def build_panel():
    kf = sorted(glob.glob(p.join(WIDE, "*_klines_1h.csv")))
    syms = [p.basename(f)[:-len("_klines_1h.csv")] for f in kf]
    kl = {s: pd.read_csv(f) for s, f in zip(syms, kf)}
    allt = np.unique(np.concatenate([kl[s]["openTime_ms"].values.astype(np.int64) for s in syms]))
    grid = np.sort(allt[(allt % HOUR_MS) == 0]); gidx = {int(t): i for i, t in enumerate(grid)}
    T, N = len(grid), len(syms)
    CLOSE = np.full((T, N), np.nan); FUND = np.full((T, N), np.nan)
    for si, s in enumerate(syms):
        df = kl[s]; ts = df["openTime_ms"].values.astype(np.int64)
        rows = np.array([gidx[int(t)] for t in ts if int(t) in gidx])
        keep = np.array([int(t) in gidx for t in ts])
        CLOSE[rows, si] = df["close"].values[keep]
        ff = p.join(WIDE, f"{s}_funding.csv")
        if p.exists(ff):
            fd = pd.read_csv(ff).sort_values("fundingTime_ms")
            ih = float(np.median(fd["funding_interval_h"].values)) if len(fd) else 8.0
            span = max(2, int(round(24.0 / max(ih, 1.0))))
            ema = pd.Series(pd.to_numeric(fd["fundingRate"], errors="coerce").values).ewm(span=span, adjust=False).mean().values
            fts = fd["fundingTime_ms"].values.astype(np.int64)
            idx = np.searchsorted(fts, grid, side="right") - 1
            ok = idx >= 0; FUND[ok, si] = ema[idx[ok]]
    return grid, syms, CLOSE, FUND


def yr_stats(grid, CLOSE, FUND, hbars):
    """Per-year xsec rank-IC (+null-z) + net-cost L/S for horizon = hbars hours (rebalanced hbars)."""
    logc = np.log(np.where(CLOSE > 0, CLOSE, np.nan))
    Y = np.full_like(logc, np.nan)
    Y[:-hbars] = logc[hbars:] - logc[:-hbars]
    gap = np.zeros(len(grid), bool); gap[:-hbars] = (grid[hbars:] - grid[:-hbars]) > (hbars + 1) * HOUR_MS
    Y[gap] = np.nan
    yr = pd.to_datetime(grid, unit="ms", utc=True).year
    out = {}
    rng = np.random.default_rng(0)
    for y in np.unique(yr):
        rows = np.where((yr == y))[0][::hbars]                       # non-overlap at the horizon
        ics = []; ws_ret = []; ws_turn = []; prevW = None
        Yr = {}
        for i in rows:
            v = np.isfinite(FUND[i]) & np.isfinite(Y[i])
            if v.sum() < 5:
                continue
            f = -FUND[i, v]                                          # sign −1: long low funding
            yv = Y[i, v] - Y[i, v].mean()
            ic = np.corrcoef(rankdata(f), rankdata(yv))[0, 1]
            if np.isfinite(ic):
                ics.append(ic)
            z = (f - f.mean()) / (f.std() + 1e-12); z -= z.mean()
            W = np.zeros(FUND.shape[1]); s = np.abs(z).sum()
            if s > 0:
                W[np.where(v)[0]] = z / s
            ws_ret.append(np.nansum(W * np.nan_to_num(Y[i])))
            ws_turn.append(np.abs(W - (prevW if prevW is not None else 0)).sum()); prevW = W
        if len(ics) < 20:
            continue
        ic = np.array(ics); gross = np.array(ws_ret); turn = np.array(ws_turn)
        net = gross - COST * turn
        # empirical null: shuffle Y rows within the year
        null = []
        for _ in range(15):
            perm = rng.permutation(len(rows))
            nic = []
            for j, i in enumerate(rows):
                v = np.isfinite(FUND[i]) & np.isfinite(Y[rows[perm[j]]])
                if v.sum() >= 5:
                    f = -FUND[i, v]; yv = Y[rows[perm[j]], v]
                    vv = np.isfinite(yv)
                    if vv.sum() >= 5:
                        c = np.corrcoef(rankdata(f[vv]), rankdata(yv[vv] - yv[vv].mean()))[0, 1]
                        if np.isfinite(c):
                            nic.append(c)
            if nic:
                null.append(np.mean(nic))
        null = np.array(null); zt = (ic.mean() - null.mean()) / (null.std() + 1e-9) if len(null) else np.nan
        sh = lambda a: float(a.mean() / (a.std() + 1e-12) * (ANN / np.sqrt(hbars))) if a.std() > 0 else np.nan
        out[int(y)] = dict(n_ts=len(ic), ic=round(float(ic.mean()), 4), z=round(float(zt), 2),
                           gross_sh=round(sh(gross), 2), net_sh=round(sh(net), 2),
                           be_bps=round(float(gross.mean() / (turn.mean() + 1e-12) * 1e4), 2),
                           turnover=round(float(turn.mean()), 3))
    return out


def main():
    grid, syms, CLOSE, FUND = build_panel()
    print(f"[replay] {len(syms)} mega-caps, T={len(grid)} hrs, "
          f"{pd.to_datetime(grid[0],unit='ms').date()}→{pd.to_datetime(grid[-1],unit='ms').date()}, "
          f"funding cov={np.isfinite(FUND).mean():.3f}", flush=True)
    res = {"1h": yr_stats(grid, CLOSE, FUND, 1), "2h": yr_stats(grid, CLOSE, FUND, 2)}
    json.dump(res, open(p.join(E, "eda/megacap_funding_replay.json"), "w"), indent=2)
    for hz in ("1h", "2h"):
        print(f"\n=== funding_ema per-YEAR replay [{hz}] (sign −1 crowding-reversion, cost 2bps/side) ===")
        print(f"{'year':6s} {'n_ts':>6s} {'IC':>8s} {'z':>7s} {'grossSh':>8s} {'netSh':>7s} {'BE_bps':>7s} {'turn':>6s}")
        for y, r in res[hz].items():
            print(f"{y:6d} {r['n_ts']:>6d} {r['ic']:>+8.4f} {r['z']:>+7.2f} {r['gross_sh']:>8.2f} "
                  f"{r['net_sh']:>+7.2f} {r['be_bps']:>7.2f} {r['turnover']:>6.3f}")
    print(f"\n-> {E}/eda/megacap_funding_replay.json", flush=True)


if __name__ == "__main__":
    main()

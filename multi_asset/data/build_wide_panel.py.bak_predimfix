#!/usr/bin/env python3
"""Phase-0b/A — WIDE hourly panel (OHLCV+vwap+funding_ema+point-in-time top-N membership).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

The wide universe is the real factor-mining ground (N=14 was the structural constraint that killed
the literature's small-coin factors). From data/wide/{SYM}_klines_1h.csv + {SYM}_funding.csv:
  - common hourly grid (union of all listed symbols' openTimes);
  - OPEN/HIGH/LOW/CLOSE/VOL/QVOL (T,N) aligned by exact openTime (NaN where not listed → causal,
    listing-aware, NO survivorship);
  - VWAP = QVOL/VOL; FUND_EMA = 24h-equiv EMA of funding, causal-ffilled to the hourly grid;
  - Y = next-hour logret (decision at close[t], hold hour t+1 — causal 1h-forward target);
  - MEMBER (T,N) bool = point-in-time top-TOPN by trailing-30d dollar-volume, MONTHLY refresh;
  - DVOL30 (T,N) trailing dollar-vol (for liquidity terciles in the net-cost gate).

Output: exports/wide_panel.npz. Usage: python multi_asset/data/build_wide_panel.py [topN=60]
"""
from __future__ import annotations
import glob, os.path as p, sys
import numpy as np, pandas as pd

WIDE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/wide"
OUT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_panel.npz"
HOUR_MS = 3_600_000


def build(topN=60, out=OUT):
    kfiles = sorted(glob.glob(p.join(WIDE, "*_klines_1h.csv")))
    syms = [p.basename(f)[:-len("_klines_1h.csv")] for f in kfiles]
    # load klines
    kl = {}
    for s, f in zip(syms, kfiles):
        try:
            df = pd.read_csv(f)
            if len(df) > 100:
                kl[s] = df
        except Exception:
            pass
    syms = [s for s in syms if s in kl]
    # common hourly grid
    allt = np.unique(np.concatenate([kl[s]["openTime_ms"].values.astype(np.int64) for s in syms]))
    allt = allt[(allt % HOUR_MS) == 0]
    grid = np.sort(allt)
    gidx = {int(t): i for i, t in enumerate(grid)}
    T, N = len(grid), len(syms)
    OPEN = np.full((T, N), np.nan); HIGH = np.full((T, N), np.nan); LOW = np.full((T, N), np.nan)
    CLOSE = np.full((T, N), np.nan); VOL = np.full((T, N), np.nan); QVOL = np.full((T, N), np.nan)
    for si, s in enumerate(syms):
        df = kl[s]; ts = df["openTime_ms"].values.astype(np.int64)
        rows = np.array([gidx[int(t)] for t in ts if int(t) in gidx])
        keep = np.array([int(t) in gidx for t in ts])
        OPEN[rows, si] = df["open"].values[keep]; HIGH[rows, si] = df["high"].values[keep]
        LOW[rows, si] = df["low"].values[keep]; CLOSE[rows, si] = df["close"].values[keep]
        VOL[rows, si] = df["volume"].values[keep]; QVOL[rows, si] = df["quote_volume"].values[keep]
    VWAP = np.where(VOL > 0, QVOL / np.where(VOL > 0, VOL, np.nan), np.nan)

    # funding_ema (24h-equiv EMA per coin, causal ffill to hourly grid)
    FUND = np.full((T, N), np.nan)
    for si, s in enumerate(syms):
        ff = p.join(WIDE, f"{s}_funding.csv")
        if not p.exists(ff):
            continue
        fd = pd.read_csv(ff)
        if len(fd) < 3:
            continue
        fd = fd.sort_values("fundingTime_ms")
        ih = float(np.median(fd["funding_interval_h"].values)) if "funding_interval_h" in fd else 8.0
        span = max(2, int(round(24.0 / max(ih, 1.0))))     # 24h-equivalent EMA
        rate = pd.to_numeric(fd["fundingRate"], errors="coerce").values.astype(np.float64)
        ema = pd.Series(rate).ewm(span=span, adjust=False).mean().values
        fts = fd["fundingTime_ms"].values.astype(np.int64)                # funding stamps in ms (== grid units)
        idx = np.searchsorted(fts, grid, side="right") - 1                # causal ffill: last funding <= t
        ok = idx >= 0
        FUND[ok, si] = ema[idx[ok]]

    # next-hour forward logret target (causal; mask cross-listing-gap)
    logc = np.log(np.where(CLOSE > 0, CLOSE, np.nan))
    Y = np.full((T, N), np.nan)
    Y[:-1] = logc[1:] - logc[:-1]
    gap = np.zeros(T, bool); gap[:-1] = (grid[1:] - grid[:-1]) > HOUR_MS      # non-consecutive hour
    Y[gap] = np.nan

    # trailing-30d dollar-volume + monthly point-in-time top-N membership
    dvol = pd.DataFrame(QVOL).rolling(24 * 30, min_periods=24 * 5).mean().values   # (T,N)
    MEMBER = np.zeros((T, N), bool)
    months = (grid // (HOUR_MS * 24)).astype(np.int64)            # day-index; refresh at month via calendar
    cal = pd.to_datetime(grid, unit="ms", utc=True)
    ym = cal.year * 100 + cal.month
    for m in np.unique(ym):
        rr = np.where(ym == m)[0]
        r0 = rr[0]
        dv = dvol[r0].copy()                                     # rank at month start (as-of)
        dv[~np.isfinite(dv)] = -1
        elig = np.isfinite(CLOSE[r0]) & (dv > 0)
        order = np.argsort(-dv)
        top = [j for j in order if elig[j]][:topN]
        if top:
            MEMBER[np.ix_(rr, top)] = True
    MEMBER &= np.isfinite(CLOSE)                                  # only when actually listed

    with open(out, "wb") as f:
        np.savez(f, ts=grid, symbols=np.array(syms, dtype=object),
                 OPEN=OPEN.astype(np.float32), HIGH=HIGH.astype(np.float32), LOW=LOW.astype(np.float32),
                 CLOSE=CLOSE.astype(np.float32), VOL=VOL.astype(np.float32), QVOL=QVOL.astype(np.float32),
                 VWAP=VWAP.astype(np.float32), FUND_EMA=FUND.astype(np.float32), Y=Y.astype(np.float32),
                 MEMBER=MEMBER, DVOL30=dvol.astype(np.float32))
    covd = (grid[-1] - grid[0]) / (HOUR_MS * 24)
    print(f"[wide] T={T} hours ({covd:.0f}d) N={N} symbols with klines", flush=True)
    print(f"  funding coverage={np.isfinite(FUND).mean():.3f}  Y coverage={np.isfinite(Y).mean():.3f}", flush=True)
    print(f"  member/ts avg={MEMBER.sum(1).mean():.1f} (target {topN})  active symbols total={ (MEMBER.any(0)).sum()}", flush=True)
    print(f"  -> {out}", flush=True)


if __name__ == "__main__":
    build(int(sys.argv[1]) if len(sys.argv) > 1 else 60,
          out=sys.argv[2] if len(sys.argv) > 2 else OUT)

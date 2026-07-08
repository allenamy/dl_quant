#!/usr/bin/env python3
"""Phase-0b/A — OHLCV+vwap 180s panel for the Alpha-101 / GTJA-191 formula sweep.

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

Aggregates the 1s bars into 180s buckets (same gap-safe bucket assignment as build_orderflow_panel:
each 1s bar → first grid ts ≥ its ts, guarded to ≤180s so nothing leaks across an overnight gap):
  open  = close of the previous bucket (open_t ≈ close_{t−1}; robust, no first-in-bucket scatter)
  high  = max 1s high in the bucket        low = min 1s low
  close = last 1s close (≈ mid at grid ts)  volume = Σ(tdQtyBuy+tdQtySell) (taker)
  vwap  = Σ(tdQtyPxBuy+tdQtyPxSell)/volume  signed = Σ(tdQtyBuy−tdQtySell) (net taker)
All CAUSAL (bucket for grid ts G = trades in (G−180s, G], ≤t). Empty buckets → NaN via per-bucket count.

Output: exports/ohlcv_panel.npz {ts, day, OPEN, HIGH, LOW, CLOSE, VOL, VWAP, SF} each (nT,nS) f32.
Usage: PYTHONPATH=. python multi_asset/data/build_ohlcv_panel.py
"""
from __future__ import annotations
import os.path as p, sys, time
import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.bar_loader import load_day_panel  # noqa: E402
from multi_asset.data.build_multihorizon_targets import SYMBOLS, list_days, WIN_START, WIN_END  # noqa: E402

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
MIDCACHE = ROOT + "/mid_panel.npz"
OUT = ROOT + "/ohlcv_panel.npz"
NS = 1_000_000_000
STRIDE = 180


def build():
    z = np.load(MIDCACHE, allow_pickle=True)
    grid = z["ts"].astype(np.int64); day = z["day"].astype(np.int64)
    CLOSE = z["MID"].astype(np.float64).copy()          # last-bar close ≈ mid at grid ts (already sampled)
    nT, nS = len(grid), len(SYMBOLS)
    HIGH = np.full((nT, nS), -np.inf); LOW = np.full((nT, nS), np.inf)
    VOL = np.zeros((nT, nS)); SF = np.zeros((nT, nS)); QP = np.zeros((nT, nS))
    CNT = np.zeros((nT, nS), np.int64)
    days = list_days(WIN_START, WIN_END); t0 = time.time()
    for di, d in enumerate(days):
        try:
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            print(f"  [warn] {d}: {e}", flush=True); continue
        dts = dp.ts.astype(np.int64)
        c = {k: dp.cols.index(k) for k in ("high", "low", "tdQtyBuy", "tdQtySell", "tdQtyPxBuy", "tdQtyPxSell")}
        bidx = np.searchsorted(grid, dts, side="left"); inr = bidx < nT
        gg = np.zeros(len(dts), bool); gg[inr] = (grid[bidx[inr]] - dts[inr]) <= STRIDE * NS
        for si, s in enumerate(SYMBOLS):
            arr = dp.data[s]
            hi = arr[:, c["high"]]; lo = arr[:, c["low"]]
            qb = arr[:, c["tdQtyBuy"]]; qs = arr[:, c["tdQtySell"]]
            qp = arr[:, c["tdQtyPxBuy"]] + arr[:, c["tdQtyPxSell"]]
            m = gg & np.isfinite(hi) & np.isfinite(lo)
            b = bidx[m]
            np.maximum.at(HIGH[:, si], b, hi[m])
            np.minimum.at(LOW[:, si], b, lo[m])
            mv = gg & np.isfinite(qb) & np.isfinite(qs)
            bv = bidx[mv]
            np.add.at(VOL[:, si], bv, (qb + qs)[mv])
            np.add.at(SF[:, si], bv, (qb - qs)[mv])
            np.add.at(QP[:, si], bv, np.where(np.isfinite(qp[mv]), qp[mv], 0.0))
            np.add.at(CNT[:, si], bv, 1)
        if (di + 1) % 50 == 0 or di == len(days) - 1:
            print(f"  ohlcv [{di+1}/{len(days)}] {d} {(time.time()-t0)/60:.1f}min covered={ (CNT>0).mean():.3f}", flush=True)
    empty = CNT == 0
    HIGH[~np.isfinite(HIGH)] = np.nan; LOW[~np.isfinite(LOW)] = np.nan
    VWAP = np.where(VOL > 0, QP / np.where(VOL > 0, VOL, np.nan), np.nan)
    VOL[empty] = np.nan; SF[empty] = np.nan
    # open_t ≈ close_{t−1}; break across day gaps
    OPEN = np.full((nT, nS), np.nan); OPEN[1:] = CLOSE[:-1]
    gap = np.zeros(nT, bool); gap[1:] = (grid[1:] - grid[:-1]) > 2 * STRIDE * NS
    OPEN[gap] = np.nan
    np.savez(OUT, ts=grid, day=day,
             OPEN=OPEN.astype(np.float32), HIGH=HIGH.astype(np.float32), LOW=LOW.astype(np.float32),
             CLOSE=CLOSE.astype(np.float32), VOL=VOL.astype(np.float32),
             VWAP=VWAP.astype(np.float32), SF=SF.astype(np.float32))
    print(f"[ohlcv] cached nT={nT} nS={nS} covered={ (~empty).mean():.3f} -> {OUT}", flush=True)


if __name__ == "__main__":
    build()

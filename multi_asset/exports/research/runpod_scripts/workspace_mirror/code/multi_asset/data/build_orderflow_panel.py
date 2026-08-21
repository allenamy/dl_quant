#!/usr/bin/env python3
"""Phase-0b/A — perp taker SIGNED-FLOW panel (180s buckets) for the order-flow factor.

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

The ★ orthogonal-to-funding candidate = accumulated net signed order flow (Hurst≈0.7 long memory
from metaorder splitting). Instantaneous OFI dies at ~2min, so we must ACCUMULATE — which means
per-180s-bucket AGGREGATION of the 1s taker flow (sum tdQtyBuy−tdQtySell over each bucket), NOT
the sampled-at-the-grid-second value that mid_panel stores. This builds that aggregated panel.

Bucket for grid ts G = trades in (G−180s, G] (causal, ≤t). Each 1s bar is assigned to the first
grid ts ≥ its ts (searchsorted side="left") with a 180s gap-guard so a bar never leaks across an
overnight gap into a far-future bucket. Empty buckets (data holes) → NaN via the per-bucket count.

Output: exports/oflow_panel.npz {ts, day, SF (nT,nS) net signed vol, VOLA (nT,nS) total taker vol}.
Usage: PYTHONPATH=. python multi_asset/data/build_orderflow_panel.py
"""
from __future__ import annotations
import os.path as p, sys, time
import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.bar_loader import load_day_panel  # noqa: E402
from multi_asset.data.build_multihorizon_targets import SYMBOLS, list_days, WIN_START, WIN_END  # noqa: E402

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
MIDCACHE = ROOT + "/mid_panel.npz"      # reuse its (ts, day) grid — identical common 180s grid
OUT = ROOT + "/oflow_panel.npz"
NS = 1_000_000_000
STRIDE = 180


def build():
    z = np.load(MIDCACHE, allow_pickle=True)
    grid = z["ts"].astype(np.int64); day = z["day"].astype(np.int64)
    nT, nS = len(grid), len(SYMBOLS)
    SF = np.zeros((nT, nS)); VOLA = np.zeros((nT, nS)); CNT = np.zeros((nT, nS), np.int64)
    days = list_days(WIN_START, WIN_END); t0 = time.time()
    for di, d in enumerate(days):
        try:
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            print(f"  [warn] {d}: {e}", flush=True); continue
        dts = dp.ts.astype(np.int64)
        try:
            qb = dp.cols.index("tdQtyBuy"); qs = dp.cols.index("tdQtySell")
        except ValueError:
            print(f"  [warn] {d}: no taker-flow cols", flush=True); continue
        bidx = np.searchsorted(grid, dts, side="left")            # first grid ts ≥ bar ts
        inr = bidx < nT
        gg = np.zeros(len(dts), bool)                              # gap-guard: bar within its 180s bucket
        gg[inr] = (grid[bidx[inr]] - dts[inr]) <= STRIDE * NS
        for si, s in enumerate(SYMBOLS):
            arr = dp.data[s]
            sf = arr[:, qb] - arr[:, qs]; vol = arr[:, qb] + arr[:, qs]
            m = gg & np.isfinite(sf) & np.isfinite(vol)
            b = bidx[m]
            np.add.at(SF[:, si], b, sf[m])
            np.add.at(VOLA[:, si], b, vol[m])
            np.add.at(CNT[:, si], b, 1)
        if (di + 1) % 50 == 0 or di == len(days) - 1:
            print(f"  ofl [{di+1}/{len(days)}] {d} {(time.time()-t0)/60:.1f}min "
                  f"covered={ (CNT>0).mean():.3f}", flush=True)
    empty = CNT == 0
    SF[empty] = np.nan; VOLA[empty] = np.nan
    np.savez(OUT, ts=grid, day=day, SF=SF.astype(np.float32), VOLA=VOLA.astype(np.float32))
    print(f"[oflow] cached nT={nT} nS={nS} covered={ (~empty).mean():.3f} -> {OUT}", flush=True)


if __name__ == "__main__":
    build()

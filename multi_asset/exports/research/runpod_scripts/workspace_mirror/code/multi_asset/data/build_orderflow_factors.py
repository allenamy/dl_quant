#!/usr/bin/env python3
"""Phase-0b/A — accumulated net signed ORDER-FLOW factors (orthogonal-to-funding candidate).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

From the 180s signed-flow panel (build_orderflow_panel.py): cumulative net taker imbalance over
multi-hour windows = rollsum(net signed vol) / rollsum(total taker vol) over the trailing window.
Per-asset comparable (dimensionless imbalance in ~[−1,1]), CAUSAL (trailing ≤t buckets), inherits
the Hurst≈0.7 long memory. A window sweep {2,4,8,24}h finds the persistence sweet spot; the mid
windows should be the ones that survive to 1h (instantaneous flow dies at ~2min).

Mechanism vs funding: funding = positioning/carry (who PAYS to hold); order flow = realized
aggressor PRESSURE (who is LIFTING). Different axis → expected low corr, real incremental IC.

Output: oflow_factor_cache/<sym>.npz {X (nT,F), ts, day, factor_names} — same schema as the
funding cache, so xsec_ridge_h --cache oflow_factor_cache consumes it identically.
Usage: PYTHONPATH=. python multi_asset/data/build_orderflow_factors.py
"""
from __future__ import annotations
import os, os.path as p
import numpy as np, pandas as pd

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
PANEL = ROOT + "/oflow_panel.npz"
OUT = ROOT + "/oflow_factor_cache"
STRIDE = 180
WINDOWS_H = [2, 4, 8, 24]
SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]


def _rollsum(A, w_steps):
    """Trailing sum over w_steps (min_periods = half) per column; NaN-tolerant."""
    return np.column_stack([pd.Series(A[:, si]).rolling(w_steps, min_periods=w_steps // 2).sum().values
                            for si in range(A.shape[1])])


def build():
    z = np.load(PANEL, allow_pickle=True)
    ts = z["ts"].astype(np.int64); day = z["day"].astype(np.int64)
    SF = z["SF"].astype(np.float64); VOLA = z["VOLA"].astype(np.float64)
    nT, nS = SF.shape
    names, cols = [], []
    for W in WINDOWS_H:
        ws = W * 3600 // STRIDE
        cum_sf = _rollsum(SF, ws); cum_vol = _rollsum(VOLA, ws)
        ofi = cum_sf / np.where(cum_vol > 0, cum_vol, np.nan)   # net imbalance ratio over window
        names.append(f"ofi_cum_{W}h"); cols.append(ofi.astype(np.float32))
    X = np.stack(cols, axis=-1)   # (nT, nS, F)
    os.makedirs(OUT, exist_ok=True)
    for si, s in enumerate(SYMBOLS):
        np.savez(p.join(OUT, f"{s}.npz"), X=X[:, si, :], ts=ts, day=day,
                 factor_names=np.array(names, dtype=object))
    fin = np.isfinite(X).mean(axis=(0, 1))
    print(f"[oflow] {len(names)} factors, nT={nT} nS={nS} -> {OUT}", flush=True)
    for k, nm in enumerate(names):
        print(f"   {nm:14s} finite={fin[k]:.3f}", flush=True)


if __name__ == "__main__":
    build()

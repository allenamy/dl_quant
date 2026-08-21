#!/usr/bin/env python3
"""Phase-0b/A — realized SEMIVARIANCE / SIGNED-JUMP asymmetry factors (2nd orthogonal axis).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

The team-lead's queued NEXT orthogonal axis after signed order-flow. Research top-5, microstructure-
persistent, orthogonal to BOTH funding (positioning) AND signed-flow (aggressor volume): it captures
return-ASYMMETRY (up-jumps vs down-jumps), a distinct signal.

From the 180s mid returns (mid_panel.npz, already cached — NO heavy load_day_panel sweep):
  RS⁺ = Σ r²·1[r>0], RS⁻ = Σ r²·1[r<0] over the trailing window (realized up/down semivariance).
  ★ semivar_skew_Wh = (RS⁺ − RS⁻)/(RS⁺ + RS⁻)   — signed-jump asymmetry, per-asset comparable [−1,1].
  rv_Wh              = RS⁺ + RS⁻                  — realized-variance LEVEL (risk/sizing, expect null-directional).
All CAUSAL (trailing ≤t). Cross-day-gap 180s returns masked (same as build_slow_factors).

NOTE vs B (slow factors, NULL): B had rvol/dvol as LEVELS; the skew (RS⁺−RS⁻)/(RS⁺+RS⁻) is a
distinct directional construction. 0C's gate-b (incremental over B+funding) will catch any
redundancy with short reversal — build it and let the gate decide.

Output: semivar_factor_cache/<sym>.npz {X (nT,F), ts, day, factor_names} — funding-cache schema.
Usage: PYTHONPATH=. python multi_asset/data/build_semivar_factors.py
"""
from __future__ import annotations
import os, os.path as p
import numpy as np, pandas as pd

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
MIDCACHE = ROOT + "/mid_panel.npz"
OUT = ROOT + "/semivar_factor_cache"
NS = 1_000_000_000
STRIDE = 180
WINDOWS_H = [4, 8, 24]
SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]


def _rollsum(A, w_steps):
    return np.column_stack([pd.Series(A[:, si]).rolling(w_steps, min_periods=w_steps // 2).sum().values
                            for si in range(A.shape[1])])


def build():
    z = np.load(MIDCACHE, allow_pickle=True)
    ts = z["ts"].astype(np.int64); day = z["day"].astype(np.int64); MID = z["MID"].astype(np.float64)
    nT, nS = MID.shape
    logmid = np.log(np.where(MID > 0, MID, np.nan))
    ret1 = np.full((nT, nS), np.nan)
    ret1[1:] = logmid[1:] - logmid[:-1]
    gap = np.full(nT, False); gap[1:] = (ts[1:] - ts[:-1]) > 2 * STRIDE * NS   # mask cross-day-gap
    ret1[gap] = np.nan
    r2p = np.where(ret1 > 0, ret1 * ret1, 0.0); r2p[~np.isfinite(ret1)] = np.nan
    r2m = np.where(ret1 < 0, ret1 * ret1, 0.0); r2m[~np.isfinite(ret1)] = np.nan

    names, cols = [], []
    for W in WINDOWS_H:
        ws = W * 3600 // STRIDE
        rsp = _rollsum(r2p, ws); rsm = _rollsum(r2m, ws); tot = rsp + rsm
        skew = (rsp - rsm) / np.where(tot > 0, tot, np.nan)
        names.append(f"semivar_skew_{W}h"); cols.append(skew.astype(np.float32))
    # RV level (24h) — risk/sizing, expect null-directional; include so the gate can confirm
    ws = 24 * 3600 // STRIDE
    rv = _rollsum(r2p, ws) + _rollsum(r2m, ws)
    names.append("rv_24h"); cols.append(np.log(np.where(rv > 0, rv, np.nan)).astype(np.float32))

    X = np.stack(cols, axis=-1)
    os.makedirs(OUT, exist_ok=True)
    for si, s in enumerate(SYMBOLS):
        np.savez(p.join(OUT, f"{s}.npz"), X=X[:, si, :], ts=ts, day=day,
                 factor_names=np.array(names, dtype=object))
    fin = np.isfinite(X).mean(axis=(0, 1))
    print(f"[semivar] {len(names)} factors, nT={nT} nS={nS} -> {OUT}", flush=True)
    for k, nm in enumerate(names):
        print(f"   {nm:18s} finite={fin[k]:.3f}", flush=True)


if __name__ == "__main__":
    build()

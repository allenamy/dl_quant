#!/usr/bin/env python3
"""Phase-0b/A — funding_ema-ONLY L/S preds for 0C's net-cost gate (the PURE low-turnover lever).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

The 7-factor combined ridge preds inherit turnover from the fast NULL factors (oi_mom, taker) and
could false-NO-GO the net-cost gate. funding_ema (24h-EMA of 8h settlements) is the load-bearing,
sign-consistent, delay-tolerant lever. Here the L/S score is the SINGLE factor, ranked xsec each ts:
  pred[i,:] = −xsec-z(funding_ema[i,:])   (IC is NEGATIVE → high score = LOW funding = LONG)
Same schema/folds/CL/panel as tag fund_h3600 so 0C's ls_gate consumes it identically.

Usage: PYTHONPATH=. python multi_asset/data/build_funding_ema_preds.py
"""
from __future__ import annotations
import os.path as p
import numpy as np

from multi_asset.baselines.xsec_ridge_h import build_panel_h, OUT
from multi_asset.baselines.xsec_ridge import SYMBOLS, FOLDS, EMBARGO

CACHE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/funding_factor_cache"
HORIZON = 3600
FACTOR = "funding_ema"
TAG = "fund_ema_h3600"


def main():
    ts, day, X, Y, CL, fnames = build_panel_h(HORIZON, CACHE)
    fi = fnames.index(FACTOR)
    uniq = np.unique(day); nS = len(SYMBOLS)

    def xsdemean_row(row):
        v = np.isfinite(row)
        out = np.full_like(row, np.nan)
        if v.sum() >= 5:
            out[v] = row[v] - row[v].mean()
        return out

    for fk, fold in enumerate(FOLDS):
        te0, te1 = fold["te"]
        if te1 > len(uniq):
            continue
        ted = set(uniq[te0:te1].tolist())
        tem = np.isin(day, list(ted))
        pred_TS = np.full((len(ts), nS), np.nan, np.float32); te_rows = []
        for i in np.where(tem)[0]:
            Yr = xsdemean_row(Y[i])
            f = X[i, :, fi]
            v = CL[i] & np.isfinite(f) & np.isfinite(Yr)
            if v.sum() >= 5:
                z = (f[v] - f[v].mean()) / (f[v].std() + 1e-12)
                pred_TS[i, v] = -z            # negative IC → long low funding
                te_rows.append(i)
        if te_rows:
            np.savez(p.join(OUT, f"fold_{fk}_preds_{TAG}.npz"),
                     te_rows=np.array(te_rows, np.int64), pred=pred_TS)
            print(f"fold {fk}: {len(te_rows)} clean test ts -> fold_{fk}_preds_{TAG}.npz", flush=True)

    np.savez(p.join(OUT, f"panel_ref_{TAG}.npz"),
             symbols=np.array(SYMBOLS, dtype=object), ts=ts, day=day, Y=Y, CL=CL)
    print(f"TAG={TAG}  panel_ref -> {OUT}/panel_ref_{TAG}.npz  (score = -xsec-z({FACTOR}))", flush=True)


if __name__ == "__main__":
    main()

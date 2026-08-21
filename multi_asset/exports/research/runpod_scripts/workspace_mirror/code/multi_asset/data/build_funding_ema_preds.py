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
import argparse, os.path as p
import numpy as np

from multi_asset.baselines.xsec_ridge_h import build_panel_h, OUT
from multi_asset.baselines.xsec_ridge import SYMBOLS, FOLDS, EMBARGO

CACHE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/funding_factor_cache"
# short aliases for the tag so files stay tidy
_ALIAS = {"funding_ema": "fund_ema", "funding_carry": "fund_carry", "toptrader_pos": "toptrader_pos"}


def main(factor="funding_ema", horizon=3600, tag=None, cache=CACHE, sign=-1.0):
    tag = tag or f"{_ALIAS.get(factor, factor)}_h{horizon}"
    ts, day, X, Y, CL, fnames = build_panel_h(horizon, cache)
    fi = fnames.index(factor)
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
                pred_TS[i, v] = sign * z      # sign = −1 for negative-IC crowding factors (long the low-crowding side); set +1 if the factor's standalone IC is positive
                te_rows.append(i)
        if te_rows:
            np.savez(p.join(OUT, f"fold_{fk}_preds_{tag}.npz"),
                     te_rows=np.array(te_rows, np.int64), pred=pred_TS)
            print(f"fold {fk}: {len(te_rows)} clean test ts -> fold_{fk}_preds_{tag}.npz", flush=True)

    np.savez(p.join(OUT, f"panel_ref_{tag}.npz"),
             symbols=np.array(SYMBOLS, dtype=object), ts=ts, day=day, Y=Y, CL=CL)
    print(f"TAG={tag}  panel_ref -> {OUT}/panel_ref_{tag}.npz  (score = {sign:+g}·xsec-z({factor}))", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--factor", default="funding_ema")
    ap.add_argument("--horizon", type=int, default=3600)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--cache", default=CACHE)
    ap.add_argument("--sign", type=float, default=-1.0)
    a = ap.parse_args()
    main(a.factor, a.horizon, a.tag, a.cache, a.sign)

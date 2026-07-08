#!/usr/bin/env python3
"""Stage fund_ema_fullhist on the M0 full-history seq-panel grid — for 0C's per-year BLEND (R4).

> **created:** 2026-07-09 | **Session:** multi-asset-v2 M0-fullhist (0B) | **状态:** in-progress

0C's per-year funding+M0 blend (pre-reg R4) needs funding_ema on the SAME grid/universe as the M0
walk-forward replay. This reads m0_fullhist_wf/panel_ref.npz (ts/day/Y/CL ≥3600, bnf* symbols),
ffill≤t-aligns funding_ema from the full-history funding_ema_hist cache (2020-2026), and emits the
funding L/S pred (score = −xsec-z(funding_ema), crowding-reversion) on the SAME 3 year-folds +
≥3600 CL, so the fold preds pair 1:1 with M0's for the blend. RUN AFTER the M0 run writes panel_ref.
Usage: PYTHONPATH=. python multi_asset/data/build_fund_ema_fullhist.py
"""
from __future__ import annotations
import os, os.path as p
import numpy as np

from multi_asset.train.train_temporal_spatial import build_fh_folds

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
WF = E + "/train/m0_fullhist_wf"
FUND = E + "/funding_ema_hist"
OUT = E + "/train/fund_ema_fullhist"


def main():
    ref = np.load(p.join(WF, "panel_ref.npz"), allow_pickle=True)
    ts = ref["ts"].astype(np.int64); day = ref["day"].astype(np.int64)
    Y = ref["Y"]; CL = ref["CL"]; syms = [str(x) for x in ref["symbols"]]
    T, S = Y.shape
    FP = np.full((T, S), np.nan)
    for si, s in enumerate(syms):
        z = np.load(p.join(FUND, f"{s}.npz"), allow_pickle=True)
        fts = z["ts"].astype(np.int64); fv = z["X"][:, 0].astype(np.float64)
        idx = np.searchsorted(fts, ts, side="right") - 1     # causal ffill ≤t
        ok = idx >= 0
        FP[ok, si] = fv[idx[ok]]
    cov = float(np.isfinite(FP).mean())
    print(f"[fund_fullhist] funding_ema aligned to M0 grid coverage={cov:.3f}", flush=True)
    uniq = np.unique(day)
    folds = build_fh_folds(uniq)
    os.makedirs(OUT, exist_ok=True)
    for fk, fold in enumerate(folds):
        te0, te1 = fold["te"]; ted = set(uniq[te0:te1].tolist())
        tem = np.isin(day, list(ted))
        pred = np.full((T, S), np.nan, np.float32); te_rows = []
        for i in np.where(tem)[0]:
            v = CL[i] & np.isfinite(FP[i]) & np.isfinite(Y[i])
            if v.sum() >= 5:
                f = FP[i, v]; z = (f - f.mean()) / (f.std() + 1e-12)
                pred[i, v] = -z                               # −1: long low funding (crowding-reversion)
                te_rows.append(i)
        if te_rows:
            np.savez(p.join(OUT, f"fold_{fk}_preds.npz"), pred=pred,
                     te_rows=np.array(te_rows, np.int64), te_days=np.array(sorted(ted), np.int64))
            print(f"  fold {fk}: {len(te_rows)} clean test ts (te {min(ted)}..{max(ted)})", flush=True)
    np.savez(p.join(OUT, "panel_ref.npz"), ts=ts, day=day, Y=Y, CL=CL, symbols=ref["symbols"])
    print(f"[fund_fullhist] -> {OUT} (pairs 1:1 with m0_fullhist_wf folds for R4 blend)", flush=True)


if __name__ == "__main__":
    main()

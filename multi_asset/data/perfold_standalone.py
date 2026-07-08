#!/usr/bin/env python3
"""Phase-0b/A — PER-FOLD standalone xsec rank-IC for the funding factors (0B).

Sign STABILITY across the 3 walk-forward folds is the decisive honesty check — the slow-price
factors (B) died exactly here (sign flipped fold-to-fold → anti-generalize). A funding factor is
a real bet only if its standalone IC keeps the SAME sign in every fold.

Usage: PYTHONPATH=. python multi_asset/data/perfold_standalone.py
"""
from __future__ import annotations
import argparse
import numpy as np
from scipy.stats import spearmanr

from multi_asset.baselines.xsec_ridge_h import build_panel_h
from multi_asset.baselines.xsec_ridge import FOLDS

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
CACHE = ROOT + "/funding_factor_cache"
HORIZON = 3600


def fold_standalone(X, Y, CL, day, uniq, fnames, te0, te1):
    ted = set(uniq[te0:te1].tolist())
    tem = np.isin(day, list(ted))
    Yr = np.full_like(Y, np.nan)
    for i in np.where(tem)[0]:
        row = Y[i]; v = np.isfinite(row)
        if v.sum() >= 5:
            Yr[i, v] = row[v] - row[v].mean()
    out = {}
    for f in range(X.shape[2]):
        ics = []
        for i in np.where(tem)[0]:
            v = CL[i] & np.isfinite(X[i, :, f]) & np.isfinite(Yr[i])
            if v.sum() >= 5:
                ic = spearmanr(X[i, v, f], Yr[i, v])[0]
                if np.isfinite(ic):
                    ics.append(ic)
        out[fnames[f]] = (round(float(np.mean(ics)), 4), len(ics)) if ics else (None, 0)
    return out


def main(cache=CACHE, horizon=HORIZON):
    ts, day, X, Y, CL, fnames = build_panel_h(horizon, cache)
    uniq = np.unique(day)
    print(f"{'factor':18s} " + " ".join(f"fold{k}" for k in range(len(FOLDS))) + "   sign-consistent?")
    rows = {fn: [] for fn in fnames}
    for k, fold in enumerate(FOLDS):
        te0, te1 = fold["te"]
        if te1 > len(uniq):
            continue
        res = fold_standalone(X, Y, CL, day, uniq, fnames, te0, te1)
        for fn in fnames:
            rows[fn].append(res[fn][0])
    for fn in fnames:
        vals = rows[fn]
        signs = set(np.sign(v) for v in vals if v is not None and v != 0)
        consistent = "YES" if len(signs) == 1 else "NO (flips)"
        cell = " ".join(f"{v:+.4f}" if v is not None else "  None " for v in vals)
        print(f"{fn:18s} {cell}   {consistent}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=CACHE)
    ap.add_argument("--horizon", type=int, default=HORIZON)
    a = ap.parse_args()
    main(a.cache, a.horizon)

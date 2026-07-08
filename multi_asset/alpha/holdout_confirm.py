#!/usr/bin/env python3
"""Pre-registered HOLDOUT confirm for the Alpha sweep survivors (0B).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

The screen z + per-fold used the 3 fold TEST blocks. A truly independent holdout = the FORWARD
month-block AFTER fold2's test window (uniq day-index ≥ fold2.te[1]) — never used in any fold's
train or test, so never touched by the screen. Confirm each survivor's standalone xsec rank-IC
keeps its screen sign there. (Also reports the two inter-fold gap blocks as extra unused holdouts.)
Usage: PYTHONPATH=. python multi_asset/alpha/holdout_confirm.py
"""
from __future__ import annotations
import json, os.path as p
import numpy as np
from scipy.stats import rankdata

from multi_asset.baselines.xsec_ridge import SYMBOLS, FOLDS

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
SURV = ["a101_044", "gtja_046", "a101_045"]


def ic_over_days(Xf, Y, CL, day, hold_days):
    m = np.isin(day, hold_days)
    ics = []
    for i in np.where(m)[0]:
        v = CL[i] & np.isfinite(Xf[i]) & np.isfinite(Y[i])
        if v.sum() >= 5:
            yr = Y[i, v] - Y[i, v].mean()
            ic = np.corrcoef(rankdata(Xf[i, v]), rankdata(yr))[0, 1]
            if np.isfinite(ic):
                ics.append(ic)
    return (float(np.mean(ics)), len(ics)) if ics else (np.nan, 0)


def main():
    ref = np.load(p.join(E, "eda/panel_ref_a101_044_h3600.npz"), allow_pickle=True)
    ts = ref["ts"].astype(np.int64); day = ref["day"].astype(np.int64)
    Y = ref["Y"]; CL = ref["CL"]
    uniq = np.unique(day); n = len(uniq)
    # survivor factor values (full grid) from the survivor cache
    fac = {}
    for nm_i, nm in enumerate(SURV):
        cols = []
        for s in SYMBOLS:
            z = np.load(p.join(E, "survivor_factor_cache", f"{s}.npz"), allow_pickle=True)
            names = [str(x) for x in z["factor_names"]]
            cols.append(z["X"][:, names.index(nm)])
        fac[nm] = np.column_stack(cols)   # (nT, nS)

    te1 = FOLDS[2]["te"][1]
    fwd_days = uniq[te1:].tolist() if te1 < n else []
    gap1 = uniq[FOLDS[0]["te"][1]:FOLDS[1]["te"][0]].tolist()
    gap2 = uniq[FOLDS[1]["te"][1]:FOLDS[2]["te"][0]].tolist()
    blocks = {"FORWARD(post-fold2)": fwd_days, "gap0-1": gap1, "gap1-2": gap2}
    screen_sign = {"a101_044": +1, "gtja_046": +1, "a101_045": +1}   # all positive screen IC

    print(f"{'survivor':12s}  " + "  ".join(f"{b}(n_days={len(d)})" for b, d in blocks.items()))
    for nm in SURV:
        cells = []
        for b, d in blocks.items():
            ic, nts = ic_over_days(fac[nm], Y, CL, day, d)
            ok = "OK" if np.isfinite(ic) and np.sign(ic) == screen_sign[nm] else "FLIP"
            cells.append(f"IC={ic:+.4f}(nts={nts},{ok})")
        print(f"{nm:12s}  " + "  ".join(cells))
    print("\nscreen sign = +1 for all 3; FORWARD block is the pre-registered holdout (post all folds).")


if __name__ == "__main__":
    main()

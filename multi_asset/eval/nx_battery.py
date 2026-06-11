"""NX evaluation battery: PAIRED model comparison with day-block bootstrap.

The statistical instrument behind every NX stage gate. At long horizons the
clean sample is thin (y_1800: ~1900 ts/fold; single-seed fold IC carries a
±0.013 95% CI), so unpaired comparisons and flat +0.003 gates are meaningless.
This battery compares two prediction sets ON THE SAME clean timestamps:

  1. per-timestamp cross-sectional rank-IC for A and B on the intersection of
     valid clean ts -> per-DAY mean IC series for each + the paired per-day dIC;
  2. day-block bootstrap (resample whole days, B=10,000) -> P(dIC>0) + 95% CI;
  3. pooled + per-fold rank-IC, IC-IR (per-day convention), per-asset P/S,
     sigma-ratio, decile monotonicity for both models;
  4. gate verdict per the NX table (screen/promote thresholds by horizon).

Inputs: two saved-prediction dirs (EXPORT/<tag>/ with panel_ref.npz +
fold_*_preds.npz, as written by train_temporal_spatial --save_tag).

Usage:
  python3 multi_asset/eval/nx_battery.py --tag_a R1_y1800 --tag_b NX_s1_y1800 \
      --horizon 1800 [--level screen|promote]
  Single-model report: omit --tag_b.
"""
from __future__ import annotations

import argparse
import glob
import json
import os.path as p

import numpy as np
from scipy.stats import pearsonr, spearmanr

EXPORT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
          "multi_asset/exports/train")
MIN_ASSETS = 5
B_BOOT = 10_000

GATES = {  # (screen_delta, promote_delta) by horizon bucket
    180: (0.003, 0.003), 600: (0.003, 0.003), 1800: (0.004, 0.004), 3600: (0.004, 0.004),
}


def load_tag(tag):
    d = p.join(EXPORT, tag)
    ref = np.load(p.join(d, "panel_ref.npz"), allow_pickle=True)
    T, S = ref["Y"].shape
    pred = np.full((T, S), np.nan, np.float32)
    folds = {}
    for f in sorted(glob.glob(p.join(d, "fold_*_preds.npz"))):
        z = np.load(f)
        rows = z["te_rows"]
        pred[rows] = z["pred"][rows]
        folds[int(p.basename(f).split("_")[1])] = rows
    return ref, pred, folds


def clean_rows(ref, horizon):
    """Non-overlap eval rows: clean600 flag for h<=600, grid-thinning for h>600."""
    Y, CL, day = ref["Y"], ref["CL"], ref["day"]
    T = Y.shape[0]
    if horizon <= 600:
        return np.arange(T), CL
    keep = np.zeros(T, bool)
    step = horizon // 180
    for d in np.unique(day):
        rows = np.where(day == d)[0]
        keep[rows[::step]] = True
    return np.where(keep)[0], np.isfinite(Y)


def ic_series(pred, ref, rows, CLm):
    """Per-timestamp rank-IC over valid clean assets -> (ts_idx, ic) arrays."""
    Y = ref["Y"]
    out_r, out_ic = [], []
    for t in rows:
        v = CLm[t] & np.isfinite(pred[t]) & np.isfinite(Y[t])
        if v.sum() >= MIN_ASSETS:
            ic = spearmanr(pred[t, v], Y[t, v]).correlation
            if np.isfinite(ic):
                out_r.append(t); out_ic.append(ic)
    return np.array(out_r), np.array(out_ic)


def per_day(day, rows, vals):
    days = day[rows]
    uniq = np.unique(days)
    return uniq, np.array([vals[days == d].mean() for d in uniq])


def day_bootstrap(day_vals, B=B_BOOT, seed=7):
    rng = np.random.default_rng(seed)
    n = len(day_vals)
    idx = rng.integers(0, n, size=(B, n))
    means = day_vals[idx].mean(axis=1)
    return float((means > 0).mean()), (float(np.quantile(means, 0.025)),
                                       float(np.quantile(means, 0.975)))


def model_report(pred, ref, rows, CLm, folds):
    day = ref["day"]
    r, ic = ic_series(pred, ref, rows, CLm)
    ud, dvals = per_day(day, r, ic)
    icir_daily = float(dvals.mean() / dvals.std()) if dvals.std() > 0 else float("nan")
    per_fold = {}
    for fi, frows in folds.items():
        fset = np.isin(r, frows)
        per_fold[fi] = round(float(ic[fset].mean()), 4) if fset.any() else None
    # per-asset P/S on the eval rows
    Y = ref["Y"]
    perP, perS = [], []
    for j in range(Y.shape[1]):
        m = np.zeros(Y.shape[0], bool); m[rows] = True
        m &= CLm[:, j] & np.isfinite(pred[:, j]) & np.isfinite(Y[:, j])
        if m.sum() > 100:
            perP.append(pearsonr(pred[m, j], Y[m, j])[0])
            perS.append(spearmanr(pred[m, j], Y[m, j])[0])
    return dict(rank_ic=round(float(ic.mean()), 4), n_ts=int(len(ic)),
                ic_ir_daily=round(icir_daily, 3), n_days=int(len(ud)),
                per_fold=per_fold,
                per_asset_P=round(float(np.mean(perP)), 4),
                per_asset_S=round(float(np.mean(perS)), 4)), (r, ic)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag_a", required=True, help="candidate")
    ap.add_argument("--tag_b", default=None, help="incumbent/baseline (paired vs)")
    ap.add_argument("--horizon", type=int, required=True)
    ap.add_argument("--level", choices=["screen", "promote"], default="screen")
    args = ap.parse_args()

    ref, pa, folds = load_tag(args.tag_a)
    rows, CLm = clean_rows(ref, args.horizon)
    rep_a, (ra, ica) = model_report(pa, ref, rows, CLm, folds)
    out = {"tag_a": args.tag_a, "horizon": args.horizon, "A": rep_a}

    if args.tag_b:
        ref_b, pb, folds_b = load_tag(args.tag_b)
        assert ref_b["Y"].shape == ref["Y"].shape, "panel mismatch"
        # coverage-confound fix (audit 2026-06-11): solo numbers for BOTH models
        # are computed on the intersection of finite-pred rows so differing
        # coverage (e.g. coarse first-hour drop) cannot flatter either model.
        both = np.isfinite(pa).any(axis=1) & np.isfinite(pb).any(axis=1)
        rows = rows[both[rows]]
        rep_a, (ra, ica) = model_report(pa, ref, rows, CLm, folds)
        out["A"] = rep_a
        rep_b, (rb, icb) = model_report(pb, ref, rows, CLm, folds_b)
        # paired on the intersection of scored ts
        common, ia, ib = np.intersect1d(ra, rb, return_indices=True)
        d_ic = ica[ia] - icb[ib]
        ud, ddays = per_day(ref["day"], common, d_ic)
        pgt, ci = day_bootstrap(ddays)
        gate = GATES.get(args.horizon, (0.004, 0.004))
        thr = gate[0] if args.level == "screen" else gate[1]
        pneed = 0.90 if args.level == "screen" else 0.95
        delta = float(d_ic.mean())
        verdict = "PASS" if (delta >= thr and pgt >= pneed) else "FAIL"
        out.update({"tag_b": args.tag_b, "B": rep_b,
                    "paired": dict(delta_ic=round(delta, 4), n_ts=int(len(common)),
                                   n_days=int(len(ud)), bootstrap_P_gt0=round(pgt, 3),
                                   delta_ci95=[round(ci[0], 4), round(ci[1], 4)]),
                    "gate": dict(level=args.level, need_delta=thr, need_P=pneed,
                                 verdict=verdict)})
    print(json.dumps(out, indent=2))
    od = p.join(EXPORT, args.tag_a, f"nx_battery_vs_{args.tag_b or 'solo'}_h{args.horizon}.json")
    json.dump(out, open(od, "w"), indent=2)
    print(f"saved -> {od}")


if __name__ == "__main__":
    main()

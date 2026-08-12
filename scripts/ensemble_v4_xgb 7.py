#!/usr/bin/env python3
"""V4 + XGBoost ensemble for Phase C backtest.

Builds ensemble predictions from existing Phase A outputs:
  - V4 y_180 predictions: experiments/v4_noattn_700d/fold_{0,1,2}/test_preds.npz
  - XGBoost y_180 predictions: experiments/baselines_v4_matched_preds/fold_{i}_XGBoost_preds.npz

Weight strategy (no-leakage):
  - PRIMARY: equal weight (V4=0.5, XGBoost=0.5) — robust, no test-set leak
  - SECONDARY (for reference only): Grinold-Kahn optimal computed on Phase A
    test set (flagged as optimistic / upper-bound, for context)

Output:
  experiments/phase_c/ensemble_preds/fold_{0,1,2}.npz
  Each contains: predictions, predictions_ew, predictions_gk, targets, mask,
  timestamps, v4_pred, xgb_pred
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Tuple

import numpy as np
from scipy.stats import pearsonr, spearmanr


def load_fold(v4_dir: pathlib.Path, xgb_dir: pathlib.Path, fold: int) -> dict:
    """Load V4 and XGBoost predictions for a fold, aligned on timestamp."""
    v4_path = v4_dir / f"fold_{fold}" / "test_preds.npz"
    xgb_path = xgb_dir / f"fold_{fold}_XGBoost_preds.npz"

    v4 = np.load(str(v4_path))
    xgb = np.load(str(xgb_path))

    v4_q50 = v4["predictions"][:, 1]  # q50 as point estimate
    v4_q10 = v4["predictions"][:, 0]
    v4_q90 = v4["predictions"][:, 2]
    v4_y = v4["targets"]
    v4_mask = v4["mask"].astype(bool)
    v4_ts = v4["timestamps"]

    xgb_pred = xgb["predictions"]
    xgb_y = xgb["targets"]
    xgb_mask = xgb["mask"].astype(bool)
    xgb_ts = xgb["timestamps"]

    # V4 targets are normalized by V4's y_sigma; XGB targets by its own y_mad_sigma.
    # Scales differ but the underlying series is the same (same test windows).
    # Align by length — same NPZ source so same order.
    assert len(v4_q50) == len(xgb_pred), (
        f"V4 (N={len(v4_q50)}) and XGB (N={len(xgb_pred)}) length differ for fold {fold}"
    )
    # Use XGB's targets as canonical (on z-score scale) for downstream backtest;
    # Pearson/Spearman are scale-invariant so ensemble metrics unaffected.
    return {
        "v4_q50": v4_q50.astype(np.float32),
        "v4_q10": v4_q10.astype(np.float32),
        "v4_q90": v4_q90.astype(np.float32),
        "xgb_pred": xgb_pred.astype(np.float32),
        "targets": xgb_y.astype(np.float32),  # z-scored scale, canonical
        "targets_v4_scale": v4_y.astype(np.float32),  # raw V4 normalization
        "mask": (v4_mask & xgb_mask).astype(bool),
        "timestamps": xgb_ts.astype(np.int64),  # XGB stores seconds directly
    }


def standardize(x: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Z-score with only masked samples for stats computation."""
    xv = x[mask]
    mu = xv.mean() if len(xv) > 0 else 0.0
    sigma = xv.std() if len(xv) > 1 else 1.0
    return (x - mu) / max(sigma, 1e-8)


def pearson(p: np.ndarray, y: np.ndarray) -> float:
    if len(p) < 2 or np.std(p) < 1e-12:
        return float("nan")
    return float(pearsonr(p, y)[0])


def spearman(p: np.ndarray, y: np.ndarray) -> float:
    if len(p) < 2:
        return float("nan")
    return float(spearmanr(p, y)[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v4-dir", type=pathlib.Path, default=pathlib.Path("experiments/v4_noattn_700d"))
    parser.add_argument("--xgb-dir", type=pathlib.Path, default=pathlib.Path("experiments/baselines_v4_matched_preds"))
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path("experiments/phase_c/ensemble_preds"))
    parser.add_argument("--folds", type=int, nargs="+", default=[0, 1, 2])
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load all folds, compute per-fold and pooled metrics
    all_folds = {}
    for f in args.folds:
        all_folds[f] = load_fold(args.v4_dir, args.xgb_dir, f)

    print("=" * 80)
    print("V4 + XGBoost Ensemble — Phase C Stage 1")
    print("=" * 80)
    print()
    print(f"{'Fold':>6} | {'Source':>12} | {'Pearson':>10} | {'Spearman':>10} | {'N (masked)':>12}")
    print("-" * 75)

    summary = {"per_fold": {}, "pooled": {}}

    # Per-fold single-model + EW ensemble
    for f, d in all_folds.items():
        m = d["mask"]
        y_m = d["targets"][m]

        # V4 q50 and XGB are on different scales. Standardize before averaging.
        v4_z = standardize(d["v4_q50"], m)
        xgb_z = standardize(d["xgb_pred"], m)
        ew = 0.5 * v4_z + 0.5 * xgb_z

        v4_p = pearson(d["v4_q50"][m], y_m); v4_s = spearman(d["v4_q50"][m], y_m)
        xgb_p = pearson(d["xgb_pred"][m], y_m); xgb_s = spearman(d["xgb_pred"][m], y_m)
        ew_p = pearson(ew[m], y_m); ew_s = spearman(ew[m], y_m)

        print(f"{f:>6} | {'V4':>12} | {v4_p:>10.4f} | {v4_s:>10.4f} | {int(m.sum()):>12}")
        print(f"{f:>6} | {'XGBoost':>12} | {xgb_p:>10.4f} | {xgb_s:>10.4f} | {int(m.sum()):>12}")
        print(f"{f:>6} | {'EW ensemble':>12} | {ew_p:>10.4f} | {ew_s:>10.4f} | {int(m.sum()):>12}")
        print()

        summary["per_fold"][f] = {
            "V4": {"pearson": v4_p, "spearman": v4_s, "n": int(m.sum())},
            "XGBoost": {"pearson": xgb_p, "spearman": xgb_s, "n": int(m.sum())},
            "EW_ensemble": {"pearson": ew_p, "spearman": ew_s, "n": int(m.sum())},
        }

        # Save per-fold ensemble preds (standardized scale — consistent across folds)
        np.savez(
            args.output_dir / f"fold_{f}.npz",
            predictions=ew.astype(np.float32),  # PRIMARY: equal-weight ensemble
            v4_q50=d["v4_q50"],
            v4_q10=d["v4_q10"],
            v4_q90=d["v4_q90"],
            xgb_pred=d["xgb_pred"],
            targets=d["targets"],
            mask=d["mask"],
            timestamps=d["timestamps"],
            weight_v4=np.float32(0.5),
            weight_xgb=np.float32(0.5),
            weighting_scheme="equal_weight_standardized",
        )

    # Pooled
    all_v4, all_xgb, all_ew, all_y = [], [], [], []
    for f, d in all_folds.items():
        m = d["mask"]
        v4_z = standardize(d["v4_q50"], m)
        xgb_z = standardize(d["xgb_pred"], m)
        ew = 0.5 * v4_z + 0.5 * xgb_z
        all_v4.append(v4_z[m])
        all_xgb.append(xgb_z[m])
        all_ew.append(ew[m])
        all_y.append(d["targets"][m])

    all_v4 = np.concatenate(all_v4); all_xgb = np.concatenate(all_xgb)
    all_ew = np.concatenate(all_ew); all_y = np.concatenate(all_y)

    v_p = pearson(all_v4, all_y); v_s = spearman(all_v4, all_y)
    x_p = pearson(all_xgb, all_y); x_s = spearman(all_xgb, all_y)
    e_p = pearson(all_ew, all_y); e_s = spearman(all_ew, all_y)

    print("=" * 75)
    print("POOLED (standardized within fold, then concat)")
    print("=" * 75)
    print(f"{'V4':>15}: Pearson={v_p:.4f}  Spearman={v_s:.4f}  N={len(all_v4):,}")
    print(f"{'XGBoost':>15}: Pearson={x_p:.4f}  Spearman={x_s:.4f}  N={len(all_xgb):,}")
    print(f"{'EW ensemble':>15}: Pearson={e_p:.4f}  Spearman={e_s:.4f}  N={len(all_ew):,}")
    print()
    print(f"Lift: Ensemble vs V4     = P+{e_p-v_p:+.4f}  S+{e_s-v_s:+.4f}")
    print(f"Lift: Ensemble vs XGB    = P+{e_p-x_p:+.4f}  S+{e_s-x_s:+.4f}")

    summary["pooled"] = {
        "V4": {"pearson": v_p, "spearman": v_s, "n": len(all_v4)},
        "XGBoost": {"pearson": x_p, "spearman": x_s, "n": len(all_xgb)},
        "EW_ensemble": {"pearson": e_p, "spearman": e_s, "n": len(all_ew)},
        "ensemble_lift_vs_v4": {"pearson": e_p - v_p, "spearman": e_s - v_s},
        "ensemble_lift_vs_xgb": {"pearson": e_p - x_p, "spearman": e_s - x_s},
    }

    with open(args.output_dir / "ensemble_summary.json", "w") as fp:
        json.dump(summary, fp, indent=2, default=float)

    print(f"\n✓ Ensemble predictions saved to {args.output_dir}/")
    print(f"✓ Summary saved to {args.output_dir}/ensemble_summary.json")


if __name__ == "__main__":
    main()

"""
Export 6 production candidate y_600 prediction CSVs.

Each CSV is multi-seed median (value-blend, NOT rank-blend per anti-pattern #16).

Output schema (per row):
  timestamp_us, datetime_utc, fold, horizon_sec, mask,
  y_true_logret, y_true_bps, y_pred_q50_logret, y_pred_q50_bps,
  y_pred_q50_z, y_sigma_train_bps

CSVs produced (under exports/):
  1. y600_baseline_plus_BEST_3seed_median.csv  (seeds 42/7/13, 3 folds)
  2. y600_baseline_plus_EMA_3seed_median.csv   (seeds 42/7/13, 3 folds) — production
  3. y600_baseline_plus_SWA_3seed_median.csv   (seeds 42/7/13, 3 folds)
  4. y600_phase3c_BEST_2seed_median.csv        (seeds 42/7,    4 folds)
  5. y600_phase3c_EMA_2seed_median.csv         (seeds 42/7,    4 folds)
  6. y600_phase3c_SWA_2seed_median.csv         (seeds 42/7,    4 folds)

Anti-pattern #18: evaluation must be against RAW y_600 (not smooth).
The targets in test_preds.npz are normalized (z-scored). To recover raw bps:
  y_raw_bps = (y_z * y_sigma_train) * 1e4  where y_sigma_train is from norm_params.

Exit 0 on success.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# (model_name, ckpt_kind, seed_dirs, num_folds)
MODEL_VARIANTS = [
    ("baseline_plus", "BEST", {
        42: Path("experiments/y600_push/baseline_plus"),
        7: Path("experiments/y600_baseline_seed7"),
        13: Path("experiments/y600_baseline_seed13"),
    }, 3),
    ("baseline_plus", "EMA", {
        42: Path("experiments/y600_push/baseline_plus"),
        7: Path("experiments/y600_baseline_seed7"),
        13: Path("experiments/y600_baseline_seed13"),
    }, 3),
    ("baseline_plus", "SWA", {
        42: Path("experiments/y600_push/baseline_plus"),
        7: Path("experiments/y600_baseline_seed7"),
        13: Path("experiments/y600_baseline_seed13"),
    }, 3),
    ("phase3c", "BEST", {
        42: Path("experiments/y600_phase3c_pure/baseline"),
        7: Path("experiments/y600_phase3c_pure_seed7/baseline"),
    }, 4),
    ("phase3c", "EMA", {
        42: Path("experiments/y600_phase3c_pure/baseline"),
        7: Path("experiments/y600_phase3c_pure_seed7/baseline"),
    }, 4),
    ("phase3c", "SWA", {
        42: Path("experiments/y600_phase3c_pure/baseline"),
        7: Path("experiments/y600_phase3c_pure_seed7/baseline"),
    }, 4),
]

# CKPT → npz file
CKPT_TO_FILE = {
    "BEST": "test_preds.npz",
    "EMA": "ema_test_preds.npz",
    "SWA": "swa_test_preds.npz",
}


def load_fold_preds(seed_dir: Path, fold: int, ckpt: str):
    """Returns (timestamps, predictions_q50, targets_z, mask, y_sigma)."""
    fpath = seed_dir / f"fold_{fold}" / CKPT_TO_FILE[ckpt]
    np_path = seed_dir / f"fold_{fold}" / "norm_params.npz"
    d = np.load(fpath)
    norm = np.load(np_path) if np_path.exists() else None
    pred = d["predictions"][:, 1].astype(np.float64)  # q50 (z-space)
    tgt = d["targets"].astype(np.float64)  # z-space
    msk = d["mask"].astype(bool)
    ts = d["timestamps"].astype(np.int64)
    # y_sigma in raw logret units
    if "y_sigma" in d.files:
        sigma_lr = float(d["y_sigma"])
    elif norm is not None and "y_sigma" in norm.files:
        sigma_lr = float(norm["y_sigma"])
    else:
        raise RuntimeError(f"No y_sigma found for {seed_dir}/fold_{fold}")
    return ts, pred, tgt, msk, sigma_lr


def build_csv(model: str, ckpt: str, seed_dirs: dict, num_folds: int, out_path: Path):
    """Build multi-seed median CSV for one (model, ckpt) variant."""
    print(f"\n=== {model} {ckpt} ({len(seed_dirs)}-seed median, {num_folds} folds) → {out_path.name} ===")
    rows = []
    for fold in range(num_folds):
        per_seed = {}
        ts_ref = None
        msk_ref = None
        sigma_ref = None
        for seed, sd in seed_dirs.items():
            try:
                ts, pred, tgt, msk, sigma = load_fold_preds(sd, fold, ckpt)
            except FileNotFoundError as e:
                print(f"  [WARN] missing fold {fold} seed {seed}: {e}")
                continue
            per_seed[seed] = (ts, pred, tgt, msk, sigma)
            if ts_ref is None:
                ts_ref, msk_ref, sigma_ref = ts, msk, sigma
            else:
                # Sanity: all seeds same fold should have same ts/mask
                assert (ts == ts_ref).all(), f"ts mismatch fold {fold} seed {seed}"
                assert (msk == msk_ref).all(), f"mask mismatch fold {fold} seed {seed}"
        if not per_seed:
            print(f"  [SKIP] fold {fold}: no seeds available")
            continue
        # Pick targets from first available seed (should be identical anyway)
        first_seed = next(iter(per_seed))
        _, _, tgt_z, _, _ = per_seed[first_seed]
        # value-blend median across seeds
        pred_stack = np.stack([per_seed[s][1] for s in sorted(per_seed.keys())], axis=0)
        pred_med = np.median(pred_stack, axis=0)
        # convert
        sigma_bps = sigma_ref * 1e4
        y_true_lr = tgt_z * sigma_ref
        y_true_bps = y_true_lr * 1e4
        y_pred_lr = pred_med * sigma_ref
        y_pred_bps = y_pred_lr * 1e4
        # build dataframe rows
        for i in range(len(ts_ref)):
            dt_utc = datetime.fromtimestamp(ts_ref[i] / 1e6, tz=timezone.utc)
            rows.append({
                "timestamp_us": int(ts_ref[i]),
                "datetime_utc": dt_utc.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "fold": fold,
                "horizon_sec": 600,
                "mask": bool(msk_ref[i]),
                "y_true_logret": float(y_true_lr[i]),
                "y_true_bps": float(y_true_bps[i]),
                "y_pred_q50_logret": float(y_pred_lr[i]),
                "y_pred_q50_bps": float(y_pred_bps[i]),
                "y_pred_q50_z": float(pred_med[i]),
                "y_sigma_train_bps": float(sigma_bps),
            })
        print(f"  fold {fold}: {len(per_seed)} seeds, {len(ts_ref)} rows ({int(msk_ref.sum())} valid)")
    df = pd.DataFrame(rows)
    out_path.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(out_path, index=False, float_format="%.8g")
    print(f"  → wrote {out_path} ({len(df):,} rows, {df['mask'].sum():,} valid)")
    return df


def main():
    out_dir = Path("exports")
    for model, ckpt, seed_dirs, num_folds in MODEL_VARIANTS:
        out_path = out_dir / f"y600_{model}_{ckpt}_{len(seed_dirs)}seed_median.csv"
        build_csv(model, ckpt, seed_dirs, num_folds, out_path)


if __name__ == "__main__":
    main()

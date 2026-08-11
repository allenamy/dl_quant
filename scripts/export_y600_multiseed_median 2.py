"""Export y_600 baseline_plus 3-seed median-blend predictions to CSV.

VALUE-blend (median across seeds) — NOT rank-blend (anti-pattern #16).
Targets are RAW y_600 from data/npz_v4 (anti-pattern #18: must eval on raw).

Output schema (sorted by timestamp_us):
  timestamp_us       : int64, microseconds since Unix epoch (UTC)
  datetime_utc       : ISO-8601 datetime string
  fold               : 0/1/2 (walk-forward fold id)
  horizon_sec        : 600
  mask               : 1 if valid target, 0 if masked out
  y_true_logret      : raw 600s forward log-return (from data/npz_v4 — un-normalised, NOT smoothed)
  y_true_bps         : y_true_logret * 1e4
  y_pred_q50_logret  : 3-seed median q50 (un-normalised by per-fold sigma)
  y_pred_q50_bps     : y_pred_q50_logret * 1e4
  y_pred_q50_z       : 3-seed median q50 in z-score units (model native output)
  y_sigma_train_bps  : per-fold train MAD-sigma in bps (used for un-normalisation)

Anchor semantics: timestamp_us = end of 600-step input window.
Target = log(mid[t+600s] / mid[t]) where t = timestamp_us. RAW y_600.

USAGE:
  python scripts/export_y600_multiseed_median.py \\
      --seeds 42 7 13 \\
      --seed-dirs experiments/v4_noattn_700d_y600 experiments/y600_baseline_seed7 experiments/y600_baseline_seed13 \\
      --variant ema_test_preds \\
      --raw-y-dir data/npz_v4 \\
      --out exports/y600_baseline_3seed_median.csv

Note: seed=42 baseline reuses original baseline_plus run if matching config; supply
the correct path. For value-blend, all seeds must use SAME config + SAME folds.
"""
from __future__ import annotations

import argparse
import os
import pathlib
from datetime import datetime, timezone

import numpy as np
import pandas as pd


def load_seed_fold(seed_dir: str, fold: int, variant: str) -> dict:
    """Load test_preds.npz for one (seed, fold) variant."""
    path = pathlib.Path(seed_dir) / f"fold_{fold}" / f"{variant}.npz"
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")
    d = np.load(path)
    return {
        "predictions": d["predictions"].astype(np.float32),
        "targets_normed": d["targets"].astype(np.float32),
        "mask": d["mask"].astype(np.int8),
        "timestamps": d["timestamps"].astype(np.int64),
        "y_sigma": float(d["y_sigma"]),
        "y_median": float(d["y_median"]),
    }


def load_raw_y600_for_fold(raw_y_dir: str, timestamps_us: np.ndarray) -> np.ndarray:
    """Look up raw y_600 (unnormalised log-return) by timestamp.

    Group timestamps by date, load each day's NPZ once, build dict, lookup.
    Returns y_raw aligned to timestamps_us (NaN for misses).
    """
    dt_arr = np.array([
        datetime.fromtimestamp(int(t) / 1e6, tz=timezone.utc).strftime("%Y-%m-%d")
        for t in timestamps_us
    ])
    y_raw = np.full(len(timestamps_us), np.nan, dtype=np.float64)
    for date in np.unique(dt_arr):
        npz_path = pathlib.Path(raw_y_dir) / f"{date}.npz"
        if not npz_path.exists():
            continue
        with np.load(npz_path, allow_pickle=True) as d2:
            ts_raw = d2["timestamps"].astype(np.int64) if "timestamps" in d2.files else None
            if ts_raw is None:
                continue
            if "y_600" in d2.files:
                y_raw_day = d2["y_600"].astype(np.float64)
            elif "y" in d2.files and d2["y"].ndim == 2:
                y_raw_day = d2["y"][:, 1].astype(np.float64)  # assumes y_600 is 2nd column
            else:
                continue
            lookup = dict(zip(ts_raw.tolist(), y_raw_day.tolist()))
        date_mask = (dt_arr == date)
        date_indices = np.where(date_mask)[0]
        for j in date_indices:
            tts = int(timestamps_us[j])
            if tts in lookup:
                y_raw[j] = lookup[tts]
    return y_raw


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, nargs="+", required=True,
                    help="Seed labels (for log/manifest only, e.g. 42 7 13)")
    ap.add_argument("--seed-dirs", type=str, nargs="+", required=True,
                    help="Per-seed experiment dirs (one per --seed)")
    ap.add_argument("--variant", choices=["test_preds", "ema_test_preds", "swa_test_preds"],
                    default="ema_test_preds",
                    help="Which test prediction variant to blend (default: EMA)")
    ap.add_argument("--folds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--raw-y-dir", type=str, default="data/npz_v4",
                    help="Dir containing raw NPZs with y_600 + timestamps")
    ap.add_argument("--out", type=str, required=True,
                    help="Output CSV path")
    args = ap.parse_args()

    if len(args.seeds) != len(args.seed_dirs):
        raise ValueError("--seeds and --seed-dirs must have same length")

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[export] {len(args.seeds)}-seed median value-blend on variant={args.variant}")
    print(f"[export] seeds: {args.seeds}")
    print(f"[export] dirs : {args.seed_dirs}")
    print(f"[export] folds: {args.folds}")

    all_rows = []

    for fold in args.folds:
        # Load all seeds for this fold
        per_seed = []
        for seed, sdir in zip(args.seeds, args.seed_dirs):
            try:
                d = load_seed_fold(sdir, fold, args.variant)
                per_seed.append(d)
            except FileNotFoundError as e:
                print(f"[export] WARNING fold {fold} seed {seed}: {e}")
        if not per_seed:
            print(f"[export] fold {fold}: NO seed data, skipping")
            continue

        # Sanity: timestamps + targets_normed must match across seeds
        ts0 = per_seed[0]["timestamps"]
        for s in per_seed[1:]:
            if not np.array_equal(s["timestamps"], ts0):
                raise ValueError(f"fold {fold}: timestamp mismatch across seeds")

        # Per-seed sigma (should be same since same fold + same training data)
        sigmas = [s["y_sigma"] for s in per_seed]
        sigma_med = float(np.median(sigmas))
        print(f"[export] fold {fold}: σ_train={sigma_med:.6e} (per-seed: {sigmas})")

        # Stack q50 z-scores across seeds: shape (n_seeds, N)
        q50_z_stack = np.stack([s["predictions"][:, 1] for s in per_seed], axis=0)
        # Median across seeds (value-blend, NOT rank)
        q50_z_med = np.median(q50_z_stack, axis=0)
        # Un-normalise
        q50_logret = q50_z_med * sigma_med  # back to log-return scale

        # Get RAW y_600 from data/npz_v4 by timestamp lookup
        timestamps_us = ts0
        y_raw = load_raw_y600_for_fold(args.raw_y_dir, timestamps_us)
        align_rate = float(np.mean(np.isfinite(y_raw)))
        print(f"[export] fold {fold}: raw y_600 align rate={align_rate:.4f} ({np.isfinite(y_raw).sum()}/{len(y_raw)})")

        mask = per_seed[0]["mask"].astype(np.int8)
        # Combined valid mask: original mask AND raw y available
        mask_combined = (mask == 1) & np.isfinite(y_raw)
        mask_int = mask_combined.astype(np.int8)

        dt = pd.to_datetime(timestamps_us, unit="us", utc=True)
        df = pd.DataFrame({
            "timestamp_us": timestamps_us,
            "datetime_utc": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fold": np.int8(fold),
            "horizon_sec": np.int32(600),
            "mask": mask_int,
            "y_true_logret": y_raw,
            "y_true_bps": y_raw * 1e4,
            "y_pred_q50_logret": q50_logret,
            "y_pred_q50_bps": q50_logret * 1e4,
            "y_pred_q50_z": q50_z_med.astype(np.float32),
            "y_sigma_train_bps": np.float32(sigma_med * 1e4),
        })
        all_rows.append(df)

    combined = pd.concat(all_rows, ignore_index=True)
    combined = combined.sort_values("timestamp_us").reset_index(drop=True)
    n_valid = int(combined["mask"].sum())
    print(f"[export] total rows: {len(combined)}, valid: {n_valid}")

    combined.to_csv(out_path, index=False, float_format="%.6e")
    print(f"[export] written: {out_path}")

    # Manifest
    manifest = out_path.with_suffix(".manifest.txt")
    with manifest.open("w") as f:
        f.write(f"# y_600 multi-seed median-blend predictions\n")
        f.write(f"# Created: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"# Variant: {args.variant}\n")
        f.write(f"# Seeds: {args.seeds}\n")
        f.write(f"# Seed dirs:\n")
        for s, d in zip(args.seeds, args.seed_dirs):
            f.write(f"#   seed={s}: {d}\n")
        f.write(f"# Folds: {args.folds}\n")
        f.write(f"# Blend: VALUE median across seeds (NOT rank-blend, NOT z-score-rescaled)\n")
        f.write(f"# y_true: RAW y_600 from {args.raw_y_dir} (un-smoothed)\n")
        f.write(f"# Total rows: {len(combined)} valid: {n_valid}\n")
    print(f"[export] manifest: {manifest}")


if __name__ == "__main__":
    main()

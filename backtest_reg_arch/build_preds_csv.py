"""Step 1: Load 3 fold NPZs → de-normalize → causal EMA-demean → single CSV.

Mirrors the production inference pipeline (scripts/y600_live_calibrate.py +
the inference.py CSV writer) so backtest = production semantics.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

EVAL_DIR = Path("../exports/reg_arch_standalone_eval")
OUT_CSV = Path("predictions_all_folds.csv")

EMA_ALPHA = 0.01
EMA_WARMUP = 50


def causal_ema_demean(q50_bps: np.ndarray, alpha=EMA_ALPHA, warmup=EMA_WARMUP):
    n = len(q50_bps)
    ema = np.zeros(n, dtype=np.float64)
    cur = 0.0
    for i in range(n):
        if i > 0:
            cur = alpha * q50_bps[i-1] + (1 - alpha) * cur
        ema[i] = cur
    demeaned = q50_bps - ema
    demeaned[:warmup] = 0.0
    return demeaned, ema


rows = []
for fold in [0, 1, 2]:
    z = np.load(EVAL_DIR / f"fold_{fold}_test_preds.npz", allow_pickle=True)
    preds_z = z["predictions"]            # (N, 3) z-space
    targets_z = z["targets"]              # (N,) z-space y_true
    mask = z["mask"]                      # (N,) bool
    ts_us = z["timestamps"]               # (N,) int64
    y_sigma = float(z["y_sigma"])         # scalar
    y_median = float(z["y_median"])

    # De-normalize: z * sigma + median → log return
    q_logret = preds_z * y_sigma + y_median
    y_logret = targets_z * y_sigma + y_median

    # Convert to bps
    q10_bps = q_logret[:, 0] * 1e4
    q50_bps = q_logret[:, 1] * 1e4
    q90_bps = q_logret[:, 2] * 1e4
    y_bps = y_logret * 1e4

    # Causal EMA-demean (live calibration) — applied per-fold (state resets each fold,
    # consistent with production inference where each fold owns its causal stream)
    q50_live, ema_state = causal_ema_demean(q50_bps)

    # Warmup flag
    warmup = np.zeros(len(q50_bps), dtype=bool)
    warmup[:EMA_WARMUP] = True

    sigma_train_bps = y_sigma * 1e4

    for i in range(len(q50_bps)):
        rows.append({
            "timestamp_us": int(ts_us[i]),
            "datetime_utc": datetime.fromtimestamp(ts_us[i] / 1e6, tz=timezone.utc).isoformat(),
            "fold": fold,
            "mask": int(mask[i]),
            "y_true_bps": float(y_bps[i]),
            "y_pred_q10_bps": float(q10_bps[i]),
            "y_pred_q50_bps": float(q50_bps[i]),
            "y_pred_q90_bps": float(q90_bps[i]),
            "y_pred_q50_bps_live": float(q50_live[i]),
            "y_sigma_train_bps": float(sigma_train_bps),
            "warmup": bool(warmup[i]),
        })

df = pd.DataFrame(rows).sort_values("timestamp_us").reset_index(drop=True)
df.to_csv(OUT_CSV, index=False)

print(f"Wrote {len(df)} rows → {OUT_CSV}")
print(f"Date range: {df['datetime_utc'].min()} → {df['datetime_utc'].max()}")
print(f"Folds: {sorted(df['fold'].unique())}")
print(f"Mean q50_live: {df['y_pred_q50_bps_live'].mean():+.4f}   "
      f"std: {df['y_pred_q50_bps_live'].std():.4f} bps")
print(f"Mean y_true:   {df['y_true_bps'].mean():+.4f}   "
      f"std: {df['y_true_bps'].std():.4f} bps")

# Sanity: pooled Pearson
valid = df[df["mask"].astype(bool) & ~df["warmup"]]
p = np.corrcoef(valid["y_pred_q50_bps_live"], valid["y_true_bps"])[0, 1]
print(f"\nValid (mask=1, post-warmup): {len(valid)} rows")
print(f"Pooled Pearson (q50_live, y_true): {p:+.4f}")

"""Phase #4: Causal EMA-demean using REALIZED y (not predicted ŷ).

Mechanism: at time t, EMA over y_600 values that are already realized
(s + 600s ≤ t). Strictly causal. With stride=180s, this means using
y_true[s] for s s.t. s + 600 ≤ ts[t], i.e., s ≤ t - 4 samples (since
stride 180 → 4 samples = 720s > 600s).

Output: new column `y_pred_q50_bps_actual_y_demean` = q50 - EMA(realized y).

Compared to existing `y_pred_q50_bps_live` (ŷ-EMA-demean):
- ŷ-EMA: tracks model's own DC drift (centers ŷ around 0)
- actual-y EMA: tracks ACTUAL market regime baseline (centers ŷ around recent realized y)

actual-y demean closer to true "regime-conditional alpha" view, since
trading goal is to predict ABOVE-baseline alpha where baseline = recent realized return.

Usage:
  python scripts/y600_actual_y_calibrate.py \
      --in-csv exports/v5_singh_alpha0_huber/y600_predictions_live.csv \
      --out-csv exports/v5_singh_alpha0_huber/y600_predictions_live_v2.csv \
      --alpha 0.01 --lag-samples 4
"""
from __future__ import annotations
import argparse
import pathlib

import numpy as np
import pandas as pd


def actual_y_ema_demean(
    yhat: np.ndarray,
    y_true: np.ndarray,
    mask: np.ndarray,
    lag_samples: int = 4,
    alpha: float = 0.01,
) -> tuple[np.ndarray, np.ndarray]:
    """Causal EMA over realized y_true with stride-aware lag.

    At sample t, ema[t] uses y_true[s] only for s ≤ t - lag_samples.
    This guarantees s + horizon ≤ t (s + 600s ≤ ts[t] when stride=180).

    Skips masked samples (mask=0) when accumulating EMA — prediction
    target wasn't realized so we shouldn't use it.

    Returns:
        (demeaned, ema_state) — both length-N arrays.
        demeaned = yhat - ema_state (subtract regime baseline).
    """
    n = len(yhat)
    ema = np.zeros(n, dtype=np.float64)
    cur_ema = None
    for t in range(n):
        if t >= lag_samples:
            src_idx = t - lag_samples
            if mask[src_idx]:
                if cur_ema is None:
                    cur_ema = float(y_true[src_idx])
                else:
                    cur_ema = (1.0 - alpha) * cur_ema + alpha * float(y_true[src_idx])
        if cur_ema is not None:
            ema[t] = cur_ema
        # else: ema stays 0 (cold start)
    return yhat - ema, ema


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-csv", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--lag-samples", type=int, default=4,
                    help="Strict-causal lag in samples (4 × stride 180s = 720s ≥ horizon 600s)")
    args = ap.parse_args()

    df = pd.read_csv(args.in_csv)
    df = df.sort_values(["fold", "timestamp_us"]).reset_index(drop=True)

    out_chunks = []
    for fid, sub in df.groupby("fold", sort=True):
        sub = sub.copy().reset_index(drop=True)
        yhat = sub["y_pred_q50_bps"].to_numpy()
        y_true = sub["y_true_bps"].to_numpy()
        mask = sub["mask"].to_numpy().astype(bool)
        demeaned, ema = actual_y_ema_demean(yhat, y_true, mask,
                                             lag_samples=args.lag_samples,
                                             alpha=args.alpha)
        sub["y_pred_q50_bps_actual_y_demean"] = demeaned
        sub["y_pred_q50_bps_actual_y_ema_state"] = ema
        # Mark warmup rows (first lag_samples + 50 samples for EMA convergence)
        warmup_n = args.lag_samples + 50
        sub["actual_y_warmup"] = False
        sub.loc[:warmup_n - 1, "actual_y_warmup"] = True
        out_chunks.append(sub)

    out = pd.concat(out_chunks, ignore_index=True)
    out_path = pathlib.Path(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, float_format="%.6e")
    print(f"→ {out_path}")
    print(f"  rows={len(out)} valid={(out['mask']==1).sum()} actual_y_warmup={out['actual_y_warmup'].sum()}")
    print(f"  alpha={args.alpha}, lag_samples={args.lag_samples} (= {args.lag_samples * 180}s ≥ horizon 600s)")


if __name__ == "__main__":
    main()

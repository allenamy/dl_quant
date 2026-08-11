"""Causal rolling-EMA demean for V5 singh α=0+Huber predictions.

Mimics live-trading drift correction: at every timestamp t, subtract
EMA(y_pred over t-1, t-2, ...). Strictly causal — uses only past
predictions, no fold-level mean leak.

Per-fold EMA reset (each fold corresponds to a different model checkpoint
deployed at retraining, so EMA state resets when checkpoint changes).

Output:
  - y_pred_q50_bps_live           : raw - EMA (live trading signal)
  - y_pred_q50_bps_live_ema_state : EMA value at each t (transparency)
  - warmup                        : True for first ALPHA_WARMUP samples per fold

Usage:
  python scripts/y600_live_calibrate.py \
      --in-csv  exports/v5_singh_alpha0_huber/y600_predictions_all_folds.csv \
      --out-csv exports/v5_singh_alpha0_huber/y600_predictions_live.csv \
      --alpha 0.01 --warmup 50
"""
from __future__ import annotations
import argparse
import pathlib
import numpy as np
import pandas as pd


def causal_ema_demean(yhat: np.ndarray, alpha: float = 0.01) -> tuple[np.ndarray, np.ndarray]:
    """Causal EMA-demean.

    ema[t] = (1-α)·ema[t-1] + α·yhat[t-1]   (note: yhat[t-1], NOT yhat[t])
    output[t] = yhat[t] - ema[t]

    ema[0] is initialized to yhat[0] (effectively output[0]=0; alternative
    is to leave ema[0]=0, then output[0]=yhat[0] which is uncalibrated).
    We choose ema[0]=yhat[0] for cleaner first-step behavior.

    Returns:
        demeaned, ema_state
    """
    n = len(yhat)
    ema = np.empty(n, dtype=np.float64)
    ema[0] = float(yhat[0])
    for t in range(1, n):
        ema[t] = (1.0 - alpha) * ema[t - 1] + alpha * float(yhat[t - 1])
    return yhat - ema, ema


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-csv", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--alpha", type=float, default=0.01,
                    help="EMA smoothing factor; HL ≈ ln(0.5)/ln(1-α). α=0.01 ≈ 69 samples HL ≈ 11.5h at 600s sample rate")
    ap.add_argument("--warmup", type=int, default=50,
                    help="number of leading samples flagged warmup=True per fold")
    args = ap.parse_args()

    df = pd.read_csv(args.in_csv)
    df = df.sort_values(["fold", "timestamp_us"]).reset_index(drop=True)

    out_chunks = []
    for fid, sub in df.groupby("fold", sort=True):
        sub = sub.copy().reset_index(drop=True)
        yhat = sub["y_pred_q50_bps"].to_numpy()
        demeaned, ema = causal_ema_demean(yhat, alpha=args.alpha)
        sub["y_pred_q50_bps_live"] = demeaned
        sub["y_pred_q50_bps_live_ema_state"] = ema
        sub["warmup"] = False
        sub.loc[: args.warmup - 1, "warmup"] = True
        out_chunks.append(sub)

    out = pd.concat(out_chunks, ignore_index=True)
    out_path = pathlib.Path(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, float_format="%.6e")
    print(f"→ {out_path}")
    print(f"  rows={len(out)} valid={(out['mask']==1).sum()} warmup={out['warmup'].sum()}")
    print(f"  alpha={args.alpha} (HL ≈ {np.log(0.5)/np.log(1-args.alpha):.1f} samples ≈ {np.log(0.5)/np.log(1-args.alpha)*600/3600:.1f}h)")


if __name__ == "__main__":
    main()

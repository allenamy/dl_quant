"""Export y_600 final_stack predictions to CSV for external backtest.

Packages predictions with timestamps from experiments/y600_push/final_stack/
into timestamp-keyed CSV files suitable for third-party backtesting.

Output per-fold CSV + one combined all-folds CSV (fold column identifies).

Columns:
  timestamp_us       : int64, microseconds since Unix epoch (UTC)
  datetime_utc       : ISO-8601 datetime string
  fold               : 0/1/2 (walk-forward fold id)
  horizon_sec        : 600
  mask               : 1 if valid target, 0 if masked out
  y_true_logret      : actual 600s forward log-return (un-normalised)
  y_true_bps         : y_true_logret * 1e4
  y_pred_q10_logret  : predicted 10th-percentile log-return
  y_pred_q50_logret  : predicted median log-return (point estimate)
  y_pred_q90_logret  : predicted 90th-percentile log-return
  y_pred_q50_bps     : y_pred_q50_logret * 1e4 (for trading convenience)
  y_pred_q50_z       : z-scored q50 (what the model directly outputs)
  y_sigma_train_bps  : train MAD-sigma used for z-scoring, in bps

Anchor semantics: timestamp_us = end of 600-step input window.
Target = log(mid[t+600s] / mid[t]) where t = timestamp_us.
"""
from __future__ import annotations

import argparse
import pathlib

import numpy as np
import pandas as pd


DEFAULT_SRC = pathlib.Path("experiments/y600_push/final_stack")
DEFAULT_OUT = pathlib.Path("experiments/y600_push/final_stack/exports")


def load_fold(src_dir: pathlib.Path, fold: int) -> pd.DataFrame:
    p = src_dir / f"fold_{fold}" / "test_preds.npz"
    d = np.load(p)

    ts_us = d["timestamps"].astype(np.int64)
    mask = d["mask"].astype(np.int8)
    y_z = d["targets"].astype(np.float32).squeeze()
    yp_z = d["predictions"].astype(np.float32)
    q10_z, q50_z, q90_z = yp_z[:, 0], yp_z[:, 1], yp_z[:, 2]
    sigma = float(d["y_sigma"])
    median = float(d["y_median"])

    # Un-normalise: the dataset did (y - median) / sigma, so raw = z * sigma + median
    y_true = y_z * sigma + median
    q10 = q10_z * sigma + median
    q50 = q50_z * sigma + median
    q90 = q90_z * sigma + median

    dt = pd.to_datetime(ts_us, unit="us", utc=True)
    df = pd.DataFrame(
        {
            "timestamp_us": ts_us,
            "datetime_utc": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fold": np.int8(fold),
            "horizon_sec": np.int32(600),
            "mask": mask,
            "y_true_logret": y_true,
            "y_true_bps": y_true * 1e4,
            "y_pred_q10_logret": q10,
            "y_pred_q50_logret": q50,
            "y_pred_q90_logret": q90,
            "y_pred_q50_bps": q50 * 1e4,
            "y_pred_q50_z": q50_z,
            "y_sigma_train_bps": np.float32(sigma * 1e4),
        }
    )
    return df.sort_values("timestamp_us").reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src-dir", type=pathlib.Path, default=DEFAULT_SRC)
    ap.add_argument("--out-dir", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument("--folds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--dedup-mode", choices=["earliest_fold", "latest_fold", "none"],
                    default="earliest_fold",
                    help="How to resolve overlapping timestamps across folds in the "
                         "combined CSV. 'earliest_fold' keeps the prediction from the "
                         "first fold a timestamp appears in (most OOS honest).")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for f in args.folds:
        df = load_fold(args.src_dir, f)
        out_csv = args.out_dir / f"y600_predictions_fold_{f}.csv"
        df.to_csv(out_csv, index=False, float_format="%.6e")
        print(f"fold {f}: N={len(df)} valid={int(df['mask'].sum())} "
              f"range=[{df['datetime_utc'].iloc[0]}, {df['datetime_utc'].iloc[-1]}] "
              f"→ {out_csv}")
        frames.append(df)

    # Combined all-folds
    combined = pd.concat(frames, ignore_index=True)
    before_dedup = len(combined)
    if args.dedup_mode == "earliest_fold":
        combined = combined.sort_values(["timestamp_us", "fold"]).drop_duplicates(
            "timestamp_us", keep="first"
        ).reset_index(drop=True)
    elif args.dedup_mode == "latest_fold":
        combined = combined.sort_values(["timestamp_us", "fold"]).drop_duplicates(
            "timestamp_us", keep="last"
        ).reset_index(drop=True)
    else:
        combined = combined.sort_values(["timestamp_us", "fold"]).reset_index(drop=True)
    after_dedup = len(combined)

    out_combined = args.out_dir / "y600_predictions_all_folds.csv"
    combined.to_csv(out_combined, index=False, float_format="%.6e")
    print(f"\ncombined: {before_dedup} rows → {after_dedup} after {args.dedup_mode} dedup")
    print(f"covered range: [{combined['datetime_utc'].iloc[0]}, "
          f"{combined['datetime_utc'].iloc[-1]}]")
    print(f"→ {out_combined}")

    # Manifest / README for colleague
    manifest = args.out_dir / "README.md"
    with open(manifest, "w") as f:
        f.write(
            "# V4 y_600 final_stack predictions — export for backtest\n\n"
            "**Model:** V4 DualPathLOBModelV3 final_stack = 0.5 × SWA(top-5) + 0.5 × EMA(Polyak 0.999) blend.\n"
            "**Horizon:** 600 seconds (10 minutes) forward log-return.\n"
            "**Symbol:** BTCUSDT Binance futures perpetual.\n"
            "**Walk-forward:** 700d train / 30d val / 90d test, 3 folds, stride 60d.\n\n"
            "## Files\n\n"
            "| File | Content |\n"
            "|---|---|\n"
            "| `y600_predictions_fold_{0,1,2}.csv` | Per-fold test-set predictions (strict OOS). |\n"
            "| `y600_predictions_all_folds.csv` | Combined timeline with overlap resolved by `earliest_fold` (keeps the OOS-honest first-seen prediction). |\n\n"
            "## Columns\n\n"
            "- `timestamp_us` — int64 UTC microseconds; **end** of the 600-step input window.\n"
            "- `datetime_utc` — ISO-8601 for convenience.\n"
            "- `fold` — 0/1/2. Test periods: fold 0 = 2025-01-08 … 2025-04-08; fold 1 ≈ 2025-03-10 … 2025-06-07; fold 2 ≈ 2025-05-11 … 2025-08-07.\n"
            "- `mask` — 1 if the forward-return window was fully observed; 0 if masked (missing mid-price).\n"
            "- `y_true_logret` / `y_true_bps` — realised 600s forward log-return.\n"
            "- `y_pred_q10/q50/q90_logret` — predicted 10/50/90 percentiles of forward return distribution (monotonic by construction).\n"
            "- `y_pred_q50_bps` — q50 in bps (×1e4) for trading convenience.\n"
            "- `y_pred_q50_z` — the raw z-scored output of the model.\n"
            "- `y_sigma_train_bps` — train-set MAD-sigma in bps (per-fold); multiply z-scores by (`y_sigma_train_bps` × 1e-4) to un-normalise, or re-z-score.\n\n"
            "## Backtest semantics\n\n"
            "- Target at `t` = `log(mid[t + 600s] / mid[t])`. Signal known at `t`.\n"
            "- **Position entry** should be at `t` (anchor = end of input window).\n"
            "- **Position exit** at `t + 600s` (for pure signal P&L). Hold longer with your own strategy overlay (e.g. EMA smoothing, hysteresis, min-hold).\n"
            "- Filter: use rows with `mask == 1` only.\n\n"
            "## Pooled-clean metrics for sanity check\n\n"
            "- Pearson ≈ 0.054–0.074 (95% CI [0.030, 0.090])\n"
            "- Spearman ≈ 0.056–0.087 (95% CI [0.022, 0.089])\n"
            "- DirAcc ≈ 0.52–0.54 on stride-10 clean subsample.\n\n"
            "## Cost economics (heads-up)\n\n"
            "Single-asset BTC y_600 IC is ~0.06. At 2 bps/trade round-trip, always-trade ≈ −6.5 Sharpe; best holding strategy (EMA=20, hold=30 samples) is near break-even (Sharpe −0.21). **Production requires breadth (multi-asset) or maker-only orders.**\n"
        )
    print(f"→ {manifest}")


if __name__ == "__main__":
    main()

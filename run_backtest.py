"""Run backtest on trained model predictions.

Usage:
    # From saved predictions NPZ
    python run_backtest.py --predictions experiments/fold_0/test_preds.npz

    # From model + test data
    python run_backtest.py --model experiments/fold_0/best_model.pt \\
                           --norm-params experiments/fold_0/norm_params.npz \\
                           --test-data data/npz_h180_s60 \\
                           --test-days 2026-02-01,2026-02-02

    # With custom backtest parameters
    python run_backtest.py --predictions test_preds.npz \\
                           --fee-bps 6.0 --slippage-bps 2.0 \\
                           --threshold 0.05 --no-confidence-sizing

Steps:
    1. Load model and test data (or pre-computed predictions)
    2. Run inference if needed
    3. De-normalize predictions back to raw return units
    4. Run BacktestEngine with configurable parameters
    5. Print summary, save results JSON + trade log CSV
    6. Run threshold analysis
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def detect_device() -> str:
    """Auto-detect best available device: cuda > mps > cpu."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def load_predictions_from_npz(path: str) -> dict:
    """Load pre-computed predictions from an NPZ file.

    Expected keys:
      predictions -- (N, 3) quantile predictions [q10, q50, q90]
      targets     -- (N,) realized returns
      mask        -- (N,) boolean mask
      timestamps  -- (N,) microsecond timestamps (optional)
      y_sigma     -- scalar, target normalization scale (optional)
      y_median    -- scalar, target normalization offset (optional)
    """
    npz = np.load(path, allow_pickle=True)
    result = {
        "predictions": npz["predictions"],
        "targets": npz["targets"],
        "mask": npz["mask"],
    }
    if "timestamps" in npz.files:
        result["timestamps"] = npz["timestamps"]
    if "y_sigma" in npz.files:
        result["y_sigma"] = float(npz["y_sigma"])
    if "y_median" in npz.files:
        result["y_median"] = float(npz["y_median"])
    return result


def run_inference(
    model_path: str,
    norm_params_path: str,
    test_data_dir: str,
    test_days: list,
    device: str,
) -> dict:
    """Run model inference on test data, return predictions dict.

    Returns same format as load_predictions_from_npz.
    """
    import torch
    from src.training.dataset import LOBDatasetV2, LOBDataset
    from torch.utils.data import DataLoader

    # Load normalization params
    norm = np.load(norm_params_path, allow_pickle=True)
    x_mean = norm["x_mean"]
    x_std = norm["x_std"]
    y_sigma = float(norm["y_sigma"]) if "y_sigma" in norm.files else 1.0
    y_median = float(norm["y_median"]) if "y_median" in norm.files else 0.0

    # Try V2 dataset first, fall back to V1
    try:
        test_ds = LOBDatasetV2(
            test_data_dir, test_days,
            normalize=True, x_mean=x_mean, x_std=x_std,
        )
        dual_path = test_ds.has_raw
    except Exception:
        test_ds = LOBDataset(
            test_data_dir, test_days,
            normalize=True, x_mean=x_mean, x_std=x_std,
        )
        dual_path = False

    # Load model
    device_obj = torch.device(device)

    # Auto-detect model class from checkpoint
    ckpt = torch.load(model_path, map_location=device_obj, weights_only=True)

    # Detect model architecture from state dict keys
    state_keys = set(ckpt.keys())
    if any("path_a" in k or "path_b" in k for k in state_keys):
        from src.model.dual_path_model import DualPathLOBModelV2
        n_features = test_ds.X.shape[-1]
        n_levels = test_ds.X_raw.shape[-2] if dual_path else 20
        model = DualPathLOBModelV2(n_features=n_features, n_levels=n_levels)
    elif any("raw_lob" in k for k in state_keys):
        from src.model.dual_path_model import DualPathLOBModel
        n_features = test_ds.X.shape[-1]
        n_levels = test_ds.X_raw.shape[-2] if dual_path else 20
        model = DualPathLOBModel(n_features=n_features, n_levels=n_levels)
    else:
        from src.model.lob_transformer import LOBTransformerV2
        n_features = test_ds.X.shape[-1]
        model = LOBTransformerV2(n_features=n_features)

    model.load_state_dict(ckpt)
    model.to(device_obj)
    model.eval()

    test_loader = DataLoader(test_ds, batch_size=64, shuffle=False)

    all_pred = []
    all_quantiles = []
    all_target = []
    all_mask = []

    with torch.no_grad():
        for batch in test_loader:
            if dual_path and len(batch) == 4:
                x_feat, x_raw, y, m = batch
                x_feat = x_feat.to(device_obj)
                x_raw = x_raw.to(device_obj)
                outputs = model(x_feat, x_raw)
            else:
                x_feat, y, m = batch[:3]
                x_feat = x_feat.to(device_obj)
                outputs = model(x_feat)

            all_quantiles.append(outputs["quantiles"].cpu().numpy())
            all_target.append(y.numpy())
            all_mask.append(m.numpy())

    predictions = np.concatenate(all_quantiles)  # (N, 3)
    targets = np.concatenate(all_target)
    mask = np.concatenate(all_mask)

    return {
        "predictions": predictions,
        "targets": targets,
        "mask": mask,
        "y_sigma": y_sigma,
        "y_median": y_median,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run backtest on model predictions"
    )

    # Input source (either pre-computed or model+data)
    parser.add_argument(
        "--predictions",
        help="Path to pre-computed predictions NPZ file",
    )
    parser.add_argument("--model", help="Path to model checkpoint (.pt)")
    parser.add_argument("--norm-params", help="Path to norm_params.npz")
    parser.add_argument("--test-data", help="Path to NPZ data directory")
    parser.add_argument(
        "--test-days",
        help="Comma-separated list of test day identifiers",
    )

    # De-normalization
    parser.add_argument(
        "--y-sigma", type=float, default=None,
        help="Target normalization scale (overrides NPZ value)",
    )
    parser.add_argument(
        "--y-median", type=float, default=None,
        help="Target normalization offset (overrides NPZ value)",
    )

    # Backtest parameters
    parser.add_argument("--fee-bps", type=float, default=4.0)
    parser.add_argument("--slippage-bps", type=float, default=1.0)
    parser.add_argument("--threshold", type=float, default=0.0)
    parser.add_argument("--max-position", type=float, default=1.0)
    parser.add_argument(
        "--no-confidence-sizing", action="store_true",
        help="Use binary positions instead of confidence sizing",
    )

    # Output
    parser.add_argument(
        "--output-dir", default=None,
        help="Directory for results (default: same as predictions file or model dir)",
    )
    parser.add_argument(
        "--skip-threshold-search", action="store_true",
        help="Skip threshold optimization analysis",
    )

    args = parser.parse_args()

    # --- Validate inputs ---
    if args.predictions is None and args.model is None:
        parser.error("Must provide either --predictions or --model")
    if args.model and not args.norm_params:
        parser.error("--norm-params is required when using --model")
    if args.model and not args.test_data:
        parser.error("--test-data is required when using --model")
    if args.model and not args.test_days:
        parser.error("--test-days is required when using --model")

    # --- Load or compute predictions ---
    if args.predictions:
        print(f"[backtest] Loading predictions from {args.predictions}")
        data = load_predictions_from_npz(args.predictions)
        output_dir = args.output_dir or str(
            Path(args.predictions).parent
        )
    else:
        print(f"[backtest] Running inference: model={args.model}")
        device = detect_device()
        print(f"[backtest] Device: {device}")
        test_days = [d.strip() for d in args.test_days.split(",")]
        data = run_inference(
            args.model,
            args.norm_params,
            args.test_data,
            test_days,
            device,
        )
        output_dir = args.output_dir or str(Path(args.model).parent)

    predictions = data["predictions"]  # (N, 3) normalized
    targets = data["targets"]          # (N,)   normalized
    mask = data["mask"]                # (N,)
    timestamps = data.get("timestamps")

    y_sigma = args.y_sigma or data.get("y_sigma", 1.0)
    y_median = args.y_median or data.get("y_median", 0.0)

    print(f"[backtest] Data: {predictions.shape[0]} periods, "
          f"{int(np.sum(mask))} valid")
    print(f"[backtest] De-normalization: y_sigma={y_sigma:.6f}, "
          f"y_median={y_median:.6f}")

    # --- De-normalize predictions to raw return units ---
    # The model outputs normalized values; convert to raw returns for
    # realistic cost modeling (fees are in bps of raw returns).
    preds_raw = predictions * y_sigma + y_median
    targets_raw = targets * y_sigma + y_median

    # --- Run backtest ---
    from src.evaluation.backtest_v2 import BacktestEngine

    engine = BacktestEngine(
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        max_position=args.max_position,
        signal_threshold=args.threshold,
        confidence_sizing=not args.no_confidence_sizing,
    )

    result = engine.run(
        predictions=preds_raw,
        targets=targets_raw,
        mask=mask.astype(bool),
        timestamps=timestamps,
    )

    # --- Print summary ---
    print(result.summary())

    # --- Save results ---
    os.makedirs(output_dir, exist_ok=True)

    results_path = os.path.join(output_dir, "backtest_results.json")
    result_dict = result.to_dict()
    result_dict["parameters"] = {
        "fee_bps": args.fee_bps,
        "slippage_bps": args.slippage_bps,
        "threshold": args.threshold,
        "max_position": args.max_position,
        "confidence_sizing": not args.no_confidence_sizing,
        "y_sigma": y_sigma,
        "y_median": y_median,
    }
    with open(results_path, "w") as f:
        json.dump(result_dict, f, indent=2, default=str)
    print(f"[backtest] Results saved to {results_path}")

    # Trade log
    if len(result.trade_log) > 0:
        trade_log_path = os.path.join(output_dir, "trade_log.csv")
        result.trade_log.to_csv(trade_log_path, index=False)
        print(f"[backtest] Trade log saved to {trade_log_path} "
              f"({len(result.trade_log)} entries)")

    # --- Threshold analysis ---
    if not args.skip_threshold_search:
        print("\n[backtest] Running threshold analysis...")
        from src.evaluation.backtest_analysis import optimal_threshold_search

        threshold_results = optimal_threshold_search(
            predictions=preds_raw,
            targets=targets_raw,
            mask=mask.astype(bool),
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
        )

        print(f"\n  WARNING: Threshold analysis is for diagnostic purposes ONLY.")
        print(f"  In-sample optimization leads to overfitting.")
        print(f"  Always validate on held-out data.\n")
        print(f"  Best threshold: {threshold_results['best_threshold']:.4f}")
        print(f"  Best Sharpe:    {threshold_results['best_sharpe']:.4f}")
        print(f"  Best Net P&L:   {threshold_results['best_net_pnl']:.4f}")
        print()
        print(threshold_results["results_df"].to_string(index=False))

        # Save threshold analysis
        thresh_path = os.path.join(output_dir, "threshold_analysis.csv")
        threshold_results["results_df"].to_csv(thresh_path, index=False)
        print(f"\n[backtest] Threshold analysis saved to {thresh_path}")

    print("\n[backtest] Done.")


if __name__ == "__main__":
    main()

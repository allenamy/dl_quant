"""DEPRECATED: End-to-end pipeline for the legacy LOBTransformerV2.

This pipeline trains the OLD ``LOBTransformerV2`` (regime-aware feature gate,
multi-task loss).  It is preserved for reference and backward compatibility
only; all current work should use ``run_pipeline_v3.py`` which trains the
DualPathLOBModelV3 (MaskNet + GDCN + RawLOBEncoder + Patched Attention).

Steps:
    1. Feature engineering: CSV -> NPZ sliding-window datasets
    2. Single-day or multi-day training with temporal splits
    3. Evaluation: metrics + backtest on held-out test set

STATUS: DEPRECATED -- kept for reference; do NOT extend.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
from src.features.pipeline import process_csv_to_npz
from src.model.lob_transformer import LOBTransformerV2
from src.training.dataset import LOBDataset, build_time_series_folds
from src.training.trainer import train_one_fold
from src.evaluation.metrics import evaluate_predictions
from src.evaluation.backtest import backtest_signal
from src.features.feature_groups import get_feature_group_indices


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _configure_feature_groups(model: LOBTransformerV2, npz_dir: str) -> None:
    """Set semantic feature groups on the model's spatial encoder.

    Reads feature names from the first NPZ file in *npz_dir* and maps them
    to bid/ask/global index groups.  If no NPZ files exist or the file
    lacks a ``features`` array, this is a silent no-op.
    """
    npz_files = sorted(Path(npz_dir).glob("*.npz"))
    if not npz_files:
        return
    npz_sample = np.load(npz_files[0], allow_pickle=True)
    raw_features = npz_sample.get("features", None)
    if raw_features is None or len(raw_features) == 0:
        return
    feature_names = [str(f) for f in raw_features]
    groups = get_feature_group_indices(feature_names)
    if groups["bid_idx"] and groups["ask_idx"] and groups["global_idx"]:
        model.spatial_encoder.set_feature_groups(
            bid_idx=groups["bid_idx"],
            ask_idx=groups["ask_idx"],
            global_idx=groups["global_idx"],
        )
        print(
            f"[pipeline] Semantic feature groups: "
            f"bid={len(groups['bid_idx'])}, "
            f"ask={len(groups['ask_idx'])}, "
            f"global={len(groups['global_idx'])}"
        )


def detect_device() -> str:
    """Auto-detect best available device: cuda > mps > cpu."""
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class SlicedDataset(Dataset):
    """Thin wrapper that exposes a contiguous slice of numpy arrays as a Dataset.

    This avoids copying data -- it simply indexes into the parent arrays.
    """

    def __init__(self, X: np.ndarray, y: np.ndarray, mask: np.ndarray) -> None:
        self.X = X
        self.y = y
        self.mask = mask

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int):
        x = torch.FloatTensor(self.X[idx].tolist())
        y_val = torch.tensor(float(self.y[idx]))
        m = torch.tensor(float(self.mask[idx]))
        return (x, y_val, m)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LOB Transformer V2 end-to-end pipeline")
    parser.add_argument("--config", default="configs/default.json", help="Path to config JSON")
    parser.add_argument("--skip-features", action="store_true", help="Skip feature engineering step")
    args = parser.parse_args()

    # --- Load config ---------------------------------------------------------
    with open(args.config, "r") as f:
        cfg = json.load(f)

    data_cfg = cfg["data"]
    model_cfg = cfg["model"]
    train_cfg = cfg["training"]
    output_dir = cfg["output_dir"]

    # --- Device --------------------------------------------------------------
    device = detect_device()
    print(f"[pipeline] Device: {device}")

    # =========================================================================
    # Step 1: Feature engineering (CSV -> NPZ)
    # =========================================================================
    npz_dir = data_cfg["npz_dir"]

    if not args.skip_features:
        print(f"[pipeline] Processing {data_cfg['csv_path']} -> {npz_dir}")
        saved = process_csv_to_npz(
            csv_path=data_cfg["csv_path"],
            output_dir=npz_dir,
            horizon_sec=data_cfg["horizon_sec"],
            input_len=data_cfg["input_len"],
            stride=data_cfg["stride"],
            n_levels=data_cfg["n_levels"],
        )
        for p in saved:
            d = np.load(p, allow_pickle=True)
            print(f"  {p.name}: X={d['X'].shape}  y={d['y'].shape}  mask_sum={d['y_mask'].sum()}")
    else:
        print("[pipeline] Skipping feature engineering (--skip-features)")

    # =========================================================================
    # Step 2: Discover available days
    # =========================================================================
    npz_files = sorted(Path(npz_dir).glob("*.npz"))
    days = [f.stem for f in npz_files]
    print(f"[pipeline] Found {len(days)} day(s): {days}")

    if len(days) == 0:
        print("[pipeline] ERROR: No NPZ files found. Run without --skip-features first.")
        sys.exit(1)

    # =========================================================================
    # Step 3: Training -- single-day vs multi-day
    # =========================================================================
    fold_window = train_cfg["train_days"] + train_cfg["val_days"] + train_cfg["test_days"]

    if len(days) >= fold_window:
        # ----- Multi-day mode: use build_time_series_folds --------------------
        print(f"[pipeline] Multi-day mode ({len(days)} days)")
        folds = build_time_series_folds(
            days,
            train_days=train_cfg["train_days"],
            val_days=train_cfg["val_days"],
            test_days=train_cfg["test_days"],
            stride=train_cfg["fold_stride"],
        )
        print(f"[pipeline] Built {len(folds)} fold(s)")

        for fold_idx, fold in enumerate(folds):
            fold_dir = os.path.join(output_dir, f"fold_{fold_idx}")
            print(f"\n{'='*60}")
            print(f"[pipeline] Fold {fold_idx}: train={fold['train']} val={fold['val']} test={fold['test']}")
            print(f"{'='*60}")

            # Build datasets
            train_ds = LOBDataset(npz_dir, fold["train"], normalize=False)
            x_mean, x_std = train_ds.compute_stats()

            train_ds = LOBDataset(npz_dir, fold["train"], normalize=True, x_mean=x_mean, x_std=x_std)
            val_ds = LOBDataset(npz_dir, fold["val"], normalize=True, x_mean=x_mean, x_std=x_std)
            test_ds = LOBDataset(npz_dir, fold["test"], normalize=True, x_mean=x_mean, x_std=x_std)

            n_features = train_ds.X.shape[-1]
            model = LOBTransformerV2(
                n_features=n_features,
                **model_cfg,
            )
            _configure_feature_groups(model, npz_dir)

            best = train_one_fold(
                model=model,
                train_dataset=train_ds,
                val_dataset=val_ds,
                out_dir=fold_dir,
                device=device,
                epochs=train_cfg["epochs"],
                batch_size=train_cfg["batch_size"],
                lr=train_cfg["lr"],
                weight_decay=train_cfg["weight_decay"],
                patience=train_cfg["patience"],
                grad_clip=train_cfg["grad_clip"],
                warmup_epochs=train_cfg["warmup_epochs"],
            )
            print(f"[pipeline] Fold {fold_idx} best: {best}")

            # Save normalization params
            np.savez(
                os.path.join(fold_dir, "norm_params.npz"),
                x_mean=x_mean,
                x_std=x_std,
            )

            # --- Test evaluation ---
            _run_test_evaluation(model, fold_dir, test_ds, train_cfg, device)

    else:
        # ----- Single-day mode ------------------------------------------------
        print(f"[pipeline] Single-day mode (only {len(days)} day(s), need {fold_window} for multi-day)")
        fold_dir = os.path.join(output_dir, "fold_0")
        os.makedirs(fold_dir, exist_ok=True)

        # Load full dataset (un-normalized) to compute stats
        full_ds = LOBDataset(npz_dir, days, normalize=False)
        x_mean, x_std = full_ds.compute_stats()

        n_total = len(full_ds)
        n_train = int(n_total * 0.70)
        n_val = int(n_total * 0.15)
        n_test = n_total - n_train - n_val

        print(f"[pipeline] Total windows: {n_total} -> train={n_train}, val={n_val}, test={n_test}")

        # Normalize full arrays
        X_norm = (full_ds.X - x_mean) / (x_std + 1e-8)
        X_norm = np.clip(X_norm, -10.0, 10.0)
        mask_all = full_ds.mask

        # Normalize targets by robust sigma (MAD) from training portion
        y_raw = full_ds.y
        y_train_valid = y_raw[:n_train][mask_all[:n_train] > 0]
        y_median = float(np.median(y_train_valid))
        y_mad = float(np.median(np.abs(y_train_valid - y_median)))
        y_sigma = max(1.4826 * y_mad, 1e-9)
        print(f"[pipeline] Target normalization: median={y_median:.6f}, sigma={y_sigma:.6f}")
        y_all = (y_raw - y_median) / y_sigma
        # Clip extreme targets
        y_all = np.clip(y_all, -5.0, 5.0)

        # Temporal split (no shuffling)
        train_ds = SlicedDataset(
            X_norm[:n_train],
            y_all[:n_train],
            mask_all[:n_train],
        )
        val_ds = SlicedDataset(
            X_norm[n_train : n_train + n_val],
            y_all[n_train : n_train + n_val],
            mask_all[n_train : n_train + n_val],
        )
        test_ds = SlicedDataset(
            X_norm[n_train + n_val :],
            y_all[n_train + n_val :],
            mask_all[n_train + n_val :],
        )

        n_features = full_ds.X.shape[-1]
        print(f"[pipeline] n_features={n_features}")

        model = LOBTransformerV2(
            n_features=n_features,
            **model_cfg,
        )
        _configure_feature_groups(model, npz_dir)
        total_params = sum(p.numel() for p in model.parameters())
        print(f"[pipeline] Model parameters: {total_params:,}")

        best = train_one_fold(
            model=model,
            train_dataset=train_ds,
            val_dataset=val_ds,
            out_dir=fold_dir,
            device=device,
            epochs=train_cfg["epochs"],
            batch_size=train_cfg["batch_size"],
            lr=train_cfg["lr"],
            weight_decay=train_cfg["weight_decay"],
            patience=train_cfg["patience"],
            grad_clip=train_cfg["grad_clip"],
            warmup_epochs=train_cfg["warmup_epochs"],
        )
        print(f"[pipeline] Training best metrics: {best}")

        # Save normalization params
        np.savez(
            os.path.join(fold_dir, "norm_params.npz"),
            x_mean=x_mean,
            x_std=x_std,
            y_median=np.array(y_median),
            y_sigma=np.array(y_sigma),
        )

        # --- Test evaluation ---
        _run_test_evaluation(model, fold_dir, test_ds, train_cfg, device, y_sigma=y_sigma, y_median=y_median)

    print("\n[pipeline] All done.")


# ---------------------------------------------------------------------------
# Test evaluation helper
# ---------------------------------------------------------------------------

def _run_test_evaluation(
    model: torch.nn.Module,
    fold_dir: str,
    test_ds: Dataset,
    train_cfg: dict,
    device: str,
    y_sigma: float = 1.0,
    y_median: float = 0.0,
) -> None:
    """Load best model, run inference on test set, compute and print metrics."""
    device_obj = torch.device(device)

    # Load best checkpoint
    ckpt_path = os.path.join(fold_dir, "best_model.pt")
    model.load_state_dict(torch.load(ckpt_path, map_location=device_obj, weights_only=True))
    model.to(device_obj)
    model.eval()

    test_loader = DataLoader(
        test_ds,
        batch_size=train_cfg["batch_size"],
        shuffle=False,
    )

    all_pred = []
    all_target = []
    all_mask = []
    all_uncertainty = []
    all_quantiles = []

    with torch.no_grad():
        for x, y, mask in test_loader:
            x = x.to(device_obj)
            outputs = model(x)

            all_pred.append(outputs["point_pred"].cpu().numpy())
            all_target.append(y.numpy())
            all_mask.append(mask.numpy())
            all_uncertainty.append(outputs["uncertainty"].cpu().numpy())
            all_quantiles.append(outputs["quantiles"].cpu().numpy())

    pred = np.concatenate(all_pred)
    target = np.concatenate(all_target)
    mask = np.concatenate(all_mask)
    uncertainty = np.concatenate(all_uncertainty)
    quantiles_pred = np.concatenate(all_quantiles)

    # --- Evaluation metrics ---
    eval_metrics = evaluate_predictions(
        pred=pred,
        target=target,
        mask=mask,
        uncertainty=uncertainty,
        quantiles_pred=quantiles_pred,
    )

    # --- Backtest (de-normalize to raw fractional returns for proper thresholding) ---
    pred_raw = pred * y_sigma + y_median
    target_raw = target * y_sigma + y_median
    bt_metrics = backtest_signal(
        pred=pred_raw,
        target=target_raw,
        mask=mask,
    )

    # --- Print comprehensive results ---
    print(f"\n{'='*60}")
    print("TEST RESULTS")
    print(f"{'='*60}")
    print(f"  Correlation:        {eval_metrics.get('correlation', float('nan')):.6f}")
    print(f"  R2:                 {eval_metrics.get('r2', float('nan')):.6f}")
    print(f"  Direction accuracy: {eval_metrics.get('direction_accuracy', float('nan')):.4f}")
    print(f"  Residual autocorr:  {eval_metrics.get('residual_autocorr_lag1', float('nan')):.4f}")
    print(f"  Left tail bias:     {eval_metrics.get('left_tail_bias', float('nan')):.6f}")
    print(f"  Score (bps):        {eval_metrics.get('score_bps', float('nan')):.4f}")
    print(f"  ---")
    print(f"  Net PnL (bps):      {bt_metrics.get('net_pnl_bps', float('nan')):.4f}")
    print(f"  Sharpe (annual):    {bt_metrics.get('sharpe_annual', float('nan')):.4f}")
    print(f"  Win rate:           {bt_metrics.get('win_rate', float('nan')):.4f}")
    print(f"  Max drawdown (bps): {bt_metrics.get('max_drawdown_bps', float('nan')):.4f}")
    print(f"  Trades:             {bt_metrics.get('n_trades', 0)}")
    print(f"{'='*60}")

    # --- Save results ---
    # Combine all metrics (convert numpy types to python floats for JSON)
    all_metrics = {"evaluation": {}, "backtest": {}}
    for k, v in eval_metrics.items():
        if isinstance(v, (np.floating, np.integer)):
            all_metrics["evaluation"][k] = float(v)
        else:
            all_metrics["evaluation"][k] = v
    for k, v in bt_metrics.items():
        if isinstance(v, (np.floating, np.integer)):
            all_metrics["backtest"][k] = float(v)
        else:
            all_metrics["backtest"][k] = v

    results_path = os.path.join(fold_dir, "test_results.json")
    with open(results_path, "w") as f:
        json.dump(all_metrics, f, indent=2, default=str)
    print(f"[pipeline] Test results saved to {results_path}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()

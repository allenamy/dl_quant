"""End-to-end pipeline for the V3 dual-path model (MaskNet+GDCN+RawLOB+PatchAttn).

Replaces the deprecated ``run_pipeline.py``.  This version:
  - Uses ``src.features.pipeline.process_csv_to_npz`` (already dual-path).
  - Uses ``src.training.dataset.LOBDatasetV2`` (loads X_raw too).
  - Uses ``src.training.trainer_v2.train_one_fold_v2`` (quantile-only loss).
  - Trains ``DualPathLOBModelV3`` by default (V2 and V1 selectable via --model).
  - Saves the checkpoint in the new format (with class name + config) so
    ``run_backtest.py`` can reinstantiate the right class without guessing
    from state-dict keys.
  - Uses ``BacktestEngine`` with ``overlap_ratio = horizon_sec / stride``.

Usage
-----
    python run_pipeline_v3.py --config configs/default.json
    python run_pipeline_v3.py --config configs/default.json --skip-features
    python run_pipeline_v3.py --config configs/default.json --model V2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
from src.features.pipeline import process_csv_to_npz
from src.training.dataset import LOBDatasetV2, build_time_series_folds
from src.training.trainer_v2 import train_one_fold_v2, _extract_model_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def detect_device() -> str:
    """Auto-detect best available device: cuda > mps > cpu."""
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def build_model(model_tag: str, n_features: int, n_levels: int,
                model_cfg: dict) -> torch.nn.Module:
    """Instantiate a model by tag (V1/V2/V3)."""
    tag = model_tag.upper()
    if tag == "V3":
        from src.model.dual_path_model_v3 import DualPathLOBModelV3
        # Accept only kwargs the V3 constructor knows about; silently ignore
        # legacy keys from the default config.
        allowed = {"d_model", "d_raw", "n_mask_blocks", "n_cross_layers",
                   "patch_size", "attn_nhead", "attn_d_ff", "d_prior",
                   "dropout", "n_horizons", "n_symbols",
                   "use_monotonic_quantile"}
        kwargs = {k: v for k, v in model_cfg.items() if k in allowed}
        return DualPathLOBModelV3(n_features=n_features, n_levels=n_levels,
                                  **kwargs)
    elif tag == "V2":
        from src.model.dual_path_model import DualPathLOBModelV2
        allowed = {"d_model", "d_raw", "n_mask_blocks", "n_cross_layers",
                   "d_prior", "dropout", "n_quantiles",
                   "use_monotonic_quantile"}
        kwargs = {k: v for k, v in model_cfg.items() if k in allowed}
        return DualPathLOBModelV2(n_features=n_features, n_levels=n_levels,
                                  **kwargs)
    elif tag == "V1":
        from src.model.dual_path_model import DualPathLOBModel
        allowed = {"d_model", "d_raw", "dropout", "n_quantiles"}
        kwargs = {k: v for k, v in model_cfg.items() if k in allowed}
        return DualPathLOBModel(n_features=n_features, n_levels=n_levels,
                                **kwargs)
    else:
        raise ValueError(f"Unknown --model tag: {model_tag}. "
                         f"Expected V1, V2, or V3.")


def _run_test_evaluation(
    model: torch.nn.Module,
    fold_dir: str,
    test_ds: LOBDatasetV2,
    train_cfg: dict,
    device: str,
    *,
    horizon_sec: int,
    stride: int,
    y_sigma: float = 1.0,
    y_median: float = 0.0,
) -> None:
    """Load best model, run inference on test set, compute metrics + backtest."""
    device_obj = torch.device(device)

    ckpt_path = os.path.join(fold_dir, "best_model.pt")
    ckpt = torch.load(ckpt_path, map_location=device_obj, weights_only=False)

    # Accept both new-format and legacy raw state_dict
    if isinstance(ckpt, dict) and "state" in ckpt:
        model.load_state_dict(ckpt["state"])
    else:
        model.load_state_dict(ckpt)
    model.to(device_obj)
    model.eval()

    test_loader = DataLoader(
        test_ds,
        batch_size=train_cfg["batch_size"],
        shuffle=False,
    )

    dual_path = test_ds.has_raw

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
    mask = np.concatenate(all_mask).astype(bool)

    # --- De-normalize for backtest ---
    preds_raw = predictions * y_sigma + y_median
    targets_raw = targets * y_sigma + y_median

    # --- Save predictions for run_backtest.py ---
    np.savez(
        os.path.join(fold_dir, "test_preds.npz"),
        predictions=predictions,
        targets=targets,
        mask=mask,
        y_sigma=np.array(y_sigma),
        y_median=np.array(y_median),
    )

    # --- Backtest using BacktestEngine with correct overlap_ratio ---
    from src.evaluation.backtest_v2 import BacktestEngine

    overlap_ratio = max(1, int(round(horizon_sec / max(stride, 1))))
    engine = BacktestEngine(
        fee_bps=4.0,
        slippage_bps=1.0,
        max_position=1.0,
        signal_threshold=0.0,
        confidence_sizing=True,
    )
    result = engine.run(
        predictions=preds_raw,
        targets=targets_raw,
        mask=mask,
        overlap_ratio=overlap_ratio,
    )

    print(result.summary())

    # Persist scalar results
    results_path = os.path.join(fold_dir, "test_results.json")
    with open(results_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)
    print(f"[pipeline_v3] Test results saved to {results_path}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dual-Path LOB V3 end-to-end pipeline"
    )
    parser.add_argument("--config", default="configs/default.json",
                        help="Path to config JSON")
    parser.add_argument("--skip-features", action="store_true",
                        help="Skip feature engineering step")
    parser.add_argument("--model", default="V3", choices=["V1", "V2", "V3"],
                        help="Which model to train (V1/V2/V3, default V3)")
    args = parser.parse_args()

    # --- Load config ---------------------------------------------------------
    with open(args.config, "r") as f:
        cfg = json.load(f)

    data_cfg = cfg["data"]
    model_cfg = cfg.get("model", {})
    train_cfg = cfg["training"]
    output_dir = cfg["output_dir"]

    # --- Device --------------------------------------------------------------
    device = detect_device()
    print(f"[pipeline_v3] Device: {device}")
    print(f"[pipeline_v3] Model: {args.model}")

    horizon_sec = int(data_cfg.get("horizon_sec", 180))
    stride = int(data_cfg.get("stride", 60))
    input_len = int(data_cfg.get("input_len", 300))
    n_levels = int(data_cfg.get("n_levels", 25))

    # =========================================================================
    # Step 1: Feature engineering (CSV -> NPZ)
    # =========================================================================
    npz_dir = data_cfg["npz_dir"]

    if not args.skip_features:
        print(f"[pipeline_v3] Processing {data_cfg['csv_path']} -> {npz_dir}")
        saved = process_csv_to_npz(
            csv_path=data_cfg["csv_path"],
            output_dir=npz_dir,
            horizon_sec=horizon_sec,
            input_len=input_len,
            stride=stride,
            n_levels=n_levels,
        )
        for p in saved:
            d = np.load(p, allow_pickle=True)
            has_raw = "X_raw" in d.files
            print(
                f"  {p.name}: X={d['X'].shape} "
                f"X_raw={'present' if has_raw else 'absent'} "
                f"y={d['y'].shape} mask_sum={d['y_mask'].sum()}"
            )
    else:
        print("[pipeline_v3] Skipping feature engineering (--skip-features)")

    # =========================================================================
    # Step 2: Discover available days
    # =========================================================================
    npz_files = sorted(Path(npz_dir).glob("*.npz"))
    days = [f.stem for f in npz_files]
    print(f"[pipeline_v3] Found {len(days)} day(s): {days}")

    if len(days) == 0:
        print("[pipeline_v3] ERROR: No NPZ files found. Run without --skip-features first.")
        sys.exit(1)

    # =========================================================================
    # Step 3: Training -- single-day vs multi-day
    # =========================================================================
    fold_window = train_cfg["train_days"] + train_cfg["val_days"] + train_cfg["test_days"]

    if len(days) >= fold_window:
        # ----- Multi-day mode --------------------------------------------------
        print(f"[pipeline_v3] Multi-day mode ({len(days)} days)")
        folds = build_time_series_folds(
            days,
            train_days=train_cfg["train_days"],
            val_days=train_cfg["val_days"],
            test_days=train_cfg["test_days"],
            stride=train_cfg["fold_stride"],
        )
        print(f"[pipeline_v3] Built {len(folds)} fold(s)")

        for fold_idx, fold in enumerate(folds):
            fold_dir = os.path.join(output_dir, f"fold_{fold_idx}")
            print(f"\n{'='*60}")
            print(
                f"[pipeline_v3] Fold {fold_idx}: "
                f"train={fold['train']} val={fold['val']} test={fold['test']}"
            )
            print(f"{'='*60}")

            # Compute normalization stats on training data only
            train_ds_raw = LOBDatasetV2(npz_dir, fold["train"], normalize=False)
            x_mean, x_std = train_ds_raw.compute_stats()

            train_ds = LOBDatasetV2(npz_dir, fold["train"], normalize=True,
                                    x_mean=x_mean, x_std=x_std)
            val_ds = LOBDatasetV2(npz_dir, fold["val"], normalize=True,
                                  x_mean=x_mean, x_std=x_std)
            test_ds = LOBDatasetV2(npz_dir, fold["test"], normalize=True,
                                   x_mean=x_mean, x_std=x_std)

            n_features = train_ds.X.shape[-1]
            raw_levels = (train_ds.X_raw.shape[-2]
                          if train_ds.has_raw else 20)
            model = build_model(args.model, n_features, raw_levels, model_cfg)
            total_params = sum(p.numel() for p in model.parameters())
            print(f"[pipeline_v3] Model parameters: {total_params:,}")

            best = train_one_fold_v2(
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
            )
            print(f"[pipeline_v3] Fold {fold_idx} best: {best}")

            np.savez(
                os.path.join(fold_dir, "norm_params.npz"),
                x_mean=x_mean,
                x_std=x_std,
            )

            _run_test_evaluation(
                model, fold_dir, test_ds, train_cfg, device,
                horizon_sec=horizon_sec, stride=stride,
            )

    else:
        # ----- Single-day mode -------------------------------------------------
        print(
            f"[pipeline_v3] Single-day mode "
            f"(only {len(days)} day(s), need {fold_window} for multi-day)"
        )
        fold_dir = os.path.join(output_dir, "fold_0")
        os.makedirs(fold_dir, exist_ok=True)

        # Load full dataset un-normalized to compute stats
        full_ds = LOBDatasetV2(npz_dir, days, normalize=False)
        x_mean, x_std = full_ds.compute_stats()

        n_total = len(full_ds)
        n_train = int(n_total * 0.70)
        n_val = int(n_total * 0.15)
        n_test = n_total - n_train - n_val
        print(
            f"[pipeline_v3] Total windows: {n_total} -> "
            f"train={n_train}, val={n_val}, test={n_test}"
        )

        # Normalize X, clip
        safe_std = np.where(x_std < 1e-4, 1.0, x_std).astype(np.float32)
        X_norm = (full_ds.X - x_mean) / safe_std
        X_norm = np.clip(X_norm, -10.0, 10.0).astype(np.float32)

        # Target normalization: robust sigma (MAD) from training portion
        y_raw = full_ds.y
        mask_all = full_ds.mask
        y_train_valid = y_raw[:n_train][mask_all[:n_train] > 0]
        y_median = float(np.median(y_train_valid)) if len(y_train_valid) > 0 else 0.0
        y_mad = float(np.median(np.abs(y_train_valid - y_median))) if len(y_train_valid) > 0 else 0.0
        y_sigma = max(1.4826 * y_mad, 1e-9)
        print(
            f"[pipeline_v3] Target normalization: "
            f"median={y_median:.6f}, sigma={y_sigma:.6f}"
        )
        y_all = np.clip((y_raw - y_median) / y_sigma, -5.0, 5.0).astype(np.float32)

        # Build sliced in-memory datasets preserving raw tensor
        X_raw_all = full_ds.X_raw  # may be None
        has_raw = full_ds.has_raw

        class _SlicedV2:
            """Thin slice wrapper matching LOBDatasetV2 interface."""

            def __init__(self, X, y, mask, X_raw):
                self.X = X
                self.y = y
                self.mask = mask
                self.X_raw = X_raw
                self.has_raw = X_raw is not None

            def __len__(self):
                return len(self.X)

            def __getitem__(self, idx):
                x = torch.FloatTensor(self.X[idx])
                yv = torch.tensor(float(self.y[idx]))
                m = torch.tensor(float(self.mask[idx]))
                if self.has_raw:
                    xr = torch.FloatTensor(self.X_raw[idx])
                    return (x, xr, yv, m)
                return (x, yv, m)

        train_ds = _SlicedV2(
            X_norm[:n_train], y_all[:n_train], mask_all[:n_train],
            X_raw_all[:n_train] if has_raw else None,
        )
        val_ds = _SlicedV2(
            X_norm[n_train:n_train + n_val],
            y_all[n_train:n_train + n_val],
            mask_all[n_train:n_train + n_val],
            X_raw_all[n_train:n_train + n_val] if has_raw else None,
        )
        test_ds = _SlicedV2(
            X_norm[n_train + n_val:],
            y_all[n_train + n_val:],
            mask_all[n_train + n_val:],
            X_raw_all[n_train + n_val:] if has_raw else None,
        )

        n_features = full_ds.X.shape[-1]
        raw_levels = full_ds.X_raw.shape[-2] if has_raw else 20
        print(f"[pipeline_v3] n_features={n_features}, raw_levels={raw_levels}")

        model = build_model(args.model, n_features, raw_levels, model_cfg)
        total_params = sum(p.numel() for p in model.parameters())
        print(f"[pipeline_v3] Model parameters: {total_params:,}")

        best = train_one_fold_v2(
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
        )
        print(f"[pipeline_v3] Training best metrics: {best}")

        np.savez(
            os.path.join(fold_dir, "norm_params.npz"),
            x_mean=x_mean, x_std=x_std,
            y_median=np.array(y_median), y_sigma=np.array(y_sigma),
        )

        _run_test_evaluation(
            model, fold_dir, test_ds, train_cfg, device,
            horizon_sec=horizon_sec, stride=stride,
            y_sigma=y_sigma, y_median=y_median,
        )

    print("\n[pipeline_v3] All done.")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()

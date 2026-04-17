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
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from torch.utils.data import DataLoader

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
from src.features.pipeline import process_csv_to_npz
from src.training.dataset import LOBDatasetV2, build_time_series_folds
from src.training.trainer_v2 import train_one_fold_v2, _extract_model_config


def _stats_cache_key(train_days, horizons_sec) -> str:
    """Stable fingerprint of (train day set, horizon list). The cache is
    invalidated automatically if either changes."""
    h = hashlib.sha256()
    for d in sorted(str(x) for x in train_days):
        h.update(d.encode()); h.update(b"|")
    h.update(b"h=")
    if horizons_sec is not None:
        for x in horizons_sec:
            h.update(str(int(x)).encode()); h.update(b",")
    return h.hexdigest()[:16]


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
                   "use_monotonic_quantile",
                   # Phase A2 ablation bypass flags
                   "use_masknet", "use_gdcn", "use_raw_path",
                   "use_attention", "use_conv",
                   # Phase A3 non-stationarity mitigation
                   "use_revin",
                   # V4 ablation flags
                   "use_channel_mix_conv", "use_level_attention_pool",
                   "use_patch_attention_pool", "use_ppnet_gate"}
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
    horizons_sec: Optional[list] = None,
) -> None:
    """Load best model, run inference on test set, compute metrics + backtest.

    For multi-horizon models (n_horizons > 1), inference is run with
    ``all_horizons=True`` and the backtest uses the horizon whose period
    matches ``horizon_sec`` (defaulting to index 0 if not found).  Targets
    and masks are sliced to the selected horizon so shapes are consistent
    with the (N, 3) quantile predictions fed to BacktestEngine.
    """
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
    has_regime_prior = getattr(test_ds, "has_regime_prior", False)

    # Detect multi-horizon model so we call all_horizons=True and slice
    # targets / masks to the correct horizon index.  Single-horizon models
    # keep the legacy path (no slicing needed).
    n_horizons = getattr(model, "n_horizons", 1)
    multi_horizon = n_horizons > 1

    # Select which horizon index to use for the backtest.  If horizons_sec
    # is provided, pick the index whose value equals horizon_sec; fall back
    # to index 0 (shortest horizon) if not found.
    if multi_horizon and horizons_sec is not None and horizon_sec in horizons_sec:
        backtest_h_idx = horizons_sec.index(horizon_sec)
    else:
        backtest_h_idx = 0

    all_quantiles = []
    all_target = []
    all_mask = []

    with torch.no_grad():
        for batch in test_loader:
            if has_regime_prior and len(batch) == 5:
                x_feat, x_raw, regime_prior, y, m = batch
                x_feat = x_feat.to(device_obj)
                x_raw = x_raw.to(device_obj)
                regime_prior = regime_prior.to(device_obj)
                if multi_horizon:
                    outputs = model(x_feat, x_raw, regime_prior=regime_prior,
                                    all_horizons=True)
                else:
                    outputs = model(x_feat, x_raw, regime_prior=regime_prior)
            elif dual_path and len(batch) == 4:
                x_feat, x_raw, y, m = batch
                x_feat = x_feat.to(device_obj)
                x_raw = x_raw.to(device_obj)
                if multi_horizon:
                    outputs = model(x_feat, x_raw, all_horizons=True)
                else:
                    outputs = model(x_feat, x_raw)
            else:
                x_feat, y, m = batch[:3]
                x_feat = x_feat.to(device_obj)
                if multi_horizon:
                    outputs = model(x_feat, all_horizons=True)
                else:
                    outputs = model(x_feat)

            if multi_horizon:
                # quantiles_by_horizon: (B, n_horizons, 3) -> slice to (B, 3)
                q = outputs["quantiles_by_horizon"][:, backtest_h_idx, :]
                # y and m are (B, n_horizons) -- slice to (B,)
                y_h = y[:, backtest_h_idx]
                m_h = m[:, backtest_h_idx]
            else:
                q = outputs["quantiles"]
                y_h = y
                m_h = m

            all_quantiles.append(q.cpu().numpy())
            all_target.append(y_h.numpy())
            all_mask.append(m_h.numpy())

    predictions = np.concatenate(all_quantiles)  # (N, 3)
    targets = np.concatenate(all_target)          # (N,)
    mask = np.concatenate(all_mask).astype(bool)  # (N,)

    # --- De-normalize for backtest ---
    preds_raw = predictions * y_sigma + y_median
    targets_raw = targets * y_sigma + y_median

    # --- Collect timestamps for downstream regime-segmented evaluation ---
    # LOBDatasetV2 exposes ``get_all_timestamps``; the _SlicedV2 wrapper does
    # not have this attribute yet, so we fall back to whatever ``.timestamps``
    # it may carry (or emit an empty array to stay schema-compatible).
    if hasattr(test_ds, "get_all_timestamps"):
        timestamps = test_ds.get_all_timestamps()
    elif hasattr(test_ds, "timestamps"):
        timestamps = np.asarray(getattr(test_ds, "timestamps"), dtype=np.int64)
    else:
        timestamps = np.zeros(0, dtype=np.int64)

    # --- Save predictions for run_backtest.py ---
    np.savez(
        os.path.join(fold_dir, "test_preds.npz"),
        predictions=predictions,
        targets=targets,
        mask=mask,
        timestamps=timestamps,
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
            include_ridge_features=data_cfg.get("include_ridge_features", False),
            include_regime_prior=data_cfg.get("include_regime_prior", False),
            quantize_features=data_cfg.get("quantize_features", False),
            horizons_sec=data_cfg.get("horizons_sec"),
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

            # ---- Streaming stats on the un-normalised training days ------
            # LOBDatasetV2 walks train-day NPZs through a parallel I/O pool
            # to accumulate mean/std (X) and median/sigma (y). The result is
            # cached per-fold so reruns (retries, ablations) skip this pass.
            os.makedirs(fold_dir, exist_ok=True)
            stats_cache = os.path.join(fold_dir, "stats_cache.npz")
            cache_key = _stats_cache_key(fold["train"], data_cfg.get("horizons_sec"))
            if os.path.exists(stats_cache):
                _c = np.load(stats_cache, allow_pickle=True)
                if str(_c.get("key", "")) == cache_key:
                    x_mean = _c["x_mean"].astype(np.float32)
                    x_std = _c["x_std"].astype(np.float32)
                    y_median = float(_c["y_median"])
                    y_sigma = float(_c["y_sigma"])
                    print(f"[pipeline_v3] Fold {fold_idx} stats cache HIT")
                else:
                    print(f"[pipeline_v3] Fold {fold_idx} stats cache key mismatch — recomputing")
                    os.remove(stats_cache)
                    x_mean = x_std = None  # sentinel
            else:
                x_mean = x_std = None
            if x_mean is None:
                _t0 = time.time()
                stats_ds = LOBDatasetV2(npz_dir, fold["train"], normalize=False)
                x_mean, x_std = stats_ds.compute_stats()
                y_median, y_sigma = stats_ds.compute_y_stats()
                stats_ds.clear_cache()
                del stats_ds
                np.savez(stats_cache,
                         x_mean=x_mean, x_std=x_std,
                         y_median=np.float64(y_median), y_sigma=np.float64(y_sigma),
                         key=np.array(cache_key))
                print(f"[pipeline_v3] Fold {fold_idx} stats computed in {time.time()-_t0:.1f}s → cached")
            print(
                f"[pipeline_v3] Fold {fold_idx} target normalization: "
                f"median={y_median:.6e}, sigma={y_sigma:.6e}"
            )

            # ---- Re-instantiate datasets with normalisation baked in ----
            # When data_cfg.preload is true, the train/val/test datasets
            # materialise the entire fold into a single in-memory tensor
            # at construction. This eliminates dataloader I/O and lets
            # the GPU saturate on training. Total RAM cost ~50 GB for a
            # 700-day fold at input_len=600, n_features=64.
            y_norm = (y_median, y_sigma, 5.0)
            preload = bool(data_cfg.get("preload", False))
            common_kwargs = dict(
                normalize=True,
                x_mean=x_mean,
                x_std=x_std,
                y_norm=y_norm,
                preload=preload,
            )
            print(f"[pipeline_v3] preload={preload}")
            train_ds = LOBDatasetV2(npz_dir, fold["train"], **common_kwargs)
            val_ds = LOBDatasetV2(npz_dir, fold["val"], **common_kwargs)
            test_ds = LOBDatasetV2(npz_dir, fold["test"], **common_kwargs)

            # Peek at the first window via the lazy loader to discover
            # feature / raw-level counts *without* concatenating every day.
            sample0 = train_ds._load_day(0)
            n_features = int(sample0["X"].shape[-1])
            raw_levels = (
                int(sample0["X_raw"].shape[-2]) if train_ds.has_raw else 20
            )
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
                dul_config=train_cfg.get("dul_config"),
                num_workers=int(train_cfg.get("num_workers", 4)),
                prefetch_factor=int(train_cfg.get("prefetch_factor", 2)),
            )
            print(f"[pipeline_v3] Fold {fold_idx} best: {best}")

            np.savez(
                os.path.join(fold_dir, "norm_params.npz"),
                x_mean=x_mean,
                x_std=x_std,
                y_median=np.array(y_median),
                y_sigma=np.array(y_sigma),
            )

            _run_test_evaluation(
                model, fold_dir, test_ds, train_cfg, device,
                horizon_sec=horizon_sec, stride=stride,
                y_sigma=y_sigma, y_median=y_median,
                horizons_sec=data_cfg.get("horizons_sec"),
            )

    else:
        # ----- Single-day mode -------------------------------------------------
        print(
            f"[pipeline_v3] Single-day mode "
            f"(only {len(days)} day(s), need {fold_window} for multi-day)"
        )
        fold_dir = os.path.join(output_dir, "fold_0")
        os.makedirs(fold_dir, exist_ok=True)

        # Load full dataset un-normalized to compute stats.
        # Single-day mode: dataset is small enough to materialise, so we
        # accept the one-shot cost of ds.X / ds.y property calls below.
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

        # Normalize X, clip.  ``full_ds.X`` materialises once here.
        safe_std = np.where(x_std < 1e-4, 1.0, x_std).astype(np.float32)
        X_norm = (full_ds.X - x_mean) / safe_std
        X_norm = np.clip(X_norm, -10.0, 10.0).astype(np.float32)

        # Target normalization: robust sigma (MAD) from training portion.
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
        has_raw = full_ds.has_raw
        X_raw_all = full_ds.X_raw if has_raw else None

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

        n_features = int(X_norm.shape[-1])
        raw_levels = int(X_raw_all.shape[-2]) if has_raw else 20
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
            dul_config=train_cfg.get("dul_config"),
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
            horizons_sec=data_cfg.get("horizons_sec"),
        )

    print("\n[pipeline_v3] All done.")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()

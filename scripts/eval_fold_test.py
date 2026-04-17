"""Quick test-set evaluation for a single fold without re-running training.

Loads `best_model.pt` from a fold directory, applies it to that fold's test
set, and reports correlation/R²/backtest. Designed for early-stop scenarios
where we want to inspect a fold's OOS performance without waiting for the
full walk-forward to complete.

CLI
---
    python scripts/eval_fold_test.py \
        --config configs/full_run.json \
        --fold-index 0 \
        --baseline-corr 0.099
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

# Make project importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.training.dataset import LOBDatasetV2, build_time_series_folds
from run_pipeline_v3 import build_model, detect_device


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--fold-index", type=int, default=0)
    ap.add_argument("--model", default="V3")
    ap.add_argument("--baseline-corr", type=float, default=None)
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    data_cfg = cfg["data"]
    train_cfg = cfg["training"]
    model_cfg = cfg["model"]
    output_dir = cfg["output_dir"]

    device = detect_device()
    print(f"Device: {device}")

    # Build folds
    days = sorted(p.stem for p in Path(data_cfg["npz_dir"]).glob("*.npz"))
    folds = build_time_series_folds(
        days,
        train_days=train_cfg["train_days"],
        val_days=train_cfg["val_days"],
        test_days=train_cfg["test_days"],
        stride=train_cfg["fold_stride"],
    )
    if args.fold_index >= len(folds):
        raise ValueError(f"fold_index {args.fold_index} out of range (have {len(folds)} folds)")
    fold = folds[args.fold_index]
    fold_dir = Path(output_dir) / f"fold_{args.fold_index}"

    print(f"\nFold {args.fold_index}:")
    print(f"  train: {fold['train'][0]} → {fold['train'][-1]}  ({len(fold['train'])}d)")
    print(f"  val  : {fold['val'][0]} → {fold['val'][-1]}  ({len(fold['val'])}d)")
    print(f"  test : {fold['test'][0]} → {fold['test'][-1]}  ({len(fold['test'])}d)")

    # Compute training stats on the train fold (needed to normalise val/test)
    print("\nComputing training stats (streaming) ...")
    stats_ds = LOBDatasetV2(data_cfg["npz_dir"], fold["train"], normalize=False)
    x_mean, x_std = stats_ds.compute_stats()
    y_median, y_sigma = stats_ds.compute_y_stats()
    print(f"  y_median = {y_median:.6e}, y_sigma = {y_sigma:.6e}")
    stats_ds.clear_cache()
    del stats_ds

    # Load test dataset with the same normalization
    print("\nLoading test dataset (lazy) ...")
    test_ds = LOBDatasetV2(
        data_cfg["npz_dir"],
        fold["test"],
        normalize=True,
        x_mean=x_mean, x_std=x_std,
        y_norm=(y_median, y_sigma, 5.0),
    )
    print(f"  test windows = {len(test_ds):,}")

    # Build model with same config and load best checkpoint
    sample_data = test_ds._load_day(0)
    n_features = sample_data["X"].shape[-1]
    raw_levels = (sample_data["X_raw"].shape[-2]
                  if test_ds._has_raw and "X_raw" in sample_data else 20)
    test_ds.clear_cache()

    model = build_model(args.model, n_features, raw_levels, model_cfg)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  model = {args.model}, {n_params:,} parameters")

    ckpt_path = fold_dir / "best_model.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"No checkpoint at {ckpt_path}")
    ckpt = torch.load(str(ckpt_path), map_location=device, weights_only=False)
    state = ckpt["state"] if isinstance(ckpt, dict) and "state" in ckpt else ckpt
    model.load_state_dict(state, strict=True)
    model = model.to(device)
    model.eval()
    print(f"  loaded checkpoint: {ckpt_path}")

    # Inference
    print("\nRunning inference ...")
    test_loader = DataLoader(test_ds, batch_size=train_cfg["batch_size"], shuffle=False)
    has_regime_prior = getattr(test_ds, "has_regime_prior", False)
    all_q, all_y, all_m = [], [], []
    with torch.no_grad():
        for batch in test_loader:
            if has_regime_prior and len(batch) == 5:
                x_feat, x_raw, regime_prior, y, m = batch
                x_feat = x_feat.to(device)
                x_raw = x_raw.to(device)
                regime_prior = regime_prior.to(device)
                outputs = model(x_feat, x_raw, regime_prior=regime_prior)
            elif test_ds.has_raw and len(batch) == 4:
                x_feat, x_raw, y, m = batch
                x_feat = x_feat.to(device)
                x_raw = x_raw.to(device)
                outputs = model(x_feat, x_raw)
            else:
                x_feat, y, m = batch[:3]
                x_feat = x_feat.to(device)
                outputs = model(x_feat)
            all_q.append(outputs["quantiles"].cpu().numpy())
            all_y.append(y.numpy())
            all_m.append(m.numpy())

    quantiles = np.concatenate(all_q)
    targets = np.concatenate(all_y)
    mask = np.concatenate(all_m).astype(bool)
    point_pred = quantiles[:, 1] if quantiles.ndim == 2 and quantiles.shape[-1] >= 3 else quantiles.ravel()

    # Apply mask
    p_valid = point_pred[mask]
    t_valid = targets[mask]
    print(f"  valid samples: {len(p_valid):,} / {len(targets):,}")

    # ===== Metrics =====
    test_corr = float(np.corrcoef(p_valid, t_valid)[0, 1])
    rank_corr = float(np.corrcoef(
        np.argsort(np.argsort(p_valid)),
        np.argsort(np.argsort(t_valid)),
    )[0, 1])
    ss_res = float(np.sum((t_valid - p_valid) ** 2))
    ss_tot = float(np.sum((t_valid - t_valid.mean()) ** 2))
    r2 = 1 - ss_res / max(ss_tot, 1e-12)

    pred_dir = np.sign(p_valid)
    true_dir = np.sign(t_valid)
    dir_acc = float(np.mean(pred_dir == true_dir))

    # ===== Print =====
    print("\n" + "=" * 70)
    print(f"FOLD {args.fold_index} TEST RESULTS  (test period {fold['test'][0]} → {fold['test'][-1]})")
    print("=" * 70)
    print(f"  Pearson correlation : {test_corr:+.4f}")
    print(f"  Rank correlation    : {rank_corr:+.4f}")
    print(f"  R²                  : {r2:+.4f}")
    print(f"  Direction accuracy  : {dir_acc:.2%}")
    print(f"  Sample count        : {len(p_valid):,}")
    if args.baseline_corr is not None:
        delta = test_corr - args.baseline_corr
        print(f"  Δ vs baseline ({args.baseline_corr:+.4f}): {delta:+.4f}")
    print("=" * 70)

    # ===== Save =====
    out_path = fold_dir / "test_results_quick.json"
    with open(out_path, "w") as f:
        json.dump({
            "fold": args.fold_index,
            "test_period": [fold["test"][0], fold["test"][-1]],
            "pearson_corr": test_corr,
            "rank_corr": rank_corr,
            "r2": r2,
            "direction_accuracy": dir_acc,
            "n_samples": int(len(p_valid)),
            "y_sigma": y_sigma,
            "y_median": y_median,
        }, f, indent=2)
    print(f"\nSaved to {out_path}")

    # Save predictions for downstream analysis
    preds_path = fold_dir / "test_preds_quick.npz"
    np.savez(
        str(preds_path),
        predictions=quantiles,
        targets=targets,
        mask=mask,
        y_sigma=np.array(y_sigma),
        y_median=np.array(y_median),
    )
    print(f"Saved preds to {preds_path}")


if __name__ == "__main__":
    main()

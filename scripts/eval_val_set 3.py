"""Generate predictions on the VAL set for existing trained checkpoints.

Val predictions are not stored at training time (only metrics aggregated).
This script re-runs inference on the validation-fold days for each
checkpoint (best_model.pt or ema_best.pt) and writes val_preds.npz.

Val preds are needed for PROPER walk-forward ensemble-weight calibration:
- model-selection during training uses val metrics → val labels are weakly
  "known" to the chosen checkpoint (leakage at the model-selection level).
- BUT second-order choice of ensemble weights fit on val preds → val
  targets does NOT leak test information. Test preds with those weights
  applied stays a clean out-of-sample estimate.

Usage:
    python scripts/eval_val_set.py \
        --config configs/y600_push/baseline_plus.json \
        --exp-dir experiments/y600_push/baseline_plus \
        --ckpt-name best_model.pt \
        --preds-name val_preds.npz
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch
from torch.utils.data import DataLoader

from src.training.dataset import LOBDatasetV2, build_time_series_folds
from run_pipeline_v3 import build_model, detect_device


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--exp-dir", required=True, help="Directory containing fold_N/ subdirs")
    ap.add_argument("--ckpt-name", default="best_model.pt",
                    help="Checkpoint filename (best_model.pt or ema_best.pt)")
    ap.add_argument("--preds-name", default="val_preds.npz",
                    help="Output preds filename")
    ap.add_argument("--fold", type=int, default=None,
                    help="Single fold index (else all 3)")
    ap.add_argument("--model", default="V3")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    data_cfg = cfg["data"]
    train_cfg = cfg["training"]
    model_cfg = cfg["model"]

    device = detect_device()

    days = sorted(p.stem for p in Path(data_cfg["npz_dir"]).glob("*.npz"))
    folds = build_time_series_folds(
        days,
        train_days=train_cfg["train_days"],
        val_days=train_cfg["val_days"],
        test_days=train_cfg["test_days"],
        stride=train_cfg["fold_stride"],
    )

    fold_indices = [args.fold] if args.fold is not None else list(range(len(folds)))

    for fi in fold_indices:
        fold = folds[fi]
        fold_dir = Path(args.exp_dir) / f"fold_{fi}"
        ckpt_path = fold_dir / args.ckpt_name
        if not ckpt_path.exists():
            print(f"fold {fi}: {ckpt_path} missing, skipping")
            continue
        print(f"=== fold {fi}: val ({len(fold['val'])} days) via {args.ckpt_name} ===")

        # Load stats cache to get normalization (same as training)
        stats_path = fold_dir / "stats_cache.npz"
        if not stats_path.exists():
            print(f"  stats cache missing, skipping")
            continue
        sc = np.load(stats_path, allow_pickle=True)
        x_mean = sc["x_mean"].astype(np.float32)
        x_std = sc["x_std"].astype(np.float32)
        y_median = float(sc["y_median"])
        y_sigma = float(sc["y_sigma"])

        _horizons_sec = data_cfg.get("horizons_sec")
        _horizons_list = [f"y_{int(h)}" for h in _horizons_sec] if _horizons_sec else None

        val_ds = LOBDatasetV2(
            data_cfg["npz_dir"], fold["val"],
            normalize=True, x_mean=x_mean, x_std=x_std,
            y_norm=(y_median, y_sigma, 5.0),
            horizons=_horizons_list,
            preload=False,
        )
        print(f"  val_ds size={len(val_ds)}")

        # Build model
        sample = val_ds._load_day(0)
        n_features = int(sample["X"].shape[-1])
        raw_levels = int(sample["X_raw"].shape[-2]) if val_ds.has_raw else 20

        model = build_model(args.model, n_features, raw_levels, model_cfg)
        ckpt = torch.load(str(ckpt_path), map_location=device, weights_only=False)
        state = ckpt["state"] if isinstance(ckpt, dict) and "state" in ckpt else ckpt
        model.load_state_dict(state)
        model.to(device)
        model.eval()

        # Inference
        loader = DataLoader(val_ds, batch_size=train_cfg["batch_size"], shuffle=False, num_workers=0)
        all_q, all_y, all_m, all_ts = [], [], [], []
        has_rp = getattr(val_ds, "has_regime_prior", False)
        horizon_sec = int(data_cfg.get("horizon_sec", 600))
        n_h = int(model_cfg.get("n_horizons", 1))
        multi_horizon = n_h > 1
        h_idx = _horizons_sec.index(horizon_sec) if (_horizons_sec and horizon_sec in _horizons_sec) else 0

        with torch.no_grad():
            for batch in loader:
                if has_rp and len(batch) == 5:
                    x, xr, rp, y, m = batch
                    kwargs = {"regime_prior": rp.to(device)}
                elif val_ds.has_raw and len(batch) == 4:
                    x, xr, y, m = batch
                    kwargs = {}
                else:
                    x, y, m = batch[:3]; xr = None
                    kwargs = {}
                x = x.to(device)
                if xr is not None:
                    xr = xr.to(device)
                if multi_horizon:
                    kwargs["all_horizons"] = True
                if xr is not None:
                    out = model(x, xr, **kwargs)
                else:
                    out = model(x, **kwargs)
                if multi_horizon:
                    # Slice to primary horizon
                    q = out["quantiles_by_horizon"][:, h_idx, :]
                    y_h = y[:, h_idx] if y.ndim == 2 else y
                    m_h = m[:, h_idx] if m.ndim == 2 else m
                else:
                    q = out["quantiles"]
                    y_h = y
                    m_h = m
                all_q.append(q.cpu().numpy())
                all_y.append(y_h.numpy() if torch.is_tensor(y_h) else y_h)
                all_m.append(m_h.numpy() if torch.is_tensor(m_h) else m_h)

        predictions = np.concatenate(all_q).astype(np.float32)
        targets = np.concatenate(all_y).astype(np.float32)
        mask = np.concatenate(all_m).astype(bool)
        timestamps = val_ds.get_all_timestamps() if hasattr(val_ds, "get_all_timestamps") else np.zeros(len(targets), dtype=np.int64)

        out_path = fold_dir / args.preds_name
        np.savez(out_path, predictions=predictions, targets=targets, mask=mask,
                 timestamps=timestamps, y_sigma=np.array(y_sigma), y_median=np.array(y_median))
        print(f"  wrote {out_path}  (N={len(predictions)}, valid={int(mask.sum())})")


if __name__ == "__main__":
    main()

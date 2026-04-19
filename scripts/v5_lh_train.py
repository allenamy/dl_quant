#!/usr/bin/env python3
"""Train V5-LH on walk-forward fold × seed.

Primary target: y_600 (10-minute return) Pearson ≥ 0.07 on clean subsampled test.

Key design choices per Option B (post-ultrareview):
  - Single-horizon y_600 by default (UNIT disabled at n_horizons=1).
  - Compact model: d_model=24, d_raw=16, n_mamba_layers=1 → ~22K params.
  - Mask filtering BEFORE loss: invalid samples (y_mask=0) are dropped
    from the training gradient so model doesn't learn fake zero-returns.
  - Early-exit thresholds to abort unproductive runs early.
  - Reports Pearson AND Spearman per METRIC_DISCIPLINE.md.

Usage:
  python3 scripts/v5_lh_train.py --config configs/v5_lh/v5_lh_base.json \
      --fold 0 --seed 1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np
import torch
from scipy.stats import pearsonr, spearmanr

from src.model_v5_lh.v5_lh_model import V5LHModel
from src.losses.dul_plus_loss import DulPlusLoss
from src.training.dataset import LOBDatasetV2, DayChunkedSampler, build_time_series_folds


def _mask_filter(
    y: torch.Tensor, mask: torch.Tensor, *tensors: torch.Tensor
) -> tuple:
    """Keep only rows where mask > 0. Returns (y_valid, *tensors_valid).

    Boolean indexing; if mask is all zero for a batch, returns empty tensors
    (caller should check and skip the batch).
    """
    keep = mask.bool()
    return (y[keep],) + tuple(t[keep] for t in tensors)


def _corr_metrics(p: np.ndarray, y: np.ndarray) -> dict:
    """Pearson + Spearman + direction accuracy."""
    finite = np.isfinite(p) & np.isfinite(y)
    p_f = p[finite]
    y_f = y[finite]
    if len(p_f) < 30:
        return {"pearson": float("nan"), "spearman": float("nan"),
                "dir_acc": float("nan"), "n": int(len(p_f))}
    return {
        "pearson": float(pearsonr(p_f, y_f)[0]),
        "spearman": float(spearmanr(p_f, y_f)[0]),
        "dir_acc": float((np.sign(p_f) == np.sign(y_f)).mean()),
        "n": int(len(p_f)),
    }


def _run_fold_seed(cfg: dict, fold_idx: int, seed: int, device: str) -> dict:
    torch.manual_seed(seed)
    np.random.seed(seed)

    data_cfg = cfg["data"]
    train_cfg = cfg["training"]
    horizons = cfg["model"]["horizons"]
    assert all(h.startswith("y_") for h in horizons), f"horizons must be 'y_*' keys, got {horizons}"

    npz_dir = pathlib.Path(data_cfg["npz_dir"])
    days = sorted(f.stem for f in npz_dir.glob("*.npz") if not f.stem.startswith("_"))
    folds = build_time_series_folds(
        days,
        train_days=train_cfg["train_days"],
        val_days=train_cfg["val_days"],
        test_days=train_cfg["test_days"],
        stride=train_cfg["fold_stride"],
    )
    if fold_idx >= len(folds):
        raise ValueError(f"fold_idx={fold_idx} >= n_folds={len(folds)} "
                         f"(days={len(days)}, window={train_cfg['train_days']+train_cfg['val_days']+train_cfg['test_days']})")
    fold = folds[fold_idx]
    print(f"[v5_lh] fold={fold_idx} seed={seed}: "
          f"train={len(fold['train'])} val={len(fold['val'])} test={len(fold['test'])} days")

    # cache_size limits per-worker LRU of per-day NPZ arrays in RAM.
    # V5-LH per-day NPZ is ~100 MB (1800-step × 59 feat + fp16 raw). With
    # num_workers=N and cache_size=C, peak data-loader RAM ≈ N*C*100 MB.
    # cgroup limit is 125 GB — we stay well under by keeping C small.
    cache_size = int(train_cfg.get("cache_size", 8))
    train_ds = LOBDatasetV2(data_dir=str(npz_dir), days=fold["train"],
                            horizons=horizons, preload=False,
                            cache_size=cache_size)
    val_ds = LOBDatasetV2(data_dir=str(npz_dir), days=fold["val"],
                          horizons=horizons, preload=False,
                          cache_size=cache_size)
    test_ds = LOBDatasetV2(data_dir=str(npz_dir), days=fold["test"],
                           horizons=horizons, preload=False,
                           cache_size=cache_size)
    print(f"[v5_lh] samples: train={len(train_ds):,} val={len(val_ds):,} test={len(test_ds):,}")

    # Compute per-horizon y_sigma from TRAIN set (MAD-sigma)
    # LOBDatasetV2.compute_y_stats returns (median, sigma) over VALID y.
    y_stats = train_ds.compute_y_stats(max_workers=4)
    y_sigma_train = y_stats[1] if isinstance(y_stats, tuple) else float(y_stats)
    print(f"[v5_lh] train y MAD-sigma = {y_sigma_train:.4f}")
    # For single-horizon, y_sigmas is (sigma,)
    y_sigmas = tuple([y_sigma_train] * len(horizons))

    # Derive input dims from one batch
    sample = train_ds[0]
    # Expected 5-tuple: (x_feat, x_raw, regime_prior, y, mask)
    assert len(sample) == 5, (
        f"expected 5-tuple from LOBDatasetV2 (x_feat, x_raw, rp, y, mask), "
        f"got len={len(sample)}"
    )
    x_feat_sample, x_raw_sample, rp_sample, y_sample, m_sample = sample
    _, L, n_features = 1, x_feat_sample.shape[0], x_feat_sample.shape[1]
    n_levels = x_raw_sample.shape[1]
    d_prior = rp_sample.shape[0]
    print(f"[v5_lh] input dims: L={L} n_features={n_features} n_levels={n_levels} d_prior={d_prior}")

    # Model
    model_cfg = cfg["model"]
    model = V5LHModel(
        n_features=n_features,
        n_levels=n_levels,
        d_model=model_cfg["d_model"],
        d_raw=model_cfg["d_raw"],
        d_prior=d_prior,
        horizons=[int(h.replace("y_", "")) for h in horizons],
        n_mamba_layers=model_cfg["n_mamba_layers"],
        mamba_d_state=model_cfg["mamba_d_state"],
        mamba_expand=model_cfg["mamba_expand"],
        use_fallback=model_cfg["use_fallback"],
    ).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[v5_lh] model params: {n_params:,}")

    # Loss
    loss_cfg = cfg["loss"]
    loss_fn = DulPlusLoss(
        n_horizons=len(horizons),
        y_sigmas=y_sigmas,
        gamma_crps=loss_cfg["gamma_crps"],
        eta_utility=loss_cfg["eta_utility"],
        alpha_decorr=loss_cfg["alpha_decorr"],
        focal_weight=loss_cfg["focal_weight"],
        focal_threshold_sigma=loss_cfg["focal_threshold_sigma"],
        use_unit=loss_cfg.get("use_unit", True),
    ).to(device)

    # Optimizer (register loss params too in case UNIT is active)
    params = list(model.parameters()) + list(loss_fn.parameters())
    opt = torch.optim.AdamW(
        params,
        lr=train_cfg["lr"],
        weight_decay=train_cfg["weight_decay"],
    )
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=train_cfg["epochs"])

    # Output directory
    out_dir = pathlib.Path(cfg["output_dir"]) / f"fold_{fold_idx}_seed{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Early-exit thresholds (from ultrareview)
    exit_cfg = cfg.get("early_exit", {})
    min_ep5_pearson = exit_cfg.get("min_epoch5_pearson", 0.010)
    max_grad_norm = exit_cfg.get("max_grad_norm", 10.0)
    grad_spike_window = exit_cfg.get("grad_spike_window", 3)

    # Training loop
    best_val_score = -np.inf   # score = 0.5*Pearson + 0.5*Spearman (METRIC_DISCIPLINE consensus)
    best_val_metrics = None
    no_improve = 0
    consecutive_grad_spikes = 0
    training_log = []

    # DayChunkedSampler keeps each batch local to ~chunk_size days, so
    # LRU cache hits ~100%. This avoids the RAM blowup that shuffle=True
    # caused on V5-LH's larger per-day NPZ (killed the pod last run).
    chunk_size = int(train_cfg.get("chunk_size", cache_size))
    train_sampler = DayChunkedSampler(
        train_ds, chunk_size=chunk_size, shuffle_days=True,
        shuffle_within_day=True, seed=seed,
    )
    print(f"[v5_lh] DataLoader: cache_size={cache_size} "
          f"chunk_size={chunk_size} num_workers={train_cfg['num_workers']}")

    for epoch in range(train_cfg["epochs"]):
        model.train()
        t0 = time.time()
        train_sampler.set_epoch(epoch) if hasattr(train_sampler, "set_epoch") else None
        train_loader = torch.utils.data.DataLoader(
            train_ds, batch_size=train_cfg["batch_size"],
            sampler=train_sampler,
            num_workers=train_cfg["num_workers"],
            pin_memory=(device == "cuda"),
            persistent_workers=(train_cfg["num_workers"] > 0),
        )
        train_losses = []
        for batch in train_loader:
            x_feat, x_raw, rp, y, mask = batch
            x_feat = x_feat.to(device, non_blocking=True)
            x_raw = x_raw.to(device, non_blocking=True)
            rp = rp.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            mask = mask.to(device, non_blocking=True)

            opt.zero_grad()
            out = model(X=x_feat, X_raw=x_raw, regime_prior=rp)

            # For each horizon, mask-filter THEN compute loss. Only valid
            # samples contribute to gradient.
            losses_by_h = []
            targets_by_h = []
            quantiles_by_h = []
            emb = out["embedding"]
            n_horizons = len(horizons)
            # y has shape (B,) for single-horizon, (B, n_horizons) for multi
            for i, h_key in enumerate(horizons):
                h_int = int(h_key.replace("y_", ""))
                q_h = out[f"y_{h_int}"]     # (B, 3)
                if n_horizons == 1:
                    y_h = y
                    m_h = mask
                else:
                    y_h = y[:, i]
                    m_h = mask[:, i] if mask.dim() > 1 else mask
                # Filter by mask
                keep = m_h.bool()
                if keep.sum() < 2:  # too few valid samples in batch
                    continue
                quantiles_by_h.append(q_h[keep])
                targets_by_h.append(y_h[keep])

            if len(quantiles_by_h) != n_horizons:
                # Skip batch if any horizon has no valid samples
                continue

            loss = loss_fn(quantiles_by_h, targets_by_h, embedding=emb)
            loss.backward()

            # Gradient clipping + spike detection
            grad_norm = torch.nn.utils.clip_grad_norm_(params, train_cfg["grad_clip"])
            if grad_norm > max_grad_norm:
                consecutive_grad_spikes += 1
                if consecutive_grad_spikes >= grad_spike_window:
                    print(f"[v5_lh] ABORT fold={fold_idx} seed={seed} ep{epoch}: "
                          f"{grad_spike_window} consecutive grad_norm > {max_grad_norm}")
                    return {"status": "aborted_grad_spike", "epoch": epoch}
            else:
                consecutive_grad_spikes = 0

            opt.step()
            train_losses.append(float(loss.item()))

        sched.step()
        train_loss_mean = float(np.mean(train_losses)) if train_losses else float("nan")

        # Validation — primary horizon y_600 metrics
        model.eval()
        val_preds = {h: [] for h in horizons}
        val_ys = {h: [] for h in horizons}
        with torch.no_grad():
            val_loader = torch.utils.data.DataLoader(
                val_ds, batch_size=train_cfg["batch_size"] * 2,
                num_workers=train_cfg["num_workers"],
            )
            for batch in val_loader:
                x_feat, x_raw, rp, y, mask = batch
                out = model(
                    X=x_feat.to(device),
                    X_raw=x_raw.to(device),
                    regime_prior=rp.to(device),
                )
                for i, h_key in enumerate(horizons):
                    h_int = int(h_key.replace("y_", ""))
                    q = out[f"y_{h_int}"][:, 1].cpu().numpy()  # q50
                    if len(horizons) == 1:
                        y_np = y.numpy()
                        m_np = mask.numpy().astype(bool)
                    else:
                        y_np = y[:, i].numpy()
                        m_np = mask[:, i].numpy().astype(bool) if mask.dim() > 1 else mask.numpy().astype(bool)
                    val_preds[h_key].append(q[m_np])
                    val_ys[h_key].append(y_np[m_np])

        # Compute metrics for each horizon
        val_metrics = {}
        for h_key in horizons:
            p = np.concatenate(val_preds[h_key])
            y = np.concatenate(val_ys[h_key])
            val_metrics[h_key] = _corr_metrics(p, y)

        # Primary metric = last horizon (y_600 in Option B)
        primary_h = horizons[-1]
        primary = val_metrics[primary_h]
        composite_score = 0.5 * (primary.get("pearson", 0) or 0) + 0.5 * (primary.get("spearman", 0) or 0)

        ep_time = time.time() - t0
        print(f"[v5_lh] fold={fold_idx} seed={seed} ep{epoch:02d} "
              f"train_loss={train_loss_mean:.4f} "
              f"{primary_h}: P={primary.get('pearson', 0):.4f} S={primary.get('spearman', 0):.4f} "
              f"DA={primary.get('dir_acc', 0):.4f} N={primary.get('n', 0):,} "
              f"time={ep_time:.1f}s")

        # Early-exit check: epoch 5 primary Pearson
        if epoch == 4 and (primary.get("pearson") is None or primary["pearson"] < min_ep5_pearson):
            print(f"[v5_lh] ABORT fold={fold_idx} seed={seed} ep5 val_pearson={primary.get('pearson')} "
                  f"< threshold {min_ep5_pearson}")
            return {"status": "aborted_ep5_pearson", "epoch": epoch,
                    "val_metrics": val_metrics}

        training_log.append({
            "epoch": epoch,
            "train_loss": train_loss_mean,
            "val_metrics": val_metrics,
            "lr": sched.get_last_lr()[0],
            "ep_time_sec": ep_time,
        })

        # Checkpoint selection: composite score (Pearson + Spearman both count)
        if composite_score > best_val_score + 1e-4:
            best_val_score = composite_score
            best_val_metrics = val_metrics
            no_improve = 0
            torch.save(model.state_dict(), out_dir / "best_model.pt")
        else:
            no_improve += 1
            if no_improve >= train_cfg["patience"]:
                print(f"[v5_lh] early stop at epoch {epoch} (no improvement for {no_improve} epochs)")
                break

    # Save training log
    with open(out_dir / "training_log.json", "w") as f:
        json.dump({
            "fold": fold_idx, "seed": seed, "n_params": n_params,
            "y_sigma_train": y_sigma_train,
            "best_val_metrics": best_val_metrics,
            "log": training_log,
        }, f, indent=2, default=float)

    # Test inference with best model
    if (out_dir / "best_model.pt").exists():
        model.load_state_dict(torch.load(out_dir / "best_model.pt", map_location=device))
    model.eval()
    test_preds = {h: [] for h in horizons}
    test_ys = {h: [] for h in horizons}
    test_masks = {h: [] for h in horizons}
    test_ts = []
    with torch.no_grad():
        test_loader = torch.utils.data.DataLoader(
            test_ds, batch_size=train_cfg["batch_size"] * 2,
            num_workers=train_cfg["num_workers"],
        )
        for batch in test_loader:
            x_feat, x_raw, rp, y, mask = batch
            out = model(
                X=x_feat.to(device),
                X_raw=x_raw.to(device),
                regime_prior=rp.to(device),
            )
            for i, h_key in enumerate(horizons):
                h_int = int(h_key.replace("y_", ""))
                q_full = out[f"y_{h_int}"].cpu().numpy()  # (B, 3)
                if len(horizons) == 1:
                    y_np = y.numpy()
                    m_np = mask.numpy()
                else:
                    y_np = y[:, i].numpy()
                    m_np = mask[:, i].numpy() if mask.dim() > 1 else mask.numpy()
                test_preds[h_key].append(q_full)
                test_ys[h_key].append(y_np)
                test_masks[h_key].append(m_np)

    # Save test predictions per horizon
    for h_key in horizons:
        h_int = int(h_key.replace("y_", ""))
        preds = np.concatenate(test_preds[h_key], axis=0)
        ys = np.concatenate(test_ys[h_key], axis=0)
        masks = np.concatenate(test_masks[h_key], axis=0)
        np.savez(
            out_dir / f"test_preds_y{h_int}.npz",
            predictions=preds, targets=ys, mask=masks,
            y_sigma=np.float64(y_sigma_train),
        )

    # Final pooled test metrics
    final_metrics = {}
    for h_key in horizons:
        preds = np.concatenate(test_preds[h_key], axis=0)[:, 1]
        ys = np.concatenate(test_ys[h_key], axis=0)
        masks = np.concatenate(test_masks[h_key], axis=0).astype(bool)
        final_metrics[h_key] = _corr_metrics(preds[masks], ys[masks])

    print(f"[v5_lh] TEST RESULTS fold={fold_idx} seed={seed}:")
    for h_key, m in final_metrics.items():
        print(f"  {h_key}: P={m['pearson']:.4f} S={m['spearman']:.4f} N={m['n']:,}")

    return {
        "status": "complete",
        "n_params": n_params,
        "best_val_metrics": best_val_metrics,
        "test_metrics": final_metrics,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=pathlib.Path, required=True)
    p.add_argument("--fold", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    args = p.parse_args()

    cfg = json.load(open(args.config))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[v5_lh] device={device}")

    result = _run_fold_seed(cfg, args.fold, args.seed, device)
    print(f"[v5_lh] DONE: {result.get('status', 'unknown')}")


if __name__ == "__main__":
    main()

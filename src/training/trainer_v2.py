"""Simplified trainer: quantile-only loss with dual-path (DualPathLOBModel) support.

Unlike ``trainer.py`` which uses the 4-component ``combined_loss``, this trainer
uses **quantile loss only** and supports the ``DualPathLOBModel``'s dual-input
interface ``forward(x_feat, x_raw)``.

Key differences from V1:
  - Quantile-only loss (from ``losses.py``)
  - Dual-path: auto-detects 3-tuple ``(x_feat, y, mask)`` vs 4-tuple
    ``(x_feat, x_raw, y, mask)`` from dataset
  - ReduceLROnPlateau (mode="max" on val_correlation)
  - Checkpoint by val_correlation (not val_loss)
  - Early stopping based on correlation plateau
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .losses import quantile_loss


# ---------------------------------------------------------------------------
# Reuse OnlineMetrics from trainer.py
# ---------------------------------------------------------------------------
from .trainer import OnlineMetrics


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train_one_fold_v2(
    *,
    model: nn.Module,
    train_dataset: "torch.utils.data.Dataset",
    val_dataset: "torch.utils.data.Dataset",
    out_dir: str,
    device: str = "cpu",
    epochs: int = 50,
    batch_size: int = 64,
    lr: float = 3e-4,
    weight_decay: float = 1e-3,
    patience: int = 10,
    grad_clip: float = 1.0,
) -> Dict[str, Any]:
    """Train with quantile-only loss, dual-path support.

    The dataset ``__getitem__`` can return either:
      ``(x_feat, y, mask)``                    -- Path A only
      ``(x_feat, x_raw, y, mask)``             -- dual path
      ``(x_feat, x_raw, regime_prior, y, mask)`` -- dual path + regime prior

    Detection: uses ``dataset.has_raw`` attribute when available (set by
    ``LOBDatasetV2``), falling back to tuple-length probing.

    Note: when using trainer_v2 with a PPNet gate model, the caller must
    either set ``d_prior=0`` OR provide ``regime_prior`` in the dataset
    (5-tuple mode). The trainer does NOT auto-compute regime_prior.

    Parameters
    ----------
    model : nn.Module
        Any model whose ``forward`` returns a dict with keys
        ``quantiles`` (B, n_quantiles) and ``point_pred`` (B,).
    train_dataset, val_dataset : Dataset
        Each ``__getitem__`` returns 3-tuple or 4-tuple (see above).
    out_dir : str
        Directory for saving ``best_model.pt`` and ``metrics.json``.
    device : str
        ``'cpu'`` or ``'cuda'`` / ``'cuda:0'`` etc.
    epochs : int
        Maximum number of training epochs.
    batch_size : int
        Mini-batch size.
    lr : float
        Initial learning rate.
    weight_decay : float
        AdamW weight-decay coefficient.
    patience : int
        Early-stopping patience (epochs without improvement).
    grad_clip : float
        Max gradient norm for clipping.

    Returns
    -------
    dict
        Best validation metrics (val_loss, val_corr, val_r2, best_epoch).
    """
    os.makedirs(out_dir, exist_ok=True)
    device_obj = torch.device(device)
    model = model.to(device_obj)

    # --- detect input mode from dataset attribute or first sample ------------
    if hasattr(train_dataset, 'has_raw'):
        dual_path = train_dataset.has_raw
    else:
        sample = train_dataset[0]
        dual_path = len(sample) >= 4

    # Detect 5-tuple mode (with regime_prior)
    sample = train_dataset[0]
    has_regime_prior = len(sample) == 5

    # --- data loaders --------------------------------------------------------
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
    )

    # --- optimizer & scheduler -----------------------------------------------
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=lr, weight_decay=weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",       # maximize val_correlation
        factor=0.5,
        patience=max(patience // 2, 2),
        min_lr=1e-6,
    )

    # --- tracking ------------------------------------------------------------
    best_metrics: Dict[str, Any] = {}
    epochs_no_improve = 0

    for epoch in range(1, epochs + 1):
        # ===== Training =====
        model.train()
        train_loss_sum = 0.0
        train_steps = 0

        for batch in train_loader:
            if has_regime_prior:
                x_feat, x_raw, regime_prior, y, mask = batch
                x_feat = x_feat.to(device_obj)
                x_raw = x_raw.to(device_obj)
                regime_prior = regime_prior.to(device_obj)
                y = y.to(device_obj)
                mask = mask.to(device_obj)
                outputs = model(x_feat, x_raw, regime_prior=regime_prior)
            elif dual_path:
                x_feat, x_raw, y, mask = batch
                x_feat = x_feat.to(device_obj)
                x_raw = x_raw.to(device_obj)
                y = y.to(device_obj)
                mask = mask.to(device_obj)
                outputs = model(x_feat, x_raw)
            else:
                x_feat, y, mask = batch
                x_feat = x_feat.to(device_obj)
                y = y.to(device_obj)
                mask = mask.to(device_obj)
                outputs = model(x_feat)

            # Apply mask
            idx = mask.nonzero(as_tuple=True)[0]
            if len(idx) == 0:
                continue

            m_quantiles = outputs["quantiles"][idx]
            m_target = y[idx]

            loss = quantile_loss(m_quantiles, m_target)

            # NaN guard: skip pathological batches
            if not torch.isfinite(loss):
                optimizer.zero_grad()
                continue

            optimizer.zero_grad()
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            # Skip step if grad norm is inf/nan — clip_grad_norm_ can produce
            # NaN gradients when the original norm is huge (1e12+), which
            # corrupts model parameters on the next step.
            if not torch.isfinite(grad_norm):
                optimizer.zero_grad()
                continue
            optimizer.step()

            train_loss_sum += loss.item()
            train_steps += 1

        avg_train_loss = train_loss_sum / max(train_steps, 1)

        # ===== Validation =====
        model.eval()
        val_loss_sum = 0.0
        val_steps = 0
        metrics = OnlineMetrics()

        with torch.no_grad():
            for batch in val_loader:
                if has_regime_prior:
                    x_feat, x_raw, regime_prior, y, mask = batch
                    x_feat = x_feat.to(device_obj)
                    x_raw = x_raw.to(device_obj)
                    regime_prior = regime_prior.to(device_obj)
                    y = y.to(device_obj)
                    mask = mask.to(device_obj)
                    outputs = model(x_feat, x_raw, regime_prior=regime_prior)
                elif dual_path:
                    x_feat, x_raw, y, mask = batch
                    x_feat = x_feat.to(device_obj)
                    x_raw = x_raw.to(device_obj)
                    y = y.to(device_obj)
                    mask = mask.to(device_obj)
                    outputs = model(x_feat, x_raw)
                else:
                    x_feat, y, mask = batch
                    x_feat = x_feat.to(device_obj)
                    y = y.to(device_obj)
                    mask = mask.to(device_obj)
                    outputs = model(x_feat)

                # Apply mask
                idx = mask.nonzero(as_tuple=True)[0]
                if len(idx) == 0:
                    continue

                m_quantiles = outputs["quantiles"][idx]
                m_target = y[idx]

                loss = quantile_loss(m_quantiles, m_target)
                val_loss_sum += loss.item()
                val_steps += 1

                # Collect masked predictions for correlation / R2
                pred_np = outputs["point_pred"][idx].cpu().numpy()
                target_np = y[idx].cpu().numpy()
                metrics.update(pred_np, target_np)

        avg_val_loss = val_loss_sum / max(val_steps, 1)
        val_corr = metrics.corr()
        val_r2 = metrics.r2()

        # ===== LR scheduler step (on correlation) =====
        scheduler.step(val_corr)

        # ===== Epoch summary =====
        current_lr = optimizer.param_groups[0]["lr"]
        print(
            f"Epoch {epoch:3d}/{epochs} | "
            f"train_loss={avg_train_loss:.6f} | "
            f"val_loss={avg_val_loss:.6f} | "
            f"corr={val_corr:.4f} | "
            f"r2={val_r2:.4f} | "
            f"lr={current_lr:.2e}"
        )

        # ===== Early stopping & checkpointing (by CORRELATION) =====
        best_corr_so_far = best_metrics.get("val_corr", -1.0)
        if val_corr > best_corr_so_far + 1e-4:
            epochs_no_improve = 0
            best_metrics = {
                "best_epoch": epoch,
                "val_loss": avg_val_loss,
                "val_corr": val_corr,
                "val_r2": val_r2,
            }
            torch.save(model.state_dict(), os.path.join(out_dir, "best_model.pt"))
        else:
            epochs_no_improve += 1

        if epochs_no_improve >= patience:
            print(f"Early stopping at epoch {epoch} (patience={patience}).")
            break

    # --- persist metrics -----------------------------------------------------
    with open(os.path.join(out_dir, "metrics.json"), "w") as f:
        json.dump(best_metrics, f, indent=2)

    return best_metrics

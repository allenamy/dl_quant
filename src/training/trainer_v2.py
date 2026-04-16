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
import random
from typing import Any, Callable, Dict, Optional

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
# LR warmup helper
# ---------------------------------------------------------------------------

def _apply_warmup(
    step: int,
    warmup_steps: int,
    base_lr: float,
    optimizer: torch.optim.Optimizer,
) -> None:
    """Linearly ramp LR from ``base_lr / 100`` to ``base_lr`` over ``warmup_steps``.

    Called *before* ``optimizer.step()`` during the first ``warmup_steps``
    iterations.  After warmup, the caller should stop invoking this helper
    so that the main scheduler (e.g. ``ReduceLROnPlateau``) takes over.

    Uses a simple linear interpolation: at ``step=0`` the LR is
    ``base_lr * 0.01``; at ``step=warmup_steps-1`` the LR is ~``base_lr``.
    """
    if warmup_steps <= 0:
        return
    if step >= warmup_steps:
        return
    scale = (step + 1) / warmup_steps
    new_lr = base_lr * (0.01 + 0.99 * scale)
    for pg in optimizer.param_groups:
        pg["lr"] = new_lr


# ---------------------------------------------------------------------------
# Seed helper (ensemble-friendly)
# ---------------------------------------------------------------------------

def _seed_everything(seed: int) -> None:
    """Seed Python's ``random``, NumPy and PyTorch for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
# Checkpoint helper
# ---------------------------------------------------------------------------

def _extract_model_config(model: nn.Module) -> Dict[str, Any]:
    """Extract the construction-relevant config from a model for checkpointing.

    We save shape-determining attributes so that the loader can reinstantiate
    the model class without brittle state-dict key heuristics.

    Only simple scalar attributes are captured (n_features, n_levels,
    d_model, d_raw, etc.); anything missing is silently skipped.  If loading
    code needs a field not captured here, it should be added.
    """
    candidate_attrs = [
        "n_features", "n_levels", "d_model", "d_raw",
        "n_mask_blocks", "n_cross_layers", "patch_size",
        "attn_nhead", "attn_d_ff", "d_prior", "dropout",
        "n_horizons", "n_symbols", "use_monotonic_quantile",
        "n_quantiles",
        # V3 ablation bypass flags (Phase A2) -- persisting these lets a
        # checkpoint reinstantiate with the exact same module graph as at
        # training time, so ablation runs don't silently revert to "full V3".
        "use_masknet", "use_gdcn", "use_raw_path",
        "use_attention", "use_conv",
        # RevIN flag (Phase A3 non-stationarity mitigation)
        "use_revin",
    ]
    config: Dict[str, Any] = {}
    for attr in candidate_attrs:
        if hasattr(model, attr):
            val = getattr(model, attr)
            # Only record simple primitive types (not nn.Modules / tensors)
            if isinstance(val, (int, float, bool, str)):
                config[attr] = val
    return config


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
    warmup_steps_pct: float = 0.05,
    loss_fn: Optional[Callable[[Dict[str, torch.Tensor], torch.Tensor], torch.Tensor]] = None,
    seed: Optional[int] = None,
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
    warmup_steps_pct : float
        Fraction of *total* optimizer steps (``epochs * steps_per_epoch``)
        used for linear LR warmup.  The LR is ramped from ``lr/100`` to
        ``lr`` over that many steps, then the main ``ReduceLROnPlateau``
        scheduler takes over.  Set to ``0`` to disable warmup.
    loss_fn : callable, optional
        Signature ``loss_fn(outputs_dict, target) -> scalar tensor``.  When
        ``None`` (default) the trainer uses pure quantile loss on
        ``outputs["quantiles"]``.  Useful to swap in IC / rank / combined
        losses without changing the training loop.
    seed : int, optional
        If provided, seed Python / NumPy / PyTorch for ensemble-friendly
        deterministic training.  ``None`` (default) leaves global RNGs
        untouched.

    Returns
    -------
    dict
        Best validation metrics (val_loss, val_corr, val_r2, best_epoch).
    """
    # Seed *first* so DataLoader worker seeding / model init shuffle are
    # reproducible when the caller requested it.
    if seed is not None:
        _seed_everything(seed)

    os.makedirs(out_dir, exist_ok=True)
    device_obj = torch.device(device)
    model = model.to(device_obj)

    # Default loss: pure quantile on ``outputs["quantiles"]``
    if loss_fn is None:
        def loss_fn(outputs, target):  # type: ignore[no-redef]
            return quantile_loss(outputs["quantiles"], target)

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

    # --- warmup bookkeeping --------------------------------------------------
    # ``drop_last=True`` above, so steps_per_epoch = len(train_ds) // batch_size.
    steps_per_epoch = max(len(train_dataset) // batch_size, 1)
    total_steps = steps_per_epoch * epochs
    warmup_steps = int(total_steps * max(warmup_steps_pct, 0.0))
    global_step = 0

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

            # Masked outputs dict -- let loss_fn decide what it needs.
            m_outputs = {k: v[idx] for k, v in outputs.items() if torch.is_tensor(v)}
            m_target = y[idx]

            loss = loss_fn(m_outputs, m_target)

            # NaN guard: skip pathological batches
            if not torch.isfinite(loss):
                optimizer.zero_grad()
                global_step += 1
                continue

            optimizer.zero_grad()
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            # Skip step if grad norm is inf/nan — clip_grad_norm_ can produce
            # NaN gradients when the original norm is huge (1e12+), which
            # corrupts model parameters on the next step.
            if not torch.isfinite(grad_norm):
                optimizer.zero_grad()
                global_step += 1
                continue
            # Apply linear LR warmup *before* the optimizer step. Once past
            # ``warmup_steps`` this is a no-op and ReduceLROnPlateau owns the LR.
            _apply_warmup(global_step, warmup_steps, lr, optimizer)
            optimizer.step()

            train_loss_sum += loss.item()
            train_steps += 1
            global_step += 1

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

                m_outputs = {k: v[idx] for k, v in outputs.items() if torch.is_tensor(v)}
                m_target = y[idx]

                loss = loss_fn(m_outputs, m_target)
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
        if val_corr > best_corr_so_far + 5e-4:
            epochs_no_improve = 0
            best_metrics = {
                "best_epoch": epoch,
                "val_loss": avg_val_loss,
                "val_corr": val_corr,
                "val_r2": val_r2,
            }
            # Save checkpoint in new format: wraps state_dict with the model
            # class name so loaders can instantiate the right class without
            # brittle state-dict key heuristics. See run_backtest.py for the
            # matching loader (with fallback to raw state_dict for old ckpts).
            ckpt = {
                "state": model.state_dict(),
                "class": type(model).__name__,
                "config": _extract_model_config(model),
            }
            torch.save(ckpt, os.path.join(out_dir, "best_model.pt"))
        else:
            epochs_no_improve += 1

        if epochs_no_improve >= patience:
            print(f"Early stopping at epoch {epoch} (patience={patience}).")
            break

    # --- persist metrics -----------------------------------------------------
    with open(os.path.join(out_dir, "metrics.json"), "w") as f:
        json.dump(best_metrics, f, indent=2)

    return best_metrics

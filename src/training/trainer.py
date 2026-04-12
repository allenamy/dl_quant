"""Training loop, learning-rate scheduler, and online metrics for LOB Transformer V2."""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, Optional, TYPE_CHECKING

import numpy as np
import torch
from torch.utils.data import DataLoader

from .losses import combined_loss

if TYPE_CHECKING:
    from ..model.lob_transformer import LOBTransformerV2


# ---------------------------------------------------------------------------
# 1. Warmup + Cosine-Decay LR Scheduler
# ---------------------------------------------------------------------------

class WarmupCosineScheduler:
    """Linear warmup followed by cosine annealing to *min_lr*.

    Parameters
    ----------
    optimizer : torch.optim.Optimizer
        Wrapped optimizer.
    warmup_steps : int
        Number of steps for the linear warmup phase.
    total_steps : int
        Total number of training steps (warmup + cosine decay).
    min_lr : float
        Minimum learning rate at the end of cosine decay.
    """

    def __init__(
        self,
        optimizer: torch.optim.Optimizer,
        warmup_steps: int,
        total_steps: int,
        min_lr: float = 1e-6,
    ) -> None:
        self.optimizer = optimizer
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps
        self.min_lr = min_lr
        self._step_count = 0

        # Store the initial LR from each param group as the base LR.
        self.base_lrs = [pg["lr"] for pg in optimizer.param_groups]

    # ------------------------------------------------------------------
    def step(self) -> None:
        """Advance by one step and update all parameter-group LRs."""
        self._step_count += 1
        scale = self._compute_scale()
        for pg, base_lr in zip(self.optimizer.param_groups, self.base_lrs):
            pg["lr"] = self.min_lr + (base_lr - self.min_lr) * scale

    # ------------------------------------------------------------------
    def _compute_scale(self) -> float:
        s = self._step_count
        if s <= self.warmup_steps:
            # Linear warmup: 0 -> 1
            return s / max(self.warmup_steps, 1)
        # Cosine decay: 1 -> 0
        progress = (s - self.warmup_steps) / max(self.total_steps - self.warmup_steps, 1)
        progress = min(progress, 1.0)
        return 0.5 * (1.0 + math.cos(math.pi * progress))


# ---------------------------------------------------------------------------
# 2. Online (streaming) Metrics
# ---------------------------------------------------------------------------

class OnlineMetrics:
    """Welford-style online tracker for Pearson correlation and R-squared.

    Call :meth:`update` with batches of predictions / targets, then read
    :meth:`corr` and :meth:`r2` at any time without materialising full arrays.
    """

    def __init__(self) -> None:
        self.reset()

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.n: int = 0
        self.sum_p: float = 0.0
        self.sum_t: float = 0.0
        self.sum_pp: float = 0.0
        self.sum_tt: float = 0.0
        self.sum_pt: float = 0.0
        self.sum_se: float = 0.0  # sum of squared errors (pred - target)^2

    # ------------------------------------------------------------------
    def update(self, pred_array: np.ndarray, target_array: np.ndarray) -> None:
        """Incorporate a batch of predictions and targets.

        Parameters
        ----------
        pred_array : np.ndarray
            1-D array of predictions.
        target_array : np.ndarray
            1-D array of targets (same length).
        """
        p = np.asarray(pred_array, dtype=np.float64).ravel()
        t = np.asarray(target_array, dtype=np.float64).ravel()
        n = len(p)
        if n == 0:
            return

        self.n += n
        self.sum_p += p.sum()
        self.sum_t += t.sum()
        self.sum_pp += (p * p).sum()
        self.sum_tt += (t * t).sum()
        self.sum_pt += (p * t).sum()
        self.sum_se += ((p - t) ** 2).sum()

    # ------------------------------------------------------------------
    def corr(self) -> float:
        """Pearson correlation coefficient, or 0.0 on degenerate input."""
        if self.n <= 1:
            return 0.0
        n = self.n
        cov = (self.sum_pt - self.sum_p * self.sum_t / n) / n
        var_p = (self.sum_pp - self.sum_p ** 2 / n) / n
        var_t = (self.sum_tt - self.sum_t ** 2 / n) / n
        denom = math.sqrt(var_p * var_t) if (var_p > 0 and var_t > 0) else 0.0
        if denom == 0.0:
            return 0.0
        return cov / denom

    # ------------------------------------------------------------------
    def r2(self) -> float:
        """R-squared (coefficient of determination), or 0.0 on degenerate input."""
        if self.n <= 1:
            return 0.0
        mse = self.sum_se / self.n
        var_t = (self.sum_tt - self.sum_t ** 2 / self.n) / self.n
        if var_t <= 0.0:
            return 0.0
        return 1.0 - mse / var_t


# ---------------------------------------------------------------------------
# 3. Single-fold training loop
# ---------------------------------------------------------------------------

def train_one_fold(
    *,
    model: torch.nn.Module,
    train_dataset: "torch.utils.data.Dataset",
    val_dataset: "torch.utils.data.Dataset",
    out_dir: str,
    device: str = "cpu",
    epochs: int = 50,
    batch_size: int = 64,
    lr: float = 3e-4,
    weight_decay: float = 1e-4,
    patience: int = 10,
    grad_clip: float = 1.0,
    warmup_epochs: int = 5,
) -> Dict[str, Any]:
    """Train one cross-validation fold.

    Parameters
    ----------
    model : nn.Module
        LOBTransformerV2 (or any model whose forward returns a dict with
        keys ``quantiles``, ``direction_logits``, ``uncertainty``, ``point_pred``).
    train_dataset, val_dataset : Dataset
        Each ``__getitem__`` returns ``(x, y, mask)`` tensors.
    out_dir : str
        Directory for saving ``best_model.pt`` and ``metrics.json``.
    device : str
        ``'cpu'`` or ``'cuda'`` / ``'cuda:0'`` etc.
    epochs : int
        Maximum number of training epochs.
    batch_size : int
        Mini-batch size.
    lr : float
        Peak learning rate (after warmup).
    weight_decay : float
        AdamW weight-decay coefficient.
    patience : int
        Early-stopping patience (epochs without improvement).
    grad_clip : float
        Max gradient norm for clipping.
    warmup_epochs : int
        Number of epochs for the linear warmup phase.

    Returns
    -------
    dict
        Best validation metrics (loss, corr, r2, best_epoch).
    """
    os.makedirs(out_dir, exist_ok=True)
    device_obj = torch.device(device)
    model = model.to(device_obj)

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
    steps_per_epoch = len(train_loader)
    warmup_steps = warmup_epochs * steps_per_epoch
    total_steps = epochs * steps_per_epoch
    scheduler = WarmupCosineScheduler(
        optimizer,
        warmup_steps=warmup_steps,
        total_steps=total_steps,
    )

    # --- tracking ------------------------------------------------------------
    best_val_loss = float("inf")
    best_metrics: Dict[str, Any] = {}
    epochs_no_improve = 0

    for epoch in range(1, epochs + 1):
        # ===== Training =====
        model.train()
        train_loss_sum = 0.0
        train_steps = 0

        for x, y, mask in train_loader:
            x = x.to(device_obj)
            y = y.to(device_obj)
            mask = mask.to(device_obj)

            outputs = model(x)
            loss, loss_dict = combined_loss(outputs, y, mask)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
            scheduler.step()

            train_loss_sum += loss_dict["total"]
            train_steps += 1

        avg_train_loss = train_loss_sum / max(train_steps, 1)

        # ===== Validation =====
        model.eval()
        val_loss_sum = 0.0
        val_steps = 0
        metrics = OnlineMetrics()

        with torch.no_grad():
            for x, y, mask in val_loader:
                x = x.to(device_obj)
                y = y.to(device_obj)
                mask = mask.to(device_obj)

                outputs = model(x)
                loss, loss_dict = combined_loss(outputs, y, mask)

                val_loss_sum += loss_dict["total"]
                val_steps += 1

                # Collect masked predictions for correlation / R2.
                idx = mask.bool().nonzero(as_tuple=True)[0]
                if len(idx) > 0:
                    pred_np = outputs["point_pred"][idx].cpu().numpy()
                    target_np = y[idx].cpu().numpy()
                    metrics.update(pred_np, target_np)

        avg_val_loss = val_loss_sum / max(val_steps, 1)
        val_corr = metrics.corr()
        val_r2 = metrics.r2()

        # ===== Epoch summary =====
        print(
            f"Epoch {epoch:3d}/{epochs} | "
            f"train_loss={avg_train_loss:.6f} | "
            f"val_loss={avg_val_loss:.6f} | "
            f"corr={val_corr:.4f} | "
            f"r2={val_r2:.4f}"
        )

        # ===== Early stopping & checkpointing (by CORRELATION, not loss) =====
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

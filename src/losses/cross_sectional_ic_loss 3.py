"""Cross-sectional IC loss (multi-symbol Pearson rank).

At each timestep t, computes Pearson correlation of (pred, target) ACROSS
the symbols present at t. Returns mean of (1 - IC) over timesteps with
>= 2 valid symbols. For single-symbol training, returns 0 (no-op).

This is the loss design from HRT-RNN (`tf_train_hrt_rnn_v1.py`,
`masked_mtl_loss`) — the strongest signal in HRT's training pipeline,
which directly optimises rank-correlation across symbols rather than
time-series correlation.

For SINGLE asset (current state), this loss is a no-op — the interface
is wired now so multi-asset extension later is plug-and-play.

Shape conventions:
    pred, target: (T, S) or (T, S, H) — when 3D, computed per-horizon
                  then averaged.
    mask:         same shape, 1 where valid.

Usage:
    loss_cs = cross_sectional_ic_loss(pred_TSH, target_TSH, mask_TSH)
    total = primary_loss + lambda_cs * loss_cs
"""
from __future__ import annotations

import torch


def cross_sectional_ic_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    eps: float = 1e-6,
) -> torch.Tensor:
    """Returns mean over timesteps of (1 - cross-sectional Pearson IC).

    Parameters
    ----------
    pred, target : (T, S) or (T, S, H) tensors.
    mask : same shape; >0 marks valid (pred, target) entries.
    eps : numerical floor for the denominator (sqrt of variance product).

    Returns
    -------
    Scalar tensor in [0, 2]. Returns 0 when no timestep has >= 2 valid
    symbols (e.g. single-asset training).
    """
    if pred.dim() == 2:
        pred = pred.unsqueeze(-1)
        target = target.unsqueeze(-1)
        mask = mask.unsqueeze(-1)

    T, S, H = pred.shape
    if S < 2:
        return torch.zeros((), device=pred.device, dtype=pred.dtype)

    valid = (mask > 0) & torch.isfinite(pred) & torch.isfinite(target)
    v = valid.to(pred.dtype)
    count = v.sum(dim=1, keepdim=True)              # (T, 1, H)
    enough = (count.squeeze(1) >= 2.0)              # (T, H)
    if not enough.any():
        return torch.zeros((), device=pred.device, dtype=pred.dtype)

    p0 = torch.where(valid, pred, torch.zeros_like(pred))
    t0 = torch.where(valid, target, torch.zeros_like(target))
    mp = p0.sum(dim=1, keepdim=True) / torch.clamp(count, min=1.0)
    mt = t0.sum(dim=1, keepdim=True) / torch.clamp(count, min=1.0)
    pc = torch.where(valid, pred - mp, torch.zeros_like(pred))
    tc = torch.where(valid, target - mt, torch.zeros_like(target))
    num = (pc * tc).sum(dim=1)                      # (T, H)
    # Clamp σ_pred and σ_target SEPARATELY so the IC can't artificially
    # explode when one of them is near zero (a single-clamp on the product
    # would let num/den swing to ±1e3 if num is also small but nonzero).
    sp = torch.sqrt((pc * pc).sum(dim=1).clamp(min=eps))
    st = torch.sqrt((tc * tc).sum(dim=1).clamp(min=eps))
    ic = num / (sp * st)                             # (T, H)

    # Loss = mean over valid (timestep, horizon) of (1 - IC)
    losses = (1.0 - ic) * enough.to(pred.dtype)
    n_ok = enough.to(pred.dtype).sum().clamp(min=1.0)
    return losses.sum() / n_ok

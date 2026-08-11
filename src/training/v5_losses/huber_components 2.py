"""Huber loss on raw y for V5.

Huber loss: smooth interpolation between MSE (inner) and MAE (outer).
   L = 0.5·(y-μ)²   if |y-μ| ≤ δ
   L = δ·(|y-μ| - 0.5δ)   if |y-μ| > δ

For low-SNR finance (heavy tails), Huber's outlier robustness reduces gradient
contributions from extreme returns, leading to more stable optimization than
pure MSE while preserving magnitude prediction (unlike q50 pinball which
shrinks to median = unconditional mean).
"""
from __future__ import annotations
import torch


def loss_huber_y(
    mu: torch.Tensor,
    y: torch.Tensor,
    mask: torch.Tensor,
    delta: float = 1.0,
) -> torch.Tensor:
    """Huber loss between μ (prediction) and y (target) with masking."""
    if mask.dtype != torch.bool:
        mask = mask.bool()
    valid = mask & torch.isfinite(y) & torch.isfinite(mu)
    n = valid.sum()
    if n == 0:
        return (mu * 0.0).sum()

    diff = y - mu
    abs_diff = diff.abs()
    quad = 0.5 * diff * diff
    lin = delta * (abs_diff - 0.5 * delta)
    per_sample = torch.where(abs_diff <= delta, quad, lin)
    per_sample_clean = torch.where(valid, per_sample, torch.zeros_like(per_sample))
    return per_sample_clean.sum() / n.clamp(min=1).float()

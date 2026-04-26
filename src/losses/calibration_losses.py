"""Calibration losses: directional Huber + β (Mincer-Zarnowitz) regularizer.

These are designed to be added as light auxiliary terms to a primary
quantile loss. The goal is end-to-end magnitude calibration so that
live trading can use ŷ directly without post-hoc β scaling.

References:
- Mincer & Zarnowitz 1969 (forecast evaluation regression)
- Huber 1964 (robust regression)
- HRT-RNN training script (directional asymmetry inspired)
"""
from __future__ import annotations

import torch


def directional_huber_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    delta: float = 2.0,
    w_wrong: float = 2.0,
    w_extreme: float = 3.0,
) -> torch.Tensor:
    """Three-tier sign-aware Huber loss.

    Tier 1 (same sign): standard Huber.
    Tier 2 (wrong sign): standard Huber × (1 + w_wrong).
    Tier 3 (wrong sign AND |target| > 1.5): standard Huber × (1 + w_wrong + w_extreme).

    Use when you want magnitude calibration AND directional accuracy.

    Parameters
    ----------
    pred : (N,) predicted values (e.g. q50 from quantile head).
    target : (N,) realized values.
    delta : Huber transition point.
    w_wrong : extra weight on wrong-sign samples.
    w_extreme : additional extra weight when wrong-sign happens on |target|>1.5σ.

    Returns
    -------
    Scalar loss (mean across samples).
    """
    err = pred - target
    abs_err = err.abs()
    base = torch.where(
        abs_err < delta,
        0.5 * err.pow(2),
        delta * (abs_err - 0.5 * delta),
    )
    sign_disagree = (pred.sign() * target.sign() < 0).to(pred.dtype)
    extreme_miss = sign_disagree * (target.abs() > 1.5).to(pred.dtype)
    weight = 1.0 + w_wrong * sign_disagree + w_extreme * extreme_miss
    return (base * weight).mean()


def beta_calib_loss(pred: torch.Tensor, target: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    """Penalize batch-level Mincer-Zarnowitz β deviating from 1.

    β = cov(pred, target) / var(pred). β=1 ↔ σ_ŷ = ρ·σ_y (perfect magnitude
    calibration). Any deviation is squared-penalized.

    Use as a light regularizer (typical λ ≤ 0.1) alongside primary loss.
    Batch size should be ≥ 256 for stable β estimation.

    Parameters
    ----------
    pred : (N,) predicted values.
    target : (N,) realized values.
    eps : numerical floor for var(pred).

    Returns
    -------
    Scalar (β - 1)².
    """
    pc = pred - pred.mean()
    tc = target - target.mean()
    cov = (pc * tc).mean()
    var_p = (pc * pc).mean() + eps
    beta = cov / var_p
    return (beta - 1.0).pow(2)

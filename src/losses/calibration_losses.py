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


def soft_rank(x: torch.Tensor, temperature: float = 1.0) -> torch.Tensor:
    """Differentiable soft rank via sigmoid-of-pairwise-differences (soft Borda count).

    Each output is in [0.5, N-0.5]. Lower temperature → harder ranks (closer to
    integer). Higher temperature → smoother but lower-fidelity ranks.

    Cost: O(N²) memory + compute. For batch≤2048 this fits on a single GPU.

    Parameters
    ----------
    x : (N,) 1D tensor.
    temperature : sigmoid sharpness scaling. Default 1.0 assumes x is z-scored.

    Returns
    -------
    (N,) soft ranks. Differentiable w.r.t. x.
    """
    diff = x.unsqueeze(0) - x.unsqueeze(1)        # (N, N), entry (i,j) = x_i - x_j
    sig = torch.sigmoid(diff / temperature)       # (N, N), ≈ 1 if x_i > x_j
    return sig.sum(dim=0) - 0.5                   # (N,) Σ_j sigmoid(x_i > x_j)


def differentiable_spearman_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    temperature: float = 1.0,
    eps: float = 1e-8,
) -> torch.Tensor:
    """1 - Spearman rank correlation, fully differentiable.

    Spearman = Pearson correlation between rank(pred) and rank(target).
    We replace the non-diff rank op with `soft_rank` for end-to-end training.

    Standardize inputs to z-score before ranking, so default temperature=1.0
    gives reasonable rank fidelity.

    Loss is in [0, 2]. Loss=0 ↔ perfect rank correlation. Loss=1 ↔ uncorrelated.

    Parameters
    ----------
    pred : (N,) predictions (e.g. q50).
    target : (N,) realized values.
    temperature : passed to soft_rank.
    eps : numerical floor for std.

    Returns
    -------
    Scalar (1 - soft_spearman).
    """
    # z-score so soft_rank temperature has consistent meaning
    pn = (pred - pred.mean()) / (pred.std() + eps)
    tn = (target - target.mean()) / (target.std() + eps)
    rp = soft_rank(pn, temperature=temperature)
    rt = soft_rank(tn, temperature=temperature)
    rpc = rp - rp.mean()
    rtc = rt - rt.mean()
    cov = (rpc * rtc).mean()
    sp = rpc.std() + eps
    st = rtc.std() + eps
    spearman = cov / (sp * st)
    return 1.0 - spearman

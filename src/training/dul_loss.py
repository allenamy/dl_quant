"""Distributional Utility Loss (DUL) components for V4 training.

Three components combined via weighted sum, with λ=0 short-circuit for speed:
  1. L_quantile   — pinball loss on (q10, q50, q90). Reuses losses.quantile_loss.
  2. L_utility_rank — pairwise logistic rank loss on risk-adjusted score
                      s = q50 - alpha * (q50 - q10).
  3. L_calib      — batch-level quantile coverage penalty via sigmoid-smoothed
                    indicator so gradients flow into quantile predictions.

All three components return a scalar torch.Tensor.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import torch
import torch.nn.functional as F

from src.training.losses import quantile_loss


def utility_rank_loss(
    quantiles: torch.Tensor,
    target: torch.Tensor,
    *,
    alpha: float = 1.0,
    n_pairs: Optional[int] = None,
    margin: float = 0.0,
) -> torch.Tensor:
    """Pairwise logistic rank loss on risk-adjusted score.

    score s_i = q50_i - alpha * (q50_i - q10_i)
              = alpha * q10_i + (1 - alpha) * q50_i

    For sampled pairs (i, j):
      desired = sign(y_i - y_j)
      pred_diff = s_i - s_j
      loss_ij = softplus(-desired * pred_diff + margin)

    alpha=1.0  → s = q10 (fully pessimistic; rewards ranking by lower tail)
    alpha=0.0  → s = q50 (neutral point estimate)

    Args:
        quantiles: (N, 3+) where columns are [q10, q50, q90, ...].
        target:    (N,).
        alpha:     risk aversion weight on (q50 - q10) spread.
        n_pairs:   number of pairs to sample. Defaults to N.
        margin:    additive margin in the logistic term (default 0).

    Returns:
        Scalar mean loss. Zero when N < 2.
    """
    if quantiles.ndim != 2 or quantiles.shape[-1] < 3:
        raise ValueError(
            f"Expected (N, 3+) quantiles, got shape {tuple(quantiles.shape)}"
        )
    q10 = quantiles[:, 0]
    q50 = quantiles[:, 1]
    s = q50 - alpha * (q50 - q10)

    n = s.shape[0]
    if n < 2:
        return torch.zeros((), device=s.device, dtype=s.dtype)

    if n_pairs is None:
        n_pairs = n

    device = s.device
    i = torch.randint(0, n, (n_pairs,), device=device)
    j = torch.randint(0, n, (n_pairs,), device=device)
    # Avoid self-pairs by shifting collisions by 1 (mod n)
    collisions = (i == j)
    if collisions.any():
        j = torch.where(collisions, (j + 1) % n, j)

    y_diff = target[i] - target[j]
    desired = torch.sign(y_diff)
    pred_diff = s[i] - s[j]
    # softplus(x) = log(1 + e^x); numerically stable logistic loss
    return F.softplus(-desired * pred_diff + margin).mean()


def coverage_calib_loss(
    quantiles: torch.Tensor,
    target: torch.Tensor,
    *,
    taus: Tuple[float, ...] = (0.1, 0.5, 0.9),
) -> torch.Tensor:
    """Quantile-coverage calibration penalty (sigmoid-smoothed).

    c_τ = mean_i sigmoid(k * (q_τ(i) - y_i)), approximating P(y ≤ q_τ).
    Loss = Σ_τ (c_τ - τ)².

    The sigmoid smoothing (k=20) is sharp enough that gradients flow
    into the quantile predictions (vs. a hard y ≤ q indicator, which
    is non-differentiable).

    Args:
        quantiles: (N, 3+) where first 3 columns correspond to taus.
        target:    (N,).
        taus:      target quantile levels (default (0.1, 0.5, 0.9)).

    Returns:
        Scalar mean loss (sum of squared gaps across τ).
    """
    if quantiles.shape[-1] < len(taus):
        raise ValueError(
            f"Expected (N, >={len(taus)}) quantiles, got {tuple(quantiles.shape)}"
        )
    loss = torch.zeros((), device=quantiles.device, dtype=quantiles.dtype)
    for k, tau in enumerate(taus):
        q = quantiles[:, k]
        coverage = torch.sigmoid(20.0 * (q - target)).mean()
        loss = loss + (coverage - tau) ** 2
    return loss


def compute_dul_loss(
    quantiles: torch.Tensor,
    target: torch.Tensor,
    *,
    lambda_quantile: float = 1.0,
    lambda_utility_rank: float = 0.3,
    lambda_calib: float = 0.0,
    utility_alpha: float = 1.0,
    n_pairs: Optional[int] = None,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """Compose the three DUL components; each is computed only if λ > 0.

    Args:
        quantiles: (N, 3+) — [q10, q50, q90, ...].
        target:    (N,).
        lambda_quantile:     weight on pinball. Default 1.0.
        lambda_utility_rank: weight on rank loss. Default 0.3.
        lambda_calib:        weight on calibration. Default 0.0 (disabled).
        utility_alpha:       risk aversion for utility score. Default 1.0.
        n_pairs:             pairs to sample for rank loss. Default N.

    Returns:
        (total_loss, parts) where parts = dict with float values for each
        component plus the total. Components with λ=0 are reported as 0.0.
    """
    parts: Dict[str, float] = {}
    total = torch.zeros((), device=quantiles.device, dtype=quantiles.dtype)

    if lambda_quantile > 0.0:
        lq = quantile_loss(quantiles, target)
        parts["quantile"] = float(lq.item())
        total = total + lambda_quantile * lq
    else:
        parts["quantile"] = 0.0

    if lambda_utility_rank > 0.0:
        lu = utility_rank_loss(
            quantiles, target, alpha=utility_alpha, n_pairs=n_pairs,
        )
        parts["utility_rank"] = float(lu.item())
        total = total + lambda_utility_rank * lu
    else:
        parts["utility_rank"] = 0.0

    if lambda_calib > 0.0:
        lc = coverage_calib_loss(quantiles, target)
        parts["calib"] = float(lc.item())
        total = total + lambda_calib * lc
    else:
        parts["calib"] = 0.0

    parts["total"] = float(total.item())
    return total, parts

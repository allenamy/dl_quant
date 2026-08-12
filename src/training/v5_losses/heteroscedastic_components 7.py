"""Heteroscedastic NLL loss component for V5.

Gaussian NLL: model outputs (μ, log_σ) per sample; loss is
   L = 0.5 · (y-μ)² / σ² + 0.5 · log(σ²) + 0.5·log(2π)

log_σ is clipped to [log_sigma_min, log_sigma_max] inside the loss to prevent
σ → 0 (loss → ∞) or σ → ∞ (μ degenerate to 0).
"""
from __future__ import annotations
import math
import torch


def loss_gaussian_nll(
    mu: torch.Tensor,
    log_sigma: torch.Tensor,
    y: torch.Tensor,
    mask: torch.Tensor,
    log_sigma_min: float = -7.0,
    log_sigma_max: float = 2.0,
    include_const: bool = True,
) -> torch.Tensor:
    """Gaussian NLL loss with masking and log_sigma clipping."""
    if mask.dtype != torch.bool:
        mask = mask.bool()
    valid = mask & torch.isfinite(y) & torch.isfinite(mu) & torch.isfinite(log_sigma)
    n = valid.sum()
    if n == 0:
        return (mu * 0.0).sum()

    log_sigma_clipped = torch.clamp(log_sigma, min=log_sigma_min, max=log_sigma_max)
    inv_var = torch.exp(-2.0 * log_sigma_clipped)
    sq_err = (y - mu) ** 2

    per_sample = 0.5 * sq_err * inv_var + log_sigma_clipped
    if include_const:
        per_sample = per_sample + 0.5 * math.log(2 * math.pi)

    per_sample_clean = torch.where(valid, per_sample, torch.zeros_like(per_sample))
    return per_sample_clean.sum() / n.clamp(min=1).float()

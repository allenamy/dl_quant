"""Tail-focal weighting for regression loss.

Samples where |y| exceeds `threshold_sigma * sigma_y` receive
`1 + extra_weight` multiplier on their loss contribution. Addresses
quantile-regression's tendency to shrink predictions toward the median.

Reference: inspired by Lin 2017 (Focal Loss for classification), adapted
for continuous regression tails.
"""
import torch


def tail_focal_weights(
    y: torch.Tensor,
    sigma: float,
    extra_weight: float = 2.0,
    threshold_sigma: float = 2.0,
) -> torch.Tensor:
    """Returns per-sample weights: 1 if |y| <= threshold, else 1 + extra_weight.

    Parameters
    ----------
    y : (N,) target tensor.
    sigma : typical scale of y (MAD-sigma from train set).
    extra_weight : additional weight on tail samples.
    threshold_sigma : how many σ defines "tail".
    """
    is_tail = (y.abs() > threshold_sigma * sigma).to(y.dtype)
    return 1.0 + extra_weight * is_tail

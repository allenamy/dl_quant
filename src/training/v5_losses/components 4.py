"""Loss components for V5 dual-head training.

Each loss returns a scalar tensor (mean over valid samples). Functions are pure —
no in-place mutation, no global state — so they can be swapped/weighted via config.

Shape conventions:
- Most losses operate on flattened (N, H) tensors after caller reshapes.
- cs_ic operates on (..., S, H) where the last-but-one dim is symbol; auto-noop if S=1.

All losses respect mask (bool) and return a 0-tensor with requires_grad=True if no
valid samples (so backward doesn't break).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


def _masked_mean(x: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
    """Mean of x over valid==True; returns 0 with grad if no valid.

    Note: NaN * 0 = NaN, so we must use torch.where to fully zero invalid entries
    BEFORE summing, otherwise a single NaN in y propagates to the loss.
    """
    if valid.dtype != torch.bool:
        valid = valid.bool()
    n = valid.sum()
    if n == 0:
        return (x * 0.0).sum()
    x_clean = torch.where(valid, x, torch.zeros_like(x))
    return x_clean.sum() / n.clamp(min=1).float()


def loss_dir_margin(dir_logit: torch.Tensor, y: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Direction margin loss: push y × dir_logit to be positive.

    softplus(-y × dir_logit) is a smooth log(1 + exp(-margin)) hinge. When y and
    dir_logit have the same sign, margin > 0 and loss → 0; opposite sign → loss
    grows. Magnitude of dir_logit is implicitly regularized by softplus saturation.

    Note: y here is in the same scale as dir_logit (typically z-space). Sign is
    what matters; magnitude controls confidence.
    """
    valid = mask & torch.isfinite(y) & torch.isfinite(dir_logit) & (y != 0)
    margin = y * dir_logit
    per_sample = F.softplus(-margin)  # = log(1 + exp(-margin)), always ≥ 0
    return _masked_mean(per_sample, valid)


def loss_mag_huber(mag_pred: torch.Tensor, y: torch.Tensor, mask: torch.Tensor,
                   delta: float = 2.0) -> torch.Tensor:
    """Huber on |y| vs predicted magnitude.

    Predicted magnitude (≥ 0 from softplus) should match |y|. Huber (smooth_l1 with
    beta=delta) is robust to extreme |y| outliers, preventing tail samples from
    dominating gradient.
    """
    valid = mask & torch.isfinite(y) & torch.isfinite(mag_pred)
    abs_y = torch.abs(y)
    # smooth_l1_loss applies elementwise; mask out invalids to 0
    diff = mag_pred - abs_y
    # Huber: 0.5 * diff^2 if |diff| <= delta else delta * (|diff| - 0.5*delta)
    abs_diff = diff.abs()
    quad = 0.5 * diff * diff
    lin = delta * (abs_diff - 0.5 * delta)
    per_sample = torch.where(abs_diff <= delta, quad, lin)
    return _masked_mean(per_sample, valid)


def loss_joint_mse(y_pred: torch.Tensor, y: torch.Tensor, mask: torch.Tensor,
                   delta_huber: float = 0.0) -> torch.Tensor:
    """End-to-end MSE (or Huber if delta_huber>0) on combined dual-head output.

    THIS is the calibration anchor — without it, the two heads can drift apart
    (each learns its own bias) and the product accumulates error (ESMM-style).
    Use moderate weight (0.3-0.5 of total).

    delta_huber > 0 switches to Huber for outlier robustness; 0 uses pure MSE.
    """
    valid = mask & torch.isfinite(y) & torch.isfinite(y_pred)
    diff = y_pred - y
    if delta_huber > 0:
        abs_diff = diff.abs()
        quad = 0.5 * diff * diff
        lin = delta_huber * (abs_diff - 0.5 * delta_huber)
        per_sample = torch.where(abs_diff <= delta_huber, quad, lin)
    else:
        per_sample = diff * diff
    return _masked_mean(per_sample, valid)


def loss_cs_ic(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor,
               min_count: int = 2) -> torch.Tensor:
    """Cross-sectional IC loss (HRT-style).

    Computes Pearson IC across the symbol dimension at each (other-dims) slice,
    returns 1 - mean(IC) over valid slices.

    Shape conventions
    -----------------
    pred, target, mask : (..., S, H) where S is symbol dim, H is horizon dim.
    For single-asset (S=1): returns 0 with requires_grad=True (auto-noop).

    Returns
    -------
    Scalar loss. Lower = higher mean cross-sectional IC.
    """
    if pred.size(-2) < min_count:
        # Auto-noop for single asset
        return (pred * 0.0).sum()

    # Flatten leading dims to N, leaving (..., S, H) -> (N, S, H)
    p = pred.reshape(-1, pred.size(-2), pred.size(-1))
    t = target.reshape(-1, target.size(-2), target.size(-1))
    m = mask.reshape(-1, mask.size(-2), mask.size(-1)).bool()
    m = m & torch.isfinite(p) & torch.isfinite(t)

    valid_count = m.sum(dim=-2).clamp(min=1)  # (N, H)
    ok = (valid_count >= min_count)  # (N, H)

    if not ok.any():
        return (pred * 0.0).sum()

    # Compute mean across S for valid entries
    p_zeroed = torch.where(m, p, torch.zeros_like(p))
    t_zeroed = torch.where(m, t, torch.zeros_like(t))
    p_mean = p_zeroed.sum(dim=-2, keepdim=True) / valid_count.unsqueeze(-2).float()
    t_mean = t_zeroed.sum(dim=-2, keepdim=True) / valid_count.unsqueeze(-2).float()

    p_centered = torch.where(m, p - p_mean, torch.zeros_like(p))
    t_centered = torch.where(m, t - t_mean, torch.zeros_like(t))

    num = (p_centered * t_centered).sum(dim=-2)  # (N, H)
    den_sq = (p_centered * p_centered).sum(dim=-2) * (t_centered * t_centered).sum(dim=-2)
    den = torch.sqrt(den_sq.clamp(min=1e-8))
    ic = num / den  # (N, H)

    # 1 - mean(IC) over OK slices only
    ok_float = ok.float()
    n_ok = ok_float.sum().clamp(min=1)
    mean_ic = (ic * ok_float).sum() / n_ok
    return 1.0 - mean_ic


def loss_beta_consistency(y_pred: torch.Tensor, y: torch.Tensor, mask: torch.Tensor,
                          target_beta: float = 1.0) -> torch.Tensor:
    """Penalize deviation of predicted trade-slope β = cov(y, ŷ) / var(ŷ) from target.

    Using target_beta=1.0 forces calibration (ŷ should be unbiased magnitude estimate).
    Using target_beta<1 acknowledges shrinkage as feature.

    Useful as a small auxiliary (weight ~0.1) to nudge magnitude toward correct
    scale without forcing variance collapse (anti-pattern #11) like a hard MSE
    on σ_ŷ would.
    """
    valid = mask & torch.isfinite(y) & torch.isfinite(y_pred)
    if valid.sum() < 10:
        return (y_pred * 0.0).sum()
    yp = y_pred[valid]
    yt = y[valid]
    yp_centered = yp - yp.mean()
    yt_centered = yt - yt.mean()
    cov = (yp_centered * yt_centered).mean()
    var_yp = (yp_centered * yp_centered).mean().clamp(min=1e-12)
    beta = cov / var_yp
    return (beta - target_beta) ** 2

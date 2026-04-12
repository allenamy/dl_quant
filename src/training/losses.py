"""Loss functions for LOB Transformer V2.

Provides quantile, asymmetric Huber, direction (cross-entropy),
uncertainty (Gaussian NLL), and a weighted combined loss.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import torch
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# 1. Quantile (pinball) loss
# ---------------------------------------------------------------------------

def quantile_loss(
    pred_quantiles: torch.Tensor,
    target: torch.Tensor,
    quantiles: List[float] | None = None,
) -> torch.Tensor:
    """Pinball loss averaged over all quantiles and samples.

    Args:
        pred_quantiles: (B, n_quantiles) predicted quantile values.
        target: (B,) observed values.
        quantiles: list of tau values, default [0.1, 0.5, 0.9].

    Returns:
        Scalar mean pinball loss.
    """
    if quantiles is None:
        quantiles = [0.1, 0.5, 0.9]

    tau = torch.tensor(quantiles, dtype=pred_quantiles.dtype, device=pred_quantiles.device)
    # err shape: (B, n_quantiles)
    err = target.unsqueeze(-1) - pred_quantiles
    # pinball: max(tau * err, (tau - 1) * err)
    loss = torch.max(tau * err, (tau - 1.0) * err)
    return loss.mean()


# ---------------------------------------------------------------------------
# 2. Asymmetric Huber loss
# ---------------------------------------------------------------------------

def asymmetric_huber_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    delta: float = 2.0,
    neg_overestimate_weight: float = 2.0,
) -> torch.Tensor:
    """Huber loss with extra penalty when overestimating negative targets.

    "Overestimate of negative" means *target < 0* AND *pred > target*
    (prediction is less negative than actual), which understates risk.

    Args:
        pred: (B,) predictions.
        target: (B,) targets.
        delta: Huber threshold.
        neg_overestimate_weight: multiplier for overestimate-of-negative samples.

    Returns:
        Scalar mean loss.
    """
    diff = pred - target
    abs_diff = diff.abs()

    # Standard Huber loss per sample
    huber = torch.where(
        abs_diff <= delta,
        0.5 * diff ** 2,
        delta * (abs_diff - 0.5 * delta),
    )

    # Weight mask: target < 0 AND pred > target  =>  diff > 0
    overestimate_mask = (target < 0) & (pred > target)
    weight = torch.where(
        overestimate_mask,
        torch.tensor(neg_overestimate_weight, dtype=huber.dtype, device=huber.device),
        torch.tensor(1.0, dtype=huber.dtype, device=huber.device),
    )

    return (huber * weight).mean()


# ---------------------------------------------------------------------------
# 3. Direction loss (3-class cross-entropy)
# ---------------------------------------------------------------------------

def direction_loss(
    logits: torch.Tensor,
    target: torch.Tensor,
    threshold_bps: float = 2.0,
) -> torch.Tensor:
    """Cross-entropy on discretised return direction.

    Classes: 0=down (target < -thresh), 1=flat, 2=up (target > thresh).

    Args:
        logits: (B, 3) raw class scores.
        target: (B,) continuous return.
        threshold_bps: threshold in basis points.

    Returns:
        Scalar cross-entropy loss.
    """
    threshold = threshold_bps / 10_000.0

    labels = torch.ones(target.shape, dtype=torch.long, device=target.device)  # flat=1
    labels[target < -threshold] = 0  # down
    labels[target > threshold] = 2   # up

    return F.cross_entropy(logits, labels)


# ---------------------------------------------------------------------------
# 4. Uncertainty (Gaussian NLL) loss
# ---------------------------------------------------------------------------

def uncertainty_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    uncertainty: torch.Tensor,
) -> torch.Tensor:
    """Gaussian negative log-likelihood.

    0.5 * (log(var) + (target - pred)^2 / var)

    Args:
        pred: (B,) predicted mean.
        target: (B,) observed values.
        uncertainty: (B,) predicted variance (clamped to >= 1e-8).

    Returns:
        Scalar mean NLL.
    """
    var = uncertainty.clamp(min=1e-8)
    nll = 0.5 * (var.log() + (target - pred) ** 2 / var)
    # Regularize: penalize very large variance to prevent collapse to "always uncertain"
    var_penalty = 0.1 * var.mean()
    return nll.mean() + var_penalty


# ---------------------------------------------------------------------------
# 5. Combined loss
# ---------------------------------------------------------------------------

def combined_loss(
    outputs: Dict[str, torch.Tensor],
    target: torch.Tensor,
    mask: torch.Tensor,
    quantile_weight: float = 1.0,
    direction_weight: float = 0.3,
    uncertainty_weight: float = 0.05,
    asymmetric_weight: float = 1.0,
    **kwargs,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """Weighted sum of all component losses, applied only to valid (masked) samples.

    Args:
        outputs: dict with keys
            'quantiles'        (B, 3)
            'direction_logits' (B, 3)
            'uncertainty'      (B,)
            'point_pred'       (B,)
        target: (B,) continuous return targets.
        mask: (B,) bool tensor; True = valid sample.
        quantile_weight: weight for quantile loss.
        direction_weight: weight for direction loss.
        uncertainty_weight: weight for uncertainty loss.
        asymmetric_weight: weight for asymmetric Huber loss.
        **kwargs: forwarded to individual loss functions.

    Returns:
        (total_loss, loss_dict) where loss_dict maps component name to float.
    """
    # Apply mask ---------------------------------------------------------------
    idx = mask.nonzero(as_tuple=True)[0]
    m_target = target[idx]
    m_quantiles = outputs["quantiles"][idx]
    m_dir_logits = outputs["direction_logits"][idx]
    m_uncertainty = outputs["uncertainty"][idx]
    m_point = outputs["point_pred"][idx]

    # Component losses ---------------------------------------------------------
    l_quantile = quantile_loss(m_quantiles, m_target)
    l_direction = direction_loss(m_dir_logits, m_target)
    l_uncertainty = uncertainty_loss(m_point, m_target, m_uncertainty)
    l_asymmetric = asymmetric_huber_loss(m_point, m_target)

    total = (
        quantile_weight * l_quantile
        + direction_weight * l_direction
        + uncertainty_weight * l_uncertainty
        + asymmetric_weight * l_asymmetric
    )

    loss_dict = {
        "quantile": l_quantile.item(),
        "direction": l_direction.item(),
        "uncertainty": l_uncertainty.item(),
        "asymmetric": l_asymmetric.item(),
        "total": total.item(),
    }

    return total, loss_dict

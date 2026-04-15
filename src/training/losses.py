"""Loss functions for LOB models.

Active (V2/V3 pipeline):
    - ``quantile_loss``              -- pinball loss over [q10, q50, q90]
    - ``asymmetric_huber_loss``      -- optional risk-asymmetric point loss
    - ``rank_loss``                  -- pairwise ranking (scale-invariant)
    - ``ic_loss``                    -- 1 - Pearson corr (scale-invariant)
    - ``combined_ic_quantile_loss``  -- blend quantile + IC
    - ``directional_huber_loss``     -- Huber with wrong-direction penalty

DEPRECATED (legacy trainer.py + LOBTransformerV2 only):
    - ``direction_loss``       -- threshold-in-bps bug for normalized targets
    - ``uncertainty_loss``     -- Gaussian NLL, unused outside combined_loss
    - ``combined_loss``        -- 4-component weighted sum; caused gradient
                                  conflicts that drove model outputs to near-
                                  constant (see CLAUDE.md anti-patterns).

Do NOT use the deprecated losses in new code.  They are kept solely for
``src.training.trainer.train_one_fold`` backwards-compat with the old
``LOBTransformerV2`` model, which has a multi-head output
(direction_logits + uncertainty + point_pred).  All V2/V3 models use
``quantile_loss`` via ``trainer_v2``.

Rationale for the new scale-invariant losses
--------------------------------------------
At R^2 < 1% the quantile loss can degenerate to predicting unconditional
quantiles (flat prediction).  Rank / IC losses focus purely on the
*ordering* of pred vs target, which is what matters for trading decisions
(direction + confidence).  ``combined_ic_quantile_loss`` hedges between
proper probabilistic intervals and ordering.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

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
    """DEPRECATED: Cross-entropy on discretised return direction.

    Known bugs (see CLAUDE.md anti-patterns):
    - ``threshold_bps`` assumes ``target`` is in raw fractional returns; if
      the caller passes normalized targets (standard in V2/V3 pipelines),
      the threshold is meaningless.
    - Not called by any active trainer; kept only for ``combined_loss``
      backward compatibility with the legacy trainer.py + LOBTransformerV2.

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
    """DEPRECATED: Gaussian negative log-likelihood.

    Not called by any active trainer; kept only for ``combined_loss``
    backward compatibility with the legacy trainer.py + LOBTransformerV2.

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
    """DEPRECATED: Weighted sum of all component losses.

    Only the legacy ``trainer.py`` + ``LOBTransformerV2`` call this.  Known
    issues:
    - 4-component gradient conflict caused model outputs to converge to
      near-constant (see CLAUDE.md anti-pattern #3, "4 个 loss 同时训练").
    - Expects output keys ``direction_logits`` and ``uncertainty`` that
      V2/V3 models do NOT produce.
    - Uses ``direction_loss`` with the bps-unit threshold bug.

    All new training code should use ``quantile_loss`` via ``trainer_v2``.


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


# ---------------------------------------------------------------------------
# 6. Rank (pairwise) loss -- scale-invariant ordering loss
# ---------------------------------------------------------------------------

def rank_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    n_pairs: Optional[int] = None,
    margin: float = 0.0,
) -> torch.Tensor:
    """Pairwise ranking loss (differentiable Spearman approximation).

    For each sampled pair (i, j), i != j:
        desired_diff = sign(target_i - target_j)
        pred_diff    = pred_i - pred_j
        loss_ij      = max(0, -desired_diff * pred_diff + margin)

    The mean over pairs is returned.  Because the loss only depends on the
    *ordering* of ``target``, any monotone transform of the predictions
    yielding the same ranks produces the same loss (scale-invariance).

    To avoid the O(N^2) cost of enumerating all pairs we sub-sample
    ``n_pairs`` random pairs.  When ``n_pairs`` is ``None`` we default to
    ``B`` (one pair per sample on average).

    Pairs where ``target_i == target_j`` contribute ``max(0, margin)`` which
    is zero when ``margin=0``.  This means "ties" are ignored rather than
    biased.

    Args:
        pred: (B,) predictions.
        target: (B,) targets.
        n_pairs: number of pairs to sample.  Defaults to ``B``.
        margin: hinge margin.  ``0`` gives a soft sign-agreement loss.

    Returns:
        Scalar mean hinge loss.  If ``B < 2`` returns ``0``.
    """
    B = pred.shape[0]
    if B < 2:
        return pred.new_zeros(())

    if n_pairs is None:
        n_pairs = B

    # Scale-invariance: standardise pred *inside* the loss so that any
    # affine transform of pred (scale + shift) yields the same loss.  We
    # use ``unbiased=False`` so the normalisation is deterministic w.r.t.
    # population.  A small epsilon guards against zero-variance pred.
    pred_std = pred.std(unbiased=False)
    pred_norm = (pred - pred.mean()) / (pred_std + 1e-8)

    # Sample random pairs (i, j) with i != j. Resample any collisions.
    device = pred.device
    i = torch.randint(0, B, (n_pairs,), device=device)
    j = torch.randint(0, B, (n_pairs,), device=device)
    # Resample collisions in a loop-free way: shift j by 1 where equal.
    collisions = (i == j)
    if collisions.any():
        j = torch.where(collisions, (j + 1) % B, j)

    desired = torch.sign(target[i] - target[j])
    pred_diff = pred_norm[i] - pred_norm[j]
    # hinge: max(0, margin - desired * pred_diff)
    raw = margin - desired * pred_diff
    loss = torch.clamp(raw, min=0.0)
    return loss.mean()


# ---------------------------------------------------------------------------
# 7. IC (Pearson-correlation) loss -- scale-invariant
# ---------------------------------------------------------------------------

def ic_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    eps: float = 1e-8,
) -> torch.Tensor:
    """Negative Pearson correlation as a loss.

    ``loss = 1 - corr(pred, target)``

    The loss is scale-invariant (corr doesn't care about scale/offset) and
    commonly used in quantitative finance (IC = Information Coefficient).
    Value is in ``[0, 2]`` (``0`` = perfectly correlated, ``2`` = perfectly
    anti-correlated).

    Args:
        pred: (B,) predictions.
        target: (B,) targets.
        eps: numerical stabilizer added to the std-product denominator.

    Returns:
        Scalar loss.
    """
    if pred.numel() < 2:
        return pred.new_zeros(())

    pred_c = pred - pred.mean()
    target_c = target - target.mean()
    cov = (pred_c * target_c).mean()
    std = pred_c.std(unbiased=False) * target_c.std(unbiased=False) + eps
    return 1.0 - cov / std


# ---------------------------------------------------------------------------
# 8. Combined IC + quantile loss
# ---------------------------------------------------------------------------

def combined_ic_quantile_loss(
    outputs: Dict[str, torch.Tensor],
    target: torch.Tensor,
    ic_weight: float = 0.5,
    quantile_weight: float = 0.5,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """Weighted sum of IC loss and quantile (pinball) loss.

    Hedges between:
      * Quantile loss: learns proper probabilistic intervals (q10/q50/q90).
      * IC loss:       learns ordering / direction (scale-invariant).

    Args:
        outputs: dict with at least the key ``"quantiles"`` (B, n_quantiles).
            The median column (index ``n_quantiles // 2``) is used as the
            point prediction for the IC term unless ``"point_pred"`` is
            present, in which case it is preferred.
        target: (B,) target values.
        ic_weight: weight on ``ic_loss``.
        quantile_weight: weight on ``quantile_loss``.

    Returns:
        ``(total_loss, loss_dict)`` with per-component scalars for logging.
    """
    q = outputs["quantiles"]
    if "point_pred" in outputs:
        point = outputs["point_pred"]
    else:
        # Median column (works for any odd n_quantiles incl. 3)
        point = q[:, q.shape[1] // 2]

    l_quantile = quantile_loss(q, target)
    l_ic = ic_loss(point, target)

    total = quantile_weight * l_quantile + ic_weight * l_ic

    loss_dict = {
        "quantile": l_quantile.item(),
        "ic": l_ic.item(),
        "total": total.item(),
    }
    return total, loss_dict


# ---------------------------------------------------------------------------
# 9. Directional Huber loss -- wrong-direction penalty
# ---------------------------------------------------------------------------

def directional_huber_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    delta: float = 1.0,
    direction_weight: float = 2.0,
) -> torch.Tensor:
    """Huber loss with an extra multiplicative penalty on wrong-direction preds.

    A sample is considered "wrong direction" when
    ``sign(pred) != sign(target)`` AND both are nonzero.  For such samples
    the per-sample Huber loss is multiplied by ``direction_weight`` (>= 1).
    Zero-valued target or pred are treated as "neutral" (no penalty).

    This prioritises getting direction right over getting magnitude right,
    which is what matters for trading decisions.

    Args:
        pred: (B,) predictions.
        target: (B,) targets.
        delta: Huber transition threshold.
        direction_weight: multiplier applied to wrong-direction samples
            (must be >= 1 to make "wrong" strictly harder than "right").

    Returns:
        Scalar mean loss.
    """
    diff = pred - target
    abs_diff = diff.abs()

    huber = torch.where(
        abs_diff <= delta,
        0.5 * diff ** 2,
        delta * (abs_diff - 0.5 * delta),
    )

    sp = torch.sign(pred)
    st = torch.sign(target)
    # Wrong direction only when BOTH have a definite sign and they differ.
    wrong = (sp != st) & (sp != 0) & (st != 0)
    weight = torch.where(
        wrong,
        torch.tensor(direction_weight, dtype=huber.dtype, device=huber.device),
        torch.tensor(1.0, dtype=huber.dtype, device=huber.device),
    )

    return (huber * weight).mean()

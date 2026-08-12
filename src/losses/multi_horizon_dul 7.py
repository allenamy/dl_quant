"""Multi-horizon DUL+ loss module for V4-style trainer_v2.

Composes:
  • Per-horizon pinball (quantile) loss with per-sample tail-focal weighting
  • Per-horizon pairwise utility-rank loss (same as V4 DUL)
  • Inter-horizon aggregation via Kendall 2018 UNIT uncertainty weighting
    (learnable log_vars) OR static weighted sum fallback.

Interface: the module is passed to ``trainer_v2.train_one_fold_v2`` as
``multi_horizon_loss_module``. The trainer detects this and skips its
built-in ``_multi_horizon_loss`` aggregator. The caller is responsible
for adding ``module.parameters()`` to the optimizer — otherwise the
UNIT log_vars stay frozen and the method degenerates.

No data-leakage concerns: the module is stateless across batches except
for learnable log_vars. All inputs come from the current mini-batch.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.losses.unit_loss import UnitMultiTaskLoss
from src.losses.focal_weighting import tail_focal_weights
from src.losses.calibration_losses import (
    directional_huber_loss,
    beta_calib_loss,
    differentiable_spearman_loss,
)


def _weighted_pinball(
    pred_quantiles: torch.Tensor,   # (N, Q)
    target: torch.Tensor,           # (N,)
    sample_weights: torch.Tensor,   # (N,)
    taus: Tuple[float, ...] = (0.1, 0.5, 0.9),
) -> torch.Tensor:
    tau_t = torch.tensor(taus, dtype=pred_quantiles.dtype, device=pred_quantiles.device)
    err = target.unsqueeze(-1) - pred_quantiles                 # (N, Q)
    per_qtau = torch.max(tau_t * err, (tau_t - 1.0) * err)      # (N, Q)
    per_sample = per_qtau.mean(dim=-1)                          # (N,)
    w_sum = sample_weights.sum().clamp_min(1e-6)
    return (per_sample * sample_weights).sum() / w_sum


def _utility_rank_loss(
    quantiles: torch.Tensor,        # (N, >=3) cols [q10, q50, q90]
    target: torch.Tensor,           # (N,)
    alpha: float = 1.0,
    n_pairs: Optional[int] = None,
) -> torch.Tensor:
    q10 = quantiles[:, 0]
    q50 = quantiles[:, 1]
    s = q50 - alpha * (q50 - q10)   # = alpha*q10 + (1-alpha)*q50
    n = s.shape[0]
    if n < 2:
        return torch.zeros((), device=s.device, dtype=s.dtype)
    if n_pairs is None:
        n_pairs = n
    device = s.device
    i = torch.randint(0, n, (n_pairs,), device=device)
    j = torch.randint(0, n, (n_pairs,), device=device)
    collisions = (i == j)
    if collisions.any():
        j = torch.where(collisions, (j + 1) % n, j)
    y_diff = target[i] - target[j]
    desired = torch.sign(y_diff)
    pred_diff = s[i] - s[j]
    return F.softplus(-desired * pred_diff).mean()


class MultiHorizonDulFocalUnit(nn.Module):
    """Multi-horizon DUL+ loss with focal weighting and UNIT aggregation.

    Parameters
    ----------
    n_horizons : int
        Number of horizons (e.g. 2 for [y_180, y_600]).
    y_sigmas : list[float]
        Per-horizon MAD-sigma of training y, used to normalise focal threshold.
        Since y is already z-scored via y_norm in the dataset, these default
        to 1.0 per horizon — pass actual sigma only when y is unnormalised.
    use_unit : bool
        When True, uses ``UnitMultiTaskLoss`` to aggregate per-horizon losses
        with learnable uncertainty weights. When False, falls back to simple
        mean across contributing horizons.
    focal_extra_weight : float
        Extra multiplier on tail samples (|y| > threshold_sigma * sigma).
        Zero disables focal weighting entirely.
    focal_threshold_sigma : float
        How many σ defines "tail".
    lambda_quantile : float
        Weight on pinball loss component (default 1.0).
    lambda_rank : float
        Weight on utility-rank loss component (default 0.3 matches V4 DUL).
    utility_alpha : float
        Risk aversion weight for rank-loss score.
    lambda_dir_huber : float
        Weight on directional-Huber on q50 (default 0.0 — disabled).
    lambda_beta_calib : float
        Weight on Mincer-Zarnowitz β-regularizer on q50 (default 0.0 — disabled).
    dir_huber_delta, dir_huber_w_wrong, dir_huber_w_extreme : float
        Directional-Huber params (see calibration_losses.directional_huber_loss).
    """

    def __init__(
        self,
        n_horizons: int,
        y_sigmas: Optional[List[float]] = None,
        *,
        use_unit: bool = True,
        horizon_weights: Optional[List[float]] = None,
        focal_extra_weight: float = 2.0,
        focal_threshold_sigma: float = 2.0,
        lambda_quantile: float = 1.0,
        lambda_rank: float = 0.3,
        utility_alpha: float = 1.0,
        lambda_dir_huber: float = 0.0,
        lambda_beta_calib: float = 0.0,
        lambda_diff_spearman: float = 0.0,
        diff_spearman_temperature: float = 1.0,
        dir_huber_delta: float = 2.0,
        dir_huber_w_wrong: float = 2.0,
        dir_huber_w_extreme: float = 3.0,
        # v5push Phase 3: classification head BCE term for DirAcc.
        # Reads outputs["sign_logit"] (B,) if present; BCE against (y > 0).
        # Keep λ_cls small (0.05-0.10) to avoid anti-pattern #10 multi-task conflict.
        lambda_cls: float = 0.0,
    ) -> None:
        super().__init__()
        if n_horizons < 1:
            raise ValueError(f"n_horizons must be >= 1, got {n_horizons}")
        self.n_horizons = int(n_horizons)
        self.y_sigmas = list(y_sigmas) if y_sigmas is not None else [1.0] * n_horizons
        if len(self.y_sigmas) != self.n_horizons:
            raise ValueError(
                f"y_sigmas length {len(self.y_sigmas)} != n_horizons {n_horizons}"
            )
        self.use_unit = bool(use_unit)
        self.horizon_weights = (
            list(horizon_weights) if horizon_weights is not None else [1.0] * n_horizons
        )
        if len(self.horizon_weights) != self.n_horizons:
            raise ValueError(
                f"horizon_weights length {len(self.horizon_weights)} != n_horizons {n_horizons}"
            )
        self.focal_extra_weight = float(focal_extra_weight)
        self.focal_threshold_sigma = float(focal_threshold_sigma)
        self.lambda_quantile = float(lambda_quantile)
        self.lambda_rank = float(lambda_rank)
        self.utility_alpha = float(utility_alpha)
        self.lambda_dir_huber = float(lambda_dir_huber)
        self.lambda_beta_calib = float(lambda_beta_calib)
        self.lambda_diff_spearman = float(lambda_diff_spearman)
        self.diff_spearman_temperature = float(diff_spearman_temperature)
        self.dir_huber_delta = float(dir_huber_delta)
        self.dir_huber_w_wrong = float(dir_huber_w_wrong)
        self.dir_huber_w_extreme = float(dir_huber_w_extreme)
        self.lambda_cls = float(lambda_cls)

        if self.use_unit:
            self.unit = UnitMultiTaskLoss(n_tasks=n_horizons)
        else:
            self.unit = None

    def forward(
        self,
        outputs: Dict[str, torch.Tensor],
        y: torch.Tensor,
        mask: torch.Tensor,
    ) -> Optional[torch.Tensor]:
        """Compute aggregated multi-horizon loss.

        Parameters
        ----------
        outputs : dict containing
            - ``quantiles_by_horizon``: (B, n_h, Q)
            - ``point_pred_by_horizon``: (B, n_h)
        y : (B, n_h) targets.
        mask : (B, n_h) per-horizon validity (float or int; >0 means valid).

        Returns
        -------
        Scalar tensor or None. None when every horizon's mask is all-zero.
        """
        if "quantiles_by_horizon" not in outputs:
            raise KeyError(
                "MultiHorizonDulFocalUnit requires outputs['quantiles_by_horizon']"
            )
        q_by_h = outputs["quantiles_by_horizon"]  # (B, n_h, Q)
        B, n_h, Q = q_by_h.shape
        if n_h != self.n_horizons:
            raise ValueError(
                f"model emitted {n_h} horizons, loss was built for {self.n_horizons}"
            )

        per_horizon_losses: List[torch.Tensor] = []
        contributing: List[int] = []
        for h in range(n_h):
            mask_h = mask[:, h]
            idx = mask_h.nonzero(as_tuple=True)[0]
            if idx.numel() == 0:
                continue
            q_h = q_by_h[idx, h, :]      # (n, Q)
            y_h = y[idx, h]              # (n,)

            # Focal weights (1.0 for non-tail samples, 1+extra for tails).
            if self.focal_extra_weight > 0.0:
                weights = tail_focal_weights(
                    y_h,
                    sigma=float(self.y_sigmas[h]),
                    extra_weight=self.focal_extra_weight,
                    threshold_sigma=self.focal_threshold_sigma,
                )
            else:
                weights = torch.ones_like(y_h)

            pinball = _weighted_pinball(q_h, y_h, weights)

            if self.lambda_rank > 0.0:
                rank = _utility_rank_loss(q_h, y_h, alpha=self.utility_alpha)
            else:
                rank = torch.zeros((), device=q_h.device, dtype=q_h.dtype)

            # Directional Huber on q50 (sign-aware magnitude calibration).
            if self.lambda_dir_huber > 0.0:
                dh = directional_huber_loss(
                    q_h[:, 1], y_h,
                    delta=self.dir_huber_delta,
                    w_wrong=self.dir_huber_w_wrong,
                    w_extreme=self.dir_huber_w_extreme,
                )
            else:
                dh = torch.zeros((), device=q_h.device, dtype=q_h.dtype)

            # Mincer-Zarnowitz β-regularizer on q50 (need batch ≥ 256 for stability).
            if self.lambda_beta_calib > 0.0 and y_h.numel() >= 256:
                bc = beta_calib_loss(q_h[:, 1], y_h)
            else:
                bc = torch.zeros((), device=q_h.device, dtype=q_h.dtype)

            # Differentiable Spearman (soft-rank Pearson). Direct rank loss.
            # Need batch ≥ 64 for sane rank statistics; O(N²) memory caps batch.
            if (
                self.lambda_diff_spearman > 0.0
                and y_h.numel() >= 64
                and y_h.numel() <= 2048
            ):
                dsp = differentiable_spearman_loss(
                    q_h[:, 1], y_h,
                    temperature=self.diff_spearman_temperature,
                )
            else:
                dsp = torch.zeros((), device=q_h.device, dtype=q_h.dtype)

            # v5push Phase 3: BCE on sign_logit (for DirAcc dual-task)
            if self.lambda_cls > 0.0 and "sign_logit" in outputs:
                # sign_logit may be (B,) (single horizon) or (B, n_h) (multi).
                _sl = outputs["sign_logit"]
                if _sl.dim() == 1:
                    sl_h = _sl[idx]
                else:
                    sl_h = _sl[idx, h]
                # Target: y > 0 ⇒ 1, else 0. Zero-y samples treated as 0 (slight bias toward neg-down).
                cls_target = (y_h > 0.0).to(sl_h.dtype)
                cls = torch.nn.functional.binary_cross_entropy_with_logits(sl_h, cls_target)
            else:
                cls = torch.zeros((), device=q_h.device, dtype=q_h.dtype)

            l_h = (
                self.lambda_quantile * pinball
                + self.lambda_rank * rank
                + self.lambda_dir_huber * dh
                + self.lambda_beta_calib * bc
                + self.lambda_diff_spearman * dsp
                + self.lambda_cls * cls
            )
            per_horizon_losses.append(l_h)
            contributing.append(h)

        if not per_horizon_losses:
            return None

        if self.use_unit and self.unit is not None and len(contributing) == self.n_horizons:
            return self.unit(per_horizon_losses)

        # Weighted sum across contributing horizons. Used when use_unit=False
        # or when any horizon has zero unmasked samples this batch (UNIT
        # expects fixed n_tasks losses, so we degrade gracefully).
        w = [self.horizon_weights[h] for h in contributing]
        stacked = torch.stack(per_horizon_losses)
        w_tensor = torch.tensor(w, dtype=stacked.dtype, device=stacked.device)
        return (stacked * w_tensor).sum() / w_tensor.sum().clamp_min(1e-6)

"""DUL+ loss: pinball + CRPS + utility_rank + focal + UNIT + decorrelation.

Composition:
  For each horizon h:
    w_h     = tail_focal_weights(y_h, sigma_h, focal_weight, focal_threshold_sigma)
    l_pin_h = weighted mean-pinball (focal)
    l_crps_h = weighted CRPS-surrogate (focal)  [same math as pinball at 3 taus]
    l_rank_h = utility_rank_loss(q_h, y_h)       [ranking; no focal needed]
    l_h     = l_pin_h + gamma_crps * l_crps_h + eta_utility * l_rank_h

  total = UnitMultiTaskLoss([l_0, ..., l_{H-1}])
  total += alpha_decorr * decorrelation_loss(embedding)  [if embedding given]

Note on pinball/CRPS duplication
---------------------------------
_pinball_weighted and _crps_weighted implement identical mathematics.
CRPS (at K quantiles) IS the mean-pinball integral approximation. Concretely,
with gamma_crps=0.5 and 3 taus this becomes 1.5 × weighted-pinball — a stable
and intentional up-weighting of distributional calibration. The design keeps
them as separate named terms so callers can zero out gamma_crps to ablate the
CRPS contribution without touching the base pinball weight.
"""
from typing import List, Tuple, Optional

import torch
import torch.nn as nn

from src.losses.unit_loss import UnitMultiTaskLoss
from src.losses.focal_weighting import tail_focal_weights
from src.losses.decorrelation_loss import decorrelation_loss
from src.training.dul_loss import utility_rank_loss


class DulPlusLoss(nn.Module):
    """Composite loss for V5-LH multi-horizon quantile training.

    Parameters
    ----------
    n_horizons : int
        Number of prediction horizons (= number of quantile heads).
    y_sigmas : tuple of float, length n_horizons
        Typical scale (e.g. MAD-sigma from training set) of each horizon's
        target. Used by tail_focal_weights to identify tail samples.
    gamma_crps : float
        Weight on the CRPS surrogate term (default 0.5).
    eta_utility : float
        Weight on the utility-rank pairwise loss (default 0.3).
    alpha_decorr : float
        Weight on the embedding decorrelation penalty (default 0.1).
        Set to 0.0 to disable without passing an embedding.
    focal_weight : float
        Extra weight multiplier applied to tail samples (default 2.0).
    focal_threshold_sigma : float
        Number of sigma beyond which a sample is considered a tail sample
        (default 2.0).
    taus : tuple of float
        Quantile levels. Must match the last dim of each quantile tensor
        passed to forward (default (0.1, 0.5, 0.9)).
    """

    def __init__(
        self,
        n_horizons: int,
        y_sigmas: Tuple[float, ...],
        gamma_crps: float = 0.5,
        eta_utility: float = 0.3,
        alpha_decorr: float = 0.1,
        focal_weight: float = 2.0,
        focal_threshold_sigma: float = 2.0,
        taus: Tuple[float, ...] = (0.1, 0.5, 0.9),
    ):
        super().__init__()
        if len(y_sigmas) != n_horizons:
            raise ValueError(
                f"len(y_sigmas)={len(y_sigmas)} must equal n_horizons={n_horizons}"
            )
        self.n_horizons = n_horizons
        self.y_sigmas = y_sigmas
        self.gamma_crps = gamma_crps
        self.eta_utility = eta_utility
        self.alpha_decorr = alpha_decorr
        self.focal_weight = focal_weight
        self.focal_threshold_sigma = focal_threshold_sigma
        self.taus = taus

        self.unit = UnitMultiTaskLoss(n_tasks=n_horizons)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _weighted_pinball(
        self,
        quantiles: torch.Tensor,
        y: torch.Tensor,
        weights: torch.Tensor,
    ) -> torch.Tensor:
        """Focal-weighted mean-pinball loss.

        Per-sample loss = mean_k pinball(y, q_k).
        Returns weighted mean over the batch.

        Args:
            quantiles : (N, K)
            y         : (N,)
            weights   : (N,) non-negative focal multipliers
        """
        tau_t = torch.tensor(
            self.taus, dtype=quantiles.dtype, device=quantiles.device
        )
        diffs = y.unsqueeze(-1) - quantiles       # (N, K)
        pb = torch.max(tau_t * diffs, (tau_t - 1.0) * diffs)  # (N, K)
        per_sample = pb.mean(dim=-1)              # (N,)
        return (per_sample * weights).mean()

    # ------------------------------------------------------------------
    # Forward
    # ------------------------------------------------------------------

    def forward(
        self,
        quantiles_by_h: List[torch.Tensor],     # list[(N, K)] per horizon
        targets_by_h: List[torch.Tensor],       # list[(N,)]   per horizon
        embedding: Optional[torch.Tensor] = None,  # (N, d) optional
    ) -> torch.Tensor:
        """Compute DUL+ composite loss.

        Args:
            quantiles_by_h : predicted quantiles, one (N, K) tensor per horizon.
            targets_by_h   : realized targets, one (N,) tensor per horizon.
            embedding      : optional (N, d) embedding for decorrelation term.

        Returns:
            Scalar loss tensor with full backward graph.
        """
        if len(quantiles_by_h) != self.n_horizons:
            raise ValueError(
                f"Expected {self.n_horizons} horizon tensors, "
                f"got {len(quantiles_by_h)}"
            )
        if len(targets_by_h) != self.n_horizons:
            raise ValueError(
                f"Expected {self.n_horizons} target tensors, "
                f"got {len(targets_by_h)}"
            )

        per_task_losses: List[torch.Tensor] = []

        for i in range(self.n_horizons):
            q = quantiles_by_h[i]     # (N, K)
            y = targets_by_h[i]       # (N,)

            # Focal weights: tail samples get (1 + focal_weight) multiplier
            w = tail_focal_weights(
                y,
                sigma=self.y_sigmas[i],
                extra_weight=self.focal_weight,
                threshold_sigma=self.focal_threshold_sigma,
            )

            # Pinball term (base distributional calibration)
            l_pin = self._weighted_pinball(q, y, w)

            # CRPS surrogate term (same math as pinball at K quantiles;
            # kept as a separate named term so gamma_crps can ablate it)
            l_crps = self._weighted_pinball(q, y, w)

            # Utility-rank term: pairwise logistic loss on risk-adj score
            # utility_rank_loss signature: (quantiles, target, *, alpha, ...)
            l_rank = utility_rank_loss(q, y, alpha=1.0)

            l_h = l_pin + self.gamma_crps * l_crps + self.eta_utility * l_rank
            per_task_losses.append(l_h)

        # UNIT: uncertainty-weighted multi-task combination
        total = self.unit(per_task_losses)

        # Embedding decorrelation (optional)
        if embedding is not None and self.alpha_decorr > 0.0:
            total = total + self.alpha_decorr * decorrelation_loss(embedding)

        return total

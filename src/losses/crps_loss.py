"""Mean-pinball-loss surrogate for CRPS, used for distributional calibration."""
from typing import Tuple
import torch

from src.training.losses import quantile_loss


def crps_quantile_loss(
    quantiles: torch.Tensor,
    targets: torch.Tensor,
    taus: Tuple[float, ...] = (0.1, 0.5, 0.9),
) -> torch.Tensor:
    """Mean-pinball-loss surrogate for CRPS, used for distributional calibration.

    This function computes the mean over samples AND quantile levels of the pinball
    (check) loss at each tau in `taus`. It is a *Riemann-sum surrogate* for the
    analytic CRPS integral, not the closed-form CRPS of a piecewise-linear CDF.

    Mathematical identity: CRPS ~= 2 * E_tau[pinball(y, q_tau)] over tau ~ U(0, 1),
    with the approximation error decreasing as len(taus) -> inf. At len(taus) = 3
    the approximation is coarse (~20-30% off the true CRPS) and concentrated on
    the interior of the distribution.

    Scale warning: the returned loss is divided by len(taus); callers composing
    this with other losses (e.g. Task 6 DUL+) must treat len(taus) as frozen when
    tuning composite weights. Changing taus will silently rescale this term by 1/K.

    Delegates to src.training.losses.quantile_loss for the actual math.

    Parameters
    ----------
    quantiles : (N, K) predicted quantiles at levels `taus`.
    targets : (N,) realized values.
    taus : tuple of K quantile levels.

    Returns
    -------
    loss : scalar (mean over batch and quantile levels).
    """
    assert quantiles.dim() == 2, f"quantiles must be 2-D (N, K), got {quantiles.shape}"
    assert quantiles.shape[-1] == len(taus), (
        f"last dim {quantiles.shape[-1]} != len(taus) {len(taus)}"
    )
    return quantile_loss(quantiles, targets, quantiles=list(taus))

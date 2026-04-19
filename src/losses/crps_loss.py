"""Continuous Ranked Probability Score for quantile predictions.

Uses piecewise-linear CDF approximation from (q10, q50, q90) and integrates
|F(x) - 1{x >= y}| dx. For the three-quantile case there is a simple closed-form
in terms of pinball losses at each tau.

Reference: Gneiting & Raftery 2007, "Strictly Proper Scoring Rules".
"""
from typing import Tuple
import torch


def crps_quantile_loss(
    quantiles: torch.Tensor,
    targets: torch.Tensor,
    taus: Tuple[float, ...] = (0.1, 0.5, 0.9),
) -> torch.Tensor:
    """Approximate CRPS via quantile loss decomposition.

    For quantile predictions q_tau, weighted pinball loss with uniform weights
    over tau grid approximates CRPS (up to a constant factor).

    Parameters
    ----------
    quantiles : (N, K) predicted quantiles at levels `taus`.
    targets : (N,) realized values.
    taus : tuple of K quantile levels.

    Returns
    -------
    loss : scalar (mean over batch).
    """
    assert quantiles.dim() == 2
    assert quantiles.shape[-1] == len(taus)
    tau_tensor = torch.tensor(taus, dtype=quantiles.dtype, device=quantiles.device)
    # Pinball at each tau
    diffs = targets.unsqueeze(-1) - quantiles  # (N, K)
    # Element-wise max compatible with PyTorch < 1.9 (torch.maximum added in 1.9)
    a = tau_tensor * diffs
    b = (tau_tensor - 1) * diffs
    loss_k = torch.where(a >= b, a, b)  # (N, K)
    # CRPS approximation: mean across quantile levels
    return loss_k.mean()

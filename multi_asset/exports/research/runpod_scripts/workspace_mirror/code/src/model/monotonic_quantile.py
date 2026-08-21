"""Monotonic quantile head that structurally guarantees q10 < q50 < q90.

The current architecture outputs q10, q50, q90 independently from a single
Linear layer, so nothing prevents quantile crossing (q10 > q50).

This module enforces monotonicity by construction:
  - Predict a base value (median / q50)
  - Predict two POSITIVE deltas via Softplus
  - q10 = base - delta_low   (always < q50)
  - q90 = base + delta_high  (always > q50)

No post-processing, sorting, or penalty terms needed.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class MonotonicQuantileHead(nn.Module):
    """Quantile head that guarantees q10 < q50 < q90 by construction.

    Architecture:
      base_head:  h -> Linear -> GELU -> Linear -> (B,)     [median]
      delta_head: h -> Linear -> GELU -> Linear -> Softplus  [positive deltas]

      q50 = base
      q10 = base - delta_low    (always < q50)
      q90 = base + delta_high   (always > q50)

    Parameters
    ----------
    d_input : int
        Dimensionality of the input hidden representation.
    d_hidden : int
        Hidden dimension inside each sub-head.
    dropout : float
        Dropout probability.
    """

    # Minimum delta floor to guarantee strict ordering even at float32
    # precision. Softplus can output values arbitrarily close to zero for
    # large negative inputs; this floor prevents q10 == q50 or q50 == q90.
    #
    # Calibrated for NORMALIZED targets in [-5, 5] (after MAD sigma).
    # 0.01 = 0.2% of the target range -- enough to be meaningful at the
    # float32 precision scale (~1e-7 rel. error), small enough not to
    # artificially widen the prediction interval.
    # Previously 1e-4 was used; that is too tight on normalized targets
    # (q10 and q50 could differ by only 0.0001 which is visually zero).
    MIN_DELTA: float = 0.01

    def __init__(self, d_input: int, d_hidden: int, dropout: float = 0.1):
        super().__init__()
        self.base_head = nn.Sequential(
            nn.Linear(d_input, d_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_hidden, 1),
        )
        self.delta_head = nn.Sequential(
            nn.Linear(d_input, d_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_hidden, 2),  # [delta_low, delta_high]
            nn.Softplus(),           # ensure positive
        )

    def forward(self, h: torch.Tensor) -> dict[str, torch.Tensor]:
        """Compute monotonic quantile predictions.

        Parameters
        ----------
        h : torch.Tensor
            Shape ``(B, d_input)`` -- hidden representation.

        Returns
        -------
        dict[str, torch.Tensor]
            - ``quantiles``: ``(B, 3)`` with columns [q10, q50, q90],
              guaranteed q10 < q50 < q90.
            - ``point_pred``: ``(B,)`` -- median prediction (q50).
        """
        base = self.base_head(h).squeeze(-1)        # (B,)
        deltas = self.delta_head(h)                  # (B, 2) positive
        # Clamp deltas to a minimum floor for strict ordering guarantee.
        deltas = deltas.clamp(min=self.MIN_DELTA)
        q10 = base - deltas[:, 0]
        q90 = base + deltas[:, 1]
        quantiles = torch.stack([q10, base, q90], dim=-1)  # (B, 3)
        return {"quantiles": quantiles, "point_pred": base}

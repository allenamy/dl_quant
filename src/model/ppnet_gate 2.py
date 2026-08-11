"""PPNet-style regime gate from PEPNet (KDD 2023, arXiv 2302.01115).

Generates per-layer scaling factors [0, 2] from explicit regime prior
features. The same DNN behaves differently under different market regimes
WITHOUT separate towers or regime detection.

Regime prior features (computed externally, NOT from the 5-min window):
  - 1-hour realized volatility
  - OBI trend over past hour (linear regression slope)
  - Hour-of-day embedding (sin, cos)
  - 1-hour average spread
  - 1-hour average depth ratio

These are passed as a separate input, not extracted from x_feat.

Architecture:
  prior_features -> Linear -> GELU -> Linear -> sigmoid * 2 -> scale [0, 2]
  hidden_units * scale -> conditioned hidden_units

The [0, 2] range means:
  0 = completely suppress this dimension (regime says it's noise)
  1 = pass through unchanged
  2 = amplify this dimension (regime says it's signal)
"""

from __future__ import annotations

import torch
import torch.nn as nn


class PPNetGate(nn.Module):
    """Parameter Personalized Gate from PEPNet (KDD 2023).

    Maps explicit regime prior features to per-dimension scaling factors
    in [0, 2], which element-wise multiply the hidden representation.

    Parameters
    ----------
    d_prior : int
        Dimensionality of the regime prior feature vector.
    d_hidden : int
        Dimensionality of the hidden representation to be gated.
    dropout : float
        Dropout probability inside the gate network.
    """

    def __init__(self, d_prior: int, d_hidden: int, dropout: float = 0.1):
        super().__init__()
        self.gate = nn.Sequential(
            nn.Linear(d_prior, d_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_hidden, d_hidden),
            nn.Sigmoid(),  # [0, 1]
        )
        self.scale = 2.0  # sigmoid * 2 -> [0, 2]

    def forward(self, h: torch.Tensor, prior: torch.Tensor) -> torch.Tensor:
        """Apply regime-conditioned gating to hidden representation.

        Parameters
        ----------
        h : torch.Tensor
            Shape ``(B, d_hidden)`` -- hidden units to be gated.
        prior : torch.Tensor
            Shape ``(B, d_prior)`` -- regime prior features.

        Returns
        -------
        torch.Tensor
            Shape ``(B, d_hidden)`` -- gated hidden units.
        """
        gate = self.gate(prior) * self.scale  # (B, d_hidden) in [0, 2]
        return h * gate

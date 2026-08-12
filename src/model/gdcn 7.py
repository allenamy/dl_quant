"""GDCN: Gated Deep Cross Network for noise-filtered feature interactions.

Reference: Chen et al., "GDCN: Gated Deep Cross Network for
Explicit Feature Interaction", CIKM 2023 (Criteo #1).
arXiv: 2311.04635

Standard cross network computes:
    x_{l+1} = x_0 * (W_l * x_l + b_l) + x_l

GDCN adds a per-dimension gate:
    x_{l+1} = x_0 * (W_l * x_l + b_l) * gate_l + x_l
    gate_l = sigmoid(W_g * x_l + b_g)

The gate learns to suppress noisy feature crosses (gate -> 0) and
amplify informative ones (gate -> 1).  This is the key innovation
for low-SNR settings: not all feature interactions are useful, and
the gate adaptively filters them per sample.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class GatedCrossLayer(nn.Module):
    """Single gated cross layer from GDCN.

    Computes::

        cross = x0 * W(x_l)
        gate  = sigmoid(W_g(x_l))
        output = cross * gate + x_l    (gated cross + residual)

    Parameters
    ----------
    d_input : int
        Input dimension (same for x0 and xl).
    """

    def __init__(self, d_input: int):
        super().__init__()
        self.weight = nn.Linear(d_input, d_input, bias=True)
        self.gate = nn.Linear(d_input, d_input, bias=True)

    def forward(self, x0: torch.Tensor, xl: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x0 : torch.Tensor
            Original input, shape ``(B, ..., d_input)``.
            Always the same across layers (preserves original features).
        xl : torch.Tensor
            Current layer output, shape ``(B, ..., d_input)``.
            Evolves layer by layer.

        Returns
        -------
        torch.Tensor
            Same shape as input.
        """
        cross = x0 * self.weight(xl)             # element-wise cross
        gate = torch.sigmoid(self.gate(xl))       # bit-wise gate in [0, 1]
        return cross * gate + xl                  # gated cross + residual


class GDCN(nn.Module):
    """Stack of GatedCrossLayers.

    Input x -> GatedCross(x, x) -> GatedCross(x, h1) -> ... -> output

    The first argument is always the original input x0, preserving
    access to original features at every layer depth.

    Parameters
    ----------
    d_input : int
        Input dimension.
    n_layers : int
        Number of gated cross layers.
    dropout : float
        Dropout probability applied after the cross stack.
    """

    def __init__(self, d_input: int, n_layers: int = 3, dropout: float = 0.1):
        super().__init__()
        self.layers = nn.ModuleList([
            GatedCrossLayer(d_input) for _ in range(n_layers)
        ])
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through stacked gated cross layers.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, d_input)`` or ``(B, L, d_input)``.

        Returns
        -------
        torch.Tensor
            Same shape as input.
        """
        x0 = x       # always keep the original input
        xl = x
        for layer in self.layers:
            xl = layer(x0, xl)
        return self.dropout(xl)

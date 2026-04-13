"""Convolutional encoder for raw LOB tensor (Path B).

Learns spatial patterns from the depth profile using Conv1d across levels.
Each timestep is processed independently (no temporal mixing here).

Architecture::

    (B*L, 4, n_levels) -> Conv1d stack -> AdaptiveAvgPool1d -> (B*L, 32)
    -> Linear proj -> (B*L, d_raw)
    reshape -> (B, L, d_raw)

The Conv1d kernels slide across LEVELS (spatial dimension), learning:
- Depth profile shape (convexity, gaps)
- Bid-ask asymmetry
- Liquidity concentration patterns

Reference: DeepLOB (Zhang 2019), TLOB (Berti 2025).
"""

from __future__ import annotations

import torch
import torch.nn as nn


class RawLOBEncoder(nn.Module):
    """Convolutional encoder for raw LOB tensor.

    Parameters
    ----------
    n_levels : int
        Number of orderbook levels (spatial dimension). Default 20.
    d_raw : int
        Output embedding dimension per timestep. Default 32.
    dropout : float
        Dropout probability in the projection layer. Default 0.1.
    """

    def __init__(self, n_levels: int = 20, d_raw: int = 32, dropout: float = 0.1):
        super().__init__()
        self.n_levels = n_levels
        self.d_raw = d_raw

        # Input: (B*L, 4, n_levels) -- 4 channels, n_levels spatial positions
        # Conv1d across levels:
        self.conv_stack = nn.Sequential(
            nn.Conv1d(4, 16, kernel_size=3, padding=1),   # mix channels within local levels
            nn.GELU(),
            nn.Conv1d(16, 32, kernel_size=3, padding=1),  # deeper spatial features
            nn.GELU(),
            nn.AdaptiveAvgPool1d(1),                       # pool across levels -> (B*L, 32, 1)
        )
        self.proj = nn.Sequential(
            nn.Linear(32, d_raw),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x_raw: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x_raw : torch.Tensor
            Shape ``(B, L, n_levels, 4)`` -- raw LOB tensor.

        Returns
        -------
        torch.Tensor
            Shape ``(B, L, d_raw)`` -- spatial embeddings per timestep.
        """
        B, L, N, C = x_raw.shape
        # Reshape to (B*L, C, N) for Conv1d -- channels=4, spatial=n_levels
        h = x_raw.reshape(B * L, N, C).permute(0, 2, 1)  # (B*L, 4, n_levels)
        h = self.conv_stack(h)      # (B*L, 32, 1)
        h = h.squeeze(-1)           # (B*L, 32)
        h = self.proj(h)            # (B*L, d_raw)
        return h.reshape(B, L, -1)  # (B, L, d_raw)

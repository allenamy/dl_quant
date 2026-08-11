"""Cross-asset attention for multi-symbol modeling.

Given n_symbols asset tokens of shape (B, n_symbols, d_model),
each asset attends to all others to incorporate cross-asset signals.

For BTCUSDT: including ETHUSDT (high correlation) adds information
about market-wide crypto sentiment vs BTC-specific moves.

Reference: PMformer (2024) validated cross-asset attention on BTC+ETH.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class CrossAssetAttention(nn.Module):
    """Cross-attention between asset representations.

    Uses a single self-attention layer over the asset dimension.
    No causal mask needed here -- all assets observe each other simultaneously.

    Parameters
    ----------
    d_model : int
        Hidden dimension of each asset token. Default 32.
    nhead : int
        Number of attention heads. Default 2.
    dropout : float
        Dropout probability. Default 0.1.
    """

    def __init__(self, d_model: int = 32, nhead: int = 2, dropout: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(
            embed_dim=d_model,
            num_heads=nhead,
            dropout=dropout,
            batch_first=True,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply cross-asset attention.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, n_symbols, d_model)`` -- per-symbol embeddings.

        Returns
        -------
        torch.Tensor
            Shape ``(B, n_symbols, d_model)`` -- cross-asset enriched embeddings.
        """
        residual = x
        h = self.norm(x)
        h, _ = self.attn(h, h, h)
        return residual + h

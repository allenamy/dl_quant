"""Patching + Causal Self-Attention for temporal modeling.

Converts sequential hidden states into patch tokens, then applies
causal self-attention to capture long-range temporal dependencies.

References:
  - PatchTST (ICLR 2023): Patching reduces attention cost dramatically.
  - TLOB (Feb 2025): Single attention head suffices for LOB data.
  - Conformer (2020): Conv BEFORE attention is the optimal ordering.

Design choices:
  - Patch from the RIGHT so that the last patch always covers the most
    recent data. If L is not divisible by patch_size, truncate from the LEFT.
  - Learned positional embeddings (not sinusoidal) -- the number of patches
    is bounded and small, so learned is simpler and equally effective.
  - Pre-norm Transformer block (LN before attention/FFN, not after).
  - Causal mask: patch i can only attend to patches j <= i.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class PatchEmbedding(nn.Module):
    """Convert sequential features into patch tokens.

    (B, L, d_model) -> reshape -> (B, L//P, P*d_model) -> Linear -> (B, n_patches, d_model)

    If L is not divisible by patch_size, truncate from the LEFT (keep recent data).
    Add learned positional embeddings to patch tokens.

    Parameters
    ----------
    d_model : int
        Hidden dimension of both input and output.
    patch_size : int
        Number of timesteps per patch. Default 8.
    max_patches : int
        Maximum number of patches (for positional embedding table). Default 128.
    """

    def __init__(self, d_model: int, patch_size: int = 8, max_patches: int = 128):
        super().__init__()
        self.d_model = d_model
        self.patch_size = patch_size
        self.max_patches = max_patches
        # Project flattened patch to d_model
        self.proj = nn.Linear(patch_size * d_model, d_model)
        # Learned positional embeddings (parameter, not Embedding, for smaller footprint)
        self.pos_embed = nn.Parameter(torch.zeros(1, max_patches, d_model))
        nn.init.trunc_normal_(self.pos_embed, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, L, d_model)``.

        Returns
        -------
        torch.Tensor
            Shape ``(B, n_patches, d_model)`` where n_patches = L // patch_size.
        """
        B, L, D = x.shape
        P = self.patch_size

        # Truncate from the LEFT to make L divisible by P
        remainder = L % P
        if remainder != 0:
            x = x[:, remainder:, :]  # drop oldest timesteps
            L = x.size(1)

        n_patches = L // P

        # Reshape: (B, n_patches, P * D)
        x = x.reshape(B, n_patches, P * D)

        # Project to d_model
        x = self.proj(x)  # (B, n_patches, d_model)

        # Add positional embeddings (slice from learned table)
        x = x + self.pos_embed[:, :n_patches, :]

        return x


class CausalPatchAttention(nn.Module):
    """Single causal self-attention layer over patch tokens.

    Pre-norm Transformer block:
      LayerNorm -> MultiHeadAttention (causal) -> residual
      LayerNorm -> FFN -> residual

    Uses standard softmax attention (O(n_patches^2) is cheap since n_patches << L).
    Causal mask: each patch can only attend to itself and earlier patches.

    Parameters
    ----------
    d_model : int
        Hidden dimension. Default 32.
    nhead : int
        Number of attention heads. Default 4.
    d_ff : int
        Feed-forward hidden dimension. Default 64.
    dropout : float
        Dropout probability. Default 0.1.
    """

    def __init__(
        self,
        d_model: int = 32,
        nhead: int = 4,
        d_ff: int = 64,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.d_model = d_model

        # Pre-norm attention
        self.norm1 = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(
            embed_dim=d_model,
            num_heads=nhead,
            dropout=dropout,
            batch_first=True,
        )

        # Pre-norm FFN
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )

    def _make_causal_mask(self, n: int, device: torch.device) -> torch.Tensor:
        """Create causal attention mask.

        Returns
        -------
        torch.Tensor
            Shape ``(n, n)`` boolean mask where True means "block attention".
            Position i can attend to positions j <= i.
        """
        # nn.MultiheadAttention expects: True = block, False = allow
        mask = torch.triu(torch.ones(n, n, device=device, dtype=torch.bool), diagonal=1)
        return mask

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, n_patches, d_model)``.

        Returns
        -------
        torch.Tensor
            Shape ``(B, n_patches, d_model)``.
        """
        n = x.size(1)

        # Causal self-attention with pre-norm
        residual = x
        h = self.norm1(x)
        causal_mask = self._make_causal_mask(n, device=x.device)
        h, _ = self.attn(h, h, h, attn_mask=causal_mask)
        x = residual + h

        # FFN with pre-norm
        residual = x
        h = self.norm2(x)
        h = self.ffn(h)
        x = residual + h

        return x

"""Causal Temporal Encoder with Rotary Position Embeddings and Conv frontend.

Implements a causal Transformer encoder suitable for sequential LOB data,
combining depthwise-separable causal convolutions with RoPE-augmented
multi-head self-attention.
"""

from __future__ import annotations

import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Rotary Position Embeddings (RoPE)
# ---------------------------------------------------------------------------

def rotary_embedding(seq_len: int, dim: int, device: torch.device) -> torch.Tensor:
    """Build a (seq_len, dim) sin/cos RoPE table.

    For each position *pos* and dimension index *i* (0-based, i < dim//2):
        freq_i = 1 / (10000 ** (2*i / dim))
        angle  = pos * freq_i
    The table concatenates [sin(angles), cos(angles)] along the last axis.

    Returns
    -------
    torch.Tensor
        Shape ``(seq_len, dim)`` with ``[:, :dim//2]`` = sin, ``[:, dim//2:]`` = cos.
    """
    half = dim // 2
    # freq: (half,)
    freq = 1.0 / (10000.0 ** (torch.arange(0, half, dtype=torch.float32, device=device) * 2.0 / dim))
    # pos: (seq_len,)
    pos = torch.arange(seq_len, dtype=torch.float32, device=device)
    # angles: (seq_len, half)
    angles = pos.unsqueeze(1) * freq.unsqueeze(0)
    # (seq_len, dim)
    return torch.cat([angles.sin(), angles.cos()], dim=-1)


def apply_rope(x: torch.Tensor, rope: torch.Tensor) -> torch.Tensor:
    """Apply rotary position embeddings to *x*.

    Parameters
    ----------
    x : torch.Tensor
        Shape ``(B, nhead, L, head_dim)``.
    rope : torch.Tensor
        Shape ``(L, head_dim)`` — output of :func:`rotary_embedding`.

    Returns
    -------
    torch.Tensor
        Same shape as *x*, with rotary embedding applied.
    """
    half = x.shape[-1] // 2
    x1 = x[..., :half]
    x2 = x[..., half:]

    # rope components — broadcast over B and nhead
    sin_part = rope[:, :half].unsqueeze(0).unsqueeze(0)  # (1, 1, L, half)
    cos_part = rope[:, half:].unsqueeze(0).unsqueeze(0)  # (1, 1, L, half)

    out1 = x1 * cos_part - x2 * sin_part
    out2 = x2 * cos_part + x1 * sin_part
    return torch.cat([out1, out2], dim=-1)


# ---------------------------------------------------------------------------
# Causal Convolution Block
# ---------------------------------------------------------------------------

class CausalConvBlock(nn.Module):
    """Depthwise-separable causal convolution with residual connection.

    Sequence:  LayerNorm -> depthwise Conv1d -> pointwise Conv1d -> GELU -> Dropout + residual.
    Causality is achieved by explicit left-padding of ``(kernel_size - 1) * dilation``.
    """

    def __init__(
        self,
        d_model: int,
        kernel_size: int = 3,
        dilation: int = 1,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.pad = (kernel_size - 1) * dilation
        self.norm = nn.LayerNorm(d_model)
        self.depthwise = nn.Conv1d(
            d_model, d_model, kernel_size, dilation=dilation, groups=d_model, bias=True,
        )
        self.pointwise = nn.Conv1d(d_model, d_model, 1, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, L, d_model)``.
        """
        residual = x
        out = self.norm(x)
        # Conv1d expects (B, C, L)
        out = out.transpose(1, 2)
        # Causal left-padding
        out = F.pad(out, (self.pad, 0))
        out = self.depthwise(out)
        # Crop to original length (padding may produce extra samples)
        out = out[..., :x.size(1)]
        out = self.pointwise(out)
        out = self.act(out)
        out = self.drop(out)
        # Back to (B, L, C)
        out = out.transpose(1, 2)
        return out + residual


# ---------------------------------------------------------------------------
# Causal Self-Attention with RoPE
# ---------------------------------------------------------------------------

class CausalSelfAttention(nn.Module):
    """Multi-head self-attention with Rotary Position Embeddings and causal masking.

    Uses ``F.scaled_dot_product_attention`` with ``is_causal=True`` for
    efficient fused causal attention (PyTorch >= 2.0).
    """

    def __init__(
        self,
        d_model: int,
        nhead: int,
        dropout: float = 0.1,
        max_len: int = 2048,
    ) -> None:
        super().__init__()
        assert d_model % nhead == 0, "d_model must be divisible by nhead"
        self.d_model = d_model
        self.nhead = nhead
        self.head_dim = d_model // nhead
        self.max_len = max_len
        self.dropout = dropout

        self.qkv = nn.Linear(d_model, 3 * d_model, bias=True)
        self.out_proj = nn.Linear(d_model, d_model, bias=True)

        # Pre-compute RoPE table (registered as buffer so it moves with the model).
        rope = rotary_embedding(max_len, self.head_dim, device=torch.device("cpu"))
        self.register_buffer("rope", rope, persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, L, d_model)``.
        """
        B, L, _ = x.shape
        qkv = self.qkv(x)  # (B, L, 3*d_model)
        qkv = qkv.reshape(B, L, 3, self.nhead, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)  # (3, B, nhead, L, head_dim)
        q, k, v = qkv.unbind(0)  # each (B, nhead, L, head_dim)

        # Apply RoPE to queries and keys
        rope = self.rope[:L]  # (L, head_dim)
        q = apply_rope(q, rope)
        k = apply_rope(k, rope)

        # Efficient causal attention
        drop_p = self.dropout if self.training else 0.0
        attn_out = F.scaled_dot_product_attention(
            q, k, v, attn_mask=None, dropout_p=drop_p, is_causal=True,
        )  # (B, nhead, L, head_dim)

        attn_out = attn_out.transpose(1, 2).reshape(B, L, self.d_model)
        return self.out_proj(attn_out)


# ---------------------------------------------------------------------------
# Transformer Block (pre-norm)
# ---------------------------------------------------------------------------

class TransformerBlock(nn.Module):
    """Pre-norm Transformer block: LN -> Attn + residual, LN -> FFN + residual."""

    def __init__(
        self,
        d_model: int,
        nhead: int,
        d_ff: int,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attn = CausalSelfAttention(d_model, nhead, dropout)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, L, d_model)``.
        """
        x = x + self.attn(self.norm1(x))
        x = x + self.ffn(self.norm2(x))
        return x


# ---------------------------------------------------------------------------
# Full Causal Temporal Encoder
# ---------------------------------------------------------------------------

class CausalTemporalEncoder(nn.Module):
    """Causal temporal encoder with conv frontend, RoPE, and Transformer blocks.

    Architecture
    ------------
    1. ``conv_layers`` :class:`CausalConvBlock` layers (dilation doubles each
       layer: 1, 2, 4, ...).
    2. ``depth`` :class:`TransformerBlock` layers.
    3. Final :class:`~torch.nn.LayerNorm`.
    """

    def __init__(
        self,
        d_model: int = 128,
        nhead: int = 4,
        depth: int = 4,
        d_ff: int = 256,
        dropout: float = 0.1,
        conv_layers: int = 2,
        conv_kernel: int = 3,
        conv_dilation_base: int = 2,
    ) -> None:
        super().__init__()

        # Conv frontend — dilation doubles each layer
        self.conv_blocks = nn.ModuleList([
            CausalConvBlock(
                d_model,
                kernel_size=conv_kernel,
                dilation=conv_dilation_base ** i,
                dropout=dropout,
            )
            for i in range(conv_layers)
        ])

        # Transformer blocks
        self.transformer_blocks = nn.ModuleList([
            TransformerBlock(d_model, nhead, d_ff, dropout)
            for _ in range(depth)
        ])

        # Final layer norm
        self.final_norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, L, d_model)``.

        Returns
        -------
        torch.Tensor
            Shape ``(B, L, d_model)``.
        """
        for conv in self.conv_blocks:
            x = conv(x)
        for block in self.transformer_blocks:
            x = block(x)
        return self.final_norm(x)

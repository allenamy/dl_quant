"""iTransformer (inverted Transformer) backbone for mid-horizon prediction.

Reference: Liu et al., "iTransformer: Inverted Transformers Are Effective for
Time Series Forecasting", ICLR 2024 (https://arxiv.org/abs/2310.06625).

Key idea — INVERSION
--------------------
Standard Transformers tokenize ALONG TIME (each timestep = one token), and
self-attention learns time-time dependencies inside a fixed feature space.

iTransformer flips it: each FEATURE CHANNEL becomes a token, and self-attention
operates ACROSS CHANNELS. The temporal dimension becomes the embedding dimension.

Why this matters for y_1800
---------------------------
1. Phase A1 Transformer (time-axis attention) was rejected at fold-0 screen.
   That tested attention over time — it didn't help. iTransformer is a
   structurally different lever: it tests whether attention over *features* helps.

2. Mid-horizon (30 min) signal is dominated by cross-feature relationships
   (price · vol · OBI · trade-flow) more than fine-grained temporal patterns.
   Channel-attention is the right inductive bias for that.

3. The d_model=32 → 32 channels is a small token set; attention is cheap and
   not prone to overfitting on this scale. Time-axis attention with L=1200
   tokens has the opposite cost profile.

Architecture
------------
Input  h: (B, L, D)
   ↓ permute → (B, D, L)        # treat each channel as a token of length L
   ↓ Linear(L → d_emb)           # embed each channel (variate)
   ↓ Norm + MultiheadAttn        # attention across D channels
   ↓ FFN + residual
   ↓ Final pooling: take token mean across D → (B, d_emb)
   ↓ Linear(d_emb → D)           # back to expected output dim

Forward signature matches other backbones:
    forward(h: Tensor[B, L, D]) -> Tensor[B, D]

Param budget vs other backbones at d_model=32, L=1200:
- conv_lasts:  ~3 conv blocks    → ~10K params
- ema_pool:    ~3 conv blocks    → ~10K params
- gru:         32→32 GRU         → ~6K params
- mamba:       d_state=16        → ~5K params
- iTransformer (ours, d_emb=64): ~80K params (Linear(1200→64) dominates)

The Linear(L→d_emb) is the cost. Set d_emb=64 default; can drop to 32 for tighter
param budget at the price of expressiveness.
"""
from __future__ import annotations

import torch
import torch.nn as nn


class ITransformerBackbone(nn.Module):
    """Channel-token attention encoder.

    Parameters
    ----------
    d_model : int
        Number of channels in the input (and required output dim).
    L : int
        Sequence length (must match the input window). Used to size the
        per-channel embedding Linear.
    d_emb : int, default 64
        Hidden dim for the channel embedding (also Q/K/V dim for attention).
    n_heads : int, default 4
    n_layers : int, default 1
        Number of transformer blocks.
    d_ff : int, default 128
        Feed-forward inner dim.
    dropout : float, default 0.15
    """

    def __init__(
        self,
        d_model: int,
        L: int = 1200,
        d_emb: int = 64,
        n_heads: int = 4,
        n_layers: int = 1,
        d_ff: int = 128,
        dropout: float = 0.15,
    ):
        super().__init__()
        if d_emb % n_heads != 0:
            raise ValueError(f"d_emb={d_emb} must be divisible by n_heads={n_heads}")
        self.d_model = int(d_model)
        self.L = int(L)
        self.d_emb = int(d_emb)

        # Per-variate (channel) embedding: project the entire L-step history
        # of each channel into a d_emb vector. This is iTransformer's signature
        # operation — the channel becomes a "variate token".
        self.variate_embed = nn.Linear(L, d_emb)

        # Build encoder in a torch-version-agnostic way.
        # Old torch (1.4) doesn't support batch_first/norm_first/gelu kwargs;
        # newer torch does. Try the modern signature, fall back to the old.
        try:
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_emb,
                nhead=n_heads,
                dim_feedforward=d_ff,
                dropout=dropout,
                batch_first=True,
                norm_first=True,
                activation="gelu",
            )
            self._needs_transpose = False
        except TypeError:
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_emb,
                nhead=n_heads,
                dim_feedforward=d_ff,
                dropout=dropout,
            )
            # old API uses (S, B, E) i.e. seq-first
            self._needs_transpose = True
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        # Pool channel tokens → single vector → back to d_model
        # We use mean over the d_model channel-tokens (each is a d_emb vector),
        # then project d_emb → d_model so downstream code (head, etc.) sees
        # the expected d_model dim.
        self.out_proj = nn.Linear(d_emb, d_model)
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

        # Init: small variate_embed weights (avoid blowing up channel tokens
        # before attention has a chance to balance them)
        with torch.no_grad():
            nn.init.kaiming_normal_(self.variate_embed.weight, nonlinearity="relu")
            nn.init.zeros_(self.variate_embed.bias)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        h : (B, L, D) input.

        Returns
        -------
        (B, D) pooled output.
        """
        B, L, D = h.shape
        if L != self.L:
            raise ValueError(
                f"iTransformerBackbone constructed with L={self.L} "
                f"but received input with L={L}. Channel embedding shape mismatch."
            )
        if D != self.d_model:
            raise ValueError(
                f"iTransformerBackbone constructed with d_model={self.d_model} "
                f"but received input with D={D}."
            )

        # (B, L, D) -> (B, D, L)  -- each channel is now a token of length L
        x = h.transpose(1, 2)
        # -> (B, D, d_emb)        -- embed each channel-token
        x = self.variate_embed(x)
        # Attention over D tokens (channels)
        if self._needs_transpose:
            # old torch wants (S, B, E) where S=D
            x = x.transpose(0, 1)         # (D, B, d_emb)
            x = self.encoder(x)
            x = x.transpose(0, 1)         # (B, D, d_emb)
        else:
            x = self.encoder(x)           # (B, D, d_emb)
        # Pool: mean across channel-tokens
        x = x.mean(dim=1)         # (B, d_emb)
        x = self.out_proj(self.dropout(x))  # (B, d_model)
        return x

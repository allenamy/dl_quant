"""Convolutional encoder for raw LOB tensor (Path B) — V4.

V4 additions (all behind flags, default True):
- use_channel_mix_conv: prepend a 1x1 Conv to explicitly mix the 4
  raw channels (bid_delta, bid_logamt, ask_delta, ask_logamt) before
  spatial convolution. When False, raw 4-channel input goes directly
  into the spatial conv.
- use_level_attention_pool: replace AdaptiveAvgPool1d(1) with a
  learned attention pool over levels (position-aware). When False,
  falls back to average pooling.

Architecture (V4, both flags on)::

    (B*L, 4, n_levels)
      -> Conv1d(4, 16, 1)   [channel mix]
      -> Conv1d(16, 16, 3)  [spatial]
      -> Conv1d(16, 32, 3)  [spatial]
      -> AttentionPool1D    [level pool]
      -> (B*L, 32)
      -> Linear proj -> (B*L, d_raw)
      reshape -> (B, L, d_raw)

When use_channel_mix_conv=False and use_level_attention_pool=False,
the topology is identical to V3 (4-channel direct spatial conv + AvgPool).

Reference: DeepLOB (Zhang 2019), TLOB (Berti 2025).
"""
from __future__ import annotations

import torch
import torch.nn as nn

from src.model.attention_pool import AttentionPool1D


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
    use_channel_mix_conv : bool
        If True, prepend a Conv1d(4, 16, kernel_size=1) to explicitly mix
        the 4 raw channels before spatial convolution. Default True.
    use_level_attention_pool : bool
        If True, replace AdaptiveAvgPool1d(1) with AttentionPool1D for
        learned, position-aware pooling across levels. Default True.
    """

    def __init__(
        self,
        n_levels: int = 20,
        d_raw: int = 32,
        dropout: float = 0.1,
        *,
        use_channel_mix_conv: bool = True,
        use_level_attention_pool: bool = True,
    ) -> None:
        super().__init__()
        self.n_levels = n_levels
        self.d_raw = d_raw
        self.use_channel_mix_conv = use_channel_mix_conv
        self.use_level_attention_pool = use_level_attention_pool

        # Optional 1x1 channel-mixing conv
        if use_channel_mix_conv:
            self.channel_mix = nn.Conv1d(4, 16, kernel_size=1, bias=True)
            conv_in = 16
        else:
            self.channel_mix = None
            conv_in = 4

        # Spatial conv stack — topology unchanged from V3, but input channels
        # depend on whether channel_mix is active.
        self.spatial_stack = nn.Sequential(
            nn.Conv1d(conv_in, 16, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Conv1d(16, 32, kernel_size=3, padding=1),
            nn.GELU(),
        )

        # Level-wise pool: attention pool (V4) or avg pool (V3 fallback)
        if use_level_attention_pool:
            self.level_pool = AttentionPool1D(d_model=32, input_is_last_dim=False)
            self._pool_is_attention = True
        else:
            self.level_pool = nn.AdaptiveAvgPool1d(1)
            self._pool_is_attention = False

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
            Shape ``(B, L, n_levels, 4)`` — raw LOB tensor.

        Returns
        -------
        torch.Tensor
            Shape ``(B, L, d_raw)`` — spatial embeddings per timestep.
        """
        B, L, N, C = x_raw.shape
        h = x_raw.reshape(B * L, N, C).permute(0, 2, 1)  # (B*L, 4, n_levels)

        if self.channel_mix is not None:
            h = self.channel_mix(h)  # (B*L, 16, n_levels)

        h = self.spatial_stack(h)  # (B*L, 32, n_levels)

        if self._pool_is_attention:
            h = self.level_pool(h)          # (B*L, 32) — AttentionPool1D returns pooled
        else:
            h = self.level_pool(h).squeeze(-1)  # (B*L, 32) — AdaptiveAvgPool

        h = self.proj(h)            # (B*L, d_raw)
        return h.reshape(B, L, -1)  # (B, L, d_raw)

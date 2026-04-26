"""EMA pool backbone: dilated conv + exponentially-weighted average over time.

Replaces the V4 last-timestep slice with a recency-weighted sum over the
full input window. With decay=0.95, ~half the weight comes from the last
~14 steps; with decay=0.99, ~half from the last ~69 steps. Most weight
on recent timesteps (consistent with conv RF), but a tail of long-context
information bleeds in — closes some of the gap to RNN/SSM without adding
learnable params.

Input  : (B, L, d_model)
Output : (B, d_model)
"""
from __future__ import annotations

import torch
import torch.nn as nn

from src.model.dual_path_model import CausalConv1dBlock


class EMAPoolBackbone(nn.Module):
    def __init__(self, d_model: int = 32, dropout: float = 0.15, decay: float = 0.95) -> None:
        super().__init__()
        if not (0.0 < decay < 1.0):
            raise ValueError(f"decay must be in (0,1), got {decay}")
        self.decay = float(decay)
        self.temporal_conv = nn.Sequential(
            CausalConv1dBlock(d_model, kernel_size=3, dilation=1, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=2, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=4, dropout=dropout),
        )

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        # h: (B, L, d_model)
        h_conv = self.temporal_conv(h)
        L = h_conv.size(1)
        device = h_conv.device
        # Weights: most-recent timestep gets the largest weight.
        # ema_t = (1-decay) · h_t + decay · ema_{t-1}, equivalently
        # weight(t) = (1-decay) · decay^(L-1-t).
        idx = torch.arange(L - 1, -1, -1, device=device, dtype=h_conv.dtype)
        weights = (1.0 - self.decay) * (self.decay ** idx)
        # Normalise so weights sum to 1 (avoids early-step underweighting bias).
        weights = weights / weights.sum()
        return (h_conv * weights.view(1, L, 1)).sum(dim=1)

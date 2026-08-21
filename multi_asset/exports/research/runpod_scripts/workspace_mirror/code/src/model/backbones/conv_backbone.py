"""Default V4 backbone: dilated causal conv stack + last-timestep slice.

Extracted from `dual_path_model_v3.py` so the temporal pooling step can be
swapped (EMA / GRU / Mamba) without touching the rest of V4. The
ConvLastTSBackbone preserves the exact V4 numerical behaviour when used
with default kwargs.
"""
from __future__ import annotations

import torch
import torch.nn as nn

from src.model.dual_path_model import CausalConv1dBlock


class ConvLastTSBackbone(nn.Module):
    """3 dilated causal conv layers (RF=15s) + last-timestep slice.

    Input  : (B, L, d_model)
    Output : (B, d_model)
    """

    def __init__(self, d_model: int = 32, dropout: float = 0.15) -> None:
        super().__init__()
        self.temporal_conv = nn.Sequential(
            CausalConv1dBlock(d_model, kernel_size=3, dilation=1, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=2, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=4, dropout=dropout),
        )

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        h_conv = self.temporal_conv(h)
        return h_conv[:, -1, :]

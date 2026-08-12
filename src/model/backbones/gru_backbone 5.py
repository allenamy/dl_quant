"""GRU backbone: dilated conv + 1-layer GRU + last hidden state.

Stateless per sample. ~6K extra params at d_model=32. Well-understood
recurrent architecture; prior to declaring Mamba/Transformer necessary,
GRU is a more conservative test of "does long-context recurrence help on
y_1800?" — V5-LH already proved that loading complexity blindly fails.

Input  : (B, L, d_model)
Output : (B, d_model)
"""
from __future__ import annotations

import torch
import torch.nn as nn

from src.model.dual_path_model import CausalConv1dBlock


class GRUBackbone(nn.Module):
    def __init__(
        self,
        d_model: int = 32,
        hidden: int = 32,
        n_layers: int = 1,
        dropout: float = 0.15,
    ) -> None:
        super().__init__()
        self.temporal_conv = nn.Sequential(
            CausalConv1dBlock(d_model, kernel_size=3, dilation=1, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=2, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=4, dropout=dropout),
        )
        self.gru = nn.GRU(
            input_size=d_model,
            hidden_size=hidden,
            num_layers=n_layers,
            batch_first=True,
            dropout=0.0 if n_layers == 1 else dropout,
        )
        self.proj = nn.Identity() if hidden == d_model else nn.Linear(hidden, d_model)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        # h: (B, L, d_model)
        h_conv = self.temporal_conv(h)
        # NOTE: GRU is non-deterministic across CUDA versions when training
        # but deterministic in eval. Tests pin eval() before equality checks.
        out, hN = self.gru(h_conv)
        last = hN[-1]                # (B, hidden)
        return self.proj(last)        # (B, d_model)

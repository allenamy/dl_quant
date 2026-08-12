"""Deeper TCN backbone: configurable n_layers + dilations.

Default: 5 layers with dilations [1, 2, 4, 8, 16], kernel=3 → RF = 1 + 2*(1+2+4+8+16) = 63 timesteps.
Returns last-timestep h_pred to match V4 behaviour, but with deeper local context.
"""
from __future__ import annotations
import torch
import torch.nn as nn
from src.model.dual_path_model import CausalConv1dBlock


class ConvDeepBackbone(nn.Module):
    def __init__(self, d_model: int = 32, dropout: float = 0.15,
                 dilations=(1, 2, 4, 8, 16), kernel_size: int = 3,
                 pool: str = 'last') -> None:
        super().__init__()
        layers = [CausalConv1dBlock(d_model, kernel_size=kernel_size,
                                     dilation=d, dropout=dropout)
                  for d in dilations]
        self.temporal_conv = nn.Sequential(*layers)
        self.pool = pool

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        h_conv = self.temporal_conv(h)
        if self.pool == 'last':
            return h_conv[:, -1, :]
        elif self.pool == 'mean':
            return h_conv.mean(dim=1)
        elif self.pool == 'max':
            return h_conv.max(dim=1).values
        else:
            return h_conv[:, -1, :]

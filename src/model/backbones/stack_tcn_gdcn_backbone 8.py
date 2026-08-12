"""Sequential block: GDCN cross → TCN temporal → Conv1x1 mix, stacked.

Per-path block stack alternating channel-cross (GDCN-V2 style), temporal
(causal dilated conv), and point-wise channel mix (Conv1x1). Each component
applies a residual transformation. After 2 stacked blocks, take last timestep
and late-concat the two paths.

Idea: V4 already does GDCN+ChannelMix as channel-only ops at one stage. This
backbone interleaves channel-cross with TEMPORAL convolutions inside the
backbone, testing whether mixing time × channel orderings beats pure parallel
(late_fusion_mamba) or pure feature-cross (DCN-V2).
"""
from __future__ import annotations
import torch
import torch.nn as nn


class _GDCNCross(nn.Module):
    """DCN-V2 style cross block applied broadcast over (B, ..., D)."""
    def __init__(self, d: int, n_layers: int = 2):
        super().__init__()
        self.layers = nn.ModuleList([nn.Linear(d, d, bias=True) for _ in range(n_layers)])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x0 = x
        xl = x
        for layer in self.layers:
            xl = x0 * layer(xl) + xl
        return xl


class _StackBlock(nn.Module):
    def __init__(self, d: int, kernel_size: int = 3, dilations=(1, 4, 16), dropout: float = 0.15):
        super().__init__()
        # GDCN cross
        self.norm_gdcn = nn.LayerNorm(d)
        self.gdcn = _GDCNCross(d, n_layers=2)
        # TCN
        self.norm_tcn = nn.LayerNorm(d)
        self.convs = nn.ModuleList()
        for dil in dilations:
            pad = (kernel_size - 1) * dil
            self.convs.append(nn.Conv1d(d, d, kernel_size, padding=pad, dilation=dil))
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
        # Conv1x1 point-wise mix
        self.norm_mix = nn.LayerNorm(d)
        self.conv1x1 = nn.Conv1d(d, d, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # (B, L, D)
        # 1. Channel cross (GDCN), residual
        x = x + self.drop(self.gdcn(self.norm_gdcn(x)))
        # 2. Temporal TCN, residual
        h = self.norm_tcn(x).transpose(1, 2)  # (B, D, L)
        L = h.size(2)
        for conv in self.convs:
            y = conv(h)[:, :, :L]  # right-trim → causal
            h = h + self.drop(self.act(y))
        x = x + h.transpose(1, 2)
        # 3. Point-wise channel mix Conv1x1, residual
        h2 = self.norm_mix(x).transpose(1, 2)
        h2 = self.conv1x1(h2).transpose(1, 2)
        return x + self.drop(self.act(h2))


class StackTcnGdcnBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 n_blocks: int = 2, kernel_size: int = 3,
                 dilations=(1, 4, 16), dropout: float = 0.15):
        super().__init__()
        self.blocks_craft = nn.Sequential(*[
            _StackBlock(d_craft, kernel_size, dilations, dropout) for _ in range(n_blocks)
        ])
        self.blocks_raw = nn.Sequential(*[
            _StackBlock(d_raw, kernel_size, dilations, dropout) for _ in range(n_blocks)
        ])
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        a = self.blocks_craft(h_craft)
        b = self.blocks_raw(h_raw)
        return self.fuse(torch.cat([a[:, -1, :], b[:, -1, :]], dim=-1))

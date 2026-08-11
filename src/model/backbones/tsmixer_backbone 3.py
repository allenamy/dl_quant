"""TSMixer-style backbone: alternating Time-MLP + Channel-MLP blocks.

Pure MLP architecture for time series (Google Research 2023). Time mixing
operates across the L dim, channel mixing across d_model. Strict alternation.
"""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F


class TSMixerBlock(nn.Module):
    def __init__(self, d_model, L, expansion_time=2, expansion_chan=2, dropout=0.15):
        super().__init__()
        d_time = L * expansion_time
        d_chan = d_model * expansion_chan
        self.time_norm = nn.LayerNorm(d_model)
        self.time_fc1 = nn.Linear(L, d_time)
        self.time_fc2 = nn.Linear(d_time, L)
        self.chan_norm = nn.LayerNorm(d_model)
        self.chan_fc1 = nn.Linear(d_model, d_chan)
        self.chan_fc2 = nn.Linear(d_chan, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # x: (B, L, d)
        # Time mixing: along L dim (transpose temporarily)
        h = self.time_norm(x).transpose(1, 2)  # (B, d, L)
        h = F.gelu(self.time_fc1(h))
        h = self.time_fc2(h)
        h = self.dropout(h).transpose(1, 2)
        x = x + h
        # Channel mixing: along d dim
        h = self.chan_norm(x)
        h = F.gelu(self.chan_fc1(h))
        h = self.chan_fc2(h)
        h = self.dropout(h)
        x = x + h
        return x


class TSMixerBackbone(nn.Module):
    def __init__(self, d_model=32, L=600, n_blocks=4, dropout=0.15):
        super().__init__()
        self.L = L
        self.blocks = nn.ModuleList([
            TSMixerBlock(d_model=d_model, L=L, dropout=dropout)
            for _ in range(n_blocks)
        ])
        self.head_norm = nn.LayerNorm(d_model)

    def forward(self, h):
        if h.size(1) != self.L:
            raise ValueError(f'TSMixer constructed for L={self.L}, got L={h.size(1)}')
        for blk in self.blocks:
            h = blk(h)
        h = self.head_norm(h)
        return h[:, -1, :]

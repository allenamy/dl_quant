"""TSMixer-lite: per-path Time-MLP + Channel-MLP, segment-pooled.

Google 2023 paradigm. Pure MLP, no attention/conv/SSM. To make compute
tractable for L=600, segment-mean-pool input down to L_seg=30 (factor 20).
Then alternating Time-MLP (over 30 dims) + Channel-MLP (over D dims) with
residuals. Take last segment, late-fuse paths.

Sanity baseline: tests whether attention/Mamba's inductive bias is actually
necessary, or if pure MLP-mixing on a coarsened time axis suffices.
"""
from __future__ import annotations
import torch
import torch.nn as nn


class _MixerBlock(nn.Module):
    def __init__(self, d: int, L_seg: int, d_ff_t: int = 64, d_ff_c: int = 64, dropout: float = 0.15):
        super().__init__()
        self.norm_t = nn.LayerNorm(d)
        self.time_mlp = nn.Sequential(
            nn.Linear(L_seg, d_ff_t), nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff_t, L_seg),
        )
        self.norm_c = nn.LayerNorm(d)
        self.chan_mlp = nn.Sequential(
            nn.Linear(d, d_ff_c), nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff_c, d),
        )
        self.drop = nn.Dropout(dropout)

    def forward(self, h: torch.Tensor) -> torch.Tensor:  # (B, L_seg, D)
        # Time mixing: transpose to (B, D, L_seg), apply MLP over L_seg, transpose back
        h_t = self.norm_t(h).transpose(1, 2)  # (B, D, L_seg)
        h_t = self.time_mlp(h_t).transpose(1, 2)
        h = h + self.drop(h_t)
        # Channel mixing: MLP over last dim
        h = h + self.drop(self.chan_mlp(self.norm_c(h)))
        return h


class TSMixerLiteBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 L: int = 600, L_seg: int = 30, n_blocks: int = 4,
                 d_ff_t: int = 64, d_ff_c: int = 64, dropout: float = 0.15):
        super().__init__()
        assert L % L_seg == 0, f"L={L} must be divisible by L_seg={L_seg}"
        self.seg_size = L // L_seg
        self.L_seg = L_seg
        self.blocks_craft = nn.ModuleList([
            _MixerBlock(d_craft, L_seg, d_ff_t, d_ff_c, dropout) for _ in range(n_blocks)
        ])
        self.blocks_raw = nn.ModuleList([
            _MixerBlock(d_raw, L_seg, d_ff_t, d_ff_c, dropout) for _ in range(n_blocks)
        ])
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def _segment_pool(self, h: torch.Tensor) -> torch.Tensor:
        B, L, D = h.shape
        return h.reshape(B, self.L_seg, self.seg_size, D).mean(dim=2)

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        a = self._segment_pool(h_craft)
        for blk in self.blocks_craft:
            a = blk(a)
        b = self._segment_pool(h_raw)
        for blk in self.blocks_raw:
            b = blk(b)
        return self.fuse(torch.cat([a[:, -1, :], b[:, -1, :]], dim=-1))

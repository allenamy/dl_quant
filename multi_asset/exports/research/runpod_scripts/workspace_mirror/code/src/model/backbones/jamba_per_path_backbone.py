"""Jamba-style per-path: Mamba layer + Attention layer + FFN, alternating.

AI21+Anthropic 2024 Jamba paradigm — alternates Mamba (linear long-range)
with Attention (detailed local). For each path, runs 2 Mamba+Attn blocks
then takes last timestep. Combines our two strongest individual extractors.
"""
from __future__ import annotations
import torch
import torch.nn as nn
try:
    from mamba_ssm import Mamba
except ImportError:
    Mamba = None


class _JambaBlock(nn.Module):
    def __init__(self, d: int, n_heads: int = 2, d_ff: int = 64, dropout: float = 0.15,
                 d_state: int = 16, d_conv: int = 4, expand: int = 2):
        super().__init__()
        # Ensure n_heads divides d
        if d % n_heads != 0:
            n_heads = max(1, d // 8)
            while d % n_heads != 0 and n_heads > 1:
                n_heads -= 1
        self.norm_m = nn.LayerNorm(d)
        self.mamba = Mamba(d_model=d, d_state=d_state, d_conv=d_conv, expand=expand)
        self.norm_a = nn.LayerNorm(d)
        self.attn = nn.MultiheadAttention(d, n_heads, batch_first=True, dropout=dropout)
        self.norm_f = nn.LayerNorm(d)
        self.ffn = nn.Sequential(
            nn.Linear(d, d_ff), nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d),
        )
        self.drop = nn.Dropout(dropout)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        # Mamba sub-layer
        h = h + self.drop(self.mamba(self.norm_m(h)))
        # Causal-mask self-attention
        L = h.size(1)
        mask = torch.triu(torch.ones(L, L, device=h.device, dtype=torch.bool), diagonal=1)
        a = self.norm_a(h)
        attn_out, _ = self.attn(a, a, a, attn_mask=mask, need_weights=False)
        h = h + self.drop(attn_out)
        # FFN sub-layer
        h = h + self.drop(self.ffn(self.norm_f(h)))
        return h


class JambaPerPathBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 n_blocks: int = 2, n_heads: int = 2, d_ff: int = 64,
                 d_state: int = 16, d_conv: int = 4, expand: int = 2,
                 dropout: float = 0.15):
        super().__init__()
        if Mamba is None:
            raise ImportError("mamba-ssm not installed")
        self.blocks_craft = nn.ModuleList([
            _JambaBlock(d_craft, n_heads, d_ff, dropout, d_state, d_conv, expand)
            for _ in range(n_blocks)
        ])
        self.blocks_raw = nn.ModuleList([
            _JambaBlock(d_raw, max(1, n_heads), d_ff, dropout, d_state, d_conv, expand)
            for _ in range(n_blocks)
        ])
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        a = h_craft
        for blk in self.blocks_craft:
            a = blk(a)
        b = h_raw
        for blk in self.blocks_raw:
            b = blk(b)
        return self.fuse(torch.cat([a[:, -1, :], b[:, -1, :]], dim=-1))

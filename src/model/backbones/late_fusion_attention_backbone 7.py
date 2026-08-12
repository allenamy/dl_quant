"""Late fusion + Self-Attention per path.

Each path runs causal self-attention over its own d-dim trajectory, then late fuse.
Tests: does attention work better when each path has its own time model
(vs current 'attention' backbone which attention-pools fused 32-dim).
"""
from __future__ import annotations
import torch
import torch.nn as nn


class CausalSelfAttn(nn.Module):
    def __init__(self, d_model, n_heads=2, d_ff=64, dropout=0.15):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True, dropout=dropout)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_ff, d_model), nn.Dropout(dropout),
        )

    def forward(self, x):
        L = x.size(1)
        causal = torch.triu(torch.ones(L, L, dtype=torch.bool, device=x.device), diagonal=1)
        h = self.norm1(x)
        h_attn, _ = self.attn(h, h, h, attn_mask=causal, need_weights=False)
        x = x + h_attn
        x = x + self.ffn(self.norm2(x))
        return x


class LateFusionAttentionBackbone(nn.Module):
    def __init__(self, d_craft=32, d_raw=16, d_out=32, n_heads=2, d_ff=64, n_blocks=1, dropout=0.15):
        super().__init__()
        self.attn_craft = nn.ModuleList([
            CausalSelfAttn(d_craft, n_heads=n_heads, d_ff=d_ff, dropout=dropout)
            for _ in range(n_blocks)
        ])
        # Path B has d_raw=16, may not be divisible by n_heads, fall back to 1 head if needed
        n_heads_b = n_heads if d_raw % n_heads == 0 else 1
        self.attn_raw = nn.ModuleList([
            CausalSelfAttn(d_raw, n_heads=n_heads_b, d_ff=d_ff, dropout=dropout)
            for _ in range(n_blocks)
        ])
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out), nn.LeakyReLU(0.1), nn.Dropout(dropout),
        )

    def forward(self, h_craft, h_raw):
        for blk in self.attn_craft: h_craft = blk(h_craft)
        for blk in self.attn_raw:   h_raw = blk(h_raw)
        return self.fuse(torch.cat([h_craft[:, -1, :], h_raw[:, -1, :]], dim=-1))

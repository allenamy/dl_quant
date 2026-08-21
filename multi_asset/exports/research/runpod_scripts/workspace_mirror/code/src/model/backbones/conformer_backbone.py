"""Conformer-style backbone: alternating Conv (time+channel) + Self-Attention + FFN.

Each block: 0.5·FFN → SelfAttn → Conv → 0.5·FFN (sandwich, residual).
Conformer combines convolution's local pattern strength with attention's long-range.
"""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F


class ConformerConvModule(nn.Module):
    def __init__(self, d_model, kernel_size=15, dropout=0.15):
        super().__init__()
        self.norm = nn.LayerNorm(d_model)
        self.conv1 = nn.Conv1d(d_model, 2 * d_model, kernel_size=1)
        # Depthwise causal conv
        self.dw_conv = nn.Conv1d(d_model, d_model, kernel_size=kernel_size,
                                 padding=kernel_size - 1, groups=d_model)
        self.bn = nn.BatchNorm1d(d_model)
        self.silu = nn.SiLU()
        self.conv2 = nn.Conv1d(d_model, d_model, kernel_size=1)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # x: (B, L, d) → (B, d, L)
        h = self.norm(x).transpose(1, 2)
        h = self.conv1(h)
        h = F.glu(h, dim=1)  # (B, d, L)
        h = self.dw_conv(h)
        h = h[:, :, :x.size(1)]  # causal trim
        h = self.bn(h)
        h = self.silu(h)
        h = self.conv2(h)
        h = self.dropout(h)
        return h.transpose(1, 2)


class ConformerFFN(nn.Module):
    def __init__(self, d_model, expansion=4, dropout=0.15):
        super().__init__()
        d_ff = d_model * expansion
        self.norm = nn.LayerNorm(d_model)
        self.fc1 = nn.Linear(d_model, d_ff)
        self.fc2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        h = self.norm(x)
        h = F.silu(self.fc1(h))
        h = self.dropout(h)
        h = self.fc2(h)
        return self.dropout(h)


class ConformerBlock(nn.Module):
    def __init__(self, d_model=32, n_heads=2, kernel_size=15, dropout=0.15):
        super().__init__()
        self.ffn1 = ConformerFFN(d_model, expansion=4, dropout=dropout)
        self.norm_attn = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True, dropout=dropout)
        self.conv = ConformerConvModule(d_model, kernel_size=kernel_size, dropout=dropout)
        self.ffn2 = ConformerFFN(d_model, expansion=4, dropout=dropout)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, x):
        # Causal mask for self-attn
        L = x.size(1)
        causal = torch.triu(torch.ones(L, L, dtype=torch.bool, device=x.device), diagonal=1)
        x = x + 0.5 * self.ffn1(x)
        h = self.norm_attn(x)
        h_attn, _ = self.attn(h, h, h, attn_mask=causal, need_weights=False)
        x = x + h_attn
        x = x + self.conv(x)
        x = x + 0.5 * self.ffn2(x)
        return self.norm(x)


class ConformerBackbone(nn.Module):
    def __init__(self, d_model=32, n_blocks=2, n_heads=2, kernel_size=15, dropout=0.15):
        super().__init__()
        self.blocks = nn.ModuleList([
            ConformerBlock(d_model=d_model, n_heads=n_heads,
                           kernel_size=kernel_size, dropout=dropout)
            for _ in range(n_blocks)
        ])

    def forward(self, h):
        for blk in self.blocks:
            h = blk(h)
        if getattr(self, 'return_sequence', False):
            return h
        return h[:, -1, :]

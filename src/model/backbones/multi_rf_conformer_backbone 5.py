"""Multi-RF Conformer per path: Mamba (long-range) → Conformer (short+full RF) ×2.

Designed to address V4's RF-mismatch (15s RF vs 600s horizon) in a way that
avoids past failures of pure parallel multi-extractor (multi_extract_gated):
sequential stacking, not parallel — Mamba captures long-range dependencies,
Conformer block adds explicit short-range conv (kernel 15s) plus full-context
attention. This couples short and long RF without inter-branch competition.

Per path:
  Layer 1: LayerNorm → Mamba → residual
  Layer 2: LayerNorm → ConformerBlock(kernel=15) → residual
  Layer 3: LayerNorm → ConformerBlock(kernel=15) → residual
  → take last timestep
Late fuse two paths.
"""
from __future__ import annotations
import torch
import torch.nn as nn
try:
    from mamba_ssm import Mamba
except ImportError:
    Mamba = None


class _ConformerSubBlock(nn.Module):
    """Conformer-style block: 0.5·FFN → SelfAttn → ConvModule → 0.5·FFN."""
    def __init__(self, d: int, n_heads: int = 2, d_ff: int = 64,
                 conv_kernel: int = 15, dropout: float = 0.15):
        super().__init__()
        if d % n_heads != 0:
            n_heads = max(1, d // 8)
            while d % n_heads != 0 and n_heads > 1:
                n_heads -= 1
        self.norm_ff1 = nn.LayerNorm(d)
        self.ff1 = nn.Sequential(
            nn.Linear(d, d_ff), nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d),
        )
        self.norm_attn = nn.LayerNorm(d)
        self.attn = nn.MultiheadAttention(d, n_heads, batch_first=True, dropout=dropout)
        self.norm_conv = nn.LayerNorm(d)
        # Causal depthwise conv: kernel size 15 → RF=15s (V4-like)
        self.conv = nn.Conv1d(d, d, conv_kernel, padding=conv_kernel - 1, groups=d)
        self.conv_act = nn.GELU()
        self.norm_ff2 = nn.LayerNorm(d)
        self.ff2 = nn.Sequential(
            nn.Linear(d, d_ff), nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d),
        )
        self.drop = nn.Dropout(dropout)

    def forward(self, h: torch.Tensor) -> torch.Tensor:  # (B, L, D)
        # 0.5·FFN
        h = h + 0.5 * self.drop(self.ff1(self.norm_ff1(h)))
        # Causal self-attention
        L = h.size(1)
        mask = torch.triu(torch.ones(L, L, device=h.device, dtype=torch.bool), diagonal=1)
        a = self.norm_attn(h)
        att, _ = self.attn(a, a, a, attn_mask=mask, need_weights=False)
        h = h + self.drop(att)
        # Causal depthwise conv (right-trim)
        c = self.norm_conv(h).transpose(1, 2)  # (B, D, L)
        c = self.conv(c)[:, :, :L]
        c = self.conv_act(c).transpose(1, 2)
        h = h + self.drop(c)
        # 0.5·FFN
        h = h + 0.5 * self.drop(self.ff2(self.norm_ff2(h)))
        return h


class _MultiRFPath(nn.Module):
    def __init__(self, d: int, mamba_kwargs: dict, n_conformer: int = 2,
                 conv_kernel: int = 15, n_heads: int = 2, d_ff: int = 64,
                 dropout: float = 0.15):
        super().__init__()
        self.norm_mamba = nn.LayerNorm(d)
        self.mamba = Mamba(d_model=d, **mamba_kwargs)
        self.drop = nn.Dropout(dropout)
        self.conformer_blocks = nn.ModuleList([
            _ConformerSubBlock(d, n_heads, d_ff, conv_kernel, dropout)
            for _ in range(n_conformer)
        ])

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        # Layer 1: Mamba (long-range)
        h = h + self.drop(self.mamba(self.norm_mamba(h)))
        # Layer 2-3: Conformer (short conv RF + full attn)
        for blk in self.conformer_blocks:
            h = blk(h)
        return h


class MultiRfConformerBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 d_state: int = 16, d_conv: int = 4, expand: int = 2,
                 n_conformer: int = 2, conv_kernel: int = 15,
                 n_heads: int = 2, d_ff: int = 64, dropout: float = 0.15):
        super().__init__()
        if Mamba is None:
            raise ImportError("mamba-ssm not installed")
        mk = dict(d_state=d_state, d_conv=d_conv, expand=expand)
        self.path_craft = _MultiRFPath(d_craft, mk, n_conformer, conv_kernel,
                                       n_heads, d_ff, dropout)
        self.path_raw = _MultiRFPath(d_raw, mk, n_conformer, conv_kernel,
                                     n_heads, d_ff, dropout)
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        a = self.path_craft(h_craft)
        b = self.path_raw(h_raw)
        return self.fuse(torch.cat([a[:, -1, :], b[:, -1, :]], dim=-1))

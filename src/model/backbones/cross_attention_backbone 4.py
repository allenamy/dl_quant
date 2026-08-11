"""Cross-attention fusion: Path A self-attn + cross-attend to Path B (and vice versa).

Lets each path attend to the OTHER path's hidden states, learning what cross-path
information is relevant at each timestep. More expressive than late_fusion's
independent processing.
"""
from __future__ import annotations
import torch
import torch.nn as nn


class CrossAttentionBlock(nn.Module):
    def __init__(self, d_q, d_kv, n_heads=2, d_ff=64, dropout=0.15):
        super().__init__()
        # Project kv path to query path's dim if mismatched
        self.kv_proj = nn.Linear(d_kv, d_q) if d_kv != d_q else nn.Identity()
        n_heads_safe = n_heads if d_q % n_heads == 0 else 1
        self.norm_q = nn.LayerNorm(d_q)
        self.norm_kv = nn.LayerNorm(d_q)
        self.self_attn = nn.MultiheadAttention(d_q, n_heads_safe, batch_first=True, dropout=dropout)
        self.cross_attn = nn.MultiheadAttention(d_q, n_heads_safe, batch_first=True, dropout=dropout)
        self.norm_ffn = nn.LayerNorm(d_q)
        self.ffn = nn.Sequential(
            nn.Linear(d_q, d_ff), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_ff, d_q), nn.Dropout(dropout),
        )

    def forward(self, q, kv):
        L = q.size(1)
        kv_proj = self.kv_proj(kv)
        causal = torch.triu(torch.ones(L, L, dtype=torch.bool, device=q.device), diagonal=1)
        # Self-attention on q
        h = self.norm_q(q)
        h_self, _ = self.self_attn(h, h, h, attn_mask=causal, need_weights=False)
        q = q + h_self
        # Cross-attention: q attends to kv_proj
        h = self.norm_kv(q)
        kv_norm = self.norm_kv(kv_proj)  # share norm — projects already to q dim
        h_cross, _ = self.cross_attn(h, kv_norm, kv_norm, attn_mask=causal, need_weights=False)
        q = q + h_cross
        # FFN
        q = q + self.ffn(self.norm_ffn(q))
        return q


class CrossAttentionBackbone(nn.Module):
    def __init__(self, d_craft=32, d_raw=16, d_out=32, n_heads=2, d_ff=64, dropout=0.15):
        super().__init__()
        # Path A queries B (asymmetric — manual features query LOB structure)
        self.block = CrossAttentionBlock(d_craft, d_raw, n_heads=n_heads, d_ff=d_ff, dropout=dropout)
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out), nn.LeakyReLU(0.1), nn.Dropout(dropout),
        )

    def forward(self, h_craft, h_raw):
        # Path A: cross-attended (with self + cross)
        h_a = self.block(h_craft, h_raw)
        # Path B: untouched, last-timestep slice
        return self.fuse(torch.cat([h_a[:, -1, :], h_raw[:, -1, :]], dim=-1))

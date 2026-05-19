"""Cross-Attention Regime Gate (Track REG_arch_v3).

Replaces FiLM γ+β modulation with multi-head cross-attention where:
  - Queries: hidden state h (B, T, d_model) or (B, d_model)
  - Keys/Values: regime_prior projected to (B, K_regime_tokens, d_model)

More expressive than FiLM (which is per-channel affine):
  - Multi-head attention allows different aspects of regime to influence
    different parts of h
  - Position-specific attention for sequence inputs (different timesteps
    can attend to regime differently)

For 2D h (post-pool): h_new = h + Attention(Q=h, K=regime_tokens, V=regime_tokens)
For 3D h (sequence): same with per-timestep query

Residual connection (h + attn) ensures identity start (zero-init output proj).
"""
from __future__ import annotations
import torch
from torch import nn


class CrossAttentionRegimeGate(nn.Module):
    def __init__(self, d_prior: int, d_hidden: int, n_heads: int = 2,
                 n_regime_tokens: int = 4, dropout: float = 0.1):
        super().__init__()
        self.n_tokens = n_regime_tokens
        self.d_hidden = d_hidden
        # Project regime prior to K_tokens × d_hidden for K/V
        self.regime_proj = nn.Linear(d_prior, n_regime_tokens * d_hidden)
        self.attn = nn.MultiheadAttention(d_hidden, n_heads, batch_first=True, dropout=dropout)
        self.out_proj = nn.Linear(d_hidden, d_hidden)
        # Zero-init output proj for identity start
        nn.init.zeros_(self.out_proj.weight)
        nn.init.zeros_(self.out_proj.bias)

    def forward(self, h: torch.Tensor, regime_prior: torch.Tensor) -> torch.Tensor:
        # regime_prior: (B, d_prior) → (B, n_tokens, d_hidden)
        B = regime_prior.size(0)
        kv = self.regime_proj(regime_prior).view(B, self.n_tokens, self.d_hidden)
        if h.dim() == 2:
            q = h.unsqueeze(1)  # (B, 1, d) — treat as single position
            attn_out, _ = self.attn(q, kv, kv, need_weights=False)
            attn_out = attn_out.squeeze(1)  # (B, d)
        else:
            # h: (B, T, d)
            attn_out, _ = self.attn(h, kv, kv, need_weights=False)
            # (B, T, d)
        return h + self.out_proj(attn_out)  # residual + zero-init output

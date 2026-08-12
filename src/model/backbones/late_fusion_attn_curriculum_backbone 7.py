"""late_fusion_attn with stochastic gradient-detach curriculum.

Same as LateFusionAttentionBackbone but adds an early-training "anti-collapse"
trick: at training time the attention output's gradient is stochastically
detached with probability that decays over global steps. The fuse layer thus
can adapt to the craft path before attention's gradient pulls it toward the
collapsed-equilibrium that pure attention configs reach in this dataset.
"""
from __future__ import annotations
import torch
import torch.nn as nn


class _CausalSelfAttn(nn.Module):
    def __init__(self, d: int, n_heads: int, d_ff: int, dropout: float):
        super().__init__()
        if d % n_heads != 0:
            n_heads = max(1, d // 8)
            while d % n_heads != 0 and n_heads > 1:
                n_heads -= 1
        self.norm1 = nn.LayerNorm(d)
        self.attn = nn.MultiheadAttention(d, n_heads, batch_first=True, dropout=dropout)
        self.norm2 = nn.LayerNorm(d)
        self.ffn = nn.Sequential(nn.Linear(d, d_ff), nn.GELU(), nn.Dropout(dropout), nn.Linear(d_ff, d))
        self.drop = nn.Dropout(dropout)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        L = h.size(1)
        mask = torch.triu(torch.ones(L, L, device=h.device, dtype=torch.bool), diagonal=1)
        a = self.norm1(h)
        att, _ = self.attn(a, a, a, attn_mask=mask, need_weights=False)
        h = h + self.drop(att)
        h = h + self.drop(self.ffn(self.norm2(h)))
        return h


class LateFusionAttnCurriculumBackbone(nn.Module):
    """Per-path attention with curriculum gradient detach.

    Detach probability ramps linearly from 1.0 → 0.0 over `warmup_steps` of
    training. Only applied at train-time. After warmup, behaves identically
    to plain late_fusion_attn.
    """
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 n_heads: int = 2, d_ff: int = 64, n_blocks: int = 1,
                 warmup_steps: int = 2000, dropout: float = 0.15):
        super().__init__()
        self.blocks_craft = nn.Sequential(*[
            _CausalSelfAttn(d_craft, n_heads, d_ff, dropout) for _ in range(n_blocks)
        ])
        self.blocks_raw = nn.Sequential(*[
            _CausalSelfAttn(d_raw, max(1, n_heads), d_ff, dropout) for _ in range(n_blocks)
        ])
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )
        self.register_buffer("step", torch.tensor(0, dtype=torch.long))
        self.warmup_steps = int(warmup_steps)

    def _maybe_detach(self, h: torch.Tensor) -> torch.Tensor:
        if not self.training:
            return h
        # Ramp detach probability from 1 → 0 over warmup
        s = float(self.step.item())
        p = max(0.0, 1.0 - s / max(1, self.warmup_steps))
        if torch.rand(1, device=h.device).item() < p:
            return h.detach()
        return h

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        a = self.blocks_craft(h_craft)
        b = self.blocks_raw(h_raw)
        # Stochastically detach attention path output's gradient
        a = self._maybe_detach(a)
        b = self._maybe_detach(b)
        if self.training:
            self.step += 1
        return self.fuse(torch.cat([a[:, -1, :], b[:, -1, :]], dim=-1))

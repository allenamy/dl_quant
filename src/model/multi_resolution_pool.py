"""Multi-Resolution Attention Pool (Track E, v5push Phase 3).

V5 uses a single AttentionPool1D over time T=600 → (B, d_model).
This may smear over time scales: recent dynamics (last 60s) vs longer regime
context (full 600s). Multi-resolution explicitly separates them:

  recent_pool  : attention over last 60s of T → (B, d_model)
  mid_pool     : attention over last 300s     → (B, d_model)
  long_pool    : attention over full 600s     → (B, d_model)
  concat → Linear(3·d_model → d_model) → (B, d_model)

Compared to single-pool: 3 separate softmax temperatures + learnable mixing.
Same downstream interface (returns (B, d_model)) so MonotonicQuantileHead /
DAQH receive identical-shape input.

Param overhead: 3 × (d_model) scores + Linear(3·d_model, d_model) ≈ 3 × 32 + 96·32 ≈ 3.2K.
"""
from __future__ import annotations
import torch
from torch import nn
import torch.nn.functional as F


class MultiResolutionPool(nn.Module):
    """Pool along time with 3 resolutions: recent / mid / long.

    Input  : (B, T, d_model) — Conformer output (sequence-first).
    Output : (B, d_model).
    """

    def __init__(self, d_model: int, T: int = 600,
                 recent_window: int = 60, mid_window: int = 300):
        super().__init__()
        self.d_model = d_model
        self.T = T
        self.recent_window = min(recent_window, T)
        self.mid_window = min(mid_window, T)
        # 3 independent score projections (softmax over their own window)
        self.score_recent = nn.Linear(d_model, 1, bias=False)
        self.score_mid = nn.Linear(d_model, 1, bias=False)
        self.score_long = nn.Linear(d_model, 1, bias=False)
        # Mix the 3 pooled vectors back to d_model
        self.mixer = nn.Linear(3 * d_model, d_model)
        nn.init.zeros_(self.mixer.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.shape
        # Recent: last K timesteps
        Kr = self.recent_window
        x_r = x[:, -Kr:, :]
        s_r = F.softmax(self.score_recent(x_r).squeeze(-1), dim=1)
        pool_r = (x_r * s_r.unsqueeze(-1)).sum(dim=1)
        # Mid: last K timesteps
        Km = self.mid_window
        x_m = x[:, -Km:, :]
        s_m = F.softmax(self.score_mid(x_m).squeeze(-1), dim=1)
        pool_m = (x_m * s_m.unsqueeze(-1)).sum(dim=1)
        # Long: full T
        s_l = F.softmax(self.score_long(x).squeeze(-1), dim=1)
        pool_l = (x * s_l.unsqueeze(-1)).sum(dim=1)
        # Concat + mix
        concat = torch.cat([pool_r, pool_m, pool_l], dim=-1)  # (B, 3D)
        out = self.mixer(concat)
        return out

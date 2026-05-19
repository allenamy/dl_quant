"""Time-Varying FiLM Gate — per-timestep regime modulation.

Extension of FiLMGate: instead of per-sample γ, β (from regime_prior),
compute γ_t, β_t per timestep from the time-varying TV features.

  γ_t = MLP_γ(TV_t)  shape (B, T, d_hidden)
  β_t = MLP_β(TV_t)  shape (B, T, d_hidden)
  h_modulated = γ_t ⊙ h + β_t

Rationale:
  - Per-sample regime_prior (d=6) is FIXED across 600s window → cannot
    adapt to intra-window regime evolution (vol spike, liquidity drop,
    burst trade clusters).
  - TV features (sv_ewm, ofi, total_depth, etc.) ARE per-timestep and
    capture regime evolution. Using them as FiLM gate input lets γ, β
    track regime dynamics within the window.

Important design choice:
  - Project TV features (input d_tv, typically 14-19) → d_hidden gate
  - Identity init: γ→1.0, β→0.0 (gate is no-op at start, learn deviation)
  - Apply to h shape (B, T, d_model) — broadcast along d_model OK

Used after Conformer blocks like FiLMGate but condition on TV instead
of regime_prior. Can complement FiLMGate (use both: per-sample regime
gate + per-timestep TV gate stacked).
"""
from __future__ import annotations
import torch
from torch import nn


class TVFiLMGate(nn.Module):
    def __init__(self, d_tv: int, d_hidden: int, dropout: float = 0.1):
        super().__init__()
        # Shared trunk: TV features → hidden
        self.trunk = nn.Sequential(
            nn.Linear(d_tv, d_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.gamma_proj = nn.Linear(d_hidden, d_hidden)
        self.beta_proj = nn.Linear(d_hidden, d_hidden)
        # Zero-init for identity start: γ→0+1=1, β→0
        nn.init.zeros_(self.gamma_proj.weight)
        nn.init.zeros_(self.gamma_proj.bias)
        nn.init.zeros_(self.beta_proj.weight)
        nn.init.zeros_(self.beta_proj.bias)

    def forward(self, h: torch.Tensor, tv: torch.Tensor) -> torch.Tensor:
        """
        h:  (B, T, d_model) — Conformer intermediate state
        tv: (B, T, d_tv)    — time-varying features (TV overlay channels)
        Returns: (B, T, d_model)
        """
        trunk_out = self.trunk(tv)  # (B, T, d_hidden)
        gamma = self.gamma_proj(trunk_out) + 1.0  # (B, T, d_hidden), init 1.0
        beta = self.beta_proj(trunk_out)          # (B, T, d_hidden), init 0.0
        return gamma * h + beta

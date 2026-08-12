"""GLU-style gated fusion for dual-path (Path A + Path B) outputs.

Replaces concat+linear with a learned gate per channel:
  gate = σ(W_g [h_a; h_b])
  h_b_proj = W_b · h_b (d_raw → d_model)
  h = gate ⊙ h_a + (1 - gate) ⊙ h_b_proj

Param count: roughly equal to concat+linear case.
- concat+linear: (d_model + d_raw) × d_model
- glu:           (d_model + d_raw) × d_model    [gate]
                 + d_raw × d_model               [b_proj]
                 ≈ same param budget

Mechanism: model dynamically chooses, per channel and per timestep, how
much to draw from handcraft (Path A) vs raw-LOB (Path B). Concat+linear
is a static linear combination — gated is data-dependent.

Initialised so gate ≈ 0.5 (balanced fusion at start, identity-ish).
"""
from __future__ import annotations

import torch
import torch.nn as nn


class GatedFusion(nn.Module):
    def __init__(self, d_a: int, d_b: int, d_out: int, dropout: float = 0.0):
        super().__init__()
        self.d_a = int(d_a)
        self.d_b = int(d_b)
        self.d_out = int(d_out)
        # Gate from concat — same input dim as concat-linear
        self.gate_proj = nn.Linear(d_a + d_b, d_out)
        # Project Path B to d_out so we can mix it
        self.b_proj = nn.Linear(d_b, d_out)
        # Project Path A only if d_a != d_out
        if d_a != d_out:
            self.a_proj = nn.Linear(d_a, d_out)
        else:
            self.a_proj = nn.Identity()
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()
        # Initialise so gate ≈ 0.5 → balanced fusion at start
        with torch.no_grad():
            nn.init.zeros_(self.gate_proj.bias)
            nn.init.normal_(self.gate_proj.weight, mean=0.0, std=0.02)

    def forward(self, h_a: torch.Tensor, h_b: torch.Tensor) -> torch.Tensor:
        cat = torch.cat([h_a, h_b], dim=-1)
        gate = torch.sigmoid(self.gate_proj(cat))         # (B, L, d_out)
        h_a_p = self.a_proj(h_a)                          # (B, L, d_out)
        h_b_p = self.b_proj(h_b)                          # (B, L, d_out)
        out = gate * h_a_p + (1.0 - gate) * h_b_p
        return self.dropout(out)

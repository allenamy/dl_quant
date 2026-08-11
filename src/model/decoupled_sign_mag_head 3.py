"""Track P: Decoupled Sign + Magnitude Head (v5push Phase 3, 2026-05-13).

Refines DAQH by REMOVING the tanh × softplus coupling:

  sign_logit       = MLP_s(h_pred)             # supervised PURELY by BCE
  magnitude_abs    = softplus(MLP_m(h_pred))   # PURELY |q50| estimate, trained on Huber(|y|)
  δ_low, δ_high    = softplus(MLP_*(h_pred)) + min_delta
  q50              = (2 σ(sign_logit) − 1) × magnitude_abs    # inference combine
  q10              = q50 − δ_low,    q90 = q50 + δ_high

Key differences vs DAQH (`direction_aware_quantile_head.py`):
  - tanh → (2 σ(·) − 1) — same range [−1, 1] but with cleaner CE interpretation.
  - At training, sign_head loss = BCE(sign_logit, sign(y)) uniform weight.
  - At training, magnitude_head loss = Huber(magnitude_abs, |y|) × focal weight.
  - Pinball loss applied only as auxiliary on signed quantiles (small λ).
  - Two heads have non-overlapping primary losses → no gradient cross-talk.

This addresses the empirical finding (2026-05-13 brief) that pooled P=0.062
but high-vol regime P=+0.085: signal is concentrated in tail samples, but
DAQH's tanh × softplus coupling forces magnitude head to learn balanced
regression that's diluted by middle samples. Decoupling lets magnitude
focus on tail via focal weight without polluting sign learning.

Anti-pattern guards:
  - #11 (variance collapse): magnitude predicts |y| ≥ 0, NOT pushed to 0
    by sign-attraction (no shared 0 dyad with sign).
  - #12 (focal P/S divergence): focal weight applied to MAGNITUDE ONLY,
    sign head sees uniform weight → Spearman protected.
  - #20 (dir_huber 0-attractor): magnitude trained on |y| (always ≥ 0,
    never has 0 attractor where sign disappears).
"""
from __future__ import annotations
import torch
from torch import nn
import torch.nn.functional as F


class DecoupledSignMagHead(nn.Module):
    """Decoupled sign + magnitude head."""

    def __init__(
        self,
        d_input: int,
        d_hidden: int = None,
        dropout: float = 0.1,
        min_delta: float = 0.01,
    ):
        super().__init__()
        if d_hidden is None:
            d_hidden = d_input

        def _mlp():
            return nn.Sequential(
                nn.Linear(d_input, d_hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_hidden, 1),
            )

        self.sign_proj = _mlp()
        self.magnitude_proj = _mlp()
        self.delta_low_proj = _mlp()
        self.delta_high_proj = _mlp()
        self.min_delta = float(min_delta)

        # Zero-init sign final layer → σ(0)=0.5 (neutral direction)
        # Zero-init magnitude final layer → softplus(0)=ln(2)≈0.69 (small positive)
        for proj in [self.sign_proj, self.magnitude_proj]:
            nn.init.zeros_(proj[-1].weight)
            nn.init.zeros_(proj[-1].bias)

    def forward(self, h: torch.Tensor) -> dict:
        """h: (B, d_input).

        Returns dict with:
          - quantiles: (B, 3) signed q10/q50/q90
          - point_pred: (B,) signed q50
          - sign_logit: (B,) raw sign logit (for BCE)
          - magnitude_abs: (B,) magnitude estimate (for Huber on |y|)
        """
        sign_logit = self.sign_proj(h).squeeze(-1)
        mag_raw = self.magnitude_proj(h).squeeze(-1)
        magnitude_abs = F.softplus(mag_raw)
        # Center-zero sign coefficient: (2 σ(s) − 1) ∈ (−1, +1)
        sign_coef = 2.0 * torch.sigmoid(sign_logit) - 1.0
        q50 = sign_coef * magnitude_abs
        d_lo = F.softplus(self.delta_low_proj(h).squeeze(-1)) + self.min_delta
        d_hi = F.softplus(self.delta_high_proj(h).squeeze(-1)) + self.min_delta
        q10 = q50 - d_lo
        q90 = q50 + d_hi
        quantiles = torch.stack([q10, q50, q90], dim=-1)
        return {
            "quantiles": quantiles,
            "point_pred": q50,
            "sign_logit": sign_logit,
            "magnitude_abs": magnitude_abs,
        }

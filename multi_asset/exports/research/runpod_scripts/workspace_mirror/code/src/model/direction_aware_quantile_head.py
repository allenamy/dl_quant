"""Direction-Aware Quantile Head (DAQH) — v5push Phase 3 (2026-05-12).

Decouples sign from magnitude in q50 prediction:

  sign_logit  = MLP_s(h_pred)           # scalar, will be supervised by BCE
  magnitude   = softplus(MLP_m(h_pred)) # scalar ≥ 0
  q50         = tanh(sign_logit) × magnitude
  δ_low       = softplus(MLP_lo(h_pred)) + min_delta
  δ_high      = softplus(MLP_hi(h_pred)) + min_delta
  q10         = q50 - δ_low
  q90         = q50 + δ_high

Outputs sign_logit explicitly for direct BCE supervision. The Direction
component (sign_logit) is decoupled from Magnitude (softplus) so the BCE
loss gradient updates only sign_logit and the pinball/Huber/utility_rank
gradients primarily update magnitude — reduces anti-pattern #10 multi-task
gradient conflict.

Why not anti-pattern #20 (dir_huber sign-attraction 0-bug):
  - dir_huber 0-bug: model predicts ŷ≡0 to dodge sign penalty (since sign(0)=0)
  - DAQH: tanh(0) × softplus(any) = 0 at init, but as training progresses
    BCE pushes sign_logit AWAY from 0 (weighted only on |y| > threshold).
    Magnitude trained separately by Huber/pinball — doesn't collapse to 0
    because regression loss penalizes σŷ=0 directly when σy>0.
  - Net: structure is decoupled, no shared 0-attractor.

Why preserve monotonicity q10 < q50 < q90:
  - δ_low, δ_high are softplus(MLP) + min_delta ≥ min_delta > 0
  - So q10 = q50 - δ_low < q50 and q90 = q50 + δ_high > q50

Init choice: sign_proj final layer zero-init → tanh(0)=0 → q50 starts at 0.
Magnitude_proj also zero-init → softplus(0)=ln(2)≈0.69 (small positive
magnitude). Together: q50 starts at 0, no directional bias at init.
"""
from __future__ import annotations
import torch
from torch import nn
import torch.nn.functional as F


class DirectionAwareQuantileHead(nn.Module):
    """Sign + magnitude decomposed quantile head.

    Parameters
    ----------
    d_input : int
        Input dimension (= d_model of backbone pool output).
    d_hidden : int
        Hidden dimension in each MLP. Default = d_input.
    dropout : float
        Dropout probability between Linear-GELU-Dropout-Linear.
    min_delta : float
        Floor for q90-q50 and q50-q10 spreads, ensures strict monotonicity.
    """

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

        # Zero-init final layers for sign and magnitude → q50 starts at 0
        # (no direction bias). Quantile spreads start at ln(2) + min_delta.
        for proj in [self.sign_proj, self.magnitude_proj]:
            nn.init.zeros_(proj[-1].weight)
            nn.init.zeros_(proj[-1].bias)

    def forward(self, h: torch.Tensor) -> dict:
        """h: (B, d_input). Returns dict with quantiles + point_pred + sign_logit."""
        sign_logit = self.sign_proj(h).squeeze(-1)              # (B,) raw, BCE-supervised
        mag_raw = self.magnitude_proj(h).squeeze(-1)            # (B,)
        magnitude = F.softplus(mag_raw)                          # (B,) ≥ 0
        q50 = torch.tanh(sign_logit) * magnitude                 # (B,) sign × magnitude
        d_lo = F.softplus(self.delta_low_proj(h).squeeze(-1)) + self.min_delta
        d_hi = F.softplus(self.delta_high_proj(h).squeeze(-1)) + self.min_delta
        q10 = q50 - d_lo
        q90 = q50 + d_hi
        quantiles = torch.stack([q10, q50, q90], dim=-1)         # (B, 3)
        return {
            "quantiles": quantiles,
            "point_pred": q50,
            "sign_logit": sign_logit,
            "magnitude_abs": magnitude,
        }

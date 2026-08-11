"""Regime-aware FiLM (Feature-wise Linear Modulation) for low-SNR regression.

Motivation: anti-pattern #15 in CLAUDE.md — y_1800 fold 2 test σ_y was +18%
above train σ_y (vol regime shift), causing catastrophic val→test drift in
direct rank losses. Regime-conditioned modulation lets the model adapt
its predictions to detected vol regime, attacking the drift mechanism
directly.

Mechanism:
  1. RegimeFeatureExtractor: from input X (B, L, F), compute K regime
     descriptors (realized vol at multiple scales, OBI persistence, vol
     acceleration). These are deterministic functions of X — no learned
     parameters.
  2. FiLM: small MLP from K regime features → (γ, β) ∈ ℝ^{2d_model}.
     Apply to backbone output: h_out = γ ⊙ h_pred + β.
  3. EMA-friendly: γ, β learned alongside main network, EMA averaging
     stabilizes the modulation coefficients across epochs.

Distinct from σ-anchor (anti-pattern #13) because:
  - σ-anchor was a SINGLE scalar α (1 dof, val-tunable)
  - FiLM is d_model parameters CONDITIONED on data-derived regime
  - The regime features are DETERMINISTIC from input → no degrees of
    freedom to overfit val that don't exist in test
"""
from __future__ import annotations

from typing import Tuple

import torch
import torch.nn as nn


class RegimeFeatureExtractor(nn.Module):
    """Extract deterministic regime descriptors from feature tensor X.

    Output features (K=6, all per-batch-element):
      0. realized vol over last 60 timesteps  (60s scale)
      1. realized vol over last 300 timesteps (5min scale)
      2. realized vol over last 1200 timesteps (full window scale, ≈ σ at 20-min)
      3. vol acceleration: vol_60 / (vol_1200 + eps)
      4. mean of feature[0] over last 1200 timesteps (proxy: feat 0 is OBI in V4)
      5. lag-60 autocorrelation of feature[0]

    Cost: O(B * L) per batch, no gradients (operations are non-learnable
    statistics). All features standardized within batch (z-score) so FiLM
    MLP sees consistent scale.

    Parameters
    ----------
    eps : float
        Numerical floor for divisions/std.
    obi_feature_idx : int
        Index of feature column to use as "OBI proxy" for trend stats.
        V4 NPZ feature 0 is the natural candidate (depth-derived OBI).
    """

    def __init__(self, eps: float = 1e-6, obi_feature_idx: int = 0):
        super().__init__()
        self.eps = float(eps)
        self.obi_feature_idx = int(obi_feature_idx)
        self.n_features_out = 6

    @torch.no_grad()
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x : (B, L, F) input feature tensor.

        Returns
        -------
        (B, 6) regime feature tensor, batch-z-scored.
        """
        B, L, F = x.shape
        # Realized vol = std of feature[0] difference (proxy for return vol)
        feat0 = x[:, :, self.obi_feature_idx]                          # (B, L)
        # Window slices
        last_60 = feat0[:, -min(60, L):]
        last_300 = feat0[:, -min(300, L):]
        full = feat0
        vol_60 = last_60.std(dim=1) + self.eps                         # (B,)
        vol_300 = last_300.std(dim=1) + self.eps
        vol_1200 = full.std(dim=1) + self.eps
        vol_accel = vol_60 / vol_1200                                  # (B,)
        mean_feat0 = full.mean(dim=1)                                  # (B,)
        # lag-60 AC
        if L > 60:
            f1 = full[:, 60:]
            f2 = full[:, :-60]
            f1c = f1 - f1.mean(dim=1, keepdim=True)
            f2c = f2 - f2.mean(dim=1, keepdim=True)
            num = (f1c * f2c).mean(dim=1)
            den = f1c.std(dim=1) * f2c.std(dim=1) + self.eps
            ac1 = num / den
        else:
            ac1 = torch.zeros(B, device=x.device, dtype=x.dtype)
        feats = torch.stack([vol_60, vol_300, vol_1200, vol_accel, mean_feat0, ac1], dim=-1)  # (B, 6)
        # Batch-z-score for stable MLP input
        m = feats.mean(dim=0, keepdim=True)
        s = feats.std(dim=0, keepdim=True) + self.eps
        return (feats - m) / s


class FiLM(nn.Module):
    """FiLM modulator: regime features → (γ, β) → modulate backbone output.

    Output of forward(h_pred, regime_feats):
        h_modulated = γ ⊙ h_pred + β
    where γ, β ∈ ℝ^{d_model} are conditioned on regime_feats.

    Initialised so that γ ≈ 1 and β ≈ 0 (identity modulation at start),
    so the model trains to baseline if FiLM provides no useful signal.
    """

    def __init__(self, d_model: int, n_regime_feats: int, hidden: int = 16, dropout: float = 0.0):
        super().__init__()
        self.d_model = int(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(n_regime_feats, hidden),
            nn.GELU(),
            nn.Dropout(dropout) if dropout > 0 else nn.Identity(),
            nn.Linear(hidden, 2 * d_model),
        )
        # Init last layer near zero so initial γ≈1, β≈0
        with torch.no_grad():
            self.mlp[-1].weight.mul_(0.01)
            self.mlp[-1].bias.zero_()

    def forward(self, h_pred: torch.Tensor, regime_feats: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        h_pred : (B, d_model) backbone output.
        regime_feats : (B, K) regime descriptors.

        Returns
        -------
        (B, d_model) modulated features.
        """
        gamma_beta = self.mlp(regime_feats)                            # (B, 2*d_model)
        gamma, beta = gamma_beta.chunk(2, dim=-1)                      # each (B, d_model)
        # γ centred around 1.0 (init: gamma_raw ~ 0 → γ = 1 + 0 = 1)
        return (1.0 + gamma) * h_pred + beta

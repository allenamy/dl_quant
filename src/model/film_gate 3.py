"""FiLM (Feature-wise Linear Modulation) Gate — regime-conditioned γ + β.

Replaces single multiplicative PPNetGate with full FiLM (Perez et al. 2018):

  γ = MLP_γ(regime)  # per-feature scale (initialized at 1.0)
  β = MLP_β(regime)  # per-feature shift (initialized at 0.0)
  h_modulated = γ ⊙ h + β

Comparison to PPNetGate (PEPNet KDD 2023):
  - PPNet: γ ∈ [0, 2] (sigmoid×2), NO additive shift. Only multiplicative.
  - FiLM:  γ ∈ ℝ initialized at 1.0, β ∈ ℝ initialized at 0.0. Both shift + scale.

FiLM is strictly more expressive (any γ-only modulation is an FiLM with β≡0).
Used in StyleGAN, FiLM Layers (visual reasoning), and conditional generation
literature. Standard regime-conditioning primitive.

Init: γ→1.0, β→0.0 → initial pass-through is identity. Model learns when
and where to deviate from no-modulation baseline. Avoids early-training
collapse.

Usage in dual_path_model_v3:
  - Stage 1: after Conformer block 1 (h shape (B, T, d_model))
  - Stage 2: after Conformer block 2
  - Stage 3: after pool (h_pred shape (B, d_model))

Stages 1/2 apply gate broadcast across T (regime is per-sample, same across time).
Stage 3 applies directly on pooled vector.

Parameters:
  d_prior: regime prior dimension (default 6)
  d_hidden: target hidden dim (= d_model, typically 32)
"""
from __future__ import annotations
import torch
from torch import nn


class FiLMGate(nn.Module):
    def __init__(self, d_prior: int, d_hidden: int, dropout: float = 0.1,
                 deeper_trunk: bool = False):
        """
        deeper_trunk (Track REG_arch_v6a): 加 1 个 hidden 非线性 layer 让 regime info
        学到 non-linear embedding. 适用场景: regime_prior d 较低 (≤6) 时, 6→32 单层 trunk
        难以表达"低 vol 趋势" vs "低 vol 反转"等组合 regime. +(d_hidden² + d_hidden) ≈ 1K params
        per gate (3 gates = 3K total, negligible vs 118K baseline).
        """
        super().__init__()
        # Shared trunk: regime → hidden
        if deeper_trunk:
            self.trunk = nn.Sequential(
                nn.Linear(d_prior, d_hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_hidden, d_hidden),  # 新 hidden layer
                nn.GELU(),
                nn.Dropout(dropout),
            )
        else:
            self.trunk = nn.Sequential(
                nn.Linear(d_prior, d_hidden),
                nn.GELU(),
                nn.Dropout(dropout),
            )
        # γ head — scale, init at 1.0
        self.gamma_proj = nn.Linear(d_hidden, d_hidden)
        # β head — shift, init at 0.0
        self.beta_proj = nn.Linear(d_hidden, d_hidden)
        # Zero-init both projections so γ→0+1 (we add 1), β→0
        nn.init.zeros_(self.gamma_proj.weight)
        nn.init.zeros_(self.gamma_proj.bias)
        nn.init.zeros_(self.beta_proj.weight)
        nn.init.zeros_(self.beta_proj.bias)

    def forward(self, h: torch.Tensor, prior: torch.Tensor) -> torch.Tensor:
        """Apply FiLM modulation.

        h: (B, d_model) or (B, T, d_model)
        prior: (B, d_prior)
        Returns: same shape as h
        """
        # Compute γ, β from regime
        trunk_out = self.trunk(prior)  # (B, d_hidden)
        gamma = self.gamma_proj(trunk_out) + 1.0  # init: 1.0 + zero = 1.0
        beta = self.beta_proj(trunk_out)          # init: 0.0
        # Broadcast for sequence inputs (B, T, d) — add T axis to γ, β
        if h.dim() == 3:
            gamma = gamma.unsqueeze(1)  # (B, 1, d) — broadcasts over T
            beta = beta.unsqueeze(1)
        return gamma * h + beta

"""SE-block (Squeeze-Excitation) for X-channel attention.

v5push Track A1 (2026-05-15): per-sample channel re-weighting on the input
feature tensor. Goal: let model learn "which X channels matter for current
sample's regime" WITHOUT adding new channels (channel addition penalty
documented in v6b/v7/v8 NEG, ~-0.013 P per 4 channels added).

Architecture (Hu 2018 SENet):
  X: (B, T, C) — input feature tensor
  Squeeze:    z = mean(X, dim=T) → (B, C)
  Excitation: w = sigmoid(Linear(ReLU(Linear(z, hidden))), C)) → (B, C)
  Scale:      X_out = X * w[:, None, :]

Channel re-weighting is per-SAMPLE (different sample → different gate). The
weighting is BOUNDED [0, 1] (sigmoid). With bias init = +large, initial sigmoid
output ≈ 1 (near-identity), keeping baseline-equivalent behavior at start.

Cheap: ~(C × hidden) + (hidden × C) = 2·C·hidden params (e.g., 64·16·2 = 2,048).
"""
from __future__ import annotations
import torch
from torch import nn


class SEBlock(nn.Module):
    def __init__(self, n_features: int, reduction: int = 4, init_open: bool = True):
        """
        Parameters
        ----------
        n_features : input channel count.
        reduction : channel-reduction ratio for the bottleneck (default 4 →
            hidden = n_features // 4 = 16 for C=64).
        init_open : if True (default), bias-init the final Linear so initial
            sigmoid output ≈ 1.0 (near-identity gating). Lets training start
            close to baseline behavior and learn channel-specific deviations.
        """
        super().__init__()
        hidden = max(n_features // max(reduction, 1), 4)
        self.fc1 = nn.Linear(n_features, hidden)
        self.fc2 = nn.Linear(hidden, n_features)
        if init_open:
            # Zero-init fc2.weight + large positive bias → sigmoid(bias)≈1.0
            nn.init.zeros_(self.fc2.weight)
            nn.init.constant_(self.fc2.bias, 5.0)  # sigmoid(5)≈0.993

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, T, C)
        Returns: (B, T, C) — channel-rescaled.
        """
        # Squeeze: mean over time
        z = x.mean(dim=1)  # (B, C)
        # Excitation: MLP → sigmoid (per-channel gate ∈ [0, 1])
        z = torch.relu(self.fc1(z))
        gate = torch.sigmoid(self.fc2(z))  # (B, C)
        # Scale: broadcast gate over T
        return x * gate.unsqueeze(1)

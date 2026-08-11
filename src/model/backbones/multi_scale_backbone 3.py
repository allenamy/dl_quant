"""Multi-scale parallel encoder backbone for mid-horizon (y_1800) prediction.

Motivation: y_1800 (30-min) needs BOTH microstructure (last 60s, immediate
order flow) AND trend context (full 1200s, vol regime). Existing single-scale
backbones (ema_pool, conv_lasts, GRU, Mamba) all force one trade-off.

Architecture:
  Input h: (B, L, d_model) from upstream Path-A+B fusion
   ├── Branch A (macro): full L=1200, EMA-pool over time
   ├── Branch B (meso): last 300s, mean-pool
   └── Branch C (micro): last 60s, last-token slice
  Fusion: concat (3*d_model) → Linear → d_model

Each branch contributes a different temporal "view" of the same upstream features.
The fusion linear learns optimal weighting.

Forward signature matches other backbones in src/model/backbones/:
  forward(h: Tensor[B, L, D]) -> Tensor[B, D]
"""
from __future__ import annotations

import torch
import torch.nn as nn


class MultiScaleBackbone(nn.Module):
    """Three parallel temporal encoders at different scales, then fuse."""

    def __init__(
        self,
        d_model: int,
        scales: tuple[int, int, int] = (60, 300, 1200),
        dropout: float = 0.15,
        ema_decay: float = 0.95,
    ):
        super().__init__()
        if len(scales) != 3:
            raise ValueError(f"expected 3 scales, got {scales}")
        self.d_model = int(d_model)
        self.scales = tuple(int(s) for s in scales)
        self.ema_decay = float(ema_decay)

        # Pre-projection per branch (keeps d_model consistent).
        # No actual conv inside — branches are simple pool ops; the upstream
        # already provides causal-conv-encoded features.
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

        # Fusion: concat 3 d_model → Linear → d_model.
        self.fuse = nn.Linear(3 * d_model, d_model)
        # Init fuse linear so each branch contributes equally at start
        with torch.no_grad():
            nn.init.kaiming_normal_(self.fuse.weight, nonlinearity="relu")

    def _ema_pool(self, h: torch.Tensor, decay: float) -> torch.Tensor:
        """EMA over time dim: o_t = (1-d) * h_t + d * o_{t-1}, return final o_T."""
        # Iterative O(L) but L=1200 is fine
        o = h[:, 0, :]                                      # (B, D)
        for t in range(1, h.shape[1]):
            o = (1.0 - decay) * h[:, t, :] + decay * o
        return o

    def _mean_pool(self, h: torch.Tensor) -> torch.Tensor:
        return h.mean(dim=1)                                # (B, D)

    def _last_token(self, h: torch.Tensor) -> torch.Tensor:
        return h[:, -1, :]                                  # (B, D)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        h : (B, L, d_model) upstream encoded features.

        Returns
        -------
        (B, d_model) fused output.
        """
        B, L, D = h.shape
        s_micro, s_meso, s_macro = self.scales

        # Branch A (macro): full sequence, EMA-pool — captures long-term regime
        h_macro = self._ema_pool(h, self.ema_decay)         # (B, D)

        # Branch B (meso): last s_meso steps, mean-pool — recent trend
        last_meso = h[:, -min(s_meso, L):, :]
        h_meso = self._mean_pool(last_meso)                 # (B, D)

        # Branch C (micro): last s_micro steps, mean-pool over short window
        # (last_token would be 1 sample, mean over last 60s is more robust)
        last_micro = h[:, -min(s_micro, L):, :]
        h_micro = self._mean_pool(last_micro)               # (B, D)

        # Concat + fuse
        cat = torch.cat([h_macro, h_meso, h_micro], dim=-1) # (B, 3D)
        out = self.fuse(self.dropout(cat))                  # (B, D)
        return out

"""Spatial LOB encoder with bid/ask/global feature-group attention.

Processes each timestep independently (no temporal mixing) using
cross-group multi-head attention over three feature groups:
bid-related, ask-related, and global/shared features.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class FeatureGroupAttention(nn.Module):
    """Multi-head attention + pre-norm FFN over a small set of group tokens.

    Architecture per block:
        x -> MHA(x, x, x) + x  (residual)  -> LayerNorm
          -> FFN                + x  (residual)  -> LayerNorm
    """

    def __init__(self, d_model: int, n_heads: int = 2, ffn_mult: int = 4, dropout: float = 0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.norm1 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_model * ffn_mult),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model * ffn_mult, d_model),
            nn.Dropout(dropout),
        )
        self.norm2 = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, 3, d_model) -> (B, 3, d_model)"""
        # Pre-norm MHA + residual
        x_norm = self.norm1(x)
        attn_out, _ = self.attn(x_norm, x_norm, x_norm, need_weights=False)
        x = x + attn_out

        # Pre-norm FFN + residual
        x_norm = self.norm2(x)
        x = x + self.ffn(x_norm)

        return x


class SpatialLOBEncoder(nn.Module):
    """Per-timestep spatial encoder with bid/ask/global group attention.

    Parameters
    ----------
    n_features : int
        Number of input features per timestep.
    d_model : int
        Hidden dimension for each group token and final output.
    n_heads : int
        Number of attention heads in FeatureGroupAttention.
    ffn_mult : int
        FFN expansion factor inside FeatureGroupAttention.
    dropout : float
        Dropout probability.
    """

    def __init__(
        self,
        n_features: int,
        d_model: int = 128,
        n_heads: int = 2,
        ffn_mult: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.n_features = n_features
        self.d_model = d_model

        # Default feature group split: roughly equal thirds
        third = n_features // 3
        remainder = n_features - 2 * third
        self._bid_idx: List[int] = list(range(0, third))
        self._ask_idx: List[int] = list(range(third, 2 * third))
        self._global_idx: List[int] = list(range(2 * third, 2 * third + remainder))

        # Projection layers (rebuilt when feature groups change)
        self._build_projections()

        # Cross-group attention
        self.group_attn = FeatureGroupAttention(d_model, n_heads, ffn_mult, dropout)

        # Final merge: concat 3 group tokens -> d_model
        self.merge = nn.Sequential(
            nn.Linear(3 * d_model, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    # ------------------------------------------------------------------
    # Projection builders (called on init and after set_feature_groups)
    # ------------------------------------------------------------------

    def _build_projections(self) -> None:
        """Create or recreate linear projections matching current group sizes."""
        self.proj_bid = nn.Linear(len(self._bid_idx), self.d_model)
        self.proj_ask = nn.Linear(len(self._ask_idx), self.d_model)
        self.proj_global = nn.Linear(len(self._global_idx), self.d_model)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_feature_groups(
        self,
        bid_idx: List[int],
        ask_idx: List[int],
        global_idx: List[int],
    ) -> None:
        """Explicitly configure which input feature indices belong to each group.

        After calling this method the projection layers are rebuilt to match
        the new group sizes.  Any previously learned projection weights are
        discarded.
        """
        self._bid_idx = list(bid_idx)
        self._ask_idx = list(ask_idx)
        self._global_idx = list(global_idx)
        self._build_projections()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x : Tensor of shape (B, L, n_features)

        Returns
        -------
        Tensor of shape (B, L, d_model)
        """
        B, L, F = x.shape

        # Index tensors (on same device, created once and cached by PyTorch JIT)
        bid_idx = torch.tensor(self._bid_idx, device=x.device, dtype=torch.long)
        ask_idx = torch.tensor(self._ask_idx, device=x.device, dtype=torch.long)
        global_idx = torch.tensor(self._global_idx, device=x.device, dtype=torch.long)

        # Split into groups
        x_bid = x.index_select(-1, bid_idx)      # (B, L, n_bid)
        x_ask = x.index_select(-1, ask_idx)       # (B, L, n_ask)
        x_global = x.index_select(-1, global_idx) # (B, L, n_global)

        # Collapse batch and time -> (B*L, n_group)
        x_bid = x_bid.reshape(B * L, -1)
        x_ask = x_ask.reshape(B * L, -1)
        x_global = x_global.reshape(B * L, -1)

        # Project each group to d_model -> (B*L, d_model)
        h_bid = self.proj_bid(x_bid)
        h_ask = self.proj_ask(x_ask)
        h_global = self.proj_global(x_global)

        # Stack as 3 tokens: (B*L, 3, d_model)
        h = torch.stack([h_bid, h_ask, h_global], dim=1)

        # Cross-group attention
        h = self.group_attn(h)  # (B*L, 3, d_model)

        # Concatenate group tokens and merge
        h = h.reshape(B * L, 3 * self.d_model)  # (B*L, 3*d_model)
        out = self.merge(h)                       # (B*L, d_model)

        # Restore batch and time dims
        out = out.reshape(B, L, self.d_model)     # (B, L, d_model)
        return out

"""Attention-weighted pooling modules.

Two shape conventions, controlled by input_is_last_dim:
  - False (default): input (N, d_model, L) — channels-first (Conv output)
  - True:            input (N, L, d_model) — sequence-first (Transformer output)

Learns a 1-D attention score per position via a Linear layer, applies
softmax over the pooled axis, returns the weighted sum.
"""
from __future__ import annotations

from typing import Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F


class AttentionPool1D(nn.Module):
    """Softmax-weighted pooling across one axis of a 3-D tensor."""

    def __init__(self, d_model: int, input_is_last_dim: bool = False) -> None:
        super().__init__()
        self.d_model = d_model
        self.input_is_last_dim = input_is_last_dim
        self.score = nn.Linear(d_model, 1, bias=False)

    def forward(
        self, x: torch.Tensor, return_weights: bool = False
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """Pool one axis of x.

        x shape:
          input_is_last_dim=True  → (N, L, d_model)
          input_is_last_dim=False → (N, d_model, L)
        Returns:
          pooled: (N, d_model)
          (optional) weights: (N, L) — softmax weights along pooled axis
        """
        if self.input_is_last_dim:
            scores = self.score(x).squeeze(-1)                  # (N, L)
            weights = F.softmax(scores, dim=1)                  # (N, L)
            pooled = (x * weights.unsqueeze(-1)).sum(dim=1)     # (N, d)
        else:
            x_t = x.transpose(1, 2)                             # (N, L, d)
            scores = self.score(x_t).squeeze(-1)                # (N, L)
            weights = F.softmax(scores, dim=1)                  # (N, L)
            pooled = (x_t * weights.unsqueeze(-1)).sum(dim=1)   # (N, d)

        if return_weights:
            return pooled, weights
        return pooled

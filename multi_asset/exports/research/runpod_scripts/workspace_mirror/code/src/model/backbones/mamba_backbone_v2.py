"""Mamba-2 backbone V2 — clean, isolated, no extra losses or aux modules.

This is the OPPOSITE of V5-LH: V5-LH combined Mamba with focal + decorr
+ side-aware bid/ask + cross-path fusion all at once and produced
test-time variance collapse (cannot attribute the failure to Mamba alone).

Here Mamba ONLY replaces the conv stack. Everything else in V4 is
identical to baseline_v4. This allows a clean A/B vs ConvLastTSBackbone /
EMAPoolBackbone / GRUBackbone.

Input  : (B, L, d_model)
Output : (B, d_model)

Requires `mamba_ssm` package + CUDA. The import is lazy so this module
is safe to import on CPU-only environments (raises ImportError only when
the class is instantiated).
"""
from __future__ import annotations

import torch
import torch.nn as nn

try:
    from mamba_ssm import Mamba2  # type: ignore[import-not-found]
    _HAS_MAMBA = True
except ImportError:
    _HAS_MAMBA = False
    Mamba2 = None  # type: ignore[assignment]


class MambaBackboneV2(nn.Module):
    def __init__(
        self,
        d_model: int = 32,
        d_state: int = 16,
        expand: int = 1,
        dropout: float = 0.15,
    ) -> None:
        super().__init__()
        if not _HAS_MAMBA:
            raise ImportError(
                "mamba-ssm not installed. Install on pod: "
                "pip install mamba-ssm causal-conv1d"
            )
        # Single Mamba-2 block. headdim=d_model -> single head, minimal params.
        self.mamba = Mamba2(  # type: ignore[misc]
            d_model=d_model,
            d_state=d_state,
            d_conv=4,
            expand=expand,
            headdim=d_model,
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        # h: (B, L, d_model)
        out = self.mamba(h)
        out = self.dropout(out)
        return out[:, -1, :]

"""Late fusion + Mamba per path.

Each path has its own Mamba SSM over time, then late fuse via linear projection.
Theoretical advantage over current 'mamba' (which sees fused 32-dim h):
  - Path A keeps 32-dim trajectory (manual features + projection structure)
  - Path B keeps 16-dim trajectory (raw LOB pooled features)
  - Mamba per path learns path-specific temporal patterns
  - Late linear fuse preserves path differentiation in output
"""
from __future__ import annotations
import torch
import torch.nn as nn
try:
    from mamba_ssm import Mamba
except ImportError:
    Mamba = None


class LateFusionMambaBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 d_state: int = 16, d_conv: int = 4, expand: int = 2, dropout: float = 0.15):
        super().__init__()
        if Mamba is None:
            raise ImportError("mamba-ssm not installed")
        self.mamba_craft = Mamba(d_model=d_craft, d_state=d_state, d_conv=d_conv, expand=expand)
        self.mamba_raw   = Mamba(d_model=d_raw,   d_state=d_state, d_conv=d_conv, expand=expand)
        self.norm_craft = nn.LayerNorm(d_craft)
        self.norm_raw = nn.LayerNorm(d_raw)
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        # Path A: Mamba over time
        ha = h_craft + self.mamba_craft(self.norm_craft(h_craft))  # residual
        # Path B
        hb = h_raw + self.mamba_raw(self.norm_raw(h_raw))
        # Last-timestep slice each path
        ha_last = ha[:, -1, :]  # (B, d_craft)
        hb_last = hb[:, -1, :]  # (B, d_raw)
        return self.fuse(torch.cat([ha_last, hb_last], dim=-1))

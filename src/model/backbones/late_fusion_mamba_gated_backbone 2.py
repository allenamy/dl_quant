"""Late-fusion Mamba per path + SENet channel gating after concat.

Extends LateFusionMamba with a learnable squeeze-excite gate on the
concatenated last-timestep vector. The gate computes per-channel weights
in [0,1] from a global summary, letting the model down-weight uninformative
channels at inference time. SE block is ~2*d/r params (r=4 default).
"""
from __future__ import annotations
import torch
import torch.nn as nn
try:
    from mamba_ssm import Mamba
except ImportError:
    Mamba = None


class SENetGate(nn.Module):
    def __init__(self, d_in: int, reduction: int = 4):
        super().__init__()
        d_red = max(1, d_in // reduction)
        self.fc = nn.Sequential(
            nn.Linear(d_in, d_red),
            nn.ReLU(),
            nn.Linear(d_red, d_in),
            nn.Sigmoid(),
        )

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        return h * self.fc(h)


class LateFusionMambaGatedBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 d_state: int = 16, d_conv: int = 4, expand: int = 2,
                 reduction: int = 4, dropout: float = 0.15):
        super().__init__()
        if Mamba is None:
            raise ImportError("mamba-ssm not installed")
        self.mamba_craft = Mamba(d_model=d_craft, d_state=d_state, d_conv=d_conv, expand=expand)
        self.mamba_raw = Mamba(d_model=d_raw, d_state=d_state, d_conv=d_conv, expand=expand)
        self.norm_craft = nn.LayerNorm(d_craft)
        self.norm_raw = nn.LayerNorm(d_raw)
        d_concat = d_craft + d_raw
        self.gate = SENetGate(d_concat, reduction=reduction)
        self.fuse = nn.Sequential(
            nn.Linear(d_concat, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        ha = h_craft + self.mamba_craft(self.norm_craft(h_craft))
        hb = h_raw + self.mamba_raw(self.norm_raw(h_raw))
        ha_last = ha[:, -1, :]
        hb_last = hb[:, -1, :]
        h_concat = torch.cat([ha_last, hb_last], dim=-1)
        h_gated = self.gate(h_concat)
        return self.fuse(h_gated)

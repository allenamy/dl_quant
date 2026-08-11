"""FiBiNET-style: per-path Mamba + bilinear path-pair interaction.

RecSys 2019 paradigm. After per-path Mamba sequence modeling, the two paths'
last-timestep vectors interact via two mechanisms:
  - Linear concat (current default)
  - Bilinear cross: f_a * W_b · h_b ⊙ W_a · h_a (Hadamard after projection)
The bilinear adds multiplicative path-pair interaction missed by additive
fusion. SE block weights both branches before concat.
"""
from __future__ import annotations
import torch
import torch.nn as nn
try:
    from mamba_ssm import Mamba
except ImportError:
    Mamba = None


class _SE(nn.Module):
    def __init__(self, d: int, reduction: int = 4):
        super().__init__()
        d_red = max(1, d // reduction)
        self.fc = nn.Sequential(
            nn.Linear(d, d_red), nn.ReLU(),
            nn.Linear(d_red, d), nn.Sigmoid(),
        )

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        return h * self.fc(h)


class FibiNetBilinearBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 d_state: int = 16, d_conv: int = 4, expand: int = 2,
                 d_bilinear: int = 16, dropout: float = 0.15):
        super().__init__()
        if Mamba is None:
            raise ImportError("mamba-ssm not installed")
        self.mamba_craft = Mamba(d_model=d_craft, d_state=d_state, d_conv=d_conv, expand=expand)
        self.mamba_raw = Mamba(d_model=d_raw, d_state=d_state, d_conv=d_conv, expand=expand)
        self.norm_c = nn.LayerNorm(d_craft)
        self.norm_r = nn.LayerNorm(d_raw)
        # Bilinear: project to common d_bilinear, Hadamard, residual
        self.proj_c = nn.Linear(d_craft, d_bilinear)
        self.proj_r = nn.Linear(d_raw, d_bilinear)
        # SE re-weights additive concat
        self.se = _SE(d_craft + d_raw, reduction=4)
        # Final fuse: SE-gated concat + bilinear
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw + d_bilinear, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        a = h_craft + self.mamba_craft(self.norm_c(h_craft))
        b = h_raw + self.mamba_raw(self.norm_r(h_raw))
        a_last = a[:, -1, :]
        b_last = b[:, -1, :]
        # Bilinear via Hadamard product after projection
        bilinear = self.proj_c(a_last) * self.proj_r(b_last)  # (B, d_bilinear)
        # Additive: SE-gated concat
        cat = self.se(torch.cat([a_last, b_last], dim=-1))
        return self.fuse(torch.cat([cat, bilinear], dim=-1))

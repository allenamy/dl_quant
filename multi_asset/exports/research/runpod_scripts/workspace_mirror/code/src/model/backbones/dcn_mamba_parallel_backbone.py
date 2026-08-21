"""DCN-V2 cross network on craft path ‖ Mamba on raw sequence — late concat.

Recommender-system paradigm: explicit feature crossing (DCN-V2) for
the structured/handcrafted side, sequence model (Mamba) for the raw LOB
side. Two inductive biases run in parallel and merge late.

DCN-V2 cross: x_l = x_0 ⊙ (W·x_l + b) + x_l. Bounded-degree polynomial
interactions of the input features; ~d² params per layer.
"""
from __future__ import annotations
import torch
import torch.nn as nn
try:
    from mamba_ssm import Mamba
except ImportError:
    Mamba = None


class CrossLayerV2(nn.Module):
    def __init__(self, d: int):
        super().__init__()
        self.proj = nn.Linear(d, d, bias=True)

    def forward(self, x_0: torch.Tensor, x_l: torch.Tensor) -> torch.Tensor:
        return x_0 * self.proj(x_l) + x_l


class DCNV2Cross(nn.Module):
    def __init__(self, d: int, n_layers: int = 3):
        super().__init__()
        self.layers = nn.ModuleList([CrossLayerV2(d) for _ in range(n_layers)])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x_0 = x
        x_l = x
        for layer in self.layers:
            x_l = layer(x_0, x_l)
        return x_l


class DcnMambaParallelBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 d_state: int = 16, d_conv: int = 4, expand: int = 2,
                 n_cross_layers: int = 3, dropout: float = 0.15):
        super().__init__()
        if Mamba is None:
            raise ImportError("mamba-ssm not installed")
        self.mamba_raw = Mamba(d_model=d_raw, d_state=d_state, d_conv=d_conv, expand=expand)
        self.norm_raw = nn.LayerNorm(d_raw)
        self.norm_craft = nn.LayerNorm(d_craft)
        self.cross = DCNV2Cross(d_craft, n_layers=n_cross_layers)
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        # Raw path: Mamba over time, take last
        hr = h_raw + self.mamba_raw(self.norm_raw(h_raw))
        hr_last = hr[:, -1, :]
        # Craft path: collapse to last timestep, then DCN-V2 cross
        hc_last = self.norm_craft(h_craft[:, -1, :])
        hc_crossed = self.cross(hc_last)
        return self.fuse(torch.cat([hc_crossed, hr_last], dim=-1))

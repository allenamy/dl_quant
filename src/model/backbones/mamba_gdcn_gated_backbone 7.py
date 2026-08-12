"""Per-path Mamba (time) ‖ GDCN (feature cross) → SE gate → late fuse.

Each path runs Mamba over the full sequence (last timestep extracted) AND
a GDCN cross network on the last-timestep representation in parallel. The
two outputs are concatenated, SE-gated, and projected back to path width.
Then the two paths are concatenated and fused linearly.

Distinguishing from multi_extract_gated: that one used Mamba+TCN+AttnPool
all temporal extractors. This one pairs Mamba (temporal) with GDCN
(explicit channel cross), testing whether time × cross at the same level
adds signal beyond multiple temporal extractors.
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


class _GDCNCross(nn.Module):
    def __init__(self, d: int, n_layers: int = 2):
        super().__init__()
        self.layers = nn.ModuleList([nn.Linear(d, d, bias=True) for _ in range(n_layers)])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x0 = x
        xl = x
        for layer in self.layers:
            xl = x0 * layer(xl) + xl
        return xl


class _PathHead(nn.Module):
    def __init__(self, d: int, mamba_kwargs: dict, gdcn_layers: int = 2, dropout: float = 0.15):
        super().__init__()
        self.mamba = Mamba(d_model=d, **mamba_kwargs)
        self.norm_m = nn.LayerNorm(d)
        self.gdcn = _GDCNCross(d, n_layers=gdcn_layers)
        self.norm_g = nn.LayerNorm(d)
        self.gate = _SE(d * 2, reduction=4)
        self.proj = nn.Linear(d * 2, d)
        self.drop = nn.Dropout(dropout)

    def forward(self, h: torch.Tensor) -> torch.Tensor:  # (B, L, D)
        # Temporal: Mamba over full seq, take last timestep with residual
        m = h + self.mamba(self.norm_m(h))
        m_last = m[:, -1, :]
        # Channel-cross: GDCN on last timestep with residual
        last = self.norm_g(h[:, -1, :])
        g_out = last + self.gdcn(last)
        # Concat-gate-project
        cat = torch.cat([m_last, g_out], dim=-1)
        return self.drop(self.proj(self.gate(cat)))


class MambaGdcnGatedBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 d_state: int = 16, d_conv: int = 4, expand: int = 2,
                 gdcn_layers: int = 2, dropout: float = 0.15):
        super().__init__()
        if Mamba is None:
            raise ImportError("mamba-ssm not installed")
        mk = dict(d_state=d_state, d_conv=d_conv, expand=expand)
        self.path_craft = _PathHead(d_craft, mk, gdcn_layers, dropout)
        self.path_raw = _PathHead(d_raw, mk, gdcn_layers, dropout)
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        a = self.path_craft(h_craft)
        b = self.path_raw(h_raw)
        return self.fuse(torch.cat([a, b], dim=-1))

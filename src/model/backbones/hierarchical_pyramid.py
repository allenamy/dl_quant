"""HierarchicalConvPyramid backbone — multi-scale conv with INDEPENDENT encoders.

Different from MultiScaleBackbone (shared encoder + multi-aggregation), this
backbone processes h at multiple temporal scales via SEPARATE causal conv
stacks at each tier, each with its own RF.

Architecture:
  Input h: (B, L, d_model) from upstream Path-A+B fusion
   ├── Tier 1 (micro): h directly, conv stack RF=K → last-token
   ├── Tier 2 (meso): avg_pool(stride=meso_stride) → conv stack RF=K → last-token
   └── Tier 3 (macro): avg_pool(stride=macro_stride) → conv stack RF=K → last-token
  Fusion: concat (3*d_model) → Linear → d_model

Effective RF per tier:
  Tier 1: K timesteps (raw)
  Tier 2: K * meso_stride timesteps (real time)
  Tier 3: K * macro_stride timesteps (real time)

For y_600 (input_len=600, horizon=600):
  scales=(1, 5, 10), K=15, dilations=(1,2,4)
  → Tier1 RF=29s, Tier2 RF=145s, Tier3 RF=290s

For y_1800 (input_len=1200, horizon=1800):
  scales=(1, 10, 30), K=15, dilations=(1,2,4)
  → Tier1 RF=29s, Tier2 RF=290s, Tier3 RF=870s

Forward signature matches other backbones in src/model/backbones/:
  forward(h: Tensor[B, L, D]) -> Tensor[B, D]
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class _CausalConvBlock(nn.Module):
    """Single causal dilated conv block: conv → GroupNorm → GELU → residual."""

    def __init__(self, d: int, kernel_size: int, dilation: int, dropout: float):
        super().__init__()
        pad = (kernel_size - 1) * dilation
        self.pad = pad
        self.conv = nn.Conv1d(d, d, kernel_size, padding=0, dilation=dilation)
        self.norm = nn.GroupNorm(num_groups=min(8, d), num_channels=d)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, d, L)
        x_padded = F.pad(x, (self.pad, 0))  # left-pad for causal
        y = self.conv(x_padded)
        y = self.norm(y)
        y = self.act(y)
        y = self.dropout(y)
        return x + y  # residual


class _ConvStack(nn.Module):
    """Stack of causal dilated conv blocks. Returns (B, L, d) features."""

    def __init__(self, d: int, kernel_size: int, dilations: tuple[int, ...], dropout: float):
        super().__init__()
        self.blocks = nn.ModuleList([
            _CausalConvBlock(d, kernel_size, dil, dropout) for dil in dilations
        ])

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        # h: (B, L, d) → transpose for conv1d
        x = h.transpose(1, 2).contiguous()  # (B, d, L)
        for blk in self.blocks:
            x = blk(x)
        return x.transpose(1, 2).contiguous()  # (B, L, d)


class HierarchicalConvPyramid(nn.Module):
    """Three-tier conv pyramid with independent encoders per tier."""

    def __init__(
        self,
        d_model: int,
        scales: tuple[int, int, int] = (1, 5, 10),
        kernel_size: int = 3,
        dilations: tuple[int, ...] = (1, 2, 4),
        dropout: float = 0.15,
    ):
        super().__init__()
        if len(scales) != 3:
            raise ValueError(f"expected 3 scales, got {scales}")
        self.d_model = int(d_model)
        self.scales = tuple(int(s) for s in scales)
        self.kernel_size = int(kernel_size)
        self.dilations = tuple(int(d) for d in dilations)

        # Three independent conv stacks, one per tier
        self.tier_micro = _ConvStack(d_model, kernel_size, dilations, dropout)
        self.tier_meso = _ConvStack(d_model, kernel_size, dilations, dropout)
        self.tier_macro = _ConvStack(d_model, kernel_size, dilations, dropout)

        # Fusion: concat 3*d_model → Linear → d_model
        self.fuse = nn.Linear(3 * d_model, d_model)
        # Init fuse so each tier starts equally weighted
        with torch.no_grad():
            scale = 1.0 / 3.0 ** 0.5
            nn.init.normal_(self.fuse.weight, mean=0.0, std=scale)
            nn.init.zeros_(self.fuse.bias)

        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def _pool_and_encode(self, h: torch.Tensor, stride: int, encoder: _ConvStack) -> torch.Tensor:
        """Pool h with given stride, encode, return last-token features.

        h: (B, L, d_model)
        Returns: (B, d_model)
        """
        if stride == 1:
            h_pooled = h
        else:
            # Avg-pool along time axis with non-overlapping stride
            x = h.transpose(1, 2).contiguous()  # (B, d, L)
            x = F.avg_pool1d(x, kernel_size=stride, stride=stride, ceil_mode=False)
            h_pooled = x.transpose(1, 2).contiguous()  # (B, L//stride, d)
        encoded = encoder(h_pooled)  # (B, L', d)
        return encoded[:, -1, :]  # last-token

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        """h: (B, L, d_model) → (B, d_model)"""
        feat_micro = self._pool_and_encode(h, self.scales[0], self.tier_micro)
        feat_meso = self._pool_and_encode(h, self.scales[1], self.tier_meso)
        feat_macro = self._pool_and_encode(h, self.scales[2], self.tier_macro)
        fused = torch.cat([feat_micro, feat_meso, feat_macro], dim=-1)  # (B, 3*d_model)
        out = self.fuse(self.dropout(fused))  # (B, d_model)
        return out

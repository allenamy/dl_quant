"""Late fusion: Path A and Path B each learn their own temporal dynamics independently,
fused only at the final embedding stage.

vs V4 early fusion: concat(h_craft, h_raw) THEN temporal — temporal sees a fused 32-dim
abstraction, never sees Path A and Path B's distinct sequential patterns.

Late fusion preserves path-specific temporal information until the very end.
"""
from __future__ import annotations
import torch
import torch.nn as nn
from src.model.dual_path_model import CausalConv1dBlock


class LateFusionBackbone(nn.Module):
    """Each path runs through its own temporal model, late fuse with linear projection.

    Args:
        d_craft: Path A (manual features) embedding dim (default 32)
        d_raw: Path B (raw LOB) embedding dim (default 16)
        d_out: Final output dim after fusion (default 32)
        dilations_craft: dilations for Path A's TCN
        dilations_raw: dilations for Path B's TCN
        kernel_size: conv kernel
        dropout: dropout per layer
        pool_kind: 'last' | 'mean' | 'attn'
    """

    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 dilations_craft=(1, 2, 4, 8), dilations_raw=(1, 2, 4, 8),
                 kernel_size: int = 3, dropout: float = 0.15,
                 pool_kind: str = 'last'):
        super().__init__()
        self.tcn_craft = nn.Sequential(*[
            CausalConv1dBlock(d_craft, kernel_size=kernel_size, dilation=d, dropout=dropout)
            for d in dilations_craft
        ])
        self.tcn_raw = nn.Sequential(*[
            CausalConv1dBlock(d_raw, kernel_size=kernel_size, dilation=d, dropout=dropout)
            for d in dilations_raw
        ])
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )
        self.pool_kind = pool_kind
        # Optional attention pool (one query per path)
        if pool_kind == 'attn':
            self.q_craft = nn.Parameter(torch.randn(1, 1, d_craft) * 0.02)
            self.q_raw = nn.Parameter(torch.randn(1, 1, d_raw) * 0.02)

    def _pool(self, x: torch.Tensor, q: torch.Tensor = None) -> torch.Tensor:
        # x: (B, L, d) → (B, d)
        if self.pool_kind == 'last':
            return x[:, -1, :]
        elif self.pool_kind == 'mean':
            return x.mean(dim=1)
        elif self.pool_kind == 'max':
            return x.max(dim=1).values
        elif self.pool_kind == 'attn':
            # scaled dot-product attention with single learned query
            d = x.shape[-1]
            attn = torch.softmax((x * q).sum(-1) / (d ** 0.5), dim=-1)  # (B, L)
            return (x * attn.unsqueeze(-1)).sum(dim=1)
        else:
            return x[:, -1, :]

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        # Independent temporal modeling per path
        ha = self.tcn_craft(h_craft)  # (B, L, d_craft)
        hb = self.tcn_raw(h_raw)      # (B, L, d_raw)
        # Independent pool
        if self.pool_kind == 'attn':
            ha_pooled = self._pool(ha, self.q_craft)
            hb_pooled = self._pool(hb, self.q_raw)
        else:
            ha_pooled = self._pool(ha)
            hb_pooled = self._pool(hb)
        # Late fuse
        return self.fuse(torch.cat([ha_pooled, hb_pooled], dim=-1))

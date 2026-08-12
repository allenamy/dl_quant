"""Multi-extractor parallel branches per path, SE-gated, late concat.

Per path, runs three parallel temporal extractors with different inductive
biases — Mamba (state-space, long-range), TCN (dilated causal conv, local
+ medium-range), and time-axis attention pool (target-anchored). The three
last-timestep outputs are concatenated, gated by a SE block, and projected
back to d. Then the two paths are concatenated and fused linearly.

This realizes the "multiple inductive biases in parallel + gated merge"
paradigm common in modern recommenders (FiBiNET / FinalMLP / DLRM-MultiArm).
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


class _TCNBranch(nn.Module):
    """Causal dilated TCN: stacked Conv1d with right-side padding trimmed."""
    def __init__(self, d: int, dilations=(1, 4, 16), kernel_size: int = 3, dropout: float = 0.15):
        super().__init__()
        self.norm = nn.LayerNorm(d)
        self.convs = nn.ModuleList()
        self.acts = nn.ModuleList()
        self.drops = nn.ModuleList()
        for dil in dilations:
            pad = (kernel_size - 1) * dil
            self.convs.append(nn.Conv1d(d, d, kernel_size, padding=pad, dilation=dil))
            self.acts.append(nn.GELU())
            self.drops.append(nn.Dropout(dropout))

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        x = self.norm(h).transpose(1, 2)  # (B, D, L)
        L = x.size(2)
        for conv, act, drop in zip(self.convs, self.acts, self.drops):
            y = conv(x)[:, :, :L]  # right-trim to enforce causality
            x = x + drop(act(y))
        return x.transpose(1, 2)


class _AttnPoolBranch(nn.Module):
    """Single-query causal attention over time, returns (B, L, D) by broadcast."""
    def __init__(self, d: int, n_heads: int = 2):
        super().__init__()
        self.norm = nn.LayerNorm(d)
        # Ensure n_heads divides d
        if d % n_heads != 0:
            n_heads = max(1, d // 8)
            while d % n_heads != 0 and n_heads > 1:
                n_heads -= 1
        self.attn = nn.MultiheadAttention(d, n_heads, batch_first=True)
        self.q = nn.Parameter(torch.randn(1, 1, d) * 0.01)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        B, L, D = h.shape
        x = self.norm(h)
        q = self.q.expand(B, 1, D)
        out, _ = self.attn(q, x, x, need_weights=False)
        return out.expand(-1, L, -1)


class _MultiExtractPath(nn.Module):
    def __init__(self, d: int, mamba_kwargs: dict, dropout: float = 0.15):
        super().__init__()
        self.mamba = Mamba(d_model=d, **mamba_kwargs)
        self.mamba_norm = nn.LayerNorm(d)
        self.tcn = _TCNBranch(d, dropout=dropout)
        self.attn = _AttnPoolBranch(d)
        self.gate = _SE(d * 3, reduction=4)
        self.proj = nn.Linear(d * 3, d)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        h_m = h + self.mamba(self.mamba_norm(h))
        h_t = h + self.tcn(h)
        h_a = h + self.attn(h)
        m_last = h_m[:, -1, :]
        t_last = h_t[:, -1, :]
        a_last = h_a[:, -1, :]
        cat = torch.cat([m_last, t_last, a_last], dim=-1)
        return self.proj(self.gate(cat))


class MultiExtractGatedBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 d_state: int = 16, d_conv: int = 4, expand: int = 2, dropout: float = 0.15):
        super().__init__()
        if Mamba is None:
            raise ImportError("mamba-ssm not installed")
        mk = dict(d_state=d_state, d_conv=d_conv, expand=expand)
        self.path_craft = _MultiExtractPath(d_craft, mk, dropout=dropout)
        self.path_raw = _MultiExtractPath(d_raw, mk, dropout=dropout)
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        a = self.path_craft(h_craft)
        b = self.path_raw(h_raw)
        return self.fuse(torch.cat([a, b], dim=-1))

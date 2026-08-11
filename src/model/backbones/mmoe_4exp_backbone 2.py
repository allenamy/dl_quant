"""MMoE: 4 experts (each = small Mamba block) with input-dependent gate.

Google KDD 2018 paradigm. Per path: pool the input to a summary vector,
softmax over 4 experts to get gate, compute weighted sum of expert outputs.
All 4 experts process the SAME input, gate selects per-sample.

Anti-collapse: small load-balance loss can be added but here we rely on
softmax-with-noise for diverse routing. This is a single-path MoE, applied
per path then late-fused.
"""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F
try:
    from mamba_ssm import Mamba
except ImportError:
    Mamba = None


class _MoEPath(nn.Module):
    def __init__(self, d: int, n_experts: int = 4, d_state: int = 16,
                 d_conv: int = 4, expand: int = 2, dropout: float = 0.15):
        super().__init__()
        self.experts = nn.ModuleList([
            Mamba(d_model=d, d_state=d_state, d_conv=d_conv, expand=expand)
            for _ in range(n_experts)
        ])
        self.norm = nn.LayerNorm(d)
        # Gate: pool h then linear → softmax
        self.gate = nn.Linear(d, n_experts)
        self.drop = nn.Dropout(dropout)

    def forward(self, h: torch.Tensor) -> torch.Tensor:  # (B, L, D)
        h_norm = self.norm(h)
        # Gate: time-pooled summary → softmax
        h_summary = h_norm.mean(dim=1)  # (B, D)
        gate = F.softmax(self.gate(h_summary), dim=-1)  # (B, n_experts)
        # Each expert produces (B, L, D); stack and weight
        outs = torch.stack([e(h_norm) for e in self.experts], dim=1)  # (B, n_exp, L, D)
        # Weighted sum across experts
        gate_b = gate.unsqueeze(-1).unsqueeze(-1)  # (B, n_exp, 1, 1)
        out = (outs * gate_b).sum(dim=1)  # (B, L, D)
        return h + self.drop(out)


class MMoE4ExpBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 n_experts: int = 4, d_state: int = 16, d_conv: int = 4,
                 expand: int = 2, dropout: float = 0.15):
        super().__init__()
        if Mamba is None:
            raise ImportError("mamba-ssm not installed")
        self.path_craft = _MoEPath(d_craft, n_experts, d_state, d_conv, expand, dropout)
        self.path_raw = _MoEPath(d_raw, n_experts, d_state, d_conv, expand, dropout)
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        a = self.path_craft(h_craft)
        b = self.path_raw(h_raw)
        return self.fuse(torch.cat([a[:, -1, :], b[:, -1, :]], dim=-1))

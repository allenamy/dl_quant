"""Frequency-domain block: FFT → MLP on real/imag → iFFT (residual).

FreTS-style (NeurIPS 2023) — captures periodicity that time-domain models
must implicitly learn. Per path: rfft along the time axis, separate MLPs on
real and imaginary parts, irfft back. Multi-block stack with residuals.

For BTC perp 600s window: hopes to capture microstructure cycles
(quote-update periodicities, batch-trading cycles) directly via spectrum.
"""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F


class _FFTBlock(nn.Module):
    def __init__(self, d: int, d_hidden: int = 64, dropout: float = 0.15):
        super().__init__()
        self.norm = nn.LayerNorm(d)
        self.real_mlp = nn.Sequential(nn.Linear(d, d_hidden), nn.GELU(), nn.Linear(d_hidden, d))
        self.imag_mlp = nn.Sequential(nn.Linear(d, d_hidden), nn.GELU(), nn.Linear(d_hidden, d))
        self.drop = nn.Dropout(dropout)

    def forward(self, h: torch.Tensor) -> torch.Tensor:  # (B, L, D)
        x = self.norm(h)
        L = x.size(1)
        z = torch.fft.rfft(x, dim=1, norm="ortho")  # (B, L//2+1, D), complex
        r = self.real_mlp(z.real)
        i = self.imag_mlp(z.imag)
        z2 = torch.complex(r, i)
        out = torch.fft.irfft(z2, n=L, dim=1, norm="ortho")
        return h + self.drop(out)


class FftFreqBlockBackbone(nn.Module):
    def __init__(self, d_craft: int = 32, d_raw: int = 16, d_out: int = 32,
                 n_blocks: int = 2, d_hidden: int = 64, dropout: float = 0.15):
        super().__init__()
        self.blocks_craft = nn.ModuleList([_FFTBlock(d_craft, d_hidden, dropout) for _ in range(n_blocks)])
        self.blocks_raw = nn.ModuleList([_FFTBlock(d_raw, d_hidden, dropout) for _ in range(n_blocks)])
        self.fuse = nn.Sequential(
            nn.Linear(d_craft + d_raw, d_out),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, h_craft: torch.Tensor, h_raw: torch.Tensor) -> torch.Tensor:
        a = h_craft
        for blk in self.blocks_craft:
            a = blk(a)
        b = h_raw
        for blk in self.blocks_raw:
            b = blk(b)
        return self.fuse(torch.cat([a[:, -1, :], b[:, -1, :]], dim=-1))

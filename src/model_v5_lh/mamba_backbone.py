"""Mamba-2 temporal backbone for V5-LH.

On POD (CUDA + mamba-ssm installed), uses official Mamba-2 blocks.
On LOCAL (CPU), falls back to a unidirectional GRU that preserves:
  - Same (B, L, d_model) interface
  - Causal / autoregressive property (past outputs not affected by future inputs)

The fallback is NOT a numerical proxy — it only exists for unit-testing wiring
and verifying the shape/grad interface. All training happens on POD with
use_fallback=False.

Reference: Mamba-2 (Dao & Gu 2024), arxiv 2405.21060.
"""
import torch
import torch.nn as nn


class _FallbackBlock(nn.Module):
    """GRU-based causal stub used when mamba-ssm is unavailable (CPU)."""

    def __init__(self, d_model: int):
        super().__init__()
        self.gru = nn.GRU(d_model, d_model, num_layers=1, batch_first=True)
        self.ln = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.gru(x)
        return self.ln(x + out)


class _RealMambaBlock(nn.Module):
    """Real Mamba-2 block (imports mamba-ssm, requires CUDA)."""

    def __init__(self, d_model: int, d_state: int, expand: int):
        super().__init__()
        from mamba_ssm import Mamba2
        self.block = Mamba2(
            d_model=d_model,
            d_state=d_state,
            expand=expand,
            headdim=max(1, d_model // 4),
        )
        self.ln = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.ln(x + self.block(x))


class MambaBackbone(nn.Module):
    def __init__(
        self,
        d_model: int = 32,
        n_layers: int = 2,
        d_state: int = 16,
        expand: int = 1,
        use_fallback: bool = False,
    ):
        super().__init__()
        self.use_fallback = use_fallback
        if use_fallback:
            self.layers = nn.ModuleList([_FallbackBlock(d_model) for _ in range(n_layers)])
        else:
            self.layers = nn.ModuleList([
                _RealMambaBlock(d_model, d_state, expand) for _ in range(n_layers)
            ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for lyr in self.layers:
            x = lyr(x)
        return x

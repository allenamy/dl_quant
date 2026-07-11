"""Engine A — BACKBONE-AGNOSTIC factor-mining harness (USER direction 2026-07-11).

The whole program (wide dataset, residual targets, K-head/orthogonality, persistence penalty,
σ/kill gates, factory acceptance) sits behind ONE clean interface where the ENCODER is pluggable.
A fresh paradigm sweep's top-5 become swap-in arms; every arm runs the SAME gates = fair race,
one leaderboard (incremental orthogonal IC over [funding+zoo] + persistence + execution economics).

  ┌─ PanelEncoder (PLUGGABLE) ──────────────────────────────┐
  │  forward(x:(B,N,W,C), mask:(B,N)) -> h:(B,N,d)           │   <- swap this only
  └─────────────────────────────────────────────────────────┘
  WideFactorModel (FIXED harness): encoder -> [opt cross-asset attn, M3] -> K factor heads (B,N,K)
  losses/gates/acceptance live in the trainer, encoder-agnostic.

Arm #1 = ConformerPanelEncoder (the known-good REG_arch stem). Planned swap-ins: SSM/Mamba,
conditional-autoencoder (GKX — N=110 is its native scale), graph/relational, KAN, attn-pool.
"""
from __future__ import annotations
import torch
import torch.nn as nn
from multi_asset.model.temporal_spatial_panel import SharedTemporalEncoder, CrossAssetAttnLayer


class PanelEncoder(nn.Module):
    """PLUGGABLE BACKBONE contract. Input: per-coin panel window x (B,N,W,C) + validity mask
    (B,N). Output: per-coin embedding h (B,N,d_out). Must be causal over W (<=t) and treat coins
    independently OR mix them internally (graph arms) — but the harness's cross-asset layer is the
    default place for spatial mixing, so a pure-temporal encoder is the simplest valid arm."""
    d_out: int

    def forward(self, x, mask):
        raise NotImplementedError


class ConformerPanelEncoder(PanelEncoder):
    """Arm #1 (reference): weight-shared causal Conformer temporal stem, per coin, last-token pool.
    Wraps the audited SharedTemporalEncoder — the known-good baseline the race is measured against."""
    def __init__(self, n_feat, d=64, n_blocks=2, kernel_size=15, dropout=0.2):
        super().__init__()
        self.enc = SharedTemporalEncoder(n_feat, d, n_blocks=n_blocks, n_heads=2,
                                         kernel_size=kernel_size, dropout=dropout)
        self.d_out = d

    def forward(self, x, mask):
        B, N, W, C = x.shape
        h = self.enc(x.reshape(B * N, W, C))        # (B*N, d) per-coin temporal embedding
        return h.reshape(B, N, self.d_out)


class WideFactorModel(nn.Module):
    """FIXED harness. encoder (pluggable) -> [optional cross-asset attention over members] ->
    K orthogonal factor heads. Output factor scores (B,N,K); the trainer applies the residual
    LambdaRankIC + orthogonality + pred-smooth losses + σ/kill gates (all encoder-agnostic)."""
    def __init__(self, encoder: PanelEncoder, n_factor_heads=6, xattn=False, n_xattn=1, dropout=0.2):
        super().__init__()
        self.encoder = encoder
        d = encoder.d_out
        self.xattn = xattn
        if xattn:                                    # M3: cross-asset attention (masked, member-only)
            self.attn = nn.ModuleList([CrossAssetAttnLayer(d, nhead=4, dropout=dropout)
                                       for _ in range(n_xattn)])
        self.factor_heads = nn.ModuleList([
            nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Dropout(dropout), nn.Linear(d, 1))
            for _ in range(n_factor_heads)])

    def forward(self, x, mask):
        h = self.encoder(x, mask)                    # (B,N,d)
        if self.xattn:
            key_pad = mask < 0.5                      # (B,N) True where invalid -> masked in attn
            for layer in self.attn:
                h = layer(h, key_pad)
        scores = torch.cat([head(h) for head in self.factor_heads], dim=-1)   # (B,N,K)
        return {"factor_scores": scores}


if __name__ == "__main__":   # smoke: arm #1 forward-passes to (B,N,K)
    B, N, W, C, K = 4, 140, 168, 32, 6
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = WideFactorModel(ConformerPanelEncoder(C, d=64), n_factor_heads=K, xattn=True).to(dev)
    x = torch.randn(B, N, W, C, device=dev); mask = (torch.rand(B, N, device=dev) > 0.2).float()
    out = m(x, mask)
    print(f"[harness] params={sum(p.numel() for p in m.parameters()):,} | "
          f"scores {tuple(out['factor_scores'].shape)} (expect ({B},{N},{K}))")

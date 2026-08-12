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
    def __init__(self, encoder: PanelEncoder, n_factor_heads=6, xattn=False, n_xattn=1, dropout=0.2,
                 aux_horizons=()):
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
        # aux-MTL: lightweight per-horizon heads on the shared trunk (regularise the encoder with
        # 1h/24h residual supervision; scored only for training, not shipped as candidate factors).
        self.aux_horizons = tuple(aux_horizons)
        if self.aux_horizons:
            self.aux_heads = nn.ModuleDict({str(int(h)): nn.Linear(d, 1) for h in self.aux_horizons})

    def forward(self, x, mask):
        h = self.encoder(x, mask)                    # (B,N,d)
        if self.xattn:
            key_pad = mask < 0.5                      # (B,N) True where invalid -> masked in attn
            for layer in self.attn:
                h = layer(h, key_pad)
        scores = torch.cat([head(h) for head in self.factor_heads], dim=-1)   # (B,N,K)
        out = {"factor_scores": scores}
        if self.aux_horizons:
            out["aux_scores"] = {int(k): self.aux_heads[k](h).squeeze(-1) for k in self.aux_heads}
        return out


class QIMHead(nn.Module):
    """ARM-QIM head (Barunik, A-grade): a monotone quantile function per coin, traded via its
    IMPLIED MEAN (trapezoidal integral of Q(tau) over tau) instead of q50 — a fat-tail-robust
    central estimate. Monotone by cumulative-softplus increments. Returns quantiles (B,N,Q) and
    factor_scores (B,N,2) = [implied_mean, q50], so the K-head export/scoring machinery compares
    the implied mean vs the point head directly (the pre-registered QIM test)."""
    def __init__(self, d, n_quantiles=25, dropout=0.2):
        super().__init__()
        assert n_quantiles % 2 == 1, "use an odd Q so tau=0.5 (q50) is on the grid"
        self.Q = n_quantiles
        self.mid = n_quantiles // 2
        taus = torch.linspace(0.02, 0.98, n_quantiles)          # symmetric grid, tau[mid]=0.5
        # trapezoidal weights for mean ~ integral_[a,b] Q(tau) dtau / (b-a): interior 1, ends 1/2.
        w = torch.ones(n_quantiles); w[0] = w[-1] = 0.5; w = w / w.sum()
        self.register_buffer("taus", taus)
        self.register_buffer("mean_w", w)
        self.base = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Dropout(dropout))
        self.q0 = nn.Linear(d, 1)                               # lowest quantile level
        self.dq = nn.Linear(d, n_quantiles - 1)                # positive increments -> monotone

    def forward(self, h):
        z = self.base(h)
        q0 = self.q0(z)                                        # (B,N,1)
        inc = torch.nn.functional.softplus(self.dq(z))         # (B,N,Q-1) >= 0
        q = torch.cat([q0, q0 + torch.cumsum(inc, dim=-1)], dim=-1)   # (B,N,Q) monotone
        imean = (q * self.mean_w).sum(-1, keepdim=True)        # (B,N,1) quantile-implied mean
        q50 = q[..., self.mid:self.mid + 1]                    # (B,N,1) median
        scores = torch.cat([imean, q50], dim=-1)               # (B,N,2)
        return {"quantiles": q, "factor_scores": scores}


class WideQIMModel(nn.Module):
    """ARM-QIM harness: pluggable encoder -> [optional cross-asset attn] -> QIMHead. Same encoder
    contract + xattn slot as WideFactorModel; only the head differs (quantile distribution vs K
    scalar factor scores). Trained with multi-quantile pinball on the residual target."""
    def __init__(self, encoder: PanelEncoder, n_quantiles=25, xattn=False, n_xattn=1, dropout=0.2):
        super().__init__()
        self.encoder = encoder
        d = encoder.d_out
        self.xattn = xattn
        if xattn:
            self.attn = nn.ModuleList([CrossAssetAttnLayer(d, nhead=4, dropout=dropout)
                                       for _ in range(n_xattn)])
        self.head = QIMHead(d, n_quantiles=n_quantiles, dropout=dropout)

    def forward(self, x, mask):
        h = self.encoder(x, mask)
        if self.xattn:
            key_pad = mask < 0.5
            for layer in self.attn:
                h = layer(h, key_pad)
        return self.head(h)


if __name__ == "__main__":   # smoke: arm #1 forward-passes to (B,N,K)
    B, N, W, C, K = 4, 140, 168, 32, 6
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = WideFactorModel(ConformerPanelEncoder(C, d=64), n_factor_heads=K, xattn=True).to(dev)
    x = torch.randn(B, N, W, C, device=dev); mask = (torch.rand(B, N, device=dev) > 0.2).float()
    out = m(x, mask)
    print(f"[harness] params={sum(p.numel() for p in m.parameters()):,} | "
          f"scores {tuple(out['factor_scores'].shape)} (expect ({B},{N},{K}))")


# =========================================================================== #
# ARM-N1b: Multi-relational cross-asset attention (2026-07-15).
# King single-xattn path (base) + gated multi-relation delta. Relation edges =
# rolling-correlation buckets at K lookbacks (co-movement structure, causal <=t).
# ZERO-INIT gates: alpha (overall) + lambda_k (edge biases) start at 0, so at
# init h_out == base(h) == the king single-xattn (byte-identical start = built-in
# ablation). Shared Q/K/V/out across edges (edges differ only by the corr bias) ->
# ~17k incremental params. Wired via WideMultiRelModel (opt-in --multirel).
# =========================================================================== #
import math as _math


class MultiRelXAttn(nn.Module):
    def __init__(self, d, nhead=4, lookbacks=(24, 72, 168), ret_idx=20, dropout=0.2):
        super().__init__()
        self.base = CrossAssetAttnLayer(d, nhead=nhead, dropout=dropout)   # king path
        self.norm = nn.LayerNorm(d)
        self.Wq = nn.Linear(d, d, bias=False)
        self.Wk = nn.Linear(d, d, bias=False)
        self.Wv = nn.Linear(d, d, bias=False)
        self.Wout = nn.Linear(d, d)
        self.lam = nn.Parameter(torch.zeros(len(lookbacks)))    # lambda_k ZERO-INIT
        self.gate = nn.Linear(d, len(lookbacks))                # input-dependent edge mix
        self.alpha = nn.Parameter(torch.zeros(1))               # overall gate ZERO-INIT
        self.drop = nn.Dropout(dropout)
        self.lookbacks = tuple(lookbacks); self.ret_idx = int(ret_idx); self.d = d

    @staticmethod
    def _corr(r, key_pad):
        # r (B,N,L) -> masked pairwise Pearson corr (B,N,N) in [-1,1]
        rc = r - r.mean(-1, keepdim=True)
        rn = rc / rc.norm(dim=-1, keepdim=True).clamp_min(1e-6)
        C = torch.bmm(rn, rn.transpose(1, 2))
        return C.masked_fill(key_pad.unsqueeze(1), 0.0)         # invalid cols -> 0 bias

    def forward(self, h, x, key_pad):
        # h (B,N,d); x (B,N,W,C); key_pad (B,N) True=invalid
        h_base = self.base(h, key_pad)
        hn = self.norm(h)
        q, k, v = self.Wq(hn), self.Wk(hn), self.Wv(hn)
        ret = x[:, :, :, self.ret_idx]                          # (B,N,W) standardized 1h-ret window
        scale = 1.0 / _math.sqrt(self.d)
        deltas = []
        for e, L in enumerate(self.lookbacks):
            Bk = self._corr(ret[:, :, -L:], key_pad)            # (B,N,N)
            logits = torch.bmm(q, k.transpose(1, 2)) * scale + self.lam[e] * Bk
            logits = logits.masked_fill(key_pad.unsqueeze(1), float("-inf"))
            a = torch.softmax(logits, dim=-1)
            a = torch.nan_to_num(a, nan=0.0)                    # all-invalid query rows -> 0
            deltas.append(torch.bmm(a, v))                      # (B,N,d)
        valid = (~key_pad).float().unsqueeze(-1)                # (B,N,1)
        pooled = (hn * valid).sum(1) / valid.sum(1).clamp_min(1.0)   # (B,d)
        g = torch.softmax(self.gate(pooled), dim=-1)            # (B,K)
        mix = sum(g[:, e].view(-1, 1, 1) * deltas[e] for e in range(len(self.lookbacks)))
        delta = torch.nan_to_num(self.Wout(self.drop(mix)), nan=0.0)
        return h_base + self.alpha * delta


class WideMultiRelModel(nn.Module):
    """ARM-N1b: same contract as WideFactorModel (encoder -> cross-asset -> K factor heads,
    output factor_scores (B,N,K)) but the single xattn is replaced by MultiRelXAttn (king base
    path + zero-init gated multi-relation delta). ret_idx = index of the 1h-return channel used
    for the rolling-correlation relation biases."""
    def __init__(self, encoder: PanelEncoder, n_factor_heads=6, lookbacks=(24, 72, 168),
                 ret_idx=20, dropout=0.2):
        super().__init__()
        self.encoder = encoder
        d = encoder.d_out
        self.multirel = MultiRelXAttn(d, nhead=4, lookbacks=lookbacks, ret_idx=ret_idx, dropout=dropout)
        self.factor_heads = nn.ModuleList([
            nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Dropout(dropout), nn.Linear(d, 1))
            for _ in range(n_factor_heads)])

    def forward(self, x, mask):
        h = self.encoder(x, mask)                    # (B,N,d)
        key_pad = mask < 0.5                          # (B,N) True where invalid
        h = self.multirel(h, x, key_pad)
        scores = torch.cat([head(h) for head in self.factor_heads], dim=-1)   # (B,N,K)
        return {"factor_scores": scores}


class FusionTwoTowerEncoder(PanelEncoder):
    """ARM-F2T: gated two-tower family fusion (DESIGN_metrics_v2 附录 2026-08-07; E10 治疗①).
    Flat concat of heterogeneous families measured to HURT (53ch vs 32ch: −0.0135, 3 seeds,
    every fold) — the slow positioning descriptors dilute the shared input_proj geometry.
    Split by family: cols [:split] = price/volume zoo -> tower A (the audited conformer stem,
    capacity-identical to the 32ch control arm); cols [split:] = slow metrics (AR1≈1, no deep
    temporal capacity needed) -> tower B (causal depthwise conv, last token). Fusion is a
    per-coin scalar gate on an additive delta with ZERO-INIT alpha: at init h == tower A alone
    (structural twin of the control = built-in ablation); the gate must EARN the metrics
    contribution, and can learn to shut tower B off where the family is absent (pre-2023-06)."""
    def __init__(self, n_feat, split=32, d=64, n_blocks=2, kernel_size=15, dropout=0.2,
                 b_kernel=24, b_width=32):
        super().__init__()
        assert 0 < split < n_feat, f"fusion split {split} outside (0, {n_feat})"
        self.split = int(split)
        self.tower_a = SharedTemporalEncoder(self.split, d, n_blocks=n_blocks, n_heads=2,
                                             kernel_size=kernel_size, dropout=dropout)
        self.b_proj = nn.Linear(n_feat - self.split, b_width)
        self.b_conv = nn.Conv1d(b_width, b_width, b_kernel, groups=b_width)  # depthwise
        self.b_out = nn.Linear(b_width, d)
        self.b_kernel = int(b_kernel)
        self.gate = nn.Sequential(nn.Linear(2 * d, 32), nn.GELU(), nn.Linear(32, 1))
        self.alpha = nn.Parameter(torch.zeros(1))               # ZERO-INIT: earn the delta
        self.drop = nn.Dropout(dropout)
        self.d_out = d

    def forward(self, x, mask):
        B, N, W, C = x.shape
        ha = self.tower_a(x[..., :self.split].reshape(B * N, W, self.split))  # (B*N, d)
        xb = self.b_proj(x[..., self.split:])                   # (B,N,W,bw)
        xb = xb.reshape(B * N, W, -1).transpose(1, 2)           # (B*N,bw,W)
        xb = torch.nn.functional.pad(xb, (self.b_kernel - 1, 0))  # causal left-pad
        hb = torch.nn.functional.gelu(self.b_conv(xb))[..., -1]  # last token (B*N,bw)
        hb = self.b_out(self.drop(hb))                          # (B*N,d)
        g = torch.sigmoid(self.gate(torch.cat([ha, hb], dim=-1)))  # (B*N,1)
        h = ha + self.alpha * g * hb
        return h.reshape(B, N, self.d_out)

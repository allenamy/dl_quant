"""Cross-asset attention panel model for crypto y_600 prediction.

The GENUINE multi-asset lever: at each timestamp the 14 asset embeddings are
tokens, and a small Transformer-style MultiheadAttention layer lets each asset
attend to ALL others (a learnable per-asset id embedding makes the tokens
identifiable). This is the structure that the per-asset Ridge / single-asset DL
*cannot* express — the whole point of going multi-asset.

Pipeline per forward:
    X  (B, S, F)   per-window features for S assets at B timestamps
    mask (B, S)    1 where asset is present/valid at that timestamp
    ->  per-asset shared MLP encoder  F -> d
    ->  + learnable asset-id embedding (S, d)
    ->  [Phase 1] optional market/common-factor token appended as slot S+1
    ->  1-2 cross-asset MultiheadAttention layers (over the S(+1)-asset axis),
        masked so padded assets neither attend nor are attended to
    ->  [Phase 2] optional in-graph factor/residual split (shared beta_proj on
        the attended market token + per-asset residual head)
    ->  per-asset head  d -> n_out  (n_out=1 normalized q50, or 3 quantiles)
    output (B, S, n_out)  (squeezed to (B, S) when n_out==1)

Small by design (low-SNR rule): d=64, 2 attn layers, nhead=4 -> ~75-90K params.
Shared encoder + shared head weights across assets; only the asset-id embedding
and attention are cross-asset. No time dimension here — the per-window feature
cache already collapses the sequence into 44 causal features, so this trains
directly on the panel (efficient, no heavy sequence pipeline).

Design phases (flag-gated so the baseline graph is recoverable):
  Phase 0 (baseline)  use_market_token=False, use_factor_split=False
  Phase 1 (+market)   use_market_token=True   — symmetric market token, S+1 slot
  Phase 2 (+factor)   use_factor_split=True   — needs market token; factor+resid
"""
from __future__ import annotations

import torch
import torch.nn as nn


class AssetEncoder(nn.Module):
    """Shared per-asset MLP: F -> d, GELU, LayerNorm. Same weights all assets."""

    def __init__(self, n_feat: int, d: int, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_feat, d),
            nn.GELU(),
            nn.LayerNorm(d),
            nn.Dropout(dropout),
            nn.Linear(d, d),
            nn.GELU(),
            nn.LayerNorm(d),
        )

    def forward(self, x):  # (B, S, F) -> (B, S, d)
        return self.net(x)


class CrossAssetAttnLayer(nn.Module):
    """One pre-norm MultiheadAttention block over the asset (S) axis + FFN.

    key_padding_mask drops padded assets from the attention (they don't get
    attended to). We zero their residual contribution on the way out too.
    """

    def __init__(self, d: int, nhead: int = 4, dropout: float = 0.2):
        super().__init__()
        self.norm1 = nn.LayerNorm(d)
        self.attn = nn.MultiheadAttention(d, nhead, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(d)
        self.ffn = nn.Sequential(
            nn.Linear(d, 2 * d),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(2 * d, d),
        )
        self.drop = nn.Dropout(dropout)

    def forward(self, x, key_padding_mask):
        # x: (B, S, d); key_padding_mask: (B, S) bool, True = PAD (ignored).
        h = self.norm1(x)
        a, _ = self.attn(h, h, h, key_padding_mask=key_padding_mask, need_weights=False)
        x = x + self.drop(a)
        x = x + self.drop(self.ffn(self.norm2(x)))
        return x


class MarketMLP(nn.Module):
    """Phase 1 — common-factor token builder.

    Input is the concat of two SYMMETRIC pooled summaries of the per-asset
    encodings at the SAME timestamp:
        m_mean : masked mean of h over the valid assets (equal weight)
        m_cap  : masked weighted mean with TRAIN-FIXED dollar-volume cap weights
    MLP: 2d -> d -> d. ~ d*(2d) + d*d ≈ 3*d^2 params (≈ 12K at d=64).
    """

    def __init__(self, d: int, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2 * d, d),
            nn.GELU(),
            nn.LayerNorm(d),
            nn.Dropout(dropout),
            nn.Linear(d, d),
        )

    def forward(self, m_mean, m_cap):  # each (B, d) -> (B, d)
        return self.net(torch.cat([m_mean, m_cap], dim=-1))


class ResidualHead(nn.Module):
    """Phase 2 — per-asset idiosyncratic residual head: LN(d) -> d -> 1.

    Spends capacity only on the thin cross-sectional alpha left after the
    common factor is removed (the factor is supplied separately by beta_proj).
    """

    def __init__(self, d: int, dropout: float = 0.2):
        super().__init__()
        self.norm = nn.LayerNorm(d)
        self.net = nn.Sequential(
            nn.Linear(d, d),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d, 1),
        )

    def forward(self, h):  # (B, S, d) -> (B, S)
        return self.net(self.norm(h)).squeeze(-1)


def _masked_mean(h, mask):
    """h: (B, S, d); mask: (B, S) {0,1} float. Masked mean over S -> (B, d)."""
    w = mask.unsqueeze(-1)                                   # (B, S, 1)
    denom = w.sum(dim=1).clamp(min=1.0)                      # (B, 1)
    return (h * w).sum(dim=1) / denom                        # (B, d)


def _masked_weighted_mean(h, mask, cap_w):
    """h: (B, S, d); mask: (B, S) float; cap_w: (S,) >=0 train-fixed weights.
    Weighted mean over the VALID assets, weights renormalized per row to the
    present assets (a restriction of the fixed vector — no test recompute)."""
    w = (mask * cap_w.unsqueeze(0)).unsqueeze(-1)            # (B, S, 1)
    denom = w.sum(dim=1).clamp(min=1e-6)                     # (B, 1)
    return (h * w).sum(dim=1) / denom                        # (B, d)


class CrossAssetPanelModel(nn.Module):
    """Shared encoder + asset-id embedding + cross-asset attention + shared head.

    Phase flags (default = baseline so the original graph is bit-for-bit
    recoverable when both are False):
        use_market_token : append a symmetric market/common-factor token (S+1)
        use_factor_split : y_hat = beta_proj(market_ctx) + residual_head(assets)
                           (requires use_market_token=True)
    """

    def __init__(
        self,
        n_feat: int,
        n_assets: int,
        d: int = 48,
        nhead: int = 4,
        n_layers: int = 2,
        n_out: int = 1,
        dropout: float = 0.2,
        use_market_token: bool = False,
        use_factor_split: bool = False,
        cap_weights=None,
    ):
        super().__init__()
        if use_factor_split and not use_market_token:
            raise ValueError("use_factor_split requires use_market_token=True "
                             "(the factor is read off the market token)")
        self.n_assets = n_assets
        self.n_out = n_out
        self.use_market_token = use_market_token
        self.use_factor_split = use_factor_split
        self.encoder = AssetEncoder(n_feat, d, dropout)
        # learnable per-asset id embedding (makes the S tokens identifiable)
        self.asset_id = nn.Parameter(torch.zeros(n_assets, d))
        nn.init.normal_(self.asset_id, std=0.02)
        self.layers = nn.ModuleList(
            [CrossAssetAttnLayer(d, nhead, dropout) for _ in range(n_layers)]
        )

        # Phase 1: market/common-factor token.
        if use_market_token:
            self.market_mlp = MarketMLP(d, dropout)
            # learnable id for the market slot (kept distinct from asset ids)
            self.market_id = nn.Parameter(torch.zeros(d))
            nn.init.normal_(self.market_id, std=0.02)
            # TRAIN-FIXED cap weights (buffer, not a Parameter — never learned,
            # never recomputed on test). Default to ones (equal -> m_cap==m_mean)
            # if not supplied, so the token still works without dollar-vol.
            if cap_weights is None:
                cap_weights = torch.ones(n_assets)
            cap_weights = torch.as_tensor(cap_weights, dtype=torch.float32)
            # normalize so the weighted mean is a proper average over all assets
            cap_weights = cap_weights / cap_weights.sum().clamp(min=1e-6) * n_assets
            self.register_buffer("cap_weights", cap_weights)

        # Phase 2: in-graph factor/residual split.
        if use_factor_split:
            # SHARED low-rank linear map d->1 (NOT a per-asset free Parameter —
            # avoids the val->test drift seen with learnable per-asset betas).
            self.beta_proj = nn.Linear(d, 1)
            self.resid_head = ResidualHead(d, dropout)
        else:
            # baseline / Phase-1-only head: shared linear over per-asset tokens
            self.head_norm = nn.LayerNorm(d)
            self.head = nn.Linear(d, n_out)

    def forward(self, x, mask):
        """x: (B, S, F) float; mask: (B, S) {0,1}. Returns (B, S) or (B, S, n_out).

        Padded assets (mask==0) are zeroed at input, excluded from attention via
        key_padding_mask, and their outputs are not used by the (masked) loss.
        """
        B, S, _ = x.shape
        x = torch.nan_to_num(x, nan=0.0)
        x = x * mask.unsqueeze(-1)              # zero padded assets at input
        h = self.encoder(x)                      # (B, S, d)
        h = h + self.asset_id.unsqueeze(0)       # broadcast asset-id over batch

        key_pad = mask < 0.5                     # (B, S) True = PAD
        # A timestamp with zero valid assets would make MHA produce NaN (all
        # keys masked). Such rows are masked out of the loss anyway; feed an
        # all-False pad row to keep MHA finite, the head output is unused.
        all_pad = key_pad.all(dim=1, keepdim=True)
        key_pad = key_pad & ~all_pad

        if self.use_market_token:
            # Phase 1: build a SYMMETRIC common-factor token from the SAME
            # timestamp's per-asset encodings and append it as slot S+1.
            m_mean = _masked_mean(h, mask)                       # (B, d)
            m_cap = _masked_weighted_mean(h, mask, self.cap_weights)  # (B, d)
            m = self.market_mlp(m_mean, m_cap)                   # (B, d)
            m = m + self.market_id.unsqueeze(0)                  # market slot id
            h_aug = torch.cat([h, m.unsqueeze(1)], dim=1)        # (B, S+1, d)
            # market slot is ALWAYS valid in the attention (False == not PAD)
            mkt_pad = torch.zeros((B, 1), dtype=key_pad.dtype, device=key_pad.device)
            key_pad_aug = torch.cat([key_pad, mkt_pad], dim=1)   # (B, S+1)
            for layer in self.layers:
                h_aug = layer(h_aug, key_pad_aug)
            h_attn = h_aug[:, :S]                                # (B, S, d)
            m_ctx = h_aug[:, S]                                  # (B, d)
        else:
            for layer in self.layers:
                h = layer(h, key_pad)
            h_attn = h
            m_ctx = None

        if self.use_factor_split:
            # Phase 2: y_hat = common_factor (broadcast) + per-asset residual.
            factor = self.beta_proj(m_ctx)                       # (B, 1)
            resid = self.resid_head(h_attn)                      # (B, S)
            out = factor + resid                                 # (B, S)
            return out

        h_attn = self.head_norm(h_attn)
        out = self.head(h_attn)                                  # (B, S, n_out)
        if self.n_out == 1:
            out = out.squeeze(-1)                                # (B, S)
        return out


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

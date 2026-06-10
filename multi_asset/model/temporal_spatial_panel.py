"""Temporal-Spatial cross-asset panel model for crypto y_600 prediction.

The shallow `CrossAssetPanelModel` encodes each asset from a single LAST-TOKEN
feature vector — it discards the temporal sequence that gave single-asset BTC its
0.058 per-asset Pearson (last-token linear per-alt Pearson is ~0). This model
restores the temporal axis and fuses it with the cross-asset (spatial) axis:

    TEMPORAL  (per asset, shared weights):
        Xseq (B, S, T, F)  -> reshape (B*S, T, F)
        -> input_proj F->d -> Conformer(2 blocks, kernel=15) -> last-token (B*S, d)
        -> (B, S, d)   per-asset embedding h_i   [recovers the single-asset signal]

    SPATIAL  (across the S assets at the SAME prediction time):
        + learnable asset-id embedding (S, d)
        + [optional] symmetric market/common-factor token  (slot S+1)
        + [optional] n_xattn cross-asset MultiheadAttention layers (masked)
        + [optional] in-graph factor/residual split (alt = beta*market + idio)

    HEAD  (per asset, shared):
        DirectionAwareQuantileHead on (B*S, d) -> q10/q50/q90 + sign_logit
        -> (B, S, 3) quantiles, (B, S) point q50

Milestones (all flag-gated so each addition is isolable):
    M0  n_xattn=0, market_token=False, factor_split=False
        -> pure per-asset temporal model. GATE: per-asset P must approach the
           single-asset 0.058 (sanity that the temporal stem + dataset are right).
    M1  + cross-asset attention (n_xattn=2)   GATE: +per-asset P over M0.
    M2  + market token / factor split          GATE each.

Capacity matched to single-asset (d=32, 2 Conformer blocks) so the shared encoder
sees B*S asset-windows -> healthy params:sample. The temporal encoder is
asset-AGNOSTIC (identity is injected downstream via the asset-id embedding), which
is what makes weight-sharing across 14 assets a regulariser rather than a
limitation.
"""
from __future__ import annotations

import sys
import os.path as _p

import torch
import torch.nn as nn

# reuse the PROVEN single-asset temporal stem + head (src/ is in the synced repo)
sys.path.insert(0, _p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
from src.model.backbones.conformer_backbone import ConformerBackbone  # noqa: E402
from src.model.direction_aware_quantile_head import (  # noqa: E402
    DirectionAwareQuantileHead,
)
from multi_asset.model.cross_asset_panel import (  # noqa: E402
    CrossAssetAttnLayer, MarketMLP,
    _masked_mean, _masked_weighted_mean,
)


class SharedTemporalEncoder(nn.Module):
    """F-channel per-asset sequence -> d-dim embedding. Shared across all assets.

    input_proj (F->d) -> Conformer(n_blocks, kernel) -> last-token pool (B*, d).
    Causal throughout (Conformer conv is causally trimmed, self-attn is masked).
    """

    def __init__(self, n_feat: int, d: int, n_blocks: int = 2,
                 n_heads: int = 2, kernel_size: int = 15, dropout: float = 0.2,
                 multipool: bool = False, pool_windows=(30, 120)):
        super().__init__()
        self.input_proj = nn.Linear(n_feat, d)
        self.in_norm = nn.LayerNorm(d)
        self.backbone = ConformerBackbone(
            d_model=d, n_blocks=n_blocks, n_heads=n_heads,
            kernel_size=kernel_size, dropout=dropout,
        )  # returns last-token (B*, d) by default (return_sequence not set)
        # A1a: multi-pool divided space-time — let cross-asset attention read K
        # causal temporal pools {last, mean(-w) for w in pool_windows} instead of
        # one collapsed last-token (fixes R1's structural blind spot: spatial
        # attention could not see time-varying relative strength).
        self.multipool = multipool
        self.pool_windows = tuple(pool_windows)
        self.K = 1 + len(self.pool_windows)
        if multipool:
            self.backbone.return_sequence = True
            self.scale_emb = nn.Parameter(torch.zeros(self.K, d))
            nn.init.normal_(self.scale_emb, std=0.02)

    def forward(self, x):  # x: (N, T, F) -> (N, d) or (N, K, d) if multipool
        h = self.in_norm(self.input_proj(x))
        if not self.multipool:
            return self.backbone(h)
        H = self.backbone(h)                               # (N, T, d) seq
        pools = [H[:, -1, :]]                               # last-token (current R1)
        for w in self.pool_windows:
            pools.append(H[:, -w:, :].mean(dim=1))          # causal mean over last w bars
        P = torch.stack(pools, dim=1)                       # (N, K, d)
        return P + self.scale_emb.unsqueeze(0)              # + scale-id embedding


class TemporalSpatialPanelModel(nn.Module):
    """Shared temporal encoder + cross-asset attention + per-asset DAQH head.

    Parameters
    ----------
    n_feat, n_assets : data dims (F=44, S=14).
    d : model width (default 32, matches single-asset capacity).
    n_blocks, kernel_size : temporal Conformer config.
    n_xattn : number of cross-asset attention layers (0 = M0, pure per-asset).
    use_market_token, use_factor_split : spatial Phase-1/2 toggles.
    cap_weights : (S,) train-fixed dollar-vol weights for the market token.
    """

    def __init__(
        self,
        n_feat: int,
        n_assets: int,
        d: int = 32,
        n_blocks: int = 2,
        kernel_size: int = 15,
        nhead: int = 4,
        n_xattn: int = 2,
        dropout: float = 0.2,
        use_market_token: bool = False,
        use_factor_split: bool = False,
        cap_weights=None,
        multipool: bool = False,
        pool_windows=(30, 120),
        coarse: bool = False,
        coarse_len: int = 240,
    ):
        super().__init__()
        if use_factor_split and not use_market_token:
            raise ValueError("use_factor_split requires use_market_token=True")
        if use_factor_split and n_xattn == 0:
            raise ValueError("use_factor_split needs cross-asset attention "
                             "(the factor is read off the attended market token)")
        if use_market_token and n_xattn == 0:
            raise ValueError("market_token only matters with cross-asset attention")
        self.n_assets = n_assets
        self.use_market_token = use_market_token
        self.use_factor_split = use_factor_split
        self.n_xattn = n_xattn

        self.multipool = multipool
        self.encoder = SharedTemporalEncoder(
            n_feat, d, n_blocks=n_blocks, n_heads=2,
            kernel_size=kernel_size, dropout=dropout,
            multipool=multipool, pool_windows=pool_windows,
        )
        self.K = self.encoder.K
        self.asset_id = nn.Parameter(torch.zeros(n_assets, d))
        nn.init.normal_(self.asset_id, std=0.02)
        if multipool:
            # softmax read-out over the K scale-tokens per asset (entropy-light)
            self.readout = nn.Linear(d, 1)
        # NX-M1: coarse multi-scale context branch (1h of 15s-pooled features).
        # Fixes the lookback:horizon mismatch at 30min horizons (fine window sees
        # only 600s). Zero-init fusion gate -> coarse-off is bit-identical to R1.
        self.coarse = coarse
        self.coarse_len = coarse_len
        if coarse:
            self.coarse_encoder = SharedTemporalEncoder(
                n_feat, d, n_blocks=1, n_heads=2, kernel_size=9, dropout=dropout)
            self.coarse_proj = nn.Linear(d, d)
            self.coarse_alpha = nn.Parameter(torch.zeros(1))

        self.layers = nn.ModuleList(
            [CrossAssetAttnLayer(d, nhead, dropout) for _ in range(n_xattn)]
        )

        if use_market_token:
            self.market_mlp = MarketMLP(d, dropout)
            self.market_id = nn.Parameter(torch.zeros(d))
            nn.init.normal_(self.market_id, std=0.02)
            if cap_weights is None:
                cap_weights = torch.ones(n_assets)
            cap_weights = torch.as_tensor(cap_weights, dtype=torch.float32)
            cap_weights = cap_weights / cap_weights.sum().clamp(min=1e-6) * n_assets
            self.register_buffer("cap_weights", cap_weights)

        if use_factor_split:
            # The DAQH below IS the per-asset idiosyncratic (residual) head; the
            # factor split only adds a shared broadcast market factor on top.
            self.beta_proj = nn.Linear(d, 1)

        # per-asset quantile head (sign x magnitude decomp + monotone q10<=q50<=q90)
        self.head = DirectionAwareQuantileHead(d_input=d, dropout=dropout)

    def forward(self, x, mask, return_dict: bool = False, x_coarse=None):
        """x: (B, S, T, F); mask: (B, S) {0,1}; x_coarse: (B, S, Tc, F) or None.
        Returns (B, S) point q50, or a dict with per-asset quantiles."""
        B, S, T, Fdim = x.shape
        x = torch.nan_to_num(x, nan=0.0)
        # zero padded assets at input so the shared encoder never sees junk
        x = x * mask.view(B, S, 1, 1)

        # ---- TEMPORAL: shared encoder over each asset-window ----
        enc = self.encoder(x.reshape(B * S, T, Fdim))        # (B*S,d) or (B*S,K,d)
        if self.coarse and x_coarse is not None:
            xc = torch.nan_to_num(x_coarse, nan=0.0) * mask.view(B, S, 1, 1)
            Tc = xc.shape[2]
            hc = self.coarse_encoder(xc.reshape(B * S, Tc, Fdim))   # (B*S, d)
            enc = enc + torch.tanh(self.coarse_alpha) * self.coarse_proj(hc)
        d = enc.shape[-1]

        # ---- SPATIAL: cross-asset attention (+ optional market token) ----
        key_pad = mask < 0.5                                  # True = PAD
        all_pad = key_pad.all(dim=1, keepdim=True)
        key_pad = key_pad & ~all_pad                          # keep MHA finite

        m_ctx = None
        if self.multipool:
            # A1a: S*K scale-tokens -> cross-asset attention over S*K -> softmax
            # read-out over the K scale-tokens per asset. Lets spatial attention
            # read the SHORT-horizon trajectory (where cross-sectional info lives),
            # not just the collapsed last-token.
            K = self.K
            h = enc.view(B, S, K, d) + self.asset_id.view(1, S, 1, d)
            h = h.reshape(B, S * K, d)                        # (B, S*K, d)
            kp = key_pad.unsqueeze(2).expand(B, S, K).reshape(B, S * K)
            for layer in self.layers:
                h = layer(h, kp)
            h = h.view(B, S, K, d)
            w = torch.softmax(self.readout(h).squeeze(-1), dim=2)   # (B,S,K)
            h_attn = (h * w.unsqueeze(-1)).sum(dim=2)               # (B,S,d)
        elif self.n_xattn > 0:
            h = enc.view(B, S, d) + self.asset_id.unsqueeze(0)
            if self.use_market_token:
                m_mean = _masked_mean(h, mask)
                m_cap = _masked_weighted_mean(h, mask, self.cap_weights)
                m = self.market_mlp(m_mean, m_cap) + self.market_id.unsqueeze(0)
                h_aug = torch.cat([h, m.unsqueeze(1)], dim=1)         # (B, S+1, d)
                mkt_pad = torch.zeros((B, 1), dtype=key_pad.dtype,
                                      device=key_pad.device)
                key_pad_aug = torch.cat([key_pad, mkt_pad], dim=1)
                for layer in self.layers:
                    h_aug = layer(h_aug, key_pad_aug)
                h_attn = h_aug[:, :S]
                m_ctx = h_aug[:, S]
            else:
                for layer in self.layers:
                    h = layer(h, key_pad)
                h_attn = h
        else:
            h_attn = enc.view(B, S, d) + self.asset_id.unsqueeze(0)

        # ---- HEAD: per-asset quantile head ----
        out = self.head(h_attn.reshape(B * S, d))             # dict, leaves (B*S,*)
        q50 = out["point_pred"].view(B, S)                    # (B, S)

        if self.use_factor_split:
            # alt = broadcast market factor + per-asset idiosyncratic residual.
            # The DAQH q50 IS the residual head's job here, so factor adds to it.
            factor = self.beta_proj(m_ctx)                    # (B, 1)
            q50 = q50 + factor                                # (B, S)

        if return_dict:
            return {
                "q50": q50,
                "quantiles": out["quantiles"].view(B, S, 3),
                "sign_logit": out["sign_logit"].view(B, S),
                "magnitude_abs": out["magnitude_abs"].view(B, S),
            }
        return q50


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

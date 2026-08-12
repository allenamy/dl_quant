"""Full shared-backbone REG_arch panel model for multi-asset cross-sectional y_600.

Wraps the PROVEN single-asset DualPathLOBModelV3 (dual-path: hand features + 5-level
raw-LOB encoder + Conformer + FiLM multistage + GDCN + RevIN) as a SHARED per-asset
backbone across the 14 assets, then mixes the per-asset embeddings with the model's
built-in CrossAssetAttention, then a shared monotonic 3-quantile head per asset. This
is the "focus a" build: the full REG_arch, not the stripped Conformer (M0/R1).

Two-pass panel forward (single-encode, efficient):
  1. encode each asset's window -> h_pred (B*S, d)   [full REG_arch stem, shared weights]
  2. cross_asset_attn over the S-asset axis -> refined (B, S, d)   [the spatial lever]
  3. shared monotonic 3-quantile head -> (B, S, 3)

Head = monotonic 3-quantile (q10<=q50<=q90), NOT DAQH (the loss research showed DAQH's
absolute-sign decomp fights the cross-sectional residual objective). q50 feeds the
LambdaRankIC + Huber residual loss; (q10,q90) feed the pinball sizing term.

NOTE on encode-order: with use_film_multistage=True (ppnet skipped) and use_regime_film
off, encode() returns h_pred right after film_gate_final, so applying cross_asset_attn
AFTER encode matches the model's intended order (cross-asset is applied at that point
inside encode when cross_asset_feats is passed). Single-encode avoids 2x compute.
"""
from __future__ import annotations

import sys
import os.path as _p

import torch
import torch.nn as nn

sys.path.insert(0, _p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
from src.model.dual_path_model_v3 import DualPathLOBModelV3  # noqa: E402


def default_reg_arch_cfg(n_features=44, n_levels=5, n_assets=14):
    """The proven REG_arch config (btc_dualpath) adapted for the cross-sectional
    residual panel: DAQH OFF -> plain monotonic 3-quantile head; n_symbols=14 so the
    built-in CrossAssetAttention is instantiated."""
    return dict(
        n_features=n_features, n_levels=n_levels, n_symbols=n_assets,
        d_model=32, d_raw=16, d_prior=6, dropout=0.2, n_horizons=1,
        use_revin=True, use_raw_path=True, use_masknet=False, use_gdcn=True,
        use_channel_mix_conv=True, use_level_attention_pool=True,
        use_ppnet_gate=True, use_film_multistage=True,
        use_attention=False, use_conv=False,
        use_monotonic_quantile=True, use_direction_aware_head=False,
        backbone_kind="conformer",
        backbone_kwargs=dict(n_blocks=2, n_heads=2, kernel_size=15),
    )


class PanelREGArch(nn.Module):
    def __init__(self, cfg=None, n_assets=14):
        super().__init__()
        self.n_assets = n_assets
        self.cfg = cfg or default_reg_arch_cfg(n_assets=n_assets)
        self.core = DualPathLOBModelV3(**self.cfg)
        assert self.core.cross_asset_attn is not None, \
            "n_symbols>1 required to instantiate CrossAssetAttention"

    def forward(self, x_feat, x_raw=None, regime=None, mask=None, return_dict=True):
        """x_feat: (B,S,T,F); x_raw: (B,S,T,L,4) or None; regime: (B,S,d_prior) or None.
        Returns dict with q50 (B,S) + quantiles (B,S,3)."""
        B, S, T, F = x_feat.shape
        xf = torch.nan_to_num(x_feat, nan=0.0).reshape(B * S, T, F)
        xr = (x_raw.reshape(B * S, T, x_raw.shape[3], x_raw.shape[4])
              if x_raw is not None else None)
        rg = regime.reshape(B * S, -1) if regime is not None else None
        # 1. shared full-REG_arch encode -> per-asset embedding
        h = self.core.encode(xf, xr, rg)                       # (B*S, d)
        d = h.shape[-1]
        h = h.view(B, S, d)
        # 2. cross-asset attention over the S-asset axis (the spatial lever)
        h = self.core.cross_asset_attn(h)                      # (B, S, d)
        # 3. shared monotonic 3-quantile head
        out = self.core.quantile_heads[0](h.reshape(B * S, d))
        q = out["quantiles"] if isinstance(out, dict) else out  # (B*S, 3)
        q = q.view(B, S, 3)
        if return_dict:
            return {"q50": q[..., 1], "quantiles": q}
        return q[..., 1]


def count_params(m):
    return sum(p.numel() for p in m.parameters() if p.requires_grad)

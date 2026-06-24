"""DualLOBREGArch: perp deep-book gated residual on top of the proven REG_arch.

The single-asset BTC ``y_600`` signal comes from a SPOT-feature model
(``REG_arch`` = ``src/model/dual_path_model_v3.py::DualPathLOBModelV3``). Its
Path-B raw-LOB tower consumes the SPOT book (``X_raw_spot`` in the dual-data
npz). This subclass FUSES the PERP deep order book as a *gated residual* on the
fused ``d_model`` bus, right after the spot Path-A/Path-B fusion and BEFORE the
Conformer backbone — so everything downstream (backbone, FiLM, DAQH head) is
UNCHANGED and the perp book never adds Path-A channels (no anti-pattern #29
channel-addition penalty; it enters as a residual on the existing bus).

Mechanism
---------
The perp book carries microstructure state (depth-pressure ladder, liquidity
placement, basis-bearing imbalance) that the spot book does not. We encode it
with the SAME ``RawLOBEncoder`` topology the parent uses for its raw path, then
inject it as a *state-dependent* residual::

    h_perp = raw_encoder_perp(x_raw_perp_deep)        # (B,T,d_perp)
    g      = sigmoid(perp_gate(h))                     # (B,T,d_model) data-dep gate
    h      = h + tanh(perp_alpha) * g * perp_proj(h_perp)

* ``perp_gate`` (bias init 0 → sigmoid≈0.5) lets the fused stream itself decide,
  per-timestep per-channel, how much perp signal to admit (state-dependent).
* ``perp_alpha`` is a learnable master gate, init ``0.05`` (NOT 0.0). A true-zero
  master gate (``tanh(0)=0``) multiplies the ENTIRE residual sub-net by zero, so
  ``raw_encoder_perp`` / ``perp_proj`` receive ZERO gradient and cannot train
  before early-stop — the gradient-starvation bug verified in
  ``multi_asset/model/temporal_spatial_panel.py`` (the ``dmf_alpha`` /
  ``reg_alpha`` "GRADIENT-STARVATION FIX" comments). Init ``tanh(0.05)≈0.05`` is
  a ~5% perturbation of the spot stream (safe) while giving the residual sub-net
  real gradient from step 0; the optimizer can still shrink ``perp_alpha``→0 if
  the perp book proves useless.

Splice (zero src/ edits)
------------------------
The injection point is between fusion (``DualPathLOBModelV3.encode`` lines ~1039
``h = self.fusion(...)``) and the temporal backbone (line ~1058
``if self.backbone is not None:``). The parent's ``encode`` does fusion AND
backbone in one method, so there is no seam to hook. We therefore OVERRIDE
``encode`` — reproducing the parent body verbatim up to the backbone, inserting
the 4 perp lines after the fused ``h`` is formed, then delegating the remainder.

To avoid duplicating the parent's ~70-line head logic in ``forward``, the new
``x_raw_perp_deep`` tensor is threaded via a one-call instance stash: the thin
``forward`` override stores it, calls ``super().forward(...)`` (which calls
``self.encode`` — our override — and runs ALL the unchanged head/output_scale/
regime_bias/sign logic), and ``encode`` reads the stash. ``encode`` is the only
method that re-runs parent code; ``forward``'s downstream stays single-sourced.

Bit-identity guarantee: with ``perp_alpha == 0`` (or ``x_raw_perp_deep is None``,
or ``use_perp_residual=False``) the residual term is EXACTLY 0, so ``encode`` is
the parent's ``encode`` line-for-line and the whole model is a pure extension.
"""
from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn

from src.model.dual_path_model_v3 import DualPathLOBModelV3
from src.model.raw_lob_encoder import RawLOBEncoder  # same class the parent uses for Path B


class DualLOBREGArch(DualPathLOBModelV3):
    """REG_arch (``DualPathLOBModelV3``) + perp deep-book gated residual.

    Parameters (new; everything else is inherited verbatim)
    -------------------------------------------------------
    use_perp_residual : bool
        Master switch. When False the class is byte-identical to the parent.
    perp_n_levels : int
        LOB levels of the perp deep book (the ``x_raw_perp_deep`` tensor's
        level axis). Default 20 (matches the dual-data ``X_raw`` cache).
    d_perp : int
        Output width of the perp ``RawLOBEncoder`` (= the parent's ``d_raw``
        role for the perp path). Default 16.
    perp_alpha_init : float
        Init value of the learnable master gate ``perp_alpha`` (pre-tanh).
        Default 0.05 — NON-zero on purpose (see module docstring: zero starves
        the residual sub-net of gradient before early-stop).
    """

    def __init__(
        self,
        *args,
        use_perp_residual: bool = False,
        perp_n_levels: int = 20,
        d_perp: int = 16,
        perp_alpha_init: float = 0.05,
        use_snapshot_skip: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.use_perp_residual = bool(use_perp_residual)
        self.perp_n_levels = int(perp_n_levels)
        self.d_perp = int(d_perp)
        # one-call stash for forward()->encode() threading of the perp tensor
        self._x_raw_perp_deep: Optional[torch.Tensor] = None

        # --- linear snapshot skip-path (default OFF; zero-init = exact identity) ---
        # Mechanism: the Conformer backbone TEMPORALLY AVERAGES the per-timestep
        # features, which DESTROYS the instantaneous-OBI-snapshot signal that a
        # Ridge on the LAST-TIMESTEP feature vector captures (the documented
        # choppy-regime ceiling: on choppy months Ridge-on-snapshot beats the DL).
        # This skip is a direct learned LINEAR readout of x_feat[:, -1, :] (the
        # last-timestep hand-crafted feature vector) added to the quantile output,
        # giving the model a parallel snapshot path the temporal pooling cannot
        # wash out. Weight AND bias are ZERO-init so the term contributes EXACTLY
        # 0 at step 0 (the model is byte-identical to the verified base at init,
        # strong result unchanged); training grows it only where it helps (choppy).
        # n_features = parent's stored feature dim (= x_feat last dim, e.g. 72/64);
        # output dim 3 = the head's quantiles [q10, q50, q90]. Added to the FINAL
        # returned quantiles (post output_scale / regime_bias, applied inside the
        # parent forward) — a learned linear term in the model's output space.
        self.use_snapshot_skip = bool(use_snapshot_skip)
        if self.use_snapshot_skip:
            self.snapshot_skip = nn.Linear(self.n_features, 3)
            nn.init.zeros_(self.snapshot_skip.weight)
            nn.init.zeros_(self.snapshot_skip.bias)
        else:
            self.snapshot_skip = None

        if self.use_perp_residual:
            # SAME encoder class + key kwargs as the parent's Path-B raw_encoder
            # (channel_mix_conv + level_attention_pool), sized for the perp book.
            self.raw_encoder_perp = RawLOBEncoder(
                n_levels=self.perp_n_levels,
                d_raw=self.d_perp,
                dropout=self.dropout,
                use_channel_mix_conv=self.use_channel_mix_conv,
                use_level_attention_pool=self.use_level_attention_pool,
            )
            # project perp embedding (d_perp) up to the fused bus width (d_model)
            self.perp_proj = nn.Linear(self.d_perp, self.d_model)
            nn.init.normal_(self.perp_proj.weight, std=0.02)
            nn.init.zeros_(self.perp_proj.bias)
            # data-dependent per-channel gate; bias 0 -> sigmoid(0)=0.5 at init
            self.perp_gate = nn.Linear(self.d_model, self.d_model)
            nn.init.zeros_(self.perp_gate.bias)
            # learnable master gate; init 0.05 (NOT 0.0) -> gradient reaches the
            # residual sub-net from step 0 (anti gradient-starvation, see docstr)
            self.perp_alpha = nn.Parameter(
                torch.tensor(float(perp_alpha_init), dtype=torch.float32)
            )
        else:
            self.raw_encoder_perp = None
            self.perp_proj = None
            self.perp_gate = None
            self.perp_alpha = None

    # ------------------------------------------------------------------ #
    # encode: parent body verbatim up to the backbone + 4 perp lines     #
    # ------------------------------------------------------------------ #
    def encode(
        self,
        x_feat: torch.Tensor,
        x_raw: torch.Tensor | None = None,
        regime_prior: torch.Tensor | None = None,
        cross_asset_feats: torch.Tensor | None = None,
        x_raw_perp_deep: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Identical to ``DualPathLOBModelV3.encode`` except the perp residual is
        injected on the fused ``h`` right BEFORE the temporal backbone.

        The perp tensor is taken from the explicit kwarg if given, else from the
        one-call stash set by :meth:`forward` (so the inherited parent ``forward``
        — which calls ``self.encode`` with the parent's fixed kwarg set — still
        delivers it without re-implementing the head logic).
        """
        if x_raw_perp_deep is None:
            x_raw_perp_deep = self._x_raw_perp_deep

        # ===== BEGIN verbatim parent encode (preprocessing -> fusion) =====
        # 0. RevIN: per-instance normalization of input features.
        if self.use_revin:
            x_feat = self.revin.normalize(x_feat)

        # v5push Track A1: SE-block input-channel attention (default off).
        if self.se_block_input is not None:
            x_feat = self.se_block_input(x_feat)

        # 1. Path A: features -> MaskNet -> GDCN -> proj
        if self.use_masknet:
            h_craft = self.masknet(x_feat)
        else:
            h_craft = x_feat

        if self.use_gdcn:
            h_craft = self.gdcn(h_craft)

        h_craft = self.input_proj(h_craft)       # (B, L, d_model)

        # 2. Path B: raw LOB tensor (SPOT book in the dual-data caliber).
        h_raw = None
        if self.use_raw_path and x_raw is not None:
            h_raw = self.raw_encoder(x_raw)      # (B, L, d_raw)
            if self.fusion_kind == "late":
                h = None
            elif self.fusion_kind == "glu":
                h = self.fusion(h_craft, h_raw)
            else:
                h = torch.cat([h_craft, h_raw], dim=-1)
                h = self.fusion(h)               # (B, L, d_model) concat-linear
        else:
            h = h_craft                          # (B, L, d_model)

        # 2.5 Multi-scale feature augmentation (Y600 push, default off).
        if self.use_multi_scale and x_raw is not None:
            ms_feat = self.multi_scale_aug(x_raw.float())
            ms_feat = self.ms_norm(ms_feat)
            ms_h = self.ms_encoder(ms_feat)
            h = h + ms_h
        # ===== END verbatim parent encode (fused stream `h` is now formed) =====

        # ---- INJECTION: perp deep-book gated residual (the 4 new lines) ----
        # Placed after the spot Path-A/Path-B fusion produces `h` (B,T,d_model),
        # BEFORE the Conformer backbone. tanh(perp_alpha)=0 => exact identity.
        # Skipped under late fusion (h is None there; perp residual unsupported
        # for late-fusion backbones, which receive h_craft/h_raw separately).
        if (
            self.use_perp_residual
            and x_raw_perp_deep is not None
            and h is not None
        ):
            h_perp = self.raw_encoder_perp(x_raw_perp_deep)        # (B,T,d_perp)
            g = torch.sigmoid(self.perp_gate(h))                    # (B,T,d_model)
            h = h + torch.tanh(self.perp_alpha) * g * self.perp_proj(h_perp)

        # ---- Delegate the UNCHANGED remainder (backbone -> gates -> pool) ----
        return self._encode_tail(h, h_craft, h_raw, x_feat, regime_prior,
                                 cross_asset_feats)

    def _encode_tail(
        self,
        h: torch.Tensor | None,
        h_craft: torch.Tensor,
        h_raw: torch.Tensor | None,
        x_feat: torch.Tensor,
        regime_prior: torch.Tensor | None,
        cross_asset_feats: torch.Tensor | None,
    ) -> torch.Tensor:
        """The parent ``encode`` body FROM the temporal backbone onward.

        Reproduced verbatim from ``DualPathLOBModelV3.encode`` (steps 3..8) so
        the injection in :meth:`encode` can sit between fusion and backbone
        without editing ``src/``. ``h_raw`` is threaded in (computed once in
        :meth:`encode`) so the late-fusion backbone path is NOT re-run — keeping
        dropout draws bit-identical to the parent. No behavioural change.
        """
        # 3. Temporal backbone.
        if self.backbone is not None:
            if self.fusion_kind == "late":
                h_pred = self.backbone(h_craft, h_raw)
            elif (getattr(self, 'use_film_multistage', False) or getattr(self, 'use_xattn_regime', False)) and regime_prior is not None:
                tv_features = None
                if getattr(self, 'use_tv_film', False) and self.n_tv_channels > 0:
                    K = self.n_tv_channels
                    tv_features = x_feat[:, :, -K:]
                for i, blk in enumerate(self.backbone.blocks):
                    h = blk(h)
                    if i == 0:
                        if self.film_gate_block1 is not None:
                            h = self.film_gate_block1(h, regime_prior)
                            if self.tv_film_gate_block1 is not None and tv_features is not None:
                                h = self.tv_film_gate_block1(h, tv_features)
                        if getattr(self, 'xattn_gate_block1', None) is not None:
                            h = self.xattn_gate_block1(h, regime_prior)
                    elif i == 1:
                        if self.film_gate_block2 is not None:
                            h = self.film_gate_block2(h, regime_prior)
                            if self.tv_film_gate_block2 is not None and tv_features is not None:
                                h = self.tv_film_gate_block2(h, tv_features)
                        if getattr(self, 'xattn_gate_block2', None) is not None:
                            h = self.xattn_gate_block2(h, regime_prior)
                    elif i == 2:
                        if getattr(self, 'film_gate_block3', None) is not None:
                            h = self.film_gate_block3(h, regime_prior)
                if getattr(self, 'seq_direction_head', None) is not None:
                    self._last_seq_dir_logits = self.seq_direction_head(h).squeeze(-1)
                else:
                    self._last_seq_dir_logits = None
                if getattr(self, 'multi_res_pool', None) is not None:
                    h_pred = self.multi_res_pool(h)
                else:
                    h_pred = h[:, -1, :]
                if self.film_gate_final is not None:
                    h_pred = self.film_gate_final(h_pred, regime_prior)
                if getattr(self, 'xattn_gate_final', None) is not None:
                    h_pred = self.xattn_gate_final(h_pred, regime_prior)
            else:
                h_pred = self.backbone(h)
                if h_pred.dim() == 3:
                    if getattr(self, 'multi_res_pool', None) is not None:
                        h_pred = self.multi_res_pool(h_pred)
                    else:
                        h_pred = h_pred[:, -1, :]
        elif self.use_attention:
            if self.use_conv:
                h = self.temporal_conv(h)
            h = self.patch_embed(h)
            h = self.patch_attention(h)
            if self.use_patch_attention_pool and self.token_pool is not None:
                h_pred = self.token_pool(h)
            else:
                h_pred = h[:, -1, :]
        else:
            if self.use_conv:
                h = self.temporal_conv(h)
            h_pred = h[:, -1, :]

        # 7. Cross-asset attention (optional)
        if cross_asset_feats is not None and self.cross_asset_attn is not None:
            all_symbols = torch.cat(
                [h_pred.unsqueeze(1), cross_asset_feats], dim=1
            )
            all_symbols = self.cross_asset_attn(all_symbols)
            h_pred = all_symbols[:, 0, :]

        # 8a. Regime-aware FiLM modulation.
        if self.use_regime_film and self.regime_film is not None:
            regime_feats = self.regime_extractor(x_feat)
            h_pred = self.regime_film(h_pred, regime_feats)

        # 8. PPNet regime-conditioned gating.
        if regime_prior is not None and self.ppnet_gate is not None \
                and not getattr(self, 'use_film_multistage', False):
            h_pred = self.ppnet_gate(h_pred, regime_prior)

        return h_pred

    # ------------------------------------------------------------------ #
    # forward: thin wrapper that threads x_raw_perp_deep, head logic kept #
    # single-sourced in the parent DualPathLOBModelV3.forward             #
    # ------------------------------------------------------------------ #
    def forward(
        self,
        x_feat: torch.Tensor,
        x_raw: torch.Tensor | None = None,
        regime_prior: torch.Tensor | None = None,
        cross_asset_feats: torch.Tensor | None = None,
        horizon_idx: int = 0,
        all_horizons: bool = False,
        x_raw_perp_deep: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        """Identical to the parent ``forward`` but accepts ``x_raw_perp_deep``.

        Stashes the perp tensor for the duration of this one call, then defers
        to the parent ``forward`` (which calls ``self.encode`` — our override —
        and runs ALL the unchanged quantile-head / output_scale / regime_bias /
        sign-head logic). The stash is cleared in a ``finally`` so the instance
        never carries state across calls.
        """
        self._x_raw_perp_deep = x_raw_perp_deep
        try:
            out = super().forward(
                x_feat=x_feat,
                x_raw=x_raw,
                regime_prior=regime_prior,
                cross_asset_feats=cross_asset_feats,
                horizon_idx=horizon_idx,
                all_horizons=all_horizons,
            )
        finally:
            self._x_raw_perp_deep = None

        # --- linear snapshot skip-path (zero-init => no-op at start) ----------
        # Add the learned linear readout of the LAST-TIMESTEP feature vector to
        # the head's quantiles, in the SAME output space the trainer/eval consume
        # (out["quantiles"] / out["point_pred"], and the *_by_horizon tensors in
        # multi-horizon mode). At init weight+bias are 0 so `snap` is exactly 0
        # and `out` is byte-identical to the base model.
        if self.use_snapshot_skip and self.snapshot_skip is not None:
            snap = self.snapshot_skip(x_feat[:, -1, :])          # (B, 3) quantiles
            if "quantiles_by_horizon" in out:
                # Multi-horizon: the loss reads quantiles_by_horizon /
                # point_pred_by_horizon, and top-level quantiles/point_pred are
                # the horizon_idx slice. Add the SAME snapshot term to EVERY
                # horizon (one snapshot readout shared across horizons), then
                # re-derive the top-level slices so all consumers stay coherent.
                q_by_h = out["quantiles_by_horizon"]             # (B, n_h, 3)
                q_by_h = q_by_h + snap.unsqueeze(1)              # broadcast over n_h
                out["quantiles_by_horizon"] = q_by_h
                out["point_pred_by_horizon"] = q_by_h[:, :, 1]   # q50 column
                out["quantiles"] = q_by_h[:, horizon_idx, :]
                out["point_pred"] = q_by_h[:, horizon_idx, 1]
            else:
                # Single-horizon: quantiles is (B, 3), point_pred is q50 (col 1).
                q = out["quantiles"] + snap                      # (B, 3)
                out["quantiles"] = q
                out["point_pred"] = q[:, 1]
        return out

"""DualLOBV2Arch: the full v2 dual-source architecture.

> **created:** 2026-06-22 | **Session:** v2-dual-source-arch | **状态:** in-progress

ARCHITECTURE (the properly-fused multi-path DL the project designed)
--------------------------------------------------------------------
Built on the proven REG_arch (``DualPathLOBModelV3``) + perp gated residual
(``DualLOBREGArch``). This subclass adds the LONG-CONTEXT branch, completing the
spec:

  FINE path (600s @ 1s)
    Path A : SPOT-64 hand feats  + 8 BOUNDED cross-venue channels (in X[...,64:])
             -> RevIN -> (MaskNet off) -> GDCN -> input_proj           (d_model bus)
    Path B : SPOT 25/20-level raw LOB -> RawLOBEncoder                  (fused in)
    Path C : PERP 25/20-level raw LOB -> RawLOBEncoder, ZERO-INIT GATED
             RESIDUAL on the fused bus  (h += tanh(α)·σ(gate)·proj(h_perp))
    fuse A+B (+C residual) -> Conformer×2 -> FiLM-multistage(regime_prior)
  LONG-CONTEXT branch (NEW)
    X_long (60s-pooled, 4h = 240 steps, 10 ch) -> ModernTCN-lite (depthwise
    large-kernel conv k≈21 + ConvFFN) -> context vector -> ZERO-INIT-GATED FiLM
    that modulates the FINE fused bus ``h`` BEFORE the Conformer backbone.
  HEAD : DAQH monotonic-quantile (proven) ; loss = singh α=0 huber (trainer).

The two NEW levers (Path C perp residual + long-context FiLM) both start at /
near identity (gates ~0), so the model can only IMPROVE on the matched base; the
optimizer grows each branch's gate iff it helps. NO regime-gating (the spec's
hard rule — regime gating overfits; additive learned-context FiLM is safe). NO
basis divergence-SEQ channels (toxic; the cross block is bounded ratios + a
clipped basis LEVEL only).

THREADING (zero src/ edits)
---------------------------
``x_long`` is threaded exactly like ``x_raw_perp_deep`` in the parent: a one-call
instance stash set by ``forward`` and read in the encode path. The long-context
FiLM is applied at the TOP of ``_encode_tail`` (overridden), i.e. on the fused
bus ``h`` AFTER Path-A/B fusion + the Path-C perp residual and BEFORE the
Conformer backbone — the single seam where a per-sample modulation of the fine
stream is well-defined. With ``use_long_context=False`` (or ``x_long is None``)
the class is byte-identical to ``DualLOBREGArch``.
"""
from __future__ import annotations

from typing import Optional

import torch

from multi_asset.model.dual_lob_regarch import DualLOBREGArch
from multi_asset.model.modern_tcn_lite import ModernTCNLiteContext, LongContextFiLM


class DualLOBV2Arch(DualLOBREGArch):
    """``DualLOBREGArch`` (REG_arch + perp residual) + ModernTCN long-context FiLM.

    New parameters (everything else inherited verbatim)
    ---------------------------------------------------
    use_long_context : bool   master switch (False => identical to parent).
    long_c_in : int           X_long channels (10).
    long_steps : int          X_long time steps (240) — informational only.
    long_d : int              ModernTCN internal width (24).
    long_n_blocks : int       number of ModernTCN blocks (2).
    long_kernel : int         depthwise kernel size (21).
    long_d_ctx : int          context-vector width (32).
    long_film_alpha_init : float  FiLM master-gate init (0.01; small non-zero so
                              the long branch gets gradient from step 0 while the
                              perturbation is negligible; γ/β heads zero-init make
                              the modulation EXACT identity at start regardless).
    """

    def __init__(
        self,
        *args,
        use_long_context: bool = False,
        long_c_in: int = 10,
        long_steps: int = 240,
        long_d: int = 24,
        long_n_blocks: int = 2,
        long_kernel: int = 21,
        long_d_ctx: int = 32,
        long_film_alpha_init: float = 0.01,
        long_film_mode: str = "affine",
        long_gamma_clip: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.use_long_context = bool(use_long_context)
        self.long_steps = int(long_steps)
        self._x_long: Optional[torch.Tensor] = None

        if self.use_long_context:
            self.long_ctx = ModernTCNLiteContext(
                c_in=int(long_c_in), d=int(long_d), n_blocks=int(long_n_blocks),
                kernel_size=int(long_kernel), d_ctx=int(long_d_ctx),
                dropout=self.dropout,
            )
            self.long_film = LongContextFiLM(
                d_ctx=int(long_d_ctx), d_model=self.d_model,
                alpha_init=float(long_film_alpha_init),
                film_mode=str(long_film_mode), gamma_clip=float(long_gamma_clip),
            )
        else:
            self.long_ctx = None
            self.long_film = None

    # ------------------------------------------------------------------ #
    # _encode_tail: apply the long-context FiLM on the fused bus h first   #
    # ------------------------------------------------------------------ #
    def _encode_tail(self, h, h_craft, h_raw, x_feat, regime_prior,
                     cross_asset_feats):
        """Modulate the fused bus ``h`` with the long-context FiLM (identity at
        start) BEFORE delegating to the parent's backbone→pool→gates tail.

        ``h`` is the fused (B,T,d_model) stream that already carries Path A+B and
        the Path-C perp residual. We apply the long-context FiLM here so the
        Conformer backbone (run inside the parent tail) sees the modulated stream.
        When the long branch is off, or ``h`` is None (late fusion), or no x_long
        was stashed, this is a pure pass-through to the parent tail."""
        if (
            self.use_long_context
            and self.long_film is not None
            and h is not None
            and self._x_long is not None
        ):
            ctx = self.long_ctx(self._x_long)            # (B, d_ctx)
            h = self.long_film(h, ctx)                   # identity at init
        return super()._encode_tail(h, h_craft, h_raw, x_feat, regime_prior,
                                    cross_asset_feats)

    # ------------------------------------------------------------------ #
    # forward: thread x_long (+ x_raw_perp_deep via the parent) one-call    #
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
        x_long: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        self._x_long = x_long
        try:
            # parent (DualLOBREGArch.forward) stashes x_raw_perp_deep and runs the
            # full head logic; our _encode_tail override reads self._x_long.
            return super().forward(
                x_feat=x_feat,
                x_raw=x_raw,
                regime_prior=regime_prior,
                cross_asset_feats=cross_asset_feats,
                horizon_idx=horizon_idx,
                all_horizons=all_horizons,
                x_raw_perp_deep=x_raw_perp_deep,
            )
        finally:
            self._x_long = None

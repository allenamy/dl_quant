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
from src.model.regime_film import FiLM  # reuse parent FiLM (identity-init) verbatim
from multi_asset.model.regime_film_rich import RichRegimeFeatureExtractor
from multi_asset.model.regime_state import (  # D1 fixed-conditioning substrate
    PreRevINRegimeExtractor,
    normalize_frozen,
    compute_window_stats,
)


class RegimeMoE(nn.Module):
    """K=2 soft mixture-of-experts on the FINAL pooled representation.

    MECHANISM (why this, not affine FiLM)
    -------------------------------------
    The adaptive regime-FiLM (γ⊙h_pred+β) can RESCALE the pooled features per
    regime but cannot change the FUNCTIONAL FORM the head applies — yet
    strong-month MOMENTUM and choppy-month REVERSION are *different functions*
    of the same features (opposite-signed maps). A shared backbone + affine
    modulation averages those two functions, collapsing on off-average regimes
    (the documented 0.105→0.016 strong→choppy collapse). A K=2 soft-MoE lets the
    model learn TWO functional forms (two small FFNs) and SOFTMAX-ROUTE between
    them by the per-window REGIME DESCRIPTOR (``regime_prior``: price-regime, and
    in the OI configs the 8 positioning/OI descriptors). So POSITIONING STATE
    selects WHICH function — momentum-expert vs reversion-expert — rather than
    just rescaling one shared function.

    DESIGN — share most params, branch ONLY this final FFN
    ------------------------------------------------------
    The entire backbone / attention / conv / FiLM stack is SHARED (one set of
    weights). Only the final pooled-representation transform is branched into 2
    experts. The MoE output is ADDED as a residual::

        moe_out = w0 * expert0(h_pred) + w1 * expert1(h_pred)   # (B, d_model)
        h_pred  = h_pred + moe_out

    so the experts learn a regime-selected *correction* to the shared pooled
    representation. On this weak signal (R²<1%) a full per-regime backbone would
    overfit; branching only the final FFN keeps the added params tiny.

    OVERFIT GUARDS (regime-MoE has overfit on this signal in project history)
    ------------------------------------------------------------------------
    1. ZERO-INIT expert specialization: BOTH experts' OUTPUT Linear is zero-init
       (weight AND bias). => each expert outputs exactly 0 at init => moe_out==0
       REGARDLESS of router weights => h_pred is UNCHANGED at init => the model
       is BIT-IDENTICAL to the use_regime_moe=False adaptive baseline at step 0.
       The MoE can therefore ONLY help; it can never break the verified baseline.
    2. K=2 ONLY (two functional forms: momentum vs reversion — no more capacity).
    3. Router init near-uniform: the router's OUTPUT Linear is zero-init too, so
       logits==0 => softmax == exact [0.5, 0.5] at init (no premature expert
       collapse; gradient flows to both experts from step 0).
    4. LOAD-BALANCING aux loss = coefficient_of_variation^2 of the batch-mean
       router weights (encourages BOTH experts to be used; penalises a degenerate
       all-mass-on-one-expert router). Exposed (NOT applied here) so the trainer
       can add it with a SMALL weight (~0.01); if the trainer cannot consume it,
       the zero-init + heavy weight-decay still guard against overfit.
    5. Heavy weight-decay on expert+router params (configs already carry wd; the
       trainer applies one wd to all params — note: keep wd ≥ the config's).

    GRADIENT NOTE
    -------------
    Unlike the perp/long-context gates (a scalar α multiplying the whole sub-net,
    which would gradient-STARVE the sub-net if α==0), here the experts feed the
    output via an ADDITIVE residual whose magnitude is the expert OUTPUT itself.
    Zero-init makes the *value* 0 but NOT the gradient: ∂moe_out/∂W_out depends on
    the (non-zero) GELU activations, so the OUTPUT Linear receives gradient from
    step 0; the gradient to the expert INPUT Linear and to the router is scaled by
    W_out (zero at init) so it ramps in as W_out grows — by design the experts
    start as the identity (moe_out=0) and specialise only as training routes
    regimes, never breaking the baseline. The router still receives gradient via
    every step where W_out≠0; a tiny load-balance weight also keeps it live.
    """

    def __init__(self, d_model: int, d_prior: int, n_experts: int = 2,
                 router_hidden: int = 16, dropout: float = 0.0,
                 use_regime_gate: bool = False) -> None:
        super().__init__()
        assert n_experts == 2, "RegimeMoE is K=2 only (guard #2)"
        self.n_experts = int(n_experts)
        self.d_model = int(d_model)
        self.d_prior = int(d_prior)

        # --- REGIME-GATED ACTIVATION (default OFF; byte-identical when off) ---
        # Mechanism (lever-conflict resolution): the MoE helps WEAK/choppy folds
        # (standalone CLEAN ~0.085) but slightly DILUTES strong folds. Rather than
        # a hard regime switch, we add a LEARNABLE scalar gate g_moe ∈ (0,1) on the
        # MoE residual, conditioned on the per-window regime descriptor
        # (regime_prior carries vol/trend/positioning). The model LEARNS to drive
        # g_moe→~1 in weak regimes (MoE active) and g_moe→~0 in strong regimes
        # (MoE suppressed) — the regime→lever mapping is learned end-to-end.
        #
        # ZERO-INIT (weight AND bias) => logit==0 => sigmoid==0.5 at init. This is
        # the NEUTRAL half-weight start the spec asks for. CRITICAL: this does NOT
        # affect zero-init NEUTRALITY of the whole model, because moe_out is
        # ALREADY exactly 0 at init (the experts' output Linear is zero-init), so
        # g_moe * moe_out == 0.5 * 0 == 0 for ANY g_moe. The gate only learns to
        # scale the (learned) moe_out by regime as training proceeds.
        self.use_regime_gate = bool(use_regime_gate)
        if self.use_regime_gate:
            self.moe_gate = nn.Linear(self.d_prior, 1)
            nn.init.zeros_(self.moe_gate.weight)
            nn.init.zeros_(self.moe_gate.bias)
        else:
            self.moe_gate = None

        # --- K=2 expert FFNs: Linear(d->d) -> GELU -> Linear(d->d) ---
        self.experts = nn.ModuleList()
        for _ in range(self.n_experts):
            lin_in = nn.Linear(self.d_model, self.d_model)
            lin_out = nn.Linear(self.d_model, self.d_model)
            # GUARD #1: zero-init the OUTPUT Linear (weight AND bias) so the
            # expert outputs EXACTLY 0 at init -> moe_out == 0 -> bit-identical
            # to the use_regime_moe=False baseline.
            nn.init.zeros_(lin_out.weight)
            nn.init.zeros_(lin_out.bias)
            self.experts.append(nn.Sequential(
                lin_in, nn.GELU(), nn.Dropout(float(dropout)), lin_out,
            ))

        # --- router: small MLP regime_prior -> n_experts logits -> softmax ---
        # GUARD #3: router init NEAR-uniform. The output Linear gets TINY (std
        # 1e-3) weights and ZERO bias so the logits are ~0 at init -> softmax ≈
        # [0.5, 0.5] (both experts used; no premature collapse). We use a tiny
        # NON-zero std rather than exact zero on purpose: with EXACT-zero logits
        # the router sits at the precise symmetric minimum of the load-balance
        # CV^2 AND the main-path router gradient is also 0 (because zero-init
        # experts make ∂moe_out/∂w = expert(h) = 0 at init) -> the router would
        # be momentarily FROZEN at step 0. A ~1e-3 perturbation keeps the router
        # essentially uniform (|Δw| < 1e-3) while giving it live gradient from
        # step 0. This does NOT affect zero-init NEUTRALITY: neutrality comes
        # from the zero-init EXPERTS (moe_out = Σ w_k·0 = 0 for ANY router
        # weights), so the forward is still bit-identical to the MoE-off baseline
        # regardless of the router init. The hidden Linear keeps default init for
        # real expressive capacity to depart from uniform as training proceeds.
        router_out = nn.Linear(int(router_hidden), self.n_experts)
        nn.init.normal_(router_out.weight, std=1e-3)
        nn.init.zeros_(router_out.bias)
        self.router = nn.Sequential(
            nn.Linear(self.d_prior, int(router_hidden)),
            nn.GELU(),
            router_out,
        )

        # filled on every forward so the caller can read the load-balance aux loss
        self._last_lb_loss: Optional[torch.Tensor] = None
        self._last_router_w: Optional[torch.Tensor] = None
        self._last_g_moe: Optional[torch.Tensor] = None

    def forward(self, h_pred: torch.Tensor,
                regime_prior: torch.Tensor) -> torch.Tensor:
        """h_pred (B, d_model), regime_prior (B, d_prior) -> h_pred + moe_out.

        Also stores the load-balancing aux loss (CV^2 of batch-mean router
        weights) on ``self._last_lb_loss`` for the trainer to consume.
        """
        logits = self.router(regime_prior)                   # (B, n_experts)
        w = torch.softmax(logits, dim=-1)                    # (B, n_experts)

        # stack expert outputs -> (B, n_experts, d_model); weight + sum
        expert_out = torch.stack(
            [e(h_pred) for e in self.experts], dim=1)        # (B, K, d_model)
        moe_out = (w.unsqueeze(-1) * expert_out).sum(dim=1)  # (B, d_model)

        # GUARD #4: load-balancing = CV^2 of the BATCH-MEAN router weights.
        # p_k = mean_b w_{b,k} (the fraction of mass expert k receives on this
        # batch); a balanced router has p ≈ [1/K..], CV^2 ≈ 0; a collapsed router
        # (all mass on one expert) has CV^2 large -> penalised.
        p = w.mean(dim=0)                                    # (n_experts,)
        cv2 = p.var(unbiased=False) / (p.mean() ** 2 + 1e-12)
        self._last_lb_loss = cv2
        self._last_router_w = w.detach()

        # REGIME GATE: scale the MoE residual by g_moe = sigmoid(moe_gate(prior)).
        # Zero-init => g_moe==0.5 at init; moe_out==0 at init => g_moe*moe_out==0
        # => bit-identical to the gate-off / MoE-off baseline at step 0. The gate
        # learns suppress-in-strong / active-in-weak from the regime descriptor.
        if self.moe_gate is not None:
            g_moe = torch.sigmoid(self.moe_gate(regime_prior))  # (B, 1) in (0,1)
            self._last_g_moe = g_moe.detach()
            moe_out = g_moe * moe_out
        else:
            self._last_g_moe = None

        return h_pred + moe_out


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
        use_rich_regime: bool = False,
        use_oi_regime: bool = False,
        use_regime_moe: bool = False,
        moe_lb_weight: float = 0.01,
        use_regime_gated_mh: bool = False,
        use_regime_gated_moe: bool = False,
        use_fixed_regime_state: bool = False,
        use_state_prior: bool = False,
        d_state_prior: int = 18,
        use_output_gain: bool = False,
        regime_state_fit_samples: int = 50000,
        revin_skip_idx=None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        # --- RANK-NORM arm (0C): per-channel RevIN BYPASS (default OFF) ----------
        # RevIN per-window de-means ALL channels, which NEUTRALIZES the causal
        # trailing-3d RANK channels (they are already stationary via static-z).
        # Channels in revin_skip_idx SKIP RevIN (keep their static-z'd rank);
        # the rest are RevIN'd as before. Wired at the revin.normalize site in
        # encode() via an autograd-safe masked combine (no in-place). Empty/None
        # => byte-identical to the current model.
        if revin_skip_idx:
            self.register_buffer("_revin_skip_idx", torch.tensor(
                sorted(set(int(i) for i in revin_skip_idx)), dtype=torch.long))
        else:
            self._revin_skip_idx = None
        self.use_perp_residual = bool(use_perp_residual)
        self.perp_n_levels = int(perp_n_levels)
        self.d_perp = int(d_perp)
        # one-call stash for forward()->encode() threading of the perp tensor
        self._x_raw_perp_deep: Optional[torch.Tensor] = None
        # last multi-horizon regime gate value (diagnostic; set in forward)
        self._last_g_mh: Optional[torch.Tensor] = None

        # --- LEVER 1: rich (14-feature) regime FiLM extractor (default OFF) ---
        # Mechanism: the parent's RegimeFeatureExtractor feeds the identity-init
        # FiLM only 6 vol-flavoured descriptors. We swap in
        # RichRegimeFeatureExtractor (14 causal descriptors: the SAME 6 + signed
        # multi-scale trend, vol-of-vol, micro-activity, multi-lag OBI
        # persistence, all-column activity ratio) and REBUILD FiLM to accept the
        # wider input. The FiLM is re-instantiated with the parent's identity-init
        # (γ≈1, β≈0) so at step 0 the swap is identity-modulation — the model is
        # NOT broken and trains to baseline if the extra axes carry no signal.
        # Only fires when the parent actually built regime FiLM (use_regime_film).
        # Flag default False => single-horizon & non-rich paths are byte-identical.
        self.use_rich_regime = bool(use_rich_regime)

        # --- LEVER (OI regime): make the regime FiLM ALSO consume regime_prior ---
        # Mechanism: regime_prior now carries 8 DESIGNED OI/funding positioning
        # descriptors appended to the 6 vol descriptors (overlaid into the caches
        # by multi_asset/data/add_oi_regime_prior.py -> regime_prior is (N,14)).
        # That vector is already threaded dataset->model and feeds the
        # regime_bias_head / ppnet / multistage FiLM gates. Here we ALSO feed it
        # to the regime FiLM (the per-sample γ⊙h+β modulation): we CONCAT
        # regime_prior to the x_feat-derived extractor output, so positioning
        # REGIME (open-interest flow, crowding, funding×OI squeeze) can modulate
        # γ/β directly. This is the decisive DL test the linear Ridge gate cannot
        # settle. Flag default False => byte-identical to the rich/base paths.
        self.use_oi_regime = bool(use_oi_regime)

        # Rebuild the regime FiLM if EITHER lever is on. Both reuse the parent's
        # identity-init FiLM (γ≈1, β≈0) so the swap is identity-modulation at
        # step 0 (the model trains to baseline if the extra axes carry no signal).
        # Only fires when the parent actually built regime FiLM (use_regime_film).
        if (self.use_rich_regime or self.use_oi_regime) \
                and getattr(self, "use_regime_film", False) \
                and self.regime_film is not None:
            # Preserve the parent's FiLM hyper-params: hidden = the existing
            # FiLM's first-Linear out_features; dropout = the model dropout
            # (parent built FiLM with dropout=dropout). d_model from the model.
            _hidden = int(self.regime_film.mlp[0].out_features)
            if self.use_rich_regime:
                # swap the 6-feat extractor for the 14-feat rich one
                self.regime_extractor = RichRegimeFeatureExtractor(
                    obi_feature_idx=self.regime_extractor.obi_feature_idx,
                )
            # n_regime_feats = extractor descriptors (+ regime_prior width when
            # the OI lever concats the prior at FiLM time). d_prior is the
            # regime_prior width the rest of the model is also built for.
            n_regime_feats = self.regime_extractor.n_features_out
            if self.use_oi_regime:
                n_regime_feats += int(self.d_prior)
            self.regime_film = FiLM(
                d_model=self.d_model,
                n_regime_feats=n_regime_feats,
                hidden=_hidden,
                dropout=self.dropout,
            )

        # --- D1 FIXED-CONDITIONING SUBSTRATE (default OFF; bit-identical when off) --
        # Fixes the two structural regime bugs (FLAGS 1/2) WITHOUT touching src/:
        #   use_fixed_regime_state:
        #     * swap RegimeFeatureExtractor (post-RevIN, batch-z) -> the pre-RevIN
        #       RAW PreRevINRegimeExtractor (regime LEVEL preserved), consumed at
        #       the FiLM site 8a on the stashed pre-RevIN x_feat;
        #     * normalise the 6 descriptors AND the whole regime_prior with FROZEN
        #       TRAIN-WINDOW stats (register_buffer, persisted in ckpt) instead of
        #       batch-z / raw (FLAG 11) -> batch-invariant, regime-level-visible.
        #   use_state_prior:  concat the (already-widened, config d_prior=24) prior
        #     onto the fixed descriptors at 8a — same mechanism as use_oi_regime but
        #     on the normalised, positioning-carrying prior.
        # The buffers/extractor swap/FiLM rebuild are zero-init (exact identity) so
        # the flag-on model is a NEUTRAL no-op at init (see fit_regime_state_stats +
        # the bit-identity tests).
        self.use_fixed_regime_state = bool(use_fixed_regime_state)
        self.use_state_prior = bool(use_state_prior)
        self.d_state_prior = int(d_state_prior)
        self._regime_state_fit_samples = int(regime_state_fit_samples)
        # one-call stash for the pre-RevIN x_feat (set in encode, read at 8a)
        self._x_feat_pre_revin: Optional[torch.Tensor] = None
        if self.use_fixed_regime_state:
            _n_desc = 6  # PreRevINRegimeExtractor.n_features_out
            self.register_buffer("rs_desc_mean", torch.zeros(_n_desc))
            self.register_buffer("rs_desc_std", torch.ones(_n_desc))
            self.register_buffer("rs_prior_mean", torch.zeros(int(self.d_prior)))
            self.register_buffer("rs_prior_std", torch.ones(int(self.d_prior)))
            # 0 => stats not yet fitted (normalisation is identity passthrough);
            # 1 => fit_regime_state_stats has run and the buffers are live.
            self.register_buffer("rs_fitted", torch.zeros(1))
            # Rebuild the pooled-h regime FiLM around the fixed extractor iff the
            # parent actually built one. EXACT zero-init (override FiLM's 0.01
            # scaling) => γ==1, β==0 exactly => the pooled-h FiLM is an EXACT
            # identity at init regardless of descriptor/prior values.
            if getattr(self, "use_regime_film", False) and self.regime_film is not None:
                _hidden_fs = int(self.regime_film.mlp[0].out_features)
                self.regime_extractor = PreRevINRegimeExtractor(
                    obi_feature_idx=getattr(self.regime_extractor, "obi_feature_idx", 0),
                )
                n_rf = self.regime_extractor.n_features_out
                if self.use_state_prior:
                    n_rf += int(self.d_prior)
                self.regime_film = FiLM(
                    d_model=self.d_model, n_regime_feats=n_rf,
                    hidden=_hidden_fs, dropout=self.dropout,
                )
                nn.init.zeros_(self.regime_film.mlp[-1].weight)
                nn.init.zeros_(self.regime_film.mlp[-1].bias)

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

        # --- LEVER (regime-MoE): K=2 soft-MoE on the FINAL pooled rep (default OFF) ---
        # Mechanism: the adaptive regime-FiLM can only RESCALE the pooled features
        # per regime (γ⊙h+β) — it cannot change the FUNCTIONAL FORM. Strong-month
        # MOMENTUM and choppy-month REVERSION are different (opposite-signed)
        # functions of the same features; a shared backbone averages them and
        # collapses off-average (0.105→0.016 strong→choppy). A K=2 soft-MoE adds
        # TWO small expert FFNs on the pooled representation h_pred, SOFTMAX-routed
        # by the per-window regime descriptor (regime_prior), so POSITIONING STATE
        # selects WHICH function. We branch ONLY this final FFN (share all
        # backbone/attention/conv/FiLM params) — a full per-regime backbone would
        # overfit this weak signal. ZERO-INIT experts => moe_out==0 at init =>
        # bit-identical to the use_regime_moe=False adaptive baseline (proven in
        # tests); the MoE can ONLY help. See RegimeMoE docstring for all 5 guards.
        # Routes on the standard regime_prior (d_prior, =6 from the shared clean
        # caches; =14 when the OI cache overlays the 8 positioning descriptors).
        # moe_lb_weight (~0.01) is the load-balance aux-loss weight the trainer
        # MAY add via out["moe_lb_loss"]; zero-init + heavy wd guard regardless.
        # --- REGIME-GATED LEVER ACTIVATION (lever-conflict resolution) -------
        # Diagnosed conflict in the naive all-levers model: MULTI-HORIZON (y_180
        # aux) HELPS strong folds (CLEAN 0.112) but HURTS weak folds (the aux
        # y_180 head competes with the primary y_600 for the shared backbone),
        # while the regime-MoE HELPS weak folds (standalone CLEAN ~0.085) but
        # slightly DILUTES strong. FIX = make BOTH levers regime-conditional in
        # ONE model via learnable sigmoid gates the model learns to map regime->
        # lever (no hard switch):
        #   * g_moe (in RegimeMoE): MoE residual scaled up in weak / down in
        #     strong (see RegimeMoE.use_regime_gate).
        #   * g_mh (here): the AUX-horizon (non-primary, y_180) head contribution
        #     scaled BEFORE it reaches the loss, so the y_180 aux gradient/loss
        #     flows mainly in strong and is suppressed in weak — leaving the
        #     primary y_600 to dominate weak folds. The PRIMARY y_600 head slice
        #     is NEVER touched (non-negotiable guard, verified in tests).
        # Both gates default OFF => existing behaviour byte-identical.
        self.use_regime_gated_mh = bool(use_regime_gated_mh)
        self.use_regime_gated_moe = bool(use_regime_gated_moe)

        # primary horizon = the LAST horizon (codebase convention: horizons_sec=
        # [180,600] => primary y_600 is index n_horizons-1; the aux y_180 is
        # index 0). g_mh gates EVERY non-primary (aux) horizon slice; the primary
        # slice is left bit-identical. Exposed as an attribute so a future trainer
        # could override it, but the default matches train_v2arch's
        # primary_horizon_idx = horizons_list.index(f"y_{horizon_sec}").
        self.primary_horizon_idx = max(int(self.n_horizons) - 1, 0)

        self.use_regime_moe = bool(use_regime_moe)
        self.moe_lb_weight = float(moe_lb_weight)
        if self.use_regime_moe:
            self.regime_moe = RegimeMoE(
                d_model=self.d_model,
                d_prior=int(self.d_prior),
                n_experts=2,
                dropout=self.dropout,
                use_regime_gate=self.use_regime_gated_moe,
            )
        else:
            self.regime_moe = None

        # --- MULTI-HORIZON regime gate head (default OFF; zero-init neutral) ---
        # g_mh = sigmoid(mh_gate(regime_prior)) ∈ (0,1). Zero-init weight+bias =>
        # logit 0 => g_mh==0.5 at init. Applied ONLY to the aux-horizon slice of
        # quantiles_by_horizon / point_pred_by_horizon (NOT the primary y_600
        # slice) in forward(). Only built when multi-horizon (n_horizons>1) AND
        # the flag is on; single-horizon configs are byte-identical regardless.
        if self.use_regime_gated_mh and int(self.n_horizons) > 1:
            self.mh_gate = nn.Linear(int(self.d_prior), 1)
            nn.init.zeros_(self.mh_gate.weight)
            nn.init.zeros_(self.mh_gate.bias)
        else:
            self.mh_gate = None
            # keep the flag truthful: gating only fires with >1 horizon + the gate
            if self.use_regime_gated_mh and int(self.n_horizons) <= 1:
                self.use_regime_gated_mh = False

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

        # --- CONDITIONED OUTPUT GAIN (default OFF; zero-init => EXACT no-op) ------
        # The direct anti-overconfidence lever (H1: β 30.8->5.1 while σp RISES —
        # the model gets LOUDER exactly when information dies). A state-conditioned
        # multiplicative gain on the quantile outputs lets the model LEARN to shrink
        # its scale in stale/drift regimes:
        #     g(prior) = 1 + 0.5 * tanh(W · prior_norm + b)   ∈ (0.5, 1.5)
        # W,b ZERO-init => tanh(0)=0 => g==1 EXACTLY at init => multiplying the
        # quantiles by g is a bit-exact no-op. Built LAST in __init__ so toggling
        # this flag does not shift any other module's RNG draws (the output-gain
        # bit-identity test relies on this). ``prior`` is the (frozen-)normalised
        # regime_prior of width d_prior (=6 Run1 / =24 Run2).
        self.use_output_gain = bool(use_output_gain)
        if self.use_output_gain and int(self.d_prior) > 0:
            self.output_gain = nn.Linear(int(self.d_prior), 1)
            nn.init.zeros_(self.output_gain.weight)
            nn.init.zeros_(self.output_gain.bias)
        else:
            self.output_gain = None

    # ------------------------------------------------------------------ #
    # D1 fixed-conditioning helpers (frozen-stat normalisation + fitting) #
    # ------------------------------------------------------------------ #
    def _normalize_desc(self, feats: torch.Tensor) -> torch.Tensor:
        """Frozen train-window normalisation of the 6 fixed descriptors.

        Identity passthrough until :meth:`fit_regime_state_stats` has run
        (``rs_fitted==0``), so an unfitted flag-on model stays a clean no-op at
        init (the FiLM is zero-init anyway).
        """
        if float(self.rs_fitted.item()) < 0.5:
            return feats
        return normalize_frozen(feats, self.rs_desc_mean, self.rs_desc_std, clip=5.0)

    def _normalize_prior(self, prior: torch.Tensor) -> torch.Tensor:
        """Frozen train-window normalisation of the full regime_prior (FLAG 11).

        Identity passthrough until fitted.
        """
        if float(self.rs_fitted.item()) < 0.5:
            return prior
        return normalize_frozen(prior, self.rs_prior_mean, self.rs_prior_std, clip=5.0)

    @torch.no_grad()
    def fit_regime_state_stats(self, dataset, n_sample: Optional[int] = None,
                               batch: int = 1024, device: str = "cpu",
                               verbose: bool = True) -> None:
        """Compute TRAIN-WINDOW frozen stats for the fixed descriptors + prior.

        MUST be called once at fold setup (after the normalised train dataset is
        built, before training) when ``use_fixed_regime_state`` is on — the
        descriptor extractor consumes the pre-RevIN (= post-static-450d-z) x_feat
        the dataset yields, and the stats are the FLAG-2 fix that replaces batch-z.
        Samples up to ``n_sample`` (default 50k) train windows deterministically,
        runs the extractor, and writes ``rs_desc_mean/std`` + ``rs_prior_mean/std``
        into the registered buffers (persisted in the checkpoint).
        """
        if not self.use_fixed_regime_state:
            return
        import numpy as np
        n = len(dataset)
        k = int(n_sample or self._regime_state_fit_samples)
        k = min(k, n)
        rng = np.random.default_rng(0)
        idx = (np.arange(n) if k >= n
               else np.sort(rng.choice(n, size=k, replace=False)))
        extractor = self.regime_extractor
        if not isinstance(extractor, PreRevINRegimeExtractor):
            extractor = PreRevINRegimeExtractor()
        extractor = extractor.to(device)
        d_prior = int(self.d_prior)

        def _split(item):
            """Return (x_feat, regime_prior_or_None) from a dataset item tuple."""
            x_feat = item[0]
            rp = None
            for t in item[1:]:
                if torch.is_tensor(t) and t.dim() == 1 and t.shape[0] == d_prior:
                    rp = t
                    break
            return x_feat, rp

        n_seen = 0
        desc_sum = torch.zeros(6, dtype=torch.float64)
        desc_sq = torch.zeros(6, dtype=torch.float64)
        prior_sum = torch.zeros(d_prior, dtype=torch.float64)
        prior_sq = torch.zeros(d_prior, dtype=torch.float64)
        prior_seen = 0
        for start in range(0, len(idx), batch):
            chunk = idx[start:start + batch]
            xs, rps = [], []
            for i in chunk:
                x_feat, rp = _split(dataset[int(i)])
                xs.append(x_feat)
                if rp is not None:
                    rps.append(rp)
            X = torch.stack(xs).to(device).float()               # (b, L, F)
            desc = extractor(X).double()                          # (b, 6) RAW
            desc_sum += desc.sum(0).cpu()
            desc_sq += (desc ** 2).sum(0).cpu()
            n_seen += desc.shape[0]
            if len(rps) == len(xs):
                RP = torch.stack(rps).double()                   # (b, d_prior)
                prior_sum += RP.sum(0)
                prior_sq += (RP ** 2).sum(0)
                prior_seen += RP.shape[0]

        dmean = (desc_sum / max(n_seen, 1))
        dvar = (desc_sq / max(n_seen, 1) - dmean ** 2).clamp_min(1e-12)
        self.rs_desc_mean.copy_(dmean.float())
        self.rs_desc_std.copy_(dvar.sqrt().clamp_min(1e-6).float())
        if prior_seen > 0:
            pmean = (prior_sum / prior_seen)
            pvar = (prior_sq / prior_seen - pmean ** 2).clamp_min(1e-12)
            self.rs_prior_mean.copy_(pmean.float())
            self.rs_prior_std.copy_(pvar.sqrt().clamp_min(1e-6).float())
        self.rs_fitted.fill_(1.0)
        if verbose:
            print(f"[regime_state] fit on {n_seen} windows (prior_seen={prior_seen}); "
                  f"desc_mean={self.rs_desc_mean.tolist()} "
                  f"desc_std={self.rs_desc_std.tolist()}", flush=True)

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
        # D1: stash the PRE-RevIN x_feat (= post-static-450d-z; regime LEVEL
        # preserved) for the fixed regime extractor consumed at 8a. revin.normalize
        # returns a NEW tensor so this reference stays pre-RevIN.
        if self.use_fixed_regime_state:
            self._x_feat_pre_revin = x_feat
        # 0. RevIN: per-instance normalization (+ optional per-channel RevIN BYPASS
        # for the rank-norm arm). skip channels keep their pre-RevIN static-z'd
        # (stationary rank) values; the rest are RevIN'd. Autograd-safe masked
        # combine (no in-place on x_feat). Empty mask => x_feat == x_norm exactly.
        if self.use_revin:
            x_pre = x_feat
            x_norm = self.revin.normalize(x_feat)
            if self._revin_skip_idx is not None:
                keep = torch.ones(x_norm.shape[-1], device=x_norm.device, dtype=x_norm.dtype)
                keep = keep.index_fill(0, self._revin_skip_idx.to(x_norm.device), 0.0)
                x_feat = x_norm * keep + x_pre * (1.0 - keep)
            else:
                x_feat = x_norm

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
            if getattr(self, "use_fixed_regime_state", False):
                # FLAG 1/2 fix: extract on the PRE-RevIN tensor (regime level
                # preserved) and normalise the RAW descriptors with FROZEN
                # train-window stats (not batch-z). regime_prior here is ALREADY
                # frozen-normalised (done once at the top of forward).
                pre = (self._x_feat_pre_revin
                       if self._x_feat_pre_revin is not None else x_feat)
                regime_feats = self.regime_extractor(pre)          # (B, 6) RAW
                regime_feats = self._normalize_desc(regime_feats)  # frozen z, clip±5
                if getattr(self, "use_state_prior", False) and regime_prior is not None:
                    regime_feats = torch.cat(
                        [regime_feats, regime_prior.to(regime_feats.dtype)], dim=-1)
                h_pred = self.regime_film(h_pred, regime_feats)
            else:
                regime_feats = self.regime_extractor(x_feat)
                # OI lever: concat the per-window regime_prior (now carrying the 8
                # OI/funding descriptors) onto the x_feat-derived descriptors so the
                # FiLM γ/β are also conditioned on positioning REGIME. The FiLM was
                # rebuilt in __init__ to accept extractor.n_features_out + d_prior.
                if getattr(self, "use_oi_regime", False) and regime_prior is not None:
                    regime_feats = torch.cat(
                        [regime_feats, regime_prior.to(regime_feats.dtype)], dim=-1)
                h_pred = self.regime_film(h_pred, regime_feats)

        # 8. PPNet regime-conditioned gating.
        if regime_prior is not None and self.ppnet_gate is not None \
                and not getattr(self, 'use_film_multistage', False):
            h_pred = self.ppnet_gate(h_pred, regime_prior)

        # 8b. Regime-MoE: K=2 soft-MoE on the FINAL pooled representation.
        # The LAST transform of h_pred — a regime-routed residual correction:
        # h_pred = h_pred + (w0·expert0(h_pred) + w1·expert1(h_pred)). Routed by
        # regime_prior so POSITIONING/PRICE STATE selects the functional form
        # (momentum-expert vs reversion-expert). ZERO-INIT experts => moe_out==0
        # at init => h_pred UNCHANGED => bit-identical to the use_regime_moe=False
        # baseline (the non-negotiable zero-init guard, proven in tests). The
        # load-balance aux loss is stashed on regime_moe._last_lb_loss and surfaced
        # to the trainer in forward() as out["moe_lb_loss"]. Requires regime_prior;
        # if absent the MoE is skipped (no descriptor to route on).
        if self.regime_moe is not None and regime_prior is not None:
            h_pred = self.regime_moe(h_pred, regime_prior)

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
        # D1 FLAG-11 fix: frozen-normalise the WHOLE regime_prior ONCE, up front,
        # so every downstream consumer (film_multistage gates, regime_bias, the
        # fixed-state pooled-h FiLM concat, and the output gain below) sees the
        # SAME train-window-normalised prior instead of the raw, drifting scale.
        # Identity passthrough until fitted; zero-init gates make it a no-op at init.
        if getattr(self, "use_fixed_regime_state", False) and regime_prior is not None:
            regime_prior = self._normalize_prior(regime_prior)

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
            self._x_feat_pre_revin = None

        # --- MULTI-HORIZON regime gate on the AUX-horizon head slice ----------
        # Resolve the diagnosed lever conflict (y_180 aux helps STRONG, hurts
        # WEAK by competing with primary y_600) by scaling the AUX-horizon head
        # contribution by a learnable regime gate g_mh ∈ (0,1) BEFORE the trainer
        # reads quantiles_by_horizon / point_pred_by_horizon for the per-horizon
        # loss (_multi_horizon_loss slices q_by_h[:, h_idx, :]). The model learns
        # g_mh→~1 in strong (aux active) and g_mh→~0 in weak (aux suppressed).
        #
        # ONLY the NON-PRIMARY (aux) horizon slices are scaled. The PRIMARY y_600
        # slice (index self.primary_horizon_idx = n_horizons-1) is left BYTE-
        # IDENTICAL — the non-negotiable guard. The top-level out["quantiles"] /
        # out["point_pred"] expose horizon_idx, which the trainer sets to the
        # primary index (primary_horizon_idx), so the eval/checkpoint metrics are
        # ALSO untouched. We re-derive the top-level slices from the (possibly
        # gated) by-horizon tensors so every consumer stays coherent.
        # Zero-init mh_gate => g_mh==0.5 at init: the aux slice is scaled by 0.5
        # at init (acceptable — it is AUX), the primary slice is bit-identical.
        if (
            self.use_regime_gated_mh
            and self.mh_gate is not None
            and regime_prior is not None
            and "quantiles_by_horizon" in out
        ):
            q_by_h = out["quantiles_by_horizon"]                 # (B, n_h, 3)
            p_by_h = out["point_pred_by_horizon"]                # (B, n_h)
            n_h = q_by_h.shape[1]
            p_idx = int(self.primary_horizon_idx)
            g_mh = torch.sigmoid(self.mh_gate(regime_prior))     # (B, 1) in (0,1)
            self._last_g_mh = g_mh.detach()
            # Build a per-horizon scale: 1.0 on the primary slice (untouched),
            # g_mh on every aux slice. Vectorised, no in-place on the primary.
            scale = torch.ones(
                q_by_h.shape[0], n_h, device=q_by_h.device, dtype=q_by_h.dtype)
            for h in range(n_h):
                if h != p_idx:
                    scale[:, h] = g_mh.squeeze(-1).to(q_by_h.dtype)
            q_by_h = q_by_h * scale.unsqueeze(-1)                # (B, n_h, 3)
            p_by_h = p_by_h * scale                              # (B, n_h)
            out["quantiles_by_horizon"] = q_by_h
            out["point_pred_by_horizon"] = p_by_h
            # Re-derive top-level slices (horizon_idx == primary at train/eval =>
            # the primary slice => these stay bit-identical to the ungated model).
            out["quantiles"] = q_by_h[:, horizon_idx, :]
            out["point_pred"] = p_by_h[:, horizon_idx]
        else:
            self._last_g_mh = None

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

        # --- conditioned output gain (zero-init => exact ×1 no-op at init) ----
        # Multiply the FINAL quantile outputs by g(prior) = 1 + 0.5·tanh(zero-init
        # linear(prior_norm)) ∈ (0.5, 1.5). Applied AFTER snapshot/mh so it scales
        # the true head output. Uses the frozen-normalised regime_prior. At init
        # g==1 exactly (W,b zero) so this is a bit-exact no-op; training learns to
        # SHRINK scale in stale/drift regimes (the H1 overconfidence fix).
        if (
            self.use_output_gain
            and self.output_gain is not None
            and regime_prior is not None
        ):
            g = 1.0 + 0.5 * torch.tanh(self.output_gain(regime_prior))  # (B, 1)
            if "quantiles_by_horizon" in out:
                q_by_h = out["quantiles_by_horizon"]                   # (B, n_h, 3)
                q_by_h = q_by_h * g.unsqueeze(1)
                out["quantiles_by_horizon"] = q_by_h
                out["point_pred_by_horizon"] = q_by_h[:, :, 1]
                out["quantiles"] = q_by_h[:, horizon_idx, :]
                out["point_pred"] = q_by_h[:, horizon_idx, 1]
            else:
                out["quantiles"] = out["quantiles"] * g
                out["point_pred"] = out["point_pred"] * g.squeeze(-1)

        # --- regime-MoE load-balancing aux loss (guard #4) -------------------
        # Surface the CV^2-of-batch-mean-router-weights aux loss computed during
        # this forward (stashed on regime_moe._last_lb_loss inside _encode_tail)
        # so the trainer MAY add moe_lb_weight·moe_lb_loss to the objective
        # (encourages both experts to be used). The trainer is free to ignore
        # this key — the zero-init experts + heavy weight-decay guard against
        # overfit regardless. moe_lb_weight is exposed as a model attribute so
        # the trainer can read the recommended (~0.01) coefficient.
        if self.regime_moe is not None and self.regime_moe._last_lb_loss is not None:
            out["moe_lb_loss"] = self.regime_moe._last_lb_loss
            out["moe_lb_weight"] = torch.as_tensor(
                self.moe_lb_weight, device=out["point_pred"].device)
        return out

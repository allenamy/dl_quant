"""DualPathLOBModelV3: Conv + Attention temporal backbone.

Extends V2 with patched causal self-attention for long-range temporal
dependencies, optional cross-asset attention, and multi-horizon support.

Architecture:
  === Input Processing (from V2, updated) ===
  Path A: X_feat (B, L, n_feat) -> MaskNet -> GDCN -> Linear -> h_craft
  Path B: X_raw (B, L, n_levels, 4) -> RawLOBEncoder -> h_raw
  Fusion: concat(h_craft, h_raw) -> Linear -> h (B, L, d_model)

  === NEW: Temporal Backbone (Conv + Attention hybrid, Conformer-inspired) ===
  Step 1 -- Dilated CausalConv x3 (dilation 1,2,4, RF=15)  [local patterns]
  Step 2 -- Patching: (B, L, d) -> (B, n_patches, d_model)  [reduce seq len]
  Step 3 -- Causal Self-Attention on patches               [global patterns]
  Step 4 -- Extract last patch token: h_pred = h[:, -1, :]

  === Optional: Cross-Asset Attention ===
  Stack per-symbol h_pred tokens -> cross-attention -> extract target

  === Output (from V2, unchanged) ===
  PPNet Gate -> MonotonicQuantileHead -> {q10, q50, q90}

  === Multi-Horizon Support ===
  Shared encoder + per-horizon MonotonicQuantileHead

References:
  - PatchTST (ICLR 2023): Patching for efficient attention
  - TLOB (Feb 2025): Dual attention for LOB, single head suffices
  - Conformer (2020): Conv before attention is optimal
  - PMformer (2024): Cross-asset attention on BTC+ETH
  - DLP-KDD 2021: MaskNet for noise suppression
  - CIKM 2023: GDCN gated feature crossing
  - KDD 2023: PPNet regime gate

Parameter budget: ~35-45K total (V2 is ~29K, attention adds ~8K).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import torch
import torch.nn as nn

from src.model.masknet import MaskNet
from src.model.gdcn import GDCN
from src.model.raw_lob_encoder import RawLOBEncoder
from src.model.dual_path_model import CausalConv1dBlock
from src.model.patch_attention import PatchEmbedding, CausalPatchAttention
from src.model.cross_asset import CrossAssetAttention
from src.model.ppnet_gate import PPNetGate
from src.model.monotonic_quantile import MonotonicQuantileHead
from src.model.attention_pool import AttentionPool1D


class RevIN(nn.Module):
    """Reversible Instance Normalization (Kim et al., ICLR 2022).

    Normalizes each input instance (window) by its own mean/std.
    This addresses non-stationarity: features from different market
    regimes become comparable after per-instance normalization.

    For return prediction, RevIN is applied to INPUT features only.
    The output (predicted return) should NOT be denormalized because
    returns are already stationary targets.

    Parameters
    ----------
    n_features : int
        Number of features in the last dimension of the input.
    eps : float
        Small constant for numerical stability in std computation.
    affine : bool
        If True, learn per-feature scale (weight) and shift (bias)
        after normalization.
    """

    def __init__(self, n_features: int, eps: float = 1e-5, affine: bool = True):
        super().__init__()
        self.eps = eps
        if affine:
            self.affine_weight = nn.Parameter(torch.ones(n_features))
            self.affine_bias = nn.Parameter(torch.zeros(n_features))
        else:
            self.affine_weight = None
            self.affine_bias = None

    def normalize(self, x: torch.Tensor) -> torch.Tensor:
        """Normalize input per-instance.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, L, F)`` -- input features.

        Returns
        -------
        torch.Tensor
            Shape ``(B, L, F)`` -- normalized features.
        """
        self._mean = x.mean(dim=1, keepdim=True)  # (B, 1, F)
        self._std = x.std(dim=1, keepdim=True) + self.eps  # (B, 1, F)
        x_norm = (x - self._mean) / self._std
        if self.affine_weight is not None:
            x_norm = x_norm * self.affine_weight + self.affine_bias
        return x_norm

    def denormalize(self, x: torch.Tensor) -> torch.Tensor:
        """Reverse the normalization on model output.

        NOTE: For return prediction, this method is NOT called because
        the target (return) is already stationary. This method exists
        for completeness and potential future use in feature-space
        prediction tasks.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, F')`` or ``(B, L, F')`` -- output to denormalize.

        Returns
        -------
        torch.Tensor
            Denormalized output in the original feature scale.
        """
        if self.affine_weight is not None:
            x = (x - self.affine_bias) / (self.affine_weight + self.eps)
        return x * self._std[:, 0, :x.shape[-1]] + self._mean[:, 0, :x.shape[-1]]


class DualPathLOBModelV3(nn.Module):
    """Complete model with Conv + Attention temporal backbone.

    Integrates all proven components:
    - MaskNet (noise suppression, DLP-KDD 2021)
    - GDCN (gated feature crossing, CIKM 2023)
    - RawLOBEncoder (spatial Conv, DeepLOB/TLOB inspired)
    - Dilated CausalConv (local temporal, Conformer pattern)
    - Patched Causal Self-Attention (global temporal, PatchTST inspired)
    - PPNet Gate (regime conditioning, KDD 2023)
    - MonotonicQuantileHead (structural q10 < q50 < q90)
    - CrossAssetAttention (optional, PMformer inspired)
    - Multi-horizon support (optional, shared encoder + per-horizon heads)

    Parameters
    ----------
    n_features : int
        Number of hand-crafted input features per timestep.
    n_levels : int
        Number of LOB levels for the raw tensor (Path B).
    d_model : int
        Hidden dimension for Path A and the fused representation.
    d_raw : int
        Output dimension of the RawLOBEncoder (Path B).
    n_mask_blocks : int
        Number of serial MaskBlocks for noise suppression.
    n_cross_layers : int
        Number of GDCN gated cross layers.
    patch_size : int
        Number of timesteps per patch for the attention layer.
    attn_nhead : int
        Number of attention heads in the causal self-attention.
    attn_d_ff : int
        Feed-forward hidden dimension in the attention block.
    d_prior : int
        Dimensionality of regime prior features (default 6).
        Set to 0 to disable PPNet gate entirely.
    dropout : float
        Dropout probability.
    n_horizons : int
        Number of prediction horizons. Each gets a separate quantile head.
        Default 1 (single horizon, backward compatible).
    n_symbols : int
        Number of symbols for cross-asset attention.
        Default 1 (single symbol, cross-asset disabled).
    use_monotonic_quantile : bool
        If True, use MonotonicQuantileHead (structurally monotonic).
        If False, use simple Linear quantile head.
    """

    def __init__(
        self,
        n_features: int = 52,
        n_levels: int = 20,
        d_model: int = 32,
        d_raw: int = 16,
        n_mask_blocks: int = 2,
        n_cross_layers: int = 2,
        patch_size: int = 8,
        attn_nhead: int = 4,
        attn_d_ff: int = 64,
        d_prior: int = 6,
        dropout: float = 0.15,
        n_horizons: int = 1,
        n_symbols: int = 1,
        use_monotonic_quantile: bool = True,
        # --- Ablation bypass flags (Phase A2) ---------------------------
        # Each flag disables the corresponding module at ``forward`` time
        # without changing construction-time shapes, so checkpoints remain
        # compatible across ablations.  ``use_raw_path=False`` forces the
        # Path-A-only branch even when ``x_raw`` is supplied.
        use_masknet: bool = True,
        use_gdcn: bool = True,
        use_raw_path: bool = True,
        use_attention: bool = True,
        use_conv: bool = True,
        # --- RevIN (Phase A3 non-stationarity mitigation) ------------------
        use_revin: bool = True,
        # --- V4 additions (default True) ---------------------------------
        use_channel_mix_conv: bool = True,
        use_level_attention_pool: bool = True,
        use_patch_attention_pool: bool = True,
        use_ppnet_gate: bool = True,
        # --- Y600 push: multi-scale feature augmentation ---------------
        # Computes 60/180/600s scale features from x_raw (raw LOB),
        # injects as residual after Path A+B fusion. Targets feature-
        # horizon mismatch (existing X tops out at RV_300s while y_600
        # horizon is 600s). 18 new features (6 per scale × 3 scales).
        use_multi_scale: bool = False,
        # --- Y1800: pluggable temporal backbone (replaces conv+last-ts) ----
        # Default ``conv_lasts`` keeps the inline V4 temporal_conv path
        # for back-compat (existing checkpoints round-trip). Other values
        # (``ema_pool`` | ``gru`` | ``mamba``) bypass the inline conv
        # and use a dedicated backbone module instead.
        backbone_kind: str = "conv_lasts",
        backbone_kwargs: Optional[Dict[str, Any]] = None,
        # --- Phase A2: dual-path fusion variant ----------------------------
        # "concat" (default) = legacy concat+Linear; "glu" = gated linear unit
        # (data-dependent per-channel mixing of Path A vs Path B). Same param
        # budget, more expressive at no capacity cost.
        fusion_kind: str = "concat",
        # --- Y1800 Phase 1.2: in-graph σ-anchor scale layer ----------------
        # Learnable scalar α multiplied into all quantile/point outputs at
        # the end of forward. Allows the model to learn the post-hoc β
        # scaling factor jointly with the rest of the network — backbone
        # gradients see the scaled output. Set to None to disable.
        output_scale_init: Optional[float] = None,
        # --- Regime-aware FiLM modulation (anti-pattern #15 mitigation) ----
        # Applied to backbone output before quantile head. When True, a
        # RegimeFeatureExtractor + FiLM layer modulates h_pred based on
        # detected vol regime, attacking val→test drift driven by regime
        # shift. See src/model/regime_film.py for mechanism.
        use_regime_film: bool = False,
        regime_film_hidden: int = 16,
        # --- Regime additive bias head (Phase B.1, 2026-05-05) ---------------
        # Feature audit (Y600_REGIME_FEATURE_AUDIT.md) showed 19 features
        # carry regime info (max |corr|=0.14 with next-30d y_mean) AND past
        # 30d y_mean has +0.32 corr with next 30d, but model output was
        # regime-anti-correlated (-0.21). Root cause: PPNetGate is
        # multiplicative-only, can't shift baseline.
        #
        # `regime_bias_head` is an MLP(d_prior → 16 → n_horizons) that
        # outputs an additive scalar (per horizon), added uniformly to
        # q10/q50/q90 (preserves monotonicity since adding constant doesn't
        # change ordering). regime_prior fed as input (already 6-dim, has
        # rp_5 |corr|=0.11, rp_0 |corr|=0.105 with future regime).
        use_regime_bias: bool = False,
        regime_bias_hidden: int = 16,
        # --- v5push Phase 3: classification head for DirAcc ----------------
        # Adds nn.Linear(d_model, 1) sign head. Output `sign_logit` returned
        # in forward dict for trainer to compute BCE on sign(y). Designed for
        # DirAcc-focused training without hurting q50 magnitude prediction.
        # Risk: anti-pattern #10 multi-task gradient conflict — keep λ_cls small.
        use_sign_head: bool = False,
        # --- v5push Phase 3 (2026-05-12): Direction-Aware Quantile Head ---
        # Replaces MonotonicQuantileHead with DAQH (q50 = tanh(s) × softplus(m)).
        # Structurally decouples sign from magnitude → BCE on sign_logit
        # supervises direction without conflicting with magnitude regression.
        # Requires use_monotonic_quantile=True (DAQH IS a monotonic head).
        # Mutually exclusive with use_sign_head (DAQH provides sign_logit natively).
        use_direction_aware_head: bool = False,
        # --- v5push Phase 3 Track REG_arch: FiLM Multi-Stage Gating --------
        # When True, replace single-stage PPNetGate at output with 3-stage FiLM:
        # (a) after Conformer block 1, (b) after block 2, (c) on pooled h_pred.
        # FiLM = γ⊙h + β (γ init 1.0, β init 0.0 → identity at start).
        # Strictly more expressive than PPNetGate (γ-only, no shift).
        # Only effective when backbone_kind == "conformer".
        use_film_multistage: bool = False,
        # --- v5push Phase 3 Track REG_arch_v2: Time-Varying FiLM ------------
        # When True, ADD per-timestep TV-conditioned FiLM gate after each
        # Conformer block (in addition to per-sample regime FiLM).
        # Uses TV channels (last K dims of x_feat = n_features - 64) as
        # per-timestep gate input. Captures intra-window regime evolution.
        # Requires use_film_multistage=True (stacks on top of regime gates).
        use_tv_film: bool = False,
        # Number of TV channels (= K, last K of x_feat is TV). If None, infer
        # from n_features - 64 (Path A is fixed 64). Set explicitly if Path A
        # dim differs.
        n_tv_channels: int = 0,
        # --- v5push Phase 3 Track REG_arch_v3: Cross-Attention regime gate --
        # When True, replace FiLM gates with multi-head cross-attention regime
        # gates (regime as K/V, h as Q). More expressive than per-channel FiLM.
        # Requires use_film_multistage=True (replaces FiLM stages).
        use_xattn_regime: bool = False,
        # --- v5push Phase 3 Track REG_arch_v5: Sequence-level direction BCE --
        # When True, add per-timestep direction head over the pre-pool sequence.
        # Trainer samples at anchor positions and computes BCE against sign(y_600).
        # Goal: deep supervision improves DA via auxiliary direction loss at
        # multiple temporal positions (not just final pooled output).
        # Requires use_film_multistage OR use_xattn_regime (needs sequence access).
        use_seq_direction_head: bool = False,
        # --- v5push Phase 3 Track REG_arch_v6a: Deeper FiLM trunk ----------
        # When True, FiLMGate uses 2-layer trunk (Linear→GELU→Dropout→Linear→
        # GELU→Dropout) instead of 1-layer. Lets regime info learn non-linear
        # embedding before γ/β projection. +~3K params total (3 gates).
        film_gate_deeper_trunk: bool = False,
        # --- v5push Track A1 (2026-05-15): SE-block on X input ---------------
        # Per-sample channel re-weighting on input X (B, T, n_features) BEFORE
        # masknet/gdcn/input_proj. Does NOT add channels. Identity-friendly
        # init (sigmoid(+5)≈1). Bottom-up architectural surgical change.
        use_se_block_input: bool = False,
        # --- v5push Phase 3 Track P: Decoupled Sign + Magnitude Head ------
        # Refines DAQH by removing tanh × softplus coupling. Sign head trained
        # purely by BCE, magnitude head trained on Huber(|y|) with focal weight.
        # Exposes `magnitude_abs` output for separate Huber loss in trainer.
        # Mutually exclusive with use_direction_aware_head / use_sign_head.
        use_decoupled_sign_mag_head: bool = False,
        # --- v5push Phase 3 Track E: Multi-Resolution Temporal Pool -------
        # When True, conformer backbone returns full sequence (B, T, d_model)
        # and a MultiResolutionPool aggregates over recent (60s) + mid (300s)
        # + long (full) windows. Captures multi-timescale dependencies that
        # the default last-timestep slice loses. Only effective when
        # backbone_kind == "conformer". Off by default (V5 prod unchanged).
        use_multi_res_pool: bool = False,
        multi_res_recent: int = 60,
        multi_res_mid: int = 300,
    ):
        super().__init__()
        self.d_model = d_model
        self.d_raw = d_raw
        self.patch_size = patch_size
        self.n_horizons = n_horizons
        self.n_symbols = n_symbols
        self.use_monotonic_quantile = use_monotonic_quantile
        # Save construction-time scalars so the checkpoint loader can
        # reinstantiate the class without guessing shapes from keys.
        self.n_features = n_features
        self.n_levels = n_levels
        self.n_mask_blocks = n_mask_blocks
        self.n_cross_layers = n_cross_layers
        self.attn_nhead = attn_nhead
        self.attn_d_ff = attn_d_ff
        self.d_prior = d_prior
        self.dropout = dropout
        # Persist ablation flags so checkpoints round-trip through
        # ``_extract_model_config`` and so ``forward`` can gate on them.
        self.use_masknet = bool(use_masknet)
        self.use_gdcn = bool(use_gdcn)
        self.use_raw_path = bool(use_raw_path)
        self.use_attention = bool(use_attention)
        self.use_conv = bool(use_conv)
        # RevIN flag (Kim et al., ICLR 2022) -- per-instance normalization
        # of input features to handle cross-day non-stationarity (PSI=0.349).
        self.use_revin = bool(use_revin)
        # V4 flags
        self.use_channel_mix_conv = bool(use_channel_mix_conv)
        self.use_level_attention_pool = bool(use_level_attention_pool)
        self.use_patch_attention_pool = bool(use_patch_attention_pool)
        self.use_ppnet_gate = bool(use_ppnet_gate)
        # Multi-scale flag (Y600 push)
        self.use_multi_scale = bool(use_multi_scale)
        if self.use_multi_scale:
            from .multi_scale_features import MultiScaleRawAugment
            self.multi_scale_aug = MultiScaleRawAugment(scales=(60, 180, 600))
            n_ms = self.multi_scale_aug.n_out
            # Per-sample layer-norm on augmented features (scales differ by
            # orders of magnitude) and small MLP projection to d_model.
            self.ms_norm = nn.LayerNorm(n_ms)
            self.ms_encoder = nn.Sequential(
                nn.Linear(n_ms, d_model * 2),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model * 2, d_model),
            )
        if self.use_revin:
            self.revin = RevIN(n_features, affine=True)

        # --- v5push Track A1 (2026-05-15): SE-block input-channel attention --
        self.use_se_block_input = bool(use_se_block_input)
        if self.use_se_block_input:
            from src.model.se_block import SEBlock
            self.se_block_input = SEBlock(n_features=n_features, reduction=4, init_open=True)
        else:
            self.se_block_input = None

        # --- Path A: hand-crafted features -----------------------------------
        # MaskNet + GDCN operate in full feature space (n_features-dim) BEFORE
        # projection to d_model.  This preserves GDCN's theoretical advantage:
        # gated crossing on raw features, not on a compressed representation.
        self.masknet = MaskNet(
            d_input=n_features,
            d_hidden=n_features,
            n_blocks=n_mask_blocks,
            dropout=dropout,
        )
        self.gdcn = GDCN(
            d_input=n_features,
            n_layers=n_cross_layers,
            dropout=dropout,
        )
        # Project AFTER interaction: n_features -> d_model
        self.input_proj = nn.Linear(n_features, d_model)

        # --- Path B: raw LOB tensor ------------------------------------------
        self.raw_encoder = RawLOBEncoder(
            n_levels=n_levels,
            d_raw=d_raw,
            dropout=dropout,
            use_channel_mix_conv=self.use_channel_mix_conv,
            use_level_attention_pool=self.use_level_attention_pool,
        )

        # --- Fusion: concat -> Linear (default) or GLU gated fusion --------
        self.fusion_kind = str(fusion_kind or "concat")
        if self.fusion_kind == "concat":
            self.fusion = nn.Linear(d_model + d_raw, d_model)
        elif self.fusion_kind == "glu":
            from src.model.gated_fusion import GatedFusion
            self.fusion = GatedFusion(d_a=d_model, d_b=d_raw, d_out=d_model, dropout=dropout)
        elif self.fusion_kind == "late":
            self.fusion = None  # late fusion: backbone handles per-path temporal
        else:
            raise ValueError(f"unknown fusion_kind={self.fusion_kind!r}, expected concat, glu, or late")

        # --- Temporal: Dilated CausalConv (local patterns) -------------------
        # Dilation [1, 2, 4] with kernel=3 gives RF = 15 steps
        self.temporal_conv = nn.Sequential(
            CausalConv1dBlock(d_model, kernel_size=3, dilation=1, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=2, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=4, dropout=dropout),
        )

        # --- Pluggable backbone (Y1800 push) -------------------------------
        # When backbone_kind != "conv_lasts" we route the post-fusion h
        # through a dedicated backbone module instead of the inline
        # temporal_conv + last-timestep slice. The inline temporal_conv
        # is kept as an attribute for back-compat (old V4 checkpoints
        # have those keys) but not invoked when an alt backbone is chosen.
        # σ-anchor learnable output scale (Phase 1.2). Initialised to 1.0
        # (no-op at start). Optimizer learns α to satisfy β_calib loss.
        # When None, the layer is absent — back-compat with all prior runs.
        if output_scale_init is not None:
            self.output_scale = nn.Parameter(
                torch.tensor(float(output_scale_init), dtype=torch.float32)
            )
        else:
            self.output_scale = None

        # Regime-aware FiLM modulation (anti-pattern #15 mitigation).
        self.use_regime_film = bool(use_regime_film)
        if self.use_regime_film:
            from src.model.regime_film import RegimeFeatureExtractor, FiLM
            self.regime_extractor = RegimeFeatureExtractor()
            self.regime_film = FiLM(
                d_model=d_model,
                n_regime_feats=self.regime_extractor.n_features_out,
                hidden=int(regime_film_hidden),
                dropout=dropout,
            )
        else:
            self.regime_extractor = None
            self.regime_film = None

        self.backbone_kind = str(backbone_kind or "conv_lasts")
        self.backbone_kwargs = dict(backbone_kwargs or {})
        if self.backbone_kind == "conv_lasts":
            # Inline path is the default — no extra module to construct.
            self.backbone: Optional[nn.Module] = None
        elif self.backbone_kind == "ema_pool":
            from src.model.backbones.ema_pool_backbone import EMAPoolBackbone
            self.backbone = EMAPoolBackbone(
                d_model=d_model,
                dropout=dropout,
                decay=float(self.backbone_kwargs.get("decay", 0.95)),
            )
        elif self.backbone_kind == "gru":
            from src.model.backbones.gru_backbone import GRUBackbone
            self.backbone = GRUBackbone(
                d_model=d_model,
                hidden=int(self.backbone_kwargs.get("hidden", d_model)),
                n_layers=int(self.backbone_kwargs.get("n_layers", 1)),
                dropout=dropout,
            )
        elif self.backbone_kind == 'conv_deep':
            from src.model.backbones.conv_deep_backbone import ConvDeepBackbone
            self.backbone = ConvDeepBackbone(
                d_model=d_model, dropout=dropout,
                dilations=tuple(self.backbone_kwargs.get('dilations', (1, 2, 4, 8, 16))),
                kernel_size=int(self.backbone_kwargs.get('kernel_size', 3)),
                pool=self.backbone_kwargs.get('pool', 'last'),
            )
        elif self.backbone_kind == "late_fusion":
            from src.model.backbones.late_fusion_backbone import LateFusionBackbone
            self.backbone = LateFusionBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                dilations_craft=tuple(self.backbone_kwargs.get('dilations_craft', (1, 2, 4, 8))),
                dilations_raw=tuple(self.backbone_kwargs.get('dilations_raw', (1, 2, 4, 8))),
                kernel_size=int(self.backbone_kwargs.get('kernel_size', 3)),
                dropout=dropout,
                pool_kind=self.backbone_kwargs.get('pool_kind', 'last'),
            )
            self.fusion_kind = 'late'  # auto-set
            self.fusion = None
        elif self.backbone_kind == "late_fusion_mamba":
            from src.model.backbones.late_fusion_mamba_backbone import LateFusionMambaBackbone
            self.backbone = LateFusionMambaBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                d_state=int(self.backbone_kwargs.get('d_state', 16)),
                d_conv=int(self.backbone_kwargs.get('d_conv', 4)),
                expand=int(self.backbone_kwargs.get('expand', 2)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "conformer":
            from src.model.backbones.conformer_backbone import ConformerBackbone
            self.backbone = ConformerBackbone(
                d_model=d_model,
                n_blocks=int(self.backbone_kwargs.get('n_blocks', 2)),
                n_heads=int(self.backbone_kwargs.get('n_heads', 2)),
                kernel_size=int(self.backbone_kwargs.get('kernel_size', 15)),
                dropout=dropout,
            )
            # Track E: route through MRP when requested
            self.use_multi_res_pool = bool(use_multi_res_pool)
            if self.use_multi_res_pool:
                self.backbone.return_sequence = True
                from src.model.multi_resolution_pool import MultiResolutionPool
                self.multi_res_pool = MultiResolutionPool(
                    d_model=d_model, T=int(self.backbone_kwargs.get('T', 600)),
                    recent_window=int(multi_res_recent),
                    mid_window=int(multi_res_mid),
                )
            else:
                self.multi_res_pool = None
            # Track REG_arch: FiLM multi-stage gating
            self.use_film_multistage = bool(use_film_multistage and d_prior > 0)
            if self.use_film_multistage:
                from src.model.film_gate import FiLMGate
                # FiLM gates after each Conformer block + after final pool.
                # block3 gate only instantiated when n_blocks >= 3 (Track REG_arch_v4).
                # v6a: pass film_gate_deeper_trunk through to FiLMGate (extra hidden layer).
                _deeper = bool(film_gate_deeper_trunk)
                self.film_gate_block1 = FiLMGate(d_prior=d_prior, d_hidden=d_model, dropout=dropout, deeper_trunk=_deeper)
                self.film_gate_block2 = FiLMGate(d_prior=d_prior, d_hidden=d_model, dropout=dropout, deeper_trunk=_deeper)
                _n_blocks = int(self.backbone_kwargs.get('n_blocks', 2))
                if _n_blocks >= 3:
                    self.film_gate_block3 = FiLMGate(d_prior=d_prior, d_hidden=d_model, dropout=dropout, deeper_trunk=_deeper)
                else:
                    self.film_gate_block3 = None
                self.film_gate_final = FiLMGate(d_prior=d_prior, d_hidden=d_model, dropout=dropout, deeper_trunk=_deeper)
                # Force backbone to return sequence so we can gate intermediate blocks
                self.backbone.return_sequence = True
            else:
                self.film_gate_block1 = None
                self.film_gate_block2 = None
                self.film_gate_block3 = None
                self.film_gate_final = None
            # Track REG_arch_v2: Time-varying FiLM (per-timestep, conditioned on TV channels)
            self.use_tv_film = bool(use_tv_film and self.use_film_multistage and n_tv_channels > 0)
            self.n_tv_channels = int(n_tv_channels) if n_tv_channels > 0 else 0
            if self.use_tv_film:
                from src.model.tv_film_gate import TVFiLMGate
                # Two TV-conditioned FiLM gates: after block 1, after block 2
                # (skip on pooled h_pred since it's no longer per-timestep)
                self.tv_film_gate_block1 = TVFiLMGate(d_tv=self.n_tv_channels, d_hidden=d_model, dropout=dropout)
                self.tv_film_gate_block2 = TVFiLMGate(d_tv=self.n_tv_channels, d_hidden=d_model, dropout=dropout)
            else:
                self.tv_film_gate_block1 = None
                self.tv_film_gate_block2 = None
            # Track REG_arch_v3: Cross-attention regime gate (multi-head attention
            # where regime_prior is K/V, hidden h is Q). More expressive than FiLM's
            # per-channel affine. Three independent gates at the same 3 stages.
            self.use_xattn_regime = bool(use_xattn_regime and d_prior > 0)
            if self.use_xattn_regime:
                from src.model.cross_attn_regime_gate import CrossAttentionRegimeGate
                self.xattn_gate_block1 = CrossAttentionRegimeGate(
                    d_prior=d_prior, d_hidden=d_model, n_heads=2,
                    n_regime_tokens=4, dropout=dropout)
                self.xattn_gate_block2 = CrossAttentionRegimeGate(
                    d_prior=d_prior, d_hidden=d_model, n_heads=2,
                    n_regime_tokens=4, dropout=dropout)
                self.xattn_gate_final = CrossAttentionRegimeGate(
                    d_prior=d_prior, d_hidden=d_model, n_heads=2,
                    n_regime_tokens=4, dropout=dropout)
                # Force backbone to return sequence (same as FiLM multi-stage)
                self.backbone.return_sequence = True
            else:
                self.xattn_gate_block1 = None
                self.xattn_gate_block2 = None
                self.xattn_gate_final = None
            # Track REG_arch_v5: Sequence-level direction head (deep supervision)
            self.use_seq_direction_head = bool(
                use_seq_direction_head and (self.use_film_multistage or self.use_xattn_regime)
            )
            if self.use_seq_direction_head:
                self.seq_direction_head = nn.Linear(d_model, 1)
            else:
                self.seq_direction_head = None
        elif self.backbone_kind == "tsmixer":
            from src.model.backbones.tsmixer_backbone import TSMixerBackbone
            self.backbone = TSMixerBackbone(
                d_model=d_model,
                L=int(self.backbone_kwargs.get('L', 600)),
                n_blocks=int(self.backbone_kwargs.get('n_blocks', 4)),
                dropout=dropout,
            )
        elif self.backbone_kind == "late_fusion_attn":
            from src.model.backbones.late_fusion_attention_backbone import LateFusionAttentionBackbone
            self.backbone = LateFusionAttentionBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                n_heads=int(self.backbone_kwargs.get('n_heads', 2)),
                d_ff=int(self.backbone_kwargs.get('d_ff', 64)),
                n_blocks=int(self.backbone_kwargs.get('n_blocks', 1)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "cross_attn":
            from src.model.backbones.cross_attention_backbone import CrossAttentionBackbone
            self.backbone = CrossAttentionBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                n_heads=int(self.backbone_kwargs.get('n_heads', 2)),
                d_ff=int(self.backbone_kwargs.get('d_ff', 64)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "late_fusion_mamba_gated":
            from src.model.backbones.late_fusion_mamba_gated_backbone import LateFusionMambaGatedBackbone
            self.backbone = LateFusionMambaGatedBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                d_state=int(self.backbone_kwargs.get('d_state', 16)),
                d_conv=int(self.backbone_kwargs.get('d_conv', 4)),
                expand=int(self.backbone_kwargs.get('expand', 2)),
                reduction=int(self.backbone_kwargs.get('reduction', 4)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "dcn_mamba_parallel":
            from src.model.backbones.dcn_mamba_parallel_backbone import DcnMambaParallelBackbone
            self.backbone = DcnMambaParallelBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                d_state=int(self.backbone_kwargs.get('d_state', 16)),
                d_conv=int(self.backbone_kwargs.get('d_conv', 4)),
                expand=int(self.backbone_kwargs.get('expand', 2)),
                n_cross_layers=int(self.backbone_kwargs.get('n_cross_layers', 3)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "multi_extract_gated":
            from src.model.backbones.multi_extract_gated_backbone import MultiExtractGatedBackbone
            self.backbone = MultiExtractGatedBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                d_state=int(self.backbone_kwargs.get('d_state', 16)),
                d_conv=int(self.backbone_kwargs.get('d_conv', 4)),
                expand=int(self.backbone_kwargs.get('expand', 2)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "stack_tcn_gdcn":
            from src.model.backbones.stack_tcn_gdcn_backbone import StackTcnGdcnBackbone
            self.backbone = StackTcnGdcnBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                n_blocks=int(self.backbone_kwargs.get('n_blocks', 2)),
                kernel_size=int(self.backbone_kwargs.get('kernel_size', 3)),
                dilations=tuple(self.backbone_kwargs.get('dilations', (1, 4, 16))),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "mamba_gdcn_gated":
            from src.model.backbones.mamba_gdcn_gated_backbone import MambaGdcnGatedBackbone
            self.backbone = MambaGdcnGatedBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                d_state=int(self.backbone_kwargs.get('d_state', 16)),
                d_conv=int(self.backbone_kwargs.get('d_conv', 4)),
                expand=int(self.backbone_kwargs.get('expand', 2)),
                gdcn_layers=int(self.backbone_kwargs.get('gdcn_layers', 2)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "jamba_per_path":
            from src.model.backbones.jamba_per_path_backbone import JambaPerPathBackbone
            self.backbone = JambaPerPathBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                n_blocks=int(self.backbone_kwargs.get('n_blocks', 2)),
                n_heads=int(self.backbone_kwargs.get('n_heads', 2)),
                d_ff=int(self.backbone_kwargs.get('d_ff', 64)),
                d_state=int(self.backbone_kwargs.get('d_state', 16)),
                d_conv=int(self.backbone_kwargs.get('d_conv', 4)),
                expand=int(self.backbone_kwargs.get('expand', 2)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "fft_freq_block":
            from src.model.backbones.fft_freq_block_backbone import FftFreqBlockBackbone
            self.backbone = FftFreqBlockBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                n_blocks=int(self.backbone_kwargs.get('n_blocks', 2)),
                d_hidden=int(self.backbone_kwargs.get('d_hidden', 64)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "fibinet_bilinear":
            from src.model.backbones.fibinet_bilinear_backbone import FibiNetBilinearBackbone
            self.backbone = FibiNetBilinearBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                d_state=int(self.backbone_kwargs.get('d_state', 16)),
                d_conv=int(self.backbone_kwargs.get('d_conv', 4)),
                expand=int(self.backbone_kwargs.get('expand', 2)),
                d_bilinear=int(self.backbone_kwargs.get('d_bilinear', 16)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "late_fusion_attn_curriculum":
            from src.model.backbones.late_fusion_attn_curriculum_backbone import LateFusionAttnCurriculumBackbone
            self.backbone = LateFusionAttnCurriculumBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                n_heads=int(self.backbone_kwargs.get('n_heads', 2)),
                d_ff=int(self.backbone_kwargs.get('d_ff', 64)),
                n_blocks=int(self.backbone_kwargs.get('n_blocks', 1)),
                warmup_steps=int(self.backbone_kwargs.get('warmup_steps', 2000)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "mmoe_4exp":
            from src.model.backbones.mmoe_4exp_backbone import MMoE4ExpBackbone
            self.backbone = MMoE4ExpBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                n_experts=int(self.backbone_kwargs.get('n_experts', 4)),
                d_state=int(self.backbone_kwargs.get('d_state', 16)),
                d_conv=int(self.backbone_kwargs.get('d_conv', 4)),
                expand=int(self.backbone_kwargs.get('expand', 2)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "multi_rf_conformer":
            from src.model.backbones.multi_rf_conformer_backbone import MultiRfConformerBackbone
            self.backbone = MultiRfConformerBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                d_state=int(self.backbone_kwargs.get('d_state', 16)),
                d_conv=int(self.backbone_kwargs.get('d_conv', 4)),
                expand=int(self.backbone_kwargs.get('expand', 2)),
                n_conformer=int(self.backbone_kwargs.get('n_conformer', 2)),
                conv_kernel=int(self.backbone_kwargs.get('conv_kernel', 15)),
                n_heads=int(self.backbone_kwargs.get('n_heads', 2)),
                d_ff=int(self.backbone_kwargs.get('d_ff', 64)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "tsmixer_lite":
            from src.model.backbones.tsmixer_lite_backbone import TSMixerLiteBackbone
            self.backbone = TSMixerLiteBackbone(
                d_craft=d_model, d_raw=d_raw, d_out=d_model,
                L=int(self.backbone_kwargs.get('L', 600)),
                L_seg=int(self.backbone_kwargs.get('L_seg', 30)),
                n_blocks=int(self.backbone_kwargs.get('n_blocks', 4)),
                d_ff_t=int(self.backbone_kwargs.get('d_ff_t', 64)),
                d_ff_c=int(self.backbone_kwargs.get('d_ff_c', 64)),
                dropout=dropout,
            )
            self.fusion_kind = 'late'
            self.fusion = None
        elif self.backbone_kind == "mamba":
            from src.model.backbones.mamba_backbone_v2 import MambaBackboneV2
            self.backbone = MambaBackboneV2(
                d_model=d_model,
                d_state=int(self.backbone_kwargs.get("d_state", 16)),
                expand=int(self.backbone_kwargs.get("expand", 1)),
                dropout=dropout,
            )
        elif self.backbone_kind == "multi_scale":
            from src.model.backbones.multi_scale_backbone import MultiScaleBackbone
            self.backbone = MultiScaleBackbone(
                d_model=d_model,
                scales=tuple(self.backbone_kwargs.get("scales", (60, 300, 1200))),
                dropout=dropout,
                ema_decay=float(self.backbone_kwargs.get("ema_decay", 0.95)),
            )
        elif self.backbone_kind == "itransformer":
            from src.model.backbones.itransformer_backbone import ITransformerBackbone
            self.backbone = ITransformerBackbone(
                d_model=d_model,
                L=int(self.backbone_kwargs.get("L", 1200)),
                d_emb=int(self.backbone_kwargs.get("d_emb", 64)),
                n_heads=int(self.backbone_kwargs.get("n_heads", 4)),
                n_layers=int(self.backbone_kwargs.get("n_layers", 1)),
                d_ff=int(self.backbone_kwargs.get("d_ff", 128)),
                dropout=dropout,
            )
        elif self.backbone_kind == "moe":
            from src.model.backbones.moe_backbone import MoEBackbone
            self.backbone = MoEBackbone(
                d_model=d_model,
                n_experts=int(self.backbone_kwargs.get("n_experts", 4)),
                top_k=int(self.backbone_kwargs.get("top_k", 2)),
                expert_decay=float(self.backbone_kwargs.get("expert_decay", 0.9)),
                regime_dim=self.backbone_kwargs.get("regime_dim", None),
                router_hidden=int(self.backbone_kwargs.get("router_hidden", 32)),
                dropout=dropout,
                load_balance_aux_weight=float(
                    self.backbone_kwargs.get("load_balance_aux_weight", 0.01)
                ),
            )
        else:
            raise ValueError(
                f"unknown backbone_kind={self.backbone_kind!r}; "
                "expected one of: conv_lasts, ema_pool, gru, mamba, multi_scale, itransformer, moe"
            )

        # --- Patching + Causal Self-Attention (global patterns) --------------
        self.patch_embed = PatchEmbedding(
            d_model=d_model,
            patch_size=patch_size,
            max_patches=150,  # L=1200/P=8 = 150 patches (supports up to 20min@1s input)
        )
        self.patch_attention = CausalPatchAttention(
            d_model=d_model,
            nhead=attn_nhead,
            d_ff=attn_d_ff,
            dropout=dropout,
        )

        # Token-level attention pool over patches (V4). Alternative to the
        # V3 last-token slice after patch attention.
        if use_patch_attention_pool:
            self.token_pool: Optional[AttentionPool1D] = AttentionPool1D(
                d_model=d_model, input_is_last_dim=True
            )
        else:
            self.token_pool = None

        # --- Cross-Asset Attention (optional) --------------------------------
        if n_symbols > 1:
            self.cross_asset_attn: Optional[CrossAssetAttention] = CrossAssetAttention(
                d_model=d_model,
                nhead=2,
                dropout=dropout,
            )
        else:
            self.cross_asset_attn = None

        # --- PPNet Gate (optional) -------------------------------------------
        # PPNet Gate: constructed only if BOTH d_prior > 0 AND use_ppnet_gate.
        # use_ppnet_gate=False disables the gate even when d_prior > 0 for
        # ablation.
        if d_prior > 0 and use_ppnet_gate:
            self.ppnet_gate: Optional[PPNetGate] = PPNetGate(
                d_prior=d_prior,
                d_hidden=d_model,
                dropout=dropout,
            )
        else:
            self.ppnet_gate = None

        # --- Regime additive bias head (Phase B.1) ----------------------------
        # Outputs a per-horizon scalar bias added to q10/q50/q90 uniformly.
        # Preserves monotonicity (adding constant). Tiny: ~few hundred params.
        # Initialized so MLP output ≈ 0 at start (final Linear weight near zero)
        # to keep checkpoint compat for ablation runs (use_regime_bias=False).
        self.use_regime_bias = bool(use_regime_bias and d_prior > 0)
        if self.use_regime_bias:
            self.regime_bias_head = nn.Sequential(
                nn.Linear(d_prior, regime_bias_hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(regime_bias_hidden, n_horizons),
            )
            # Initialize last Linear weights to zero so initial bias ≈ 0
            # (model recovers identity behavior at training start)
            nn.init.zeros_(self.regime_bias_head[-1].weight)
            nn.init.zeros_(self.regime_bias_head[-1].bias)
        else:
            self.regime_bias_head = None

        # --- Quantile Heads (per-horizon) ------------------------------------
        self.use_decoupled_sign_mag_head = bool(use_decoupled_sign_mag_head)
        self.use_direction_aware_head = bool(use_direction_aware_head)
        if self.use_decoupled_sign_mag_head:
            # Track P: decoupled sign + magnitude (no tanh × softplus coupling).
            self.use_monotonic_quantile = True
            from src.model.decoupled_sign_mag_head import DecoupledSignMagHead
            self.quantile_heads = nn.ModuleList([
                DecoupledSignMagHead(
                    d_input=d_model, d_hidden=d_model, dropout=dropout,
                )
                for _ in range(n_horizons)
            ])
        elif self.use_direction_aware_head:
            # v5push Phase 3: sign + magnitude decomposed monotonic head.
            # Provides sign_logit output for explicit BCE supervision.
            # DAQH IS monotonic (q10<q50<q90 via softplus offsets), so we
            # force use_monotonic_quantile=True to route through the dict
            # head path in forward().
            self.use_monotonic_quantile = True
            from src.model.direction_aware_quantile_head import (
                DirectionAwareQuantileHead,
            )
            self.quantile_heads = nn.ModuleList([
                DirectionAwareQuantileHead(
                    d_input=d_model,
                    d_hidden=d_model,
                    dropout=dropout,
                )
                for _ in range(n_horizons)
            ])
        elif use_monotonic_quantile:
            self.quantile_heads = nn.ModuleList([
                MonotonicQuantileHead(
                    d_input=d_model,
                    d_hidden=d_model,
                    dropout=dropout,
                )
                for _ in range(n_horizons)
            ])
        else:
            self.quantile_heads = nn.ModuleList([
                nn.Sequential(
                    nn.Linear(d_model, d_model),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.Linear(d_model, 3),
                )
                for _ in range(n_horizons)
            ])

        # v5push (2026-05-12): optional binary classification head for DirAcc.
        # Predicts sign(y) directly via BCE on shared encoder.
        # Trainer reads `sign_logit` if present and adds λ_cls * BCE term.
        # Risk: anti-pattern #10 multi-task gradient conflict — keep λ_cls small.
        self.use_sign_head = bool(use_sign_head)
        if self.use_sign_head:
            self.sign_heads = nn.ModuleList([
                nn.Sequential(
                    nn.Linear(d_model, d_model),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.Linear(d_model, 1),
                )
                for _ in range(n_horizons)
            ])
            # Zero-init final layer so model starts at neutral 0.5 probability
            for head in self.sign_heads:
                nn.init.zeros_(head[-1].weight)
                nn.init.zeros_(head[-1].bias)
        else:
            self.sign_heads = None

    def encode(
        self,
        x_feat: torch.Tensor,
        x_raw: torch.Tensor | None = None,
        regime_prior: torch.Tensor | None = None,
        cross_asset_feats: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Encode inputs into pooled embedding ``h_pred`` (pre-head).

        Runs every preprocessing / temporal / regime stage of ``forward``
        EXCEPT the final quantile head and ``output_scale`` post-multiply.
        Returned tensor is the same ``h_pred`` value the legacy ``forward``
        used to feed ``self.quantile_heads[...]``.

        This refactor enables V5 (and future heads) to reuse V4's proven
        encoder without re-running quantile prediction. ``forward`` calls
        ``encode`` then applies ``self.quantile_heads`` + ``output_scale``,
        so behaviour is bit-identical pre/post refactor.

        Parameters
        ----------
        x_feat : torch.Tensor
            Shape ``(B, L, n_features)`` -- hand-crafted features.
        x_raw : torch.Tensor | None
            Shape ``(B, L, n_levels, 4)`` -- raw LOB tensor, or ``None``
            for Path-A-only mode.
        regime_prior : torch.Tensor | None
            Shape ``(B, d_prior)`` -- regime prior features for PPNet gate.
            If ``None``, PPNet gate is bypassed (identity).
        cross_asset_feats : torch.Tensor | None
            Shape ``(B, n_symbols-1, d_model)`` -- other symbols' h_pred
            tokens. If ``None``, cross-asset attention is skipped.

        Returns
        -------
        torch.Tensor
            Shape ``(B, d_model)`` -- modulated, gated embedding ready for
            a head.
        """
        # 0. RevIN: per-instance normalization of input features (ICLR 2022).
        # Applied BEFORE any learned layers so that MaskNet/GDCN see
        # distribution-stable features regardless of market regime.
        # NOTE: RevIN normalizes INPUT features only.  The OUTPUT (predicted
        # return) is NOT denormalized because returns are already stationary
        # targets -- RevIN addresses feature non-stationarity, not target shift.
        if self.use_revin:
            x_feat = self.revin.normalize(x_feat)

        # v5push Track A1: SE-block input-channel attention (per-sample
        # channel re-weighting on existing X channels — NOT channel addition).
        # Default off → baseline behavior preserved.
        if self.se_block_input is not None:
            x_feat = self.se_block_input(x_feat)

        # 1. Path A: features -> MaskNet -> GDCN -> proj
        # Ablation flags ``use_masknet`` / ``use_gdcn`` skip the corresponding
        # interaction layer while preserving the n_features -> d_model shape
        # via ``input_proj`` at the end of Path A.
        if self.use_masknet:
            h_craft = self.masknet(x_feat)       # (B, L, n_features) -- noise suppressed
        else:
            h_craft = x_feat                     # (B, L, n_features)

        if self.use_gdcn:
            h_craft = self.gdcn(h_craft)         # (B, L, n_features) -- feature interactions

        h_craft = self.input_proj(h_craft)       # (B, L, d_model) -- project after interaction

        # 2. Path B: raw LOB tensor (optional)
        # ``use_raw_path`` gates Path B even when ``x_raw`` is supplied.  This
        # lets the ablation runner disable Path B while still feeding x_raw.
        if self.use_raw_path and x_raw is not None:
            h_raw = self.raw_encoder(x_raw)      # (B, L, d_raw)
            if self.fusion_kind == "late":
                h = None  # late fusion: backbone receives h_craft and h_raw separately
            elif self.fusion_kind == "glu":
                h = self.fusion(h_craft, h_raw)  # (B, L, d_model) gated
            else:
                h = torch.cat([h_craft, h_raw], dim=-1)  # (B, L, d_model + d_raw)
                h = self.fusion(h)               # (B, L, d_model) concat-linear
        else:
            h = h_craft                          # (B, L, d_model)

        # 2.5 Multi-scale feature augmentation (Y600 push).
        # Computes 60/180/600s scale microstructure features from x_raw and
        # injects as residual. Targets feature-horizon mismatch — existing
        # X tops out at RV_300s but y_600 horizon is 600s.
        if self.use_multi_scale and x_raw is not None:
            ms_feat = self.multi_scale_aug(x_raw.float())  # (B, L, 18)
            ms_feat = self.ms_norm(ms_feat)
            ms_h = self.ms_encoder(ms_feat)                # (B, L, d_model)
            h = h + ms_h                                    # residual inject

        # 3. Temporal backbone.
        # Default conv_lasts: inline temporal_conv (RF=15s) + last-timestep
        # slice (V4 behaviour, bit-identical when backbone_kind="conv_lasts").
        # Other backbones (ema_pool/gru/mamba) bypass the inline conv path.
        if self.backbone is not None:
            if self.fusion_kind == "late":
                h_pred = self.backbone(h_craft, h_raw)
            elif (getattr(self, 'use_film_multistage', False) or getattr(self, 'use_xattn_regime', False)) and regime_prior is not None:
                # Track REG_arch: manual iteration through conformer blocks
                # with FiLM gating between blocks (regime info reaches intermediate
                # representations, not only output).
                # Track REG_arch_v2: also apply TV-conditioned per-timestep gate.
                # Track REG_arch_v3: cross-attention gate (mutually exclusive with FiLM
                # in typical use; both supported if user wants stacked).
                tv_features = None
                if getattr(self, 'use_tv_film', False) and self.n_tv_channels > 0:
                    # Extract TV channels (last K of x_feat)
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
                        # Track REG_arch_v4: 3rd FiLM gate when n_blocks >= 3
                        if getattr(self, 'film_gate_block3', None) is not None:
                            h = self.film_gate_block3(h, regime_prior)
                # Track REG_arch_v5: capture sequence direction logits BEFORE pool
                # h shape: (B, T, d_model). Stash on instance for forward() to read
                # and add to outputs dict (encode signature unchanged for V5Model).
                if getattr(self, 'seq_direction_head', None) is not None:
                    self._last_seq_dir_logits = self.seq_direction_head(h).squeeze(-1)  # (B, T)
                else:
                    self._last_seq_dir_logits = None
                # MRP or last-token slice
                if getattr(self, 'multi_res_pool', None) is not None:
                    h_pred = self.multi_res_pool(h)
                else:
                    h_pred = h[:, -1, :]
                # Final FiLM gate (replaces PPNet at output) — per-sample only
                if self.film_gate_final is not None:
                    h_pred = self.film_gate_final(h_pred, regime_prior)
                if getattr(self, 'xattn_gate_final', None) is not None:
                    h_pred = self.xattn_gate_final(h_pred, regime_prior)
            else:
                h_pred = self.backbone(h)
                # Track E / FiLM: conformer in return_sequence mode → reduce
                if h_pred.dim() == 3:
                    if getattr(self, 'multi_res_pool', None) is not None:
                        h_pred = self.multi_res_pool(h_pred)
                    else:
                        h_pred = h_pred[:, -1, :]  # fallback last-token
        elif self.use_attention:
            # Legacy attention path (use_attention=True is V4 ablation; off in
            # baseline_plus). Patching + causal self-attention.
            if self.use_conv:
                h = self.temporal_conv(h)
            h = self.patch_embed(h)
            h = self.patch_attention(h)
            if self.use_patch_attention_pool and self.token_pool is not None:
                h_pred = self.token_pool(h)
            else:
                h_pred = h[:, -1, :]
        else:
            # Legacy V4 default: dilated causal conv + last-timestep slice.
            if self.use_conv:
                h = self.temporal_conv(h)
            h_pred = h[:, -1, :]

        # 7. Cross-asset attention (optional)
        if cross_asset_feats is not None and self.cross_asset_attn is not None:
            # Stack: target symbol + other symbols
            # h_pred: (B, d_model), cross_asset_feats: (B, n_symbols-1, d_model)
            all_symbols = torch.cat(
                [h_pred.unsqueeze(1), cross_asset_feats], dim=1
            )  # (B, n_symbols, d_model)
            all_symbols = self.cross_asset_attn(all_symbols)  # (B, n_symbols, d_model)
            h_pred = all_symbols[:, 0, :]  # extract target symbol

        # 8a. Regime-aware FiLM modulation (anti-pattern #15 mitigation).
        # Computed from input x_feat directly — provides regime-aware adaptation
        # of backbone output BEFORE PPNet/quantile head. Closed-form regime
        # extractor (no learned params) → no val-tunable degrees of freedom.
        if self.use_regime_film and self.regime_film is not None:
            regime_feats = self.regime_extractor(x_feat)               # (B, K)
            h_pred = self.regime_film(h_pred, regime_feats)            # (B, d_model)

        # 8. PPNet regime-conditioned gating
        # Skip when FiLM multistage active (avoids double gating — FiLM_final already applied)
        if regime_prior is not None and self.ppnet_gate is not None \
                and not getattr(self, 'use_film_multistage', False):
            h_pred = self.ppnet_gate(h_pred, regime_prior)

        return h_pred

    def forward(
        self,
        x_feat: torch.Tensor,
        x_raw: torch.Tensor | None = None,
        regime_prior: torch.Tensor | None = None,
        cross_asset_feats: torch.Tensor | None = None,
        horizon_idx: int = 0,
        all_horizons: bool = False,
    ) -> dict[str, torch.Tensor]:
        """Forward pass.

        Calls :meth:`encode` to produce ``h_pred`` then applies the quantile
        head(s) (and optional ``output_scale`` modulation). Behaviour is
        bit-identical to the pre-refactor monolithic forward — only the
        encoder body has been factored out into :meth:`encode` so V5 / future
        heads can reuse the proven preprocessing.

        Parameters
        ----------
        x_feat : torch.Tensor
            Shape ``(B, L, n_features)`` -- hand-crafted features.
        x_raw : torch.Tensor | None
            Shape ``(B, L, n_levels, 4)`` -- raw LOB tensor, or ``None``
            for Path-A-only mode.
        regime_prior : torch.Tensor | None
            Shape ``(B, d_prior)`` -- regime prior features for PPNet gate.
            If None, PPNet gate is bypassed (identity).
        cross_asset_feats : torch.Tensor | None
            Shape ``(B, n_symbols-1, d_model)`` -- other symbols' h_pred tokens.
            If None, cross-asset attention is skipped.
        horizon_idx : int
            Which horizon head to use (0-indexed).  Default 0.  Ignored when
            ``all_horizons=True`` or when ``n_horizons == 1``.
        all_horizons : bool
            When ``True`` AND ``n_horizons > 1``, run every quantile head in
            a single forward and return an extra ``quantiles_by_horizon``
            key (shape ``(B, n_horizons, 3)``) alongside the original
            ``quantiles`` / ``point_pred`` keys (selected via
            ``horizon_idx`` for back-compat).  Default ``False`` keeps
            legacy single-head behaviour.

        Returns
        -------
        dict[str, torch.Tensor]
            Always returned:
              - ``quantiles``: ``(B, 3)`` with [q10, q50, q90]
              - ``point_pred``: ``(B,)`` -- median prediction (q50)
            Additionally when ``n_horizons > 1`` and ``all_horizons=True``:
              - ``quantiles_by_horizon``: ``(B, n_horizons, 3)``
              - ``point_pred_by_horizon``: ``(B, n_horizons)``
        """
        h_pred = self.encode(
            x_feat=x_feat,
            x_raw=x_raw,
            regime_prior=regime_prior,
            cross_asset_feats=cross_asset_feats,
        )

        # 9. Quantile head (horizon-specific if multi-horizon).
        # ``all_horizons=True`` runs every head in one forward so the
        # multi-horizon trainer can apply per-horizon losses without
        # re-encoding the input.  ``n_horizons == 1`` short-circuits back to
        # the legacy single-head path regardless of ``all_horizons`` to keep
        # single-horizon checkpoints / training bit-identical.
        if self.n_horizons > 1 and all_horizons:
            q_list = []
            p_list = []
            for head in self.quantile_heads:
                if self.use_monotonic_quantile:
                    out = head(h_pred)
                    q_list.append(out["quantiles"])
                    p_list.append(out["point_pred"])
                else:
                    q = head(h_pred)
                    q_list.append(q)
                    p_list.append(q[:, 1])
            # Stack along the horizon axis: (B, n_horizons, n_quantiles)
            quantiles_by_h = torch.stack(q_list, dim=1)
            point_pred_by_h = torch.stack(p_list, dim=1)
            # Back-compat: top-level ``quantiles`` / ``point_pred`` expose the
            # caller-selected horizon (default 0) so anything that reads
            # outputs["quantiles"] (e.g. monitoring code) keeps working.
            return {
                "quantiles": quantiles_by_h[:, horizon_idx, :],
                "point_pred": point_pred_by_h[:, horizon_idx],
                "quantiles_by_horizon": quantiles_by_h,
                "point_pred_by_horizon": point_pred_by_h,
            }

        head = self.quantile_heads[horizon_idx]
        if self.use_monotonic_quantile:
            outputs = head(h_pred)
        else:
            quantiles = head(h_pred)
            outputs = {"quantiles": quantiles, "point_pred": quantiles[:, 1]}

        # Apply σ-anchor scale if enabled. Scales quantile outputs and
        # point pred by the learnable α. β_calib loss in compute_dul_loss
        # applies AFTER this scaling, so optimizer sees the scaled output.
        if self.output_scale is not None:
            alpha = self.output_scale
            outputs["quantiles"] = outputs["quantiles"] * alpha
            outputs["point_pred"] = outputs["point_pred"] * alpha

        # Phase B.1: Regime additive bias (preserves monotonicity).
        # Computed from regime_prior, added uniformly to q10/q50/q90.
        # Applied AFTER output_scale so bias is in final output space.
        if self.regime_bias_head is not None and regime_prior is not None:
            bias_all_h = self.regime_bias_head(regime_prior)  # (B, n_horizons)
            b = bias_all_h[:, horizon_idx:horizon_idx + 1]    # (B, 1)
            outputs["quantiles"] = outputs["quantiles"] + b
            outputs["point_pred"] = outputs["point_pred"] + b.squeeze(-1)

        # v5push Phase 3: classification head for DirAcc (BCE on sign(y))
        # If DAQH already provided sign_logit, do NOT overwrite — DAQH's
        # logit is the head's native direction signal.
        if self.sign_heads is not None and "sign_logit" not in outputs:
            sign_head = self.sign_heads[horizon_idx]
            outputs["sign_logit"] = sign_head(h_pred).squeeze(-1)  # (B,)
        # Track REG_arch_v5: surface stashed sequence direction logits if set
        if getattr(self, '_last_seq_dir_logits', None) is not None:
            outputs["seq_dir_logits"] = self._last_seq_dir_logits  # (B, T)
        return outputs

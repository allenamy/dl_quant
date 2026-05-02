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

        # --- Quantile Heads (per-horizon) ------------------------------------
        if use_monotonic_quantile:
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
            else:
                h_pred = self.backbone(h)
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
        if regime_prior is not None and self.ppnet_gate is not None:
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
        return outputs

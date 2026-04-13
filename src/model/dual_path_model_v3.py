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

from typing import Optional

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
    ):
        super().__init__()
        self.d_model = d_model
        self.d_raw = d_raw
        self.patch_size = patch_size
        self.n_horizons = n_horizons
        self.n_symbols = n_symbols
        self.use_monotonic_quantile = use_monotonic_quantile

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
        )

        # --- Fusion: concat -> Linear ---------------------------------------
        self.fusion = nn.Linear(d_model + d_raw, d_model)

        # --- Temporal: Dilated CausalConv (local patterns) -------------------
        # Dilation [1, 2, 4] with kernel=3 gives RF = 15 steps
        self.temporal_conv = nn.Sequential(
            CausalConv1dBlock(d_model, kernel_size=3, dilation=1, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=2, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=4, dropout=dropout),
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
        if d_prior > 0:
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

    def forward(
        self,
        x_feat: torch.Tensor,
        x_raw: torch.Tensor | None = None,
        regime_prior: torch.Tensor | None = None,
        cross_asset_feats: torch.Tensor | None = None,
        horizon_idx: int = 0,
    ) -> dict[str, torch.Tensor]:
        """Forward pass.

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
            Which horizon head to use (0-indexed). Default 0.

        Returns
        -------
        dict[str, torch.Tensor]
            - ``quantiles``: ``(B, 3)`` with [q10, q50, q90]
            - ``point_pred``: ``(B,)`` -- median prediction (q50)
        """
        # 1. Path A: features -> MaskNet -> GDCN -> proj
        h_craft = self.masknet(x_feat)           # (B, L, n_features) -- noise suppressed
        h_craft = self.gdcn(h_craft)             # (B, L, n_features) -- feature interactions
        h_craft = self.input_proj(h_craft)       # (B, L, d_model) -- project after interaction

        # 2. Path B: raw LOB tensor (optional)
        if x_raw is not None:
            h_raw = self.raw_encoder(x_raw)      # (B, L, d_raw)
            h = torch.cat([h_craft, h_raw], dim=-1)  # (B, L, d_model + d_raw)
            h = self.fusion(h)                   # (B, L, d_model)
        else:
            h = h_craft                          # (B, L, d_model)

        # 3. Temporal: dilated causal convolutions (local patterns)
        h = self.temporal_conv(h)                # (B, L, d_model)

        # 4. Patching: (B, L, d_model) -> (B, n_patches, d_model)
        h = self.patch_embed(h)                  # (B, n_patches, d_model)

        # 5. Causal self-attention (global patterns)
        h = self.patch_attention(h)              # (B, n_patches, d_model)

        # 6. Extract last patch token (most recent context)
        h_pred = h[:, -1, :]                     # (B, d_model)

        # 7. Cross-asset attention (optional)
        if cross_asset_feats is not None and self.cross_asset_attn is not None:
            # Stack: target symbol + other symbols
            # h_pred: (B, d_model), cross_asset_feats: (B, n_symbols-1, d_model)
            all_symbols = torch.cat(
                [h_pred.unsqueeze(1), cross_asset_feats], dim=1
            )  # (B, n_symbols, d_model)
            all_symbols = self.cross_asset_attn(all_symbols)  # (B, n_symbols, d_model)
            h_pred = all_symbols[:, 0, :]  # extract target symbol

        # 8. PPNet regime-conditioned gating
        if regime_prior is not None and self.ppnet_gate is not None:
            h_pred = self.ppnet_gate(h_pred, regime_prior)

        # 9. Quantile head (horizon-specific if multi-horizon)
        head = self.quantile_heads[horizon_idx]

        if self.use_monotonic_quantile:
            return head(h_pred)
        else:
            quantiles = head(h_pred)
            point_pred = quantiles[:, 1]
            return {"quantiles": quantiles, "point_pred": point_pred}

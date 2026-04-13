"""Dual-path model: hand-crafted features + raw LOB tensor.

Path A: features  -> LayerNorm -> Linear proj -> h_craft (B, L, d_model)
Path B: raw LOB   -> RawLOBEncoder            -> h_raw   (B, L, d_raw)
Fusion: concat    -> Linear -> CausalConv x2  -> quantile head

Total params target: ~15-20K (Phase 1 budget).

V2 (DualPathLOBModelV2) adds MaskNet + GDCN to Path A, PPNet regime gate,
and MonotonicQuantileHead:
Path A: features -> Linear proj -> MaskNet -> GDCN -> h_craft
Fusion -> CausalConv -> PPNet gate (regime prior) -> MonotonicQuantileHead
Total params target: < 30K (Phase 2 budget).
"""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.model.raw_lob_encoder import RawLOBEncoder
from src.model.masknet import MaskNet
from src.model.gdcn import GDCN
from src.model.ppnet_gate import PPNetGate
from src.model.monotonic_quantile import MonotonicQuantileHead


class CausalConv1dBlock(nn.Module):
    """Single causal Conv1d layer with residual connection.

    Causality is achieved by explicit left-padding of ``kernel_size - 1``.
    """

    def __init__(self, d_model: int, kernel_size: int = 3, dilation: int = 1, dropout: float = 0.1):
        super().__init__()
        self.pad = (kernel_size - 1) * dilation
        self.norm = nn.LayerNorm(d_model)
        self.conv = nn.Conv1d(d_model, d_model, kernel_size, dilation=dilation, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, L, d_model) -> (B, L, d_model)"""
        residual = x
        h = self.norm(x)
        # Conv1d expects (B, C, L)
        h = h.transpose(1, 2)
        h = F.pad(h, (self.pad, 0))  # causal left-padding
        h = self.conv(h)
        h = h[..., :x.size(1)]       # crop to original length
        h = self.act(h)
        h = self.drop(h)
        h = h.transpose(1, 2)        # back to (B, L, C)
        return h + residual


class DualPathLOBModel(nn.Module):
    """Dual-path model: hand-crafted features + raw LOB tensor.

    Path A: features -> input_norm -> input_proj -> h_craft (B, L, d_model)
    Path B: raw LOB  -> RawLOBEncoder            -> h_raw   (B, L, d_raw)
    Fusion: concat   -> Linear(d_model + d_raw, d_model)
    Temporal: CausalConv x2
    Head: quantile only

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
    nhead : int
        Number of attention heads (reserved for optional attention layer).
    d_ff : int
        Feed-forward hidden dimension (unused currently, kept for interface).
    dropout : float
        Dropout probability.
    n_quantiles : int
        Number of quantile outputs (default 3 for q10, q50, q90).
    """

    def __init__(
        self,
        n_features: int = 44,
        n_levels: int = 20,
        d_model: int = 32,
        d_raw: int = 16,
        nhead: int = 4,
        d_ff: int = 64,
        dropout: float = 0.15,
        n_quantiles: int = 3,
    ):
        super().__init__()
        self.d_model = d_model
        self.d_raw = d_raw

        # --- Path A: hand-crafted features ------------------------------------
        self.input_norm = nn.LayerNorm(n_features)
        self.input_proj = nn.Linear(n_features, d_model)

        # --- Path B: raw LOB tensor -------------------------------------------
        self.raw_encoder = RawLOBEncoder(
            n_levels=n_levels,
            d_raw=d_raw,
            dropout=dropout,
        )

        # --- Fusion: concat -> Linear ----------------------------------------
        self.fusion = nn.Linear(d_model + d_raw, d_model)

        # --- Temporal: CausalConv x2 -----------------------------------------
        self.temporal = nn.Sequential(
            CausalConv1dBlock(d_model, kernel_size=3, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dropout=dropout),
        )

        # --- Head: quantile only ---------------------------------------------
        self.quantile_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, n_quantiles),
        )

    def forward(
        self,
        x_feat: torch.Tensor,
        x_raw: torch.Tensor | None = None,
        pred_step: int = -1,
    ) -> dict[str, torch.Tensor]:
        """Forward pass.

        Parameters
        ----------
        x_feat : torch.Tensor
            Shape ``(B, L, n_features)`` -- hand-crafted features.
        x_raw : torch.Tensor | None
            Shape ``(B, L, n_levels, 4)`` -- raw LOB tensor, or ``None``
            for backward-compatible Path-A-only mode.
        pred_step : int
            Which temporal position to use for prediction (default: last).

        Returns
        -------
        dict[str, torch.Tensor]
            - ``quantiles``: ``(B, n_quantiles)``
            - ``point_pred``: ``(B,)`` -- median quantile
        """
        # Path A: hand-crafted features
        h_craft = self.input_proj(self.input_norm(x_feat))  # (B, L, d_model)

        if x_raw is not None:
            # Path B: raw LOB tensor
            h_raw = self.raw_encoder(x_raw)  # (B, L, d_raw)
            # Fusion: concat + project
            h = torch.cat([h_craft, h_raw], dim=-1)  # (B, L, d_model + d_raw)
            h = self.fusion(h)  # (B, L, d_model)
        else:
            # Fallback: Path A only (backward compatible)
            h = h_craft  # (B, L, d_model)

        # Temporal encoding
        h = self.temporal(h)  # (B, L, d_model)

        # Extract prediction timestep
        h_pred = h[:, pred_step, :]  # (B, d_model)

        # Quantile head
        quantiles = self.quantile_head(h_pred)  # (B, n_quantiles)
        point_pred = quantiles[:, 1]             # (B,) -- median

        return {
            "quantiles": quantiles,
            "point_pred": point_pred,
        }


class DualPathLOBModelV2(nn.Module):
    """Enhanced dual-path model with MaskNet, GDCN, PPNet gate, and monotonic quantiles.

    Path A: features -> MaskNet (noise suppression, n_features-dim) -> GDCN (gated crossing, n_features-dim) -> Linear proj -> h_craft
    Path B: raw LOB  -> RawLOBEncoder -> h_raw
    Fusion: concat   -> Linear(d_model + d_raw, d_model)
    Temporal: CausalConv x3 (dilated)
    Gate: PPNet regime gate (optional, from explicit hourly priors)
    Head: MonotonicQuantileHead (structurally guarantees q10 < q50 < q90)

    Compared to DualPathLOBModel:
    - MaskNet + GDCN operate in full feature space (n_features-dim) BEFORE projection
    - This preserves GDCN's theoretical advantage (gated crossing on raw features)
    - PPNet gate conditions model on explicit regime priors (hourly timescale)
    - MonotonicQuantileHead prevents quantile crossing by construction

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
    d_prior : int
        Dimensionality of regime prior features (default 6).
        Set to 0 to disable PPNet gate entirely.
    dropout : float
        Dropout probability.
    n_quantiles : int
        Number of quantile outputs (default 3 for q10, q50, q90).
    use_monotonic_quantile : bool
        If True, use MonotonicQuantileHead (structurally monotonic).
        If False, use the simple Linear quantile head (backward compatible).
    """

    def __init__(
        self,
        n_features: int = 44,
        n_levels: int = 20,
        d_model: int = 32,
        d_raw: int = 16,
        n_mask_blocks: int = 2,
        n_cross_layers: int = 2,
        d_prior: int = 6,
        dropout: float = 0.15,
        n_quantiles: int = 3,
        use_monotonic_quantile: bool = True,
    ):
        super().__init__()
        self.d_model = d_model
        self.d_raw = d_raw

        # --- Path A: hand-crafted features ------------------------------------
        # MaskNet + GDCN operate in full feature space (n_features-dim) BEFORE
        # projection to d_model.  This preserves GDCN's theoretical advantage:
        # gated crossing on raw features, not on a compressed representation.

        # MaskNet: per-sample noise suppression in feature space
        self.masknet = MaskNet(
            d_input=n_features,
            d_hidden=n_features,
            n_blocks=n_mask_blocks,
            dropout=dropout,
        )

        # GDCN: gated feature crossing in feature space
        self.gdcn = GDCN(
            d_input=n_features,
            n_layers=n_cross_layers,
            dropout=dropout,
        )

        # Project AFTER interaction: n_features -> d_model
        self.input_proj = nn.Linear(n_features, d_model)

        # --- Path B: raw LOB tensor -------------------------------------------
        self.raw_encoder = RawLOBEncoder(
            n_levels=n_levels,
            d_raw=d_raw,
            dropout=dropout,
        )

        # --- Fusion: concat -> Linear ----------------------------------------
        self.fusion = nn.Linear(d_model + d_raw, d_model)

        # --- Temporal: Dilated CausalConv for wider receptive field ------------
        # Dilation [1, 2, 4] with kernel=3 gives RF = 1+2+4+8 = 15 steps
        # vs RF=5 without dilation. Dilation adds zero extra parameters.
        self.temporal = nn.Sequential(
            CausalConv1dBlock(d_model, kernel_size=3, dilation=1, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=2, dropout=dropout),
            CausalConv1dBlock(d_model, kernel_size=3, dilation=4, dropout=dropout),
        )

        # --- PPNet Gate (optional) --------------------------------------------
        if d_prior > 0:
            self.ppnet_gate: Optional[PPNetGate] = PPNetGate(
                d_prior=d_prior,
                d_hidden=d_model,
                dropout=dropout,
            )
        else:
            self.ppnet_gate = None

        # --- Quantile Head ----------------------------------------------------
        self.use_monotonic_quantile = use_monotonic_quantile
        if use_monotonic_quantile:
            self.quantile_head = MonotonicQuantileHead(
                d_input=d_model,
                d_hidden=d_model,
                dropout=dropout,
            )
        else:
            # Fallback: simple linear head (backward compatible, no ordering)
            self._simple_quantile_head = nn.Sequential(
                nn.Linear(d_model, d_model),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model, n_quantiles),
            )

    def forward(
        self,
        x_feat: torch.Tensor,
        x_raw: torch.Tensor | None = None,
        regime_prior: torch.Tensor | None = None,
        pred_step: int = -1,
    ) -> dict[str, torch.Tensor]:
        """Forward pass.

        Parameters
        ----------
        x_feat : torch.Tensor
            Shape ``(B, L, n_features)`` -- hand-crafted features.
        x_raw : torch.Tensor | None
            Shape ``(B, L, n_levels, 4)`` -- raw LOB tensor, or ``None``
            for backward-compatible Path-A-only mode.
        regime_prior : torch.Tensor | None
            Shape ``(B, d_prior)`` -- regime prior features for PPNet gate.
            If None, PPNet gate is bypassed (identity).
        pred_step : int
            Which temporal position to use for prediction (default: last).

        Returns
        -------
        dict[str, torch.Tensor]
            - ``quantiles``: ``(B, 3)`` with [q10, q50, q90]
            - ``point_pred``: ``(B,)`` -- median prediction (q50)
        """
        # Path A: features -> MaskNet -> GDCN -> proj
        h_craft = self.masknet(x_feat)           # (B, L, n_features) -- noise suppressed
        h_craft = self.gdcn(h_craft)             # (B, L, n_features) -- feature interactions
        h_craft = self.input_proj(h_craft)       # (B, L, d_model) -- project after interaction

        if x_raw is not None:
            # Path B: raw LOB tensor
            h_raw = self.raw_encoder(x_raw)      # (B, L, d_raw)
            # Fusion: concat + project
            h = torch.cat([h_craft, h_raw], dim=-1)  # (B, L, d_model + d_raw)
            h = self.fusion(h)                   # (B, L, d_model)
        else:
            # Fallback: Path A only (backward compatible)
            h = h_craft                          # (B, L, d_model)

        # Temporal encoding
        h = self.temporal(h)                     # (B, L, d_model)

        # Extract prediction timestep
        h_pred = h[:, pred_step, :]              # (B, d_model)

        # PPNet regime-conditioned gating
        if regime_prior is not None and self.ppnet_gate is not None:
            h_pred = self.ppnet_gate(h_pred, regime_prior)

        # Quantile head
        if self.use_monotonic_quantile:
            return self.quantile_head(h_pred)
        else:
            quantiles = self._simple_quantile_head(h_pred)
            point_pred = quantiles[:, 1]
            return {"quantiles": quantiles, "point_pred": point_pred}

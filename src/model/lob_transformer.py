"""LOB Transformer V2 with regime-aware feature gating and multi-task heads.

Composes RegimeAwareFeatureGate, SpatialLOBEncoder, and CausalTemporalEncoder
into a full model that predicts quantiles, direction, and uncertainty from
limit-order-book data.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.model.side_encoder import SpatialLOBEncoder
from src.model.temporal_encoder import CausalTemporalEncoder


class RegimeAwareFeatureGate(nn.Module):
    """Soft feature gating conditioned on detected market regime.

    Parameters
    ----------
    d_input : int
        Number of input features.
    n_regimes : int
        Number of latent regimes.
    """

    def __init__(self, d_input: int, n_regimes: int = 4) -> None:
        super().__init__()

        # Regime detector: Linear -> GELU -> Linear -> Softmax
        self.regime_detector = nn.Sequential(
            nn.Linear(d_input, d_input // 4),
            nn.GELU(),
            nn.Linear(d_input // 4, n_regimes),
            nn.Softmax(dim=-1),
        )

        # Per-regime gate vectors
        self.regime_gates = nn.Parameter(torch.ones(n_regimes, d_input))

        # Direct (input-dependent) gate: Linear -> GELU -> Linear -> Sigmoid
        self.direct_gate = nn.Sequential(
            nn.Linear(d_input, d_input // 4),
            nn.GELU(),
            nn.Linear(d_input // 4, d_input),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply regime-aware gating.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, L, d_input)``.

        Returns
        -------
        torch.Tensor
            Same shape as *x*, element-wise gated.
        """
        # Causal cumulative mean: each timestep t uses mean(x[:, :t+1, :])
        # so that future inputs do not affect gating at earlier timesteps.
        cumsum = x.cumsum(dim=1)  # (B, L, d_input)
        counts = torch.arange(1, x.size(1) + 1, device=x.device, dtype=x.dtype)
        counts = counts.view(1, -1, 1)  # (1, L, 1)
        x_mean = cumsum / counts  # (B, L, d_input)

        # Regime detection per timestep
        regime_probs = self.regime_detector(x_mean)  # (B, L, n_regimes)

        # Weighted combination of per-regime gates: (B, L, d_input)
        regime_gate = torch.matmul(regime_probs, self.regime_gates)  # (B, L, d_input)

        # Direct gate per timestep
        d_gate = self.direct_gate(x_mean)  # (B, L, d_input)

        # Combine: 50/50 mix
        combined_gate = 0.5 * regime_gate + 0.5 * d_gate  # (B, L, d_input)

        return x * combined_gate


class LOBTransformerV2(nn.Module):
    """Full LOB Transformer V2 model.

    Pipeline::

        x -> RegimeAwareFeatureGate -> SpatialLOBEncoder -> CausalTemporalEncoder
          -> h[:, pred_step, :] -> {quantile_head, direction_head, uncertainty_head}

    Parameters
    ----------
    n_features : int
        Raw input features per timestep.
    d_model : int
        Hidden dimension throughout the model.
    nhead : int
        Number of attention heads.
    depth : int
        Number of Transformer blocks in the temporal encoder.
    d_ff : int
        Feed-forward hidden dimension.
    dropout : float
        Dropout probability.
    n_quantiles : int
        Number of quantile outputs (default 3 for lower, median, upper).
    n_direction_classes : int
        Number of direction classes (default 3 for down, neutral, up).
    n_regimes : int
        Number of latent regimes for feature gating.
    conv_layers : int
        Number of causal conv layers in temporal encoder.
    conv_kernel : int
        Kernel size for causal convolutions.
    """

    def __init__(
        self,
        n_features: int,
        d_model: int = 128,
        nhead: int = 4,
        depth: int = 4,
        d_ff: int = 256,
        dropout: float = 0.1,
        n_quantiles: int = 3,
        n_direction_classes: int = 3,
        n_regimes: int = 4,
        conv_layers: int = 2,
        conv_kernel: int = 9,
    ) -> None:
        super().__init__()

        # Feature gate
        self.feature_gate = RegimeAwareFeatureGate(n_features, n_regimes)

        # Spatial encoder (per-timestep)
        self.spatial_encoder = SpatialLOBEncoder(
            n_features=n_features,
            d_model=d_model,
            n_heads=nhead,
            dropout=dropout,
        )

        # Temporal encoder (causal)
        self.temporal_encoder = CausalTemporalEncoder(
            d_model=d_model,
            nhead=nhead,
            depth=depth,
            d_ff=d_ff,
            dropout=dropout,
            conv_layers=conv_layers,
            conv_kernel=conv_kernel,
            conv_dilation_base=2,
        )

        # --- Output heads ---

        # Quantile head: Linear -> GELU -> Dropout -> Linear -> (B, n_quantiles)
        self.quantile_head = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, n_quantiles),
        )

        # Direction head: Linear -> GELU -> Dropout -> Linear -> (B, n_direction_classes)
        self.direction_head = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, n_direction_classes),
        )

        # Uncertainty head: Linear -> GELU -> Linear -> Softplus -> (B,)
        self.uncertainty_head = nn.Sequential(
            nn.Linear(d_model, d_ff // 2),
            nn.GELU(),
            nn.Linear(d_ff // 2, 1),
            nn.Softplus(),
        )

    def forward(
        self,
        x: torch.Tensor,
        pred_step: int = -1,
    ) -> dict[str, torch.Tensor]:
        """Forward pass.

        Parameters
        ----------
        x : torch.Tensor
            Shape ``(B, L, n_features)``.
        pred_step : int
            Which temporal position to use for prediction (default: last).

        Returns
        -------
        dict[str, torch.Tensor]
            - ``quantiles``: (B, n_quantiles)
            - ``direction_logits``: (B, n_direction_classes)
            - ``uncertainty``: (B,)
            - ``point_pred``: (B,)  — median quantile
        """
        # Feature gating
        x = self.feature_gate(x)  # (B, L, n_features)

        # Spatial encoding
        h = self.spatial_encoder(x)  # (B, L, d_model)

        # Temporal encoding
        h = self.temporal_encoder(h)  # (B, L, d_model)

        # Extract prediction timestep
        h_pred = h[:, pred_step, :]  # (B, d_model)

        # Output heads
        quantiles = self.quantile_head(h_pred)            # (B, n_quantiles)
        direction_logits = self.direction_head(h_pred)     # (B, n_direction_classes)
        uncertainty = self.uncertainty_head(h_pred).squeeze(-1)  # (B,)
        point_pred = quantiles[:, 1]                       # (B,) — median

        return {
            "quantiles": quantiles,
            "direction_logits": direction_logits,
            "uncertainty": uncertainty,
            "point_pred": point_pred,
        }

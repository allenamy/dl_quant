"""V5-LH top-level model assembly.

Path A: handcrafted features → GDCN → Linear → (B, L, d_model)
Path B: raw LOB → SideAwareRawEncoder → (B, L, d_raw)
Fusion: CrossPathFusion(A, B) → (B, L, d_model)
Temporal: MambaBackbone → (B, L, d_model)
Pool: AttentionPool1D (sequence-last attention pool) → (B, d_model)
Per horizon h ∈ horizons:
  gated = PPNetGate(emb, regime_prior)   → (B, d_model)
  q_h   = MonotonicQuantileHead(gated)  → (B, 3)  [q10, q50, q90]

Return: {"embedding": emb, "y_180": ..., "y_600": ...}

Adaptations from plan reference (verified against actual V4 source):
- MonotonicQuantileHead.forward() returns a DICT {"quantiles": (B,3), "point_pred": (B,)},
  not a tensor. Must index result["quantiles"].
- PPNetGate.forward(h, prior) — first positional arg is h (hidden rep), second is prior.
  Plan used positional order (emb, regime_prior) which matches (h, prior) — no change needed.
- AttentionPool1D(d_model, input_is_last_dim=True) — plan uses input_is_last_dim=True for
  (N, L, d_model) input from MambaBackbone. Confirmed correct.
- GDCN(d_input, n_layers, dropout) — matches plan reference exactly.
"""
from __future__ import annotations

from typing import Dict, List

import torch
import torch.nn as nn

from src.model.gdcn import GDCN
from src.model.attention_pool import AttentionPool1D
from src.model.ppnet_gate import PPNetGate
from src.model.monotonic_quantile import MonotonicQuantileHead

from src.model_v5_lh.side_encoder import SideAwareRawEncoder
from src.model_v5_lh.cross_path_fusion import CrossPathFusion
from src.model_v5_lh.mamba_backbone import MambaBackbone


class V5LHModel(nn.Module):
    """V5 Long-Horizon dual-path model.

    Parameters
    ----------
    n_features : int
        Number of handcrafted input features (Path A width).
    n_levels : int
        Number of LOB levels in raw input tensor (Path B).
    d_model : int
        Core hidden dimension shared by Path A, fusion output, and temporal backbone.
    d_raw : int
        Output dimension of the SideAwareRawEncoder (Path B embedding width).
    d_prior : int
        Dimensionality of the regime prior vector (PPNetGate input).
    horizons : list[int]
        Prediction horizons in seconds. A separate PPNetGate + MonotonicQuantileHead
        is created for each horizon.
    n_mamba_layers : int
        Number of stacked Mamba (or fallback GRU) blocks.
    mamba_d_state : int
        State expansion factor for Mamba-2 SSM.
    mamba_expand : int
        Inner-dimension expansion inside Mamba-2 blocks.
    use_fallback : bool
        If True, replaces Mamba-2 with a GRU stub (for CPU / unit-test environments).

    Capacity tuning (2026-04-19 Option B):
        d_model=24 (was 32), n_mamba_layers=1 (was 2) — shrunk after discovering
        LH sample count is ~119K/fold (not 1M as spec estimated). At 1:2.5 param:sample
        ratio the 47K-param version would overfit; the 22K version gives 1:5.4 which
        is still tight but defensible in low-SNR regime.
    """

    def __init__(
        self,
        n_features: int,
        n_levels: int = 20,
        d_model: int = 24,
        d_raw: int = 16,
        d_prior: int = 6,
        horizons: List[int] = None,
        n_mamba_layers: int = 1,
        mamba_d_state: int = 16,
        mamba_expand: int = 1,
        use_fallback: bool = False,
    ):
        super().__init__()
        if horizons is None:
            horizons = [180, 600]
        self.horizons = horizons

        # ------------------------------------------------------------------
        # Path A: handcrafted features → GDCN cross-interactions → project
        # ------------------------------------------------------------------
        # GDCN operates at input width (n_features), preserving shape.
        # A Linear then maps to d_model.
        self.gdcn = GDCN(d_input=n_features, n_layers=2, dropout=0.15)
        self.input_proj = nn.Linear(n_features, d_model)

        # ------------------------------------------------------------------
        # Path B: raw LOB tensor → SideAwareRawEncoder
        # ------------------------------------------------------------------
        # d_side=8 is the internal per-side embedding width inside the encoder;
        # d_out=d_raw is what gets concatenated into fusion.
        self.raw_encoder = SideAwareRawEncoder(
            n_levels=n_levels, d_side=8, d_out=d_raw
        )

        # ------------------------------------------------------------------
        # Fusion: bidirectional cross-path attention + residual decomposition
        # ------------------------------------------------------------------
        self.fusion = CrossPathFusion(
            d_A=d_model, d_B=d_raw, d_out=d_model, nhead=4
        )

        # ------------------------------------------------------------------
        # Temporal: Mamba-2 backbone (GRU fallback for CPU tests)
        # ------------------------------------------------------------------
        self.mamba = MambaBackbone(
            d_model=d_model,
            n_layers=n_mamba_layers,
            d_state=mamba_d_state,
            expand=mamba_expand,
            use_fallback=use_fallback,
        )

        # ------------------------------------------------------------------
        # Pool: softmax-weighted attention pool over the sequence axis
        # MambaBackbone output is (B, L, d_model) — sequence-last dim format,
        # so input_is_last_dim=True.
        # ------------------------------------------------------------------
        self.pool = AttentionPool1D(d_model=d_model, input_is_last_dim=True)

        # ------------------------------------------------------------------
        # Per-horizon heads: PPNetGate + MonotonicQuantileHead
        # One pair per prediction horizon so gradients are decoupled.
        # ------------------------------------------------------------------
        self.ppnet_gates = nn.ModuleDict({
            str(h): PPNetGate(d_prior=d_prior, d_hidden=d_model, dropout=0.15)
            for h in horizons
        })
        self.heads = nn.ModuleDict({
            str(h): MonotonicQuantileHead(
                d_input=d_model, d_hidden=d_model, dropout=0.15
            )
            for h in horizons
        })

    def forward(
        self,
        X: torch.Tensor,             # (B, L, F) handcrafted features
        X_raw: torch.Tensor,         # (B, L, levels, 4) raw LOB tensor
        regime_prior: torch.Tensor,  # (B, d_prior) regime conditioning
    ) -> Dict[str, torch.Tensor]:
        """Run the full dual-path forward pass.

        Returns
        -------
        dict with keys:
          "embedding": (B, d_model)  — pooled embedding for decorrelation loss
          "y_{h}":     (B, 3)        — [q10, q50, q90] for each horizon h
        """
        # ------------------------------------------------------------------
        # Path A
        # ------------------------------------------------------------------
        h_A_feat = self.gdcn(X)          # (B, L, n_features) — same shape
        h_A = self.input_proj(h_A_feat)  # (B, L, d_model)

        # ------------------------------------------------------------------
        # Path B
        # ------------------------------------------------------------------
        h_B = self.raw_encoder(X_raw)    # (B, L, d_raw)

        # ------------------------------------------------------------------
        # Cross-path fusion
        # ------------------------------------------------------------------
        h_fused = self.fusion(h_A, h_B)  # (B, L, d_model)

        # ------------------------------------------------------------------
        # Temporal modeling
        # ------------------------------------------------------------------
        h_temp = self.mamba(h_fused)     # (B, L, d_model)

        # ------------------------------------------------------------------
        # Sequence pooling → single embedding
        # ------------------------------------------------------------------
        emb = self.pool(h_temp)          # (B, d_model)

        # ------------------------------------------------------------------
        # Per-horizon gated quantile prediction
        # ------------------------------------------------------------------
        out: Dict[str, torch.Tensor] = {"embedding": emb}
        for h in self.horizons:
            # PPNetGate(h_hidden, regime_prior) → (B, d_model)
            gated = self.ppnet_gates[str(h)](emb, regime_prior)
            # MonotonicQuantileHead.forward() returns a dict — extract quantiles
            head_out = self.heads[str(h)](gated)  # dict with "quantiles" key
            out[f"y_{h}"] = head_out["quantiles"]  # (B, 3): [q10, q50, q90]

        return out

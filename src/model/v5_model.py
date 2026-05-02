"""V5Model: V4 backbone (via .encode()) + HeteroscedasticHead.

V5 reuses V4's proven preprocessing (RevIN, MaskNet, GDCN, RawLOBEncoder,
fusion, temporal backbone, optional cross-asset attention, regime FiLM,
PPNet gate) by calling DualPathLOBModelV3.encode(), then routes the
embedding to HeteroscedasticHead which outputs (mu, log_sigma) per sample.

Important: the V4 backbone's quantile head is still INSTANTIATED (we don't
modify V4 architecture) but its parameters are unused in V5 forward. This
is a small overhead but keeps V4 checkpoints loadable into self.backbone.
"""
from __future__ import annotations
from typing import Dict, Optional
import torch
import torch.nn as nn

from src.model.dual_path_model_v3 import DualPathLOBModelV3
from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead


class V5Model(nn.Module):
    """Compose V4 encoder with V5 heteroscedastic head."""

    def __init__(
        self,
        v4_kwargs: dict,
        head_hidden: int = 0,
        head_dropout: float = 0.1,
    ):
        super().__init__()
        v4_kwargs = dict(v4_kwargs)
        self.n_horizons = int(v4_kwargs.get("n_horizons", 1))
        self.backbone = DualPathLOBModelV3(**v4_kwargs)
        d_emb = self._discover_d_emb()
        self.d_emb = d_emb
        self.v5_head = HeteroscedasticHead(
            d_emb=d_emb,
            n_horizons=self.n_horizons,
            hidden=head_hidden,
            dropout=head_dropout,
        )

    def _discover_d_emb(self) -> int:
        """Locate embedding dimension via direct attribute on backbone."""
        b = self.backbone
        for attr in ("d_emb", "d_fused", "d_out", "d_model"):
            if hasattr(b, attr):
                v = getattr(b, attr)
                if isinstance(v, int):
                    return v
        # Fallback: probe first Linear in V4's quantile head
        if hasattr(b, "quantile_heads") and len(b.quantile_heads) > 0:
            for m in b.quantile_heads[0].modules():
                if isinstance(m, nn.Linear):
                    return m.in_features
        return 32

    def forward(
        self,
        *args,
        mask: Optional[torch.Tensor] = None,
        **kwargs,
    ) -> Dict[str, torch.Tensor]:
        if not hasattr(self.backbone, "encode"):
            raise RuntimeError(
                "V4 backbone is missing .encode() — V5 A.8 refactor required."
            )
        emb = self.backbone.encode(*args, **kwargs)
        out = self.v5_head(emb)
        if mask is not None:
            out["mask"] = mask
        return out

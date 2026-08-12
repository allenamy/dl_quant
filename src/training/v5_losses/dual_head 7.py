"""Dual head: direction × magnitude decoupled prediction.

Replaces V4's single q50 head. Designed for low-SNR regression where the standard
quantile head over-shrinks magnitude (per V4 bin-plot diagnostics).

Forward signature mirrors V4 single head (returns one tensor per call), so it can
be slotted into model.head with minimal trainer changes; the loss assembly uses
the auxiliary returns to compute the multi-component loss.
"""
from __future__ import annotations

from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class DualHead(nn.Module):
    """Direction × magnitude with shared embedding.

    Architecture
    ------------
    Two parallel linear projections from the shared embedding:
      - dir_proj : emb → dir_logit (any real, sign decides direction)
      - mag_proj : emb → mag_pre (real, softplus → magnitude ≥ 0)

    Combination (during forward, used by joint loss + inference):
      - soft_sign = tanh(dir_logit / temperature)  ∈ (-1, 1)
      - y_pred    = soft_sign × magnitude

    Hidden bottleneck (optional) gives the head its own capacity beyond the
    shared backbone. Default 0 = direct linear from embedding.

    Parameters
    ----------
    d_emb : embedding dimension from backbone
    n_horizons : number of forecast horizons (V4 currently uses 1 for y_600)
    hidden : if >0, adds a hidden layer with this size + LeakyReLU before final proj
    dropout : dropout on hidden layer (only used if hidden>0)
    temperature : softens tanh; 1.0 = standard, larger → softer sign
    n_symbols : reserved for multi-asset (>=2 enables symbol embedding)
    """

    def __init__(
        self,
        d_emb: int,
        n_horizons: int = 1,
        hidden: int = 0,
        dropout: float = 0.1,
        temperature: float = 1.0,
        n_symbols: int = 1,
    ):
        super().__init__()
        self.d_emb = d_emb
        self.n_horizons = n_horizons
        self.temperature = max(temperature, 1e-3)
        self.n_symbols = n_symbols

        # Optional hidden bottleneck per head
        if hidden > 0:
            self.dir_trunk = nn.Sequential(
                nn.Linear(d_emb, hidden),
                nn.LeakyReLU(0.1),
                nn.Dropout(dropout),
            )
            self.mag_trunk = nn.Sequential(
                nn.Linear(d_emb, hidden),
                nn.LeakyReLU(0.1),
                nn.Dropout(dropout),
            )
            d_out = hidden
        else:
            self.dir_trunk = nn.Identity()
            self.mag_trunk = nn.Identity()
            d_out = d_emb

        self.dir_proj = nn.Linear(d_out, n_horizons)
        self.mag_proj = nn.Linear(d_out, n_horizons)

        # Optional symbol embedding (multi-asset hook)
        if n_symbols > 1:
            self.symbol_emb = nn.Embedding(n_symbols, d_emb)
        else:
            self.symbol_emb = None

        self._init_weights()

    def _init_weights(self):
        # Small init for stable warmup; magnitude proj has positive bias to avoid
        # degenerate softplus(0) = ln(2) ≈ 0.69 at start (we want similar magnitude
        # to typical y, which is ~1.0 in z-space).
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, a=0.1, nonlinearity="leaky_relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
        # Initialize mag_proj bias to ln(e^1 - 1) ≈ 0.5413 so softplus(bias) ≈ 1.0
        # (matches typical |y_z| ≈ 1 at start, avoids early-train under-prediction)
        nn.init.constant_(self.mag_proj.bias, 0.5413)
        # Final layer uses smaller weight init to prevent saturating tanh
        nn.init.normal_(self.dir_proj.weight, mean=0.0, std=1e-3)
        nn.init.normal_(self.mag_proj.weight, mean=0.0, std=1e-3)

    def forward(
        self,
        emb: torch.Tensor,
        symbol_id: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """Forward pass.

        Parameters
        ----------
        emb : (..., d_emb) embedding tensor
        symbol_id : (..., ) optional symbol indices; required if n_symbols > 1

        Returns
        -------
        dict with:
            dir_logit : (..., H) raw direction logit
            mag       : (..., H) softplus magnitude (≥ 0)
            soft_sign : (..., H) tanh-softened sign ∈ (-1, 1)
            y_pred    : (..., H) soft_sign × mag (combined output)
        """
        if self.symbol_emb is not None:
            if symbol_id is None:
                raise ValueError("symbol_id required when n_symbols > 1")
            emb = emb + self.symbol_emb(symbol_id)

        h_dir = self.dir_trunk(emb)
        h_mag = self.mag_trunk(emb)

        dir_logit = self.dir_proj(h_dir)
        mag_pre = self.mag_proj(h_mag)
        mag = F.softplus(mag_pre)

        soft_sign = torch.tanh(dir_logit / self.temperature)
        y_pred = soft_sign * mag

        return {
            "dir_logit": dir_logit,
            "mag": mag,
            "soft_sign": soft_sign,
            "y_pred": y_pred,
        }

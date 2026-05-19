"""V5 HeteroscedasticHead: outputs (μ, log_σ) per sample."""
from __future__ import annotations
from typing import Dict
import torch
import torch.nn as nn


class HeteroscedasticHead(nn.Module):
    def __init__(self, d_emb: int, n_horizons: int = 1, hidden: int = 0, dropout: float = 0.1):
        super().__init__()
        self.d_emb = d_emb
        self.n_horizons = n_horizons

        if hidden > 0:
            self.mu_trunk = nn.Sequential(
                nn.Linear(d_emb, hidden), nn.LeakyReLU(0.1), nn.Dropout(dropout)
            )
            self.log_sigma_trunk = nn.Sequential(
                nn.Linear(d_emb, hidden), nn.LeakyReLU(0.1), nn.Dropout(dropout)
            )
            d_out = hidden
        else:
            self.mu_trunk = nn.Identity()
            self.log_sigma_trunk = nn.Identity()
            d_out = d_emb

        self.mu_proj = nn.Linear(d_out, n_horizons)
        self.log_sigma_proj = nn.Linear(d_out, n_horizons)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, a=0.1, nonlinearity="leaky_relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
        nn.init.normal_(self.mu_proj.weight, mean=0.0, std=1e-3)
        nn.init.normal_(self.log_sigma_proj.weight, mean=0.0, std=1e-3)
        nn.init.zeros_(self.log_sigma_proj.bias)

    def forward(self, emb: torch.Tensor) -> Dict[str, torch.Tensor]:
        h_mu = self.mu_trunk(emb)
        h_ls = self.log_sigma_trunk(emb)
        mu = self.mu_proj(h_mu)
        log_sigma = self.log_sigma_proj(h_ls)
        return {"mu": mu, "log_sigma": log_sigma, "y_pred": mu, "point_pred": mu}

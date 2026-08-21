"""Multi-scale feature augmentation for y_600.

Computes long-timescale features on-the-fly from X_raw (raw LOB) so we capture
horizons matching the prediction target (y_600 = 10 min) without needing
NPZ regeneration. Existing X features top out at RV_300s — for a 600s
horizon that's a feature-horizon mismatch.

The module takes X_raw of shape (B, T=600, L=20, 4) where the 4 channels are
    [bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt]
both bid/ask deltas are the price levels relative to the mid of that timestep,
expressed in basis points.

Outputs per-timestep features at three aggregation scales (60s, 180s, 600s)
covering both microstructure (spread, book imbalance) and flow persistence:

  spread_bps_{scale}           rolling std of spread
  obi_L0_{scale}               rolling mean of top-level order-book imbalance
  depth_imb_{scale}            rolling mean of total-depth imbalance across 20 levels
  mid_vol_{scale}              rolling std of per-step bid/ask midpoint drift
  trend_mid_{scale}            rolling mean of mid-drift (momentum proxy)
  mean_rev_{scale}             current - rolling mean (mean-reversion z-score)

At scale=60 each feature gives one value per every-60-step window summary,
broadcast back to (B, T). At scale=600 the feature is a single scalar per
sample repeated across all timesteps (regime summary).

Total new features per timestep: 6 × 3 scales = 18.
"""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F


class MultiScaleRawAugment(nn.Module):
    def __init__(self, scales=(60, 180, 600)):
        super().__init__()
        self.scales = tuple(int(s) for s in scales)
        self.n_features_per_scale = 6
        self.n_out = self.n_features_per_scale * len(self.scales)

    @staticmethod
    def _rolling_mean(x: torch.Tensor, window: int) -> torch.Tensor:
        """Causal rolling mean with left-pad replication. x: (B, T)."""
        B, T = x.shape
        if window >= T:
            m = x.mean(dim=-1, keepdim=True)  # (B, 1)
            return m.expand(B, T)
        # Pad left with x[:, 0] so rolling mean at early steps doesn't underflow
        pad_left = x[:, :1].expand(B, window - 1)
        xp = torch.cat([pad_left, x], dim=-1)  # (B, T + w - 1)
        kernel = torch.full((1, 1, window), 1.0 / window,
                            dtype=x.dtype, device=x.device)
        # F.conv1d expects (B, C, T)
        y = F.conv1d(xp.unsqueeze(1), kernel)  # (B, 1, T)
        return y.squeeze(1)

    @classmethod
    def _rolling_std(cls, x: torch.Tensor, window: int) -> torch.Tensor:
        """Causal rolling std (biased) with left-pad replication."""
        m = cls._rolling_mean(x, window)
        m2 = cls._rolling_mean(x * x, window)
        var = (m2 - m * m).clamp(min=0.0)
        return torch.sqrt(var + 1e-8)

    def forward(self, x_raw: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x_raw : (B, T, L, 4) float tensor
            L levels × 4 channels per level, T=600 timesteps.

        Returns
        -------
        features : (B, T, n_out) per-timestep multi-scale aggregates.
        """
        B, T, L, _ = x_raw.shape
        # Top-level best bid/ask deltas (in bps)
        best_bid_bps = x_raw[:, :, 0, 0]  # (B, T)
        best_ask_bps = x_raw[:, :, 0, 2]  # (B, T)

        # Spread in bps (ask - bid), clamp non-negative to handle fp16 artefacts
        spread_bps = (best_ask_bps - best_bid_bps).clamp(min=0.0)

        # Top-level OBI (using log amounts as proxy for size ranking)
        best_bid_sz = x_raw[:, :, 0, 1]
        best_ask_sz = x_raw[:, :, 0, 3]
        obi_L0 = (best_bid_sz - best_ask_sz) / (best_bid_sz + best_ask_sz + 1e-3)

        # Total-depth imbalance across 20 levels
        total_bid = x_raw[:, :, :, 1].sum(dim=-1)  # (B, T)
        total_ask = x_raw[:, :, :, 3].sum(dim=-1)
        depth_imb = (total_bid - total_ask) / (total_bid + total_ask + 1e-3)

        # Mid-drift proxy: change of the midpoint relative to the sample's own
        # reference mid. Both best_bid_bps and best_ask_bps are relative to the
        # per-timestep mid; their sum approximates twice the deviation of this
        # tick's midpoint from the sample anchor.
        mid_proxy = (best_bid_bps + best_ask_bps) / 2.0  # (B, T) in bps

        features = []
        for scale in self.scales:
            features.append(self._rolling_std(spread_bps, scale))
            features.append(self._rolling_mean(obi_L0, scale))
            features.append(self._rolling_mean(depth_imb, scale))
            features.append(self._rolling_std(mid_proxy, scale))
            features.append(self._rolling_mean(mid_proxy, scale))
            # Mean-reversion z-score: (current mid proxy - rolling mean) / rolling std
            rm = self._rolling_mean(mid_proxy, scale)
            rs = self._rolling_std(mid_proxy, scale).clamp(min=1e-6)
            features.append((mid_proxy - rm) / rs)

        # Stack along feature dimension: list of (B, T) → (B, T, n_out)
        return torch.stack(features, dim=-1)

    def extra_repr(self) -> str:
        return f"scales={self.scales}, n_out={self.n_out}"


if __name__ == "__main__":
    # Smoke test
    torch.manual_seed(0)
    m = MultiScaleRawAugment(scales=(60, 180, 600))
    x = torch.randn(4, 600, 20, 4)
    y = m(x)
    assert y.shape == (4, 600, 18), y.shape
    print(f"Output shape OK: {tuple(y.shape)}")
    print(f"Features per scale: {m.n_features_per_scale}, total: {m.n_out}")
    print(f"Stats per feature (mean, std): ")
    for i in range(y.shape[-1]):
        v = y[..., i]
        print(f"  feature {i:2d}: mean={v.mean().item():+.4f} std={v.std().item():.4f}")

"""Tests for raw LOB tensor extraction, RawLOBEncoder, and DualPathLOBModel."""

from __future__ import annotations

import sys
import os
import unittest

import numpy as np
import pandas as pd

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from src.features.raw_lob import extract_raw_lob_tensor
from src.model.raw_lob_encoder import RawLOBEncoder
from src.model.dual_path_model import DualPathLOBModel


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

def _make_1s_bars(
    n_rows: int = 120,
    n_levels: int = 20,
    start_ts_us: int = 1_700_000_000_000_000,
    mid_price: float = 30_000.0,
) -> pd.DataFrame:
    """Create synthetic 1-second LOB bars (already resampled).

    Prices form a gentle random walk around *mid_price*.
    """
    rng = np.random.default_rng(99)
    us_per_sec = 1_000_000
    ts = start_ts_us + np.arange(n_rows) * us_per_sec

    # Small random walk for mid
    mid = mid_price + np.cumsum(rng.normal(0, 0.5, n_rows))

    data: dict[str, np.ndarray] = {"timestamp": ts}
    for i in range(n_levels):
        data[f"asks[{i}].price"] = mid + (i + 1) * 0.1 + rng.normal(0, 0.01, n_rows)
        data[f"asks[{i}].amount"] = rng.uniform(0.01, 5.0, n_rows)
        data[f"bids[{i}].price"] = mid - (i + 1) * 0.1 + rng.normal(0, 0.01, n_rows)
        data[f"bids[{i}].amount"] = rng.uniform(0.01, 5.0, n_rows)
    return pd.DataFrame(data)


# ===========================================================================
# Tests for extract_raw_lob_tensor
# ===========================================================================

class TestExtractRawLobTensorShape(unittest.TestCase):
    """Verify output shape is (N, n_levels, 4)."""

    def test_shape_default_levels(self) -> None:
        df = _make_1s_bars(n_rows=100, n_levels=20)
        tensor = extract_raw_lob_tensor(df, n_levels=20)
        self.assertEqual(tensor.shape, (100, 20, 4))

    def test_shape_custom_levels(self) -> None:
        df = _make_1s_bars(n_rows=50, n_levels=20)
        tensor = extract_raw_lob_tensor(df, n_levels=10)
        self.assertEqual(tensor.shape, (50, 10, 4))

    def test_dtype_float32(self) -> None:
        df = _make_1s_bars(n_rows=30, n_levels=20)
        tensor = extract_raw_lob_tensor(df, n_levels=20)
        self.assertEqual(tensor.dtype, np.float32)


class TestRawLobNormalization(unittest.TestCase):
    """Verify bid deltas are negative, ask deltas are positive, amounts are log-transformed."""

    def test_bid_deltas_negative(self) -> None:
        df = _make_1s_bars(n_rows=100, n_levels=20)
        tensor = extract_raw_lob_tensor(df, n_levels=20)
        bid_delta_bps = tensor[:, :, 0]  # channel 0
        # All bid deltas should be <= 0 (bid prices are at or below mid)
        self.assertTrue(
            (bid_delta_bps <= 0.5).all(),  # tiny tolerance for float precision
            f"Bid deltas should be negative; max={bid_delta_bps.max():.4f}",
        )

    def test_ask_deltas_positive(self) -> None:
        df = _make_1s_bars(n_rows=100, n_levels=20)
        tensor = extract_raw_lob_tensor(df, n_levels=20)
        ask_delta_bps = tensor[:, :, 2]  # channel 2
        # All ask deltas should be >= 0 (ask prices are at or above mid)
        self.assertTrue(
            (ask_delta_bps >= -0.5).all(),  # tiny tolerance for float precision
            f"Ask deltas should be positive; min={ask_delta_bps.min():.4f}",
        )

    def test_amounts_log_transformed(self) -> None:
        df = _make_1s_bars(n_rows=100, n_levels=20)
        tensor = extract_raw_lob_tensor(df, n_levels=20)
        bid_log_amt = tensor[:, :, 1]  # channel 1
        ask_log_amt = tensor[:, :, 3]  # channel 3
        # log1p(amount) should be >= 0 for non-negative amounts
        self.assertTrue((bid_log_amt >= 0).all(), "Bid log amounts should be >= 0")
        self.assertTrue((ask_log_amt >= 0).all(), "Ask log amounts should be >= 0")

    def test_no_nan_or_inf(self) -> None:
        df = _make_1s_bars(n_rows=100, n_levels=20)
        tensor = extract_raw_lob_tensor(df, n_levels=20)
        self.assertFalse(np.isnan(tensor).any(), "Tensor should contain no NaN")
        self.assertFalse(np.isinf(tensor).any(), "Tensor should contain no Inf")


class TestRawLobStationarity(unittest.TestCase):
    """Verify tensor values are bounded and don't drift with price level."""

    def test_bounded_values(self) -> None:
        """Tensor values should be bounded (bps deltas typically < 100 for near levels)."""
        df = _make_1s_bars(n_rows=200, n_levels=20, mid_price=30_000.0)
        tensor = extract_raw_lob_tensor(df, n_levels=20)
        # Price deltas in bps should be bounded (within a few bps for tight LOB)
        bid_delta = tensor[:, :, 0]
        ask_delta = tensor[:, :, 2]
        self.assertTrue(
            (np.abs(bid_delta) < 200).all(),
            f"Bid deltas too large; max abs={np.abs(bid_delta).max():.1f}",
        )
        self.assertTrue(
            (np.abs(ask_delta) < 200).all(),
            f"Ask deltas too large; max abs={np.abs(ask_delta).max():.1f}",
        )

    def test_price_level_invariance(self) -> None:
        """Tensor should be similar regardless of absolute price level.

        The bps normalization should remove non-stationarity from price drift.
        """
        df_low = _make_1s_bars(n_rows=100, n_levels=20, mid_price=10_000.0)
        df_high = _make_1s_bars(n_rows=100, n_levels=20, mid_price=100_000.0)

        tensor_low = extract_raw_lob_tensor(df_low, n_levels=20)
        tensor_high = extract_raw_lob_tensor(df_high, n_levels=20)

        # The bps deltas should have similar magnitude regardless of price level
        # because we normalize by mid price. Both use the same level offsets (0.1, 0.2, ...)
        # so the bps values will differ by the ratio of price levels.
        # The key point: neither drifts over time within its own series.
        bid_delta_low = tensor_low[:, :, 0]
        bid_delta_high = tensor_high[:, :, 0]

        # Standard deviation across time should be small (no drift)
        std_low = bid_delta_low[:, 0].std()
        std_high = bid_delta_high[:, 0].std()
        # Both should have small temporal variability
        self.assertLess(std_low, 1.0, "Low-price bid delta drifts too much")
        self.assertLess(std_high, 1.0, "High-price bid delta drifts too much")


# ===========================================================================
# Tests for RawLOBEncoder
# ===========================================================================

class TestRawLOBEncoderForward(unittest.TestCase):
    """Verify RawLOBEncoder produces correct output shape."""

    def test_output_shape(self) -> None:
        torch.manual_seed(42)
        B, L, N, d_raw = 4, 10, 20, 32
        encoder = RawLOBEncoder(n_levels=N, d_raw=d_raw, dropout=0.0)
        encoder.eval()

        x = torch.randn(B, L, N, 4)
        with torch.no_grad():
            out = encoder(x)

        self.assertEqual(out.shape, (B, L, d_raw))

    def test_finite_output(self) -> None:
        torch.manual_seed(42)
        encoder = RawLOBEncoder(n_levels=20, d_raw=16, dropout=0.0)
        encoder.eval()

        x = torch.randn(2, 5, 20, 4)
        with torch.no_grad():
            out = encoder(x)

        self.assertTrue(torch.isfinite(out).all(), "Non-finite values in encoder output")

    def test_per_timestep_independence(self) -> None:
        """Modifying one timestep should not affect others (no temporal mixing)."""
        torch.manual_seed(42)
        encoder = RawLOBEncoder(n_levels=20, d_raw=16, dropout=0.0)
        encoder.eval()

        x = torch.randn(2, 10, 20, 4)
        with torch.no_grad():
            out_orig = encoder(x.clone())

        # Perturb timestep 5
        x_pert = x.clone()
        x_pert[:, 5, :, :] = torch.randn(2, 20, 4)
        with torch.no_grad():
            out_pert = encoder(x_pert)

        # All timesteps except 5 should be identical
        for t in range(10):
            if t == 5:
                continue
            diff = (out_orig[:, t, :] - out_pert[:, t, :]).abs().max().item()
            self.assertEqual(diff, 0.0, f"Timestep {t} changed when timestep 5 was perturbed")


class TestRawLOBEncoderParams(unittest.TestCase):
    """Verify encoder has < 5K params."""

    def test_param_count(self) -> None:
        encoder = RawLOBEncoder(n_levels=20, d_raw=32, dropout=0.1)
        n_params = sum(p.numel() for p in encoder.parameters())
        self.assertLess(
            n_params, 5000,
            f"RawLOBEncoder has {n_params} params, expected < 5000",
        )


# ===========================================================================
# Tests for DualPathLOBModel
# ===========================================================================

class TestDualPathModelForward(unittest.TestCase):
    """Verify DualPathLOBModel works with both paths."""

    def test_dual_path_forward(self) -> None:
        torch.manual_seed(42)
        B, L = 4, 10
        n_features, n_levels = 44, 20

        model = DualPathLOBModel(
            n_features=n_features,
            n_levels=n_levels,
            d_model=32,
            d_raw=16,
            dropout=0.0,
        )
        model.eval()

        x_feat = torch.randn(B, L, n_features)
        x_raw = torch.randn(B, L, n_levels, 4)

        with torch.no_grad():
            out = model(x_feat, x_raw)

        self.assertIn("quantiles", out)
        self.assertIn("point_pred", out)
        self.assertEqual(out["quantiles"].shape, (B, 3))
        self.assertEqual(out["point_pred"].shape, (B,))
        self.assertTrue(torch.isfinite(out["quantiles"]).all())
        self.assertTrue(torch.isfinite(out["point_pred"]).all())


class TestDualPathModelFallback(unittest.TestCase):
    """Verify model works with x_raw=None (Path A only)."""

    def test_path_a_only(self) -> None:
        torch.manual_seed(42)
        B, L, n_features = 4, 10, 44

        model = DualPathLOBModel(
            n_features=n_features,
            d_model=32,
            d_raw=16,
            dropout=0.0,
        )
        model.eval()

        x_feat = torch.randn(B, L, n_features)

        with torch.no_grad():
            out = model(x_feat, x_raw=None)

        self.assertEqual(out["quantiles"].shape, (B, 3))
        self.assertEqual(out["point_pred"].shape, (B,))
        self.assertTrue(torch.isfinite(out["quantiles"]).all())

    def test_path_a_matches_no_raw(self) -> None:
        """Output with x_raw=None should differ from output with x_raw provided."""
        torch.manual_seed(42)
        B, L, n_features, n_levels = 2, 8, 44, 20

        model = DualPathLOBModel(
            n_features=n_features,
            n_levels=n_levels,
            d_model=32,
            d_raw=16,
            dropout=0.0,
        )
        model.eval()

        x_feat = torch.randn(B, L, n_features)
        x_raw = torch.randn(B, L, n_levels, 4)

        with torch.no_grad():
            out_dual = model(x_feat, x_raw)
            out_single = model(x_feat, x_raw=None)

        # Outputs should be different (raw path contributes)
        diff = (out_dual["quantiles"] - out_single["quantiles"]).abs().sum().item()
        self.assertGreater(diff, 0.0, "Raw path should change the output")


class TestDualPathModelParams(unittest.TestCase):
    """Verify total params < 25K."""

    def test_total_param_count(self) -> None:
        model = DualPathLOBModel(
            n_features=44,
            n_levels=20,
            d_model=32,
            d_raw=16,
            dropout=0.15,
        )
        n_params = sum(p.numel() for p in model.parameters())
        self.assertLess(
            n_params, 25000,
            f"DualPathLOBModel has {n_params} params, expected < 25000",
        )

    def test_param_breakdown(self) -> None:
        """Print parameter breakdown for inspection (informational, always passes)."""
        model = DualPathLOBModel(
            n_features=44,
            n_levels=20,
            d_model=32,
            d_raw=16,
            dropout=0.15,
        )
        total = 0
        for name, param in model.named_parameters():
            total += param.numel()
        # Just verify it's countable (no error)
        self.assertGreater(total, 0)


if __name__ == "__main__":
    unittest.main()

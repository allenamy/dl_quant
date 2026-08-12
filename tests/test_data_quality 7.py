"""Tests for scripts/check_data_quality.py."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.check_data_quality import check_depth_quality, check_trades_quality


class TestCheckDepthQuality(unittest.TestCase):
    """Verify quality checker works on synthetic data."""

    def test_check_depth_quality_ok(self) -> None:
        """Clean depth data should get OK status."""
        n = 1000
        # Timestamps: 1s apart, in microseconds
        base_ts = 1_776_000_000_000_000  # some base microsecond timestamp
        timestamps = base_ts + np.arange(n) * 1_000_000  # 1s intervals in us

        ask_prices = 71000.0 + np.random.default_rng(0).uniform(0.1, 0.5, n)
        bid_prices = ask_prices - np.random.default_rng(1).uniform(0.05, 0.3, n)

        df = pd.DataFrame({
            "timestamp": timestamps,
            "asks[0].price": ask_prices,
            "asks[0].amount": np.random.default_rng(2).uniform(0.1, 5.0, n),
            "bids[0].price": bid_prices,
            "bids[0].amount": np.random.default_rng(3).uniform(0.1, 5.0, n),
        })

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            df.to_csv(f, index=False)
            path = f.name

        try:
            result = check_depth_quality(path)
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["nan_count"], 0)
            self.assertTrue(result["spread_always_positive"])
            # avg_interval should be ~1.0s
            self.assertAlmostEqual(result["avg_interval"], 1.0, places=1)
        finally:
            os.unlink(path)

    def test_check_depth_quality_nan(self) -> None:
        """NaN in data should produce ERROR status."""
        n = 100
        base_ts = 1_776_000_000_000_000
        timestamps = base_ts + np.arange(n) * 1_000_000

        ask_prices = np.full(n, 71000.5)
        bid_prices = np.full(n, 71000.0)
        ask_prices[50] = np.nan  # introduce NaN

        df = pd.DataFrame({
            "timestamp": timestamps,
            "asks[0].price": ask_prices,
            "asks[0].amount": np.ones(n),
            "bids[0].price": bid_prices,
            "bids[0].amount": np.ones(n),
        })

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            df.to_csv(f, index=False)
            path = f.name

        try:
            result = check_depth_quality(path)
            self.assertEqual(result["status"], "ERROR")
            self.assertGreater(result["nan_count"], 0)
        finally:
            os.unlink(path)


class TestGapDetection(unittest.TestCase):
    """Verify gaps > 5s are detected."""

    def test_gap_detection_warning(self) -> None:
        """A 10s gap should produce WARNING status."""
        n = 100
        base_ts = 1_776_000_000_000_000
        # Normal 1s intervals
        timestamps = base_ts + np.arange(n) * 1_000_000
        # Insert a 10s gap at position 50
        timestamps[50:] += 9_000_000  # shift by +9s to make a 10s gap

        ask_prices = np.full(n, 71000.5)
        bid_prices = np.full(n, 71000.0)

        df = pd.DataFrame({
            "timestamp": timestamps,
            "asks[0].price": ask_prices,
            "asks[0].amount": np.ones(n),
            "bids[0].price": bid_prices,
            "bids[0].amount": np.ones(n),
        })

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            df.to_csv(f, index=False)
            path = f.name

        try:
            result = check_depth_quality(path)
            self.assertIn(result["status"], ("WARNING", "ERROR"))
            self.assertGreater(result["gap_count_gt5s"], 0)
            self.assertGreaterEqual(result["max_gap_sec"], 10.0)
        finally:
            os.unlink(path)

    def test_gap_detection_error_gt60s(self) -> None:
        """A 120s gap should produce ERROR status."""
        n = 100
        base_ts = 1_776_000_000_000_000
        timestamps = base_ts + np.arange(n) * 1_000_000
        # Insert a 120s gap
        timestamps[50:] += 119_000_000

        ask_prices = np.full(n, 71000.5)
        bid_prices = np.full(n, 71000.0)

        df = pd.DataFrame({
            "timestamp": timestamps,
            "asks[0].price": ask_prices,
            "asks[0].amount": np.ones(n),
            "bids[0].price": bid_prices,
            "bids[0].amount": np.ones(n),
        })

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            df.to_csv(f, index=False)
            path = f.name

        try:
            result = check_depth_quality(path)
            self.assertEqual(result["status"], "ERROR")
            self.assertGreater(result["gap_count_gt60s"], 0)
        finally:
            os.unlink(path)

    def test_trades_gap_detection(self) -> None:
        """Verify gap detection works for trades CSV too."""
        n = 50
        base_ts = 1_776_000_000_000_000
        timestamps = base_ts + np.arange(n) * 1_000_000
        # Insert a 15s gap
        timestamps[25:] += 14_000_000

        df = pd.DataFrame({
            "timestamp": timestamps,
            "price": np.full(n, 71000.0),
            "size": np.random.default_rng(0).uniform(0.01, 1.0, n),
            "side": np.where(np.random.default_rng(1).integers(0, 2, n), "Buy", "Sell"),
            "exec_id": [f"id-{i}" for i in range(n)],
        })

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            df.to_csv(f, index=False)
            path = f.name

        try:
            result = check_trades_quality(path)
            self.assertIn(result["status"], ("WARNING", "ERROR"))
            self.assertGreater(result["gap_count_gt5s"], 0)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

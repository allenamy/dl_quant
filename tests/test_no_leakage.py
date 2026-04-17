"""Tests for the CSV-to-NPZ pipeline — shape checks and no-leakage verification."""

from __future__ import annotations

import sys
import os
import unittest

import numpy as np
import pandas as pd

# Ensure project root is on sys.path so `src.*` imports work.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.features.pipeline import build_npz_for_day


def _make_synthetic_1s(n_rows: int = 600, n_levels: int = 25, seed: int = 42) -> pd.DataFrame:
    """Create a synthetic 1-second LOB DataFrame with *n_rows* rows.

    The prices form a gentle random walk so that mid_price is realistic and
    non-zero.  All bid/ask amounts are positive random values.
    """
    rng = np.random.RandomState(seed)

    us_per_sec = 1_000_000
    # Start at an arbitrary epoch timestamp (2024-01-01 00:00:00 UTC)
    t0 = 1_704_067_200 * us_per_sec
    timestamps = np.arange(t0, t0 + n_rows * us_per_sec, us_per_sec)

    # Mid price random walk around 50_000 (crypto-like)
    mid = 50_000.0 + np.cumsum(rng.randn(n_rows) * 0.5)

    data: dict[str, np.ndarray] = {"timestamp": timestamps}

    for i in range(n_levels):
        offset = (i + 1) * 0.01  # small price offset per level
        data[f"bids[{i}].price"] = mid - offset
        data[f"asks[{i}].price"] = mid + offset
        data[f"bids[{i}].amount"] = rng.exponential(1.0, size=n_rows).astype(np.float64)
        data[f"asks[{i}].amount"] = rng.exponential(1.0, size=n_rows).astype(np.float64)

    return pd.DataFrame(data)


class TestNpzShapeAndLabels(unittest.TestCase):
    """Verify shapes, dtypes, and no-leakage invariants of build_npz_for_day."""

    @classmethod
    def setUpClass(cls):
        cls.df_1s = _make_synthetic_1s(n_rows=600, n_levels=25)
        cls.result = build_npz_for_day(
            cls.df_1s,
            horizon_sec=180,
            input_len=300,
            stride=60,
            n_levels=25,
        )

    # ------------------------------------------------------------------
    # Shape / dtype checks
    # ------------------------------------------------------------------
    def test_X_is_3d(self):
        X = self.result["X"]
        self.assertEqual(X.ndim, 3, "X must be 3-dimensional (N_win, input_len, n_features)")

    def test_X_input_len(self):
        X = self.result["X"]
        self.assertEqual(X.shape[1], 300, "X.shape[1] must equal input_len=300")

    def test_y_is_1d(self):
        y = self.result["y"]
        self.assertEqual(y.ndim, 1, "y must be 1-dimensional")

    def test_shapes_match(self):
        X = self.result["X"]
        y = self.result["y"]
        y_mask = self.result["y_mask"]
        timestamps = self.result["timestamps"]
        self.assertEqual(X.shape[0], y.shape[0])
        self.assertEqual(X.shape[0], y_mask.shape[0])
        self.assertEqual(X.shape[0], timestamps.shape[0])

    def test_dtypes(self):
        self.assertEqual(self.result["X"].dtype, np.float32)
        self.assertEqual(self.result["y"].dtype, np.float32)
        self.assertEqual(self.result["y_mask"].dtype, np.uint8)
        self.assertEqual(self.result["timestamps"].dtype, np.int64)

    def test_no_nan_in_X(self):
        self.assertFalse(
            np.isnan(self.result["X"]).any(),
            "X must not contain any NaN values",
        )

    # ------------------------------------------------------------------
    # Label-integrity / no-leakage check
    # ------------------------------------------------------------------
    def test_target_within_bounds_when_mask_is_1(self):
        """When y_mask==1 the target index must not exceed data length."""
        n_total = 600  # same as n_rows used for construction
        input_len = 300
        stride = 60
        horizon_sec = 180

        y_mask = self.result["y_mask"]
        n_win = y_mask.shape[0]

        for win_idx in range(n_win):
            start = win_idx * stride
            pred_idx = start + input_len - 1
            target_idx = pred_idx + horizon_sec

            if y_mask[win_idx] == 1:
                self.assertLess(
                    target_idx, n_total,
                    f"Window {win_idx}: target_idx={target_idx} exceeds data "
                    f"length {n_total} but mask=1 (no-leakage violation)",
                )

    def test_positive_window_count(self):
        """With 600 rows, input_len=300, stride=60 we expect >0 windows."""
        self.assertGreater(self.result["X"].shape[0], 0, "Should produce at least one window")

    def test_expected_window_count(self):
        """Check the exact number of windows: range(0, 600-300+1, 60) = 6 windows."""
        n_total = 600
        input_len = 300
        stride = 60
        expected = len(range(0, n_total - input_len + 1, stride))
        self.assertEqual(self.result["X"].shape[0], expected)

    def test_features_list_nonempty(self):
        features = self.result["features"]
        self.assertIsInstance(features, list)
        self.assertGreater(len(features), 0)
        # mid_price should NOT be in features (used for labels only)
        self.assertNotIn("mid_price", features)
        # timestamp should NOT be in features
        self.assertNotIn("timestamp", features)

    def test_feature_count_matches_X(self):
        n_features = self.result["X"].shape[2]
        self.assertEqual(n_features, len(self.result["features"]))


def test_v4_npz_has_regime_prior_and_ridge_features():
    """When pipeline runs with new flags, NPZ output includes regime_prior + ridge features."""
    import tempfile, os, sys, numpy as np, pandas as pd
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.features.pipeline import build_npz_for_day

    n = 1500
    n_levels = 25
    rng = np.random.default_rng(42)
    base_ts = 1_704_067_200_000_000
    timestamps = base_ts + np.arange(n, dtype=np.int64) * 1_000_000
    cols = {"timestamp": timestamps}
    mid = 60000.0 + np.cumsum(rng.normal(0, 0.5, n))
    for i in range(n_levels):
        cols[f"asks[{i}].price"] = mid + 0.1 * (i + 1)
        cols[f"asks[{i}].amount"] = rng.exponential(1.0, n)
        cols[f"bids[{i}].price"] = mid - 0.1 * (i + 1)
        cols[f"bids[{i}].amount"] = rng.exponential(1.0, n)
    df_1s = pd.DataFrame(cols)

    # Synthesize trades aligned to the 1s depth grid so trade features
    # are computed (58 base cols). Without this, ridge features would
    # still work but base would be 49 cols (no trade features).
    n_trades = 3000
    trade_ts = base_ts + rng.integers(0, n * 1_000_000, n_trades).astype(np.int64)
    trade_ts.sort()
    trades_df = pd.DataFrame({
        "timestamp": trade_ts,
        "price": mid[np.clip((trade_ts - base_ts) // 1_000_000, 0, n - 1)] + rng.normal(0, 0.5, n_trades),
        "size": rng.exponential(0.1, n_trades),
        "side": rng.choice(["Buy", "Sell"], n_trades),
    })

    result = build_npz_for_day(
        df_1s,
        trades_df=trades_df,
        horizons_sec=[60, 180],
        input_len=600,
        stride=60,
        n_levels=n_levels,
        include_ridge_features=True,
        include_regime_prior=True,
    )

    assert result["X"].shape[-1] == 64, \
        f"Expected 64 features (58 + 6 ridge), got {result['X'].shape[-1]}"
    assert "regime_prior" in result
    assert result["regime_prior"].shape == (result["X"].shape[0], 6)
    assert len(result["features"]) == 64
    for name in ("net_flow_x_spread", "obi_L5_rank_1h", "large_trade_arrival_60s"):
        assert name in result["features"], f"{name} missing from features"
    print("PASS: test_v4_npz_has_regime_prior_and_ridge_features")


def test_v4_raises_when_ridge_flag_without_trades_df():
    """include_ridge_features=True without trades_df should raise KeyError
    instead of silently zero-filling trade-dependent inputs."""
    import sys, os, numpy as np, pandas as pd
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.features.pipeline import build_npz_for_day

    n, n_levels = 1500, 25
    rng = np.random.default_rng(42)
    base_ts = 1_704_067_200_000_000
    cols = {"timestamp": base_ts + np.arange(n, dtype=np.int64) * 1_000_000}
    mid = 60000.0 + np.cumsum(rng.normal(0, 0.5, n))
    for i in range(n_levels):
        cols[f"asks[{i}].price"] = mid + 0.1 * (i + 1)
        cols[f"asks[{i}].amount"] = rng.exponential(1.0, n)
        cols[f"bids[{i}].price"] = mid - 0.1 * (i + 1)
        cols[f"bids[{i}].amount"] = rng.exponential(1.0, n)
    df_1s = pd.DataFrame(cols)

    try:
        build_npz_for_day(
            df_1s, horizons_sec=[60, 180], input_len=600, stride=60,
            n_levels=n_levels, include_ridge_features=True,
        )
    except KeyError as e:
        assert "net_trade_flow_1s" in str(e), f"Wrong column in error: {e}"
        print("PASS: test_v4_raises_when_ridge_flag_without_trades_df")
        return
    raise AssertionError("Expected KeyError when trades_df missing and ridge flag on")


def test_process_csv_to_npz_forwards_v4_flags():
    """process_csv_to_npz accepts and forwards include_ridge_features /
    include_regime_prior flags."""
    import tempfile, os, sys, numpy as np, pandas as pd
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.features.pipeline import process_csv_to_npz

    # Inspect the signature to confirm the two flags are accepted kwargs.
    import inspect
    sig = inspect.signature(process_csv_to_npz)
    assert "include_ridge_features" in sig.parameters, \
        "process_csv_to_npz should accept include_ridge_features"
    assert "include_regime_prior" in sig.parameters, \
        "process_csv_to_npz should accept include_regime_prior"
    assert sig.parameters["include_ridge_features"].default is False
    assert sig.parameters["include_regime_prior"].default is False
    print("PASS: test_process_csv_to_npz_forwards_v4_flags")


if __name__ == "__main__":
    import unittest
    unittest.main(exit=False)
    test_v4_npz_has_regime_prior_and_ridge_features()
    test_v4_raises_when_ridge_flag_without_trades_df()
    test_process_csv_to_npz_forwards_v4_flags()

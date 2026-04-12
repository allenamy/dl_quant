"""Tests for src/features – resample & microstructure."""

from __future__ import annotations

import sys
import os
import unittest

import numpy as np
import pandas as pd

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.features.resample import resample_lob_to_1s
from src.features.microstructure import compute_microstructure_features


class TestResampleLobTo1s(unittest.TestCase):
    """Unit tests for the LOB 1-second resampler."""

    @staticmethod
    def _make_synthetic_lob(
        n_ticks: int = 100,
        n_levels: int = 5,
        tick_interval_us: int = 50_000,  # ~50 ms
        start_ts_us: int = 1_700_000_000_000_000,  # arbitrary epoch (us)
    ) -> pd.DataFrame:
        """Create a synthetic LOB DataFrame.

        Returns *n_ticks* rows spaced ~tick_interval_us apart with small
        jitter, containing *n_levels* of asks/bids price+amount columns.
        """
        rng = np.random.default_rng(42)

        # Timestamps with slight jitter
        ts = start_ts_us + np.arange(n_ticks) * tick_interval_us
        ts = ts + rng.integers(-5_000, 5_000, size=n_ticks)  # +/- 5 ms jitter
        ts.sort()

        data: dict[str, np.ndarray] = {"timestamp": ts}

        base_ask = 30_000.0
        base_bid = 29_999.0
        for i in range(n_levels):
            data[f"asks[{i}].price"] = base_ask + i * 0.1 + rng.normal(0, 0.01, n_ticks)
            data[f"asks[{i}].amount"] = rng.uniform(0.01, 5.0, n_ticks)
            data[f"bids[{i}].price"] = base_bid - i * 0.1 + rng.normal(0, 0.01, n_ticks)
            data[f"bids[{i}].amount"] = rng.uniform(0.01, 5.0, n_ticks)

        return pd.DataFrame(data)

    def test_resample_basic(self) -> None:
        """Core resampling contract: correct row count, spacing, completeness."""
        n_levels = 5
        df = self._make_synthetic_lob(n_ticks=100, n_levels=n_levels)
        result = resample_lob_to_1s(df, n_levels=n_levels)

        # --- 1. Row count should match the duration in whole seconds (+-2) ---
        us_per_sec = 1_000_000
        first_sec = df["timestamp"].iloc[0] // us_per_sec
        last_sec = df["timestamp"].iloc[-1] // us_per_sec
        expected_rows = int(last_sec - first_sec) + 1
        self.assertAlmostEqual(len(result), expected_rows, delta=2,
                               msg=f"Expected ~{expected_rows} rows, got {len(result)}")

        # --- 2. Timestamps are exactly 1 second apart -------------------------
        diffs = result["timestamp"].diff().dropna().unique()
        self.assertEqual(len(diffs), 1, f"Expected uniform spacing; got diffs: {diffs}")
        self.assertEqual(diffs[0], us_per_sec,
                         f"Expected 1-second spacing ({us_per_sec} us); got {diffs[0]}")

        # --- 3. All LOB columns present and non-NaN ---------------------------
        for i in range(n_levels):
            for side in ("asks", "bids"):
                for field in ("price", "amount"):
                    col = f"{side}[{i}].{field}"
                    self.assertIn(col, result.columns, f"Missing column: {col}")
                    self.assertFalse(
                        result[col].isna().any(),
                        f"Column {col} has NaN values after resample",
                    )

    def test_forward_fill_gap(self) -> None:
        """Ensure gaps are forward-filled, not interpolated or back-filled."""
        n_levels = 5
        df = self._make_synthetic_lob(n_ticks=100, n_levels=n_levels)

        # Introduce a 3-second gap by removing ticks in the middle
        us_per_sec = 1_000_000
        mid_sec = (df["timestamp"].iloc[0] // us_per_sec + 2) * us_per_sec
        gap_mask = (df["timestamp"] >= mid_sec) & (df["timestamp"] < mid_sec + 3 * us_per_sec)
        df_gap = df[~gap_mask].reset_index(drop=True)

        result = resample_lob_to_1s(df_gap, n_levels=n_levels)

        # There should be no NaNs (gaps forward-filled)
        lob_cols = [c for c in result.columns if c != "timestamp"]
        self.assertFalse(result[lob_cols].isna().any().any(),
                         "Forward-fill should eliminate all NaNs")

        # Spacing must still be uniform 1s
        diffs = result["timestamp"].diff().dropna().unique()
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0], us_per_sec)


class TestMicrostructureFeatures(unittest.TestCase):
    """Unit tests for compute_microstructure_features."""

    N_LEVELS = 25

    @staticmethod
    def _make_1s_bars(
        n_rows: int = 120,
        n_levels: int = 25,
        start_ts_us: int = 1_700_000_000_000_000,
    ) -> pd.DataFrame:
        """Create synthetic 1-second LOB bars (already resampled)."""
        rng = np.random.default_rng(99)
        us_per_sec = 1_000_000
        ts = start_ts_us + np.arange(n_rows) * us_per_sec

        data: dict[str, np.ndarray] = {"timestamp": ts}
        base_ask = 30_000.0
        base_bid = 29_999.0
        for i in range(n_levels):
            data[f"asks[{i}].price"] = base_ask + i * 0.1 + rng.normal(0, 0.01, n_rows)
            data[f"asks[{i}].amount"] = rng.uniform(0.01, 5.0, n_rows)
            data[f"bids[{i}].price"] = base_bid - i * 0.1 + rng.normal(0, 0.01, n_rows)
            data[f"bids[{i}].amount"] = rng.uniform(0.01, 5.0, n_rows)
        return pd.DataFrame(data)

    def test_microstructure_feature_count(self) -> None:
        """Verify exactly 40 feature columns (excluding timestamp)."""
        df = self._make_1s_bars()
        features = compute_microstructure_features(df, n_levels=self.N_LEVELS)

        feature_cols = [c for c in features.columns if c != "timestamp"]
        self.assertEqual(
            len(feature_cols),
            40,
            f"Expected 40 feature columns, got {len(feature_cols)}: {feature_cols}",
        )

        # Also verify timestamp IS present
        self.assertIn("timestamp", features.columns)

        # No NaN values
        self.assertFalse(
            features[feature_cols].isna().any().any(),
            "Feature DataFrame should have no NaN values",
        )

    def test_microstructure_no_leakage(self) -> None:
        """Modify future data and verify current features are unchanged.

        Strategy: compute features on the full DataFrame, then mutate rows
        at index >= T and recompute.  Features at index < T must be identical.
        """
        df = self._make_1s_bars(n_rows=120)
        features_full = compute_microstructure_features(df, n_levels=self.N_LEVELS)

        # Modify data from row 60 onward (the "future" relative to row 59)
        df_modified = df.copy()
        rng = np.random.default_rng(777)
        T = 60
        for i in range(self.N_LEVELS):
            for side in ("asks", "bids"):
                for field in ("price", "amount"):
                    col = f"{side}[{i}].{field}"
                    df_modified.loc[T:, col] = rng.uniform(
                        1.0, 50_000.0, size=len(df_modified) - T
                    )

        features_modified = compute_microstructure_features(
            df_modified, n_levels=self.N_LEVELS
        )

        feature_cols = [c for c in features_full.columns if c != "timestamp"]

        # All features at rows 0..T-1 must be identical
        for col in feature_cols:
            orig = features_full[col].iloc[:T].values
            modi = features_modified[col].iloc[:T].values
            np.testing.assert_array_almost_equal(
                orig,
                modi,
                decimal=10,
                err_msg=f"Feature '{col}' at rows <{T} changed when future data was modified — causality violation!",
            )


if __name__ == "__main__":
    unittest.main()

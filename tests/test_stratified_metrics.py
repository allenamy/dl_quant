"""Tests for stratified metrics and prediction-set comparison utilities."""

from __future__ import annotations

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.evaluation.metrics import (
    stratified_metrics_by_hour,
    stratified_metrics_by_vol_regime,
)
from src.evaluation.backtest_analysis import (
    compare_predictions_table,
    bootstrap_confidence_interval,
)


def _make_timestamps(n: int, start_hour: int = 0) -> np.ndarray:
    """Return `n` microsecond timestamps spread evenly across 24h."""
    seconds_per_sample = 86400.0 / n
    start_seconds = start_hour * 3600
    sec = start_seconds + np.arange(n) * seconds_per_sample
    return (sec * 1_000_000).astype(np.int64)


class TestStratifiedByHour(unittest.TestCase):
    """Hour-of-day stratification has correct shape and ordering."""

    def test_shape_and_columns(self) -> None:
        np.random.seed(0)
        n = 2400  # 100 per hour
        ts = _make_timestamps(n)
        pred = np.random.randn(n)
        target = np.random.randn(n)
        mask = np.ones(n, dtype=bool)

        df = stratified_metrics_by_hour(pred, target, mask, ts)

        self.assertEqual(len(df), 24)
        for col in ["hour", "n_samples", "corr", "r2", "mean_pred", "std_pred"]:
            self.assertIn(col, df.columns)
        # Hours must be 0..23 in order
        self.assertListEqual(list(df["hour"]), list(range(24)))
        # Each hour should have roughly equal coverage (all > 0)
        self.assertTrue((df["n_samples"] > 0).all())

    def test_empty_hour_has_zero_count(self) -> None:
        """If only 1h of data is present, other hours have 0 samples."""
        n = 100
        # All timestamps inside hour 3
        sec = 3 * 3600 + np.linspace(0, 60, n)
        ts = (sec * 1_000_000).astype(np.int64)
        pred = np.random.randn(n)
        target = np.random.randn(n)
        mask = np.ones(n, dtype=bool)

        df = stratified_metrics_by_hour(pred, target, mask, ts)
        h3 = df[df["hour"] == 3].iloc[0]
        self.assertEqual(h3["n_samples"], n)
        # Everybody else has 0
        other = df[df["hour"] != 3]
        self.assertTrue((other["n_samples"] == 0).all())


class TestStratifiedByVol(unittest.TestCase):
    """Volatility-regime stratification: rows ordered low -> high."""

    def test_default_three_buckets(self) -> None:
        np.random.seed(1)
        n = 600
        pred = np.random.randn(n)
        target = np.random.randn(n)
        mask = np.ones(n, dtype=bool)
        vol = np.abs(np.random.randn(n))

        df = stratified_metrics_by_vol_regime(pred, target, mask, vol)

        self.assertEqual(len(df), 3)
        self.assertListEqual(list(df["regime"]), ["low", "medium", "high"])
        self.assertTrue((df["n_samples"] > 0).all())

    def test_buckets_partition_samples(self) -> None:
        """The sum of n_samples across buckets equals the masked sample count."""
        np.random.seed(2)
        n = 300
        pred = np.random.randn(n)
        target = np.random.randn(n)
        mask = np.ones(n, dtype=bool)
        # Give each sample a unique vol so quantile splits are clean
        vol = np.arange(n, dtype=np.float64)

        df = stratified_metrics_by_vol_regime(pred, target, mask, vol, n_buckets=3)
        self.assertEqual(int(df["n_samples"].sum()), n)

    def test_n_buckets_4(self) -> None:
        np.random.seed(3)
        n = 400
        pred = np.random.randn(n)
        target = np.random.randn(n)
        mask = np.ones(n, dtype=bool)
        vol = np.random.rand(n)

        df = stratified_metrics_by_vol_regime(pred, target, mask, vol, n_buckets=4)
        self.assertEqual(len(df), 4)


class TestComparePredictionsTable(unittest.TestCase):
    """Side-by-side prediction comparison."""

    def test_basic_comparison(self) -> None:
        np.random.seed(0)
        n = 200
        target = np.random.randn(n)
        pred_a = target + 0.1 * np.random.randn(n)  # strong
        pred_b = np.random.randn(n)  # noise
        mask = np.ones(n, dtype=bool)

        df = compare_predictions_table(
            {"ModelA": (pred_a, mask), "ModelB": (pred_b, mask)},
            targets=target,
        )
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("correlation", df.columns)
        self.assertEqual(len(df), 2)
        # ModelA correlation should clearly exceed ModelB
        self.assertGreater(df.loc["ModelA", "correlation"],
                           df.loc["ModelB", "correlation"])

    def test_baseline_win_rate_column(self) -> None:
        np.random.seed(4)
        n = 150
        target = np.random.randn(n)
        # A is exactly target (perfect); B is noise
        pred_a = target.copy()
        pred_b = np.random.randn(n)
        mask = np.ones(n, dtype=bool)

        df = compare_predictions_table(
            {"Perfect": (pred_a, mask), "Noise": (pred_b, mask)},
            targets=target,
            baseline_key="Noise",
        )
        self.assertIn("win_rate_vs_baseline", df.columns)
        # Perfect model wins almost every sample vs noise
        self.assertGreater(df.loc["Perfect", "win_rate_vs_baseline"], 0.9)


class TestBootstrapCI(unittest.TestCase):
    """Bootstrap confidence interval sanity checks."""

    def test_ci_contains_point_estimate(self) -> None:
        np.random.seed(0)
        n = 500
        target = np.random.randn(n)
        pred = target + 0.3 * np.random.randn(n)
        mask = np.ones(n, dtype=bool)

        point = float(np.corrcoef(pred, target)[0, 1])
        lower, upper = bootstrap_confidence_interval(
            pred, target, mask, metric="correlation",
            n_bootstrap=300, seed=42,
        )
        self.assertLess(lower, upper)
        self.assertTrue(lower <= point <= upper,
                        f"CI [{lower}, {upper}] should contain point {point}")

    def test_ci_widens_with_smaller_n(self) -> None:
        np.random.seed(1)
        n_big = 2000
        target_big = np.random.randn(n_big)
        pred_big = target_big + np.random.randn(n_big)
        mask_big = np.ones(n_big, dtype=bool)

        n_small = 50
        # Use first 50 samples of the same process
        target_small = target_big[:n_small]
        pred_small = pred_big[:n_small]
        mask_small = np.ones(n_small, dtype=bool)

        big = bootstrap_confidence_interval(
            pred_big, target_big, mask_big,
            metric="correlation", n_bootstrap=300, seed=0,
        )
        small = bootstrap_confidence_interval(
            pred_small, target_small, mask_small,
            metric="correlation", n_bootstrap=300, seed=0,
        )
        width_big = big[1] - big[0]
        width_small = small[1] - small[0]
        self.assertGreater(width_small, width_big,
                           f"Expected small-n CI wider; small={width_small}, big={width_big}")

    def test_block_bootstrap_runs(self) -> None:
        """Moving-block bootstrap with block_size>1 is callable and returns CI."""
        np.random.seed(2)
        n = 300
        target = np.random.randn(n)
        pred = target * 0.5 + 0.3 * np.random.randn(n)
        mask = np.ones(n, dtype=bool)

        lower, upper = bootstrap_confidence_interval(
            pred, target, mask, metric="correlation",
            n_bootstrap=200, block_size=3, seed=7,
        )
        self.assertLess(lower, upper)

    def test_unsupported_metric_raises(self) -> None:
        pred = np.random.randn(20)
        target = np.random.randn(20)
        mask = np.ones(20, dtype=bool)
        with self.assertRaises(ValueError):
            bootstrap_confidence_interval(pred, target, mask, metric="foo")


if __name__ == "__main__":
    unittest.main()

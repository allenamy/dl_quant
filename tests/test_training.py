"""Tests for src/training – losses, dataset loader, and fold builder."""

from __future__ import annotations

import sys
import os
import tempfile
import unittest

import numpy as np
import torch

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.training.losses import (
    quantile_loss,
    asymmetric_huber_loss,
    combined_loss,
)
from src.training.dataset import LOBDataset, build_time_series_folds


class TestQuantileLoss(unittest.TestCase):
    """Quantile (pinball) loss sanity checks."""

    def test_quantile_loss_calibration(self) -> None:
        """Perfect quantile predictions should yield very small loss (<0.05).

        When all targets equal a constant c, the true conditional quantiles
        at every tau are also c.  Predicting pred_q = c for every quantile
        gives zero pinball loss.  We use a tiny spread around c to keep
        gradients alive and verify loss < 0.05.
        """
        torch.manual_seed(0)
        B = 1_000
        c = 1.5
        target = torch.full((B,), c)

        # Predict the exact quantile value for each tau (all equal c for a
        # point distribution).  Add small noise to make the test non-trivial.
        pred_quantiles = torch.full((B, 3), c) + torch.randn(B, 3) * 1e-4

        loss = quantile_loss(pred_quantiles, target)
        self.assertLess(loss.item(), 0.05,
                        f"Pinball loss for near-perfect quantile preds should be < 0.05, got {loss.item():.4f}")


class TestAsymmetricHuber(unittest.TestCase):
    """Asymmetric Huber loss behaviour."""

    def test_asymmetric_huber_penalizes_left_overestimate(self) -> None:
        """For negative targets, overestimate (pred > target) loss > underestimate loss."""
        B = 256
        target = torch.full((B,), -0.5)  # negative targets

        # Overestimate: predict closer to zero than actual (less negative)
        pred_over = torch.full((B,), -0.2)  # pred > target => overestimate
        # Underestimate: predict more negative than actual
        pred_under = torch.full((B,), -0.8)  # pred < target => underestimate

        loss_over = asymmetric_huber_loss(pred_over, target)
        loss_under = asymmetric_huber_loss(pred_under, target)

        self.assertGreater(
            loss_over.item(), loss_under.item(),
            f"Overestimate loss ({loss_over.item():.4f}) should exceed "
            f"underestimate loss ({loss_under.item():.4f}) for negative targets",
        )


class TestCombinedLoss(unittest.TestCase):
    """Combined loss integration."""

    def test_combined_loss_finite(self) -> None:
        """Combined loss produces finite values for random inputs."""
        torch.manual_seed(42)
        B = 64

        outputs = {
            "quantiles": torch.randn(B, 3),
            "direction_logits": torch.randn(B, 3),
            "uncertainty": torch.rand(B) + 0.01,  # positive variance
            "point_pred": torch.randn(B),
        }
        target = torch.randn(B)
        mask = torch.ones(B, dtype=torch.bool)

        total, loss_dict = combined_loss(outputs, target, mask)

        self.assertTrue(torch.isfinite(total), f"Total loss is not finite: {total}")
        for name, val in loss_dict.items():
            self.assertTrue(
                val == val and abs(val) < float("inf"),
                f"Component '{name}' is not finite: {val}",
            )


# ======================================================================
# Dataset & fold-builder tests (Task 8)
# ======================================================================


class TestLOBDataset(unittest.TestCase):
    """Unit tests for the NPZ-backed LOBDataset."""

    def test_dataset_loads_npz(self) -> None:
        """Create temp NPZ files, load via LOBDataset, verify shapes & types."""
        rng = np.random.default_rng(42)
        n_win, input_len, n_features = 20, 10, 5

        with tempfile.TemporaryDirectory() as tmpdir:
            for day in ("day1", "day2"):
                X = rng.standard_normal((n_win, input_len, n_features)).astype(np.float32)
                y = rng.integers(0, 3, size=n_win).astype(np.float32)
                y_mask = rng.integers(0, 2, size=n_win).astype(np.float32)
                timestamps = np.arange(n_win, dtype=np.int64)
                features = np.array([f"f{i}" for i in range(n_features)], dtype=object)
                np.savez(
                    os.path.join(tmpdir, f"{day}.npz"),
                    X=X, y=y, y_mask=y_mask, timestamps=timestamps, features=features,
                )

            ds = LOBDataset(data_dir=tmpdir, days=["day1", "day2"])

            # Total windows = 2 * n_win
            self.assertEqual(len(ds), 2 * n_win)

            # Single sample shapes
            x_t, y_t, m_t = ds[0]
            self.assertEqual(x_t.shape, (input_len, n_features))
            self.assertEqual(y_t.shape, ())
            self.assertEqual(m_t.shape, ())

            # dtype should be float
            self.assertTrue(x_t.dtype.is_floating_point)

    def test_dataset_sanitizes_nan(self) -> None:
        """NaN values are replaced and masked labels zeroed."""
        n_win, input_len, n_features = 5, 4, 3

        with tempfile.TemporaryDirectory() as tmpdir:
            X = np.full((n_win, input_len, n_features), np.nan, dtype=np.float32)
            y = np.array([1.0, 2.0, np.nan, 1.0, 0.0], dtype=np.float32)
            y_mask = np.array([1, 1, 0, 0, 1], dtype=np.float32)
            timestamps = np.arange(n_win, dtype=np.int64)
            features = np.array([f"f{i}" for i in range(n_features)], dtype=object)
            np.savez(
                os.path.join(tmpdir, "day1.npz"),
                X=X, y=y, y_mask=y_mask, timestamps=timestamps, features=features,
            )

            ds = LOBDataset(data_dir=tmpdir, days=["day1"])

            # X should have no NaN
            self.assertFalse(np.isnan(ds.X).any(), "X still contains NaN after sanitise")
            # Where mask==0, y must be 0
            masked_y = ds.y[ds.mask == 0]
            np.testing.assert_array_equal(masked_y, 0.0)

    def test_dataset_normalize(self) -> None:
        """Normalization clips to [-10, 10]."""
        rng = np.random.default_rng(7)
        n_win, input_len, n_features = 10, 4, 3

        with tempfile.TemporaryDirectory() as tmpdir:
            X = rng.standard_normal((n_win, input_len, n_features)).astype(np.float32) * 100
            y = np.zeros(n_win, dtype=np.float32)
            y_mask = np.ones(n_win, dtype=np.float32)
            timestamps = np.arange(n_win, dtype=np.int64)
            features = np.array([f"f{i}" for i in range(n_features)], dtype=object)
            np.savez(
                os.path.join(tmpdir, "day1.npz"),
                X=X, y=y, y_mask=y_mask, timestamps=timestamps, features=features,
            )

            # First, load without normalize to get stats
            ds_raw = LOBDataset(data_dir=tmpdir, days=["day1"])
            mean, std = ds_raw.compute_stats()

            # Load with normalize
            ds_norm = LOBDataset(
                data_dir=tmpdir, days=["day1"],
                normalize=True, x_mean=mean, x_std=std,
            )

            self.assertTrue(ds_norm.X.max() <= 10.0)
            self.assertTrue(ds_norm.X.min() >= -10.0)

    def test_compute_stats_shape(self) -> None:
        """compute_stats returns (mean, std) with shape (n_features,)."""
        rng = np.random.default_rng(0)
        n_win, input_len, n_features = 8, 6, 4

        with tempfile.TemporaryDirectory() as tmpdir:
            X = rng.standard_normal((n_win, input_len, n_features)).astype(np.float32)
            y = np.zeros(n_win, dtype=np.float32)
            y_mask = np.ones(n_win, dtype=np.float32)
            timestamps = np.arange(n_win, dtype=np.int64)
            features = np.array([f"f{i}" for i in range(n_features)], dtype=object)
            np.savez(
                os.path.join(tmpdir, "d.npz"),
                X=X, y=y, y_mask=y_mask, timestamps=timestamps, features=features,
            )

            ds = LOBDataset(data_dir=tmpdir, days=["d"])
            mean, std = ds.compute_stats()
            self.assertEqual(mean.shape, (n_features,))
            self.assertEqual(std.shape, (n_features,))


class TestBuildTimeSeriesFolds(unittest.TestCase):
    """Unit tests for the sliding-window fold builder."""

    def test_fold_builder_no_leakage(self) -> None:
        """All train days < all val days < all test days (strict temporal order)."""
        days = [f"2024-01-{d:02d}" for d in range(1, 31)]  # 30 days
        folds = build_time_series_folds(
            days, train_days=10, val_days=3, test_days=3, stride=3,
        )

        self.assertGreater(len(folds), 0, "Expected at least one fold")

        for i, fold in enumerate(folds):
            max_train = max(fold["train"])
            min_val = min(fold["val"])
            max_val = max(fold["val"])
            min_test = min(fold["test"])

            self.assertLess(
                max_train, min_val,
                f"Fold {i}: train leaks into val ({max_train} >= {min_val})",
            )
            self.assertLess(
                max_val, min_test,
                f"Fold {i}: val leaks into test ({max_val} >= {min_test})",
            )

    def test_fold_builder_window_sizes(self) -> None:
        """Each fold has the correct number of train / val / test days."""
        days = [str(d) for d in range(100)]
        train_d, val_d, test_d, stride = 20, 5, 5, 5
        folds = build_time_series_folds(days, train_d, val_d, test_d, stride)

        for fold in folds:
            self.assertEqual(len(fold["train"]), train_d)
            self.assertEqual(len(fold["val"]), val_d)
            self.assertEqual(len(fold["test"]), test_d)

    def test_fold_builder_stride(self) -> None:
        """Consecutive folds are offset by *stride* days."""
        days = [str(d) for d in range(50)]
        stride = 7
        folds = build_time_series_folds(days, train_days=10, val_days=3, test_days=3, stride=stride)

        for i in range(1, len(folds)):
            offset = days.index(folds[i]["train"][0]) - days.index(folds[i - 1]["train"][0])
            self.assertEqual(offset, stride, f"Fold {i} offset is {offset}, expected {stride}")

    def test_fold_builder_empty_when_too_few_days(self) -> None:
        """Return empty list when days are fewer than one full window."""
        days = ["a", "b", "c"]
        folds = build_time_series_folds(days, train_days=5, val_days=2, test_days=2, stride=1)
        self.assertEqual(folds, [])


if __name__ == "__main__":
    unittest.main()

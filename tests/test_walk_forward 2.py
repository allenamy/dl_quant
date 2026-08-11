"""Tests for walk-forward cross-validation helpers."""

from __future__ import annotations

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.evaluation.walk_forward import (
    walk_forward_evaluate,
    evaluate_across_folds,
)


class TestWalkForwardEvaluate(unittest.TestCase):
    """``walk_forward_evaluate`` produces the right number of folds."""

    def test_walk_forward_calls_predict_fn_n_times(self) -> None:
        calls = []

        def predict_fn(train_end, test_end):
            calls.append((train_end, test_end))
            n = test_end - train_end
            rng = np.random.default_rng(train_end)
            preds = rng.standard_normal(n)
            targets = rng.standard_normal(n)
            mask = np.ones(n, dtype=bool)
            return preds, targets, mask

        result = walk_forward_evaluate(
            predict_fn=predict_fn, n_samples=1000, n_folds=5,
        )
        self.assertEqual(result["n_folds"], 5)
        self.assertEqual(len(calls), 5)
        self.assertEqual(len(result["corrs"]), 5)

    def test_walk_forward_ordering(self) -> None:
        """Later folds must have larger train_end."""

        def predict_fn(train_end, test_end):
            n = test_end - train_end
            return np.zeros(n), np.zeros(n), np.ones(n, dtype=bool)

        result = walk_forward_evaluate(
            predict_fn=predict_fn, n_samples=500, n_folds=4,
        )
        boundaries = result["fold_boundaries"]
        train_ends = [b[0] for b in boundaries]
        test_ends = [b[1] for b in boundaries]
        # strictly non-decreasing
        for a, b in zip(train_ends, train_ends[1:]):
            self.assertLess(a, b)
        for a, b in zip(test_ends, test_ends[1:]):
            self.assertLess(a, b)

    def test_walk_forward_metrics_scalar_shape(self) -> None:
        """mean_corr is scalar, ci_95 is a 2-tuple."""

        def predict_fn(train_end, test_end):
            n = test_end - train_end
            rng = np.random.default_rng(train_end)
            base = rng.standard_normal(n)
            preds = base + 0.1 * rng.standard_normal(n)  # correlated
            return preds, base, np.ones(n, dtype=bool)

        result = walk_forward_evaluate(
            predict_fn=predict_fn, n_samples=600, n_folds=5,
        )
        self.assertIsInstance(result["mean_corr"], float)
        self.assertEqual(len(result["ci_95"]), 2)
        # Since preds is correlated with target, mean corr should be high
        self.assertGreater(result["mean_corr"], 0.8)


class _DummyDataset:
    def __init__(self, N=400, L=10, F=3):
        rng = np.random.default_rng(0)
        self.X = rng.standard_normal((N, L, F)).astype(np.float32)
        self.y = (0.3 * self.X[:, -1, 0] + 0.1 * rng.standard_normal(N)).astype(np.float32)
        self.mask = np.ones(N, dtype=bool)

    def __len__(self):
        return len(self.X)


class _DummyModel:
    """A minimal ridge-like fitted model that just uses feature 0 at the last step."""

    def __init__(self):
        self.scale = 0.0

    def fit(self, X_tr, y_tr):
        # OLS on feature 0 at last step
        x = X_tr[:, -1, 0]
        denom = float(np.dot(x, x))
        if denom > 0:
            self.scale = float(np.dot(x, y_tr) / denom)
        else:
            self.scale = 0.0
        return self

    def predict(self, X):
        return X[:, -1, 0] * self.scale


class TestEvaluateAcrossFolds(unittest.TestCase):
    """``evaluate_across_folds`` returns a DataFrame with expected columns."""

    def test_evaluate_across_folds_returns_df(self) -> None:
        ds = _DummyDataset()

        def model_fn():
            return _DummyModel()

        def train_fn(model, train_slice, val_slice):
            X_tr = ds.X[train_slice]
            y_tr = ds.y[train_slice]
            return model.fit(X_tr, y_tr)

        df = evaluate_across_folds(
            model_fn=model_fn,
            dataset=ds,
            train_fn=train_fn,
            n_folds=4,
        )

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 4)
        expected = {
            "fold_id", "train_start", "train_end",
            "test_start", "test_end", "test_corr",
            "test_r2", "n_samples",
        }
        self.assertTrue(expected.issubset(df.columns))
        # Train ends strictly increasing
        self.assertTrue(df["train_end"].is_monotonic_increasing)
        # Since a planted linear signal exists, at least one fold should
        # have positive test correlation
        self.assertTrue((df["test_corr"].dropna() > 0).any())


if __name__ == "__main__":
    unittest.main()

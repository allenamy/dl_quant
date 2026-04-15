"""Tests for single-feature naive baselines."""

from __future__ import annotations

import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.baselines.naive_baselines import (
    OBIBaseline,
    MomentumBaseline,
    FlowBaseline,
    MicropriceDeviationBaseline,
    run_all_naive_baselines,
)


class TestNaiveBaselineSigns(unittest.TestCase):
    """Signs / orientations of each baseline match their specification."""

    def test_obi_contrarian_sign(self) -> None:
        """OBI baseline with contrarian=True returns negative of raw feature."""
        np.random.seed(0)
        N, L, F = 50, 10, 3
        X = np.random.randn(N, L, F).astype(np.float32)
        feature_names = ["obi_L5", "log_return_30s", "net_trade_flow_1s"]

        bl = OBIBaseline(obi_feature="obi_L5", contrarian=True)
        pred = bl.predict(X, feature_names)

        np.testing.assert_allclose(pred, -X[:, -1, 0], rtol=1e-6)

    def test_obi_non_contrarian_sign(self) -> None:
        """OBI with contrarian=False returns the raw feature unchanged."""
        np.random.seed(1)
        N, L, F = 30, 5, 2
        X = np.random.randn(N, L, F).astype(np.float32)
        feature_names = ["obi_L5", "other"]

        bl = OBIBaseline(obi_feature="obi_L5", contrarian=False)
        pred = bl.predict(X, feature_names)
        np.testing.assert_allclose(pred, X[:, -1, 0], rtol=1e-6)

    def test_momentum_sign(self) -> None:
        """Momentum baseline returns the raw log return at the last timestep."""
        np.random.seed(2)
        N, L, F = 40, 8, 4
        X = np.random.randn(N, L, F).astype(np.float32)
        feature_names = ["a", "b", "log_return_30s", "d"]

        bl = MomentumBaseline(horizon="log_return_30s")
        pred = bl.predict(X, feature_names)
        np.testing.assert_allclose(pred, X[:, -1, 2], rtol=1e-6)

    def test_flow_sign(self) -> None:
        np.random.seed(3)
        N, L, F = 20, 4, 3
        X = np.random.randn(N, L, F).astype(np.float32)
        feature_names = ["x", "net_trade_flow_1s", "y"]

        bl = FlowBaseline(flow_feature="net_trade_flow_1s")
        pred = bl.predict(X, feature_names)
        np.testing.assert_allclose(pred, X[:, -1, 1], rtol=1e-6)

    def test_microprice_dev_sign(self) -> None:
        np.random.seed(4)
        N, L, F = 15, 6, 2
        X = np.random.randn(N, L, F).astype(np.float32)
        feature_names = ["microprice_dev_bps", "z"]

        bl = MicropriceDeviationBaseline(feature="microprice_dev_bps")
        pred = bl.predict(X, feature_names)
        np.testing.assert_allclose(pred, X[:, -1, 0], rtol=1e-6)


class TestMissingFeature(unittest.TestCase):
    """Clear error when a requested feature is absent."""

    def test_missing_feature_raises(self) -> None:
        X = np.random.randn(10, 5, 3)
        feature_names = ["only_this_one", "and_this", "something_else"]

        bl = OBIBaseline(obi_feature="obi_L5")
        with self.assertRaises(KeyError) as ctx:
            bl.predict(X, feature_names)
        # Error message should mention the missing feature name
        self.assertIn("obi_L5", str(ctx.exception))


class TestRunAllBaselines(unittest.TestCase):
    """Batch runner returns a well-formed DataFrame."""

    def _make_data(self):
        np.random.seed(42)
        feature_names = [
            "obi_L5", "log_return_30s",
            "net_trade_flow_1s", "microprice_dev_bps",
        ]
        N, L, F = 200, 20, len(feature_names)
        X_train = np.random.randn(N, L, F).astype(np.float32)
        y_train = np.random.randn(N).astype(np.float32)
        X_test = np.random.randn(N, L, F).astype(np.float32)
        # Plant momentum signal: y_test loosely follows log_return_30s
        y_test = (X_test[:, -1, 1] * 0.3
                  + 0.1 * np.random.randn(N)).astype(np.float32)
        mask_test = np.ones(N, dtype=bool)
        return X_train, y_train, X_test, y_test, mask_test, feature_names

    def test_run_all_baselines_shape(self) -> None:
        X_tr, y_tr, X_te, y_te, m_te, names = self._make_data()
        df = run_all_naive_baselines(X_tr, y_tr, X_te, y_te, m_te, names)

        self.assertIsInstance(df, pd.DataFrame)
        # One row per default baseline (4)
        self.assertEqual(len(df), 4)
        for col in ["model", "feature", "n", "correlation", "r2"]:
            self.assertIn(col, df.columns)
        # All models report the same sample count when mask is all True
        self.assertTrue((df["n"] == len(y_te)).all())

    def test_momentum_detects_planted_signal(self) -> None:
        """With y loosely driven by log_return_30s the momentum baseline
        should produce a clearly positive correlation."""
        X_tr, y_tr, X_te, y_te, m_te, names = self._make_data()
        df = run_all_naive_baselines(X_tr, y_tr, X_te, y_te, m_te, names)

        mom_row = df[df["model"].str.startswith("Momentum")].iloc[0]
        self.assertGreater(
            mom_row["correlation"], 0.2,
            f"Momentum should detect planted signal, got {mom_row['correlation']}"
        )

    def test_missing_feature_records_error(self) -> None:
        """Baselines whose feature is missing get error-recorded, not crash."""
        np.random.seed(0)
        X = np.random.randn(30, 5, 2).astype(np.float32)
        y = np.random.randn(30).astype(np.float32)
        mask = np.ones(30, dtype=bool)
        feature_names = ["some_feat", "another"]  # none of the defaults present

        df = run_all_naive_baselines(
            X_train=X, y_train=y, X_test=X, y_test=y, mask_test=mask,
            feature_names=feature_names,
        )
        self.assertEqual(len(df), 4)
        self.assertTrue(df["error"].notna().all())
        self.assertTrue(df["correlation"].isna().all())


if __name__ == "__main__":
    unittest.main()

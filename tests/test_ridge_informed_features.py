import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd

from src.features.ridge_informed_features import (
    compute_ridge_informed_features,
    RIDGE_INFORMED_FEATURE_NAMES,
)


class TestRidgeInformedFeatures(unittest.TestCase):

    def _make_inputs(self, n=600, seed=0):
        rng = np.random.default_rng(seed)
        df = pd.DataFrame({
            "timestamp": np.arange(n, dtype=np.int64) * 1_000_000,
            "net_trade_flow_1s": rng.normal(0.0, 1.0, n),
            "spread_bps": rng.uniform(0.01, 0.1, n),
            "realized_vol_30s": rng.uniform(1e-5, 1e-3, n),
            "obi_L5": rng.uniform(-1.0, 1.0, n),
            "book_pressure_imbalance": rng.normal(0, 0.5, n),
        })
        return df

    def test_feature_count_and_names(self):
        df = self._make_inputs()
        out = compute_ridge_informed_features(df)
        self.assertEqual(len(RIDGE_INFORMED_FEATURE_NAMES), 6)
        for name in RIDGE_INFORMED_FEATURE_NAMES:
            self.assertIn(name, out.columns)
        self.assertIn("timestamp", out.columns)
        self.assertNotIn("obi_L5", out.columns)
        self.assertEqual(len(out), len(df))

    def test_no_future_leakage(self):
        """Modifying rows AFTER index k must not change feature values at index k."""
        df = self._make_inputs()
        out_full = compute_ridge_informed_features(df)
        k = 300
        df_modified = df.copy()
        for col in ("net_trade_flow_1s", "spread_bps", "realized_vol_30s", "obi_L5",
                    "book_pressure_imbalance"):
            df_modified.loc[k + 1:, col] = 1e6
        out_modified = compute_ridge_informed_features(df_modified)
        for name in RIDGE_INFORMED_FEATURE_NAMES:
            orig = out_full[name].iloc[:k + 1].to_numpy()
            new = out_modified[name].iloc[:k + 1].to_numpy()
            np.testing.assert_allclose(orig, new, equal_nan=True, err_msg=f"LEAK in {name}")

    def test_rolling_rank_is_percentile_in_01(self):
        """Rolling rank features must be in [0, 1]."""
        df = self._make_inputs()
        out = compute_ridge_informed_features(df)
        for name in ("obi_L5_rank_1h", "net_flow_rank_1h"):
            v = out[name].to_numpy()
            v = v[np.isfinite(v)]
            self.assertTrue(np.all((v >= 0.0) & (v <= 1.0)), f"{name} out of [0,1]")

    def test_large_trade_arrival_is_binary(self):
        df = self._make_inputs()
        out = compute_ridge_informed_features(df)
        vals = out["large_trade_arrival_60s"].unique()
        for v in vals:
            self.assertIn(v, (0.0, 1.0))

    def test_interaction_features_equal_product(self):
        df = self._make_inputs()
        out = compute_ridge_informed_features(df)
        np.testing.assert_allclose(
            out["net_flow_x_spread"].to_numpy(),
            df["net_trade_flow_1s"].to_numpy() * df["spread_bps"].to_numpy(),
            rtol=1e-10,
        )
        np.testing.assert_allclose(
            out["net_flow_x_vol"].to_numpy(),
            df["net_trade_flow_1s"].to_numpy() * df["realized_vol_30s"].to_numpy(),
            rtol=1e-10,
        )

    def test_book_pressure_delta_is_first_difference(self):
        df = self._make_inputs()
        out = compute_ridge_informed_features(df)
        deltas = out["book_pressure_delta_60s"].to_numpy()
        self.assertTrue(np.all(deltas[:60] == 0.0))
        expected = df["book_pressure_imbalance"].to_numpy()[60:] - df["book_pressure_imbalance"].to_numpy()[:-60]
        np.testing.assert_allclose(deltas[60:], expected, rtol=1e-10)


if __name__ == "__main__":
    unittest.main()

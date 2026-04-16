import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd

from src.features.regime_prior_features import (
    compute_regime_prior_features,
    REGIME_PRIOR_FEATURE_NAMES,
)


class TestRegimePriorFeatures(unittest.TestCase):

    def _make_inputs(self, n=30_000, seed=0):
        """8.3h of 1s bars — enough for 6h price_return horizon."""
        rng = np.random.default_rng(seed)
        start_us = 1_704_067_200_000_000  # 2024-01-01 00:00:00 UTC
        ts = start_us + np.arange(n, dtype=np.int64) * 1_000_000
        mid = 60000.0 + np.cumsum(rng.normal(0, 0.5, n))
        log_ret_1s = np.diff(np.log(mid), prepend=np.log(mid[0]))
        obi_L5 = rng.uniform(-1.0, 1.0, n)
        spread_bps = rng.uniform(0.02, 0.1, n)
        return pd.DataFrame({
            "timestamp": ts,
            "mid_price": mid,
            "log_return_1s": log_ret_1s,
            "obi_L5": obi_L5,
            "spread_bps": spread_bps,
        })

    def test_feature_count_and_names(self):
        df = self._make_inputs()
        out = compute_regime_prior_features(df)
        self.assertEqual(len(REGIME_PRIOR_FEATURE_NAMES), 6)
        for name in REGIME_PRIOR_FEATURE_NAMES:
            self.assertIn(name, out.columns)
        self.assertEqual(len(out), len(df))

    def test_no_future_leakage(self):
        df = self._make_inputs(n=20_000)
        out_full = compute_regime_prior_features(df)
        k = 10_000
        df_modified = df.copy()
        for col in ("mid_price", "log_return_1s", "obi_L5", "spread_bps"):
            df_modified.loc[k + 1:, col] = 1e6
        out_modified = compute_regime_prior_features(df_modified)
        for name in REGIME_PRIOR_FEATURE_NAMES:
            np.testing.assert_allclose(
                out_full[name].iloc[:k + 1].to_numpy(),
                out_modified[name].iloc[:k + 1].to_numpy(),
                equal_nan=True,
                err_msg=f"LEAK in {name}",
            )

    def test_hour_sin_cos_deterministic(self):
        """hour_sin/cos depend only on the timestamp's hour-of-day (UTC)."""
        df = self._make_inputs(n=3_600)
        out = compute_regime_prior_features(df)
        self.assertLess(abs(out["hour_cos"].iloc[0] - 1.0), 0.01)
        self.assertLess(abs(out["hour_sin"].iloc[0]), 0.01)

    def test_vol_1h_requires_warmup(self):
        """Before accumulating 1h of history, vol is estimated from available data."""
        df = self._make_inputs(n=7_200)
        out = compute_regime_prior_features(df)
        self.assertTrue(np.isfinite(out["vol_1h"].iloc[0]))
        self.assertTrue(np.all(np.isfinite(out["vol_1h"].iloc[3_600:])))

    def test_price_return_6h_zero_before_warmup(self):
        df = self._make_inputs(n=10_000)
        out = compute_regime_prior_features(df)
        self.assertTrue(np.all(out["price_return_6h"].to_numpy() == 0.0))

    def test_price_return_6h_matches_formula_when_warm(self):
        df = self._make_inputs(n=30_000)
        out = compute_regime_prior_features(df)
        mid = df["mid_price"].to_numpy()
        t = 25_000
        expected = np.log(mid[t] / mid[t - 21_600])
        np.testing.assert_allclose(out["price_return_6h"].iloc[t], expected, rtol=1e-8)


if __name__ == "__main__":
    unittest.main()

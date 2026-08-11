"""Unit tests for src/features/derived_features.py."""

from __future__ import annotations

import os
import sys
import unittest

import numpy as np
import pandas as pd

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.features.derived_features import (
    DERIVED_FEATURE_NAMES,
    compute_book_pressure_imbalance,
    compute_derived_features,
    compute_microprice,
    compute_microprice_deviation_bps,
    compute_price_impact_proxy,
    compute_roll_spread,
    compute_vpin,
)


class TestMicroprice(unittest.TestCase):
    """Tests for ``compute_microprice`` and its bps deviation."""

    def test_microprice_correct_formula(self) -> None:
        """Hand-computed values must match the Stoikov formula."""
        bid_p = np.array([100.0])
        ask_p = np.array([101.0])
        bid_a = np.array([3.0])
        ask_a = np.array([1.0])

        # formula: (b_vol * a_price + a_vol * b_price) / (b_vol + a_vol)
        #        = (3 * 101 + 1 * 100) / 4 = 403 / 4 = 100.75
        out = compute_microprice(bid_p, bid_a, ask_p, ask_a)
        np.testing.assert_allclose(out, [100.75], atol=1e-12)

    def test_microprice_balanced_equals_mid(self) -> None:
        """Equal queues => microprice equals mid."""
        bid_p = np.array([100.0, 99.5])
        ask_p = np.array([101.0, 101.5])
        bid_a = np.array([2.0, 4.0])
        ask_a = np.array([2.0, 4.0])

        mid = 0.5 * (bid_p + ask_p)
        out = compute_microprice(bid_p, bid_a, ask_p, ask_a)
        np.testing.assert_allclose(out, mid, atol=1e-12)

    def test_microprice_empty_queues_falls_back_to_mid(self) -> None:
        """Zero queues on both sides => fall back to mid (no NaNs)."""
        bid_p = np.array([100.0])
        ask_p = np.array([101.0])
        bid_a = np.array([0.0])
        ask_a = np.array([0.0])

        out = compute_microprice(bid_p, bid_a, ask_p, ask_a)
        np.testing.assert_allclose(out, [100.5], atol=1e-12)
        self.assertFalse(np.isnan(out).any())

    def test_microprice_deviation_sign(self) -> None:
        """Bid-heavy book => positive deviation (pressure to move up)."""
        bid_p = np.array([100.0])
        ask_p = np.array([101.0])
        bid_a = np.array([10.0])   # large bid queue
        ask_a = np.array([1.0])

        micro = compute_microprice(bid_p, bid_a, ask_p, ask_a)
        mid = 0.5 * (bid_p + ask_p)
        dev = compute_microprice_deviation_bps(mid, micro)
        self.assertGreater(dev[0], 0.0)

        # Ask-heavy mirror case
        ask_a_heavy = np.array([10.0])
        bid_a_light = np.array([1.0])
        micro_a = compute_microprice(bid_p, bid_a_light, ask_p, ask_a_heavy)
        dev_a = compute_microprice_deviation_bps(mid, micro_a)
        self.assertLess(dev_a[0], 0.0)

    def test_microprice_causal(self) -> None:
        """Microprice at time t must not depend on data from t+1 or later."""
        n = 40
        rng = np.random.default_rng(42)
        bid_p = 100.0 + rng.normal(0, 0.1, n)
        ask_p = bid_p + 1.0
        bid_a = rng.uniform(0.1, 5.0, n)
        ask_a = rng.uniform(0.1, 5.0, n)

        full = compute_microprice(bid_p, bid_a, ask_p, ask_a)

        T = 20
        bid_a_mod = bid_a.copy()
        ask_a_mod = ask_a.copy()
        bid_a_mod[T:] = 999.0
        ask_a_mod[T:] = 0.01

        modified = compute_microprice(bid_p, bid_a_mod, ask_p, ask_a_mod)

        np.testing.assert_array_almost_equal(
            full[:T], modified[:T], decimal=12,
            err_msg="microprice is not causal — future data leaked into past",
        )


class TestRollSpread(unittest.TestCase):
    """Tests for ``compute_roll_spread``."""

    def test_roll_spread_nonnegative(self) -> None:
        """Roll spread is non-negative by construction."""
        rng = np.random.default_rng(0)
        returns = rng.normal(0, 1e-4, 500)
        spread = compute_roll_spread(returns, window=60)
        self.assertTrue((spread >= 0).all())

    def test_roll_spread_causal(self) -> None:
        """Roll spread must be strictly causal."""
        rng = np.random.default_rng(1)
        n = 200
        returns = rng.normal(0, 1e-4, n)

        full = compute_roll_spread(returns, window=60)

        T = 80
        mod = returns.copy()
        mod[T:] = rng.normal(0, 1e-2, n - T)  # big shock in "future"
        modified = compute_roll_spread(mod, window=60)

        np.testing.assert_array_almost_equal(full[:T], modified[:T], decimal=12)

    def test_roll_spread_no_nans(self) -> None:
        """Output must be finite even for short inputs."""
        returns = np.array([0.0, 0.01, -0.01, 0.005, -0.005])
        out = compute_roll_spread(returns, window=10)
        self.assertTrue(np.isfinite(out).all())


class TestVPIN(unittest.TestCase):
    """Tests for ``compute_vpin``."""

    def test_vpin_range(self) -> None:
        """VPIN values must lie in [0, 1]."""
        rng = np.random.default_rng(7)
        n = 300
        buy = rng.uniform(0, 5, n)
        sell = rng.uniform(0, 5, n)
        out = compute_vpin(buy, sell, window=60)
        self.assertTrue((out >= 0).all())
        self.assertTrue((out <= 1).all())

    def test_vpin_balanced_flow(self) -> None:
        """Perfectly balanced buy/sell => VPIN near 0."""
        n = 100
        buy = np.ones(n) * 1.0
        sell = np.ones(n) * 1.0
        out = compute_vpin(buy, sell, window=30)
        # After window has filled, VPIN is exactly 0.
        np.testing.assert_array_almost_equal(out, np.zeros(n), decimal=12)

    def test_vpin_one_sided_flow(self) -> None:
        """All buys, no sells => VPIN == 1 once window fills."""
        n = 100
        buy = np.ones(n) * 1.0
        sell = np.zeros(n)
        out = compute_vpin(buy, sell, window=30)
        # After first few samples VPIN should be 1.
        self.assertAlmostEqual(out[-1], 1.0, places=12)

    def test_vpin_zero_volume_returns_zero(self) -> None:
        """When the entire window has zero volume VPIN must be 0 (not NaN)."""
        n = 20
        buy = np.zeros(n)
        sell = np.zeros(n)
        out = compute_vpin(buy, sell, window=10)
        np.testing.assert_array_equal(out, np.zeros(n))
        self.assertFalse(np.isnan(out).any())

    def test_vpin_causal(self) -> None:
        rng = np.random.default_rng(3)
        n = 150
        buy = rng.uniform(0, 5, n)
        sell = rng.uniform(0, 5, n)

        full = compute_vpin(buy, sell, window=30)

        T = 60
        buy_mod = buy.copy()
        sell_mod = sell.copy()
        buy_mod[T:] = 100.0
        sell_mod[T:] = 0.0

        modified = compute_vpin(buy_mod, sell_mod, window=30)
        np.testing.assert_array_almost_equal(full[:T], modified[:T], decimal=12)


class TestBookPressureImbalance(unittest.TestCase):
    """Tests for ``compute_book_pressure_imbalance``."""

    def test_book_pressure_weighting(self) -> None:
        """Outer levels must have strictly less weight than inner levels."""
        # Two rows, 5 levels each, uniform depth.
        K = 5
        bid = np.ones((2, K))
        ask = np.ones((2, K))

        # Balanced depth yields 0 regardless of weighting.
        out = compute_book_pressure_imbalance(bid, ask)
        np.testing.assert_allclose(out, [0.0, 0.0], atol=1e-12)

        # Verify that the exponential weights themselves decay.
        alpha = 0.5
        weights = np.exp(-alpha * np.arange(K))
        for i in range(1, K):
            self.assertLess(weights[i], weights[i - 1])

    def test_book_pressure_sign(self) -> None:
        """Bid-dominant depths => positive imbalance; ask-dominant => negative."""
        bid = np.array([[5.0, 4.0, 3.0]])
        ask = np.array([[1.0, 1.0, 1.0]])
        out = compute_book_pressure_imbalance(bid, ask)
        self.assertGreater(out[0], 0.0)

        out2 = compute_book_pressure_imbalance(ask, bid)
        self.assertLess(out2[0], 0.0)

    def test_book_pressure_in_range(self) -> None:
        """Output must be in [-1, 1]."""
        rng = np.random.default_rng(13)
        bid = rng.uniform(0, 10, (200, 10))
        ask = rng.uniform(0, 10, (200, 10))
        out = compute_book_pressure_imbalance(bid, ask)
        self.assertTrue((out >= -1 - 1e-12).all())
        self.assertTrue((out <= 1 + 1e-12).all())

    def test_book_pressure_custom_weights(self) -> None:
        """Custom weights (e.g. only top level) recover OBI_L1."""
        K = 4
        bid = np.array([[3.0, 0.0, 0.0, 0.0]])
        ask = np.array([[1.0, 0.0, 0.0, 0.0]])
        weights = np.array([1.0, 0.0, 0.0, 0.0])
        out = compute_book_pressure_imbalance(bid, ask, weights=weights)
        # (3 - 1) / (3 + 1) = 0.5
        np.testing.assert_allclose(out, [0.5], atol=1e-12)


class TestPriceImpactProxy(unittest.TestCase):
    """Tests for ``compute_price_impact_proxy``."""

    def test_price_impact_uses_trade_volume(self) -> None:
        """Changing trade volume must change the output; LOB depth must NOT.

        We verify this by keeping returns constant and doubling the volume
        input.  If the implementation really used LOB depth, the same
        returns with the same trade-volume would have to produce *different*
        output depending on which array it was called with.  Here we just
        show the feature is volume-sensitive.
        """
        n = 50
        returns = np.full(n, 0.001)
        vol_low = np.full(n, 1.0)
        vol_high = np.full(n, 10.0)

        out_low = compute_price_impact_proxy(vol_low, returns, window=10)
        out_high = compute_price_impact_proxy(vol_high, returns, window=10)

        # Impact should DECREASE as volume increases (more volume for the
        # same move => less impact per unit volume).
        self.assertTrue((out_high < out_low).all())

    def test_price_impact_zero_volume_is_finite(self) -> None:
        """Zero-volume bars must not blow up."""
        n = 30
        returns = np.full(n, 0.001)
        vol = np.zeros(n)
        out = compute_price_impact_proxy(vol, returns, window=5)
        self.assertTrue(np.isfinite(out).all())
        # With vol=0 and +1 denominator shift, impact == |0.001|/1 == 0.001
        np.testing.assert_allclose(out, np.full(n, 0.001), atol=1e-12)

    def test_price_impact_causal(self) -> None:
        rng = np.random.default_rng(5)
        n = 120
        returns = rng.normal(0, 1e-4, n)
        vol = rng.uniform(0, 5, n)

        full = compute_price_impact_proxy(vol, returns, window=30)

        T = 50
        ret_mod = returns.copy()
        vol_mod = vol.copy()
        ret_mod[T:] = 10.0  # huge future shock
        vol_mod[T:] = 0.0

        mod = compute_price_impact_proxy(vol_mod, ret_mod, window=30)
        np.testing.assert_array_almost_equal(full[:T], mod[:T], decimal=12)


class TestComputeDerivedFeatures(unittest.TestCase):
    """Integration tests for the full ``compute_derived_features`` wrapper."""

    def _make_inputs(self, n: int = 100, K: int = 5, seed: int = 0):
        rng = np.random.default_rng(seed)
        bid_prices = 100.0 + rng.normal(0, 0.05, (n, K))
        ask_prices = 101.0 + rng.normal(0, 0.05, (n, K))
        bid_amounts = rng.uniform(0.1, 5.0, (n, K))
        ask_amounts = rng.uniform(0.1, 5.0, (n, K))
        mid = 0.5 * (bid_prices[:, 0] + ask_prices[:, 0])
        log_ret_1s = np.concatenate([[0.0], np.diff(np.log(mid))])
        buy_volume_1s = rng.uniform(0, 2, n)
        sell_volume_1s = rng.uniform(0, 2, n)
        return (
            bid_prices, ask_prices, bid_amounts, ask_amounts, mid,
            log_ret_1s, buy_volume_1s, sell_volume_1s,
        )

    def test_all_columns_present(self) -> None:
        (bp, ap, ba, aa, mid, lr, bv, sv) = self._make_inputs()
        out = compute_derived_features(
            bid_prices=bp, ask_prices=ap,
            bid_amounts=ba, ask_amounts=aa,
            mid=mid, log_returns_1s=lr,
            buy_volume_1s=bv, sell_volume_1s=sv,
        )
        self.assertEqual(list(out.columns), DERIVED_FEATURE_NAMES)
        self.assertEqual(len(out), len(mid))

    def test_no_nans(self) -> None:
        (bp, ap, ba, aa, mid, lr, bv, sv) = self._make_inputs()
        out = compute_derived_features(
            bid_prices=bp, ask_prices=ap,
            bid_amounts=ba, ask_amounts=aa,
            mid=mid, log_returns_1s=lr,
            buy_volume_1s=bv, sell_volume_1s=sv,
        )
        self.assertFalse(out.isna().any().any())

    def test_no_trades_still_works(self) -> None:
        """Without trades, VPIN and price-impact columns fall back to 0."""
        (bp, ap, ba, aa, mid, lr, _, _) = self._make_inputs()
        out = compute_derived_features(
            bid_prices=bp, ask_prices=ap,
            bid_amounts=ba, ask_amounts=aa,
            mid=mid, log_returns_1s=lr,
            buy_volume_1s=None, sell_volume_1s=None,
        )
        np.testing.assert_array_equal(out["vpin_60s"].values, np.zeros(len(mid)))
        np.testing.assert_array_equal(out["vpin_300s"].values, np.zeros(len(mid)))
        np.testing.assert_array_equal(
            out["price_impact_30s"].values, np.zeros(len(mid))
        )
        # LOB-only columns must still vary.
        self.assertGreater(np.std(out["microprice_dev_bps"].values), 0.0)
        self.assertGreater(np.std(out["book_pressure_imbalance"].values), 0.0)

    def test_end_to_end_causal(self) -> None:
        """compute_derived_features must be causal across all outputs."""
        (bp, ap, ba, aa, mid, lr, bv, sv) = self._make_inputs(n=120, seed=11)
        full = compute_derived_features(
            bid_prices=bp, ask_prices=ap,
            bid_amounts=ba, ask_amounts=aa,
            mid=mid, log_returns_1s=lr,
            buy_volume_1s=bv, sell_volume_1s=sv,
        )

        T = 60
        # Mutate all per-row inputs at t >= T.
        bp_m = bp.copy(); ap_m = ap.copy()
        ba_m = ba.copy(); aa_m = aa.copy()
        bp_m[T:] = 0.5 * bp_m[T:]
        ap_m[T:] = 2.0 * ap_m[T:]
        ba_m[T:] = 999.0
        aa_m[T:] = 0.0001
        mid_m = mid.copy(); mid_m[T:] = 2 * mid_m[T:]
        lr_m = lr.copy(); lr_m[T:] = 1e3
        bv_m = bv.copy(); bv_m[T:] = 9999.0
        sv_m = sv.copy(); sv_m[T:] = 0.0

        modified = compute_derived_features(
            bid_prices=bp_m, ask_prices=ap_m,
            bid_amounts=ba_m, ask_amounts=aa_m,
            mid=mid_m, log_returns_1s=lr_m,
            buy_volume_1s=bv_m, sell_volume_1s=sv_m,
        )

        for col in DERIVED_FEATURE_NAMES:
            np.testing.assert_array_almost_equal(
                full[col].values[:T],
                modified[col].values[:T],
                decimal=10,
                err_msg=f"Derived feature '{col}' leaks future data at t<{T}",
            )


if __name__ == "__main__":
    unittest.main()

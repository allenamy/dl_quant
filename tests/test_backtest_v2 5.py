"""Tests for the production backtest engine (backtest_v2) and analysis helpers."""

from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
import pytest

from src.evaluation.backtest_v2 import BacktestEngine, BacktestResult
from src.evaluation.backtest_analysis import (
    analyze_by_regime,
    analyze_by_hour,
    compare_models,
    optimal_threshold_search,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_data(
    n: int = 200,
    seed: int = 42,
    signal_strength: float = 1.0,
):
    """Create synthetic predictions and targets for testing.

    Returns (predictions, targets, mask) where predictions are (N, 3)
    quantile predictions and targets are (N,) realized returns.
    Signal is: targets = signal_strength * q50 + noise.
    """
    rng = np.random.RandomState(seed)

    # q50 as the signal
    q50 = rng.randn(n) * 0.1
    # q10 = q50 - spread, q90 = q50 + spread
    spread = np.abs(rng.randn(n)) * 0.05 + 0.01  # always positive
    q10 = q50 - spread
    q90 = q50 + spread
    predictions = np.column_stack([q10, q50, q90])

    # Targets correlated with q50
    noise = rng.randn(n) * 0.05
    targets = signal_strength * q50 + noise

    # All observations valid
    mask = np.ones(n, dtype=bool)

    return predictions, targets, mask


# ===========================================================================
# TestBacktestEngine
# ===========================================================================


class TestBacktestEngine:

    def test_no_signal_no_trades(self):
        """Zero predictions should produce zero trades."""
        n = 100
        predictions = np.zeros((n, 3))
        targets = np.random.randn(n) * 0.01
        mask = np.ones(n, dtype=bool)

        engine = BacktestEngine(signal_threshold=0.01)
        result = engine.run(predictions, targets, mask)

        assert result.n_trades == 0
        assert result.trade_rate == 0.0
        assert result.gross_pnl_bps == 0.0
        assert result.net_pnl_bps == 0.0
        assert result.total_cost_bps == 0.0

    def test_perfect_signal(self):
        """Perfect predictions should yield positive P&L."""
        n = 200
        rng = np.random.RandomState(123)
        targets = rng.randn(n) * 0.1
        # Perfect signal: q50 = actual target
        spread = 0.02
        predictions = np.column_stack([
            targets - spread,
            targets,
            targets + spread,
        ])
        mask = np.ones(n, dtype=bool)

        engine = BacktestEngine(fee_bps=0.0, slippage_bps=0.0)
        result = engine.run(predictions, targets, mask)

        # With zero costs and perfect signal, gross P&L should be positive
        assert result.gross_pnl_bps > 0, (
            f"Perfect signal should yield positive gross P&L, got {result.gross_pnl_bps}"
        )
        assert result.net_pnl_bps > 0, (
            f"Perfect signal with zero costs should yield positive net P&L"
        )

    def test_inverted_signal(self):
        """Anti-correlated predictions should yield negative P&L."""
        n = 200
        rng = np.random.RandomState(123)
        targets = rng.randn(n) * 0.1
        # Anti-signal: q50 = -target (inverted)
        spread = 0.02
        predictions = np.column_stack([
            -targets - spread,
            -targets,
            -targets + spread,
        ])
        mask = np.ones(n, dtype=bool)

        engine = BacktestEngine(fee_bps=0.0, slippage_bps=0.0)
        result = engine.run(predictions, targets, mask)

        # Anti-correlated signal should lose money
        assert result.gross_pnl_bps < 0, (
            f"Inverted signal should yield negative P&L, got {result.gross_pnl_bps}"
        )

    def test_fee_impact(self):
        """Higher fees should reduce net P&L."""
        predictions, targets, mask = _make_data(n=200, signal_strength=1.0)

        engine_low = BacktestEngine(fee_bps=1.0, slippage_bps=0.0)
        engine_high = BacktestEngine(fee_bps=10.0, slippage_bps=0.0)

        result_low = engine_low.run(predictions, targets, mask)
        result_high = engine_high.run(predictions, targets, mask)

        # Same gross P&L (same positions)
        assert abs(result_low.gross_pnl_bps - result_high.gross_pnl_bps) < 1e-10

        # Higher fees -> higher costs
        assert result_high.total_cost_bps > result_low.total_cost_bps

        # Higher fees -> lower net P&L
        assert result_high.net_pnl_bps < result_low.net_pnl_bps

    def test_confidence_sizing(self):
        """Wider quantile spread should reduce position size."""
        n = 100
        rng = np.random.RandomState(42)

        q50 = np.ones(n) * 0.1  # consistent positive signal

        # Narrow spread -> high confidence
        preds_narrow = np.column_stack([
            q50 - 0.01,
            q50,
            q50 + 0.01,
        ])

        # Wide spread -> low confidence
        preds_wide = np.column_stack([
            q50 - 1.0,
            q50,
            q50 + 1.0,
        ])

        targets = rng.randn(n) * 0.01
        mask = np.ones(n, dtype=bool)

        engine = BacktestEngine(
            fee_bps=0.0, slippage_bps=0.0, confidence_sizing=True
        )

        result_narrow = engine.run(preds_narrow, targets, mask)
        result_wide = engine.run(preds_wide, targets, mask)

        # Narrow spread should have larger average position
        avg_pos_narrow = np.mean(np.abs(result_narrow.position_timeseries))
        avg_pos_wide = np.mean(np.abs(result_wide.position_timeseries))

        assert avg_pos_narrow > avg_pos_wide, (
            f"Narrow spread ({avg_pos_narrow:.4f}) should have larger "
            f"positions than wide spread ({avg_pos_wide:.4f})"
        )

    def test_threshold_filtering(self):
        """Higher threshold should reduce trade count."""
        predictions, targets, mask = _make_data(n=200, signal_strength=0.5)

        engine_low = BacktestEngine(signal_threshold=0.01)
        engine_high = BacktestEngine(signal_threshold=0.2)

        result_low = engine_low.run(predictions, targets, mask)
        result_high = engine_high.run(predictions, targets, mask)

        assert result_high.trade_rate <= result_low.trade_rate, (
            f"Higher threshold should reduce trades: "
            f"low={result_low.trade_rate:.4f}, high={result_high.trade_rate:.4f}"
        )

    def test_position_constraints(self):
        """Position should never exceed max_position."""
        predictions, targets, mask = _make_data(n=200)
        max_pos = 0.5

        engine = BacktestEngine(
            max_position=max_pos, confidence_sizing=True
        )
        result = engine.run(predictions, targets, mask)

        max_observed = np.max(np.abs(result.position_timeseries))
        assert max_observed <= max_pos + 1e-10, (
            f"Max position {max_observed:.4f} exceeds limit {max_pos}"
        )

    def test_pnl_timeseries_length(self):
        """P&L timeseries should match number of valid periods."""
        n = 150
        predictions, targets, mask = _make_data(n=n)

        # Mask out some periods
        mask[10:20] = False
        mask[50:55] = False

        engine = BacktestEngine()
        result = engine.run(predictions, targets, mask)

        n_valid = int(np.sum(mask))
        assert len(result.pnl_timeseries) == n_valid, (
            f"P&L timeseries length ({len(result.pnl_timeseries)}) != "
            f"valid periods ({n_valid})"
        )
        assert len(result.drawdown_timeseries) == n_valid
        assert len(result.position_timeseries) == n_valid

    def test_result_to_dict(self):
        """Result should be JSON-serializable."""
        predictions, targets, mask = _make_data(n=100)
        engine = BacktestEngine()
        result = engine.run(predictions, targets, mask)

        d = result.to_dict()

        # All values should be JSON-serializable
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

        # Check all expected keys are present
        expected_keys = {
            "n_periods", "n_trades", "trade_rate",
            "gross_pnl_bps", "total_cost_bps", "net_pnl_bps",
            "avg_pnl_per_trade_bps",
            "sharpe_annual", "max_drawdown_bps", "calmar_ratio",
            "win_rate", "profit_factor",
        }
        assert set(d.keys()) == expected_keys

    def test_result_summary_string(self):
        """Summary should produce a readable string."""
        predictions, targets, mask = _make_data(n=100)
        engine = BacktestEngine()
        result = engine.run(predictions, targets, mask)

        s = result.summary()
        assert "BACKTEST RESULTS" in s
        assert "Sharpe" in s
        assert "Net P&L" in s

    def test_empty_mask(self):
        """All-False mask should return an empty result gracefully."""
        n = 50
        predictions = np.random.randn(n, 3)
        targets = np.random.randn(n)
        mask = np.zeros(n, dtype=bool)

        engine = BacktestEngine()
        result = engine.run(predictions, targets, mask)

        assert result.n_periods == 0
        assert result.n_trades == 0
        assert result.net_pnl_bps == 0.0

    def test_single_column_predictions(self):
        """Engine should handle 1D predictions (q50 only)."""
        n = 100
        rng = np.random.RandomState(42)
        q50 = rng.randn(n) * 0.1
        targets = q50 + rng.randn(n) * 0.05
        mask = np.ones(n, dtype=bool)

        engine = BacktestEngine(fee_bps=0.0, slippage_bps=0.0)
        result = engine.run(q50, targets, mask)

        assert result.n_periods == n
        assert result.n_trades > 0

    def test_binary_sizing_mode(self):
        """Without confidence sizing, all positions should have same magnitude."""
        n = 100
        q50 = np.ones(n) * 0.1
        predictions = np.column_stack([
            q50 - 0.02,
            q50,
            q50 + 0.02,
        ])
        targets = np.random.randn(n) * 0.01
        mask = np.ones(n, dtype=bool)

        engine = BacktestEngine(
            confidence_sizing=False, max_position=0.7
        )
        result = engine.run(predictions, targets, mask)

        active = result.position_timeseries != 0
        if np.any(active):
            active_sizes = np.abs(result.position_timeseries[active])
            # All active positions should be exactly max_position
            np.testing.assert_allclose(
                active_sizes, 0.7,
                err_msg="Binary sizing should produce uniform position sizes",
            )

    def test_trade_log_structure(self):
        """Trade log should be a DataFrame with required columns."""
        predictions, targets, mask = _make_data(n=100)
        engine = BacktestEngine()
        result = engine.run(predictions, targets, mask)

        assert isinstance(result.trade_log, pd.DataFrame)
        required_cols = {"period_idx", "direction", "size", "signal_q50",
                         "net_pnl", "cost"}
        assert required_cols.issubset(set(result.trade_log.columns))

    def test_drawdown_non_negative(self):
        """Drawdown should always be >= 0."""
        predictions, targets, mask = _make_data(n=200)
        engine = BacktestEngine()
        result = engine.run(predictions, targets, mask)

        assert np.all(result.drawdown_timeseries >= -1e-15), (
            "Drawdown should never be negative"
        )

    def test_validation_errors(self):
        """Invalid parameters should raise ValueError."""
        with pytest.raises(ValueError):
            BacktestEngine(fee_bps=-1.0)
        with pytest.raises(ValueError):
            BacktestEngine(slippage_bps=-1.0)
        with pytest.raises(ValueError):
            BacktestEngine(max_position=0.0)
        with pytest.raises(ValueError):
            BacktestEngine(signal_threshold=-0.1)

    def test_mismatched_lengths(self):
        """Mismatched array lengths should raise ValueError."""
        engine = BacktestEngine()
        with pytest.raises(ValueError, match="same length"):
            engine.run(
                np.zeros((10, 3)),
                np.zeros(5),
                np.ones(10, dtype=bool),
            )
        with pytest.raises(ValueError, match="same length"):
            engine.run(
                np.zeros((10, 3)),
                np.zeros(10),
                np.ones(5, dtype=bool),
            )


# ===========================================================================
# TestBacktestAnalysis
# ===========================================================================


class TestBacktestAnalysis:

    def test_optimal_threshold_returns_best(self):
        """Grid search should find the threshold that maximizes Sharpe."""
        predictions, targets, mask = _make_data(n=300, signal_strength=0.8)

        result = optimal_threshold_search(
            predictions, targets, mask,
            fee_bps=2.0, slippage_bps=0.0,
            thresholds=np.linspace(0, 0.3, 11),
        )

        assert "best_threshold" in result
        assert "best_sharpe" in result
        assert "best_net_pnl" in result
        assert "results_df" in result

        df = result["results_df"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 11  # one row per threshold
        assert "threshold" in df.columns
        assert "sharpe" in df.columns

        # The best_sharpe should equal the max sharpe in the DataFrame
        assert abs(result["best_sharpe"] - df["sharpe"].max()) < 1e-10

    def test_compare_models_output(self):
        """Comparison should produce a DataFrame with one row per model."""
        predictions, targets, mask = _make_data(n=100)

        engine_a = BacktestEngine(fee_bps=2.0)
        engine_b = BacktestEngine(fee_bps=5.0)

        results = {
            "model_A": engine_a.run(predictions, targets, mask),
            "model_B": engine_b.run(predictions, targets, mask),
        }

        df = compare_models(results)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "model_A" in df.index
        assert "model_B" in df.index
        assert "net_pnl_bps" in df.columns
        assert "sharpe_annual" in df.columns

    def test_analyze_by_regime(self):
        """Regime analysis should produce results for each regime."""
        predictions, targets, mask = _make_data(n=200)
        engine = BacktestEngine()
        result = engine.run(predictions, targets, mask)

        # Create a volatility series
        vol = np.abs(targets)  # use abs returns as proxy for vol

        regime_results = analyze_by_regime(result, vol, n_regimes=3)

        assert "low" in regime_results
        assert "medium" in regime_results
        assert "high" in regime_results

        for name, r in regime_results.items():
            assert "n_periods" in r
            assert "net_pnl" in r
            assert "sharpe" in r
            assert "win_rate" in r

    def test_analyze_by_hour(self):
        """Hour analysis should produce results for hours with data."""
        predictions, targets, mask = _make_data(n=200)
        engine = BacktestEngine()
        result = engine.run(predictions, targets, mask)

        # Create fake timestamps spanning multiple hours
        base_ts = 1_700_000_000_000_000  # microseconds
        interval_us = 3 * 60 * 1_000_000  # 3 minutes in microseconds
        timestamps = np.arange(200, dtype=np.int64) * interval_us + base_ts

        # Only pass valid timestamps (matching result length)
        valid_ts = timestamps[mask]

        hour_results = analyze_by_hour(result, valid_ts)

        # Should have entries for hours covered by the timestamps
        assert len(hour_results) == 24
        for h in range(24):
            assert h in hour_results
            r = hour_results[h]
            assert "n_periods" in r

    def test_compare_models_empty(self):
        """Empty comparison should return empty DataFrame."""
        df = compare_models({})
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_regime_analysis_empty_result(self):
        """Regime analysis with empty result should return empty dict."""
        result = BacktestResult()  # empty
        vol = np.array([])
        regime_results = analyze_by_regime(result, vol)
        assert regime_results == {}

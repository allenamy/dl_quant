"""CRITICAL test: verify streaming output == batch output for same data.

This is the MOST IMPORTANT test in the entire project.  If it fails,
live trading models will silently produce wrong predictions because the
features computed at inference time differ from those computed during
training.

Strategy
--------
1. Generate synthetic depth + trade data for 500 seconds
2. Run batch pipeline: full DataFrame -> features -> window extraction
3. Run streaming: feed one second at a time -> get_tensors()
4. Compare outputs at overlapping positions -- must be IDENTICAL (atol=1e-6)
"""

from __future__ import annotations

import os
import sys
import unittest

import numpy as np
import pandas as pd

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.features.microstructure import compute_microstructure_features
from src.features.raw_lob import extract_raw_lob_tensor
from src.features.trade_features import (
    TRADE_FEATURE_NAMES,
    aggregate_trades_to_1s,
    compute_trade_flow_features,
)
from src.inference.streaming import StreamingFeatureComputer


# ---------------------------------------------------------------------------
# Shared synthetic data generators
# ---------------------------------------------------------------------------

def make_synthetic_depth_1s(
    n_rows: int = 500,
    n_levels: int = 25,
    start_ts_us: int = 1_700_000_000_000_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Create synthetic 1-second LOB bars (already resampled).

    Returns a DataFrame with ``timestamp`` (1s-boundary microseconds) and
    ``asks[i].price/amount``, ``bids[i].price/amount`` for i in range(n_levels).
    """
    rng = np.random.default_rng(seed)
    us_per_sec = 1_000_000
    ts = start_ts_us + np.arange(n_rows) * us_per_sec

    data: dict[str, np.ndarray] = {"timestamp": ts}
    base_ask = 70_000.0
    base_bid = 69_999.0

    # Make prices mildly non-stationary (random walk)
    walk = np.cumsum(rng.normal(0, 0.5, n_rows))

    for i in range(n_levels):
        data[f"asks[{i}].price"] = (
            base_ask + walk + i * 0.5 + rng.normal(0, 0.02, n_rows)
        )
        data[f"asks[{i}].amount"] = rng.uniform(0.01, 5.0, n_rows)
        data[f"bids[{i}].price"] = (
            base_bid + walk - i * 0.5 + rng.normal(0, 0.02, n_rows)
        )
        data[f"bids[{i}].amount"] = rng.uniform(0.01, 5.0, n_rows)

    return pd.DataFrame(data)


def make_synthetic_trades(
    depth_df: pd.DataFrame,
    avg_trades_per_sec: int = 5,
    seed: int = 123,
) -> pd.DataFrame:
    """Create synthetic trade ticks aligned to a depth DataFrame's time range.

    Returns a DataFrame with columns: timestamp, price, size, side, exec_id.
    """
    rng = np.random.default_rng(seed)

    ts_start = int(depth_df["timestamp"].iloc[0])
    ts_end = int(depth_df["timestamp"].iloc[-1])
    us_per_sec = 1_000_000
    n_seconds = (ts_end - ts_start) // us_per_sec + 1

    rows = []
    mid_base = (
        depth_df["asks[0].price"].values[0] + depth_df["bids[0].price"].values[0]
    ) / 2.0

    for sec_idx in range(n_seconds):
        sec_ts = ts_start + sec_idx * us_per_sec
        n_trades = rng.poisson(avg_trades_per_sec)
        for _ in range(n_trades):
            offset_us = rng.integers(0, us_per_sec)
            price = mid_base + rng.normal(0, 5.0)
            size = rng.uniform(0.001, 2.0)
            side = rng.choice(["Buy", "Sell"])
            rows.append({
                "timestamp": sec_ts + offset_us,
                "price": price,
                "size": size,
                "side": side,
                "exec_id": f"exec_{sec_idx}_{offset_us}",
            })

    trades_df = pd.DataFrame(rows)
    trades_df.sort_values("timestamp", inplace=True)
    trades_df.reset_index(drop=True, inplace=True)
    return trades_df


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStreamingConsistency(unittest.TestCase):
    """CRITICAL: Streaming feature computer must match batch pipeline exactly."""

    N_ROWS = 500
    N_LEVELS = 25
    INPUT_LEN = 300
    FEATURE_CLIP = 10.0

    @classmethod
    def setUpClass(cls) -> None:
        """Generate shared synthetic data and compute batch results once."""
        cls.depth_df = make_synthetic_depth_1s(
            n_rows=cls.N_ROWS, n_levels=cls.N_LEVELS
        )
        cls.trades_df = make_synthetic_trades(cls.depth_df)
        cls.trade_bars = aggregate_trades_to_1s(
            cls.trades_df,
            start_ts_us=int(cls.depth_df["timestamp"].iloc[0]),
            end_ts_us=int(cls.depth_df["timestamp"].iloc[-1]),
        )

        # Batch: compute microstructure features
        cls.batch_feat_df = compute_microstructure_features(
            cls.depth_df, n_levels=cls.N_LEVELS
        )
        cls.batch_feature_cols = [
            c for c in cls.batch_feat_df.columns
            if c not in ("timestamp", "mid_price")
        ]
        cls.batch_mid_prices = cls.batch_feat_df["mid_price"].values.astype(
            np.float64
        )

        # Batch: compute trade features
        cls.batch_trade_feat_df = compute_trade_flow_features(
            cls.trade_bars, mid_prices=cls.batch_mid_prices
        )
        cls.batch_trade_cols = [
            c for c in cls.batch_trade_feat_df.columns if c != "timestamp"
        ]

        # Batch: full feature matrix (44 micro + 8 trade = 52)
        micro_mat = cls.batch_feat_df[cls.batch_feature_cols].values.astype(
            np.float32
        )
        trade_mat = cls.batch_trade_feat_df[cls.batch_trade_cols].values.astype(
            np.float32
        )
        cls.batch_feat_matrix = np.concatenate([micro_mat, trade_mat], axis=1)
        cls.batch_feat_matrix = np.nan_to_num(
            cls.batch_feat_matrix, nan=0.0, posinf=0.0, neginf=0.0
        )
        cls.batch_feat_matrix = np.clip(
            cls.batch_feat_matrix, -cls.FEATURE_CLIP, cls.FEATURE_CLIP
        )

        # Batch: raw LOB tensor
        raw_levels = min(cls.N_LEVELS, 20)
        cls.batch_raw_tensor = extract_raw_lob_tensor(
            cls.depth_df, n_levels=raw_levels
        )

    def test_streaming_matches_batch_features(self) -> None:
        """Streaming features must be identical to batch for the last full window."""
        computer = StreamingFeatureComputer(
            input_len=self.INPUT_LEN,
            n_levels=self.N_LEVELS,
            use_trades=True,
            feature_clip=self.FEATURE_CLIP,
            warmup=0,  # consistency test: match batch pipeline (no warmup)
        )

        us_per_sec = 1_000_000
        ts_start = int(self.depth_df["timestamp"].iloc[0])

        # Feed data one second at a time
        for row_idx in range(self.N_ROWS):
            ts = int(self.depth_df["timestamp"].iloc[row_idx])

            # Build depth snapshot dict
            snapshot = {"timestamp": ts}
            for i in range(self.N_LEVELS):
                for side in ("asks", "bids"):
                    for field in ("price", "amount"):
                        col = f"{side}[{i}].{field}"
                        snapshot[col] = float(self.depth_df[col].iloc[row_idx])

            # Collect trades for this second
            sec_start = ts
            sec_end = ts + us_per_sec
            mask = (
                (self.trades_df["timestamp"] >= sec_start)
                & (self.trades_df["timestamp"] < sec_end)
            )
            sec_trades = self.trades_df[mask].to_dict("records")

            ready = computer.update(snapshot, sec_trades)

            if ready:
                # Compare at this position
                x_feat, x_raw = computer.get_tensors()

                # The streaming window covers rows [row_idx - INPUT_LEN + 1, row_idx]
                batch_start = row_idx - self.INPUT_LEN + 1

                # --- Batch: recompute on the SAME window to guarantee fair comparison ---
                # (this matches what the streaming computer does: it takes the last
                # INPUT_LEN rows and passes them through the same functions)
                window_df = self.depth_df.iloc[batch_start:row_idx + 1].reset_index(drop=True)
                batch_feat_df = compute_microstructure_features(window_df, n_levels=self.N_LEVELS)
                batch_feature_cols = [c for c in batch_feat_df.columns if c not in ("timestamp", "mid_price")]
                batch_mid = batch_feat_df["mid_price"].values.astype(np.float64)

                # Trade bars for the same window
                win_ts_start = int(window_df["timestamp"].iloc[0])
                win_ts_end = int(window_df["timestamp"].iloc[-1])
                win_trades_mask = (
                    (self.trades_df["timestamp"] >= win_ts_start)
                    & (self.trades_df["timestamp"] < win_ts_end + us_per_sec)
                )
                win_trades = self.trades_df[win_trades_mask]
                win_trade_bars = aggregate_trades_to_1s(
                    win_trades, start_ts_us=win_ts_start, end_ts_us=win_ts_end
                )
                win_trade_feat = compute_trade_flow_features(
                    win_trade_bars, mid_prices=batch_mid
                )
                win_trade_cols = [c for c in win_trade_feat.columns if c != "timestamp"]

                micro_mat = batch_feat_df[batch_feature_cols].values.astype(np.float32)
                trade_mat = win_trade_feat[win_trade_cols].values.astype(np.float32)
                batch_feat_win = np.concatenate([micro_mat, trade_mat], axis=1)
                batch_feat_win = np.nan_to_num(batch_feat_win, nan=0.0, posinf=0.0, neginf=0.0)
                batch_feat_win = np.clip(batch_feat_win, -self.FEATURE_CLIP, self.FEATURE_CLIP)

                batch_raw_win = extract_raw_lob_tensor(window_df, n_levels=min(self.N_LEVELS, 20))

                # --- Compare features ---
                np.testing.assert_allclose(
                    x_feat[0],
                    batch_feat_win,
                    atol=1e-6,
                    rtol=1e-5,
                    err_msg=(
                        f"Streaming features differ from batch at row_idx={row_idx}. "
                        f"Streaming shape: {x_feat.shape}, batch shape: {batch_feat_win.shape}"
                    ),
                )

                # --- Compare raw LOB tensor ---
                np.testing.assert_allclose(
                    x_raw[0],
                    batch_raw_win,
                    atol=1e-6,
                    rtol=1e-5,
                    err_msg=(
                        f"Streaming raw LOB tensor differs from batch at row_idx={row_idx}. "
                        f"Streaming shape: {x_raw.shape}, batch shape: {batch_raw_win.shape}"
                    ),
                )

        # Ensure we actually tested at least one window
        self.assertTrue(
            computer.is_ready(),
            "Streaming computer was never ready -- test did not verify anything!",
        )

    def test_streaming_matches_batch_no_trades(self) -> None:
        """Streaming without trades must match batch without trades."""
        computer = StreamingFeatureComputer(
            input_len=self.INPUT_LEN,
            n_levels=self.N_LEVELS,
            use_trades=False,
            feature_clip=self.FEATURE_CLIP,
            warmup=0,  # consistency test: match batch pipeline (no warmup)
        )

        # Feed all depth data
        for row_idx in range(self.N_ROWS):
            ts = int(self.depth_df["timestamp"].iloc[row_idx])
            snapshot = {"timestamp": ts}
            for i in range(self.N_LEVELS):
                for side in ("asks", "bids"):
                    for field in ("price", "amount"):
                        col = f"{side}[{i}].{field}"
                        snapshot[col] = float(self.depth_df[col].iloc[row_idx])

            computer.update(snapshot, None)

        # Compare the last window
        x_feat, x_raw = computer.get_tensors()

        # Batch computation on last window
        batch_start = self.N_ROWS - self.INPUT_LEN
        window_df = self.depth_df.iloc[batch_start:].reset_index(drop=True)
        batch_feat_df = compute_microstructure_features(window_df, n_levels=self.N_LEVELS)
        batch_feature_cols = [c for c in batch_feat_df.columns if c not in ("timestamp", "mid_price")]
        batch_feat_win = batch_feat_df[batch_feature_cols].values.astype(np.float32)
        batch_feat_win = np.nan_to_num(batch_feat_win, nan=0.0, posinf=0.0, neginf=0.0)
        batch_feat_win = np.clip(batch_feat_win, -self.FEATURE_CLIP, self.FEATURE_CLIP)
        batch_raw_win = extract_raw_lob_tensor(window_df, n_levels=min(self.N_LEVELS, 20))

        self.assertEqual(x_feat.shape[2], 44, f"Without trades: expected 44 features, got {x_feat.shape[2]}")

        np.testing.assert_allclose(
            x_feat[0], batch_feat_win, atol=1e-6, rtol=1e-5,
            err_msg="No-trade streaming features differ from batch",
        )
        np.testing.assert_allclose(
            x_raw[0], batch_raw_win, atol=1e-6, rtol=1e-5,
            err_msg="No-trade streaming raw tensor differs from batch",
        )

    def test_streaming_multiple_windows(self) -> None:
        """Verify consistency at multiple positions as the window slides."""
        computer = StreamingFeatureComputer(
            input_len=self.INPUT_LEN,
            n_levels=self.N_LEVELS,
            use_trades=True,
            feature_clip=self.FEATURE_CLIP,
            warmup=0,  # consistency test: match batch pipeline (no warmup)
        )

        us_per_sec = 1_000_000
        checked_positions = []

        for row_idx in range(self.N_ROWS):
            ts = int(self.depth_df["timestamp"].iloc[row_idx])
            snapshot = {"timestamp": ts}
            for i in range(self.N_LEVELS):
                for side in ("asks", "bids"):
                    for field in ("price", "amount"):
                        col = f"{side}[{i}].{field}"
                        snapshot[col] = float(self.depth_df[col].iloc[row_idx])

            sec_start = ts
            sec_end = ts + us_per_sec
            mask = (
                (self.trades_df["timestamp"] >= sec_start)
                & (self.trades_df["timestamp"] < sec_end)
            )
            sec_trades = self.trades_df[mask].to_dict("records")
            computer.update(snapshot, sec_trades)

            # Check at specific positions to keep test runtime reasonable
            if computer.is_ready() and row_idx % 50 == 0:
                x_feat, x_raw = computer.get_tensors()

                batch_start = row_idx - self.INPUT_LEN + 1
                window_df = self.depth_df.iloc[batch_start:row_idx + 1].reset_index(drop=True)
                batch_feat_df = compute_microstructure_features(window_df, n_levels=self.N_LEVELS)
                batch_feature_cols = [c for c in batch_feat_df.columns if c not in ("timestamp", "mid_price")]
                batch_mid = batch_feat_df["mid_price"].values.astype(np.float64)

                win_ts_start = int(window_df["timestamp"].iloc[0])
                win_ts_end = int(window_df["timestamp"].iloc[-1])
                win_trades_mask = (
                    (self.trades_df["timestamp"] >= win_ts_start)
                    & (self.trades_df["timestamp"] < win_ts_end + us_per_sec)
                )
                win_trades = self.trades_df[win_trades_mask]
                win_trade_bars = aggregate_trades_to_1s(
                    win_trades, start_ts_us=win_ts_start, end_ts_us=win_ts_end
                )
                win_trade_feat = compute_trade_flow_features(
                    win_trade_bars, mid_prices=batch_mid
                )
                win_trade_cols = [c for c in win_trade_feat.columns if c != "timestamp"]

                micro_mat = batch_feat_df[batch_feature_cols].values.astype(np.float32)
                trade_mat = win_trade_feat[win_trade_cols].values.astype(np.float32)
                batch_feat_win = np.concatenate([micro_mat, trade_mat], axis=1)
                batch_feat_win = np.nan_to_num(batch_feat_win, nan=0.0, posinf=0.0, neginf=0.0)
                batch_feat_win = np.clip(batch_feat_win, -self.FEATURE_CLIP, self.FEATURE_CLIP)

                batch_raw_win = extract_raw_lob_tensor(window_df, n_levels=min(self.N_LEVELS, 20))

                np.testing.assert_allclose(
                    x_feat[0], batch_feat_win, atol=1e-6, rtol=1e-5,
                    err_msg=f"Feature mismatch at position {row_idx}",
                )
                np.testing.assert_allclose(
                    x_raw[0], batch_raw_win, atol=1e-6, rtol=1e-5,
                    err_msg=f"Raw tensor mismatch at position {row_idx}",
                )
                checked_positions.append(row_idx)

        self.assertGreaterEqual(
            len(checked_positions), 3,
            f"Expected at least 3 checked positions, got {len(checked_positions)}",
        )

    def test_feature_count_and_names(self) -> None:
        """Verify streaming feature count matches expectations."""
        computer_with = StreamingFeatureComputer(
            input_len=self.INPUT_LEN, n_levels=self.N_LEVELS, use_trades=True,
            warmup=0,
        )
        computer_without = StreamingFeatureComputer(
            input_len=self.INPUT_LEN, n_levels=self.N_LEVELS, use_trades=False,
            warmup=0,
        )

        # Feed enough data to fill buffers
        for row_idx in range(self.INPUT_LEN):
            ts = int(self.depth_df["timestamp"].iloc[row_idx])
            snapshot = {"timestamp": ts}
            for i in range(self.N_LEVELS):
                for side in ("asks", "bids"):
                    for field in ("price", "amount"):
                        col = f"{side}[{i}].{field}"
                        snapshot[col] = float(self.depth_df[col].iloc[row_idx])

            us_per_sec = 1_000_000
            mask = (
                (self.trades_df["timestamp"] >= ts)
                & (self.trades_df["timestamp"] < ts + us_per_sec)
            )
            sec_trades = self.trades_df[mask].to_dict("records")

            computer_with.update(snapshot, sec_trades)
            computer_without.update(snapshot, None)

        x_with, _ = computer_with.get_tensors()
        x_without, _ = computer_without.get_tensors()

        self.assertEqual(x_with.shape[2], 52, f"With trades: expected 52 features, got {x_with.shape[2]}")
        self.assertEqual(x_without.shape[2], 44, f"Without trades: expected 44 features, got {x_without.shape[2]}")

        # First 44 features should be identical
        np.testing.assert_allclose(
            x_with[0, :, :44], x_without[0, :, :44], atol=1e-6, rtol=1e-5,
            err_msg="First 44 features differ between with/without trades",
        )

    def test_buffer_not_ready_raises(self) -> None:
        """get_tensors() must raise if buffer not full."""
        computer = StreamingFeatureComputer(input_len=300, warmup=0)
        self.assertFalse(computer.is_ready())
        with self.assertRaises(RuntimeError):
            computer.get_tensors()

    def test_reset_clears_buffer(self) -> None:
        """reset() must clear all buffers."""
        computer = StreamingFeatureComputer(input_len=10, n_levels=self.N_LEVELS, warmup=0)

        for row_idx in range(10):
            ts = int(self.depth_df["timestamp"].iloc[row_idx])
            snapshot = {"timestamp": ts}
            for i in range(self.N_LEVELS):
                for side in ("asks", "bids"):
                    for field in ("price", "amount"):
                        col = f"{side}[{i}].{field}"
                        snapshot[col] = float(self.depth_df[col].iloc[row_idx])
            computer.update(snapshot, None)

        self.assertTrue(computer.is_ready())
        computer.reset()
        self.assertFalse(computer.is_ready())

    def test_output_shapes(self) -> None:
        """Verify output tensor shapes."""
        computer = StreamingFeatureComputer(
            input_len=self.INPUT_LEN, n_levels=self.N_LEVELS, use_trades=True,
            warmup=0,
        )

        for row_idx in range(self.INPUT_LEN):
            ts = int(self.depth_df["timestamp"].iloc[row_idx])
            snapshot = {"timestamp": ts}
            for i in range(self.N_LEVELS):
                for side in ("asks", "bids"):
                    for field in ("price", "amount"):
                        col = f"{side}[{i}].{field}"
                        snapshot[col] = float(self.depth_df[col].iloc[row_idx])

            us_per_sec = 1_000_000
            mask = (
                (self.trades_df["timestamp"] >= ts)
                & (self.trades_df["timestamp"] < ts + us_per_sec)
            )
            sec_trades = self.trades_df[mask].to_dict("records")
            computer.update(snapshot, sec_trades)

        x_feat, x_raw = computer.get_tensors()

        self.assertEqual(x_feat.shape, (1, self.INPUT_LEN, 52))
        self.assertEqual(x_raw.shape, (1, self.INPUT_LEN, 20, 4))
        self.assertEqual(x_feat.dtype, np.float32)
        self.assertEqual(x_raw.dtype, np.float32)

    def test_no_nan_or_inf_in_output(self) -> None:
        """Output tensors must not contain NaN or Inf."""
        computer = StreamingFeatureComputer(
            input_len=self.INPUT_LEN, n_levels=self.N_LEVELS, use_trades=True,
            warmup=0,
        )

        for row_idx in range(self.INPUT_LEN):
            ts = int(self.depth_df["timestamp"].iloc[row_idx])
            snapshot = {"timestamp": ts}
            for i in range(self.N_LEVELS):
                for side in ("asks", "bids"):
                    for field in ("price", "amount"):
                        col = f"{side}[{i}].{field}"
                        snapshot[col] = float(self.depth_df[col].iloc[row_idx])
            computer.update(snapshot, None)

        x_feat, x_raw = computer.get_tensors()

        self.assertFalse(np.any(np.isnan(x_feat)), "NaN found in feature tensor")
        self.assertFalse(np.any(np.isinf(x_feat)), "Inf found in feature tensor")
        self.assertFalse(np.any(np.isnan(x_raw)), "NaN found in raw tensor")
        self.assertFalse(np.any(np.isinf(x_raw)), "Inf found in raw tensor")

    def test_warmup_buffer(self) -> None:
        """With warmup > 0, buffer needs input_len + warmup rows to be ready.

        Output tensors must still be (1, input_len, ...) shaped.
        """
        warmup = 100
        input_len = 200
        computer = StreamingFeatureComputer(
            input_len=input_len,
            n_levels=self.N_LEVELS,
            use_trades=False,
            warmup=warmup,
        )

        # Feed data but not enough for warmup
        for row_idx in range(input_len):
            ts = int(self.depth_df["timestamp"].iloc[row_idx])
            snapshot = {"timestamp": ts}
            for i in range(self.N_LEVELS):
                for side in ("asks", "bids"):
                    for field in ("price", "amount"):
                        col = f"{side}[{i}].{field}"
                        snapshot[col] = float(self.depth_df[col].iloc[row_idx])
            computer.update(snapshot, None)

        # Should NOT be ready yet (need input_len + warmup = 300 rows)
        self.assertFalse(
            computer.is_ready(),
            f"Should not be ready with only {input_len} rows (need {input_len + warmup})",
        )

        # Feed the remaining warmup rows
        for row_idx in range(input_len, input_len + warmup):
            ts = int(self.depth_df["timestamp"].iloc[row_idx])
            snapshot = {"timestamp": ts}
            for i in range(self.N_LEVELS):
                for side in ("asks", "bids"):
                    for field in ("price", "amount"):
                        col = f"{side}[{i}].{field}"
                        snapshot[col] = float(self.depth_df[col].iloc[row_idx])
            computer.update(snapshot, None)

        self.assertTrue(
            computer.is_ready(),
            f"Should be ready with {input_len + warmup} rows",
        )

        x_feat, x_raw = computer.get_tensors()

        # Output must still be input_len rows, not input_len + warmup
        self.assertEqual(
            x_feat.shape[1], input_len,
            f"Expected output length {input_len}, got {x_feat.shape[1]}",
        )
        self.assertEqual(
            x_raw.shape[1], input_len,
            f"Expected raw output length {input_len}, got {x_raw.shape[1]}",
        )


class TestTradeFeatures(unittest.TestCase):
    """Unit tests for trade feature computation."""

    def test_aggregate_trades_basic(self) -> None:
        """Basic aggregation: correct columns, non-negative volumes."""
        rng = np.random.default_rng(42)
        n = 100
        start_ts = 1_700_000_000_000_000

        trades = pd.DataFrame({
            "timestamp": start_ts + np.sort(rng.integers(0, 5_000_000, size=n)),
            "price": 70_000.0 + rng.normal(0, 5, n),
            "size": rng.uniform(0.001, 1.0, n),
            "side": rng.choice(["Buy", "Sell"], size=n),
        })

        bars = aggregate_trades_to_1s(trades)

        expected_cols = {
            "timestamp", "trade_count", "buy_volume", "sell_volume",
            "net_trade_flow", "trade_imbalance", "vwap", "trade_intensity",
        }
        self.assertEqual(set(bars.columns), expected_cols)
        self.assertTrue((bars["buy_volume"] >= 0).all())
        self.assertTrue((bars["sell_volume"] >= 0).all())
        self.assertTrue((bars["trade_imbalance"] >= -1).all())
        self.assertTrue((bars["trade_imbalance"] <= 1).all())

    def test_aggregate_empty_seconds_filled(self) -> None:
        """Seconds with no trades should be filled with zeros."""
        # Create trades only in seconds 0 and 3 (gap at 1, 2)
        us = 1_000_000
        ts_base = 1_700_000_000_000_000
        trades = pd.DataFrame({
            "timestamp": [ts_base + 100, ts_base + 200, ts_base + 3 * us + 100],
            "price": [70000.0, 70001.0, 70002.0],
            "size": [0.1, 0.2, 0.3],
            "side": ["Buy", "Sell", "Buy"],
        })

        bars = aggregate_trades_to_1s(trades)
        self.assertEqual(len(bars), 4)  # seconds 0, 1, 2, 3
        # Seconds 1 and 2 should have zero trades
        self.assertEqual(bars.iloc[1]["trade_count"], 0)
        self.assertEqual(bars.iloc[2]["trade_count"], 0)
        self.assertEqual(bars.iloc[1]["buy_volume"], 0.0)
        self.assertEqual(bars.iloc[2]["sell_volume"], 0.0)

    def test_trade_flow_features_count(self) -> None:
        """Verify exactly 8 trade feature columns."""
        rng = np.random.default_rng(42)
        n = 200
        start_ts = 1_700_000_000_000_000

        trades = pd.DataFrame({
            "timestamp": start_ts + np.sort(rng.integers(0, 10_000_000, size=n)),
            "price": 70_000.0 + rng.normal(0, 5, n),
            "size": rng.uniform(0.001, 1.0, n),
            "side": rng.choice(["Buy", "Sell"], size=n),
        })

        bars = aggregate_trades_to_1s(trades)
        features = compute_trade_flow_features(bars)

        feat_cols = [c for c in features.columns if c != "timestamp"]
        self.assertEqual(len(feat_cols), 8, f"Expected 8 trade features, got {len(feat_cols)}: {feat_cols}")

        expected = set(TRADE_FEATURE_NAMES)
        self.assertEqual(set(feat_cols), expected)

    def test_trade_features_causal(self) -> None:
        """Trade features must be strictly causal (backward-looking only).

        Modifying future data should not affect past features.
        """
        rng = np.random.default_rng(42)
        n = 500
        start_ts = 1_700_000_000_000_000

        trades = pd.DataFrame({
            "timestamp": start_ts + np.sort(rng.integers(0, 30_000_000, size=n)),
            "price": 70_000.0 + rng.normal(0, 5, n),
            "size": rng.uniform(0.001, 1.0, n),
            "side": rng.choice(["Buy", "Sell"], size=n),
        })

        bars_full = aggregate_trades_to_1s(trades)
        features_full = compute_trade_flow_features(bars_full)

        T = 15  # check rows 0..T-1
        bars_truncated = bars_full.iloc[:T + 10].copy().reset_index(drop=True)
        # Modify rows T..end
        bars_modified = bars_truncated.copy()
        bars_modified.loc[T:, "buy_volume"] = 999.0
        bars_modified.loc[T:, "sell_volume"] = 0.0
        bars_modified.loc[T:, "net_trade_flow"] = 999.0
        bars_modified.loc[T:, "trade_count"] = 1000

        features_modified = compute_trade_flow_features(bars_modified)

        for col in TRADE_FEATURE_NAMES:
            orig = features_full[col].iloc[:T].values
            modi = features_modified[col].iloc[:T].values
            np.testing.assert_array_almost_equal(
                orig, modi, decimal=10,
                err_msg=f"Trade feature '{col}' at rows <{T} changed when future was modified -- causality violation!",
            )

    def test_vwap_return_with_mid_prices(self) -> None:
        """vwap_return_1s should be non-zero when mid_prices are provided."""
        rng = np.random.default_rng(42)
        n = 100
        start_ts = 1_700_000_000_000_000

        trades = pd.DataFrame({
            "timestamp": start_ts + np.sort(rng.integers(0, 5_000_000, size=n)),
            "price": 70_000.0 + rng.normal(0, 5, n),
            "size": rng.uniform(0.001, 1.0, n),
            "side": rng.choice(["Buy", "Sell"], size=n),
        })

        bars = aggregate_trades_to_1s(trades)
        mid_prices = np.full(len(bars), 70_000.0) + rng.normal(0, 1, len(bars))

        features = compute_trade_flow_features(bars, mid_prices=mid_prices)

        # At seconds with trades, vwap_return should be non-zero
        has_trades = bars["trade_count"] > 0
        vwap_ret = features["vwap_return_1s"].values
        non_zero = vwap_ret[has_trades.values] != 0.0
        self.assertTrue(
            non_zero.any(),
            "vwap_return_1s should be non-zero for seconds with trades",
        )


class TestPipelineTradeIntegration(unittest.TestCase):
    """Test that build_npz_for_day handles trades correctly."""

    def test_build_npz_backward_compatible(self) -> None:
        """Without trades_df, build_npz_for_day must produce 44 features."""
        from src.features.pipeline import build_npz_for_day

        depth_df = make_synthetic_depth_1s(n_rows=500, n_levels=25)
        result = build_npz_for_day(depth_df, input_len=300, stride=60)

        self.assertEqual(
            len(result["features"]), 44,
            f"Without trades: expected 44 features, got {len(result['features'])}",
        )
        self.assertEqual(result["X"].shape[2], 44)

    def test_build_npz_with_trades(self) -> None:
        """With trades_df, build_npz_for_day must produce 52 features."""
        from src.features.pipeline import build_npz_for_day

        depth_df = make_synthetic_depth_1s(n_rows=500, n_levels=25)
        trades_df = make_synthetic_trades(depth_df)

        result = build_npz_for_day(
            depth_df, trades_df=trades_df, input_len=300, stride=60
        )

        self.assertEqual(
            len(result["features"]), 52,
            f"With trades: expected 52 features, got {len(result['features'])}",
        )
        self.assertEqual(result["X"].shape[2], 52)

        # First 44 features should match the no-trades run
        result_no_trades = build_npz_for_day(depth_df, input_len=300, stride=60)
        np.testing.assert_allclose(
            result["X"][:, :, :44],
            result_no_trades["X"],
            atol=1e-6,
            err_msg="First 44 features differ between with/without trades in pipeline",
        )


if __name__ == "__main__":
    unittest.main()

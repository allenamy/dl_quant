"""Tests for Bybit JSONL → CSV adapter (scripts/bybit_to_csv).

Verifies:
    1. JSONL parsing with synthetic data
    2. Output CSV has correct columns and types
    3. Handling of <25 levels (zero-padding)
    4. Timestamp conversion (ms → microseconds)
    5. Compatibility with ``resample_lob_to_1s()``
    6. Malformed / empty line handling
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.bybit_to_csv import (
    N_LEVELS,
    build_csv_columns,
    convert_bybit_to_csv,
    iter_parse_jsonl,
    parse_bybit_line,
)
from src.features.resample import resample_lob_to_1s


# ---------------------------------------------------------------------------
# Helpers — synthetic Bybit JSONL data
# ---------------------------------------------------------------------------

def _make_bybit_json_line(
    ts_ms: int = 1_700_000_000_123,
    symbol: str = "BTCUSDT",
    n_ask_levels: int = 500,
    n_bid_levels: int = 500,
    base_ask: float = 30_001.0,
    base_bid: float = 30_000.0,
    ask_step: float = 0.1,
    bid_step: float = 0.1,
    base_amount: float = 1.5,
) -> str:
    """Create a single synthetic Bybit JSONL line."""
    asks = [
        [str(base_ask + i * ask_step), str(round(base_amount + i * 0.01, 4))]
        for i in range(n_ask_levels)
    ]
    bids = [
        [str(base_bid - i * bid_step), str(round(base_amount + i * 0.01, 4))]
        for i in range(n_bid_levels)
    ]
    obj = {"ts": ts_ms, "s": symbol, "a": asks, "b": bids}
    return json.dumps(obj)


def _make_jsonl_stream(
    n_ticks: int = 100,
    start_ts_ms: int = 1_700_000_000_000,
    tick_interval_ms: int = 100,
    n_ask_levels: int = 500,
    n_bid_levels: int = 500,
) -> list[str]:
    """Create a list of JSONL lines simulating a short data file."""
    lines = []
    for i in range(n_ticks):
        ts = start_ts_ms + i * tick_interval_ms
        line = _make_bybit_json_line(
            ts_ms=ts,
            n_ask_levels=n_ask_levels,
            n_bid_levels=n_bid_levels,
            base_ask=30_001.0 + np.sin(i * 0.1) * 0.5,
            base_bid=30_000.0 + np.sin(i * 0.1) * 0.5,
        )
        lines.append(line + "\n")
    return lines


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseBybitLine(unittest.TestCase):
    """Test single-line JSONL parsing."""

    def test_basic_parse(self) -> None:
        """A well-formed line should produce a dict with all expected keys."""
        line = _make_bybit_json_line(ts_ms=1_700_000_000_123)
        result = parse_bybit_line(line)
        self.assertIsNotNone(result)
        assert result is not None  # for type checker

        expected_cols = build_csv_columns()
        for col in expected_cols:
            self.assertIn(col, result, f"Missing key: {col}")

    def test_timestamp_conversion(self) -> None:
        """Timestamp must be converted from ms to microseconds."""
        ts_ms = 1_700_000_000_123
        line = _make_bybit_json_line(ts_ms=ts_ms)
        result = parse_bybit_line(line)
        assert result is not None

        expected_us = ts_ms * 1_000
        self.assertEqual(result["timestamp"], expected_us)

    def test_ask_bid_values(self) -> None:
        """Ask/bid prices and amounts must match the input data."""
        line = _make_bybit_json_line(
            base_ask=50_000.0,
            base_bid=49_999.0,
            ask_step=1.0,
            bid_step=1.0,
            base_amount=2.0,
        )
        result = parse_bybit_line(line)
        assert result is not None

        # Level 0
        self.assertAlmostEqual(result["asks[0].price"], 50_000.0)
        self.assertAlmostEqual(result["asks[0].amount"], 2.0)
        self.assertAlmostEqual(result["bids[0].price"], 49_999.0)
        self.assertAlmostEqual(result["bids[0].amount"], 2.0)

        # Level 5
        self.assertAlmostEqual(result["asks[5].price"], 50_005.0)
        self.assertAlmostEqual(result["bids[5].price"], 49_994.0)

    def test_empty_line(self) -> None:
        """Empty and whitespace-only lines should return None."""
        self.assertIsNone(parse_bybit_line(""))
        self.assertIsNone(parse_bybit_line("   "))
        self.assertIsNone(parse_bybit_line("\n"))

    def test_malformed_json(self) -> None:
        """Invalid JSON should return None (not raise)."""
        self.assertIsNone(parse_bybit_line("{not valid json"))
        self.assertIsNone(parse_bybit_line("hello world"))

    def test_missing_ts_field(self) -> None:
        """A line without 'ts' should return None."""
        line = json.dumps({"s": "BTCUSDT", "a": [], "b": []})
        self.assertIsNone(parse_bybit_line(line))


class TestPaddingLevels(unittest.TestCase):
    """Test handling of fewer than 25 levels."""

    def test_fewer_than_25_asks(self) -> None:
        """If only 10 ask levels provided, levels 10-24 should be padded with 0."""
        line = _make_bybit_json_line(n_ask_levels=10, n_bid_levels=500)
        result = parse_bybit_line(line)
        assert result is not None

        # Levels 0-9 should have real values
        for i in range(10):
            self.assertGreater(result[f"asks[{i}].price"], 0.0)
            self.assertGreater(result[f"asks[{i}].amount"], 0.0)

        # Levels 10-24 should be padded with 0
        for i in range(10, N_LEVELS):
            self.assertEqual(result[f"asks[{i}].price"], 0.0)
            self.assertEqual(result[f"asks[{i}].amount"], 0.0)

    def test_fewer_than_25_bids(self) -> None:
        """If only 3 bid levels provided, levels 3-24 should be padded with 0."""
        line = _make_bybit_json_line(n_ask_levels=500, n_bid_levels=3)
        result = parse_bybit_line(line)
        assert result is not None

        for i in range(3):
            self.assertGreater(result[f"bids[{i}].price"], 0.0)

        for i in range(3, N_LEVELS):
            self.assertEqual(result[f"bids[{i}].price"], 0.0)
            self.assertEqual(result[f"bids[{i}].amount"], 0.0)

    def test_zero_levels(self) -> None:
        """Empty asks/bids arrays should produce all-zero levels."""
        line = _make_bybit_json_line(n_ask_levels=0, n_bid_levels=0)
        result = parse_bybit_line(line)
        assert result is not None

        for i in range(N_LEVELS):
            self.assertEqual(result[f"asks[{i}].price"], 0.0)
            self.assertEqual(result[f"bids[{i}].price"], 0.0)

    def test_exactly_25_levels(self) -> None:
        """Exactly 25 levels should work without padding."""
        line = _make_bybit_json_line(n_ask_levels=25, n_bid_levels=25)
        result = parse_bybit_line(line)
        assert result is not None

        for i in range(N_LEVELS):
            self.assertGreater(result[f"asks[{i}].price"], 0.0)
            self.assertGreater(result[f"bids[{i}].price"], 0.0)


class TestIterParseJsonl(unittest.TestCase):
    """Test batch JSONL iteration."""

    def test_skips_bad_lines(self) -> None:
        """Malformed lines should be silently skipped."""
        lines = [
            _make_bybit_json_line(ts_ms=1_700_000_000_100) + "\n",
            "{bad json}\n",
            "",
            _make_bybit_json_line(ts_ms=1_700_000_000_200) + "\n",
        ]
        rows = list(iter_parse_jsonl(iter(lines)))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["timestamp"], 1_700_000_000_100 * 1_000)
        self.assertEqual(rows[1]["timestamp"], 1_700_000_000_200 * 1_000)


class TestCsvColumns(unittest.TestCase):
    """Test that build_csv_columns produces the correct schema."""

    def test_column_count(self) -> None:
        """Should have 1 (timestamp) + 25 * 4 (price/amount x ask/bid) = 101 columns."""
        cols = build_csv_columns()
        self.assertEqual(len(cols), 1 + N_LEVELS * 4)

    def test_column_names(self) -> None:
        """Column names must match the pipeline's expected format."""
        cols = build_csv_columns()
        self.assertEqual(cols[0], "timestamp")
        self.assertEqual(cols[1], "asks[0].price")
        self.assertEqual(cols[2], "asks[0].amount")
        self.assertEqual(cols[3], "bids[0].price")
        self.assertEqual(cols[4], "bids[0].amount")
        self.assertEqual(cols[-2], "bids[24].price")
        self.assertEqual(cols[-1], "bids[24].amount")


class TestConvertBybitToCsv(unittest.TestCase):
    """Test end-to-end JSONL -> CSV conversion."""

    def test_csv_output_plain(self) -> None:
        """Write a plain CSV and verify content."""
        lines = _make_jsonl_stream(n_ticks=50)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test.csv"
            n = convert_bybit_to_csv(iter(lines), out_path)
            self.assertEqual(n, 50)

            # Read back and verify
            df = pd.read_csv(out_path)
            expected_cols = build_csv_columns()
            self.assertEqual(list(df.columns), expected_cols)
            self.assertEqual(len(df), 50)

            # Timestamp should be int64 microseconds
            self.assertTrue(df["timestamp"].dtype in [np.int64, np.float64])
            self.assertTrue((df["timestamp"] > 1e15).all(), "Timestamps should be in microseconds")

    def test_csv_output_gzip(self) -> None:
        """Write a .csv.gz file and verify it is valid gzip."""
        lines = _make_jsonl_stream(n_ticks=30)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test.csv.gz"
            n = convert_bybit_to_csv(iter(lines), out_path)
            self.assertEqual(n, 30)

            # Verify it's a valid gzip with correct content
            df = pd.read_csv(out_path, compression="gzip")
            self.assertEqual(len(df), 30)
            expected_cols = build_csv_columns()
            self.assertEqual(list(df.columns), expected_cols)

    def test_csv_types(self) -> None:
        """Verify that all numeric columns are float and timestamp is int-compatible."""
        lines = _make_jsonl_stream(n_ticks=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test.csv"
            convert_bybit_to_csv(iter(lines), out_path)

            df = pd.read_csv(out_path)

            # Timestamp: integer-valued (may load as int64 or float64)
            ts_vals = df["timestamp"].values
            np.testing.assert_array_equal(
                ts_vals, ts_vals.astype(np.int64),
                err_msg="Timestamps must be exact integers (microseconds)",
            )

            # All price/amount columns should be numeric
            for col in df.columns:
                if col == "timestamp":
                    continue
                self.assertTrue(
                    np.issubdtype(df[col].dtype, np.number),
                    f"Column {col} should be numeric, got {df[col].dtype}",
                )


class TestPipelineCompatibility(unittest.TestCase):
    """Test that converted CSV output is accepted by resample_lob_to_1s()."""

    def test_resample_accepts_converted_data(self) -> None:
        """Generate synthetic JSONL, convert to CSV, feed to resample_lob_to_1s.

        The resampler should run without errors and produce valid output.
        """
        # Generate 10 seconds of ticks at ~100ms intervals (100 ticks)
        lines = _make_jsonl_stream(
            n_ticks=200,
            start_ts_ms=1_700_000_000_000,
            tick_interval_ms=100,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test.csv"
            convert_bybit_to_csv(iter(lines), out_path)

            # Load and pass to resampler
            df = pd.read_csv(out_path)

            # Force timestamp to int64 (CSV may load as float)
            df["timestamp"] = df["timestamp"].astype(np.int64)

            result = resample_lob_to_1s(df, n_levels=N_LEVELS)

            # Should produce some rows (20 seconds of data at 100ms = ~20 1s bars)
            self.assertGreater(len(result), 0)

            # Timestamps should be uniformly spaced at 1s
            diffs = result["timestamp"].diff().dropna().unique()
            self.assertEqual(len(diffs), 1)
            self.assertEqual(diffs[0], 1_000_000)

            # All LOB columns should be present and non-NaN
            for i in range(N_LEVELS):
                for side in ("asks", "bids"):
                    for field in ("price", "amount"):
                        col = f"{side}[{i}].{field}"
                        self.assertIn(col, result.columns)
                        self.assertFalse(result[col].isna().any())

    def test_resample_with_padded_levels(self) -> None:
        """Resampler should handle data where some levels are zero-padded."""
        # Only 10 levels of real data (levels 10-24 will be 0.0)
        lines = _make_jsonl_stream(
            n_ticks=200,
            tick_interval_ms=100,
            n_ask_levels=10,
            n_bid_levels=10,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test_padded.csv"
            convert_bybit_to_csv(iter(lines), out_path)

            df = pd.read_csv(out_path)
            df["timestamp"] = df["timestamp"].astype(np.int64)

            # Should not raise
            result = resample_lob_to_1s(df, n_levels=N_LEVELS)
            self.assertGreater(len(result), 0)


class TestZipInput(unittest.TestCase):
    """Test reading from ZIP archives."""

    def test_convert_from_zip(self) -> None:
        """Create a synthetic ZIP, convert it, verify output."""
        from scripts.bybit_to_csv import _read_lines_from_zip

        lines = _make_jsonl_stream(n_ticks=20)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a synthetic ZIP
            zip_path = Path(tmpdir) / "test.data.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                content = "".join(lines)
                zf.writestr("2025-06-01_BTCUSDT_ob500.data", content)

            # Read lines from ZIP
            zip_lines = list(_read_lines_from_zip(zip_path))
            self.assertEqual(len(zip_lines), 20)

            # Convert via the full pipeline
            out_csv = Path(tmpdir) / "output.csv"
            n = convert_bybit_to_csv(
                _read_lines_from_zip(zip_path), out_csv
            )
            self.assertEqual(n, 20)


class TestDownloadUrl(unittest.TestCase):
    """Test URL construction (scripts/download_bybit.py)."""

    def test_url_format(self) -> None:
        """Verify download URL is correctly constructed."""
        from datetime import date

        from scripts.download_bybit import _build_url

        url = _build_url(date(2025, 6, 15), "BTCUSDT", "ob500")
        self.assertEqual(
            url,
            "https://quote-saver.bycsi.com/2025-06-15_BTCUSDT_ob500.data.zip",
        )

    def test_url_ob1000(self) -> None:
        from datetime import date

        from scripts.download_bybit import _build_url

        url = _build_url(date(2025, 10, 1), "ETHUSDT", "ob1000")
        self.assertEqual(
            url,
            "https://quote-saver.bycsi.com/2025-10-01_ETHUSDT_ob1000.data.zip",
        )


if __name__ == "__main__":
    unittest.main()

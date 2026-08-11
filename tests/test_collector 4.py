"""Tests for the Binance depth collector and JSONL-to-CSV converter.

Tests cover the non-network components:
- JSONL line parsing
- CSV column generation
- Gap detection logic
- Daily file rotation naming
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
from pathlib import Path

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.collected_to_csv import (
    build_csv_columns,
    convert_jsonl_to_csv,
    derive_output_path,
    parse_depth_line,
)
from scripts.collect_binance_depth import DailyGzWriter, GapTracker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _make_depth_message(
    n_levels: int = 20,
    event_time_ms: int = 1_700_000_000_123,
    first_update_id: int = 1000,
    final_update_id: int = 1005,
    prev_final_update_id: int = 999,
    base_ask: float = 30_000.0,
    base_bid: float = 29_999.0,
) -> dict:
    """Create a synthetic Binance depth update message."""
    asks = [
        [str(base_ask + i * 0.1), str(round(0.5 + i * 0.1, 4))]
        for i in range(n_levels)
    ]
    bids = [
        [str(base_bid - i * 0.1), str(round(0.5 + i * 0.1, 4))]
        for i in range(n_levels)
    ]
    return {
        "e": "depthUpdate",
        "E": event_time_ms,
        "T": event_time_ms - 1,
        "s": "BTCUSDT",
        "U": first_update_id,
        "u": final_update_id,
        "pu": prev_final_update_id,
        "b": bids,
        "a": asks,
    }


# ---------------------------------------------------------------------------
# Tests: CSV column generation
# ---------------------------------------------------------------------------
class TestBuildCsvColumns(unittest.TestCase):

    def test_column_count(self):
        """20 levels -> 1 timestamp + 40 ask cols + 40 bid cols = 81."""
        cols = build_csv_columns(20)
        self.assertEqual(len(cols), 1 + 20 * 2 + 20 * 2)
        self.assertEqual(len(cols), 81)

    def test_column_count_5_levels(self):
        cols = build_csv_columns(5)
        self.assertEqual(len(cols), 1 + 5 * 2 + 5 * 2)

    def test_column_order(self):
        """Asks come before bids; within each side, price before amount."""
        cols = build_csv_columns(3)
        self.assertEqual(cols[0], "timestamp")
        self.assertEqual(cols[1], "asks[0].price")
        self.assertEqual(cols[2], "asks[0].amount")
        self.assertEqual(cols[3], "asks[1].price")
        self.assertEqual(cols[4], "asks[1].amount")
        self.assertEqual(cols[5], "asks[2].price")
        self.assertEqual(cols[6], "asks[2].amount")
        self.assertEqual(cols[7], "bids[0].price")
        self.assertEqual(cols[8], "bids[0].amount")

    def test_first_and_last_columns(self):
        cols = build_csv_columns(20)
        self.assertEqual(cols[0], "timestamp")
        self.assertEqual(cols[-1], "bids[19].amount")


# ---------------------------------------------------------------------------
# Tests: JSONL line parsing
# ---------------------------------------------------------------------------
class TestParseDepthLine(unittest.TestCase):

    def test_basic_parse(self):
        msg = _make_depth_message(n_levels=20, event_time_ms=1_700_000_000_123)
        line = json.dumps(msg)
        row = parse_depth_line(line, n_levels=20)

        self.assertIsNotNone(row)
        # Timestamp: ms -> us
        self.assertEqual(row["timestamp"], 1_700_000_000_123 * 1000)

    def test_ask_bid_values(self):
        msg = _make_depth_message(
            n_levels=3,
            base_ask=30_000.0,
            base_bid=29_999.0,
        )
        line = json.dumps(msg)
        row = parse_depth_line(line, n_levels=3)

        self.assertIsNotNone(row)
        self.assertAlmostEqual(row["asks[0].price"], 30_000.0, places=2)
        self.assertAlmostEqual(row["asks[1].price"], 30_000.1, places=2)
        self.assertAlmostEqual(row["bids[0].price"], 29_999.0, places=2)
        self.assertAlmostEqual(row["bids[1].price"], 29_998.9, places=2)
        self.assertAlmostEqual(row["asks[0].amount"], 0.5, places=4)

    def test_insufficient_levels_returns_none(self):
        """If data has fewer levels than requested, return None."""
        msg = _make_depth_message(n_levels=5)
        line = json.dumps(msg)
        row = parse_depth_line(line, n_levels=20)
        self.assertIsNone(row)

    def test_missing_event_time_returns_none(self):
        msg = _make_depth_message()
        del msg["E"]
        line = json.dumps(msg)
        row = parse_depth_line(line, n_levels=20)
        self.assertIsNone(row)

    def test_invalid_json_returns_none(self):
        row = parse_depth_line("not valid json{{{", n_levels=20)
        self.assertIsNone(row)

    def test_empty_line_returns_none(self):
        row = parse_depth_line("", n_levels=20)
        self.assertIsNone(row)

    def test_all_20_levels_present(self):
        msg = _make_depth_message(n_levels=20)
        line = json.dumps(msg)
        row = parse_depth_line(line, n_levels=20)

        self.assertIsNotNone(row)
        expected_cols = build_csv_columns(20)
        for col in expected_cols:
            self.assertIn(col, row, "Missing column: {}".format(col))


# ---------------------------------------------------------------------------
# Tests: Gap detection
# ---------------------------------------------------------------------------
class TestGapTracker(unittest.TestCase):

    def test_no_gap_on_first_message(self):
        tracker = GapTracker()
        msg = _make_depth_message(final_update_id=100, prev_final_update_id=99)
        gap = tracker.check(msg)
        self.assertFalse(gap)
        self.assertEqual(tracker.total_messages, 1)

    def test_no_gap_continuous_sequence(self):
        tracker = GapTracker()
        # Message 1: u=100
        msg1 = _make_depth_message(final_update_id=100, prev_final_update_id=99)
        tracker.check(msg1)
        # Message 2: pu=100 (matches prev u)
        msg2 = _make_depth_message(final_update_id=105, prev_final_update_id=100)
        gap = tracker.check(msg2)
        self.assertFalse(gap)
        self.assertEqual(tracker.total_gaps, 0)

    def test_gap_detected(self):
        tracker = GapTracker()
        msg1 = _make_depth_message(final_update_id=100, prev_final_update_id=99)
        tracker.check(msg1)
        # Message 2: pu=200 != prev u=100 -> gap
        msg2 = _make_depth_message(final_update_id=210, prev_final_update_id=200)
        gap = tracker.check(msg2)
        self.assertTrue(gap)
        self.assertEqual(tracker.total_gaps, 1)

    def test_multiple_gaps_counted(self):
        tracker = GapTracker()
        ids = [(100, 99), (210, 200), (320, 300)]
        for u, pu in ids:
            tracker.check(_make_depth_message(final_update_id=u, prev_final_update_id=pu))
        # First message: no gap check (prev_u is None)
        # Second: pu=200 != prev_u=100 -> gap
        # Third: pu=300 != prev_u=210 -> gap
        self.assertEqual(tracker.total_gaps, 2)
        self.assertEqual(tracker.total_messages, 3)

    def test_reset_clears_state(self):
        tracker = GapTracker()
        msg1 = _make_depth_message(final_update_id=100, prev_final_update_id=99)
        tracker.check(msg1)
        tracker.reset()
        # After reset, first message should not trigger gap
        msg2 = _make_depth_message(final_update_id=500, prev_final_update_id=499)
        gap = tracker.check(msg2)
        self.assertFalse(gap)


# ---------------------------------------------------------------------------
# Tests: Daily file rotation naming
# ---------------------------------------------------------------------------
class TestDeriveOutputPath(unittest.TestCase):

    def test_standard_name(self):
        inp = Path("data/collected/2026-04-13_BTCUSDT_depth20.jsonl.gz")
        out = derive_output_path(inp, Path("data/csv"))
        self.assertEqual(out, Path("data/csv/2026-04-13_BTCUSDT_depth20.csv.gz"))

    def test_different_symbol(self):
        inp = Path("/tmp/2026-01-01_ETHUSDT_depth10.jsonl.gz")
        out = derive_output_path(inp, Path("/tmp/csv"))
        self.assertEqual(out, Path("/tmp/csv/2026-01-01_ETHUSDT_depth10.csv.gz"))


class TestDailyGzWriter(unittest.TestCase):

    def test_file_naming(self):
        """Writer creates files with the expected daily naming pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = DailyGzWriter(tmpdir, "BTCUSDT", 20)
            writer.write_line(b'{"test":1}\n')
            writer.close()

            files = list(Path(tmpdir).glob("*.jsonl.gz"))
            self.assertEqual(len(files), 1)

            name = files[0].name
            # Should match YYYY-MM-DD_BTCUSDT_depth20.jsonl.gz
            self.assertRegex(
                name,
                r"\d{4}-\d{2}-\d{2}_BTCUSDT_depth20\.jsonl\.gz",
            )

    def test_written_content(self):
        """Written data can be read back correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = DailyGzWriter(tmpdir, "BTCUSDT", 20)
            line1 = b'{"msg":1}\n'
            line2 = b'{"msg":2}\n'
            writer.write_line(line1)
            writer.write_line(line2)
            writer.close()

            files = list(Path(tmpdir).glob("*.jsonl.gz"))
            with gzip.open(str(files[0]), "rt") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["msg"], 1)
            self.assertEqual(json.loads(lines[1])["msg"], 2)

    def test_bytes_written_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = DailyGzWriter(tmpdir, "BTCUSDT", 20)
            data = b'{"x":123}\n'
            writer.write_line(data)
            self.assertEqual(writer.bytes_written, len(data))
            writer.close()


# ---------------------------------------------------------------------------
# Tests: End-to-end JSONL -> CSV conversion
# ---------------------------------------------------------------------------
class TestConvertJsonlToCsv(unittest.TestCase):

    def test_roundtrip(self):
        """Write JSONL, convert, read CSV, verify columns and values."""
        n_levels = 20

        with tempfile.TemporaryDirectory() as tmpdir:
            jsonl_path = Path(tmpdir) / "test.jsonl.gz"
            csv_path = Path(tmpdir) / "test.csv.gz"

            # Write 3 messages
            msgs = []
            for i in range(3):
                msg = _make_depth_message(
                    n_levels=n_levels,
                    event_time_ms=1_700_000_000_000 + i * 100,
                    final_update_id=100 + i,
                    prev_final_update_id=99 + i,
                )
                msg["local_ts"] = 1_700_000_000_000_000 + i * 100_000
                msgs.append(msg)

            with gzip.open(str(jsonl_path), "wt") as f:
                for msg in msgs:
                    f.write(json.dumps(msg) + "\n")

            # Convert
            total, converted = convert_jsonl_to_csv(jsonl_path, csv_path, n_levels=n_levels)

            self.assertEqual(total, 3)
            self.assertEqual(converted, 3)

            # Read CSV and verify
            with gzip.open(str(csv_path), "rt") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            self.assertEqual(len(rows), 3)

            # Check column names
            expected_cols = build_csv_columns(n_levels)
            self.assertEqual(sorted(reader.fieldnames), sorted(expected_cols))

            # Check first row timestamp (ms -> us)
            self.assertEqual(
                int(rows[0]["timestamp"]),
                1_700_000_000_000 * 1000,
            )

            # Check ask/bid values are numeric and reasonable
            self.assertAlmostEqual(float(rows[0]["asks[0].price"]), 30_000.0, places=1)
            self.assertAlmostEqual(float(rows[0]["bids[0].price"]), 29_999.0, places=1)

    def test_skips_invalid_lines(self):
        """Invalid lines are skipped, valid lines are converted."""
        n_levels = 20

        with tempfile.TemporaryDirectory() as tmpdir:
            jsonl_path = Path(tmpdir) / "mixed.jsonl.gz"
            csv_path = Path(tmpdir) / "mixed.csv.gz"

            valid_msg = _make_depth_message(n_levels=n_levels)
            valid_msg["local_ts"] = 123

            with gzip.open(str(jsonl_path), "wt") as f:
                f.write("this is not json\n")
                f.write(json.dumps(valid_msg) + "\n")
                f.write(json.dumps({"E": 123}) + "\n")  # missing a/b
                f.write(json.dumps(valid_msg) + "\n")

            total, converted = convert_jsonl_to_csv(jsonl_path, csv_path, n_levels=n_levels)

            self.assertEqual(total, 4)
            self.assertEqual(converted, 2)


if __name__ == "__main__":
    unittest.main()

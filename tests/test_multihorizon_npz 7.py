"""Tests for multi-horizon label support in ``build_npz_for_day`` and the
multi-day pipeline.

We cover:

* Single-horizon default preserves the old (``y`` / ``y_mask``) shape, so
  legacy callers are unaffected.
* ``horizons_sec=[60, 180, 300, 600]`` produces ``y_{H}`` / ``y_mask_{H}``
  for every ``H`` with the documented log-return formula and correct
  masks (labels within [pred_idx+H < n_total] are valid).
* The back-compat ``y`` / ``y_mask`` aliases point to the smallest
  horizon.
* ``multi_day_pipeline.process_multi_day_crypto_folder`` forwards
  ``horizons_sec`` and enforces
  ``min_rows >= input_len + max(horizons_sec)`` (not just the default
  horizon), i.e. days too short for the *longest* horizon are skipped.
* The NPZ on disk carries every ``y_{H}`` / ``y_mask_{H}`` field and the
  ``horizons_sec`` metadata.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.features.pipeline import build_npz_for_day
from src.features.multi_day_pipeline import process_multi_day_crypto_folder


# ---------------------------------------------------------------------------
# Synthetic 1-second LOB bar builder
# ---------------------------------------------------------------------------

US_PER_SEC = 1_000_000


def _make_1s_bars(
    n_rows: int,
    n_levels: int = 25,
    start_ts_us: int = 1_700_000_000_000_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Build a deterministic 1-second LOB bar DataFrame.

    Mid-price follows a random walk so log-returns are non-degenerate, which
    lets us pin the expected ``y_H`` value by looking at the mid prices
    directly in the test.
    """
    rng = np.random.default_rng(seed)
    ts = start_ts_us + np.arange(n_rows, dtype=np.int64) * US_PER_SEC

    # Random-walk mids starting at 30_000.
    mid = 30_000.0 + np.cumsum(rng.normal(0.0, 0.5, n_rows))

    data: dict[str, np.ndarray] = {"timestamp": ts}
    for i in range(n_levels):
        # Asks above mid, bids below mid; positive spread for every row.
        data[f"asks[{i}].price"] = mid + 1.0 + i * 0.5
        data[f"asks[{i}].amount"] = rng.uniform(0.1, 5.0, n_rows)
        data[f"bids[{i}].price"] = mid - 1.0 - i * 0.5
        data[f"bids[{i}].amount"] = rng.uniform(0.1, 5.0, n_rows)
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# build_npz_for_day tests
# ---------------------------------------------------------------------------


class TestBuildNpzSingleHorizonBackCompat(unittest.TestCase):
    """Default (``horizons_sec=None``) behaves exactly like pre-patch."""

    def test_default_single_horizon_emits_y_and_y_mask(self) -> None:
        df = _make_1s_bars(n_rows=900, n_levels=25)
        result = build_npz_for_day(
            df,
            horizon_sec=180,
            input_len=300,
            stride=180,
            n_levels=25,
        )

        # Classic fields always present.
        for key in ("X", "X_raw", "y", "y_mask", "timestamps", "features"):
            self.assertIn(key, result, f"missing back-compat key {key!r}")

        # Per-horizon y / y_mask for the requested horizon must also be
        # present (back-compat == alias to the only horizon).
        self.assertIn("y_180", result)
        self.assertIn("y_mask_180", result)

        # Aliases are identical arrays (values), not just the same shape.
        np.testing.assert_array_equal(result["y"], result["y_180"])
        np.testing.assert_array_equal(result["y_mask"], result["y_mask_180"])

        # horizons_sec metadata recorded.
        self.assertEqual(list(result["horizons_sec"]), [180])


class TestBuildNpzMultiHorizon(unittest.TestCase):
    """``horizons_sec=[60, 180, 300, 600]`` produces 4 label pairs."""

    HORIZONS = [60, 180, 300, 600]

    def _build(self) -> dict:
        df = _make_1s_bars(n_rows=1500, n_levels=25)
        # stride = max(horizons) so the test doesn't trip the overlap warning.
        return build_npz_for_day(
            df,
            horizons_sec=self.HORIZONS,
            input_len=300,
            stride=600,
            n_levels=25,
        )

    def test_emits_all_horizon_labels(self) -> None:
        result = self._build()
        for h in self.HORIZONS:
            self.assertIn(f"y_{h}", result, f"missing y_{h}")
            self.assertIn(f"y_mask_{h}", result, f"missing y_mask_{h}")
            self.assertEqual(result[f"y_{h}"].shape, result["y_60"].shape)
            self.assertEqual(
                result[f"y_mask_{h}"].shape, result["y_mask_60"].shape
            )
        self.assertEqual(list(result["horizons_sec"]), self.HORIZONS)

    def test_back_compat_aliases_smallest_horizon(self) -> None:
        result = self._build()
        # Smallest horizon in [60, 180, 300, 600] is 60.
        np.testing.assert_array_equal(result["y"], result["y_60"])
        np.testing.assert_array_equal(result["y_mask"], result["y_mask_60"])

    def test_label_values_match_log_return_formula(self) -> None:
        """y_{H}[i] == log(mid[pred_idx+H] / mid[pred_idx]) for valid rows."""
        df = _make_1s_bars(n_rows=1500, n_levels=25)
        # Re-derive mids exactly as the pipeline does (top-level asks[0] +
        # bids[0] midpoint).
        mid = 0.5 * (df["asks[0].price"].values + df["bids[0].price"].values)

        input_len, stride = 300, 600
        result = build_npz_for_day(
            df,
            horizons_sec=self.HORIZONS,
            input_len=input_len,
            stride=stride,
            n_levels=25,
        )

        n_total = len(df)
        starts = list(range(0, n_total - input_len + 1, stride))

        for win_i, start in enumerate(starts):
            pred_idx = start + input_len - 1
            for h in self.HORIZONS:
                target_idx = pred_idx + h
                mask_val = int(result[f"y_mask_{h}"][win_i])
                y_val = float(result[f"y_{h}"][win_i])
                if target_idx < n_total and mid[pred_idx] > 0:
                    expected = float(np.log(mid[target_idx] / mid[pred_idx]))
                    self.assertEqual(mask_val, 1)
                    self.assertAlmostEqual(y_val, expected, places=6)
                else:
                    # Beyond the day boundary: mask must be 0 and y set to 0.
                    self.assertEqual(mask_val, 0)
                    self.assertEqual(y_val, 0.0)

    def test_masks_shrink_as_horizon_grows(self) -> None:
        """Longer horizons can have *fewer* valid labels near the day end,
        never more."""
        result = self._build()
        counts = {h: int(result[f"y_mask_{h}"].sum()) for h in self.HORIZONS}
        # Monotone non-increasing in H.
        ordered = [counts[h] for h in sorted(self.HORIZONS)]
        for a, b in zip(ordered, ordered[1:]):
            self.assertGreaterEqual(
                a, b,
                f"mask count should not grow with horizon: {counts}",
            )

    def test_x_x_raw_timestamps_unchanged_by_horizon_list(self) -> None:
        """X / X_raw / timestamps depend only on windowing, not labels."""
        df = _make_1s_bars(n_rows=1500, n_levels=25)
        single = build_npz_for_day(
            df, horizon_sec=180, input_len=300, stride=600, n_levels=25,
        )
        multi = build_npz_for_day(
            df, horizons_sec=self.HORIZONS,
            input_len=300, stride=600, n_levels=25,
        )
        np.testing.assert_array_equal(single["X"], multi["X"])
        np.testing.assert_array_equal(single["X_raw"], multi["X_raw"])
        np.testing.assert_array_equal(
            single["timestamps"], multi["timestamps"]
        )

    def test_duplicate_horizon_deduped(self) -> None:
        """Caller-supplied duplicates don't produce duplicate output keys."""
        df = _make_1s_bars(n_rows=900, n_levels=25)
        result = build_npz_for_day(
            df,
            horizons_sec=[60, 180, 60, 180],
            input_len=300,
            stride=300,
            n_levels=25,
        )
        self.assertEqual(list(result["horizons_sec"]), [60, 180])
        self.assertIn("y_60", result)
        self.assertIn("y_180", result)

    def test_empty_horizons_raises(self) -> None:
        df = _make_1s_bars(n_rows=900, n_levels=25)
        with self.assertRaises(ValueError):
            build_npz_for_day(
                df, horizons_sec=[], input_len=300, stride=180, n_levels=25,
            )

    def test_non_positive_horizon_raises(self) -> None:
        df = _make_1s_bars(n_rows=900, n_levels=25)
        with self.assertRaises(ValueError):
            build_npz_for_day(
                df, horizons_sec=[60, 0], input_len=300, stride=180,
                n_levels=25,
            )


# ---------------------------------------------------------------------------
# multi_day_pipeline tests
# ---------------------------------------------------------------------------


class TestMultiDayPipelineMultiHorizon(unittest.TestCase):
    """Pipeline forwards ``horizons_sec`` and honours the new min_rows rule."""

    HORIZONS = [60, 180, 300, 600]
    DATES = ["2024-02-01", "2024-02-02"]

    def _materialise(
        self, root: Path, n_seconds: int
    ) -> tuple[Path, Path, Path]:
        book_root = root / "book_snapshot_25"
        trades_root = root / "trades"
        output_dir = root / "npz"
        for i, date_str in enumerate(self.DATES):
            day_start_us = int(
                pd.Timestamp(date_str, tz="UTC").timestamp() * US_PER_SEC
            )
            df = _make_1s_bars(n_rows=n_seconds, n_levels=25, seed=i)
            # Shift timestamps to the folder's UTC day so the sanity filter
            # doesn't strip them.
            df["timestamp"] = (
                day_start_us + np.arange(n_seconds, dtype=np.int64) * US_PER_SEC
            )
            book_dir = book_root / date_str
            book_dir.mkdir(parents=True, exist_ok=True)
            df.to_csv(
                book_dir / "BTCUSDT.csv.gz", index=False, compression="gzip"
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        return book_root, trades_root, output_dir

    def test_multi_horizon_npz_written_with_all_fields(self) -> None:
        # Need >= input_len + max(horizons) = 300 + 600 = 900 rows; use 1500.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_root, _, output_dir = self._materialise(root, n_seconds=1500)

            paths = process_multi_day_crypto_folder(
                book_root=book_root,
                trades_root=None,
                output_dir=output_dir,
                horizons_sec=self.HORIZONS,
                input_len=300,
                stride=600,
                n_levels=25,
                verbose=False,
            )

            self.assertEqual(len(paths), len(self.DATES))
            for p in paths:
                with np.load(p, allow_pickle=True) as data:
                    keys = set(data.files)
                    # All 4 per-horizon label pairs present.
                    for h in self.HORIZONS:
                        self.assertIn(f"y_{h}", keys)
                        self.assertIn(f"y_mask_{h}", keys)
                    # Back-compat alias.
                    self.assertIn("y", keys)
                    self.assertIn("y_mask", keys)
                    # Metadata.
                    self.assertIn("horizons_sec", keys)
                    self.assertEqual(
                        list(data["horizons_sec"]), self.HORIZONS
                    )
                    # y aliases the smallest horizon (60).
                    np.testing.assert_array_equal(data["y"], data["y_60"])
                    np.testing.assert_array_equal(
                        data["y_mask"], data["y_mask_60"]
                    )

    def test_min_rows_uses_max_horizon(self) -> None:
        """A day that has 'enough' for horizon=60 but not for 600 is skipped
        when horizons_sec=[60, 600] is requested."""
        # 800 rows: enough for input_len+60=360 but not input_len+600=900.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_root, _, output_dir = self._materialise(root, n_seconds=800)

            paths = process_multi_day_crypto_folder(
                book_root=book_root,
                trades_root=None,
                output_dir=output_dir,
                horizons_sec=[60, 600],
                input_len=300,
                stride=600,
                n_levels=25,
                verbose=False,
            )
            # Both days should be skipped because of insufficient rows
            # for the 600s horizon.
            self.assertEqual(paths, [])

    def test_min_rows_permits_short_horizon(self) -> None:
        """Same 800-row day is *not* skipped when we only ask for horizon=60."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_root, _, output_dir = self._materialise(root, n_seconds=800)

            paths = process_multi_day_crypto_folder(
                book_root=book_root,
                trades_root=None,
                output_dir=output_dir,
                horizons_sec=[60],
                input_len=300,
                stride=180,
                n_levels=25,
                verbose=False,
            )
            self.assertEqual(len(paths), len(self.DATES))


if __name__ == "__main__":
    unittest.main()

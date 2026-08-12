"""Tests for ``src/features/multi_day_pipeline.py``.

We build a synthetic folder tree with three fake days of depth + trade data,
exercise ``process_multi_day_crypto_folder`` end-to-end, and verify:

* one NPZ is written per day, with the expected shapes;
* trades are incorporated (58 features when trades are present, 49 without);
* ``skip_existing=True`` actually short-circuits — confirmed via mtime.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

# Allow imports without pip install.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.features.multi_day_pipeline import process_multi_day_crypto_folder


# ---------------------------------------------------------------------------
# Synthetic-data helpers
# ---------------------------------------------------------------------------

N_LEVELS = 25
US_PER_SEC = 1_000_000
US_PER_DAY = 86_400 * US_PER_SEC


def _make_book_df(
    day_start_us: int,
    n_seconds: int,
    n_levels: int = N_LEVELS,
    seed: int = 0,
) -> pd.DataFrame:
    """Synthetic tick-level depth for a single day.

    We emit two ticks per second so the resampler has material to work with
    (last-per-second reduction). The price/amount columns follow the
    ``asks[i].price|amount`` / ``bids[i].price|amount`` naming convention
    the resampler expects.
    """
    rng = np.random.default_rng(seed)
    ticks_per_sec = 2
    n_ticks = n_seconds * ticks_per_sec

    # Two ticks per second, spaced ~500 ms, with a little jitter.
    base = np.repeat(np.arange(n_seconds) * US_PER_SEC, ticks_per_sec)
    offsets = np.tile(np.array([100_000, 600_000]), n_seconds)
    jitter = rng.integers(-50_000, 50_000, size=n_ticks)
    ts = day_start_us + base + offsets + jitter

    mid = 30_000.0 + np.cumsum(rng.normal(0, 0.5, n_ticks))

    data: dict[str, np.ndarray] = {"timestamp": ts.astype(np.int64)}
    for i in range(n_levels):
        # Asks go up, bids go down. Small per-level spread guarantees a
        # positive top-of-book spread for the microstructure features.
        data[f"asks[{i}].price"] = mid + 1.0 + i * 0.5
        data[f"asks[{i}].amount"] = rng.uniform(0.01, 5.0, n_ticks)
        data[f"bids[{i}].price"] = mid - 1.0 - i * 0.5
        data[f"bids[{i}].amount"] = rng.uniform(0.01, 5.0, n_ticks)

    return pd.DataFrame(data)


def _make_trades_df(
    day_start_us: int,
    n_seconds: int,
    seed: int = 0,
) -> pd.DataFrame:
    """Synthetic trade ticks for a single day, with the on-disk schema
    ``exchange, symbol, timestamp, local_timestamp, id, side, price, amount``
    (lowercase side values).  The pipeline is expected to normalise these
    into the names ``aggregate_trades_to_1s`` wants.
    """
    rng = np.random.default_rng(seed + 7)
    # ~20 trades per second keeps the test snappy but still exercises the
    # 1-second aggregation.
    n_trades = n_seconds * 20
    ts = day_start_us + np.sort(rng.integers(0, n_seconds * US_PER_SEC, size=n_trades))
    return pd.DataFrame(
        {
            "exchange": "binance-futures",
            "symbol": "BTCUSDT",
            "timestamp": ts,
            "local_timestamp": ts + rng.integers(0, 1000, n_trades),
            "id": np.arange(n_trades, dtype=np.int64),
            "side": rng.choice(["buy", "sell"], size=n_trades),
            "price": 30_000.0 + rng.normal(0, 5.0, n_trades),
            "amount": rng.uniform(0.001, 1.0, n_trades),
        }
    )


def _materialise_day(
    book_root: Path,
    trades_root: Path | None,
    date_str: str,
    day_index: int,
    n_seconds: int,
    include_trades: bool,
) -> None:
    """Write one day's book (and optionally trades) to the expected paths."""
    # Use timestamps that match the folder date (UTC midnight start).
    # The date-folder sanity filter in multi_day_pipeline strips rows
    # outside the folder's UTC day, so synthetic timestamps must match.
    day_start_us = int(pd.Timestamp(date_str, tz="UTC").timestamp() * US_PER_SEC)

    book_dir = book_root / date_str
    book_dir.mkdir(parents=True, exist_ok=True)
    book_df = _make_book_df(day_start_us, n_seconds, seed=day_index)
    book_df.to_csv(book_dir / "BTCUSDT.csv.gz", index=False, compression="gzip")

    if include_trades and trades_root is not None:
        trades_dir = trades_root / date_str
        trades_dir.mkdir(parents=True, exist_ok=True)
        trades_df = _make_trades_df(day_start_us, n_seconds, seed=day_index)
        trades_df.to_csv(
            trades_dir / "BTCUSDT.csv.gz", index=False, compression="gzip"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


DATES = ["2024-01-01", "2024-01-02", "2024-01-03"]
# Enough seconds to yield >=2 windows per day with input_len=300, stride=180,
# horizon=180: need >= 300 + 180 + 180 = 660s so there is at least one valid
# label. We use 900s (15 minutes) to get ~4 windows/day.
N_SECONDS = 900


class _FixtureMixin:
    """Shared setup/teardown for the multi-day pipeline tests."""

    tmpdir: tempfile.TemporaryDirectory
    book_root: Path
    trades_root: Path
    output_dir: Path

    def _setup_fixture(self, with_trades: bool = True) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.book_root = root / "book_snapshot_25"
        self.trades_root = root / "trades" / "trades"
        self.output_dir = root / "npz"

        for i, date_str in enumerate(DATES):
            _materialise_day(
                self.book_root,
                self.trades_root if with_trades else None,
                date_str,
                day_index=i,
                n_seconds=N_SECONDS,
                include_trades=with_trades,
            )

    def _teardown_fixture(self) -> None:
        self.tmpdir.cleanup()


class TestMultiDayPipelineHappyPath(unittest.TestCase, _FixtureMixin):
    """Three days, trades present — expect 3 NPZs with 58 features each."""

    def setUp(self) -> None:
        self._setup_fixture(with_trades=True)

    def tearDown(self) -> None:
        self._teardown_fixture()

    def test_three_npz_with_trade_features(self) -> None:
        paths = process_multi_day_crypto_folder(
            book_root=self.book_root,
            trades_root=self.trades_root,
            output_dir=self.output_dir,
            horizon_sec=180,
            input_len=300,
            stride=180,
            n_levels=N_LEVELS,
            verbose=False,
        )

        # --- 3 NPZs are returned and physically present ---------------------
        self.assertEqual(len(paths), 3)
        for p in paths:
            self.assertTrue(p.exists(), f"missing output: {p}")
            self.assertEqual(p.suffix, ".npz")

        # --- per-file shape contract ----------------------------------------
        for p in paths:
            with np.load(p, allow_pickle=True) as data:
                X = data["X"]
                X_raw = data["X_raw"]
                y = data["y"]
                y_mask = data["y_mask"]
                timestamps = data["timestamps"]
                features = list(data["features"])

            # Trade-enabled: 43 microstructure + 9 trade + 6 derived = 58.
            self.assertEqual(
                X.shape[2], 58,
                f"{p.name}: expected 58 features (trades on), got {X.shape[2]}",
            )
            self.assertEqual(len(features), 58)

            self.assertEqual(X.ndim, 3)
            self.assertEqual(X.shape[1], 300)          # input_len

            self.assertEqual(X_raw.ndim, 4)
            self.assertEqual(X_raw.shape[0], X.shape[0])
            self.assertEqual(X_raw.shape[1], 300)
            self.assertEqual(X_raw.shape[3], 4)        # [bid_dp, bid_la, ask_dp, ask_la]

            self.assertEqual(y.shape, (X.shape[0],))
            self.assertEqual(y_mask.shape, (X.shape[0],))
            self.assertEqual(timestamps.shape, (X.shape[0],))

            # dtypes — important because we size disk budgets against them.
            self.assertEqual(X.dtype, np.float32)
            self.assertEqual(X_raw.dtype, np.float32)
            self.assertEqual(y.dtype, np.float32)
            self.assertEqual(y_mask.dtype, np.uint8)

            # At least *some* labels should be valid. If they are all
            # masked out the windowing maths is wrong.
            self.assertGreater(int(y_mask.sum()), 0)

        # Trade-specific feature name must appear when trades are supplied.
        with np.load(paths[0], allow_pickle=True) as data:
            features = [str(f) for f in data["features"]]
        self.assertIn("buy_volume_1s", features)
        self.assertIn("net_trade_flow_1s", features)


class TestMultiDayPipelineNoTrades(unittest.TestCase, _FixtureMixin):
    """Without ``trades_root`` the output must carry exactly 49 features."""

    def setUp(self) -> None:
        self._setup_fixture(with_trades=False)

    def tearDown(self) -> None:
        self._teardown_fixture()

    def test_depth_only_feature_count(self) -> None:
        paths = process_multi_day_crypto_folder(
            book_root=self.book_root,
            trades_root=None,
            output_dir=self.output_dir,
            horizon_sec=180,
            input_len=300,
            stride=180,
            n_levels=N_LEVELS,
            verbose=False,
        )

        self.assertEqual(len(paths), 3)
        with np.load(paths[0], allow_pickle=True) as data:
            features = [str(f) for f in data["features"]]
            X = data["X"]

        # 43 microstructure + 6 derived = 49 (no trade block).
        self.assertEqual(X.shape[2], 49)
        self.assertEqual(len(features), 49)
        self.assertNotIn("buy_volume_1s", features)


class TestMultiDayPipelineSkipExisting(unittest.TestCase, _FixtureMixin):
    """``skip_existing=True`` must not rewrite files that already exist."""

    def setUp(self) -> None:
        self._setup_fixture(with_trades=True)

    def tearDown(self) -> None:
        self._teardown_fixture()

    def test_second_run_skips(self) -> None:
        # --- first run populates the output dir ----------------------------
        first = process_multi_day_crypto_folder(
            book_root=self.book_root,
            trades_root=self.trades_root,
            output_dir=self.output_dir,
            horizon_sec=180,
            input_len=300,
            stride=180,
            n_levels=N_LEVELS,
            skip_existing=True,
            verbose=False,
        )
        self.assertEqual(len(first), 3)
        mtimes_before = {p.name: p.stat().st_mtime_ns for p in first}
        sizes_before = {p.name: p.stat().st_size for p in first}

        # Ensure clock advances past filesystem mtime resolution.
        time.sleep(1.1)

        # --- second run with skip_existing=True ----------------------------
        second = process_multi_day_crypto_folder(
            book_root=self.book_root,
            trades_root=self.trades_root,
            output_dir=self.output_dir,
            horizon_sec=180,
            input_len=300,
            stride=180,
            n_levels=N_LEVELS,
            skip_existing=True,
            verbose=False,
        )
        self.assertEqual(len(second), 3)
        for p in second:
            self.assertEqual(
                p.stat().st_mtime_ns,
                mtimes_before[p.name],
                f"{p.name} should not have been rewritten",
            )
            self.assertEqual(p.stat().st_size, sizes_before[p.name])

        # Sanity: with skip_existing=False the mtime *must* move for at
        # least one file. We re-run the first date only by deleting the
        # others from the output dir so the run is cheap.
        kept = self.output_dir / f"{DATES[0]}.npz"
        time.sleep(1.1)
        third = process_multi_day_crypto_folder(
            book_root=self.book_root,
            trades_root=self.trades_root,
            output_dir=self.output_dir,
            horizon_sec=180,
            input_len=300,
            stride=180,
            n_levels=N_LEVELS,
            skip_existing=False,
            start_date=DATES[0],
            end_date=DATES[0],
            verbose=False,
        )
        self.assertEqual(len(third), 1)
        self.assertGreater(kept.stat().st_mtime_ns, mtimes_before[kept.name])


class TestMultiDayPipelineDateFilter(unittest.TestCase, _FixtureMixin):
    """``start_date`` / ``end_date`` slice the discovered set correctly."""

    def setUp(self) -> None:
        self._setup_fixture(with_trades=True)

    def tearDown(self) -> None:
        self._teardown_fixture()

    def test_date_range_filter(self) -> None:
        paths = process_multi_day_crypto_folder(
            book_root=self.book_root,
            trades_root=self.trades_root,
            output_dir=self.output_dir,
            horizon_sec=180,
            input_len=300,
            stride=180,
            n_levels=N_LEVELS,
            start_date=DATES[1],
            end_date=DATES[1],
            verbose=False,
        )
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].name, f"{DATES[1]}.npz")


class TestMultiDayPipelineV4Flags(unittest.TestCase):
    """``include_ridge_features`` and ``include_regime_prior`` are forwarded."""

    def test_forwards_v4_flags(self) -> None:
        """process_multi_day_crypto_folder accepts and forwards V4 flags."""
        with tempfile.TemporaryDirectory() as tmp:
            book_root = Path(tmp) / "book"
            trades_root = Path(tmp) / "trades"
            out_dir = Path(tmp) / "npz"
            _materialise_day(
                book_root, trades_root, "2024-01-01",
                day_index=0, n_seconds=2400, include_trades=True,
            )
            paths = process_multi_day_crypto_folder(
                book_root=str(book_root),
                trades_root=str(trades_root),
                output_dir=str(out_dir),
                horizons_sec=[60, 180],
                input_len=600,
                stride=60,
                n_levels=25,
                include_ridge_features=True,
                include_regime_prior=True,
                skip_existing=False,
                verbose=False,
            )
            self.assertEqual(len(paths), 1)
            d = np.load(paths[0], allow_pickle=True)
            self.assertIn("regime_prior", d.files)
            self.assertEqual(d["regime_prior"].shape[1], 6)
            self.assertEqual(d["X"].shape[-1], 64)
            print("PASS: test_forwards_v4_flags")


if __name__ == "__main__":
    unittest.main()

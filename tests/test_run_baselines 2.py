"""Smoke test for ``run_baselines.py``.

Creates a handful of synthetic NPZ files matching the real schema that
``src/features/pipeline.py`` produces, plants a mild linear signal, and
runs the full baseline CLI end-to-end.  The goal is *schema correctness*
and *pipeline wiring* -- not accuracy guarantees.

What we verify:
  1. ``run_baselines.main`` returns exit code 0 on synthetic data.
  2. An output JSON is written with the expected top-level keys.
  3. Every baseline that's applicable is present in ``results``.
  4. A planted linear signal (y = beta * last-step feature + noise) is
     recovered by Ridge with positive correlation -- sanity check that
     the temporal split isn't silently leaking.
  5. Naive baselines whose required features are missing are silently
     skipped (not raised as errors).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import run_baselines as rb  # noqa: E402  (path manipulation above)


# The canonical feature list produced by src.features.pipeline when trades
# are available (matches what we see in data/npz_full/*.npz).
# We ONLY need feature names that either (a) exist in the real NPZ schema,
# or (b) are required by naive baseline defaults; the rest can be padded
# out with dummy names as the runner only looks up what it needs.
_REAL_FEATURES = [
    "log_return_1s", "log_return_5s", "log_return_30s",
    "spread_bps", "spread_change",
    "obi_L1", "obi_L5", "obi_L10", "obi_L25", "obi_L1_delta",
    "bid_depth_L5", "ask_depth_L5", "bid_depth_L25", "ask_depth_L25",
    "depth_ratio_L5",
    "weighted_price_bid_L10", "weighted_price_ask_L10",
    "price_pressure",
    "realized_vol_30s", "realized_vol_60s", "realized_vol_300s",
    "depth_flow_ratio_30s",
    "bid_slope_L10", "ask_slope_L10",
    "bid_concentration", "ask_concentration",
    "bid_amt_ratio_L0", "ask_amt_ratio_L0",
    "bid_amt_ratio_L1", "ask_amt_ratio_L1",
    "bid_amt_ratio_L2", "ask_amt_ratio_L2",
    "bid_amt_ratio_L3", "ask_amt_ratio_L3",
    "bid_amt_ratio_L4", "ask_amt_ratio_L4",
    "second_of_day_sin", "second_of_day_cos",
    "delta_bid_depth_L5", "delta_ask_depth_L5", "net_order_flow_L5",
    "delta_obi_L5_5s", "delta_pressure_5s",
    "buy_volume_1s", "sell_volume_1s",
    "net_trade_flow_1s", "trade_imbalance_1s",
    "cumulative_net_flow_30s", "cumulative_net_flow_300s",
    "trade_intensity_30s", "vwap_return_1s",
    "kyle_lambda_30s", "microprice_dev_bps", "roll_spread_60s",
    "vpin_60s", "vpin_300s", "book_pressure_imbalance",
    "price_impact_30s",
]


def _synth_day_npz(
    path: Path,
    n_windows: int,
    seq_len: int,
    feature_names: list,
    seed: int = 0,
    signal_strength: float = 0.3,
) -> None:
    """Write a synthetic NPZ with the V3 dual-path schema.

    Signal: y = ``signal_strength`` * X[:, -1, obi_L5] + noise, matching
    the OBI contrarian baseline (negated) up to sign.  Ridge should pick
    up this linear dependency easily.
    """
    rng = np.random.default_rng(seed)
    n_features = len(feature_names)
    n_levels = 20

    X = rng.standard_normal((n_windows, seq_len, n_features)).astype(np.float32)
    X_raw = rng.standard_normal((n_windows, seq_len, n_levels, 4)).astype(np.float32)

    obi_idx = feature_names.index("obi_L5")
    noise = 0.1 * rng.standard_normal(n_windows).astype(np.float32)
    y = signal_strength * X[:, -1, obi_idx] + noise
    y = y.astype(np.float32)

    y_mask = np.ones(n_windows, dtype=np.float32)
    # Poke a handful of zero-mask samples just like the real pipeline does
    y_mask[:: max(1, n_windows // 10)] = 0.0

    # Timestamps: evenly spaced seconds across one day, microseconds epoch
    day_offset_us = 1_672_531_200 * 1_000_000 + seed * 86_400_000_000
    timestamps = (day_offset_us + np.arange(n_windows) * 60 * 1_000_000).astype(
        np.int64
    )

    np.savez(
        str(path),
        X=X,
        X_raw=X_raw,
        y=y,
        y_mask=y_mask,
        timestamps=timestamps,
        features=np.array(feature_names, dtype=object),
    )


class TestRunBaselines(unittest.TestCase):

    def test_end_to_end_smoke(self) -> None:
        """Full CLI-equivalent run on synthetic NPZ files."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp) / "npz"
            npz_dir.mkdir()
            out_path = Path(tmp) / "baselines.json"

            # 4 days x ~70 windows each -- small enough to run in seconds,
            # but respects the 3-day minimum for temporal split.
            for i in range(4):
                _synth_day_npz(
                    path=npz_dir / f"2023-01-{i+1:02d}.npz",
                    n_windows=70,
                    seq_len=80,            # keep small for FITS speed
                    feature_names=_REAL_FEATURES,
                    seed=100 + i,
                )

            ret = rb.main([
                "--npz-dir", str(npz_dir),
                "--output", str(out_path),
                "--fits-epochs", "3",       # quick smoke
                "--fits-batch-size", "64",
            ])

            self.assertEqual(ret, 0, "run_baselines.main should exit 0")
            self.assertTrue(out_path.exists(), "output JSON missing")

            with open(out_path) as f:
                data = json.load(f)

            # Top-level schema
            for key in ("npz_dir", "n_days", "n_windows",
                        "seq_len", "n_features", "split", "results"):
                self.assertIn(key, data, f"missing key {key!r}")

            self.assertEqual(data["n_days"], 4)
            self.assertEqual(data["n_windows"], 4 * 70)
            self.assertEqual(data["split"]["train_windows"]
                             + data["split"]["val_windows"]
                             + data["split"]["test_windows"],
                             data["n_windows"])

            # Every baseline result row has the expected metric keys
            results = data["results"]
            self.assertGreater(len(results), 0, "no baseline results")

            needed_metrics = {
                "model", "correlation", "rank_correlation", "r2",
                "direction_accuracy", "residual_autocorr_lag1",
                "score_bps", "n",
            }
            for row in results:
                missing = needed_metrics - set(row.keys())
                self.assertFalse(
                    missing, f"row {row.get('model')!r} missing {missing}"
                )

            # Trainable baselines must have run (models referenced by exact
            # prefix so the Ridge-noise test below can find them).
            names = [r["model"] for r in results]
            self.assertIn("Ridge", names)
            self.assertIn("TemporalRidge", names)

            # Ridge should recover the planted signal -- positive correlation.
            ridge_row = next(r for r in results if r["model"] == "Ridge")
            self.assertFalse(
                np.isnan(ridge_row["correlation"]),
                "Ridge correlation is NaN on signal-planted data",
            )
            # With a beta of 0.3 and low noise we expect solidly > 0.1.
            self.assertGreater(
                ridge_row["correlation"], 0.1,
                f"Ridge should find planted signal, got corr="
                f"{ridge_row['correlation']:.4f}",
            )

            # Naive baselines that require real features should have been
            # auto-matched: OBI uses obi_L5, Momentum uses log_return_30s,
            # Flow uses net_trade_flow_1s, MicropriceDev uses microprice_dev_bps.
            self.assertTrue(
                any(r["model"].startswith("OBI[contrarian]") for r in results),
                f"OBI baseline not in results: {names}",
            )
            self.assertTrue(
                any(r["model"].startswith("Momentum") for r in results),
                f"Momentum baseline not in results: {names}",
            )

    def test_load_days_and_temporal_split(self) -> None:
        """Directly exercise the lower-level loader + split helpers."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp)
            counts = [30, 45, 20, 50, 40]
            for i, n in enumerate(counts):
                _synth_day_npz(
                    path=npz_dir / f"2023-02-{i+1:02d}.npz",
                    n_windows=n,
                    seq_len=20,
                    feature_names=_REAL_FEATURES,
                    seed=200 + i,
                )

            days, X, y, mask, feats, per_day = rb.load_days(str(npz_dir))
            self.assertEqual(len(days), 5)
            self.assertEqual(X.shape[0], sum(counts))
            self.assertEqual(per_day, counts)
            self.assertEqual(feats, _REAL_FEATURES)

            tr, va, te = rb.temporal_split(per_day, train_frac=0.6, val_frac=0.2)

            # Non-overlapping, covers all samples, in order.
            self.assertEqual(tr.start, 0)
            self.assertEqual(tr.stop, va.start)
            self.assertEqual(va.stop, te.start)
            self.assertEqual(te.stop, sum(counts))
            # Every split must be non-empty on this 5-day setup.
            self.assertGreater(tr.stop - tr.start, 0)
            self.assertGreater(va.stop - va.start, 0)
            self.assertGreater(te.stop - te.start, 0)

    def test_naive_baseline_feature_fallback(self) -> None:
        """Missing feature for a naive baseline should be skipped, not raise."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp) / "npz"
            npz_dir.mkdir()
            out_path = Path(tmp) / "baselines.json"

            # Build a minimal feature set that only has obi_L5 (OBI) and
            # log_return_30s (Momentum).  Flow + MicropriceDev should be
            # skipped with a warning, not raise.
            feats = [
                "obi_L5", "log_return_30s",
                "dummy_a", "dummy_b", "dummy_c",
            ]
            for i in range(3):
                _synth_day_npz(
                    path=npz_dir / f"2023-03-{i+1:02d}.npz",
                    n_windows=40,
                    seq_len=20,
                    feature_names=feats,
                    seed=300 + i,
                )

            ret = rb.main([
                "--npz-dir", str(npz_dir),
                "--output", str(out_path),
                "--no-fits",    # skip FITS for this test
            ])
            self.assertEqual(ret, 0)

            data = json.loads(out_path.read_text())
            names = [r["model"] for r in data["results"]]

            # OBI + Momentum available
            self.assertTrue(any(n.startswith("OBI[contrarian]") for n in names))
            self.assertTrue(any(n.startswith("Momentum") for n in names))

            # Flow + MicropriceDev should have been silently skipped
            self.assertFalse(any(n.startswith("Flow[") for n in names),
                             f"Flow should be skipped, got names={names}")
            self.assertFalse(any(n.startswith("MicropriceDeviation[") for n in names),
                             f"MicropriceDev should be skipped, got names={names}")

    def test_fewer_than_three_days_raises(self) -> None:
        """``temporal_split`` refuses to split < 3 days -- test surfaces that."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp)
            for i in range(2):
                _synth_day_npz(
                    path=npz_dir / f"2023-04-{i+1:02d}.npz",
                    n_windows=30,
                    seq_len=20,
                    feature_names=_REAL_FEATURES,
                    seed=400 + i,
                )

            with self.assertRaises(ValueError):
                rb.run_baselines(
                    npz_dir=str(npz_dir),
                    output_path=str(Path(tmp) / "out.json"),
                    run_fits=False,
                )


if __name__ == "__main__":
    unittest.main()

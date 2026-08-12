"""Memory-efficient NPZ loader tests for ``run_baselines``.

Covers the new streaming loaders added to prevent the 100+ GB OOM that
the previous ``load_days()`` would hit on a full 1004-day run:

- ``load_last_step_features`` must return ``(N, F)`` last-timestep data
  that matches ``X[:, -1, :]`` of the full tensor.
- ``load_temporal_features`` must return ``(N, 4F)`` with the four
  ``(last, mean, std, trend)`` aggregates computed per-day.
- Feature names must be validated across days; a mismatch should raise.
- Empty NPZs should be skipped silently (they contribute 0 samples but
  are otherwise valid).

Intentionally uses small synthetic NPZs (a few hundred windows each) so
the test runs in under a second on CI.  The goal is *shape + correctness*
verification, not benchmarking real RAM usage.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import run_baselines as rb  # noqa: E402


# A reasonable fake feature list -- names don't have to be realistic for
# the loader tests, only for the naive-baseline tests.  We include
# ``obi_L5`` / ``log_return_30s`` in case later tests want to reuse this.
_FEATURES = [f"feat_{i}" for i in range(10)]


def _write_synth_day(
    path: Path,
    n_windows: int,
    seq_len: int,
    features: list,
    seed: int = 0,
    empty: bool = False,
) -> np.ndarray:
    """Write a synthetic per-day NPZ matching the pipeline schema.

    Returns the full ``X`` array so the caller can cross-check slices
    against what the streaming loader produces.
    """
    rng = np.random.default_rng(seed)
    n_feat = len(features)

    if empty:
        X = np.zeros((0, seq_len, n_feat), dtype=np.float32)
        X_raw = np.zeros((0, seq_len, 20, 4), dtype=np.float32)
        y = np.zeros((0,), dtype=np.float32)
        mask = np.zeros((0,), dtype=np.float32)
        timestamps = np.zeros((0,), dtype=np.int64)
    else:
        X = rng.standard_normal((n_windows, seq_len, n_feat)).astype(np.float32)
        X_raw = rng.standard_normal((n_windows, seq_len, 20, 4)).astype(np.float32)
        y = rng.standard_normal(n_windows).astype(np.float32)
        mask = np.ones(n_windows, dtype=np.float32)
        mask[::7] = 0.0  # sprinkle some zero-mask to exercise the sanitiser
        timestamps = np.arange(n_windows, dtype=np.int64) * 60

    np.savez(
        str(path),
        X=X,
        X_raw=X_raw,
        y=y,
        y_mask=mask,
        timestamps=timestamps,
        features=np.array(features, dtype=object),
    )
    return X


class TestStreamingLoaders(unittest.TestCase):

    def test_load_last_step_shapes_and_values(self) -> None:
        """``load_last_step_features`` returns X[:, -1, :] exactly."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp)
            n_days = 5
            n_win_per_day = 200
            seq_len = 60

            full_xs = []
            for i in range(n_days):
                X_full = _write_synth_day(
                    path=npz_dir / f"2024-01-{i+1:02d}.npz",
                    n_windows=n_win_per_day,
                    seq_len=seq_len,
                    features=_FEATURES,
                    seed=10 + i,
                )
                full_xs.append(X_full[:, -1, :])  # expected last-step slice

            days, X_last, y, mask, feats, counts = rb.load_last_step_features(
                str(npz_dir)
            )

            # Shape: (N_total, F) -- memory savings vs (N, L, F).
            self.assertEqual(X_last.shape, (n_days * n_win_per_day, len(_FEATURES)))
            self.assertEqual(y.shape, (n_days * n_win_per_day,))
            self.assertEqual(mask.shape, (n_days * n_win_per_day,))

            # Values: exactly the last-timestep slice of the original data.
            expected = np.concatenate(full_xs, axis=0)
            np.testing.assert_allclose(X_last, expected, rtol=0, atol=0)

            # Metadata sanity checks
            self.assertEqual(len(days), n_days)
            self.assertEqual(counts, [n_win_per_day] * n_days)
            self.assertEqual(feats, _FEATURES)

    def test_load_temporal_aggregates_correctness(self) -> None:
        """``load_temporal_features`` computes (last, mean, std, trend) correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp)
            n_days = 3
            n_win_per_day = 100
            seq_len = 40

            full_xs = []
            for i in range(n_days):
                X_full = _write_synth_day(
                    path=npz_dir / f"2024-02-{i+1:02d}.npz",
                    n_windows=n_win_per_day,
                    seq_len=seq_len,
                    features=_FEATURES,
                    seed=50 + i,
                )
                full_xs.append(X_full)

            days, X_agg, y, mask, feats, counts = rb.load_temporal_features(
                str(npz_dir)
            )

            F = len(_FEATURES)
            # Shape: (N, 4F) -- last ⊕ mean ⊕ std ⊕ trend
            self.assertEqual(X_agg.shape, (n_days * n_win_per_day, 4 * F))

            # Reconstruct expected aggregates day-by-day and compare.
            expected_blocks = []
            for X_day in full_xs:
                last = X_day[:, -1, :]
                mean = X_day.mean(axis=1)
                std = X_day.std(axis=1)
                trend = X_day[:, -1, :] - X_day[:, 0, :]
                expected_blocks.append(
                    np.concatenate([last, mean, std, trend], axis=1)
                )
            expected = np.concatenate(expected_blocks, axis=0).astype(np.float32)
            # Float32 aggregate math + post-concat: tolerate tiny drift.
            np.testing.assert_allclose(X_agg, expected, rtol=1e-5, atol=1e-5)

            self.assertEqual(feats, _FEATURES)
            self.assertEqual(counts, [n_win_per_day] * n_days)

    def test_feature_name_mismatch_raises(self) -> None:
        """A day with different feature names must raise a clear error."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp)
            _write_synth_day(
                npz_dir / "2024-03-01.npz",
                n_windows=30, seq_len=10, features=_FEATURES, seed=1,
            )
            # Second day has DIFFERENT feature names -- runner must reject.
            bad_features = [f"bogus_{i}" for i in range(len(_FEATURES))]
            _write_synth_day(
                npz_dir / "2024-03-02.npz",
                n_windows=30, seq_len=10, features=bad_features, seed=2,
            )

            for loader in (rb.load_last_step_features, rb.load_temporal_features):
                with self.assertRaises(ValueError):
                    loader(str(npz_dir))

    def test_empty_day_is_skipped(self) -> None:
        """A 0-window NPZ should be silently skipped, not raise."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp)
            # Day 1: real data.  Day 2: empty.  Day 3: real data.
            _write_synth_day(
                npz_dir / "2024-04-01.npz",
                n_windows=50, seq_len=20, features=_FEATURES, seed=11,
            )
            _write_synth_day(
                npz_dir / "2024-04-02.npz",
                n_windows=0, seq_len=20, features=_FEATURES, seed=12,
                empty=True,
            )
            _write_synth_day(
                npz_dir / "2024-04-03.npz",
                n_windows=70, seq_len=20, features=_FEATURES, seed=13,
            )

            days, X_last, y, _, _, counts = rb.load_last_step_features(str(npz_dir))
            self.assertEqual(days, ["2024-04-01", "2024-04-03"])
            self.assertEqual(counts, [50, 70])
            self.assertEqual(X_last.shape, (120, len(_FEATURES)))
            self.assertEqual(y.shape, (120,))

    def test_backcompat_load_days_alias(self) -> None:
        """``rb.load_days`` must still exist and behave as ``_load_days_full``."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp)
            for i in range(3):
                _write_synth_day(
                    npz_dir / f"2024-05-{i+1:02d}.npz",
                    n_windows=40, seq_len=15, features=_FEATURES, seed=20 + i,
                )
            days, X, y, mask, feats, counts = rb.load_days(str(npz_dir))
            # Full 3D tensor -- the legacy behaviour we still need for FITS.
            self.assertEqual(X.ndim, 3)
            self.assertEqual(X.shape[1], 15)
            self.assertEqual(X.shape[2], len(_FEATURES))
            self.assertEqual(counts, [40, 40, 40])
            self.assertEqual(feats, _FEATURES)


class TestPeakMemoryEstimate(unittest.TestCase):
    """Sanity check that the loaders actually return much smaller arrays."""

    def test_last_step_is_smaller_than_full(self) -> None:
        """Compare element counts -- last-step must be ~L times smaller."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp)
            for i in range(4):
                _write_synth_day(
                    npz_dir / f"2024-06-{i+1:02d}.npz",
                    n_windows=150, seq_len=50, features=_FEATURES, seed=30 + i,
                )
            _, X_last, _, _, _, _ = rb.load_last_step_features(str(npz_dir))
            _, X_agg, _, _, _, _ = rb.load_temporal_features(str(npz_dir))
            _, X_full, _, _, _, _ = rb.load_days(str(npz_dir))

            # N_total*L*F for full vs N_total*F for last vs N_total*4F for agg.
            self.assertEqual(X_last.size * 50, X_full.size)  # last-step is L=50 smaller
            self.assertEqual(X_agg.size, 4 * X_last.size)    # 4 aggregates


class TestFITSAutoSkip(unittest.TestCase):
    """Verify the FITS-auto-skip logic that prevents OOM on large datasets."""

    def test_path_snapshot_stable_across_loads(self) -> None:
        """``snapshot_npz_paths`` returns a list that's loader-compatible."""
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp)
            for i in range(3):
                _write_synth_day(
                    npz_dir / f"2024-07-{i+1:02d}.npz",
                    n_windows=40, seq_len=20, features=_FEATURES, seed=40 + i,
                )
            paths = rb.snapshot_npz_paths(str(npz_dir))
            self.assertEqual(len(paths), 3)

            # Now "inject" a 4th file AFTER the snapshot -- the loader
            # should still only see the 3 captured in the snapshot.
            _write_synth_day(
                npz_dir / "2024-07-04.npz",
                n_windows=40, seq_len=20, features=_FEATURES, seed=44,
            )
            days, _, _, _, _, counts = rb.load_last_step_features(paths)
            self.assertEqual(len(days), 3)
            self.assertEqual(counts, [40, 40, 40])

    def test_fits_autoskip_on_small_dataset(self) -> None:
        """Small datasets must NOT auto-skip FITS."""
        import json
        with tempfile.TemporaryDirectory() as tmp:
            npz_dir = Path(tmp) / "n"
            npz_dir.mkdir()
            out = Path(tmp) / "out.json"
            for i in range(3):
                _write_synth_day(
                    npz_dir / f"2024-08-{i+1:02d}.npz",
                    n_windows=30, seq_len=20, features=_FEATURES, seed=50 + i,
                )
            rb.run_baselines(
                npz_dir=str(npz_dir),
                output_path=str(out),
                run_fits=False,  # don't actually train FITS (slow on CI)
            )
            data = json.loads(out.read_text())
            # fits_skipped_reason is None when the dataset is small enough.
            self.assertIsNone(data.get("fits_skipped_reason"))


if __name__ == "__main__":
    unittest.main()

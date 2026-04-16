"""Tests for lazy per-day loading in ``LOBDatasetV2``.

Covers the refactor that replaced eager ``np.concatenate`` at init with a
metadata-only scan + LRU-bounded on-demand day loading:

  1. Smoke — N synthetic NPZs, round-trip len/getitem shapes.
  2. LRU — cache never exceeds ``cache_size`` even under random access.
  3. Streaming compute_stats — within float32 tolerance of the naive reference.
  4. Normalize integration — ``normalize=True`` with supplied mean/std yields
     already-normalised features in __getitem__.
  5. Y-normalise — ``y_norm=(median, sigma, clip)`` applied per-item.
  6. OOM regression — 20 days at ~50 MB each stay bounded to roughly
     ``cache_size × per_day + overhead`` RSS.
  7. Multi-horizon — stacked y/mask + horizon keys still work lazily.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.training import dataset as ds_module
from src.training.dataset import LOBDatasetV2, _np_load_with_retry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_day(
    path: str,
    n_win: int,
    seq_len: int,
    n_features: int,
    *,
    n_levels: int = 0,
    horizons: tuple[int, ...] = (),
    seed: int = 0,
) -> None:
    """Write a single synthetic day to ``path``."""
    rng = np.random.default_rng(seed)
    save: dict[str, np.ndarray] = {
        "X": rng.standard_normal((n_win, seq_len, n_features)).astype(np.float32),
        "timestamps": np.arange(n_win, dtype=np.int64),
        "features": np.array([f"f{i}" for i in range(n_features)], dtype=object),
    }
    if n_levels:
        save["X_raw"] = rng.standard_normal(
            (n_win, seq_len, n_levels, 4)
        ).astype(np.float32)

    # Shortest-horizon alias always present
    save["y"] = rng.standard_normal(n_win).astype(np.float32)
    save["y_mask"] = (rng.random(n_win) > 0.1).astype(np.float32)

    for h in horizons:
        save[f"y_{h}"] = rng.standard_normal(n_win).astype(np.float32)
        save[f"y_mask_{h}"] = (rng.random(n_win) > 0.1).astype(np.float32)

    np.savez_compressed(path, **save)


def _tmp_dataset(
    tmpdir: str,
    n_days: int = 5,
    n_win: int = 8,
    seq_len: int = 4,
    n_features: int = 3,
    n_levels: int = 0,
    horizons: tuple[int, ...] = (),
    seed: int = 42,
) -> list[str]:
    days: list[str] = []
    for d in range(n_days):
        day = f"day_{d:03d}"
        _write_day(
            os.path.join(tmpdir, f"{day}.npz"),
            n_win=n_win,
            seq_len=seq_len,
            n_features=n_features,
            n_levels=n_levels,
            horizons=horizons,
            seed=seed + d,
        )
        days.append(day)
    return days


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSmoke(unittest.TestCase):
    def test_basic_shapes_and_totals(self) -> None:
        n_days, n_win, seq_len, n_features, n_levels = 5, 7, 4, 3, 5
        with tempfile.TemporaryDirectory() as tmp:
            days = _tmp_dataset(
                tmp, n_days=n_days, n_win=n_win, seq_len=seq_len,
                n_features=n_features, n_levels=n_levels,
            )
            ds = LOBDatasetV2(tmp, days=days, cache_size=3)
            self.assertEqual(len(ds), n_days * n_win)
            self.assertTrue(ds.has_raw)

            # First, last, and a middle sample all succeed.
            for idx in (0, n_win, n_days * n_win - 1):
                sample = ds[idx]
                self.assertEqual(len(sample), 4)
                x_feat, x_raw, y, m = sample
                self.assertEqual(x_feat.shape, (seq_len, n_features))
                self.assertEqual(x_raw.shape, (seq_len, n_levels, 4))
                self.assertEqual(y.ndim, 0)
                self.assertEqual(m.ndim, 0)


class TestLRUCache(unittest.TestCase):
    def test_cache_bounded_to_cache_size(self) -> None:
        n_days, n_win = 5, 6
        with tempfile.TemporaryDirectory() as tmp:
            days = _tmp_dataset(
                tmp, n_days=n_days, n_win=n_win, seq_len=3, n_features=2,
            )
            ds = LOBDatasetV2(tmp, days=days, cache_size=2)

            # Hit each day in order — cache size should never exceed 2.
            for d in range(n_days):
                _ = ds[d * n_win]   # first sample of day d
                self.assertLessEqual(
                    len(ds._cache), 2,
                    f"cache grew past cache_size=2 after visiting day {d}",
                )

    def test_lru_eviction_order(self) -> None:
        n_days, n_win = 4, 3
        with tempfile.TemporaryDirectory() as tmp:
            days = _tmp_dataset(
                tmp, n_days=n_days, n_win=n_win, seq_len=2, n_features=2,
            )
            ds = LOBDatasetV2(tmp, days=days, cache_size=2)
            _ = ds[0 * n_win]        # day 0
            _ = ds[1 * n_win]        # day 1
            self.assertEqual(set(ds._cache.keys()), {0, 1})
            _ = ds[2 * n_win]        # day 2 — evicts day 0 (oldest)
            self.assertEqual(set(ds._cache.keys()), {1, 2})
            _ = ds[1 * n_win]        # touch day 1, now day 2 is oldest
            _ = ds[3 * n_win]        # day 3 — evicts day 2
            self.assertEqual(set(ds._cache.keys()), {1, 3})


class TestStreamingStats(unittest.TestCase):
    def test_matches_monolithic_reference(self) -> None:
        n_days, n_win, seq_len, n_features = 4, 9, 5, 6
        with tempfile.TemporaryDirectory() as tmp:
            days = _tmp_dataset(
                tmp, n_days=n_days, n_win=n_win, seq_len=seq_len,
                n_features=n_features, seed=123,
            )

            # Reference: load every NPZ eagerly, concat, compute mean/std.
            X_all = np.concatenate(
                [np.load(os.path.join(tmp, f"{d}.npz"))["X"] for d in days],
                axis=0,
            ).astype(np.float32)
            ref_mean = X_all.mean(axis=(0, 1))
            ref_std = X_all.std(axis=(0, 1))

            ds = LOBDatasetV2(tmp, days=days, cache_size=2)
            stream_mean, stream_std = ds.compute_stats()

            np.testing.assert_allclose(stream_mean, ref_mean, rtol=1e-5, atol=1e-5)
            np.testing.assert_allclose(stream_std, ref_std, rtol=1e-5, atol=1e-5)


class TestNormalizeIntegration(unittest.TestCase):
    def test_getitem_returns_normalised_features(self) -> None:
        n_days, n_win, seq_len, n_features = 3, 5, 4, 4
        with tempfile.TemporaryDirectory() as tmp:
            days = _tmp_dataset(
                tmp, n_days=n_days, n_win=n_win, seq_len=seq_len,
                n_features=n_features, seed=7,
            )
            # Pre-compute mean/std with the same streaming pass we bake in.
            stats_ds = LOBDatasetV2(tmp, days=days)
            x_mean, x_std = stats_ds.compute_stats()

            ds = LOBDatasetV2(
                tmp, days=days, normalize=True,
                x_mean=x_mean, x_std=x_std, cache_size=2,
            )

            # Manually compute expected value for window 0 of day 0.
            raw_x = np.load(os.path.join(tmp, f"{days[0]}.npz"))["X"][0].astype(np.float32)
            safe_std = np.where(x_std < 1e-4, 1.0, x_std).astype(np.float32)
            expected = np.clip((raw_x - x_mean) / safe_std, -10.0, 10.0).astype(np.float32)

            sample = ds[0]
            x_feat = sample[0]
            np.testing.assert_allclose(x_feat.numpy(), expected, rtol=1e-5, atol=1e-5)


class TestYNormalise(unittest.TestCase):
    def test_y_norm_transform_applied(self) -> None:
        n_days, n_win, seq_len, n_features = 2, 6, 3, 2
        with tempfile.TemporaryDirectory() as tmp:
            days = _tmp_dataset(
                tmp, n_days=n_days, n_win=n_win, seq_len=seq_len,
                n_features=n_features, seed=0,
            )
            median, sigma, clip = 0.3, 0.5, 5.0
            ds = LOBDatasetV2(
                tmp, days=days,
                y_norm=(median, sigma, clip), cache_size=1,
            )

            # Walk every window and verify per-item transform.
            for idx in range(len(ds)):
                sample = ds[idx]
                # 3-tuple because no X_raw
                _, y_t, m_t = sample
                day_idx = idx // n_win
                local_idx = idx - day_idx * n_win
                npz = np.load(os.path.join(tmp, f"{days[day_idx]}.npz"))
                raw_y = float(npz["y"][local_idx])
                raw_m = float(npz["y_mask"][local_idx])
                exp = 0.0
                if raw_m > 0:
                    exp = float(np.clip((raw_y - median) / sigma, -clip, clip))
                self.assertAlmostEqual(float(y_t), exp, places=5)
                self.assertAlmostEqual(float(m_t), raw_m, places=5)


class TestMultiHorizonLazy(unittest.TestCase):
    HORIZONS = ("y_60", "y_180", "y_300", "y_600")

    def test_stacked_y_and_mask(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            days = _tmp_dataset(
                tmp, n_days=3, n_win=7, seq_len=4, n_features=3, n_levels=4,
                horizons=(60, 180, 300, 600), seed=11,
            )
            ds = LOBDatasetV2(
                tmp, days=days,
                horizons=list(self.HORIZONS), cache_size=2,
            )
            sample = ds[0]
            self.assertEqual(len(sample), 4)
            _, _, y, m = sample
            self.assertEqual(y.shape, (len(self.HORIZONS),))
            self.assertEqual(m.shape, (len(self.HORIZONS),))

    def test_dataloader_batches(self) -> None:
        from torch.utils.data import DataLoader

        with tempfile.TemporaryDirectory() as tmp:
            days = _tmp_dataset(
                tmp, n_days=2, n_win=8, seq_len=4, n_features=3, n_levels=4,
                horizons=(60, 180, 300, 600), seed=17,
            )
            ds = LOBDatasetV2(
                tmp, days=days,
                horizons=list(self.HORIZONS), cache_size=1,
            )
            loader = DataLoader(ds, batch_size=4, shuffle=False)
            batch = next(iter(loader))
            self.assertEqual(len(batch), 4)
            _, _, y, m = batch
            self.assertEqual(y.shape, (4, len(self.HORIZONS)))
            self.assertEqual(m.shape, (4, len(self.HORIZONS)))


class TestComputeYStatsStreaming(unittest.TestCase):
    def test_matches_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            days = _tmp_dataset(
                tmp, n_days=4, n_win=11, seq_len=3, n_features=2, seed=51,
            )
            # Reference: pull all valid y values.
            ys, ms = [], []
            for d in days:
                npz = np.load(os.path.join(tmp, f"{d}.npz"))
                ys.append(npz["y"])
                ms.append(npz["y_mask"])
            y_all = np.concatenate(ys)
            m_all = np.concatenate(ms)
            y_valid = y_all[m_all > 0]
            ref_med = float(np.median(y_valid))
            ref_sig = max(1.4826 * float(np.median(np.abs(y_valid - ref_med))), 1e-9)

            ds = LOBDatasetV2(tmp, days=days, cache_size=1)
            med, sig = ds.compute_y_stats()
            self.assertAlmostEqual(med, ref_med, places=5)
            self.assertAlmostEqual(sig, ref_sig, places=5)


class TestOOMRegression(unittest.TestCase):
    """Create 20 'fat' days, iterate them with cache_size=3, and assert RSS
    stays within the expected bound.  This is a coarse regression test —
    we use ``resource.getrusage`` where available and skip on platforms
    that don't support it (Windows)."""

    def test_cache_bounds_peak_rss(self) -> None:
        try:
            import resource  # type: ignore
        except ImportError:
            self.skipTest("resource module unavailable on this platform")

        # Each day: 1000 windows × 300 × 58 × float32 ≈ 66 MB on disk,
        # compressed NPZ shrinks to ~half. We shrink further for CI
        # speed while keeping the ratio meaningful.
        n_days = 20
        n_win = 800
        seq_len = 60
        n_features = 40
        per_day_mb = n_win * seq_len * n_features * 4 / 1024 ** 2
        with tempfile.TemporaryDirectory() as tmp:
            days = _tmp_dataset(
                tmp, n_days=n_days, n_win=n_win, seq_len=seq_len,
                n_features=n_features, seed=99,
            )

            baseline_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            ds = LOBDatasetV2(tmp, days=days, cache_size=3)

            # Sequential scan: cache holds at most 3 days at a time.
            for idx in range(0, len(ds), max(len(ds) // 200, 1)):
                _ = ds[idx]
                self.assertLessEqual(len(ds._cache), 3)

            peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # On Linux ru_maxrss is in KiB, on macOS in bytes.
            unit_bytes = 1 if sys.platform == "darwin" else 1024
            peak_delta_mb = max(peak_rss - baseline_rss, 0) * unit_bytes / 1024 ** 2

            # 3 days × per_day_mb + decent overhead.  We give generous
            # slack (5× headroom) so the test isn't flaky under Python
            # memory fragmentation.
            bound_mb = 5 * (3 * per_day_mb) + 200
            self.assertLess(
                peak_delta_mb, bound_mb,
                f"RSS grew by {peak_delta_mb:.0f} MB (bound {bound_mb:.0f} MB) "
                f"- lazy cache is leaking."
            )


class TestFeatureNameDriftStillDetected(unittest.TestCase):
    def test_mismatch_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write_day(
                os.path.join(tmp, "d1.npz"), n_win=3, seq_len=2, n_features=2, seed=1,
            )
            # Second day with *different* feature names.
            rng = np.random.default_rng(2)
            np.savez_compressed(
                os.path.join(tmp, "d2.npz"),
                X=rng.standard_normal((3, 2, 2)).astype(np.float32),
                y=rng.standard_normal(3).astype(np.float32),
                y_mask=np.ones(3, dtype=np.float32),
                timestamps=np.arange(3, dtype=np.int64),
                features=np.array(["zzz", "xxx"], dtype=object),
            )
            with self.assertRaises(ValueError) as ctx:
                LOBDatasetV2(tmp, days=["d1", "d2"])
            self.assertIn("Feature-name mismatch", str(ctx.exception))


class TestXRawConsistencyCheck(unittest.TestCase):
    def test_mixed_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Day 1 with X_raw, day 2 without.
            _write_day(
                os.path.join(tmp, "d1.npz"), n_win=3, seq_len=2, n_features=2,
                n_levels=4, seed=1,
            )
            _write_day(
                os.path.join(tmp, "d2.npz"), n_win=3, seq_len=2, n_features=2,
                n_levels=0, seed=2,
            )
            with self.assertRaises(ValueError) as ctx:
                LOBDatasetV2(tmp, days=["d1", "d2"])
            self.assertIn("X_raw", str(ctx.exception))


class TestNpLoadRetry(unittest.TestCase):
    """Retry wrapper — transient OSError should not bubble up if a later
    attempt succeeds."""

    def test_np_load_retry_on_transient_oserror(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "real.npz")
            expected = np.arange(6, dtype=np.float32).reshape(2, 3)
            np.savez_compressed(path, X=expected)

            real_np_load = np.load
            call_count = {"n": 0}

            def flaky_load(p, **kwargs):
                call_count["n"] += 1
                if call_count["n"] < 3:
                    raise OSError("transient stall (mocked)")
                return real_np_load(p, **kwargs)

            with mock.patch.object(ds_module.np, "load", side_effect=flaky_load):
                # backoff_sec=0 so the test is fast; retry logic still exercised.
                npz = _np_load_with_retry(
                    path, allow_pickle=True,
                    max_retries=5, backoff_sec=0.0,
                )
                try:
                    np.testing.assert_array_equal(npz["X"], expected)
                finally:
                    npz.close()

            self.assertEqual(call_count["n"], 3,
                             "expected 2 failed attempts followed by success")

    def test_np_load_retry_reraises_on_persistent_error(self) -> None:
        """After ``max_retries`` failures the last exception propagates."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "missing.npz")  # never created

            call_count = {"n": 0}

            def always_fail(p, **kwargs):
                call_count["n"] += 1
                raise OSError("disk offline (mocked)")

            with mock.patch.object(ds_module.np, "load", side_effect=always_fail):
                with self.assertRaises(OSError):
                    _np_load_with_retry(
                        path, allow_pickle=True,
                        max_retries=3, backoff_sec=0.0,
                    )
            self.assertEqual(call_count["n"], 3)


class TestGetAllTimestamps(unittest.TestCase):
    """``get_all_timestamps`` must stream across every day and return a
    concatenated int64 array in day order matching ``__len__``."""

    def test_returns_concatenated_in_day_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Three synthetic days with deterministic, distinguishable
            # timestamp ranges so we can verify ordering, not just length.
            # Day 0: 1000..1004, Day 1: 2000..2006, Day 2: 3000..3002
            day_specs = [
                ("day_000", np.array([1000, 1001, 1002, 1003, 1004], dtype=np.int64)),
                ("day_001", np.array([2000, 2001, 2002, 2003, 2004, 2005, 2006],
                                     dtype=np.int64)),
                ("day_002", np.array([3000, 3001, 3002], dtype=np.int64)),
            ]
            rng = np.random.default_rng(0)
            for day, ts in day_specs:
                n_win = ts.shape[0]
                np.savez_compressed(
                    os.path.join(tmp, f"{day}.npz"),
                    X=rng.standard_normal((n_win, 3, 2)).astype(np.float32),
                    y=rng.standard_normal(n_win).astype(np.float32),
                    y_mask=np.ones(n_win, dtype=np.float32),
                    timestamps=ts,
                    features=np.array(["f0", "f1"], dtype=object),
                )

            ds = LOBDatasetV2(tmp, days=[d for d, _ in day_specs], cache_size=2)
            expected = np.concatenate([ts for _, ts in day_specs], axis=0)
            actual = ds.get_all_timestamps()

            self.assertEqual(actual.dtype, np.int64)
            self.assertEqual(actual.shape, (len(ds),))
            np.testing.assert_array_equal(actual, expected)


def test_dataset_returns_regime_prior_when_present():
    """If NPZ has regime_prior field, dataset returns it in the tuple."""
    import tempfile, os, sys, numpy as np
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.training.dataset import LOBDatasetV2

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "2024-01-01.npz")
        np.savez_compressed(
            path,
            X=np.random.randn(10, 600, 64).astype(np.float32),
            X_raw=np.random.randn(10, 600, 20, 4).astype(np.float32),
            y=np.random.randn(10).astype(np.float32),
            y_mask=np.ones(10, dtype=np.uint8),
            regime_prior=np.random.randn(10, 6).astype(np.float32),
            timestamps=np.arange(10, dtype=np.int64),
            features=np.array([f"f{i}" for i in range(64)], dtype=object),
        )
        ds = LOBDatasetV2(tmp, ["2024-01-01"], normalize=False)
        assert ds.has_regime_prior is True, "expected has_regime_prior=True"
        item = ds[3]
        # With x_raw present, item is (x_feat, x_raw, regime_prior, y, mask)
        assert len(item) == 5, f"expected 5-tuple, got {len(item)}"
        x_feat, x_raw, regime_prior, y, mask = item
        assert x_feat.shape == (600, 64)
        assert x_raw.shape == (600, 20, 4)
        assert regime_prior.shape == (6,)
    print("PASS: test_dataset_returns_regime_prior_when_present")


def test_dataset_no_regime_prior_back_compat():
    """NPZ without regime_prior: dataset returns old 4-tuple shape."""
    import tempfile, os, sys, numpy as np
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.training.dataset import LOBDatasetV2

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "2024-01-01.npz")
        np.savez_compressed(
            path,
            X=np.random.randn(10, 300, 58).astype(np.float32),
            X_raw=np.random.randn(10, 300, 20, 4).astype(np.float32),
            y=np.random.randn(10).astype(np.float32),
            y_mask=np.ones(10, dtype=np.uint8),
            timestamps=np.arange(10, dtype=np.int64),
            features=np.array([f"f{i}" for i in range(58)], dtype=object),
        )
        ds = LOBDatasetV2(tmp, ["2024-01-01"], normalize=False)
        assert ds.has_regime_prior is False, "expected has_regime_prior=False"
        item = ds[3]
        assert len(item) == 4, f"expected 4-tuple (back-compat), got {len(item)}"
    print("PASS: test_dataset_no_regime_prior_back_compat")


def test_dataset_regime_prior_consistency_check():
    """Mixing days with and without regime_prior must raise."""
    import tempfile, os, sys, numpy as np
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.training.dataset import LOBDatasetV2

    with tempfile.TemporaryDirectory() as tmp:
        # Day 1: with regime_prior
        np.savez_compressed(
            os.path.join(tmp, "2024-01-01.npz"),
            X=np.random.randn(8, 100, 64).astype(np.float32),
            X_raw=np.random.randn(8, 100, 20, 4).astype(np.float32),
            y=np.random.randn(8).astype(np.float32),
            y_mask=np.ones(8, dtype=np.uint8),
            regime_prior=np.random.randn(8, 6).astype(np.float32),
            timestamps=np.arange(8, dtype=np.int64),
            features=np.array([f"f{i}" for i in range(64)], dtype=object),
        )
        # Day 2: without regime_prior
        np.savez_compressed(
            os.path.join(tmp, "2024-01-02.npz"),
            X=np.random.randn(8, 100, 64).astype(np.float32),
            X_raw=np.random.randn(8, 100, 20, 4).astype(np.float32),
            y=np.random.randn(8).astype(np.float32),
            y_mask=np.ones(8, dtype=np.uint8),
            timestamps=np.arange(8, dtype=np.int64),
            features=np.array([f"f{i}" for i in range(64)], dtype=object),
        )
        try:
            ds = LOBDatasetV2(tmp, ["2024-01-01", "2024-01-02"], normalize=False)
        except ValueError as e:
            assert "regime_prior" in str(e).lower()
            print("PASS: test_dataset_regime_prior_consistency_check")
            return
        raise AssertionError(
            "Expected ValueError when regime_prior presence differs across days"
        )


if __name__ == "__main__":
    unittest.main(exit=False)
    test_dataset_returns_regime_prior_when_present()
    test_dataset_no_regime_prior_back_compat()
    test_dataset_regime_prior_consistency_check()

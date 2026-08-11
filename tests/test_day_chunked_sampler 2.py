import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import tempfile
import unittest

from src.training.dataset import LOBDatasetV2, DayChunkedSampler


def _write_synthetic_npz(path, n_windows, n_features, day_marker):
    """Create a minimal valid NPZ with n_windows windows."""
    np.savez_compressed(
        path,
        X=np.full((n_windows, 10, n_features), day_marker, dtype=np.float32),
        y=np.full(n_windows, day_marker, dtype=np.float32),
        y_mask=np.ones(n_windows, dtype=np.uint8),
        timestamps=np.arange(n_windows, dtype=np.int64),
        features=np.array([f"f{i}" for i in range(n_features)], dtype=object),
    )


class TestDayChunkedSampler(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.days = []
        for i, n in enumerate([3, 5, 4, 2]):  # 4 days with varying windows
            day = f"2024-01-{i+1:02d}"
            _write_synthetic_npz(
                os.path.join(self.tmp, f"{day}.npz"),
                n_windows=n, n_features=3, day_marker=float(i),
            )
            self.days.append(day)
        self.ds = LOBDatasetV2(self.tmp, self.days, cache_size=2)

    def test_yields_all_samples(self):
        sampler = DayChunkedSampler(self.ds, shuffle_days=False, shuffle_within_day=False)
        indices = list(sampler)
        self.assertEqual(len(indices), 3+5+4+2)
        # No duplicates
        self.assertEqual(len(set(indices)), len(indices))
        # Covers [0, total)
        self.assertEqual(sorted(indices), list(range(14)))
        print("PASS: test_yields_all_samples")

    def test_day_chunking_preserves_contiguous_runs(self):
        """Without shuffling, sample indices from each day are contiguous."""
        sampler = DayChunkedSampler(self.ds, shuffle_days=False, shuffle_within_day=False)
        indices = list(sampler)
        # day 0: 0,1,2  day 1: 3,4,5,6,7  day 2: 8,9,10,11  day 3: 12,13
        self.assertEqual(indices, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
        print("PASS: test_day_chunking_preserves_contiguous_runs")

    def test_shuffle_days_still_covers_all(self):
        sampler = DayChunkedSampler(self.ds, shuffle_days=True, shuffle_within_day=True, seed=42)
        sampler.set_epoch(0)
        indices = list(sampler)
        # Still covers all 14 samples exactly once
        self.assertEqual(len(set(indices)), 14)
        self.assertEqual(sorted(indices), list(range(14)))
        print("PASS: test_shuffle_days_still_covers_all")

    def test_chunk_size_one_is_pure_day_chunked(self):
        """chunk_size=1: each day processed independently, contiguous runs."""
        sampler = DayChunkedSampler(
            self.ds, chunk_size=1,
            shuffle_days=False, shuffle_within_day=False,
        )
        indices = list(sampler)
        # Day 0 (3 samples) then day 1 (5) then day 2 (4) then day 3 (2)
        self.assertEqual(indices, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
        print("PASS: test_chunk_size_one_is_pure_day_chunked")

    def test_chunk_size_large_is_global_shuffle(self):
        """chunk_size >= n_days: one chunk, samples globally shuffled."""
        sampler = DayChunkedSampler(
            self.ds, chunk_size=100,  # >= 4 days
            shuffle_days=False, shuffle_within_day=True, seed=42,
        )
        indices = list(sampler)
        # All 14 samples, but in random order (NOT contiguous-by-day)
        self.assertEqual(sorted(indices), list(range(14)))
        # Samples from different days will be interleaved
        day_ids = [self.ds._locate(idx)[0] for idx in indices]
        # Not monotonically non-decreasing → at least one day-jump happens
        day_jumps = sum(1 for i in range(1, len(day_ids)) if day_ids[i] < day_ids[i-1])
        self.assertGreater(day_jumps, 0)
        print("PASS: test_chunk_size_large_is_global_shuffle")

    def test_set_epoch_changes_order(self):
        sampler = DayChunkedSampler(self.ds, shuffle_days=True, seed=42)
        sampler.set_epoch(0)
        order0 = list(sampler)
        sampler.set_epoch(1)
        order1 = list(sampler)
        # Should differ (otherwise shuffle_days has no per-epoch effect)
        self.assertNotEqual(order0, order1)
        print("PASS: test_set_epoch_changes_order")

    def test_requires_lobdatasetv2_attrs(self):
        """Non-LOBDatasetV2 dataset raises clear error."""
        class FakeDS:
            pass
        with self.assertRaises(TypeError):
            DayChunkedSampler(FakeDS())
        print("PASS: test_requires_lobdatasetv2_attrs")


if __name__ == "__main__":
    unittest.main()

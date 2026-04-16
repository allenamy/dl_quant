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
        self.assertEqual(len(set(indices)), 14)
        # But samples from each day still come in consecutive chunks:
        # find the run lengths and verify they match day sizes [3, 5, 4, 2] in some order
        day_sizes = []
        run_start = 0
        for i in range(1, len(indices) + 1):
            if i == len(indices) or self.ds._locate(indices[i])[0] != self.ds._locate(indices[i-1])[0]:
                day_sizes.append(i - run_start)
                run_start = i
        self.assertEqual(sorted(day_sizes), [2, 3, 4, 5])
        print("PASS: test_shuffle_days_still_covers_all")

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

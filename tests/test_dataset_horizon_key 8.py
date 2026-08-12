"""Tests for the multi-horizon ``LOBDatasetV2`` API additions.

We cover:

* Default ``horizon_key="y"`` keeps legacy behaviour (3-tuple / 4-tuple
  returns, scalar y/mask).
* Explicit ``horizon_key="y_60"`` / ``"y_180"`` loads the corresponding
  per-horizon array and auto-derives the matching mask key.
* Missing horizon key raises a helpful ``ValueError`` (pipeline-version
  mismatch).
* Multi-horizon mode via ``horizons=["y_60","y_180","y_300","y_600"]``
  stacks per-horizon y / mask and returns a 1-D tensor of length
  ``n_horizons`` per item.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

import numpy as np
import torch

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.training.dataset import LOBDatasetV2, _derive_mask_key


def _make_multihorizon_npz(
    tmpdir: str,
    day: str,
    n_win: int = 20,
    seq_len: int = 8,
    n_features: int = 5,
    n_levels: int = 6,
    horizons: tuple[int, ...] = (60, 180, 300, 600),
    seed: int = 0,
) -> str:
    """Build a fake multi-horizon NPZ file matching pipeline output shape."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n_win, seq_len, n_features)).astype(np.float32)
    X_raw = rng.standard_normal((n_win, seq_len, n_levels, 4)).astype(np.float32)
    timestamps = np.arange(n_win, dtype=np.int64)
    path = os.path.join(tmpdir, f"{day}.npz")

    save: dict[str, np.ndarray] = {
        "X": X,
        "X_raw": X_raw,
        "timestamps": timestamps,
        "features": np.array([f"f{i}" for i in range(n_features)], dtype=object),
        "horizons_sec": np.array(list(horizons), dtype=np.int64),
    }
    for h in horizons:
        y_h = rng.standard_normal(n_win).astype(np.float32)
        m_h = (rng.random(n_win) > 0.1).astype(np.uint8)
        save[f"y_{h}"] = y_h
        save[f"y_mask_{h}"] = m_h
    # Back-compat alias -> smallest horizon.
    smallest = min(horizons)
    save["y"] = save[f"y_{smallest}"]
    save["y_mask"] = save[f"y_mask_{smallest}"]

    np.savez_compressed(path, **save)
    return path


# ---------------------------------------------------------------------------
# _derive_mask_key
# ---------------------------------------------------------------------------


class TestDeriveMaskKey(unittest.TestCase):
    def test_alias(self) -> None:
        self.assertEqual(_derive_mask_key("y"), "y_mask")

    def test_per_horizon(self) -> None:
        self.assertEqual(_derive_mask_key("y_60"), "y_mask_60")
        self.assertEqual(_derive_mask_key("y_180"), "y_mask_180")
        self.assertEqual(_derive_mask_key("y_300"), "y_mask_300")
        self.assertEqual(_derive_mask_key("y_600"), "y_mask_600")

    def test_invalid_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            _derive_mask_key("yy_60")
        with self.assertRaises(ValueError):
            _derive_mask_key("mask")


# ---------------------------------------------------------------------------
# Single-horizon mode (back-compat)
# ---------------------------------------------------------------------------


class TestSingleHorizonBackCompat(unittest.TestCase):
    def test_default_loads_y_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_multihorizon_npz(tmp, "day1")
            ds = LOBDatasetV2(tmp, days=["day1"])
            # horizons property reflects single-horizon mode.
            self.assertIsNone(ds.horizons)
            # has_raw auto-detected from NPZ.
            self.assertTrue(ds.has_raw)
            # __getitem__ returns 4-tuple with scalar y/mask.
            sample = ds[0]
            self.assertEqual(len(sample), 4)
            x_feat, x_raw, y, mask = sample
            self.assertEqual(y.ndim, 0)
            self.assertEqual(mask.ndim, 0)

    def test_horizon_key_y_60(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_multihorizon_npz(tmp, "day1", seed=7)
            ds60 = LOBDatasetV2(tmp, days=["day1"], horizon_key="y_60")
            # Same Y values as the back-compat alias (smallest horizon = 60).
            ds_default = LOBDatasetV2(tmp, days=["day1"])
            np.testing.assert_array_equal(ds60.y, ds_default.y)
            np.testing.assert_array_equal(ds60.mask, ds_default.mask)

    def test_horizon_key_y_300_differs_from_y_60(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_multihorizon_npz(tmp, "day1", seed=7)
            ds60 = LOBDatasetV2(tmp, days=["day1"], horizon_key="y_60")
            ds300 = LOBDatasetV2(tmp, days=["day1"], horizon_key="y_300")
            self.assertFalse(np.allclose(ds60.y, ds300.y),
                             "y_60 and y_300 should have different values")

    def test_missing_horizon_key_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_multihorizon_npz(tmp, "day1", horizons=(60, 180))
            with self.assertRaises(ValueError) as ctx:
                LOBDatasetV2(tmp, days=["day1"], horizon_key="y_600")
            # Helpful message points at the rebuild path.
            self.assertIn("y_600", str(ctx.exception))
            self.assertIn("horizons_sec", str(ctx.exception))

    def test_explicit_mask_key_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_multihorizon_npz(tmp, "day1", seed=3)
            # Use horizon_key="y_60" but supply mask_key explicitly.
            ds = LOBDatasetV2(
                tmp, days=["day1"],
                horizon_key="y_60", mask_key="y_mask_60",
            )
            # Sanity: y_60 matches reload.
            with np.load(os.path.join(tmp, "day1.npz")) as npz:
                exp_y = npz["y_60"].astype(np.float32)
                exp_mask = npz["y_mask_60"].astype(np.float32)
                exp_y = np.where(exp_mask == 0, 0.0, exp_y)
            np.testing.assert_array_equal(ds.y, exp_y)


# ---------------------------------------------------------------------------
# Multi-horizon mode
# ---------------------------------------------------------------------------


class TestMultiHorizonMode(unittest.TestCase):
    HORIZONS = ("y_60", "y_180", "y_300", "y_600")

    def test_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_multihorizon_npz(tmp, "day1", n_win=30, seed=5)
            ds = LOBDatasetV2(
                tmp, days=["day1"], horizons=list(self.HORIZONS),
            )
            # horizons property reflects multi-horizon mode.
            self.assertEqual(ds.horizons, list(self.HORIZONS))
            # y and mask are (N, n_horizons).
            self.assertEqual(ds.y.shape, (30, len(self.HORIZONS)))
            self.assertEqual(ds.mask.shape, (30, len(self.HORIZONS)))

    def test_getitem_returns_horizon_vector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_multihorizon_npz(tmp, "day1", n_win=10, seed=1)
            ds = LOBDatasetV2(
                tmp, days=["day1"], horizons=list(self.HORIZONS),
            )
            sample = ds[0]
            # 4-tuple because X_raw is present.
            self.assertEqual(len(sample), 4)
            x_feat, x_raw, y, mask = sample
            self.assertIsInstance(y, torch.Tensor)
            self.assertEqual(y.shape, (len(self.HORIZONS),))
            self.assertEqual(mask.shape, (len(self.HORIZONS),))

    def test_dataloader_batches_correctly(self) -> None:
        """Verify that default torch collation stacks samples into
        (B, n_horizons) tensors -- the shape the trainer expects."""
        from torch.utils.data import DataLoader

        with tempfile.TemporaryDirectory() as tmp:
            _make_multihorizon_npz(tmp, "day1", n_win=16, seed=2)
            ds = LOBDatasetV2(
                tmp, days=["day1"], horizons=list(self.HORIZONS),
            )
            loader = DataLoader(ds, batch_size=4, shuffle=False)
            batch = next(iter(loader))
            # 4-tuple (x_feat, x_raw, y, mask).
            self.assertEqual(len(batch), 4)
            _, _, y, mask = batch
            self.assertEqual(y.shape, (4, len(self.HORIZONS)))
            self.assertEqual(mask.shape, (4, len(self.HORIZONS)))

    def test_per_horizon_values_match_npz(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_multihorizon_npz(tmp, "day1", n_win=15, seed=11)
            ds = LOBDatasetV2(
                tmp, days=["day1"], horizons=list(self.HORIZONS),
            )
            with np.load(os.path.join(tmp, "day1.npz")) as npz:
                for i, key in enumerate(self.HORIZONS):
                    exp_y = npz[key].astype(np.float32)
                    exp_mask = npz[f"y_mask{key[1:]}"].astype(np.float32)
                    exp_y = np.where(exp_mask == 0, 0.0, exp_y)
                    np.testing.assert_array_equal(ds.y[:, i], exp_y)
                    np.testing.assert_array_equal(ds.mask[:, i], exp_mask)

    def test_empty_horizons_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _make_multihorizon_npz(tmp, "day1")
            with self.assertRaises(ValueError):
                LOBDatasetV2(tmp, days=["day1"], horizons=[])


class TestBackCompatOldNPZ(unittest.TestCase):
    """Old NPZ files (no y_{H} fields) still load when horizon_key='y'."""

    def test_old_npz_loads_with_default(self) -> None:
        rng = np.random.default_rng(0)
        n_win, seq_len, n_features = 10, 4, 3
        with tempfile.TemporaryDirectory() as tmp:
            X = rng.standard_normal((n_win, seq_len, n_features)).astype(np.float32)
            y = rng.standard_normal(n_win).astype(np.float32)
            y_mask = np.ones(n_win, dtype=np.float32)
            np.savez(
                os.path.join(tmp, "day1.npz"),
                X=X, y=y, y_mask=y_mask,
            )
            ds = LOBDatasetV2(tmp, days=["day1"])
            # No X_raw -> 3-tuple.
            sample = ds[0]
            self.assertEqual(len(sample), 3)
            self.assertFalse(ds.has_raw)
            self.assertIsNone(ds.horizons)


if __name__ == "__main__":
    unittest.main()

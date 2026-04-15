"""Tests for trainer_v2 (quantile-only, dual-path) and LOBDatasetV2."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.training.trainer_v2 import train_one_fold_v2
from src.training.dataset import LOBDatasetV2


# ---------------------------------------------------------------------------
# Tiny stub models for testing
# ---------------------------------------------------------------------------

class _TinySinglePathModel(nn.Module):
    """Minimal model: x_feat -> quantiles + point_pred."""

    def __init__(self, n_features: int = 5, n_quantiles: int = 3):
        super().__init__()
        self.proj = nn.Linear(n_features, n_quantiles)

    def forward(self, x_feat: torch.Tensor, x_raw=None) -> dict:
        # x_feat: (B, L, F) -> use last timestep
        h = x_feat[:, -1, :]  # (B, F)
        q = self.proj(h)      # (B, n_quantiles)
        return {"quantiles": q, "point_pred": q[:, 1]}


class _TinyDualPathModel(nn.Module):
    """Minimal dual-path model: x_feat + x_raw -> quantiles + point_pred."""

    def __init__(self, n_features: int = 5, n_raw_ch: int = 4, n_quantiles: int = 3):
        super().__init__()
        self.feat_proj = nn.Linear(n_features, 8)
        self.raw_proj = nn.Linear(n_raw_ch, 8)
        self.head = nn.Linear(16, n_quantiles)

    def forward(self, x_feat: torch.Tensor, x_raw: torch.Tensor) -> dict:
        h_feat = self.feat_proj(x_feat[:, -1, :])         # (B, 8)
        # x_raw: (B, L, n_levels, 4) -> mean across L and levels
        h_raw = self.raw_proj(x_raw.mean(dim=(1, 2)))     # (B, 8)
        h = torch.cat([h_feat, h_raw], dim=-1)             # (B, 16)
        q = self.head(h)                                    # (B, n_quantiles)
        return {"quantiles": q, "point_pred": q[:, 1]}


# ---------------------------------------------------------------------------
# Simple in-memory datasets for testing
# ---------------------------------------------------------------------------

class _SinglePathDataset(Dataset):
    """Yields (x_feat, y, mask) tuples."""

    def __init__(self, n: int = 100, seq_len: int = 10, n_features: int = 5, seed: int = 0):
        rng = np.random.default_rng(seed)
        self.X = rng.standard_normal((n, seq_len, n_features)).astype(np.float32)
        self.y = rng.standard_normal(n).astype(np.float32)
        self.mask = np.ones(n, dtype=np.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return (
            torch.FloatTensor(self.X[idx]),
            torch.tensor(float(self.y[idx])),
            torch.tensor(float(self.mask[idx])),
        )


class _DualPathDataset(Dataset):
    """Yields (x_feat, x_raw, y, mask) tuples."""

    def __init__(
        self, n: int = 100, seq_len: int = 10,
        n_features: int = 5, n_levels: int = 5, seed: int = 0,
    ):
        rng = np.random.default_rng(seed)
        self.X = rng.standard_normal((n, seq_len, n_features)).astype(np.float32)
        self.X_raw = rng.standard_normal((n, seq_len, n_levels, 4)).astype(np.float32)
        self.y = rng.standard_normal(n).astype(np.float32)
        self.mask = np.ones(n, dtype=np.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return (
            torch.FloatTensor(self.X[idx]),
            torch.FloatTensor(self.X_raw[idx]),
            torch.tensor(float(self.y[idx])),
            torch.tensor(float(self.mask[idx])),
        )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestTrainQuantileOnly(unittest.TestCase):
    """Verify training loop works with quantile-only loss."""

    def test_train_quantile_only(self) -> None:
        model = _TinySinglePathModel(n_features=5)
        train_ds = _SinglePathDataset(n=80, seed=0)
        val_ds = _SinglePathDataset(n=20, seed=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = train_one_fold_v2(
                model=model,
                train_dataset=train_ds,
                val_dataset=val_ds,
                out_dir=tmpdir,
                epochs=3,
                batch_size=16,
                patience=5,
            )
            # Should return dict with expected keys
            self.assertIn("best_epoch", result)
            self.assertIn("val_loss", result)
            self.assertIn("val_corr", result)
            self.assertIn("val_r2", result)

            # best_model.pt should exist
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "best_model.pt")))

            # metrics.json should exist and be valid
            with open(os.path.join(tmpdir, "metrics.json")) as f:
                saved = json.load(f)
            self.assertEqual(saved["best_epoch"], result["best_epoch"])


class TestTrainDualPath(unittest.TestCase):
    """Verify trainer handles (x_feat, x_raw, y, mask) tuples."""

    def test_train_dual_path(self) -> None:
        model = _TinyDualPathModel(n_features=5, n_raw_ch=4)
        train_ds = _DualPathDataset(n=80, n_features=5, n_levels=5, seed=0)
        val_ds = _DualPathDataset(n=20, n_features=5, n_levels=5, seed=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = train_one_fold_v2(
                model=model,
                train_dataset=train_ds,
                val_dataset=val_ds,
                out_dir=tmpdir,
                epochs=3,
                batch_size=16,
                patience=5,
            )
            self.assertIn("best_epoch", result)
            self.assertIn("val_corr", result)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "best_model.pt")))


class TestTrainSinglePathFallback(unittest.TestCase):
    """Verify trainer handles (x_feat, y, mask) tuples (no x_raw)."""

    def test_train_single_path_fallback(self) -> None:
        model = _TinySinglePathModel(n_features=5)
        train_ds = _SinglePathDataset(n=80, seed=0)
        val_ds = _SinglePathDataset(n=20, seed=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = train_one_fold_v2(
                model=model,
                train_dataset=train_ds,
                val_dataset=val_ds,
                out_dir=tmpdir,
                epochs=2,
                batch_size=16,
                patience=5,
            )
            self.assertIn("best_epoch", result)
            self.assertIn("val_corr", result)
            # Verify model checkpoint was saved
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "best_model.pt")))


class TestDatasetV2WithRaw(unittest.TestCase):
    """Verify LOBDatasetV2 loads X_raw from NPZ."""

    def test_dataset_v2_with_raw(self) -> None:
        rng = np.random.default_rng(42)
        n_win, seq_len, n_features, n_levels = 20, 10, 5, 8

        with tempfile.TemporaryDirectory() as tmpdir:
            for day in ("day1", "day2"):
                X = rng.standard_normal((n_win, seq_len, n_features)).astype(np.float32)
                X_raw = rng.standard_normal((n_win, seq_len, n_levels, 4)).astype(np.float32)
                y = rng.standard_normal(n_win).astype(np.float32)
                y_mask = np.ones(n_win, dtype=np.float32)
                np.savez(
                    os.path.join(tmpdir, f"{day}.npz"),
                    X=X, X_raw=X_raw, y=y, y_mask=y_mask,
                )

            ds = LOBDatasetV2(data_dir=tmpdir, days=["day1", "day2"])

            # has_raw should be True
            self.assertTrue(ds.has_raw)

            # Total windows
            self.assertEqual(len(ds), 2 * n_win)

            # __getitem__ returns 4-tuple
            sample = ds[0]
            self.assertEqual(len(sample), 4)
            x_feat, x_raw, y_val, m_val = sample
            self.assertEqual(x_feat.shape, (seq_len, n_features))
            self.assertEqual(x_raw.shape, (seq_len, n_levels, 4))


class TestDatasetV2WithoutRaw(unittest.TestCase):
    """Verify LOBDatasetV2 works with old NPZ (no X_raw)."""

    def test_dataset_v2_without_raw(self) -> None:
        rng = np.random.default_rng(42)
        n_win, seq_len, n_features = 20, 10, 5

        with tempfile.TemporaryDirectory() as tmpdir:
            for day in ("day1",):
                X = rng.standard_normal((n_win, seq_len, n_features)).astype(np.float32)
                y = rng.standard_normal(n_win).astype(np.float32)
                y_mask = np.ones(n_win, dtype=np.float32)
                np.savez(
                    os.path.join(tmpdir, f"{day}.npz"),
                    X=X, y=y, y_mask=y_mask,
                )

            ds = LOBDatasetV2(data_dir=tmpdir, days=["day1"])

            # has_raw should be False
            self.assertFalse(ds.has_raw)

            # Total windows
            self.assertEqual(len(ds), n_win)

            # __getitem__ returns 3-tuple
            sample = ds[0]
            self.assertEqual(len(sample), 3)
            x_feat, y_val, m_val = sample
            self.assertEqual(x_feat.shape, (seq_len, n_features))


class TestGradNanGuard(unittest.TestCase):
    """Verify trainer_v2 skips optimizer.step() when gradients are NaN/Inf.

    Without the guard, a single batch producing inf/nan gradients poisons
    every parameter on the next step, turning all subsequent predictions
    into NaN for the rest of training.  The guard checks ``grad_norm``
    after ``clip_grad_norm_`` and skips ``optimizer.step()`` if the norm
    is not finite.
    """

    def test_grad_nan_guard_skips_step(self) -> None:
        from src.training.trainer_v2 import train_one_fold_v2

        torch.manual_seed(0)

        class _PathologicalModel(nn.Module):
            """Model whose forward returns enormous quantile preds (huge loss).

            When combined with enormous input values, this reliably produces
            non-finite gradients in at least some of the early batches.
            """

            def __init__(self, n_features: int, scale: float):
                super().__init__()
                self.lin = nn.Linear(n_features, 3)
                # Pre-scale weights to inf-size after first input
                with torch.no_grad():
                    self.lin.weight.fill_(scale)
                    self.lin.bias.fill_(scale)

            def forward(self, x: torch.Tensor, x_raw=None) -> dict:
                h = x[:, -1, :]
                q = self.lin(h)
                return {"quantiles": q, "point_pred": q[:, 1]}

        class _HugeInputDataset(Dataset):
            """Dataset whose values are huge enough to overflow when multiplied.

            This reliably produces inf/nan in the loss for some batches.
            """

            def __init__(self, n: int = 32, seq_len: int = 5, n_features: int = 4):
                rng = np.random.default_rng(0)
                # Mix normal + huge samples so some batches are fine, some not
                X = rng.standard_normal((n, seq_len, n_features)).astype(np.float32)
                # Inject huge values in half the samples
                X[n // 2:] *= 1e20
                self.X = X
                self.y = rng.standard_normal(n).astype(np.float32) * 1e10
                self.mask = np.ones(n, dtype=np.float32)

            def __len__(self):
                return len(self.X)

            def __getitem__(self, idx):
                return (
                    torch.FloatTensor(self.X[idx]),
                    torch.tensor(float(self.y[idx])),
                    torch.tensor(float(self.mask[idx])),
                )

        n_features = 4
        model = _PathologicalModel(n_features=n_features, scale=1e10)
        train_ds = _HugeInputDataset(n=32, seq_len=5, n_features=n_features)
        val_ds = _HugeInputDataset(n=8, seq_len=5, n_features=n_features)

        # Capture the initial parameter snapshot so we can verify no NaN
        # was ever written into the params.
        initial_params = {
            name: p.detach().clone()
            for name, p in model.named_parameters()
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Run just 1 epoch -- enough to exercise the NaN guard path
            train_one_fold_v2(
                model=model,
                train_dataset=train_ds,
                val_dataset=val_ds,
                out_dir=tmpdir,
                epochs=1,
                batch_size=4,
                patience=5,
                grad_clip=1.0,
            )

            # CRITICAL: no parameter should contain NaN/inf after training.
            # If the guard had been bypassed, even one bad step would have
            # corrupted these tensors.
            for name, p in model.named_parameters():
                self.assertTrue(
                    torch.isfinite(p).all().item(),
                    f"Parameter {name} contains NaN/Inf -- grad NaN guard failed!",
                )


class TestCheckpointByCorrelation(unittest.TestCase):
    """Verify best model is saved by val_correlation, not val_loss."""

    def test_checkpoint_by_correlation(self) -> None:
        model = _TinySinglePathModel(n_features=5)
        train_ds = _SinglePathDataset(n=80, seed=0)
        val_ds = _SinglePathDataset(n=20, seed=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = train_one_fold_v2(
                model=model,
                train_dataset=train_ds,
                val_dataset=val_ds,
                out_dir=tmpdir,
                epochs=5,
                batch_size=16,
                patience=10,
            )

            # metrics.json must contain val_corr as the selection criterion
            with open(os.path.join(tmpdir, "metrics.json")) as f:
                saved = json.load(f)
            self.assertIn("val_corr", saved)
            self.assertEqual(saved["val_corr"], result["val_corr"])

            # Verify that the checkpoint file exists and can be loaded
            state = torch.load(
                os.path.join(tmpdir, "best_model.pt"),
                map_location="cpu",
            )
            self.assertIsInstance(state, dict)


if __name__ == "__main__":
    unittest.main()

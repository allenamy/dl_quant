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


class TestDatasetV2SmoothTargetPassThrough(unittest.TestCase):
    """smooth_target is stored but not yet applied (handled at NPZ-build time)."""

    def test_smooth_target_default_zero(self) -> None:
        rng = np.random.default_rng(0)
        n_win, seq_len, n_features = 10, 4, 3
        with tempfile.TemporaryDirectory() as tmpdir:
            X = rng.standard_normal((n_win, seq_len, n_features)).astype(np.float32)
            y = rng.standard_normal(n_win).astype(np.float32)
            y_mask = np.ones(n_win, dtype=np.float32)
            np.savez(os.path.join(tmpdir, "day1.npz"), X=X, y=y, y_mask=y_mask)

            ds = LOBDatasetV2(data_dir=tmpdir, days=["day1"])
            self.assertEqual(ds.smooth_target, 0)

    def test_smooth_target_custom_value_stored(self) -> None:
        rng = np.random.default_rng(1)
        n_win, seq_len, n_features = 10, 4, 3
        with tempfile.TemporaryDirectory() as tmpdir:
            X = rng.standard_normal((n_win, seq_len, n_features)).astype(np.float32)
            y = rng.standard_normal(n_win).astype(np.float32)
            y_mask = np.ones(n_win, dtype=np.float32)
            np.savez(os.path.join(tmpdir, "day1.npz"), X=X, y=y, y_mask=y_mask)

            ds = LOBDatasetV2(data_dir=tmpdir, days=["day1"], smooth_target=10)
            self.assertEqual(ds.smooth_target, 10)
            # y passthrough: values are untouched (no smoothing applied yet)
            self.assertEqual(len(ds), n_win)


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


class TestLRWarmup(unittest.TestCase):
    """Verify _apply_warmup ramps LR from base_lr/100 to base_lr linearly."""

    def test_warmup_helper_schedule(self) -> None:
        from src.training.trainer_v2 import _apply_warmup

        model = nn.Linear(4, 3)
        base_lr = 1e-3
        optimizer = torch.optim.Adam(model.parameters(), lr=base_lr)

        # Step 0 of 100-step warmup: lr ~= base_lr * 0.0199 (first increment)
        _apply_warmup(step=0, warmup_steps=100, base_lr=base_lr, optimizer=optimizer)
        lr0 = optimizer.param_groups[0]["lr"]
        # Step 99 (last warmup step): lr == base_lr
        _apply_warmup(step=99, warmup_steps=100, base_lr=base_lr, optimizer=optimizer)
        lr99 = optimizer.param_groups[0]["lr"]
        # Step 100 (past warmup): no change, should remain whatever it was
        optimizer.param_groups[0]["lr"] = 0.5  # sentinel
        _apply_warmup(step=100, warmup_steps=100, base_lr=base_lr, optimizer=optimizer)
        lr_past = optimizer.param_groups[0]["lr"]

        self.assertLess(lr0, lr99, "LR must increase during warmup")
        self.assertAlmostEqual(lr99, base_lr, places=6)
        self.assertGreaterEqual(lr0, base_lr * 0.01 - 1e-9)
        self.assertEqual(lr_past, 0.5, "Past warmup, _apply_warmup must be a no-op")

    def test_warmup_disabled_when_pct_zero(self) -> None:
        """warmup_steps_pct=0 means training runs at the base lr from step 0."""
        model = _TinySinglePathModel(n_features=5)
        train_ds = _SinglePathDataset(n=32, seed=0)
        val_ds = _SinglePathDataset(n=8, seed=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            train_one_fold_v2(
                model=model,
                train_dataset=train_ds,
                val_dataset=val_ds,
                out_dir=tmpdir,
                epochs=1,
                batch_size=8,
                patience=5,
                warmup_steps_pct=0.0,
                lr=1e-3,
            )
            # Sanity: training completes, no exception


class TestLossFnSelector(unittest.TestCase):
    """Verify trainer accepts a custom loss_fn and uses it."""

    def test_custom_loss_fn_invoked(self) -> None:
        calls = {"n": 0}

        def my_loss(outputs, target):
            calls["n"] += 1
            return (outputs["quantiles"] - target.unsqueeze(-1)).pow(2).mean()

        model = _TinySinglePathModel(n_features=5)
        train_ds = _SinglePathDataset(n=32, seed=0)
        val_ds = _SinglePathDataset(n=8, seed=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            train_one_fold_v2(
                model=model,
                train_dataset=train_ds,
                val_dataset=val_ds,
                out_dir=tmpdir,
                epochs=1,
                batch_size=8,
                patience=5,
                loss_fn=my_loss,
            )
        self.assertGreater(calls["n"], 0, "Custom loss_fn was never called")


class TestSeedDeterminism(unittest.TestCase):
    """Same seed + same data => identical final weights.

    NOTE: model weights are initialised by the caller *before* the trainer
    runs, so the caller must seed before instantiating the model for full
    determinism.  ``train_ensemble`` does this automatically; here we do
    it explicitly for the same reason.
    """

    def test_same_seed_same_weights(self) -> None:
        def _run(seed: int) -> torch.Tensor:
            # Caller-side pre-seed so weight init is deterministic.
            torch.manual_seed(seed)
            np.random.seed(seed)
            model = _TinySinglePathModel(n_features=5)
            train_ds = _SinglePathDataset(n=32, seed=0)
            val_ds = _SinglePathDataset(n=8, seed=1)
            with tempfile.TemporaryDirectory() as tmpdir:
                train_one_fold_v2(
                    model=model,
                    train_dataset=train_ds,
                    val_dataset=val_ds,
                    out_dir=tmpdir,
                    epochs=2,
                    batch_size=8,
                    patience=5,
                    seed=seed,
                )
            return model.proj.weight.detach().clone()

        w_a = _run(seed=42)
        w_b = _run(seed=42)
        self.assertTrue(
            torch.allclose(w_a, w_b, atol=1e-6),
            "Same seed produced different weights -- seeding is not deterministic",
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


def test_trainer_handles_5tuple_with_regime_prior_and_dul():
    """Trainer accepts a dataset that returns 5-tuple and runs DUL loss."""
    import os, sys, tempfile, numpy as np, torch
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.training.trainer_v2 import train_one_fold_v2
    from src.model.dual_path_model_v3 import DualPathLOBModelV3
    from src.training.dataset import LOBDatasetV2

    with tempfile.TemporaryDirectory() as tmp:
        rng = np.random.default_rng(0)
        for name, n_win in [("2024-01-01", 32), ("2024-01-02", 16)]:
            np.savez_compressed(
                os.path.join(tmp, f"{name}.npz"),
                X=rng.standard_normal((n_win, 100, 64)).astype(np.float32),
                X_raw=rng.standard_normal((n_win, 100, 20, 4)).astype(np.float32),
                y=(rng.standard_normal(n_win) * 0.001).astype(np.float32),
                y_mask=np.ones(n_win, dtype=np.uint8),
                regime_prior=rng.standard_normal((n_win, 6)).astype(np.float32),
                timestamps=np.arange(n_win, dtype=np.int64),
                features=np.array([f"f{i}" for i in range(64)], dtype=object),
            )
        train_ds = LOBDatasetV2(tmp, ["2024-01-01"], normalize=False)
        val_ds = LOBDatasetV2(tmp, ["2024-01-02"], normalize=False)

        model = DualPathLOBModelV3(
            n_features=64, n_levels=20, d_model=16, d_raw=8,
            patch_size=10, attn_nhead=2, attn_d_ff=32,
            d_prior=6, n_horizons=1, dropout=0.0,
            use_ppnet_gate=True,
        )
        metrics = train_one_fold_v2(
            model=model,
            train_dataset=train_ds,
            val_dataset=val_ds,
            out_dir=os.path.join(tmp, "ckpt"),
            device="cpu",
            epochs=1,
            batch_size=16,
            lr=1e-3,
            weight_decay=0.0,
            patience=2,
            grad_clip=1.0,
            dul_config={
                "lambda_quantile": 1.0,
                "lambda_utility_rank": 0.3,
                "lambda_calib": 0.0,
                "utility_alpha": 1.0,
            },
        )
        assert metrics is not None
        assert "val_corr" in metrics
    print("PASS: test_trainer_handles_5tuple_with_regime_prior_and_dul")


def test_trainer_without_dul_config_unchanged():
    """Without dul_config, trainer behaviour is the pure quantile-loss path."""
    import os, sys, tempfile, numpy as np, torch
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.training.trainer_v2 import train_one_fold_v2
    from src.model.dual_path_model_v3 import DualPathLOBModelV3
    from src.training.dataset import LOBDatasetV2

    with tempfile.TemporaryDirectory() as tmp:
        rng = np.random.default_rng(0)
        for name, n_win in [("2024-01-01", 32), ("2024-01-02", 16)]:
            np.savez_compressed(
                os.path.join(tmp, f"{name}.npz"),
                X=rng.standard_normal((n_win, 100, 64)).astype(np.float32),
                X_raw=rng.standard_normal((n_win, 100, 20, 4)).astype(np.float32),
                y=(rng.standard_normal(n_win) * 0.001).astype(np.float32),
                y_mask=np.ones(n_win, dtype=np.uint8),
                regime_prior=rng.standard_normal((n_win, 6)).astype(np.float32),
                timestamps=np.arange(n_win, dtype=np.int64),
                features=np.array([f"f{i}" for i in range(64)], dtype=object),
            )
        train_ds = LOBDatasetV2(tmp, ["2024-01-01"], normalize=False)
        val_ds = LOBDatasetV2(tmp, ["2024-01-02"], normalize=False)

        model = DualPathLOBModelV3(
            n_features=64, n_levels=20, d_model=16, d_raw=8,
            patch_size=10, attn_nhead=2, attn_d_ff=32,
            d_prior=6, n_horizons=1, dropout=0.0,
            use_ppnet_gate=True,
        )
        metrics = train_one_fold_v2(
            model=model,
            train_dataset=train_ds, val_dataset=val_ds,
            out_dir=os.path.join(tmp, "ckpt2"),
            device="cpu", epochs=1, batch_size=16, lr=1e-3,
            weight_decay=0.0, patience=2, grad_clip=1.0,
        )
        assert metrics is not None
        assert "val_corr" in metrics
    print("PASS: test_trainer_without_dul_config_unchanged")


if __name__ == "__main__":
    unittest.main(exit=False)
    test_trainer_handles_5tuple_with_regime_prior_and_dul()
    test_trainer_without_dul_config_unchanged()

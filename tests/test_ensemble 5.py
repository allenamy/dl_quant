"""Tests for ModelEnsemble, train_ensemble and ensemble_predict.

Covers:
- Averaging correctness of :class:`ModelEnsemble`
- Different seeds produce different trained models
- Ensemble reduces prediction-error variance relative to individual models
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.training.ensemble import (
    ModelEnsemble,
    ensemble_predict,
    train_ensemble,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ConstModel(nn.Module):
    """Returns a fixed ``quantiles`` tensor regardless of input.

    Used to exercise the pure averaging math of :class:`ModelEnsemble`.
    """

    def __init__(self, q: torch.Tensor):
        super().__init__()
        self.register_buffer("q", q)

    def forward(self, *args, **kwargs):
        return {"quantiles": self.q.clone(), "point_pred": self.q[:, self.q.shape[1] // 2].clone()}


class _TinyModel(nn.Module):
    """Minimal quantile head used for train_ensemble tests."""

    def __init__(self, n_features: int = 4, n_quantiles: int = 3):
        super().__init__()
        self.proj = nn.Linear(n_features, n_quantiles)

    def forward(self, x_feat: torch.Tensor, x_raw=None) -> dict:
        h = x_feat[:, -1, :]
        q = self.proj(h)
        return {"quantiles": q, "point_pred": q[:, 1]}


class _TinyDataset(Dataset):
    def __init__(self, n: int = 64, seq_len: int = 6, n_features: int = 4, seed: int = 0):
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestModelEnsembleAveraging(unittest.TestCase):
    """Check the averaging math of ModelEnsemble."""

    def test_ensemble_averages_quantiles(self) -> None:
        B, n_q = 8, 3
        q1 = torch.full((B, n_q), 1.0)
        q2 = torch.full((B, n_q), 3.0)
        q3 = torch.full((B, n_q), 5.0)
        ens = ModelEnsemble([_ConstModel(q1), _ConstModel(q2), _ConstModel(q3)])
        ens.eval()

        out = ens(torch.zeros(B, 2, 4))  # dummy input, ignored by _ConstModel
        # Expected mean: (1+3+5)/3 = 3
        self.assertTrue(torch.allclose(out["quantiles"], torch.full((B, n_q), 3.0)))
        # Point pred = median column of averaged quantiles
        self.assertTrue(torch.allclose(out["point_pred"], torch.full((B,), 3.0)))

    def test_ensemble_requires_at_least_one_model(self) -> None:
        with self.assertRaises(ValueError):
            ModelEnsemble([])


class TestTrainEnsembleDifferentSeeds(unittest.TestCase):
    """Different seeds should produce different model weights + metrics dict."""

    def test_train_ensemble_different_seeds(self) -> None:
        train_ds = _TinyDataset(n=64, seed=0)
        val_ds = _TinyDataset(n=16, seed=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = train_ensemble(
                model_fn=lambda: _TinyModel(n_features=4),
                train_dataset=train_ds,
                val_dataset=val_ds,
                out_dir=tmpdir,
                n_seeds=3,
                epochs=2,
                batch_size=16,
                patience=5,
            )

            # Three trained models
            self.assertEqual(len(result["models"]), 3)
            self.assertEqual(len(result["seeds"]), 3)
            self.assertEqual(len(result["best_metrics"]), 3)

            # Each seed has its own sub-folder with best_model.pt
            for s in result["seeds"]:
                ckpt = os.path.join(tmpdir, f"seed_{s}", "best_model.pt")
                self.assertTrue(
                    os.path.exists(ckpt),
                    f"checkpoint not found for seed {s}: {ckpt}",
                )

            # Member weights must differ (different seeds -> different init/shuffle)
            w0 = result["models"][0].proj.weight.detach().cpu()
            w1 = result["models"][1].proj.weight.detach().cpu()
            self.assertFalse(
                torch.allclose(w0, w1, atol=1e-6),
                "Two ensemble members trained with different seeds have identical weights",
            )

            # Summary stats are finite
            self.assertTrue(np.isfinite(result["mean_val_corr"]))
            # std is finite with n>=2
            self.assertTrue(np.isfinite(result["std_val_corr"]))

    def test_train_ensemble_rejects_reserved_kwargs(self) -> None:
        """`seed` / `out_dir` must not leak into train_kwargs."""
        train_ds = _TinyDataset(n=32, seed=0)
        val_ds = _TinyDataset(n=8, seed=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                train_ensemble(
                    model_fn=lambda: _TinyModel(n_features=4),
                    train_dataset=train_ds,
                    val_dataset=val_ds,
                    out_dir=tmpdir,
                    n_seeds=2,
                    epochs=1,
                    batch_size=8,
                    seed=99,  # illegal
                )


class TestEnsembleReducesVariance(unittest.TestCase):
    """Synthetic sanity check: ensemble MSE <= worst individual MSE.

    We construct several "models" whose predictions are ``true_signal + noise``
    with independent noise per model.  The averaged prediction has noise
    reduced by ``1/sqrt(K)``, so its MSE is strictly lower than the worst
    individual model's MSE.  This is the core property that motivates
    ensembling in low-SNR regimes.
    """

    def test_ensemble_reduces_variance(self) -> None:
        torch.manual_seed(0)
        B, n_q = 200, 3
        true_signal = torch.randn(B, n_q)

        noisy_models = []
        individual_mses = []
        K = 5
        for k in range(K):
            noise = 0.8 * torch.randn(B, n_q)
            pred = true_signal + noise
            noisy_models.append(_ConstModel(pred))
            mse_k = ((pred - true_signal) ** 2).mean().item()
            individual_mses.append(mse_k)

        ens = ModelEnsemble(noisy_models)
        ens.eval()
        out = ens(torch.zeros(B, 2, 4))  # input ignored
        ens_mse = ((out["quantiles"] - true_signal) ** 2).mean().item()

        # Strictly below the WORST individual model
        self.assertLess(
            ens_mse, max(individual_mses),
            f"Ensemble MSE {ens_mse:.4f} should be < worst member {max(individual_mses):.4f}",
        )
        # Also below the MEAN individual MSE (theory: noise variance / K)
        self.assertLess(
            ens_mse, float(np.mean(individual_mses)),
            f"Ensemble MSE {ens_mse:.4f} should be < mean member {np.mean(individual_mses):.4f}",
        )


class TestEnsemblePredict(unittest.TestCase):
    """ensemble_predict concatenates across batches and averages across members."""

    def test_ensemble_predict_shape_and_values(self) -> None:
        B_total, seq_len, n_features = 20, 5, 4

        # Build a deterministic dataloader
        ds = _TinyDataset(n=B_total, seq_len=seq_len, n_features=n_features, seed=3)
        loader = DataLoader(ds, batch_size=8, shuffle=False)

        # Use constant models with known quantile vectors; since their output
        # doesn't depend on the input, the ensemble average is deterministic.
        q_a = torch.full((8, 3), 1.0)  # largest batch size we'll see
        q_b = torch.full((8, 3), 3.0)

        # Wrap _ConstModel so the returned tensor's leading dim matches the
        # incoming batch -- _TinyDataset yields varying last-batch sizes.
        class _BatchSizedConst(nn.Module):
            def __init__(self, value: float, n_q: int = 3):
                super().__init__()
                self.value = value
                self.n_q = n_q

            def forward(self, x_feat, x_raw=None, **_):
                B = x_feat.shape[0]
                q = torch.full((B, self.n_q), self.value, device=x_feat.device)
                return {"quantiles": q, "point_pred": q[:, self.n_q // 2]}

        models = [_BatchSizedConst(1.0), _BatchSizedConst(3.0)]
        preds = ensemble_predict(models, loader, device="cpu", has_raw=False)

        self.assertEqual(preds.shape, (B_total, 3))
        # Average of 1.0 and 3.0 is 2.0
        np.testing.assert_allclose(preds, np.full((B_total, 3), 2.0), atol=1e-6)


if __name__ == "__main__":
    unittest.main()

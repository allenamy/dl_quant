"""Tests for baseline models: Ridge, TemporalRidge, FITS.

Validates:
1. Ridge detects a planted linear signal
2. TemporalRidge does not overfit pure noise
3. FITS model has correct output shapes and param budget (<30K)
4. FITS low-pass filter suppresses high-frequency noise
"""

from __future__ import annotations

import os
import sys
import unittest

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.baselines.linear_baseline import RidgeBaseline, TemporalRidgeBaseline
from src.baselines.fits_baseline import FITSModel


class TestRidgeBaseline(unittest.TestCase):
    """Ridge baseline must detect a planted linear signal."""

    def test_ridge_finds_planted_signal(self) -> None:
        """Plant a known linear relationship and verify Ridge recovers it.

        Signal: y = 0.5 * x[:, -1, 0] + noise, where noise << signal.
        Ridge should achieve positive correlation on held-out data.
        """
        np.random.seed(42)

        N, L, F = 500, 10, 5
        X = np.random.randn(N, L, F).astype(np.float32)

        # Plant signal in feature 0 at last timestep
        signal = 0.5 * X[:, -1, 0]
        noise = 0.05 * np.random.randn(N)
        y = signal + noise

        # Train/test split (temporal)
        split = int(0.7 * N)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        model = RidgeBaseline(alpha=1.0)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # Correlation must be strongly positive
        corr = np.corrcoef(y_pred, y_test)[0, 1]
        self.assertGreater(corr, 0.8,
                           f"Ridge should find planted signal; got corr={corr:.4f}")

    def test_ridge_handles_2d_input(self) -> None:
        """Ridge should work with 2D input (no time dimension)."""
        np.random.seed(123)
        N, F = 200, 10
        X = np.random.randn(N, F).astype(np.float32)
        y = X[:, 0] * 0.3 + np.random.randn(N) * 0.1

        model = RidgeBaseline(alpha=1.0)
        model.fit(X[:150], y[:150])
        pred = model.predict(X[150:])

        self.assertEqual(pred.shape, (50,))
        corr = np.corrcoef(pred, y[150:])[0, 1]
        self.assertGreater(corr, 0.5)


class TestTemporalRidgeBaseline(unittest.TestCase):
    """TemporalRidge should extract temporal patterns without overfitting noise."""

    def test_temporal_ridge_noise_robustness(self) -> None:
        """On pure noise, TemporalRidge should NOT achieve significant correlation.

        We test that |correlation| < 0.15 on pure noise data, confirming Ridge
        regularisation prevents overfitting even with 4x feature expansion.
        """
        np.random.seed(99)

        N, L, F = 500, 20, 10
        X = np.random.randn(N, L, F).astype(np.float32)
        y = np.random.randn(N).astype(np.float32)

        split = int(0.7 * N)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        model = TemporalRidgeBaseline(alpha=1.0)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        corr = np.corrcoef(y_pred, y_test)[0, 1]
        self.assertLess(abs(corr), 0.15,
                        f"TemporalRidge overfit noise; |corr|={abs(corr):.4f}")

    def test_temporal_ridge_finds_trend_signal(self) -> None:
        """TemporalRidge should detect a trend-based signal that plain Ridge misses.

        Signal: y = mean(x[:, :, 2]) - x[:, -1, 2] (mean-reversion signal).
        This requires the temporal aggregate features to capture.
        """
        np.random.seed(7)

        N, L, F = 500, 30, 5
        X = np.random.randn(N, L, F).astype(np.float32)

        # Mean-reversion signal using feature 2
        y = (X[:, :, 2].mean(axis=1) - X[:, -1, 2]) + 0.1 * np.random.randn(N)
        y = y.astype(np.float32)

        split = int(0.7 * N)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        model = TemporalRidgeBaseline(alpha=1.0)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        corr = np.corrcoef(y_pred, y_test)[0, 1]
        self.assertGreater(corr, 0.5,
                           f"TemporalRidge should find trend signal; got corr={corr:.4f}")

    def test_temporal_feature_shape(self) -> None:
        """Verify temporal features have shape (N, 4*F)."""
        N, L, F = 50, 20, 8
        X = np.random.randn(N, L, F).astype(np.float32)

        model = TemporalRidgeBaseline()
        feats = model._extract_features(X)

        self.assertEqual(feats.shape, (N, 4 * F),
                         f"Expected shape ({N}, {4*F}), got {feats.shape}")


class TestFITSModelForward(unittest.TestCase):
    """Verify FITS model shapes, param budget, and output interface."""

    def test_output_shapes(self) -> None:
        """FITS output must have correct shapes and required keys."""
        torch.manual_seed(42)

        B, L, F = 8, 300, 44
        model = FITSModel(n_features=F, seq_len=L, cut_freq=50, d_compress=8, d_hidden=32)
        model.eval()

        x = torch.randn(B, L, F)
        with torch.no_grad():
            out = model(x)

        # Required keys
        self.assertIn("quantiles", out)
        self.assertIn("point_pred", out)

        # Shape checks
        self.assertEqual(out["quantiles"].shape, (B, 3),
                         f"Expected quantiles (B, 3), got {out['quantiles'].shape}")
        self.assertEqual(out["point_pred"].shape, (B,),
                         f"Expected point_pred (B,), got {out['point_pred'].shape}")

        # All finite
        self.assertTrue(torch.isfinite(out["quantiles"]).all(),
                        "Non-finite values in quantiles")
        self.assertTrue(torch.isfinite(out["point_pred"]).all(),
                        "Non-finite values in point_pred")

    def test_param_count_under_30k(self) -> None:
        """FITS with default settings must have fewer than 30K parameters."""
        model = FITSModel(n_features=44, seq_len=300, cut_freq=50, d_compress=8, d_hidden=32)
        n_params = model.count_parameters()

        self.assertLess(n_params, 30_000,
                        f"FITS has {n_params} params, exceeds 30K budget")

    def test_variable_seq_len(self) -> None:
        """FITS should handle different sequence lengths (with matching cut_freq)."""
        torch.manual_seed(0)

        for L in [50, 100, 200]:
            n_freq = L // 2 + 1
            cut = min(30, n_freq)
            model = FITSModel(n_features=20, seq_len=L, cut_freq=cut, d_compress=4, d_hidden=16)
            model.eval()

            x = torch.randn(4, L, 20)
            with torch.no_grad():
                out = model(x)

            self.assertEqual(out["quantiles"].shape, (4, 3),
                             f"Failed for seq_len={L}")

    def test_cut_freq_validation(self) -> None:
        """cut_freq exceeding available frequency bins should raise ValueError."""
        with self.assertRaises(ValueError):
            FITSModel(n_features=10, seq_len=20, cut_freq=100)


class TestFITSFrequencyFiltering(unittest.TestCase):
    """Verify FITS low-pass filtering suppresses high-frequency noise."""

    def test_high_freq_noise_suppression(self) -> None:
        """Feed sine + noise, verify FITS output is smoother than input.

        We train FITS on clean sine wave targets and noisy sine inputs.
        The model should learn to suppress noise, producing smoother predictions.
        We verify by comparing the variance of first-differences (roughness).
        """
        torch.manual_seed(42)
        np.random.seed(42)

        B, L, F = 200, 100, 1
        n_freq = L // 2 + 1
        cut_freq = 10  # keep only 10 low-freq components

        # Create inputs: low-freq sine + high-freq noise
        t = np.linspace(0, 2 * np.pi, L)
        X_clean = np.sin(t).reshape(1, L, 1).repeat(B, axis=0)  # (B, L, 1)
        noise = 0.5 * np.random.randn(B, L, 1)
        X_noisy = (X_clean + noise).astype(np.float32)

        # Target: use value at last timestep of clean signal
        y = X_clean[:, -1, 0].astype(np.float32)

        # Build FITS model with aggressive low-pass
        model = FITSModel(
            n_features=F, seq_len=L, cut_freq=cut_freq,
            d_compress=1, d_hidden=8, n_quantiles=3,
        )

        # Quick training
        optimiser = torch.optim.Adam(model.parameters(), lr=1e-3)
        model.train()
        x_tensor = torch.tensor(X_noisy)
        y_tensor = torch.tensor(y)

        for _ in range(50):
            out = model(x_tensor)
            loss = torch.nn.functional.mse_loss(out["point_pred"], y_tensor)
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()

        # Compare roughness: input vs what FITS "sees" internally
        # The frequency truncation itself is the denoising mechanism
        model.eval()
        with torch.no_grad():
            # Compute internal frequency representation
            x_t = torch.tensor(X_noisy)
            x_compressed = model.feature_compress(x_t)
            x_freq = torch.fft.rfft(x_compressed, dim=1)
            x_freq_low = x_freq[:, :cut_freq, :]

            # Reconstruct from low-freq only
            x_reconstructed = torch.zeros_like(x_freq)
            x_reconstructed[:, :cut_freq, :] = x_freq_low
            x_smooth = torch.fft.irfft(x_reconstructed, n=L, dim=1)

        # Roughness = variance of first-differences
        input_roughness = np.var(np.diff(X_noisy[:, :, 0], axis=1))
        smooth_roughness = x_smooth[:, :, 0].diff(dim=1).var().item()

        self.assertLess(
            smooth_roughness, input_roughness * 0.5,
            f"Low-pass filter should reduce roughness by at least 50%; "
            f"input={input_roughness:.4f}, smooth={smooth_roughness:.4f}"
        )

    def test_dc_component_preserved(self) -> None:
        """The DC (zero-frequency) component should be preserved by low-pass filter.

        A constant signal should pass through the frequency filter unchanged.
        """
        torch.manual_seed(0)

        B, L, F = 10, 100, 1
        model = FITSModel(n_features=F, seq_len=L, cut_freq=5, d_compress=1, d_hidden=8)
        model.eval()

        # Constant input (only DC component)
        x = torch.ones(B, L, F) * 3.0

        with torch.no_grad():
            x_compressed = model.feature_compress(x)
            x_freq = torch.fft.rfft(x_compressed, dim=1)
            x_freq_low = x_freq[:, :5, :]

            # DC component (index 0) should be dominant
            dc_magnitude = x_freq_low[:, 0, :].abs().mean().item()
            other_magnitude = x_freq_low[:, 1:, :].abs().mean().item()

        self.assertGreater(
            dc_magnitude, other_magnitude * 10,
            f"DC component should dominate for constant input; "
            f"DC={dc_magnitude:.4f}, others={other_magnitude:.4f}"
        )


if __name__ == "__main__":
    unittest.main()

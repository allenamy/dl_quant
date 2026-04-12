"""Tests for src/model components (SpatialLOBEncoder, CausalTemporalEncoder)."""

from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from src.model.side_encoder import SpatialLOBEncoder
from src.model.temporal_encoder import CausalTemporalEncoder
from src.model.lob_transformer import LOBTransformerV2


class TestSpatialEncoder(unittest.TestCase):
    """Unit tests for the SpatialLOBEncoder module."""

    def test_spatial_encoder_shapes(self) -> None:
        """Output shape must be (B, L, d_model) from input (B, L, n_features)."""
        B, L, n_features, d_model = 4, 10, 30, 64
        model = SpatialLOBEncoder(n_features=n_features, d_model=d_model)
        model.eval()

        x = torch.randn(B, L, n_features)
        with torch.no_grad():
            out = model(x)

        self.assertEqual(out.shape, (B, L, d_model),
                         f"Expected shape ({B}, {L}, {d_model}), got {tuple(out.shape)}")

    def test_spatial_encoder_causal(self) -> None:
        """Modifying future timesteps must NOT change output at earlier timesteps.

        Because SpatialLOBEncoder is per-timestep (no temporal mixing),
        perturbing timestep t should leave all other timesteps unchanged.
        """
        B, L, n_features, d_model = 2, 8, 24, 32
        model = SpatialLOBEncoder(n_features=n_features, d_model=d_model)
        model.eval()

        x = torch.randn(B, L, n_features)

        with torch.no_grad():
            out_orig = model(x.clone())

        # Perturb the last 3 timesteps (indices 5, 6, 7)
        x_perturbed = x.clone()
        x_perturbed[:, 5:, :] = torch.randn(B, 3, n_features)

        with torch.no_grad():
            out_perturbed = model(x_perturbed)

        # Earlier timesteps (0..4) must be identical
        diff = (out_orig[:, :5, :] - out_perturbed[:, :5, :]).abs().max().item()
        self.assertEqual(diff, 0.0,
                         f"Early timesteps changed after perturbing future; max diff = {diff}")


class TestTemporalEncoder(unittest.TestCase):
    """Unit tests for the CausalTemporalEncoder module."""

    def test_temporal_encoder_causal(self) -> None:
        """Modifying future tokens must NOT change output at earlier positions.

        Strategy: run the encoder twice -- once on the original input and once
        on a version where positions >= 25 are drastically perturbed.  Output
        at position 24 must remain identical in both runs, proving that the
        encoder is strictly causal.
        """
        torch.manual_seed(42)

        B, L, d_model = 2, 50, 64
        nhead, depth, d_ff = 4, 2, 128
        conv_layers, conv_kernel = 2, 3

        encoder = CausalTemporalEncoder(
            d_model=d_model,
            nhead=nhead,
            depth=depth,
            d_ff=d_ff,
            dropout=0.0,  # disable dropout for deterministic comparison
            conv_layers=conv_layers,
            conv_kernel=conv_kernel,
            conv_dilation_base=2,
        )
        encoder.eval()

        x = torch.randn(B, L, d_model)

        # First forward -- original input
        with torch.no_grad():
            out_original = encoder(x.clone())

        # Modify future positions (25 onward) drastically
        x_modified = x.clone()
        x_modified[:, 25:, :] += 1000.0 * torch.randn_like(x_modified[:, 25:, :])

        # Second forward -- modified input
        with torch.no_grad():
            out_modified = encoder(x_modified)

        # Position 24 output must be unchanged
        diff = (out_original[:, 24, :] - out_modified[:, 24, :]).abs().max().item()
        self.assertLess(diff, 1e-5,
                        f"Causality violated: max abs diff at position 24 = {diff:.2e}")


# Standalone runner for test_temporal_encoder_causal
def test_temporal_encoder_causal() -> None:
    """Convenience function so the test can be called directly."""
    suite = unittest.TestLoader().loadTestsFromName(
        "test_temporal_encoder_causal", TestTemporalEncoder)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


class TestFullModel(unittest.TestCase):
    """Unit tests for the LOBTransformerV2 end-to-end model."""

    def test_full_model_forward(self) -> None:
        """Verify all output shapes, all values finite, and uncertainty > 0."""
        torch.manual_seed(0)

        B, L, n_features = 4, 20, 30
        d_model, nhead, depth, d_ff = 64, 4, 2, 128
        n_quantiles, n_direction_classes = 3, 3

        model = LOBTransformerV2(
            n_features=n_features,
            d_model=d_model,
            nhead=nhead,
            depth=depth,
            d_ff=d_ff,
            dropout=0.0,
            n_quantiles=n_quantiles,
            n_direction_classes=n_direction_classes,
            n_regimes=4,
            conv_layers=2,
            conv_kernel=9,
        )
        model.eval()

        x = torch.randn(B, L, n_features)
        with torch.no_grad():
            out = model(x)

        # Shape checks
        self.assertEqual(out["quantiles"].shape, (B, n_quantiles))
        self.assertEqual(out["direction_logits"].shape, (B, n_direction_classes))
        self.assertEqual(out["uncertainty"].shape, (B,))
        self.assertEqual(out["point_pred"].shape, (B,))

        # All finite
        for key in ("quantiles", "direction_logits", "uncertainty", "point_pred"):
            self.assertTrue(
                torch.isfinite(out[key]).all(),
                f"Non-finite values in output '{key}'",
            )

        # Uncertainty must be strictly positive (Softplus output)
        self.assertTrue(
            (out["uncertainty"] > 0).all(),
            f"Uncertainty contains non-positive values: {out['uncertainty']}",
        )

    def test_full_model_causal(self) -> None:
        """Changing future inputs must not alter prediction at an earlier step."""
        torch.manual_seed(42)

        B, L, n_features = 2, 30, 24
        d_model, nhead, depth, d_ff = 64, 4, 2, 128
        pred_idx = 15  # predict at step 15

        model = LOBTransformerV2(
            n_features=n_features,
            d_model=d_model,
            nhead=nhead,
            depth=depth,
            d_ff=d_ff,
            dropout=0.0,
            conv_layers=2,
            conv_kernel=9,
        )
        model.eval()

        x = torch.randn(B, L, n_features)

        with torch.no_grad():
            out_orig = model(x.clone(), pred_step=pred_idx)

        # Perturb future timesteps (after pred_idx)
        x_perturbed = x.clone()
        x_perturbed[:, pred_idx + 1 :, :] += 1000.0 * torch.randn_like(
            x_perturbed[:, pred_idx + 1 :, :]
        )

        with torch.no_grad():
            out_perturbed = model(x_perturbed, pred_step=pred_idx)

        # All outputs at pred_idx must be unchanged
        for key in ("quantiles", "direction_logits", "uncertainty", "point_pred"):
            diff = (out_orig[key] - out_perturbed[key]).abs().max().item()
            self.assertLess(
                diff,
                1e-5,
                f"Causality violated for '{key}': max abs diff = {diff:.2e}",
            )


if __name__ == "__main__":
    unittest.main()

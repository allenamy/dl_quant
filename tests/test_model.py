"""Tests for src/model/side_encoder – SpatialLOBEncoder."""

from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from src.model.side_encoder import SpatialLOBEncoder


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


if __name__ == "__main__":
    unittest.main()

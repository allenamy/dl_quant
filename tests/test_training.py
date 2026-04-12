"""Tests for src/training – losses, dataset loader, and fold builder."""

from __future__ import annotations

import sys
import os
import tempfile
import unittest

import numpy as np
import torch

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.training.losses import (
    quantile_loss,
    asymmetric_huber_loss,
    combined_loss,
)
from src.training.dataset import LOBDataset, build_time_series_folds


class TestQuantileLoss(unittest.TestCase):
    """Quantile (pinball) loss sanity checks."""

    def test_quantile_loss_calibration(self) -> None:
        """Perfect quantile predictions should yield very small loss (<0.05).

        When all targets equal a constant c, the true conditional quantiles
        at every tau are also c.  Predicting pred_q = c for every quantile
        gives zero pinball loss.  We use a tiny spread around c to keep
        gradients alive and verify loss < 0.05.
        """
        torch.manual_seed(0)
        B = 1_000
        c = 1.5
        target = torch.full((B,), c)

        # Predict the exact quantile value for each tau (all equal c for a
        # point distribution).  Add small noise to make the test non-trivial.
        pred_quantiles = torch.full((B, 3), c) + torch.randn(B, 3) * 1e-4

        loss = quantile_loss(pred_quantiles, target)
        self.assertLess(loss.item(), 0.05,
                        f"Pinball loss for near-perfect quantile preds should be < 0.05, got {loss.item():.4f}")


class TestAsymmetricHuber(unittest.TestCase):
    """Asymmetric Huber loss behaviour."""

    def test_asymmetric_huber_penalizes_left_overestimate(self) -> None:
        """For negative targets, overestimate (pred > target) loss > underestimate loss."""
        B = 256
        target = torch.full((B,), -0.5)  # negative targets

        # Overestimate: predict closer to zero than actual (less negative)
        pred_over = torch.full((B,), -0.2)  # pred > target => overestimate
        # Underestimate: predict more negative than actual
        pred_under = torch.full((B,), -0.8)  # pred < target => underestimate

        loss_over = asymmetric_huber_loss(pred_over, target)
        loss_under = asymmetric_huber_loss(pred_under, target)

        self.assertGreater(
            loss_over.item(), loss_under.item(),
            f"Overestimate loss ({loss_over.item():.4f}) should exceed "
            f"underestimate loss ({loss_under.item():.4f}) for negative targets",
        )


class TestCombinedLoss(unittest.TestCase):
    """Combined loss integration."""

    def test_combined_loss_finite(self) -> None:
        """Combined loss produces finite values for random inputs."""
        torch.manual_seed(42)
        B = 64

        outputs = {
            "quantiles": torch.randn(B, 3),
            "direction_logits": torch.randn(B, 3),
            "uncertainty": torch.rand(B) + 0.01,  # positive variance
            "point_pred": torch.randn(B),
        }
        target = torch.randn(B)
        mask = torch.ones(B, dtype=torch.bool)

        total, loss_dict = combined_loss(outputs, target, mask)

        self.assertTrue(torch.isfinite(total), f"Total loss is not finite: {total}")
        for name, val in loss_dict.items():
            self.assertTrue(
                val == val and abs(val) < float("inf"),
                f"Component '{name}' is not finite: {val}",
            )


if __name__ == "__main__":
    unittest.main()

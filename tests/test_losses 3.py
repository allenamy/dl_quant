"""Tests for the new scale-invariant / directional loss functions.

Covers ``ic_loss``, ``rank_loss``, ``combined_ic_quantile_loss`` and
``directional_huber_loss`` from ``src.training.losses``.  The existing
pinball / asymmetric / combined-4 losses are exercised in
``test_training.py`` and are not duplicated here.
"""

from __future__ import annotations

import os
import sys
import unittest

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.training.losses import (
    combined_ic_quantile_loss,
    directional_huber_loss,
    ic_loss,
    rank_loss,
)


class TestICLoss(unittest.TestCase):
    """IC (1 - Pearson correlation) loss."""

    def test_ic_loss_perfect(self) -> None:
        """Perfectly correlated inputs -> loss ~ 0."""
        torch.manual_seed(0)
        target = torch.randn(256)
        pred = target.clone()  # corr = 1
        loss = ic_loss(pred, target)
        self.assertLess(
            loss.item(), 1e-5,
            f"IC loss for corr=+1 should be ~0, got {loss.item():.6f}",
        )

    def test_ic_loss_correlation(self) -> None:
        """Perfectly anti-correlated inputs -> loss ~ 2."""
        torch.manual_seed(1)
        target = torch.randn(256)
        pred = -target
        loss = ic_loss(pred, target)
        self.assertAlmostEqual(
            loss.item(), 2.0, places=4,
            msg=f"IC loss for corr=-1 should be ~2, got {loss.item():.6f}",
        )

    def test_ic_loss_scale_invariant(self) -> None:
        """Multiplying pred by any positive constant doesn't change loss."""
        torch.manual_seed(7)
        target = torch.randn(128)
        pred = 0.3 * target + 0.1 * torch.randn(128)

        loss_a = ic_loss(pred, target)
        loss_b = ic_loss(100.0 * pred, target)
        loss_c = ic_loss(pred + 50.0, target)  # shift invariance too

        self.assertAlmostEqual(loss_a.item(), loss_b.item(), places=5)
        self.assertAlmostEqual(loss_a.item(), loss_c.item(), places=5)


class TestRankLoss(unittest.TestCase):
    """Pairwise hinge ranking loss."""

    def test_rank_loss_invariant_to_scale(self) -> None:
        """Monotone scaling of pred preserves ranks and thus the loss.

        Determinism is enforced by seeding *just before* each call so the
        random pair sample is identical across the two invocations.
        """
        torch.manual_seed(0)
        target = torch.randn(200)
        pred = 0.5 * target + 0.2 * torch.randn(200)

        torch.manual_seed(42)
        loss_a = rank_loss(pred, target, n_pairs=512)

        torch.manual_seed(42)
        loss_b = rank_loss(10.0 * pred, target, n_pairs=512)

        self.assertAlmostEqual(
            loss_a.item(), loss_b.item(), places=5,
            msg=(
                f"rank_loss must be scale-invariant: "
                f"{loss_a.item():.6f} vs {loss_b.item():.6f}"
            ),
        )

    def test_rank_loss_perfect_order_zero(self) -> None:
        """Pred exactly equal to target -> loss is 0 (all signs agree)."""
        torch.manual_seed(0)
        target = torch.randn(64)
        pred = target.clone()
        loss = rank_loss(pred, target, n_pairs=256)
        self.assertLess(
            loss.item(), 1e-6,
            f"rank_loss for perfect order should be ~0, got {loss.item():.6f}",
        )

    def test_rank_loss_reverse_order_positive(self) -> None:
        """Pred = -target (reversed ranks) -> loss > 0."""
        torch.manual_seed(0)
        target = torch.arange(64, dtype=torch.float32)
        pred = -target
        loss = rank_loss(pred, target, n_pairs=256)
        self.assertGreater(
            loss.item(), 0.0,
            f"rank_loss for reversed order should be > 0, got {loss.item():.6f}",
        )

    def test_rank_loss_small_batch(self) -> None:
        """B<2 -> zero loss (no pairs to evaluate)."""
        pred = torch.tensor([0.5])
        target = torch.tensor([0.1])
        self.assertEqual(rank_loss(pred, target).item(), 0.0)


class TestCombinedICQuantileLoss(unittest.TestCase):
    """Weighted IC + pinball combo."""

    def test_combined_finite_and_weighted(self) -> None:
        """Total equals weighted sum of components, all finite."""
        torch.manual_seed(0)
        B = 64
        outputs = {
            "quantiles": torch.randn(B, 3),
            "point_pred": torch.randn(B),
        }
        target = torch.randn(B)
        total, parts = combined_ic_quantile_loss(
            outputs, target, ic_weight=0.3, quantile_weight=0.7,
        )
        self.assertTrue(torch.isfinite(total))
        expected = 0.7 * parts["quantile"] + 0.3 * parts["ic"]
        self.assertAlmostEqual(parts["total"], expected, places=5)

    def test_combined_defaults_to_median_column(self) -> None:
        """Without ``point_pred`` the median quantile column is used."""
        torch.manual_seed(0)
        B = 32
        q = torch.randn(B, 3)
        target = torch.randn(B)

        total1, _ = combined_ic_quantile_loss(
            {"quantiles": q, "point_pred": q[:, 1]},
            target, ic_weight=0.5, quantile_weight=0.5,
        )
        total2, _ = combined_ic_quantile_loss(
            {"quantiles": q}, target, ic_weight=0.5, quantile_weight=0.5,
        )
        self.assertAlmostEqual(total1.item(), total2.item(), places=6)


class TestDirectionalHuberLoss(unittest.TestCase):
    """Huber with wrong-direction penalty."""

    def test_directional_huber_direction_penalty(self) -> None:
        """Wrong-direction pred yields strictly larger loss than right-direction."""
        B = 128
        target = torch.full((B,), 0.3)

        # Both predictions have the same absolute residual magnitude (0.6)
        # but opposite direction signs relative to target.
        pred_right = torch.full((B,), 0.9)   # same sign as target, |diff|=0.6
        pred_wrong = torch.full((B,), -0.3)  # wrong sign,            |diff|=0.6

        l_right = directional_huber_loss(pred_right, target, direction_weight=2.0)
        l_wrong = directional_huber_loss(pred_wrong, target, direction_weight=2.0)

        self.assertGreater(
            l_wrong.item(), l_right.item(),
            f"Wrong-direction loss ({l_wrong.item():.4f}) must exceed "
            f"right-direction loss ({l_right.item():.4f})",
        )
        # With the same |diff| and weight=2, wrong should be ~2x right.
        self.assertAlmostEqual(
            l_wrong.item() / max(l_right.item(), 1e-8), 2.0, places=3,
        )

    def test_directional_huber_collapses_to_huber_when_weight_is_one(self) -> None:
        """direction_weight=1 -> equivalent to vanilla Huber (no dir penalty)."""
        torch.manual_seed(0)
        pred = torch.randn(64)
        target = torch.randn(64)
        l_weighted = directional_huber_loss(pred, target, direction_weight=1.0)

        # Compute vanilla Huber for cross-check
        diff = pred - target
        absd = diff.abs()
        huber = torch.where(absd <= 1.0, 0.5 * diff ** 2, 1.0 * (absd - 0.5))
        self.assertAlmostEqual(l_weighted.item(), huber.mean().item(), places=5)


if __name__ == "__main__":
    unittest.main()

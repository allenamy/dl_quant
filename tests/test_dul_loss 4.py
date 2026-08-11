import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from src.training.dul_loss import (
    utility_rank_loss,
    coverage_calib_loss,
    compute_dul_loss,
)


class TestUtilityRankLoss(unittest.TestCase):

    def test_low_loss_when_rank_perfect(self):
        """If predicted score order matches target order, logistic loss is small."""
        torch.manual_seed(0)
        n = 64
        y = torch.arange(n, dtype=torch.float32)
        q10 = y - 1.0
        q50 = y
        q90 = y + 1.0
        quantiles = torch.stack([q10, q50, q90], dim=1)
        loss = utility_rank_loss(quantiles, y, alpha=1.0, n_pairs=128)
        self.assertLess(loss.item(), 0.3)

    def test_gradient_flows(self):
        torch.manual_seed(0)
        q = torch.randn(16, 3, requires_grad=True)
        y = torch.randn(16)
        loss = utility_rank_loss(q, y, alpha=1.0, n_pairs=32)
        loss.backward()
        self.assertIsNotNone(q.grad)
        self.assertTrue(torch.isfinite(q.grad).all())

    def test_zero_loss_no_crash_for_n_lt_2(self):
        """Batch of 1 sample: loss should be zero (or very small)."""
        q = torch.randn(1, 3)
        y = torch.randn(1)
        loss = utility_rank_loss(q, y, alpha=1.0, n_pairs=8)
        self.assertTrue(torch.isfinite(loss))


class TestCoverageCalibLoss(unittest.TestCase):

    def test_low_loss_when_perfectly_calibrated(self):
        """If y is Gaussian and quantiles match its 10/50/90 → loss small."""
        torch.manual_seed(0)
        n = 1000
        y = torch.randn(n)
        q10 = torch.quantile(y, 0.1).expand(n)
        q50 = torch.quantile(y, 0.5).expand(n)
        q90 = torch.quantile(y, 0.9).expand(n)
        quantiles = torch.stack([q10, q50, q90], dim=1)
        loss = coverage_calib_loss(quantiles, y)
        # Sigmoid smoothing with k=20 makes this ~0.01 or less
        self.assertLess(loss.item(), 0.03)

    def test_high_loss_when_miscalibrated(self):
        """If all quantiles=0 but y=1.0, coverage is ~0 but should be 10/50/90%."""
        y = torch.ones(100)
        quantiles = torch.zeros(100, 3)
        loss = coverage_calib_loss(quantiles, y)
        # sigmoid(20 * (0 - 1)) ≈ 0, so coverage c≈0 for all τ.
        # Loss = (0 - 0.1)^2 + (0 - 0.5)^2 + (0 - 0.9)^2 = 1.07
        self.assertGreater(loss.item(), 0.5)


class TestComputeDUL(unittest.TestCase):

    def test_dul_matches_sum_of_weighted_components(self):
        torch.manual_seed(0)
        n = 32
        quantiles = torch.randn(n, 3).sort(dim=1).values  # enforce q10<q50<q90
        y = torch.randn(n)
        from src.training.losses import quantile_loss
        l_q = quantile_loss(quantiles, y)
        # For deterministic re-seeding in compute_dul_loss vs direct call
        torch.manual_seed(1)
        l_u = utility_rank_loss(quantiles, y, alpha=1.0, n_pairs=n)
        l_c = coverage_calib_loss(quantiles, y)

        torch.manual_seed(1)  # match the utility rng draw
        total, parts = compute_dul_loss(
            quantiles, y,
            lambda_quantile=1.0,
            lambda_utility_rank=0.3,
            lambda_calib=0.1,
            utility_alpha=1.0,
            n_pairs=n,
        )
        expected = 1.0 * l_q + 0.3 * l_u + 0.1 * l_c
        torch.testing.assert_close(total, expected, rtol=1e-4, atol=1e-5)
        self.assertIn("quantile", parts)
        self.assertIn("utility_rank", parts)
        self.assertIn("calib", parts)
        self.assertIn("total", parts)

    def test_dul_short_circuits_at_weight_zero(self):
        """λ=0 means the component is reported as 0 (no compute)."""
        torch.manual_seed(0)
        quantiles = torch.randn(16, 3).sort(dim=1).values
        y = torch.randn(16)
        total, parts = compute_dul_loss(
            quantiles, y,
            lambda_quantile=1.0,
            lambda_utility_rank=0.0,
            lambda_calib=0.0,
            utility_alpha=1.0,
        )
        self.assertEqual(parts["utility_rank"], 0.0)
        self.assertEqual(parts["calib"], 0.0)
        # total should equal the quantile loss exactly (no other components)
        from src.training.losses import quantile_loss
        expected = 1.0 * quantile_loss(quantiles, y)
        torch.testing.assert_close(total, expected, rtol=1e-6, atol=1e-6)


if __name__ == "__main__":
    unittest.main()

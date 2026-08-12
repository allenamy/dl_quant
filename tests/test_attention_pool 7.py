import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from src.model.attention_pool import AttentionPool1D


class TestAttentionPool1D(unittest.TestCase):

    def test_levels_pool_output_shape(self):
        """Pool 20 LOB levels into one vector per window."""
        B, L, n_levels, d = 4, 600, 20, 32
        x = torch.randn(B * L, d, n_levels)
        pool = AttentionPool1D(d_model=d)
        out = pool(x)
        self.assertEqual(out.shape, (B * L, d))
        self.assertTrue(torch.isfinite(out).all())

    def test_tokens_pool_output_shape(self):
        """Pool 120 patch tokens into one vector per batch element."""
        B, T, d = 4, 120, 32
        x = torch.randn(B, T, d)
        pool = AttentionPool1D(d_model=d, input_is_last_dim=True)
        out = pool(x)
        self.assertEqual(out.shape, (B, d))

    def test_weights_sum_to_one(self):
        """Softmax weights across the pooled axis must sum to 1."""
        B, T, d = 2, 16, 8
        x = torch.randn(B, T, d)
        pool = AttentionPool1D(d_model=d, input_is_last_dim=True)
        _, weights = pool(x, return_weights=True)
        self.assertEqual(weights.shape, (B, T))
        sums = weights.sum(dim=1)
        for s in sums.tolist():
            self.assertAlmostEqual(s, 1.0, places=5)

    def test_no_future_leakage_preserved(self):
        """Stateless — same input → same output."""
        B, T, d = 2, 10, 8
        x = torch.randn(B, T, d)
        pool = AttentionPool1D(d_model=d, input_is_last_dim=True)
        pool.eval()
        out1 = pool(x)
        out2 = pool(x)
        torch.testing.assert_close(out1, out2)


if __name__ == "__main__":
    unittest.main()

import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from src.model.raw_lob_encoder import RawLOBEncoder


class TestRawLOBEncoderV4(unittest.TestCase):

    def test_shape_with_all_v4_flags_on(self):
        enc = RawLOBEncoder(
            d_raw=16,
            n_levels=20,
            use_channel_mix_conv=True,
            use_level_attention_pool=True,
        )
        x_raw = torch.randn(2, 600, 20, 4)
        out = enc(x_raw)
        self.assertEqual(out.shape, (2, 600, 16))
        self.assertTrue(torch.isfinite(out).all())

    def test_no_channel_mix_fallback(self):
        enc = RawLOBEncoder(
            d_raw=16,
            n_levels=20,
            use_channel_mix_conv=False,
            use_level_attention_pool=True,
        )
        x_raw = torch.randn(2, 300, 20, 4)
        out = enc(x_raw)
        self.assertEqual(out.shape, (2, 300, 16))

    def test_no_level_attention_pool_fallback_to_avg(self):
        enc = RawLOBEncoder(
            d_raw=16,
            n_levels=20,
            use_channel_mix_conv=True,
            use_level_attention_pool=False,
        )
        x_raw = torch.randn(2, 300, 20, 4)
        out = enc(x_raw)
        self.assertEqual(out.shape, (2, 300, 16))

    def test_both_off_matches_v3_baseline(self):
        """With both V4 flags off, module behaves like V3 baseline shape-wise."""
        enc = RawLOBEncoder(
            d_raw=16,
            n_levels=20,
            use_channel_mix_conv=False,
            use_level_attention_pool=False,
        )
        x_raw = torch.randn(2, 300, 20, 4)
        out = enc(x_raw)
        self.assertEqual(out.shape, (2, 300, 16))


if __name__ == "__main__":
    unittest.main()

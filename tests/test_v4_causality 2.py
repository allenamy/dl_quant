"""End-to-end V4 causality + shape tests."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from src.model.dual_path_model_v3 import DualPathLOBModelV3


class TestV4Forward(unittest.TestCase):

    def _build(self, **overrides):
        cfg = dict(
            n_features=64,
            n_levels=20,
            d_model=32,
            d_raw=16,
            n_mask_blocks=1,
            n_cross_layers=1,
            patch_size=5,
            attn_nhead=2,
            attn_d_ff=64,
            d_prior=6,
            dropout=0.0,
            n_horizons=4,
            n_symbols=1,
            use_monotonic_quantile=True,
            use_revin=True,
            use_masknet=False,
            use_gdcn=True,
            use_raw_path=True,
            use_attention=True,
            use_conv=True,
            use_channel_mix_conv=True,
            use_level_attention_pool=True,
            use_patch_attention_pool=True,
            use_ppnet_gate=True,
        )
        cfg.update(overrides)
        return DualPathLOBModelV3(**cfg)

    def test_v4_default_forward(self):
        """V4-default flags: produces quantiles_by_horizon with correct shape."""
        m = self._build()
        x_feat = torch.randn(4, 600, 64)
        x_raw = torch.randn(4, 600, 20, 4)
        regime_prior = torch.randn(4, 6)
        out = m(x_feat, x_raw=x_raw, regime_prior=regime_prior, all_horizons=True)
        self.assertIn("quantiles_by_horizon", out)
        self.assertEqual(out["quantiles_by_horizon"].shape, (4, 4, 3))
        # Monotonic quantile: q10 <= q50 <= q90 per (batch, horizon)
        q = out["quantiles_by_horizon"]
        self.assertTrue((q[..., 0] <= q[..., 1]).all())
        self.assertTrue((q[..., 1] <= q[..., 2]).all())

    def test_no_regime_prior_when_gate_off(self):
        """use_ppnet_gate=False: regime_prior ignored, forward still works."""
        m = self._build(use_ppnet_gate=False)
        x_feat = torch.randn(2, 600, 64)
        x_raw = torch.randn(2, 600, 20, 4)
        out = m(x_feat, x_raw=x_raw, regime_prior=None, all_horizons=True)
        self.assertEqual(out["quantiles_by_horizon"].shape, (2, 4, 3))

    def test_ablation_all_v4_flags_off(self):
        """Turn off every V4-specific flag; model must still produce shapes."""
        m = self._build(
            use_revin=False,
            use_gdcn=False,
            use_raw_path=False,
            use_attention=False,
            use_conv=False,
            use_channel_mix_conv=False,
            use_level_attention_pool=False,
            use_patch_attention_pool=False,
            use_ppnet_gate=False,
        )
        x_feat = torch.randn(2, 600, 64)
        out = m(x_feat, x_raw=None, regime_prior=None, all_horizons=True)
        self.assertEqual(out["quantiles_by_horizon"].shape, (2, 4, 3))
        self.assertTrue(torch.isfinite(out["quantiles_by_horizon"]).all())

    def test_deterministic_eval(self):
        """Identical inputs -> identical outputs in eval mode (no hidden state)."""
        m = self._build()
        m.eval()
        x_feat = torch.randn(2, 600, 64)
        x_raw = torch.randn(2, 600, 20, 4)
        regime_prior = torch.randn(2, 6)
        with torch.no_grad():
            out1 = m(x_feat, x_raw=x_raw, regime_prior=regime_prior, all_horizons=True)
            out2 = m(x_feat, x_raw=x_raw, regime_prior=regime_prior, all_horizons=True)
        torch.testing.assert_close(out1["quantiles_by_horizon"], out2["quantiles_by_horizon"])

    def test_perturbation_flows_through(self):
        """Perturbing x_feat changes predictions (smoke test that gradients flow)."""
        m = self._build()
        m.eval()
        x_feat = torch.zeros(1, 600, 64)
        x_feat[:, :, 0] = 1.0
        x_raw = torch.zeros(1, 600, 20, 4)
        regime_prior = torch.zeros(1, 6)
        with torch.no_grad():
            base = m(x_feat, x_raw=x_raw, regime_prior=regime_prior, all_horizons=True)
            x_perturb = x_feat.clone()
            x_perturb[:, 590, :] += 5.0  # perturb late token
            out_perturb = m(x_perturb, x_raw=x_raw, regime_prior=regime_prior, all_horizons=True)
        diff = (out_perturb["quantiles_by_horizon"] - base["quantiles_by_horizon"]).abs().mean()
        self.assertGreater(float(diff), 0.0)
        self.assertTrue(torch.isfinite(diff))

    def test_tcn_causal_under_perturbation(self):
        """Explicit causality audit (reviewer M2): perturb x_feat[:, t=300, :] and
        assert that post-TCN activations at positions < 300 are bit-identical.
        A non-causal conv or pooled LN would fail this."""
        m = self._build(
            # RevIN is intentionally window-aware (not per-timestep causal); disable
            # it so this test directly audits the temporal conv stack.
            use_revin=False,
        )
        m.eval()
        x_feat = torch.randn(1, 600, 64)
        x_raw = torch.randn(1, 600, 20, 4)
        regime_prior = torch.randn(1, 6)

        captured = {}
        def _hook(module, inp, out):
            captured["tcn_out"] = out.detach().clone()

        handle = m.temporal_conv.register_forward_hook(_hook)
        try:
            with torch.no_grad():
                m(x_feat, x_raw=x_raw, regime_prior=regime_prior, all_horizons=True)
                a1 = captured["tcn_out"]
                x2 = x_feat.clone()
                x2[:, 300, :] += 10.0   # perturb mid-sequence tick
                m(x2, x_raw=x_raw, regime_prior=regime_prior, all_horizons=True)
                a2 = captured["tcn_out"]
        finally:
            handle.remove()

        self.assertEqual(a1.shape, a2.shape)
        # Positions [0..299] must be bit-identical after the causal TCN.
        self.assertTrue(
            torch.allclose(a1[:, :300, :], a2[:, :300, :], atol=0.0),
            "TCN output changed at t < 300 when x[300] was perturbed — non-causal!",
        )
        # Positions [300..] should of course differ (sanity).
        self.assertGreater(
            float((a1[:, 300:, :] - a2[:, 300:, :]).abs().max()), 0.0,
            "TCN output at t >= 300 did NOT change when x[300] was perturbed — suspicious.",
        )


if __name__ == "__main__":
    unittest.main()

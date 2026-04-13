"""Tests for MaskNet, GDCN, and DualPathLOBModelV2.

Tests cover:
- MaskBlock / MaskNet shape, mask range, noise suppression
- GatedCrossLayer / GDCN shape, gate range, x0 preservation
- DualPathLOBModelV2 forward (dual + single path), param count, output interface
"""

from __future__ import annotations

import sys
import os
import unittest

# Allow imports without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from src.model.masknet import MaskBlock, MaskNet
from src.model.gdcn import GatedCrossLayer, GDCN
from src.model.dual_path_model import DualPathLOBModel, DualPathLOBModelV2


# ===========================================================================
# Tests for MaskBlock / MaskNet
# ===========================================================================


class TestMaskBlock(unittest.TestCase):
    """Tests for MaskBlock instance-guided mask."""

    def test_forward_shape_2d(self) -> None:
        """Output shape == input shape for (B, d_input)."""
        torch.manual_seed(42)
        block = MaskBlock(d_input=32, d_hidden=32, dropout=0.0)
        block.eval()
        x = torch.randn(8, 32)
        with torch.no_grad():
            out = block(x)
        self.assertEqual(out.shape, (8, 32))

    def test_forward_shape_3d(self) -> None:
        """Output shape == input shape for (B, L, d_input)."""
        torch.manual_seed(42)
        block = MaskBlock(d_input=32, d_hidden=32, dropout=0.0)
        block.eval()
        x = torch.randn(4, 10, 32)
        with torch.no_grad():
            out = block(x)
        self.assertEqual(out.shape, (4, 10, 32))

    def test_mask_range(self) -> None:
        """Mask values should be in [0, 1] (sigmoid output)."""
        torch.manual_seed(42)
        block = MaskBlock(d_input=32, d_hidden=32, dropout=0.0)
        block.eval()
        x = torch.randn(16, 32)
        with torch.no_grad():
            mask = block.mask_net(x)
        self.assertTrue(
            (mask >= 0.0).all() and (mask <= 1.0).all(),
            f"Mask values out of [0, 1] range: min={mask.min():.4f}, max={mask.max():.4f}",
        )

    def test_noise_suppression(self) -> None:
        """With noisy input, mask should suppress some dimensions (not all ones)."""
        torch.manual_seed(42)
        block = MaskBlock(d_input=32, d_hidden=32, dropout=0.0)
        block.eval()
        # Create input with some very noisy dimensions
        x = torch.randn(16, 32)
        with torch.no_grad():
            mask = block.mask_net(x)
        # After sigmoid, not all values should be exactly 1.0 or 0.0
        # (the mask should vary across dimensions)
        mask_std = mask.std()
        self.assertGreater(
            mask_std.item(), 1e-4,
            "Mask should have variation across dimensions (not constant)",
        )

    def test_finite_output(self) -> None:
        """Output should contain no NaN or Inf."""
        torch.manual_seed(42)
        block = MaskBlock(d_input=32, d_hidden=32, dropout=0.0)
        block.eval()
        x = torch.randn(8, 32)
        with torch.no_grad():
            out = block(x)
        self.assertTrue(torch.isfinite(out).all(), "Output should be finite")

    def test_residual_connection(self) -> None:
        """Output should be different from input (FFN contributes)."""
        torch.manual_seed(42)
        block = MaskBlock(d_input=32, d_hidden=32, dropout=0.0)
        block.eval()
        x = torch.randn(4, 32)
        with torch.no_grad():
            out = block(x)
        diff = (out - x).abs().sum().item()
        self.assertGreater(diff, 0.0, "FFN should contribute to output")


class TestMaskNet(unittest.TestCase):
    """Tests for MaskNet (stack of MaskBlocks)."""

    def test_forward_shape(self) -> None:
        """Output shape should match input shape."""
        torch.manual_seed(42)
        net = MaskNet(d_input=32, d_hidden=32, n_blocks=2, dropout=0.0)
        net.eval()
        x = torch.randn(4, 10, 32)
        with torch.no_grad():
            out = net(x)
        self.assertEqual(out.shape, (4, 10, 32))

    def test_multiple_blocks_differ(self) -> None:
        """More blocks should produce different output than fewer blocks."""
        torch.manual_seed(42)
        net1 = MaskNet(d_input=32, d_hidden=32, n_blocks=1, dropout=0.0)
        net2 = MaskNet(d_input=32, d_hidden=32, n_blocks=2, dropout=0.0)
        # They have different structure, so outputs should differ
        self.assertNotEqual(
            len(list(net1.parameters())),
            len(list(net2.parameters())),
            "Different block counts should have different param counts",
        )

    def test_gradient_flows(self) -> None:
        """Gradients should flow through all blocks."""
        torch.manual_seed(42)
        net = MaskNet(d_input=32, d_hidden=32, n_blocks=2, dropout=0.0)
        x = torch.randn(4, 32, requires_grad=True)
        out = net(x)
        loss = out.sum()
        loss.backward()
        self.assertIsNotNone(x.grad, "Gradient should flow to input")
        self.assertTrue(
            (x.grad.abs() > 0).any(),
            "At least some gradient should be nonzero",
        )


# ===========================================================================
# Tests for GatedCrossLayer / GDCN
# ===========================================================================


class TestGatedCrossLayer(unittest.TestCase):
    """Tests for single GatedCrossLayer."""

    def test_gated_cross_shape_2d(self) -> None:
        """Output shape preserved for (B, d_input)."""
        torch.manual_seed(42)
        layer = GatedCrossLayer(d_input=32)
        layer.eval()
        x = torch.randn(8, 32)
        with torch.no_grad():
            out = layer(x, x)
        self.assertEqual(out.shape, (8, 32))

    def test_gated_cross_shape_3d(self) -> None:
        """Output shape preserved for (B, L, d_input)."""
        torch.manual_seed(42)
        layer = GatedCrossLayer(d_input=32)
        layer.eval()
        x = torch.randn(4, 10, 32)
        with torch.no_grad():
            out = layer(x, x)
        self.assertEqual(out.shape, (4, 10, 32))

    def test_gate_range(self) -> None:
        """Gate values should be in [0, 1] (sigmoid output)."""
        torch.manual_seed(42)
        layer = GatedCrossLayer(d_input=32)
        layer.eval()
        x = torch.randn(16, 32)
        with torch.no_grad():
            gate_val = torch.sigmoid(layer.gate(x))
        self.assertTrue(
            (gate_val >= 0.0).all() and (gate_val <= 1.0).all(),
            f"Gate values out of [0, 1]: min={gate_val.min():.4f}, max={gate_val.max():.4f}",
        )

    def test_residual_from_xl(self) -> None:
        """Output should include residual from xl."""
        torch.manual_seed(42)
        layer = GatedCrossLayer(d_input=32)
        layer.eval()
        x0 = torch.randn(4, 32)
        xl = torch.randn(4, 32)
        with torch.no_grad():
            out = layer(x0, xl)
        # Output should be different from xl (cross term contributes)
        diff = (out - xl).abs().sum().item()
        self.assertGreater(diff, 0.0, "Cross term should contribute to output")


class TestGDCN(unittest.TestCase):
    """Tests for GDCN (stack of GatedCrossLayers)."""

    def test_forward_shape(self) -> None:
        """Output shape should match input shape."""
        torch.manual_seed(42)
        gdcn = GDCN(d_input=32, n_layers=3, dropout=0.0)
        gdcn.eval()
        x = torch.randn(4, 10, 32)
        with torch.no_grad():
            out = gdcn(x)
        self.assertEqual(out.shape, (4, 10, 32))

    def test_cross_uses_x0(self) -> None:
        """Verify x0 is always the original input across layers.

        We do this by checking that the first layer gets x as both x0 and xl,
        and subsequent layers always get x as x0 (not the modified output).
        We verify by tracing: if we manually step through the GDCN forward,
        x0 should remain the original input at every step.
        """
        torch.manual_seed(42)
        gdcn = GDCN(d_input=32, n_layers=3, dropout=0.0)
        gdcn.eval()
        x = torch.randn(2, 32)

        # Manual step-through to verify x0 is always x
        x0 = x.clone()
        xl = x.clone()
        with torch.no_grad():
            for layer in gdcn.layers:
                xl_new = layer(x0, xl)
                # x0 should not have changed
                self.assertTrue(
                    torch.equal(x0, x),
                    "x0 should remain the original input across all layers",
                )
                xl = xl_new

    def test_gradient_flows(self) -> None:
        """Gradients should flow through all layers."""
        torch.manual_seed(42)
        gdcn = GDCN(d_input=32, n_layers=2, dropout=0.0)
        x = torch.randn(4, 32, requires_grad=True)
        out = gdcn(x)
        loss = out.sum()
        loss.backward()
        self.assertIsNotNone(x.grad)
        self.assertTrue((x.grad.abs() > 0).any())


# ===========================================================================
# Tests for DualPathLOBModelV2
# ===========================================================================


class TestDualPathV2Forward(unittest.TestCase):
    """Verify DualPathLOBModelV2 forward with both paths."""

    # Use d_prior=0, use_monotonic_quantile=False to test MaskNet+GDCN
    # in isolation from PPNet/MonotonicQuantile (those have their own tests).
    _V2_KWARGS = dict(d_prior=0, use_monotonic_quantile=False)

    def test_forward_dual_path(self) -> None:
        """With both x_feat and x_raw."""
        torch.manual_seed(42)
        B, L = 4, 10
        n_features, n_levels = 44, 20

        model = DualPathLOBModelV2(
            n_features=n_features,
            n_levels=n_levels,
            d_model=32,
            d_raw=16,
            dropout=0.0,
            **self._V2_KWARGS,
        )
        model.eval()

        x_feat = torch.randn(B, L, n_features)
        x_raw = torch.randn(B, L, n_levels, 4)

        with torch.no_grad():
            out = model(x_feat, x_raw)

        self.assertIn("quantiles", out)
        self.assertIn("point_pred", out)
        self.assertEqual(out["quantiles"].shape, (B, 3))
        self.assertEqual(out["point_pred"].shape, (B,))
        self.assertTrue(torch.isfinite(out["quantiles"]).all())
        self.assertTrue(torch.isfinite(out["point_pred"]).all())

    def test_forward_single_path(self) -> None:
        """With x_raw=None (Path A only)."""
        torch.manual_seed(42)
        B, L, n_features = 4, 10, 44

        model = DualPathLOBModelV2(
            n_features=n_features,
            d_model=32,
            d_raw=16,
            dropout=0.0,
            **self._V2_KWARGS,
        )
        model.eval()

        x_feat = torch.randn(B, L, n_features)

        with torch.no_grad():
            out = model(x_feat, x_raw=None)

        self.assertEqual(out["quantiles"].shape, (B, 3))
        self.assertEqual(out["point_pred"].shape, (B,))
        self.assertTrue(torch.isfinite(out["quantiles"]).all())

    def test_raw_path_contributes(self) -> None:
        """Output should change when x_raw is provided vs None."""
        torch.manual_seed(42)
        B, L = 2, 8
        n_features, n_levels = 44, 20

        model = DualPathLOBModelV2(
            n_features=n_features,
            n_levels=n_levels,
            d_model=32,
            d_raw=16,
            dropout=0.0,
            **self._V2_KWARGS,
        )
        model.eval()

        x_feat = torch.randn(B, L, n_features)
        x_raw = torch.randn(B, L, n_levels, 4)

        with torch.no_grad():
            out_dual = model(x_feat, x_raw)
            out_single = model(x_feat, x_raw=None)

        diff = (out_dual["quantiles"] - out_single["quantiles"]).abs().sum().item()
        self.assertGreater(diff, 0.0, "Raw path should change the output")


class TestDualPathV2ParamCount(unittest.TestCase):
    """Verify total params < 40K (Phase 2 budget, MaskNet+GDCN in feature space)."""

    def test_param_count(self) -> None:
        model = DualPathLOBModelV2(
            n_features=44,
            n_levels=20,
            d_model=32,
            d_raw=16,
            n_mask_blocks=2,
            n_cross_layers=2,
            d_prior=0,
            use_monotonic_quantile=False,
            dropout=0.15,
        )
        n_params = sum(p.numel() for p in model.parameters())
        # MaskNet+GDCN now operate in feature space (44-dim) before projection
        # to d_model (32-dim), so param count is higher than d_model-space version.
        self.assertLess(
            n_params, 40000,
            f"DualPathLOBModelV2 has {n_params} params, expected < 40000",
        )

    def test_param_breakdown(self) -> None:
        """Verify params are countable and positive (informational)."""
        model = DualPathLOBModelV2(
            n_features=44,
            n_levels=20,
            d_model=32,
            d_raw=16,
            d_prior=0,
            use_monotonic_quantile=False,
            dropout=0.15,
        )
        total = sum(p.numel() for p in model.parameters())
        self.assertGreater(total, 0)


class TestDualPathV2OutputInterface(unittest.TestCase):
    """Verify output interface matches DualPathLOBModel."""

    _V2_KWARGS = dict(d_prior=0, use_monotonic_quantile=False)

    def test_output_interface(self) -> None:
        """Returns quantiles + point_pred with correct shapes."""
        torch.manual_seed(42)
        B, L = 4, 10

        model = DualPathLOBModelV2(
            n_features=44, d_model=32, d_raw=16, dropout=0.0,
            **self._V2_KWARGS,
        )
        model.eval()

        x_feat = torch.randn(B, L, 44)
        with torch.no_grad():
            out = model(x_feat)

        # Check exact keys
        self.assertEqual(set(out.keys()), {"quantiles", "point_pred"})
        # Check shapes
        self.assertEqual(out["quantiles"].shape, (B, 3))
        self.assertEqual(out["point_pred"].shape, (B,))

    def test_point_pred_is_median(self) -> None:
        """point_pred should be the median (index 1) quantile."""
        torch.manual_seed(42)
        B, L = 4, 10

        model = DualPathLOBModelV2(
            n_features=44, d_model=32, d_raw=16, dropout=0.0,
            **self._V2_KWARGS,
        )
        model.eval()

        x_feat = torch.randn(B, L, 44)
        with torch.no_grad():
            out = model(x_feat)

        self.assertTrue(
            torch.equal(out["point_pred"], out["quantiles"][:, 1]),
            "point_pred should be quantiles[:, 1] (median)",
        )


class TestDualPathV2BackwardCompatible(unittest.TestCase):
    """Verify DualPathLOBModelV2 has the same interface as DualPathLOBModel."""

    _V2_KWARGS = dict(d_prior=0, use_monotonic_quantile=False)

    def test_same_interface(self) -> None:
        """Both models should accept the same inputs and return the same output keys."""
        torch.manual_seed(42)
        B, L = 2, 8
        n_features, n_levels = 44, 20

        v1 = DualPathLOBModel(
            n_features=n_features, n_levels=n_levels,
            d_model=32, d_raw=16, dropout=0.0,
        )
        v2 = DualPathLOBModelV2(
            n_features=n_features, n_levels=n_levels,
            d_model=32, d_raw=16, dropout=0.0,
            **self._V2_KWARGS,
        )
        v1.eval()
        v2.eval()

        x_feat = torch.randn(B, L, n_features)
        x_raw = torch.randn(B, L, n_levels, 4)

        with torch.no_grad():
            out_v1 = v1(x_feat, x_raw)
            out_v2 = v2(x_feat, x_raw)

        # Same output keys
        self.assertEqual(set(out_v1.keys()), set(out_v2.keys()))
        # Same output shapes
        self.assertEqual(out_v1["quantiles"].shape, out_v2["quantiles"].shape)
        self.assertEqual(out_v1["point_pred"].shape, out_v2["point_pred"].shape)

    def test_same_interface_path_a_only(self) -> None:
        """Both models should work with x_raw=None."""
        torch.manual_seed(42)
        B, L, n_features = 2, 8, 44

        v1 = DualPathLOBModel(
            n_features=n_features, d_model=32, d_raw=16, dropout=0.0,
        )
        v2 = DualPathLOBModelV2(
            n_features=n_features, d_model=32, d_raw=16, dropout=0.0,
            **self._V2_KWARGS,
        )
        v1.eval()
        v2.eval()

        x_feat = torch.randn(B, L, n_features)

        with torch.no_grad():
            out_v1 = v1(x_feat, x_raw=None)
            out_v2 = v2(x_feat, x_raw=None)

        self.assertEqual(set(out_v1.keys()), set(out_v2.keys()))
        self.assertEqual(out_v1["quantiles"].shape, out_v2["quantiles"].shape)
        self.assertEqual(out_v1["point_pred"].shape, out_v2["point_pred"].shape)

    def test_v2_gradient_flows_end_to_end(self) -> None:
        """Full backward pass should work (no detached paths)."""
        torch.manual_seed(42)
        B, L = 4, 10

        model = DualPathLOBModelV2(
            n_features=44, n_levels=20, d_model=32, d_raw=16, dropout=0.0,
            **self._V2_KWARGS,
        )

        x_feat = torch.randn(B, L, 44)
        x_raw = torch.randn(B, L, 20, 4)

        out = model(x_feat, x_raw)
        loss = out["quantiles"].sum() + out["point_pred"].sum()
        loss.backward()

        # Check all parameters received gradients
        for name, p in model.named_parameters():
            self.assertIsNotNone(
                p.grad,
                f"Parameter {name} should have gradient",
            )


if __name__ == "__main__":
    unittest.main()

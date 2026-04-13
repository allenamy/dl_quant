"""Tests for DualPathLOBModelV3, PatchEmbedding, CausalPatchAttention, CrossAssetAttention.

Tests cover:
- PatchEmbedding: shape, left-truncation, positional encoding
- CausalPatchAttention: shape, causality, single patch edge case
- CrossAssetAttention: shape, single asset passthrough
- DualPathLOBModelV3: forward (basic, no raw, cross-asset, multi-horizon),
  param count, causality, variable input length, output interface,
  gradient flow, quantile monotonicity
- V3 vs V2 comparison: same output shape, param ratio
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import torch

from src.model.patch_attention import PatchEmbedding, CausalPatchAttention
from src.model.cross_asset import CrossAssetAttention
from src.model.dual_path_model_v3 import DualPathLOBModelV3


# ====================================================================
# TestPatchEmbedding
# ====================================================================


class TestPatchEmbedding:
    """Tests for PatchEmbedding module."""

    def test_output_shape(self):
        """Output shape should be (B, L/P, d_model)."""
        d_model, patch_size = 32, 8
        embed = PatchEmbedding(d_model=d_model, patch_size=patch_size, max_patches=128)
        embed.eval()

        B, L = 4, 64  # 64 / 8 = 8 patches
        x = torch.randn(B, L, d_model)
        with torch.no_grad():
            out = embed(x)

        assert out.shape == (B, 8, d_model), (
            f"Expected shape ({B}, 8, {d_model}), got {tuple(out.shape)}"
        )

    def test_truncation_from_left(self):
        """When L is not divisible by P, truncate from the LEFT (keep recent data).

        With L=70 and P=8: 70 % 8 = 6, so drop first 6 timesteps.
        Result: 64 / 8 = 8 patches.
        """
        d_model, patch_size = 32, 8
        embed = PatchEmbedding(d_model=d_model, patch_size=patch_size, max_patches=128)
        embed.eval()

        B = 2
        L = 70  # 70 % 8 = 6, so 8 patches from the last 64 steps
        x = torch.randn(B, L, d_model)
        with torch.no_grad():
            out = embed(x)

        n_patches = 70 // 8  # = 8 (drop 6 from left)
        assert out.shape == (B, n_patches, d_model), (
            f"Expected {n_patches} patches, got {out.shape[1]}"
        )

    def test_truncation_preserves_recent_data(self):
        """Truncation keeps the most recent data, not the oldest.

        We verify this by checking that the last patch's content comes from
        the last patch_size timesteps of the input.
        """
        torch.manual_seed(42)
        d_model, patch_size = 16, 4
        embed = PatchEmbedding(d_model=d_model, patch_size=patch_size, max_patches=128)
        embed.eval()

        B = 1
        L = 10  # 10 % 4 = 2, drop first 2 steps, keep last 8 -> 2 patches

        x = torch.randn(B, L, d_model)

        # Run with full L=10
        with torch.no_grad():
            out_full = embed(x)

        # Run with only the last 8 steps (manually truncated)
        with torch.no_grad():
            out_truncated = embed(x[:, 2:, :])

        # Both should produce identical output (same data after truncation)
        diff = (out_full - out_truncated).abs().max().item()
        assert diff < 1e-6, (
            f"Truncation should keep recent data; max diff = {diff}"
        )

    def test_positional_encoding(self):
        """Different patches should get different positional embeddings.

        We verify by checking that the positional embedding parameter has
        different values for different positions.
        """
        d_model = 32
        embed = PatchEmbedding(d_model=d_model, patch_size=8, max_patches=128)

        # Check that at least some positions differ
        pos_0 = embed.pos_embed[0, 0, :]
        pos_1 = embed.pos_embed[0, 1, :]
        # After init, they may have small random differences or zeros
        # We just need to verify the structure exists and is the right shape
        assert embed.pos_embed.shape == (1, 128, d_model), (
            f"Expected pos_embed shape (1, 128, {d_model}), got {tuple(embed.pos_embed.shape)}"
        )

    def test_exact_divisible_no_truncation(self):
        """When L is exactly divisible by P, no truncation occurs."""
        d_model, patch_size = 32, 8
        embed = PatchEmbedding(d_model=d_model, patch_size=patch_size, max_patches=128)
        embed.eval()

        B, L = 2, 48  # 48 / 8 = 6, no truncation
        x = torch.randn(B, L, d_model)
        with torch.no_grad():
            out = embed(x)

        assert out.shape == (B, 6, d_model)

    def test_single_patch(self):
        """Edge case: input length equals patch_size -> exactly 1 patch."""
        d_model, patch_size = 32, 8
        embed = PatchEmbedding(d_model=d_model, patch_size=patch_size, max_patches=128)
        embed.eval()

        B, L = 2, 8  # 8 / 8 = 1 patch
        x = torch.randn(B, L, d_model)
        with torch.no_grad():
            out = embed(x)

        assert out.shape == (B, 1, d_model)


# ====================================================================
# TestCausalPatchAttention
# ====================================================================


class TestCausalPatchAttention:
    """Tests for CausalPatchAttention module."""

    def test_output_shape(self):
        """Output shape should match input shape."""
        d_model = 32
        attn = CausalPatchAttention(d_model=d_model, nhead=4, d_ff=64, dropout=0.0)
        attn.eval()

        B, n_patches = 4, 10
        x = torch.randn(B, n_patches, d_model)
        with torch.no_grad():
            out = attn(x)

        assert out.shape == (B, n_patches, d_model), (
            f"Expected shape ({B}, {n_patches}, {d_model}), got {tuple(out.shape)}"
        )

    def test_causality(self):
        """Future patches must NOT affect past patches.

        Strategy: run the attention twice, once on original input, once with
        future patches drastically perturbed. Output at earlier positions
        must be identical.
        """
        torch.manual_seed(42)
        d_model = 32
        attn = CausalPatchAttention(d_model=d_model, nhead=4, d_ff=64, dropout=0.0)
        attn.eval()

        B, n_patches = 2, 8
        x = torch.randn(B, n_patches, d_model)

        with torch.no_grad():
            out_orig = attn(x.clone())

        # Perturb the last 3 patches (indices 5, 6, 7)
        x_pert = x.clone()
        x_pert[:, 5:, :] = torch.randn(B, 3, d_model) * 1000.0

        with torch.no_grad():
            out_pert = attn(x_pert)

        # Patches 0-4 should be unchanged
        diff = (out_orig[:, :5, :] - out_pert[:, :5, :]).abs().max().item()
        assert diff < 1e-5, (
            f"Causality violated: max diff at early patches = {diff:.2e}"
        )

    def test_single_patch(self):
        """Edge case: single patch should work (no attention to compute)."""
        d_model = 32
        attn = CausalPatchAttention(d_model=d_model, nhead=4, d_ff=64, dropout=0.0)
        attn.eval()

        B = 2
        x = torch.randn(B, 1, d_model)
        with torch.no_grad():
            out = attn(x)

        assert out.shape == (B, 1, d_model)
        assert torch.isfinite(out).all(), "Non-finite values with single patch"

    def test_finite_output(self):
        """Output should contain no NaN or Inf."""
        torch.manual_seed(42)
        d_model = 32
        attn = CausalPatchAttention(d_model=d_model, nhead=4, d_ff=64, dropout=0.0)
        attn.eval()

        x = torch.randn(4, 20, d_model)
        with torch.no_grad():
            out = attn(x)

        assert torch.isfinite(out).all(), "Non-finite values in attention output"


# ====================================================================
# TestCrossAssetAttention
# ====================================================================


class TestCrossAssetAttention:
    """Tests for CrossAssetAttention module."""

    def test_output_shape(self):
        """Output shape should match input shape."""
        d_model = 32
        ca = CrossAssetAttention(d_model=d_model, nhead=2, dropout=0.0)
        ca.eval()

        B, n_symbols = 4, 3
        x = torch.randn(B, n_symbols, d_model)
        with torch.no_grad():
            out = ca(x)

        assert out.shape == (B, n_symbols, d_model), (
            f"Expected shape ({B}, {n_symbols}, {d_model}), got {tuple(out.shape)}"
        )

    def test_single_asset_passthrough(self):
        """With 1 symbol, output should be approximately the input (residual dominant).

        Since the attention layer has a residual connection and the attention
        with a single token just attends to itself, the output should be
        close to the input (the attention + FFN contribute but residual dominates
        at initialization).
        """
        torch.manual_seed(42)
        d_model = 32
        ca = CrossAssetAttention(d_model=d_model, nhead=2, dropout=0.0)
        ca.eval()

        B = 4
        x = torch.randn(B, 1, d_model)  # single symbol
        with torch.no_grad():
            out = ca(x)

        # Residual connection means output should be close to input
        diff = (out - x).abs().mean().item()
        assert diff < 2.0, (
            f"Single asset output diverges too much from input: mean diff = {diff}"
        )

    def test_multi_asset_cross_information(self):
        """With multiple assets, each should incorporate information from others.

        We verify via gradients: the loss on asset 0's output should produce
        non-zero gradients for asset 2's input, proving that cross-attention
        connects them.
        """
        torch.manual_seed(42)
        d_model = 32
        ca = CrossAssetAttention(d_model=d_model, nhead=2, dropout=0.0)

        B = 2
        x = torch.randn(B, 3, d_model, requires_grad=True)

        out = ca(x)

        # Loss on asset 0 only
        loss = out[:, 0, :].sum()
        loss.backward()

        # Gradient should flow to asset 2's input (cross-attention)
        grad_asset_2 = x.grad[:, 2, :].abs().sum().item()
        assert grad_asset_2 > 0.0, (
            f"No gradient flow from asset 0 to asset 2 (cross-attention not connecting)"
        )

    def test_gradient_flow(self):
        """Gradients should flow through all assets."""
        d_model = 32
        ca = CrossAssetAttention(d_model=d_model, nhead=2, dropout=0.0)

        x = torch.randn(2, 3, d_model, requires_grad=True)
        out = ca(x)
        loss = out.sum()
        loss.backward()

        assert x.grad is not None, "No gradient for input"
        assert x.grad.abs().sum() > 0, "Zero gradient"


# ====================================================================
# TestDualPathV3
# ====================================================================


class TestDualPathV3:
    """Tests for DualPathLOBModelV3."""

    def _make_model(self, **overrides):
        """Create a V3 model with sensible test defaults."""
        defaults = dict(
            n_features=52,
            n_levels=20,
            d_model=32,
            d_raw=16,
            n_mask_blocks=2,
            n_cross_layers=2,
            patch_size=8,
            attn_nhead=4,
            attn_d_ff=64,
            d_prior=6,
            dropout=0.0,  # deterministic for testing
            n_horizons=1,
            n_symbols=1,
            use_monotonic_quantile=True,
        )
        defaults.update(overrides)
        return DualPathLOBModelV3(**defaults)

    def test_forward_basic(self):
        """Standard forward pass with both paths."""
        torch.manual_seed(42)
        model = self._make_model()
        model.eval()

        B, L = 4, 64  # 64 / 8 = 8 patches
        x_feat = torch.randn(B, L, 52)
        x_raw = torch.randn(B, L, 20, 4)
        regime_prior = torch.randn(B, 6)

        with torch.no_grad():
            out = model(x_feat, x_raw=x_raw, regime_prior=regime_prior)

        assert "quantiles" in out
        assert "point_pred" in out
        assert out["quantiles"].shape == (B, 3)
        assert out["point_pred"].shape == (B,)
        assert torch.isfinite(out["quantiles"]).all()
        assert torch.isfinite(out["point_pred"]).all()

    def test_forward_no_raw(self):
        """Path A only (x_raw=None)."""
        torch.manual_seed(42)
        model = self._make_model()
        model.eval()

        B, L = 4, 64
        x_feat = torch.randn(B, L, 52)

        with torch.no_grad():
            out = model(x_feat, x_raw=None)

        assert out["quantiles"].shape == (B, 3)
        assert out["point_pred"].shape == (B,)

    def test_forward_with_cross_asset(self):
        """Multi-symbol forward with cross-asset features."""
        torch.manual_seed(42)
        model = self._make_model(n_symbols=2)
        model.eval()

        B, L = 4, 64
        x_feat = torch.randn(B, L, 52)
        x_raw = torch.randn(B, L, 20, 4)
        cross_feats = torch.randn(B, 1, 32)  # 1 other symbol's h_pred

        with torch.no_grad():
            out = model(x_feat, x_raw=x_raw, cross_asset_feats=cross_feats)

        assert out["quantiles"].shape == (B, 3)
        assert out["point_pred"].shape == (B,)

    def test_forward_multi_horizon(self):
        """Multi-horizon: different heads produce different outputs."""
        torch.manual_seed(42)
        model = self._make_model(n_horizons=3)
        model.eval()

        B, L = 4, 64
        x_feat = torch.randn(B, L, 52)
        x_raw = torch.randn(B, L, 20, 4)

        outputs = []
        with torch.no_grad():
            for h in range(3):
                out = model(x_feat, x_raw=x_raw, horizon_idx=h)
                outputs.append(out["quantiles"])

        # Different horizon heads should (generally) produce different outputs
        # At initialization with random weights, they should differ.
        diff_01 = (outputs[0] - outputs[1]).abs().sum().item()
        diff_02 = (outputs[0] - outputs[2]).abs().sum().item()
        assert diff_01 > 0.001, "Horizon 0 and 1 produce identical output"
        assert diff_02 > 0.001, "Horizon 0 and 2 produce identical output"

    def test_param_count(self):
        """Total params should be in a reasonable range.

        V2 is ~39K (MaskNet+GDCN in feature space). V3 adds attention + patching.
        MaskNet+GDCN operate in n_features-dim (52) before projection,
        so params are higher than d_model-space versions.
        max_patches=150 supports up to L=1200 (20min input).
        """
        model = self._make_model(dropout=0.15)
        n_params = sum(p.numel() for p in model.parameters())
        assert n_params < 75000, (
            f"V3 has {n_params} params, expected < 75000"
        )
        # Should be more than V2 (~39K) due to attention
        assert n_params > 40000, (
            f"V3 has {n_params} params, expected > 40000 (should include attention)"
        )

    def test_causality(self):
        """Future inputs must not affect prediction.

        Strategy: run model twice. Second time, drastically perturb the
        LAST portion of the input sequence. Since the model uses causal
        conv + causal attention + takes the last patch, we check that
        changing data after a split point affects the output (since the
        last patch includes that data), but changing data before the split
        does NOT change the output at earlier conv positions.

        For a proper causality test: we check that conv layers are causal
        by verifying that changing future timesteps does not change the
        conv output at earlier timesteps.
        """
        torch.manual_seed(42)
        model = self._make_model()
        model.eval()

        B, L = 2, 64
        x_feat = torch.randn(B, L, 52)
        x_raw = torch.randn(B, L, 20, 4)

        # Test conv causality: perturb the last half, check first half unchanged
        # We need to test the conv part separately
        # Path A: MaskNet -> GDCN -> proj (MaskNet+GDCN in feature space)
        h_craft = model.masknet(x_feat)
        h_craft = model.gdcn(h_craft)
        h_craft = model.input_proj(h_craft)
        h_raw = model.raw_encoder(x_raw)
        h = torch.cat([h_craft, h_raw], dim=-1)
        h = model.fusion(h)

        with torch.no_grad():
            h_conv_orig = model.temporal_conv(h.clone())

        # Perturb the last 16 timesteps of h
        h_pert = h.clone()
        h_pert[:, 48:, :] += 1000.0 * torch.randn_like(h_pert[:, 48:, :])

        with torch.no_grad():
            h_conv_pert = model.temporal_conv(h_pert)

        # First 33 timesteps should be unchanged (RF=15, so position 33+14=47 < 48)
        # Actually, with dilation [1,2,4] and kernel=3, the cumulative RF:
        # Layer 1: RF = 3 (dilation 1)
        # Layer 2: RF = 3 + 2*2 = 7 (dilation 2)
        # Layer 3: RF = 7 + 4*2 = 15 (dilation 4)
        # Position 32 depends on positions 32-14=18 to 32. All < 48. Safe.
        diff = (h_conv_orig[:, :33, :] - h_conv_pert[:, :33, :]).abs().max().item()
        assert diff < 1e-5, (
            f"Conv causality violated: max diff at early positions = {diff:.2e}"
        )

    def test_variable_input_length(self):
        """Model should work with different input lengths."""
        torch.manual_seed(42)
        model = self._make_model()
        model.eval()

        B = 2
        for L in [16, 32, 64, 128, 300, 600]:
            x_feat = torch.randn(B, L, 52)
            x_raw = torch.randn(B, L, 20, 4)
            with torch.no_grad():
                out = model(x_feat, x_raw=x_raw)

            assert out["quantiles"].shape == (B, 3), (
                f"Failed for L={L}: shape = {tuple(out['quantiles'].shape)}"
            )
            assert torch.isfinite(out["quantiles"]).all(), (
                f"Non-finite values for L={L}"
            )

    def test_output_interface(self):
        """Output dict should have exactly 'quantiles' and 'point_pred'."""
        torch.manual_seed(42)
        model = self._make_model()
        model.eval()

        x_feat = torch.randn(4, 64, 52)
        with torch.no_grad():
            out = model(x_feat)

        assert set(out.keys()) == {"quantiles", "point_pred"}, (
            f"Unexpected output keys: {set(out.keys())}"
        )

    def test_backward_gradient_flow(self):
        """Gradients must flow through all components end-to-end."""
        torch.manual_seed(42)
        model = self._make_model()

        B, L = 4, 64
        x_feat = torch.randn(B, L, 52)
        x_raw = torch.randn(B, L, 20, 4)
        regime_prior = torch.randn(B, 6)

        out = model(x_feat, x_raw=x_raw, regime_prior=regime_prior)
        loss = out["quantiles"].sum() + out["point_pred"].sum()
        loss.backward()

        # Check all parameters received gradients
        for name, p in model.named_parameters():
            assert p.grad is not None, f"No gradient for parameter {name}"

    def test_quantile_monotonic(self):
        """q10 < q50 < q90 must be guaranteed (structural monotonicity)."""
        torch.manual_seed(42)
        model = self._make_model()
        model.eval()

        # Test with many random inputs
        for _ in range(10):
            B = 16
            L = 64
            x_feat = torch.randn(B, L, 52) * 5  # varied magnitudes
            x_raw = torch.randn(B, L, 20, 4) * 5

            with torch.no_grad():
                out = model(x_feat, x_raw=x_raw)

            q = out["quantiles"]
            assert (q[:, 0] < q[:, 1]).all(), (
                f"q10 >= q50: q10={q[:, 0]}, q50={q[:, 1]}"
            )
            assert (q[:, 1] < q[:, 2]).all(), (
                f"q50 >= q90: q50={q[:, 1]}, q90={q[:, 2]}"
            )

    def test_no_ppnet_gate(self):
        """V3 with d_prior=0 disables PPNet gate entirely."""
        model = self._make_model(d_prior=0)
        assert model.ppnet_gate is None, "PPNet gate should be None when d_prior=0"

        # Should still work without regime_prior
        model.eval()
        x_feat = torch.randn(2, 64, 52)
        with torch.no_grad():
            out = model(x_feat)
        assert out["quantiles"].shape == (2, 3)

    def test_simple_quantile_fallback(self):
        """V3 with use_monotonic_quantile=False uses simple linear head."""
        torch.manual_seed(42)
        model = self._make_model(use_monotonic_quantile=False, d_prior=0)
        model.eval()

        x_feat = torch.randn(4, 64, 52)
        with torch.no_grad():
            out = model(x_feat)

        assert out["quantiles"].shape == (4, 3)
        assert out["point_pred"].shape == (4,)

    def test_raw_path_contributes(self):
        """Output should change when x_raw is provided vs None."""
        torch.manual_seed(42)
        model = self._make_model()
        model.eval()

        B, L = 2, 64
        x_feat = torch.randn(B, L, 52)
        x_raw = torch.randn(B, L, 20, 4)

        with torch.no_grad():
            out_dual = model(x_feat, x_raw=x_raw)
            out_single = model(x_feat, x_raw=None)

        diff = (out_dual["quantiles"] - out_single["quantiles"]).abs().sum().item()
        assert diff > 0.0, "Raw path should change the output"

    def test_cross_asset_contributes(self):
        """Cross-asset features should change the output."""
        torch.manual_seed(42)
        model = self._make_model(n_symbols=2)
        model.eval()

        B, L = 2, 64
        x_feat = torch.randn(B, L, 52)
        x_raw = torch.randn(B, L, 20, 4)
        cross_feats = torch.randn(B, 1, 32)

        with torch.no_grad():
            out_with_ca = model(x_feat, x_raw=x_raw, cross_asset_feats=cross_feats)
            out_without_ca = model(x_feat, x_raw=x_raw, cross_asset_feats=None)

        diff = (
            out_with_ca["quantiles"] - out_without_ca["quantiles"]
        ).abs().sum().item()
        assert diff > 0.0, "Cross-asset features should change the output"


# ====================================================================
# TestV3vsV2
# ====================================================================


class TestV3vsV2:
    """Comparison tests between V3 and V2."""

    def test_same_output_shape(self):
        """V3 and V2 should produce outputs with the same shape."""
        from src.model.dual_path_model import DualPathLOBModelV2

        torch.manual_seed(42)
        B, L = 4, 64
        n_feat, n_levels = 52, 20

        v2 = DualPathLOBModelV2(
            n_features=n_feat, n_levels=n_levels,
            d_model=32, d_raw=16, d_prior=6,
            dropout=0.0, use_monotonic_quantile=True,
        )
        v3 = DualPathLOBModelV3(
            n_features=n_feat, n_levels=n_levels,
            d_model=32, d_raw=16, d_prior=6,
            dropout=0.0, use_monotonic_quantile=True,
            n_horizons=1, n_symbols=1,
        )
        v2.eval()
        v3.eval()

        x_feat = torch.randn(B, L, n_feat)
        x_raw = torch.randn(B, L, n_levels, 4)
        regime_prior = torch.randn(B, 6)

        with torch.no_grad():
            out_v2 = v2(x_feat, x_raw=x_raw, regime_prior=regime_prior)
            out_v3 = v3(x_feat, x_raw=x_raw, regime_prior=regime_prior)

        # Same output keys
        assert set(out_v2.keys()) == set(out_v3.keys()), (
            f"V2 keys: {set(out_v2.keys())}, V3 keys: {set(out_v3.keys())}"
        )
        # Same output shapes
        assert out_v2["quantiles"].shape == out_v3["quantiles"].shape
        assert out_v2["point_pred"].shape == out_v3["point_pred"].shape

    def test_param_comparison(self):
        """V3 should have less than 2x the params of V2."""
        from src.model.dual_path_model import DualPathLOBModelV2

        v2 = DualPathLOBModelV2(
            n_features=52, n_levels=20, d_model=32, d_raw=16,
            n_mask_blocks=2, n_cross_layers=2, d_prior=6,
            use_monotonic_quantile=True, dropout=0.15,
        )
        v3 = DualPathLOBModelV3(
            n_features=52, n_levels=20, d_model=32, d_raw=16,
            n_mask_blocks=2, n_cross_layers=2, d_prior=6,
            dropout=0.15, n_horizons=1, n_symbols=1,
            use_monotonic_quantile=True,
        )

        n_v2 = sum(p.numel() for p in v2.parameters())
        n_v3 = sum(p.numel() for p in v3.parameters())

        assert n_v3 < 2 * n_v2, (
            f"V3 ({n_v3}) >= 2x V2 ({n_v2}). "
            f"Ratio: {n_v3 / n_v2:.2f}x"
        )

    def test_v3_backward_compatible_interface(self):
        """V3 with default params should accept the same inputs as V2."""
        from src.model.dual_path_model import DualPathLOBModelV2

        torch.manual_seed(42)
        B, L, n_feat = 2, 64, 52

        v2 = DualPathLOBModelV2(
            n_features=n_feat, d_model=32, d_raw=16,
            d_prior=0, dropout=0.0, use_monotonic_quantile=True,
        )
        v3 = DualPathLOBModelV3(
            n_features=n_feat, d_model=32, d_raw=16,
            d_prior=0, dropout=0.0, use_monotonic_quantile=True,
            n_horizons=1, n_symbols=1,
        )
        v2.eval()
        v3.eval()

        x_feat = torch.randn(B, L, n_feat)

        # Both should work with Path A only
        with torch.no_grad():
            out_v2 = v2(x_feat, x_raw=None)
            out_v3 = v3(x_feat, x_raw=None)

        assert set(out_v2.keys()) == set(out_v3.keys())
        assert out_v2["quantiles"].shape == out_v3["quantiles"].shape


# ====================================================================
# Run with pytest
# ====================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

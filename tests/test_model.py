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
from src.features.feature_groups import get_feature_groups, get_feature_group_indices


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


class TestFeatureGroups(unittest.TestCase):
    """Unit tests for semantic feature grouping."""

    # The 39 features produced by compute_microstructure_features (excluding
    # timestamp and mid_price), in their exact output order.
    ORIGINAL_39 = [
        "log_return_1s", "log_return_5s", "log_return_30s",
        "spread_bps", "spread_change",
        "obi_L1", "obi_L5", "obi_L10", "obi_L25", "obi_L1_delta",
        "bid_depth_L5", "ask_depth_L5", "bid_depth_L25", "ask_depth_L25",
        "depth_ratio_L5",
        "weighted_price_bid_L10", "weighted_price_ask_L10", "price_pressure",
        "realized_vol_30s", "realized_vol_60s", "realized_vol_300s",
        "kyle_lambda_30s", "amihud_30s",
        "bid_slope_L10", "ask_slope_L10",
        "bid_concentration", "ask_concentration",
        "bid_amt_ratio_L0", "bid_amt_ratio_L1", "bid_amt_ratio_L2",
        "bid_amt_ratio_L3", "bid_amt_ratio_L4",
        "ask_amt_ratio_L0", "ask_amt_ratio_L1", "ask_amt_ratio_L2",
        "ask_amt_ratio_L3", "ask_amt_ratio_L4",
        "second_of_day_sin", "second_of_day_cos",
    ]

    # 5 new order-flow features (being added in parallel)
    ORDER_FLOW_5 = [
        "delta_bid_depth_L5", "delta_ask_depth_L5",
        "net_order_flow_L5", "delta_obi_L5_5s", "delta_pressure_5s",
    ]

    ALL_44 = ORIGINAL_39 + ORDER_FLOW_5

    def test_feature_group_assignment(self) -> None:
        """Verify that known features are placed in the semantically correct group."""
        groups = get_feature_groups()

        # Bid group must contain bid-specific features
        self.assertIn("bid_depth_L5", groups["bid"])
        self.assertIn("bid_depth_L25", groups["bid"])
        self.assertIn("weighted_price_bid_L10", groups["bid"])
        self.assertIn("bid_slope_L10", groups["bid"])
        self.assertIn("bid_concentration", groups["bid"])
        self.assertIn("bid_amt_ratio_L0", groups["bid"])
        self.assertIn("obi_L1", groups["bid"])
        self.assertIn("delta_bid_depth_L5", groups["bid"])

        # Ask group must contain ask-specific features
        self.assertIn("ask_depth_L5", groups["ask"])
        self.assertIn("ask_depth_L25", groups["ask"])
        self.assertIn("weighted_price_ask_L10", groups["ask"])
        self.assertIn("ask_slope_L10", groups["ask"])
        self.assertIn("ask_concentration", groups["ask"])
        self.assertIn("ask_amt_ratio_L0", groups["ask"])
        self.assertIn("delta_ask_depth_L5", groups["ask"])

        # Global group must contain cross-side and market-wide features
        self.assertIn("log_return_1s", groups["global"])
        self.assertIn("spread_bps", groups["global"])
        self.assertIn("depth_ratio_L5", groups["global"])
        self.assertIn("price_pressure", groups["global"])
        self.assertIn("realized_vol_30s", groups["global"])
        self.assertIn("second_of_day_sin", groups["global"])
        self.assertIn("net_order_flow_L5", groups["global"])

        # Bid features must NOT appear in ask or global groups
        self.assertNotIn("bid_depth_L5", groups["ask"])
        self.assertNotIn("bid_depth_L5", groups["global"])

        # Ask features must NOT appear in bid or global groups
        self.assertNotIn("ask_depth_L5", groups["bid"])
        self.assertNotIn("ask_depth_L5", groups["global"])

    def test_feature_groups_no_overlap(self) -> None:
        """No feature should appear in more than one group."""
        groups = get_feature_groups()

        bid_set = set(groups["bid"])
        ask_set = set(groups["ask"])
        global_set = set(groups["global"])

        self.assertEqual(len(bid_set & ask_set), 0,
                         f"Overlap bid/ask: {bid_set & ask_set}")
        self.assertEqual(len(bid_set & global_set), 0,
                         f"Overlap bid/global: {bid_set & global_set}")
        self.assertEqual(len(ask_set & global_set), 0,
                         f"Overlap ask/global: {ask_set & global_set}")

    def test_feature_groups_cover_all(self) -> None:
        """All 44 canonical features must appear in exactly one group."""
        groups = get_feature_groups()
        all_grouped = set(groups["bid"]) | set(groups["ask"]) | set(groups["global"])

        for feat in self.ALL_44:
            self.assertIn(feat, all_grouped,
                          f"Feature '{feat}' not in any group")

    def test_feature_group_indices_original_39(self) -> None:
        """Index mapping with the original 39 features must cover all and not overlap."""
        idx = get_feature_group_indices(self.ORIGINAL_39)

        all_indices = idx["bid_idx"] + idx["ask_idx"] + idx["global_idx"]
        # Must cover every feature
        self.assertEqual(sorted(all_indices), list(range(len(self.ORIGINAL_39))))
        # No duplicates
        self.assertEqual(len(all_indices), len(set(all_indices)))

    def test_feature_group_indices_all_44(self) -> None:
        """Index mapping with all 44 features must cover all and not overlap."""
        idx = get_feature_group_indices(self.ALL_44)

        all_indices = idx["bid_idx"] + idx["ask_idx"] + idx["global_idx"]
        self.assertEqual(sorted(all_indices), list(range(len(self.ALL_44))))
        self.assertEqual(len(all_indices), len(set(all_indices)))

    def test_feature_group_indices_unknown_feature(self) -> None:
        """Unknown features should be assigned to global group."""
        names = ["bid_depth_L5", "some_mystery_feature", "log_return_1s"]
        idx = get_feature_group_indices(names)

        # mystery feature at index 1 should be in global
        self.assertIn(1, idx["global_idx"])
        # bid_depth_L5 at index 0 should be in bid
        self.assertIn(0, idx["bid_idx"])

    def test_spatial_encoder_with_semantic_groups(self) -> None:
        """SpatialLOBEncoder forward pass works after set_feature_groups with correct grouping."""
        torch.manual_seed(0)

        n_features = len(self.ORIGINAL_39)
        d_model = 64
        B, L = 4, 10

        model = SpatialLOBEncoder(n_features=n_features, d_model=d_model)

        # Apply semantic groups
        idx = get_feature_group_indices(self.ORIGINAL_39)
        model.set_feature_groups(
            bid_idx=idx["bid_idx"],
            ask_idx=idx["ask_idx"],
            global_idx=idx["global_idx"],
        )

        # Verify projection sizes match the semantic groups
        self.assertEqual(model.proj_bid.in_features, len(idx["bid_idx"]))
        self.assertEqual(model.proj_ask.in_features, len(idx["ask_idx"]))
        self.assertEqual(model.proj_global.in_features, len(idx["global_idx"]))

        # Forward pass must produce correct shape
        model.eval()
        x = torch.randn(B, L, n_features)
        with torch.no_grad():
            out = model(x)

        self.assertEqual(out.shape, (B, L, d_model))
        self.assertTrue(torch.isfinite(out).all(), "Non-finite values in output")


if __name__ == "__main__":
    unittest.main()

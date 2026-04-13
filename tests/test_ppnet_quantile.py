"""Tests for PPNet gate, MonotonicQuantileHead, and regime prior features."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest
import torch

from src.model.ppnet_gate import PPNetGate
from src.model.monotonic_quantile import MonotonicQuantileHead
from src.features.regime_features import (
    compute_regime_priors,
    compute_regime_priors_batch,
    compute_regime_priors_from_buffer,
    N_REGIME_PRIORS,
    REGIME_PRIOR_NAMES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_lob_df(n_rows: int, n_levels: int = 5, seed: int = 42) -> "pd.DataFrame":
    """Create a synthetic 1s LOB DataFrame for testing regime priors."""
    import pandas as pd

    rng = np.random.RandomState(seed)
    base_price = 50000.0

    # Microsecond timestamps, 1 second apart, starting at noon UTC
    start_ts = 12 * 3600 * 1_000_000  # noon UTC in microseconds
    timestamps = np.arange(start_ts, start_ts + n_rows * 1_000_000, 1_000_000)

    data = {"timestamp": timestamps}

    # Generate bid/ask prices with a small random walk
    mid_walk = base_price + np.cumsum(rng.randn(n_rows) * 0.5)

    for i in range(n_levels):
        spread_half = 0.5 + i * 0.3
        data[f"bids[{i}].price"] = mid_walk - spread_half
        data[f"asks[{i}].price"] = mid_walk + spread_half
        data[f"bids[{i}].amount"] = rng.exponential(1.0, n_rows).clip(0.01)
        data[f"asks[{i}].amount"] = rng.exponential(1.0, n_rows).clip(0.01)

    return pd.DataFrame(data)


# ====================================================================
# TestPPNetGate
# ====================================================================

class TestPPNetGate:
    """Tests for the PPNet regime gate module."""

    def test_gate_output_shape(self):
        """Gate output must have the same shape as the input hidden representation."""
        B, d_prior, d_hidden = 8, 6, 32
        gate = PPNetGate(d_prior=d_prior, d_hidden=d_hidden, dropout=0.0)
        gate.eval()

        h = torch.randn(B, d_hidden)
        prior = torch.randn(B, d_prior)

        with torch.no_grad():
            out = gate(h, prior)

        assert out.shape == (B, d_hidden), (
            f"Expected shape ({B}, {d_hidden}), got {tuple(out.shape)}"
        )

    def test_gate_range(self):
        """Gate scaling factors must be in [0, 2], so output magnitude is bounded."""
        torch.manual_seed(0)
        B, d_prior, d_hidden = 64, 6, 32
        gate = PPNetGate(d_prior=d_prior, d_hidden=d_hidden, dropout=0.0)
        gate.eval()

        h = torch.ones(B, d_hidden)  # unit input to isolate gate range
        prior = torch.randn(B, d_prior) * 10  # extreme priors

        with torch.no_grad():
            out = gate(h, prior)

        # Since h = 1 and gate in [0, 2], output should be in [0, 2]
        assert out.min() >= 0.0, f"Gate output below 0: {out.min()}"
        assert out.max() <= 2.0 + 1e-6, f"Gate output above 2: {out.max()}"

    def test_gate_no_prior_passthrough(self):
        """When prior is zeros, gate should produce values near 1 (passthrough).

        At initialization, the sigmoid output for zero input is 0.5,
        so gate = 0.5 * 2.0 = 1.0 (passthrough). We test that freshly
        initialized gate with zero prior gives output close to the input.
        """
        torch.manual_seed(123)
        B, d_prior, d_hidden = 16, 6, 32
        gate = PPNetGate(d_prior=d_prior, d_hidden=d_hidden, dropout=0.0)
        gate.eval()

        h = torch.randn(B, d_hidden)
        prior_zeros = torch.zeros(B, d_prior)

        with torch.no_grad():
            out = gate(h, prior_zeros)

        # The gate internal layers process zeros; because of random weight init,
        # the hidden output won't be exactly zero input to sigmoid. But the
        # architecture is designed so sigmoid(0) * 2 = 1.0 at the final layer.
        # We check the gate factors themselves via unit input.
        h_unit = torch.ones(B, d_hidden)
        with torch.no_grad():
            gate_factors = gate(h_unit, prior_zeros)

        # Gate factors should be centered around 1.0 (since sigmoid is centered at 0.5)
        # With random init, bias terms shift this, so we use a loose tolerance.
        mean_factor = gate_factors.mean().item()
        assert 0.5 < mean_factor < 1.5, (
            f"Mean gate factor for zero prior = {mean_factor}, expected near 1.0"
        )

    def test_gate_gradient_flow(self):
        """Gradients must flow through both h and prior inputs."""
        B, d_prior, d_hidden = 4, 6, 32
        gate = PPNetGate(d_prior=d_prior, d_hidden=d_hidden, dropout=0.0)

        h = torch.randn(B, d_hidden, requires_grad=True)
        prior = torch.randn(B, d_prior, requires_grad=True)

        out = gate(h, prior)
        loss = out.sum()
        loss.backward()

        assert h.grad is not None, "No gradient for h"
        assert prior.grad is not None, "No gradient for prior"
        assert h.grad.abs().sum() > 0, "Zero gradient for h"
        assert prior.grad.abs().sum() > 0, "Zero gradient for prior"

    def test_gate_different_priors_different_output(self):
        """Different regime priors must produce different gated outputs."""
        torch.manual_seed(0)
        B, d_prior, d_hidden = 4, 6, 32
        gate = PPNetGate(d_prior=d_prior, d_hidden=d_hidden, dropout=0.0)
        gate.eval()

        h = torch.randn(B, d_hidden)
        prior_a = torch.randn(B, d_prior)
        prior_b = torch.randn(B, d_prior) + 5.0  # shifted priors

        with torch.no_grad():
            out_a = gate(h, prior_a)
            out_b = gate(h, prior_b)

        diff = (out_a - out_b).abs().max().item()
        assert diff > 0.01, (
            f"Different priors produced nearly identical outputs (max diff={diff})"
        )


# ====================================================================
# TestMonotonicQuantile
# ====================================================================

class TestMonotonicQuantile:
    """Tests for the MonotonicQuantileHead module."""

    def test_quantile_ordering(self):
        """q10 < q50 < q90 must hold for ALL inputs (random + extreme)."""
        torch.manual_seed(42)
        head = MonotonicQuantileHead(d_input=32, d_hidden=16, dropout=0.0)
        head.eval()

        # Test with many random inputs
        for _ in range(20):
            h = torch.randn(64, 32) * 10  # varied magnitudes
            with torch.no_grad():
                out = head(h)

            q = out["quantiles"]  # (B, 3)
            q10, q50, q90 = q[:, 0], q[:, 1], q[:, 2]

            assert (q10 < q50).all(), (
                f"q10 >= q50 found: q10={q10}, q50={q50}"
            )
            assert (q50 < q90).all(), (
                f"q50 >= q90 found: q50={q50}, q90={q90}"
            )

    def test_quantile_ordering_extreme_inputs(self):
        """Monotonicity holds even for extreme input values."""
        torch.manual_seed(99)
        head = MonotonicQuantileHead(d_input=16, d_hidden=8, dropout=0.0)
        head.eval()

        # Extreme positive, negative, and zero inputs
        extremes = [
            torch.zeros(8, 16),
            torch.ones(8, 16) * 100,
            torch.ones(8, 16) * -100,
            torch.randn(8, 16) * 1000,
        ]

        for h in extremes:
            with torch.no_grad():
                out = head(h)

            q = out["quantiles"]
            assert (q[:, 0] < q[:, 1]).all(), "q10 >= q50 for extreme input"
            assert (q[:, 1] < q[:, 2]).all(), "q50 >= q90 for extreme input"

    def test_output_interface(self):
        """Output dict must contain 'quantiles' (B, 3) and 'point_pred' (B,)."""
        B, d_input = 8, 32
        head = MonotonicQuantileHead(d_input=d_input, d_hidden=16, dropout=0.0)
        head.eval()

        h = torch.randn(B, d_input)
        with torch.no_grad():
            out = head(h)

        assert "quantiles" in out, "Missing 'quantiles' key"
        assert "point_pred" in out, "Missing 'point_pred' key"
        assert out["quantiles"].shape == (B, 3), (
            f"Expected quantiles shape ({B}, 3), got {tuple(out['quantiles'].shape)}"
        )
        assert out["point_pred"].shape == (B,), (
            f"Expected point_pred shape ({B},), got {tuple(out['point_pred'].shape)}"
        )

    def test_point_pred_equals_q50(self):
        """point_pred must equal q50 (the median)."""
        head = MonotonicQuantileHead(d_input=32, d_hidden=16, dropout=0.0)
        head.eval()

        h = torch.randn(16, 32)
        with torch.no_grad():
            out = head(h)

        q50 = out["quantiles"][:, 1]
        diff = (out["point_pred"] - q50).abs().max().item()
        assert diff < 1e-6, f"point_pred != q50, max diff = {diff}"

    def test_gradient_flow(self):
        """Gradients must flow to both base_head and delta_head parameters."""
        head = MonotonicQuantileHead(d_input=32, d_hidden=16, dropout=0.0)

        h = torch.randn(8, 32, requires_grad=True)
        out = head(h)

        # Loss that uses all three quantiles
        loss = out["quantiles"].sum() + out["point_pred"].sum()
        loss.backward()

        assert h.grad is not None, "No gradient for input h"
        assert h.grad.abs().sum() > 0, "Zero gradient for input h"

        # Check that both sub-heads have non-zero gradients
        base_grad_sum = sum(
            p.grad.abs().sum().item()
            for p in head.base_head.parameters()
            if p.grad is not None
        )
        delta_grad_sum = sum(
            p.grad.abs().sum().item()
            for p in head.delta_head.parameters()
            if p.grad is not None
        )

        assert base_grad_sum > 0, "No gradient flow to base_head"
        assert delta_grad_sum > 0, "No gradient flow to delta_head"

    def test_all_outputs_finite(self):
        """All outputs must be finite (no NaN or inf)."""
        torch.manual_seed(7)
        head = MonotonicQuantileHead(d_input=32, d_hidden=16, dropout=0.0)
        head.eval()

        h = torch.randn(32, 32) * 5
        with torch.no_grad():
            out = head(h)

        assert torch.isfinite(out["quantiles"]).all(), "Non-finite quantiles"
        assert torch.isfinite(out["point_pred"]).all(), "Non-finite point_pred"


# ====================================================================
# TestRegimePriors
# ====================================================================

class TestRegimePriors:
    """Tests for regime prior feature computation."""

    def test_compute_regime_priors_shape(self):
        """Output must be a 6-dim float32 vector."""
        import pandas as pd
        df = _make_lob_df(n_rows=100, n_levels=5)
        result = compute_regime_priors(df, current_idx=99)

        assert result.shape == (N_REGIME_PRIORS,), (
            f"Expected shape ({N_REGIME_PRIORS},), got {result.shape}"
        )
        assert result.dtype == np.float32, f"Expected float32, got {result.dtype}"
        assert len(REGIME_PRIOR_NAMES) == N_REGIME_PRIORS

    def test_regime_priors_no_nan(self):
        """Output must contain no NaN or inf values."""
        df = _make_lob_df(n_rows=200, n_levels=5)
        result = compute_regime_priors(df, current_idx=199)

        assert np.all(np.isfinite(result)), f"Non-finite values in output: {result}"

    def test_regime_priors_causal(self):
        """Modifying data AFTER current_idx must NOT change the output."""
        df = _make_lob_df(n_rows=200, n_levels=5)

        idx = 100
        result_orig = compute_regime_priors(df, current_idx=idx)

        # Modify data after idx
        df_modified = df.copy()
        for i in range(5):
            df_modified.loc[idx + 1:, f"bids[{i}].price"] = 99999.0
            df_modified.loc[idx + 1:, f"asks[{i}].price"] = 99999.0
            df_modified.loc[idx + 1:, f"bids[{i}].amount"] = 99999.0
            df_modified.loc[idx + 1:, f"asks[{i}].amount"] = 99999.0

        result_modified = compute_regime_priors(df_modified, current_idx=idx)

        np.testing.assert_array_equal(
            result_orig, result_modified,
            err_msg="Regime priors changed when future data was modified (causality violation)"
        )

    def test_regime_priors_different_regimes(self):
        """Different market states should produce different prior vectors."""
        # Regime A: low volatility, balanced book
        df_a = _make_lob_df(n_rows=100, n_levels=5, seed=1)

        # Regime B: high volatility, imbalanced book
        df_b = _make_lob_df(n_rows=100, n_levels=5, seed=2)
        # Amplify volatility and skew the book
        for i in range(5):
            df_b[f"bids[{i}].price"] += np.cumsum(np.random.randn(100) * 5)
            df_b[f"asks[{i}].price"] += np.cumsum(np.random.randn(100) * 5)
            df_b[f"bids[{i}].amount"] *= 3.0

        result_a = compute_regime_priors(df_a, current_idx=99)
        result_b = compute_regime_priors(df_b, current_idx=99)

        diff = np.abs(result_a - result_b).max()
        assert diff > 0.01, (
            f"Different regimes produced nearly identical priors (max diff={diff})"
        )

    def test_regime_priors_batch(self):
        """Batch computation must match individual computation."""
        df = _make_lob_df(n_rows=200, n_levels=5)
        indices = np.array([50, 100, 150, 199])

        batch_result = compute_regime_priors_batch(df, indices)

        assert batch_result.shape == (4, N_REGIME_PRIORS)

        for i, idx in enumerate(indices):
            individual = compute_regime_priors(df, current_idx=int(idx))
            np.testing.assert_array_almost_equal(
                batch_result[i], individual, decimal=5,
                err_msg=f"Batch result mismatch at index {idx}"
            )

    def test_regime_priors_short_window(self):
        """Must work gracefully with fewer rows than lookback."""
        df = _make_lob_df(n_rows=10, n_levels=5)
        result = compute_regime_priors(df, current_idx=9, lookback=3600)

        assert result.shape == (N_REGIME_PRIORS,)
        assert np.all(np.isfinite(result))

    def test_regime_priors_minimal_rows(self):
        """Must work with a single row."""
        df = _make_lob_df(n_rows=1, n_levels=5)
        result = compute_regime_priors(df, current_idx=0)

        assert result.shape == (N_REGIME_PRIORS,)
        assert np.all(np.isfinite(result))

    def test_regime_priors_with_streaming(self):
        """Streaming buffer interface must produce same results as DataFrame interface."""
        df = _make_lob_df(n_rows=200, n_levels=5)

        # Extract arrays as streaming would
        timestamps = df["timestamp"].values
        bid0 = df["bids[0].price"].values
        ask0 = df["asks[0].price"].values
        bid_amt_l5 = np.column_stack([
            df[f"bids[{i}].amount"].values for i in range(5)
        ])
        ask_amt_l5 = np.column_stack([
            df[f"asks[{i}].amount"].values for i in range(5)
        ])

        stream_result = compute_regime_priors_from_buffer(
            timestamps, bid0, ask0, bid_amt_l5, ask_amt_l5, lookback=200
        )

        df_result = compute_regime_priors(df, current_idx=199, lookback=200)

        np.testing.assert_array_almost_equal(
            stream_result, df_result, decimal=5,
            err_msg="Streaming and DataFrame results differ"
        )

    def test_hour_encoding_varies(self):
        """Hour-of-day encoding must change with time of day."""
        import pandas as pd

        results = []
        for hour in [0, 6, 12, 18]:
            ts_base = hour * 3600 * 1_000_000
            df = _make_lob_df(n_rows=10, n_levels=5)
            df["timestamp"] = np.arange(
                ts_base, ts_base + 10 * 1_000_000, 1_000_000
            )
            result = compute_regime_priors(df, current_idx=9)
            results.append(result)

        # hour_sin (index 2) and hour_cos (index 3) should differ across hours
        sin_values = [r[2] for r in results]
        cos_values = [r[3] for r in results]

        # Not all the same
        assert len(set(round(v, 4) for v in sin_values)) > 1, (
            f"hour_sin does not vary: {sin_values}"
        )
        assert len(set(round(v, 4) for v in cos_values)) > 1, (
            f"hour_cos does not vary: {cos_values}"
        )


# ====================================================================
# TestIntegration
# ====================================================================

class TestIntegration:
    """Integration tests for PPNet + MonotonicQuantile in DualPathLOBModelV2."""

    def _try_import_v2(self):
        """Try to import DualPathLOBModelV2. Skip test if dependencies missing."""
        try:
            from src.model.dual_path_model import DualPathLOBModelV2
            return DualPathLOBModelV2
        except ImportError as e:
            pytest.skip(f"DualPathLOBModelV2 dependency not available: {e}")

    def test_v2_forward_with_regime_prior(self):
        """V2 model forward pass with regime_prior produces valid output."""
        DualPathLOBModelV2 = self._try_import_v2()

        torch.manual_seed(0)
        B, L, n_feat, n_levels, d_model = 4, 20, 44, 20, 32

        model = DualPathLOBModelV2(
            n_features=n_feat,
            n_levels=n_levels,
            d_model=d_model,
            d_raw=16,
            d_prior=6,
            dropout=0.0,
            use_monotonic_quantile=True,
        )
        model.eval()

        x_feat = torch.randn(B, L, n_feat)
        x_raw = torch.randn(B, L, n_levels, 4)
        regime_prior = torch.randn(B, 6)

        with torch.no_grad():
            out = model(x_feat, x_raw=x_raw, regime_prior=regime_prior)

        # Check output structure
        assert "quantiles" in out
        assert "point_pred" in out
        assert out["quantiles"].shape == (B, 3)
        assert out["point_pred"].shape == (B,)

        # Monotonic ordering
        q = out["quantiles"]
        assert (q[:, 0] < q[:, 1]).all(), "q10 >= q50 in V2 model"
        assert (q[:, 1] < q[:, 2]).all(), "q50 >= q90 in V2 model"

    def test_v2_forward_without_regime_prior(self):
        """V2 model forward pass without regime_prior still works (gate bypassed)."""
        DualPathLOBModelV2 = self._try_import_v2()

        torch.manual_seed(0)
        B, L, n_feat = 4, 20, 44

        model = DualPathLOBModelV2(
            n_features=n_feat,
            d_model=32,
            d_prior=6,
            dropout=0.0,
            use_monotonic_quantile=True,
        )
        model.eval()

        x_feat = torch.randn(B, L, n_feat)

        with torch.no_grad():
            out = model(x_feat, regime_prior=None)

        assert out["quantiles"].shape == (B, 3)
        assert (out["quantiles"][:, 0] < out["quantiles"][:, 1]).all()

    def test_v2_no_ppnet_gate(self):
        """V2 with d_prior=0 disables PPNet gate entirely."""
        DualPathLOBModelV2 = self._try_import_v2()

        model = DualPathLOBModelV2(
            n_features=44,
            d_model=32,
            d_prior=0,
            dropout=0.0,
            use_monotonic_quantile=True,
        )

        assert model.ppnet_gate is None, "PPNet gate should be None when d_prior=0"

    def test_v2_simple_quantile_fallback(self):
        """V2 with use_monotonic_quantile=False uses simple linear head."""
        DualPathLOBModelV2 = self._try_import_v2()

        torch.manual_seed(0)
        B, L, n_feat = 4, 20, 44

        model = DualPathLOBModelV2(
            n_features=n_feat,
            d_model=32,
            d_prior=0,
            dropout=0.0,
            use_monotonic_quantile=False,
        )
        model.eval()

        x_feat = torch.randn(B, L, n_feat)
        with torch.no_grad():
            out = model(x_feat)

        assert out["quantiles"].shape == (B, 3)
        assert out["point_pred"].shape == (B,)

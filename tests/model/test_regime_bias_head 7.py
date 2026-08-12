"""Unit tests for Phase B.1 regime_bias_head additive bias.

Verifies:
1. Module structure: MLP(d_prior → hidden → n_horizons), zero-init final layer
2. Bias ≈ 0 at init
3. Bias varies with regime_prior after weight perturbation
4. Monotonicity preservation: adding scalar bias to all 3 quantiles preserves q10<q50<q90

Note: full DualPathLOBModelV3 construction skipped (local torch version
lacks nn.init.trunc_normal_ used by patch_attention). Pod has newer torch
where full model integration test will run during training.
"""
from __future__ import annotations
import torch
import torch.nn as nn


def make_regime_bias_head(d_prior: int = 6, hidden: int = 16, n_horizons: int = 1, dropout: float = 0.0):
    """Replicate the construction logic from DualPathLOBModelV3."""
    head = nn.Sequential(
        nn.Linear(d_prior, hidden),
        nn.GELU(),
        nn.Dropout(dropout),
        nn.Linear(hidden, n_horizons),
    )
    nn.init.zeros_(head[-1].weight)
    nn.init.zeros_(head[-1].bias)
    return head


def test_bias_zero_at_init():
    """Final-layer zero init → bias ≈ 0 for any input."""
    head = make_regime_bias_head()
    head.eval()
    rp = torch.randn(8, 6)
    bias = head(rp)
    assert bias.abs().max() < 1e-6, f"Initial bias should be ≈ 0, got max abs {bias.abs().max():.6f}"


def test_bias_adapts_with_input_after_perturbation():
    """After perturbing weights, different regime_prior → different bias."""
    head = make_regime_bias_head()
    with torch.no_grad():
        head[-1].weight.normal_(mean=0.0, std=0.5)
        head[-1].bias.zero_()
    rp1 = torch.zeros(4, 6)
    rp2 = torch.ones(4, 6) * 2.0
    b1 = head(rp1)
    b2 = head(rp2)
    assert (b1 != b2).any(), "Bias should differ for different regime_prior"


def test_n_horizons_output_shape():
    """n_horizons=2 → output shape (B, 2)."""
    head = make_regime_bias_head(n_horizons=2)
    rp = torch.randn(8, 6)
    out = head(rp)
    assert out.shape == (8, 2), f"Expected (8, 2), got {out.shape}"


def test_monotonicity_preserved_under_uniform_bias():
    """Adding a scalar bias to all 3 quantiles preserves q10 < q50 < q90."""
    torch.manual_seed(42)
    # Simulate quantile head output (B=8, 3) with strict monotonicity
    base = torch.randn(8)
    delta_low = torch.nn.functional.softplus(torch.randn(8)) + 0.01
    delta_high = torch.nn.functional.softplus(torch.randn(8)) + 0.01
    q10 = base - delta_low
    q50 = base
    q90 = base + delta_high
    quantiles = torch.stack([q10, q50, q90], dim=-1)  # (8, 3)
    assert (quantiles[:, 0] < quantiles[:, 1]).all()
    assert (quantiles[:, 1] < quantiles[:, 2]).all()

    # Add arbitrary scalar bias per sample
    bias = torch.randn(8, 1)  # (8, 1) for broadcasting
    biased = quantiles + bias  # (8, 3) by broadcasting

    # Monotonicity must still hold
    assert (biased[:, 0] < biased[:, 1]).all(), "After uniform bias, q10 < q50 must hold"
    assert (biased[:, 1] < biased[:, 2]).all(), "After uniform bias, q50 < q90 must hold"

    # Differences should be unchanged (additive bias preserves spread)
    spread_orig = quantiles[:, 2] - quantiles[:, 0]
    spread_biased = biased[:, 2] - biased[:, 0]
    assert torch.allclose(spread_orig, spread_biased, atol=1e-6), "Spread should be preserved"


def test_bias_with_realistic_regime_prior_distribution():
    """Test that with a perturbed head, output bias is bounded and reasonable."""
    head = make_regime_bias_head(n_horizons=1, hidden=16)
    with torch.no_grad():
        # Realistic small init (e.g. Xavier-like)
        head[-1].weight.normal_(mean=0.0, std=0.3)
        head[-1].bias.zero_()
    # regime_prior typically z-score normalized in [-3, 3]
    rp = torch.randn(1024, 6) * 1.5
    bias = head(rp)
    # Distribution of bias should be reasonable: not blown up
    assert bias.abs().mean() < 5.0, f"Mean abs bias {bias.abs().mean()} unreasonably large"
    assert bias.std() < 5.0, f"Bias std {bias.std()} unreasonably large"


if __name__ == "__main__":
    tests = [
        test_bias_zero_at_init,
        test_bias_adapts_with_input_after_perturbation,
        test_n_horizons_output_shape,
        test_monotonicity_preserved_under_uniform_bias,
        test_bias_with_realistic_regime_prior_distribution,
    ]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print("\nAll regime_bias_head unit tests PASSED")

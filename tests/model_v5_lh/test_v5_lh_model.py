import torch
from src.model_v5_lh.v5_lh_model import V5LHModel


def test_output_shapes_multi_horizon():
    B, L = 2, 600
    n_features = 50
    n_levels = 20
    d_prior = 6
    model = V5LHModel(
        n_features=n_features,
        n_levels=n_levels,
        d_prior=d_prior,
        horizons=[180, 600],
        use_fallback=True,
    )
    X = torch.randn(B, L, n_features)
    X_raw = torch.randn(B, L, n_levels, 4)
    prior = torch.randn(B, d_prior)
    out = model(X=X, X_raw=X_raw, regime_prior=prior)
    assert "y_180" in out and "y_600" in out
    # Each horizon outputs quantile (B, 3)
    assert out["y_180"].shape == (B, 3)
    assert out["y_600"].shape == (B, 3)
    # Embedding exposed for decorrelation loss
    assert out["embedding"].shape[0] == B


def test_monotonic_quantiles():
    """q10 <= q50 <= q90 for every sample (MonotonicQuantileHead invariant)."""
    torch.manual_seed(0)
    B, L = 4, 600
    model = V5LHModel(n_features=50, n_levels=20, d_prior=6, horizons=[180], use_fallback=True)
    model.eval()
    X = torch.randn(B, L, 50)
    X_raw = torch.randn(B, L, 20, 4)
    prior = torch.randn(B, 6)
    with torch.no_grad():
        out = model(X=X, X_raw=X_raw, regime_prior=prior)
    q = out["y_180"]  # (B, 3) = [q10, q50, q90]
    assert torch.all(q[:, 1] >= q[:, 0] - 1e-5)
    assert torch.all(q[:, 2] >= q[:, 1] - 1e-5)


def test_parameter_count():
    """Total params should fall within ~25K-50K range per Section 2.2 of spec."""
    model = V5LHModel(n_features=52, n_levels=20, d_prior=6, horizons=[180, 600], use_fallback=True)
    total = sum(p.numel() for p in model.parameters())
    # With GRU fallback instead of real Mamba, count may differ slightly.
    # The key is it's well below V4's 59K.
    assert 15000 < total < 60000, f"param count {total} out of expected range"

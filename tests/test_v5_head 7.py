"""Unit tests for HeteroscedasticHead."""
import torch


def test_head_output_shapes():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    head = HeteroscedasticHead(d_emb=32, n_horizons=1, hidden=0)
    emb = torch.randn(4, 32)
    out = head(emb)
    assert "mu" in out and "log_sigma" in out and "y_pred" in out
    assert out["mu"].shape == (4, 1)
    assert out["log_sigma"].shape == (4, 1)
    assert torch.allclose(out["y_pred"], out["mu"])


def test_head_initial_log_sigma_reasonable():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    torch.manual_seed(0)
    head = HeteroscedasticHead(d_emb=32, n_horizons=1, hidden=0)
    emb = torch.randn(100, 32)
    with torch.no_grad():
        out = head(emb)
    sigma = torch.exp(out["log_sigma"])
    assert 0.3 < sigma.mean().item() < 3.0


def test_head_with_hidden_bottleneck():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    head = HeteroscedasticHead(d_emb=32, n_horizons=1, hidden=16, dropout=0.1)
    emb = torch.randn(4, 32)
    out = head(emb)
    assert out["mu"].shape == (4, 1)


def test_head_backward_stable():
    from src.training.v5_losses.heteroscedastic_head import HeteroscedasticHead
    head = HeteroscedasticHead(d_emb=8, n_horizons=1, hidden=0)
    emb = torch.randn(4, 8) * 100
    out = head(emb)
    loss = out["mu"].sum() + out["log_sigma"].sum()
    loss.backward()
    for p in head.parameters():
        assert torch.isfinite(p.grad).all()

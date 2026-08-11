"""Unit tests for V5 Huber loss on raw y."""
import torch


def test_huber_zero_at_perfect():
    from src.training.v5_losses.huber_components import loss_huber_y
    y = torch.tensor([0.0, 1.0, -1.0, 2.5])
    mu = y.clone()
    mask = torch.ones_like(y).bool()
    loss = loss_huber_y(mu, y, mask, delta=1.0)
    assert abs(loss.item()) < 1e-6


def test_huber_quadratic_in_inner_region():
    """For |y-μ| < δ, loss = 0.5·(y-μ)² (quadratic)."""
    from src.training.v5_losses.huber_components import loss_huber_y
    y = torch.tensor([0.0])
    mu = torch.tensor([0.5])  # diff = 0.5, δ = 1.0 → inner region
    mask = torch.ones_like(y).bool()
    loss = loss_huber_y(mu, y, mask, delta=1.0)
    expected = 0.5 * 0.5 ** 2
    assert abs(loss.item() - expected) < 1e-6


def test_huber_linear_in_outer_region():
    """For |y-μ| > δ, loss = δ·(|y-μ| - 0.5δ) (linear)."""
    from src.training.v5_losses.huber_components import loss_huber_y
    y = torch.tensor([0.0])
    mu = torch.tensor([3.0])  # diff = 3, δ = 1.0 → outer region
    mask = torch.ones_like(y).bool()
    loss = loss_huber_y(mu, y, mask, delta=1.0)
    expected = 1.0 * (3.0 - 0.5)
    assert abs(loss.item() - expected) < 1e-6


def test_huber_robust_to_outlier_vs_mse():
    """Huber loss should be smaller than MSE for extreme outliers (key property)."""
    from src.training.v5_losses.huber_components import loss_huber_y
    y = torch.tensor([0.0, 0.0, 0.0, 0.0, 100.0])  # one extreme outlier
    mu = torch.zeros_like(y)
    mask = torch.ones_like(y).bool()
    huber_loss = loss_huber_y(mu, y, mask, delta=1.0).item()
    mse_loss = ((y - mu) ** 2).mean().item()
    assert huber_loss < mse_loss / 2  # Huber bounds outlier impact


def test_huber_mask_handling():
    from src.training.v5_losses.huber_components import loss_huber_y
    y = torch.tensor([1e10, 0.0, 0.0, 1.0])
    mu = torch.zeros_like(y)
    mask = torch.tensor([False, True, True, True])
    loss = loss_huber_y(mu, y, mask, delta=1.0)
    # Only y=0,0,1 contribute; (0-0)² + (0-0)² + (0.5·1²) avg
    # = (0 + 0 + 0.5) / 3
    expected = 0.5 / 3
    assert abs(loss.item() - expected) < 1e-5

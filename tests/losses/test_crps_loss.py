import torch
from src.losses.crps_loss import crps_quantile_loss


def test_crps_perfect_prediction_is_zero():
    """When q10 = q50 = q90 = y, CRPS should be ~0."""
    y = torch.tensor([1.0, 2.0, -0.5])
    quantiles = torch.stack([y, y, y], dim=-1)  # (N, 3)
    loss = crps_quantile_loss(quantiles, y, taus=(0.1, 0.5, 0.9))
    assert loss.item() < 1e-4


def test_crps_is_positive_for_miscalibrated():
    """CRPS must be > 0 when quantiles are off."""
    y = torch.tensor([1.0])
    quantiles = torch.tensor([[-1.0, 0.0, 1.0]])  # q10, q50, q90 all below or at y
    loss = crps_quantile_loss(quantiles, y, taus=(0.1, 0.5, 0.9))
    assert loss.item() > 0.1


def test_crps_is_differentiable():
    """Gradient should flow back to quantile predictions."""
    y = torch.tensor([0.5])
    quantiles = torch.tensor([[-1.0, 0.0, 1.0]], requires_grad=True)
    loss = crps_quantile_loss(quantiles, y, taus=(0.1, 0.5, 0.9))
    loss.backward()
    assert quantiles.grad is not None
    assert quantiles.grad.abs().sum().item() > 0

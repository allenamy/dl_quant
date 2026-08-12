import torch
from src.losses.focal_weighting import tail_focal_weights


def test_weights_are_1_for_body():
    """Samples with |y| < 2σ get weight 1.0."""
    y = torch.tensor([0.0, 0.5, 1.0, 1.9])
    sigma = 1.0
    w = tail_focal_weights(y, sigma, extra_weight=2.0)
    assert torch.allclose(w, torch.tensor([1.0, 1.0, 1.0, 1.0]))


def test_weights_are_3_for_tails():
    """Samples with |y| > 2σ get weight 1 + extra_weight."""
    y = torch.tensor([-3.0, 2.5, -2.1])
    sigma = 1.0
    w = tail_focal_weights(y, sigma, extra_weight=2.0)
    assert torch.allclose(w, torch.tensor([3.0, 3.0, 3.0]))


def test_weights_broadcast_correctly():
    """Shape (N,) input gives shape (N,) output."""
    y = torch.randn(100)
    w = tail_focal_weights(y, 1.0, 2.0)
    assert w.shape == y.shape

"""Cross-sectional IC loss tests.

Single-symbol case must return zero (no-op contract). Multi-symbol case
must return a finite scalar in [0, 2]. Perfect prediction → 0.
"""
import torch

from src.losses.cross_sectional_ic_loss import cross_sectional_ic_loss


def test_single_symbol_returns_zero_2d():
    """Single symbol per timestep, 2D shape (T, 1) → no-op."""
    pred = torch.randn(100, 1)
    target = torch.randn(100, 1)
    mask = torch.ones(100, 1)
    loss = cross_sectional_ic_loss(pred, target, mask)
    assert loss.item() == 0.0


def test_single_symbol_returns_zero_3d():
    """Single symbol with explicit horizon dim, (T, 1, H) → no-op."""
    pred = torch.randn(100, 1, 3)
    target = torch.randn(100, 1, 3)
    mask = torch.ones(100, 1, 3)
    loss = cross_sectional_ic_loss(pred, target, mask)
    assert loss.item() == 0.0


def test_multi_symbol_finite_in_unit_range():
    """When S>=2, returns a finite scalar (in practice in [0, 2])."""
    torch.manual_seed(0)
    pred = torch.randn(100, 5)
    target = torch.randn(100, 5)
    mask = torch.ones(100, 5)
    loss = cross_sectional_ic_loss(pred, target, mask)
    assert torch.isfinite(loss)
    assert 0.0 <= loss.item() <= 2.0


def test_perfect_correlation_gives_zero():
    """If pred == target, cross-sectional IC = 1, loss = 1 - 1 = 0."""
    torch.manual_seed(0)
    target = torch.randn(50, 4)
    loss = cross_sectional_ic_loss(target.clone(), target, torch.ones(50, 4))
    assert loss.item() < 1e-4


def test_negative_correlation_gives_two():
    """If pred = -target, cross-sectional IC = -1, loss = 1 - (-1) = 2."""
    torch.manual_seed(0)
    target = torch.randn(50, 4)
    loss = cross_sectional_ic_loss(-target, target, torch.ones(50, 4))
    assert loss.item() == 2.0 or abs(loss.item() - 2.0) < 1e-4


def test_mask_excludes_invalid_symbols():
    """Symbols with mask=0 should be excluded from the per-timestep IC."""
    torch.manual_seed(0)
    T, S = 10, 4
    pred = torch.randn(T, S)
    target = torch.randn(T, S)
    mask = torch.ones(T, S)
    # Mask out half the symbols at every timestep
    mask[:, S // 2:] = 0
    loss = cross_sectional_ic_loss(pred, target, mask)
    assert torch.isfinite(loss)


def test_gradient_flows():
    """Backward must propagate through the IC loss."""
    torch.manual_seed(0)
    pred = torch.randn(100, 5, requires_grad=True)
    target = torch.randn(100, 5)
    mask = torch.ones(100, 5)
    loss = cross_sectional_ic_loss(pred, target, mask)
    loss.backward()
    assert pred.grad is not None
    assert torch.isfinite(pred.grad).all()

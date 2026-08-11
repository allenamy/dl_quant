"""Unit tests for V5 Gaussian NLL component."""
import math
import torch


def test_gaussian_nll_perfect_prediction():
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([0.0, 1.0, -1.0, 2.5])
    mu = y.clone()
    log_sigma = torch.zeros_like(y)
    mask = torch.ones_like(y).bool()
    loss = loss_gaussian_nll(mu, log_sigma, y, mask)
    expected = 0.5 * math.log(2 * math.pi)
    assert abs(loss.item() - expected) < 1e-5


def test_gaussian_nll_high_confidence_penalizes_error():
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1.0])
    mu = torch.tensor([0.0])
    mask = torch.ones_like(y).bool()
    loss_high_conf = loss_gaussian_nll(mu, torch.tensor([-2.0]), y, mask)
    loss_low_conf = loss_gaussian_nll(mu, torch.tensor([2.0]), y, mask)
    assert loss_high_conf.item() > loss_low_conf.item()


def test_gaussian_nll_mask_handling():
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1e10, 0.0, -1e10, 1.0])
    mu = torch.zeros_like(y)
    log_sigma = torch.zeros_like(y)
    mask = torch.tensor([False, True, False, True])
    loss = loss_gaussian_nll(mu, log_sigma, y, mask)
    expected = 0.25 + 0.5 * math.log(2 * math.pi)
    assert abs(loss.item() - expected) < 1e-5


def test_gaussian_nll_log_sigma_clip():
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1.0])
    mu = torch.tensor([0.0])
    mask = torch.ones_like(y).bool()
    extreme_log_sigma = torch.tensor([-100.0], requires_grad=True)
    loss = loss_gaussian_nll(mu, extreme_log_sigma, y, mask, log_sigma_min=-7.0, log_sigma_max=2.0)
    assert torch.isfinite(loss).all()
    loss.backward()
    assert torch.isfinite(extreme_log_sigma.grad).all()


def test_gaussian_nll_no_valid_returns_zero_with_grad():
    from src.training.v5_losses.heteroscedastic_components import loss_gaussian_nll
    y = torch.tensor([1.0, 2.0])
    mu = torch.tensor([0.5, 0.5], requires_grad=True)
    log_sigma = torch.zeros_like(y)
    mask = torch.zeros_like(y).bool()
    loss = loss_gaussian_nll(mu, log_sigma, y, mask)
    assert loss.item() == 0.0
    loss.backward()
    assert mu.grad is not None

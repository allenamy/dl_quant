import torch
from src.losses.dul_plus_loss import DulPlusLoss


def test_full_loss_is_scalar():
    torch.manual_seed(0)
    loss_fn = DulPlusLoss(n_horizons=2, y_sigmas=(1.0, 1.5))
    q1 = torch.randn(10, 3, requires_grad=True)  # quantiles horizon 0
    q2 = torch.randn(10, 3, requires_grad=True)  # horizon 1
    y1 = torch.randn(10)
    y2 = torch.randn(10)
    emb = torch.randn(10, 32)
    loss = loss_fn([q1, q2], [y1, y2], embedding=emb)
    assert loss.dim() == 0
    loss.backward()
    assert q1.grad is not None and q2.grad is not None


def test_focal_increases_tail_contribution():
    """Loss on tail-heavy batch > loss on body-only batch (same mean q)."""
    loss_fn = DulPlusLoss(n_horizons=1, y_sigmas=(1.0,), focal_weight=5.0)
    q = torch.zeros(100, 3)  # flat median=0 predictions
    y_body = torch.randn(100) * 0.5  # small y
    y_tail = torch.randn(100) * 3.0  # large y
    loss_body = loss_fn([q], [y_body])
    loss_tail = loss_fn([q], [y_tail])
    assert loss_tail.item() > loss_body.item() * 3

import torch
from src.losses.unit_loss import UnitMultiTaskLoss


def test_unit_combines_two_tasks():
    """Wrapping two losses; forward produces weighted scalar + stores log_vars."""
    loss_fn = UnitMultiTaskLoss(n_tasks=2, init_log_var=0.0)
    l1 = torch.tensor(1.0)
    l2 = torch.tensor(2.0)
    combined = loss_fn([l1, l2])
    # At log_var=0, weights = 0.5 for each, + log(sigma) = 0
    assert combined.item() > 0
    # Check log_vars are learnable params
    assert loss_fn.log_vars.requires_grad


def test_unit_backprop_adjusts_log_vars():
    """After backprop on imbalanced tasks, uncertain task should increase log_var."""
    torch.manual_seed(0)
    loss_fn = UnitMultiTaskLoss(n_tasks=2)
    opt = torch.optim.SGD(loss_fn.parameters(), lr=0.1)
    for _ in range(50):
        l1 = torch.tensor(0.01, requires_grad=True)  # easy task
        l2 = torch.tensor(5.0, requires_grad=True)   # hard task
        loss = loss_fn([l1, l2])
        opt.zero_grad()
        loss.backward()
        opt.step()
    # Task 2 (harder) should have higher log_var
    assert loss_fn.log_vars[1].item() > loss_fn.log_vars[0].item()

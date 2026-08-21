"""Multi-task uncertainty weighting (Kendall, Gal, Cipolla 2018).

L_total = Σ_i [ (1 / (2 σ_i²)) · L_i + log(σ_i) ]

We parameterize log(σ_i²) directly (log_var) for stability. When a task is
uncertain, σ grows → its loss is down-weighted.

IMPORTANT FOR CALLERS: `log_vars` are nn.Parameter tensors. The optimizer MUST
be given `list(model.parameters()) + list(loss_fn.parameters())` — otherwise
log_vars stay frozen at their init value and multi-task weighting is a no-op.
"""
from typing import List
import torch
import torch.nn as nn


class UnitMultiTaskLoss(nn.Module):
    def __init__(self, n_tasks: int, init_log_var: float = 0.0):
        super().__init__()
        self.n_tasks = n_tasks
        # log(σ²), learnable
        self.log_vars = nn.Parameter(torch.full((n_tasks,), float(init_log_var)))

    def forward(self, task_losses: List[torch.Tensor]) -> torch.Tensor:
        assert len(task_losses) == self.n_tasks, (
            f"expected {self.n_tasks} task losses, got {len(task_losses)}"
        )
        # Clamp to prevent runaway: precision = exp(-log_var) blows up if log_var is very negative.
        log_vars = torch.clamp(self.log_vars, min=-5.0, max=5.0)
        total = torch.zeros((), dtype=log_vars.dtype, device=log_vars.device)
        for i, l_i in enumerate(task_losses):
            precision = torch.exp(-log_vars[i])  # 1 / σ²
            total = total + 0.5 * precision * l_i + 0.5 * log_vars[i]
        return total

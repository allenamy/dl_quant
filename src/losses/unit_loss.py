"""Multi-task uncertainty weighting (Kendall, Gal, Cipolla 2018).

L_total = Σ_i [ (1 / (2 σ_i²)) · L_i + log(σ_i) ]

We parameterize log(σ_i²) directly (log_var) for stability.
When a task is uncertain, σ grows → its loss is down-weighted.
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
        total = 0.0
        for i, l_i in enumerate(task_losses):
            precision = torch.exp(-self.log_vars[i])  # 1 / σ²
            total = total + 0.5 * precision * l_i + 0.5 * self.log_vars[i]
        return total

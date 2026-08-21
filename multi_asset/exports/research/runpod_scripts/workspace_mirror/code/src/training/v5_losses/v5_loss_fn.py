"""Factory: build a loss_fn compatible with train_one_fold_v2.

train_one_fold_v2 expects: loss_fn(outputs_dict, target) -> scalar tensor

V5LossAssembly expects: assembly(head_out, y, mask) -> {'total': ...}
"""
from __future__ import annotations
from typing import Callable, Dict
import torch

from .loss_assembly import V5LossAssembly, V5LossConfig


def build_v5_loss_fn(loss_cfg_dict: dict) -> Callable[[Dict[str, torch.Tensor], torch.Tensor], torch.Tensor]:
    cfg = V5LossConfig(**loss_cfg_dict)
    assembly = V5LossAssembly(cfg)

    def _loss_fn(outputs: Dict[str, torch.Tensor], target: torch.Tensor) -> torch.Tensor:
        mask = outputs.get("mask")
        if mask is None:
            mask = torch.isfinite(target)
        out = assembly(outputs, target, mask)
        return out["total"]

    return _loss_fn

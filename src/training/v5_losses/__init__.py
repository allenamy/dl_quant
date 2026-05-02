"""V5 loss exploration — independent module, does NOT touch V4 production.

See docs/superpowers/specs/2026-05-01-v5-loss-design.md for design.

Components:
  - vol_adaptive: σ_local rolling computation (numpy, offline-deterministic)
  - dual_head:    DualHead nn.Module (direction × magnitude)
  - components:   loss functions (dir_margin, mag_huber, joint_mse, cs_ic)
  - heteroscedastic_components: Gaussian NLL loss
  - huber_components: Huber-on-raw-y loss
  - loss_assembly: config-driven loss combiner
"""
from .vol_adaptive import compute_sigma_local_mad, compute_sigma_local_ewma
from .dual_head import DualHead
from .components import (
    loss_dir_margin,
    loss_mag_huber,
    loss_joint_mse,
    loss_cs_ic,
)
from .heteroscedastic_components import loss_gaussian_nll
from .huber_components import loss_huber_y
from .loss_assembly import V5LossAssembly, V5LossConfig
from .v5_loss_fn import build_v5_loss_fn

__all__ = [
    "compute_sigma_local_mad",
    "compute_sigma_local_ewma",
    "DualHead",
    "loss_dir_margin",
    "loss_mag_huber",
    "loss_joint_mse",
    "loss_cs_ic",
    "loss_gaussian_nll",
    "loss_huber_y",
    "V5LossAssembly",
    "V5LossConfig",
    "build_v5_loss_fn",
]

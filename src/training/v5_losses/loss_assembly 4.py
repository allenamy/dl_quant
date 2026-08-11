"""Config-driven loss assembly for V5 dual-head training.

Combines components per a config dict, returns total loss + per-component breakdown
for logging. Single point of integration with trainer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import torch

from .components import (
    loss_dir_margin,
    loss_mag_huber,
    loss_joint_mse,
    loss_cs_ic,
    loss_beta_consistency,
)
from .heteroscedastic_components import loss_gaussian_nll
from .huber_components import loss_huber_y


@dataclass
class V5LossConfig:
    """Per-component weights. 0.0 = disabled."""
    w_dir_margin: float = 0.3
    w_mag_huber: float = 0.3
    w_joint_mse: float = 0.5
    w_cs_ic: float = 0.0           # auto-disabled if S=1; set >0 only when multi-asset
    w_beta_consistency: float = 0.0  # optional aux

    # V5 heteroscedastic NLL path
    w_gaussian_nll: float = 0.0
    nll_log_sigma_min: float = -7.0
    nll_log_sigma_max: float = 2.0
    # V5 Huber-on-raw-y path (single head, robust MSE)
    w_huber_y: float = 0.0
    huber_y_delta: float = 1.0

    mag_huber_delta: float = 2.0
    joint_huber_delta: float = 0.0  # 0 = pure MSE; >0 = Huber
    beta_target: float = 1.0


class V5LossAssembly:
    """Stateless loss combiner. Init with config, call forward(...) per batch."""

    def __init__(self, config: Optional[V5LossConfig] = None):
        self.cfg = config or V5LossConfig()

    def __call__(
        self,
        head_out: Dict[str, torch.Tensor],
        y: torch.Tensor,
        mask: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """Compute total loss + per-component breakdown.

        Parameters
        ----------
        head_out : dict from DualHead.forward, must contain 'dir_logit', 'mag', 'y_pred'
                   shapes typically (B, H) or (B, S, H)
        y : target with same shape as head_out['y_pred']
        mask : bool, same shape

        Returns
        -------
        dict with keys: 'total', 'dir_margin', 'mag_huber', 'joint_mse',
                        'cs_ic' (if applicable), 'beta_consistency' (if applicable)
        Each value is a scalar tensor.
        """
        cfg = self.cfg
        out: Dict[str, torch.Tensor] = {}
        total = torch.zeros((), device=y.device, dtype=y.dtype)

        if cfg.w_dir_margin > 0:
            l = loss_dir_margin(head_out["dir_logit"], y, mask)
            out["dir_margin"] = l
            total = total + cfg.w_dir_margin * l

        if cfg.w_mag_huber > 0:
            l = loss_mag_huber(head_out["mag"], y, mask, delta=cfg.mag_huber_delta)
            out["mag_huber"] = l
            total = total + cfg.w_mag_huber * l

        if cfg.w_joint_mse > 0:
            l = loss_joint_mse(head_out["y_pred"], y, mask, delta_huber=cfg.joint_huber_delta)
            out["joint_mse"] = l
            total = total + cfg.w_joint_mse * l

        if cfg.w_cs_ic > 0:
            l = loss_cs_ic(head_out["y_pred"], y, mask)
            out["cs_ic"] = l
            total = total + cfg.w_cs_ic * l

        if cfg.w_beta_consistency > 0:
            l = loss_beta_consistency(head_out["y_pred"], y, mask, target_beta=cfg.beta_target)
            out["beta_consistency"] = l
            total = total + cfg.w_beta_consistency * l

        if cfg.w_gaussian_nll > 0:
            l = loss_gaussian_nll(
                head_out["mu"], head_out["log_sigma"], y, mask,
                log_sigma_min=cfg.nll_log_sigma_min,
                log_sigma_max=cfg.nll_log_sigma_max,
            )
            out["gaussian_nll"] = l
            total = total + cfg.w_gaussian_nll * l

        if cfg.w_huber_y > 0:
            # For Huber, head_out['mu'] is the prediction; if NLL not active, mu = y_pred
            mu_for_huber = head_out.get("mu", head_out.get("y_pred"))
            l = loss_huber_y(mu_for_huber, y, mask, delta=cfg.huber_y_delta)
            out["huber_y"] = l
            total = total + cfg.w_huber_y * l

        out["total"] = total
        return out

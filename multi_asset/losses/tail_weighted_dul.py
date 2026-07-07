"""ARM TAILW: bounded tail-weighted emphasis on the PRIMARY rank + dir_Huber terms
of the single-horizon DUL loss, GATED by `use_tail_weight` (default OFF).

> **created:** 2026-07-07 | **Session:** arch_iter (0B) | **状态:** in-progress

Mechanism (why): H1 says the IC lives in the fat tail. Run1's pinball is already
tail-focal-weighted, but its RANK (`utility_rank_loss`) and DIR_HUBER
(`directional_huber_loss`) primary terms are UN-weighted plain means. This arm
up-weights per-sample by a BOUNDED monotone f(|y|/σ) on exactly those two terms,
so the model spends capacity getting the tail's magnitude+ordering right.

Bit-identity (OFF): `build_tailw_loss_fn(cfg)` with `use_tail_weight` absent/False
returns `_build_loss_fn_for_dul(cfg)` VERBATIM (the src closure) — bit-identical to
Run1 for every existing config. src/ is READ-ONLY: we do NOT edit the src loss; we
build it with `lambda_utility_rank=0` + `lambda_dir_huber=0` (dropping the un-weighted
terms, keeping pinball + ALL aux terms EXACT) and add back the tail-weighted rank+dh.

Anti-pattern #12 guard: BOUNDED emphasis (weight ∈ [1, tail_weight_max], WEIGHT not
REPLACE) — the sign/ordering supervision is preserved, so Spearman is protected. Gate
the arm on BOTH Pearson AND Spearman.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import torch
import torch.nn.functional as F

from src.training.trainer_v2 import _build_loss_fn_for_dul  # src, read-only (import only)


def _pos_or_default(x, default):
    return float(default) if x is None else float(x)


def _tail_weight(target: torch.Tensor, gamma: float, wmax: float) -> torch.Tensor:
    """Bounded monotone per-sample weight w = clamp(1 + gamma*|y|/sigma, max=wmax).
    sigma = batch std of y (matches the loss's magnitude scale). w>=1 always."""
    sigma = target.std().clamp_min(1e-6)
    z = target.abs() / sigma
    return torch.clamp(1.0 + gamma * z, max=wmax)


def _weighted_dir_huber(pred, target, delta, w_wrong, w_extreme, w):
    """Per-sample directional Huber (replicates src directional_huber_loss element-wise)
    × tail weight w, weighted mean. w==1 everywhere reproduces the src scalar exactly."""
    err = pred - target
    abs_err = err.abs()
    base = torch.where(abs_err < delta, 0.5 * err.pow(2), delta * (abs_err - 0.5 * delta))
    sign_disagree = (pred.sign() * target.sign() < 0).to(pred.dtype)
    extreme_miss = sign_disagree * (target.abs() > 1.5).to(pred.dtype)
    dweight = 1.0 + w_wrong * sign_disagree + w_extreme * extreme_miss
    per_sample = base * dweight
    return (per_sample * w).sum() / w.sum().clamp_min(1e-6)


def _weighted_utility_rank(quantiles, target, alpha, w, margin=0.0, n_pairs=None):
    """Pairwise logistic rank on s = alpha*q10 + (1-alpha)*q50, each pair weighted by
    max(w_i, w_j) (a pair matters if EITHER endpoint is a tail sample)."""
    q10 = quantiles[:, 0]
    q50 = quantiles[:, 1]
    s = q50 - alpha * (q50 - q10)
    n = s.shape[0]
    if n < 2:
        return torch.zeros((), device=s.device, dtype=s.dtype)
    if n_pairs is None:
        n_pairs = n
    device = s.device
    i = torch.randint(0, n, (n_pairs,), device=device)
    j = torch.randint(0, n, (n_pairs,), device=device)
    collisions = (i == j)
    if collisions.any():
        j = torch.where(collisions, (j + 1) % n, j)
    desired = torch.sign(target[i] - target[j])
    pred_diff = s[i] - s[j]
    per_pair = F.softplus(-desired * pred_diff + margin)
    pw = torch.maximum(w[i], w[j])
    return (per_pair * pw).sum() / pw.sum().clamp_min(1e-6)


def build_tailw_loss_fn(dul_config: Dict[str, Any]) -> Callable:
    """Tail-weight-aware loss builder. Passthrough (bit-identical to the src loss) unless
    dul_config['use_tail_weight'] is truthy."""
    if not bool(dul_config.get("use_tail_weight", False)):
        return _build_loss_fn_for_dul(dul_config)  # BIT-IDENTICAL passthrough

    gamma = _pos_or_default(dul_config.get("tail_weight_gamma"), 1.0)
    wmax = _pos_or_default(dul_config.get("tail_weight_max"), 3.0)
    lu = _pos_or_default(dul_config.get("lambda_utility_rank"), 0.3)
    ldh = _pos_or_default(dul_config.get("lambda_dir_huber"), 0.0)
    alpha = _pos_or_default(dul_config.get("utility_alpha"), 1.0)
    dh_delta = _pos_or_default(dul_config.get("dir_huber_delta"), 2.0)
    dh_w_wrong = _pos_or_default(dul_config.get("dir_huber_w_wrong"), 2.0)
    dh_w_extreme = _pos_or_default(dul_config.get("dir_huber_w_extreme"), 3.0)
    n_pairs = dul_config.get("n_pairs", None)

    # src loss WITHOUT the (un-weighted) rank + dir_huber — pinball + every aux term stay EXACT.
    base_cfg = dict(dul_config)
    base_cfg["lambda_utility_rank"] = 0.0
    base_cfg["lambda_dir_huber"] = 0.0
    base_fn = _build_loss_fn_for_dul(base_cfg)

    def tailw_loss_fn(outputs, target):
        total = base_fn(outputs, target)
        q = outputs["quantiles"]
        w = _tail_weight(target, gamma, wmax)
        if lu > 0.0:
            total = total + lu * _weighted_utility_rank(q, target, alpha, w, n_pairs=n_pairs)
        if ldh > 0.0:
            total = total + ldh * _weighted_dir_huber(
                q[:, 1], target, dh_delta, dh_w_wrong, dh_w_extreme, w)
        return total

    return tailw_loss_fn

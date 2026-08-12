"""Simplified trainer: quantile-only loss with dual-path (DualPathLOBModel) support.

Unlike ``trainer.py`` which uses the 4-component ``combined_loss``, this trainer
uses **quantile loss only** and supports the ``DualPathLOBModel``'s dual-input
interface ``forward(x_feat, x_raw)``.

Key differences from V1:
  - Quantile-only loss (from ``losses.py``)
  - Dual-path: auto-detects 3-tuple ``(x_feat, y, mask)`` vs 4-tuple
    ``(x_feat, x_raw, y, mask)`` from dataset
  - ReduceLROnPlateau (mode="max" on val_correlation)
  - Checkpoint by val_correlation (not val_loss)
  - Early stopping based on correlation plateau
"""

from __future__ import annotations

import json
import math
import os
import random
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .dataset import DayChunkedSampler
from .dul_loss import compute_dul_loss
from .losses import quantile_loss
from .sam_optimizer import SAM


# ---------------------------------------------------------------------------
# Reuse OnlineMetrics from trainer.py
# ---------------------------------------------------------------------------
from .trainer import OnlineMetrics


# ---------------------------------------------------------------------------
# LR warmup helper
# ---------------------------------------------------------------------------

def _apply_warmup(
    step: int,
    warmup_steps: int,
    base_lr: float,
    optimizer: torch.optim.Optimizer,
) -> None:
    """Linearly ramp LR from ``base_lr / 100`` to ``base_lr`` over ``warmup_steps``.

    Called *before* ``optimizer.step()`` during the first ``warmup_steps``
    iterations.  After warmup, the caller should stop invoking this helper
    so that the main scheduler (e.g. ``ReduceLROnPlateau``) takes over.

    Uses a simple linear interpolation: at ``step=0`` the LR is
    ``base_lr * 0.01``; at ``step=warmup_steps-1`` the LR is ~``base_lr``.
    """
    if warmup_steps <= 0:
        return
    if step >= warmup_steps:
        return
    scale = (step + 1) / warmup_steps
    new_lr = base_lr * (0.01 + 0.99 * scale)
    for pg in optimizer.param_groups:
        pg["lr"] = new_lr


# ---------------------------------------------------------------------------
# Seed helper (ensemble-friendly)
# ---------------------------------------------------------------------------

def _seed_everything(seed: int) -> None:
    """Seed Python's ``random``, NumPy and PyTorch + cudnn for reproducibility.

    Forces cudnn deterministic mode (slower ~1.3-2× but reproducible).
    Required for low-SNR research where single-run variance can flip
    EMA test β from +0.94 to -0.49 between identical-config runs (observed
    on y_1800 Phase 1.1 — see anti-pattern #14 in CLAUDE.md).

    NOTE: torch.use_deterministic_algorithms(True) requires
    CUBLAS_WORKSPACE_CONFIG env var but its absence only warns. We don't
    set it here to allow training without env-var setup; cudnn flags alone
    cover ~95% of non-determinism in our common ops (conv, attention).
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    # cudnn determinism (the main source of run-to-run variance in low SNR).
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# ---------------------------------------------------------------------------
# Checkpoint helper
# ---------------------------------------------------------------------------

def _extract_model_config(model: nn.Module) -> Dict[str, Any]:
    """Extract the construction-relevant config from a model for checkpointing.

    We save shape-determining attributes so that the loader can reinstantiate
    the model class without brittle state-dict key heuristics.

    Only simple scalar attributes are captured (n_features, n_levels,
    d_model, d_raw, etc.); anything missing is silently skipped.  If loading
    code needs a field not captured here, it should be added.
    """
    candidate_attrs = [
        "n_features", "n_levels", "d_model", "d_raw",
        "n_mask_blocks", "n_cross_layers", "patch_size",
        "attn_nhead", "attn_d_ff", "d_prior", "dropout",
        "n_horizons", "n_symbols", "use_monotonic_quantile",
        "n_quantiles",
        # V3 ablation bypass flags (Phase A2) -- persisting these lets a
        # checkpoint reinstantiate with the exact same module graph as at
        # training time, so ablation runs don't silently revert to "full V3".
        "use_masknet", "use_gdcn", "use_raw_path",
        "use_attention", "use_conv",
        # RevIN flag (Phase A3 non-stationarity mitigation)
        "use_revin",
        # V4 additions
        "use_channel_mix_conv", "use_level_attention_pool",
        "use_patch_attention_pool", "use_ppnet_gate",
        "use_multi_scale",
        # Y1800 push: pluggable temporal backbone
        "backbone_kind", "backbone_kwargs",
        # Y1800 Phase 1.2: in-graph σ-anchor scale layer (learnable α)
        "output_scale_init",
        # Y1800 Phase 2: regime-aware FiLM modulation
        "use_regime_film", "regime_film_hidden",
        # Y1800 Phase A2: dual-path fusion variant
        "fusion_kind",
        # v5push Phase 3: binary classification head for DirAcc
        "use_sign_head",
        # v5push Phase 3 (DAQH): direction-aware quantile head
        "use_direction_aware_head",
        "use_decoupled_sign_mag_head",
    ]
    config: Dict[str, Any] = {}
    for attr in candidate_attrs:
        if hasattr(model, attr):
            val = getattr(model, attr)
            # Record primitives + plain dict (e.g. backbone_kwargs).
            if isinstance(val, (int, float, bool, str, dict)):
                config[attr] = val
    return config


# ---------------------------------------------------------------------------
# Multi-horizon loss helper
# ---------------------------------------------------------------------------

def _multi_horizon_loss(
    outputs: Dict[str, torch.Tensor],
    y: torch.Tensor,
    mask: torch.Tensor,
    loss_fn: Callable[[Dict[str, torch.Tensor], torch.Tensor], torch.Tensor],
    horizon_weights: Optional[List[float]] = None,
) -> Optional[torch.Tensor]:
    """Sum per-horizon quantile losses for multi-horizon training.

    Parameters
    ----------
    outputs : dict
        Model output.  Must contain ``quantiles_by_horizon`` of shape
        ``(B, n_horizons, n_quantiles)`` AND ``point_pred_by_horizon`` of
        shape ``(B, n_horizons)``.  The model is responsible for producing
        these when called with ``all_horizons=True``.
    y : torch.Tensor
        Shape ``(B, n_horizons)`` targets.
    mask : torch.Tensor
        Shape ``(B, n_horizons)`` per-horizon validity mask.
    loss_fn : callable
        Same signature as the trainer-level ``loss_fn`` but invoked with
        the single-horizon slice ``{"quantiles": (B', Q), "point_pred":
        (B',)}`` and target ``(B',)``.  This lets the caller swap in IC /
        rank / combined losses without changing the trainer.

    Returns
    -------
    torch.Tensor or None
        Summed loss across horizons that had at least one unmasked sample,
        divided by the number of contributing horizons (so the scalar stays
        comparable to the single-horizon case).  Returns ``None`` when every
        horizon's mask is zero for this batch — caller should ``continue``.
    """
    if "quantiles_by_horizon" not in outputs:
        raise KeyError(
            "Multi-horizon mode requires model output to contain "
            "'quantiles_by_horizon' -- make sure the model is called with "
            "all_horizons=True and supports n_horizons > 1."
        )
    q_by_h = outputs["quantiles_by_horizon"]        # (B, n_h, Q)
    p_by_h = outputs["point_pred_by_horizon"]       # (B, n_h)
    n_h = q_by_h.shape[1]

    # Sync-free accumulation: compute each horizon's loss on its masked
    # slice and stack. The per-horizon torch.isfinite() guard was removed
    # because it forced a CUDA sync every horizon (n_h sync points per
    # step) — the nan guard at the outer training loop plus grad clip
    # already protect against pathological batches, and individual-horizon
    # slices rarely NaN in practice. idx.numel() is a Python int from the
    # tensor shape and does not sync.
    losses: list[torch.Tensor] = []
    weights: list[float] = []
    for h_idx in range(n_h):
        mask_h = mask[:, h_idx]
        idx = mask_h.nonzero(as_tuple=True)[0]
        if idx.numel() == 0:
            continue
        m_outputs = {
            "quantiles": q_by_h[idx, h_idx, :],
            "point_pred": p_by_h[idx, h_idx],
        }
        m_target = y[idx, h_idx]
        losses.append(loss_fn(m_outputs, m_target))
        # Per-horizon weight; default 1.0 each (unchanged from prior behavior).
        w = 1.0 if horizon_weights is None else float(horizon_weights[h_idx])
        weights.append(w)

    if not losses:
        return None
    # Weighted mean across horizons. When weights are all 1.0 this reduces to
    # the original torch.stack(...).mean() (sync-free, same numerical path).
    stacked = torch.stack(losses)  # (n_contributing,)
    w_tensor = torch.tensor(weights, dtype=stacked.dtype, device=stacked.device)
    return (stacked * w_tensor).sum() / w_tensor.sum()


# ---------------------------------------------------------------------------
# Batch / forward / loss helpers (DRY)
# ---------------------------------------------------------------------------

def _unpack_batch(
    batch: tuple,
    dual_path: bool,
    has_regime_prior: bool,
    has_domain: bool = False,
):
    """Normalize batch tuple to (x_feat, x_raw, regime_prior, y, mask, domain).

    Absent parts are None. Supported shapes:
      - 3-tuple: (x_feat, y, mask)                        -> Path A only
      - 4-tuple: (x_feat, x_raw, y, mask)                 -> Dual path
      - 5-tuple: (x_feat, x_raw, regime_prior, y, mask)   -> Dual + prior
    With ``has_domain=True`` (DANN), each shape gains a trailing domain tensor.
    """
    if has_domain:
        # Domain is the last element; strip it then recurse with has_domain=False
        *base, domain = batch
        x_feat, x_raw, regime_prior, y, mask = _unpack_batch(
            tuple(base), dual_path, has_regime_prior, has_domain=False
        )[:5]
        return x_feat, x_raw, regime_prior, y, mask, domain
    if has_regime_prior:
        x_feat, x_raw, regime_prior, y, mask = batch
        return x_feat, x_raw, regime_prior, y, mask, None
    if dual_path:
        x_feat, x_raw, y, mask = batch
        return x_feat, x_raw, None, y, mask, None
    x_feat, y, mask = batch
    return x_feat, None, None, y, mask, None


def _forward_with_regime(
    model: nn.Module,
    x_feat: torch.Tensor,
    x_raw: Optional[torch.Tensor],
    regime_prior: Optional[torch.Tensor],
    multi_horizon: bool,
) -> Dict[str, torch.Tensor]:
    """Dispatch the right forward call given what's available."""
    kwargs: Dict[str, Any] = {}
    if regime_prior is not None:
        kwargs["regime_prior"] = regime_prior
    if multi_horizon:
        kwargs["all_horizons"] = True
    if x_raw is not None:
        return model(x_feat, x_raw, **kwargs)
    return model(x_feat, **kwargs)


def _build_loss_fn_for_dul(cfg: Dict[str, Any]) -> Callable:
    """Build a loss_fn(outputs, target) -> scalar from a DUL config dict.

    Config keys (all optional with defaults):
      lambda_quantile      (default 1.0)
      lambda_utility_rank  (default 0.3)
      lambda_calib         (default 0.0)
      utility_alpha        (default 1.0)
      n_pairs              (default None -> use batch size)

    Explicit ``None`` values in ``cfg`` are treated as "use default"
    (defensive: raw JSON config loaders may emit ``None`` for missing
    fields).  Explicit ``0.0`` is preserved (do NOT use the ``or``
    shortcut, which would resurrect the default for legitimate 0.0).
    """
    def _pos_or_default(x, default):
        return float(default) if x is None else float(x)

    lambda_q = _pos_or_default(cfg.get("lambda_quantile"), 1.0)
    lambda_u = _pos_or_default(cfg.get("lambda_utility_rank"), 0.3)
    lambda_c = _pos_or_default(cfg.get("lambda_calib"), 0.0)
    lambda_dh = _pos_or_default(cfg.get("lambda_dir_huber"), 0.0)
    lambda_bc = _pos_or_default(cfg.get("lambda_beta_calib"), 0.0)
    lambda_dsp = _pos_or_default(cfg.get("lambda_diff_spearman"), 0.0)
    diff_sp_temp = _pos_or_default(cfg.get("diff_spearman_temperature"), 1.0)
    lambda_crps_v = _pos_or_default(cfg.get("lambda_crps"), 0.0)
    alpha_u = _pos_or_default(cfg.get("utility_alpha"), 1.0)
    lambda_pearson = _pos_or_default(cfg.get("lambda_pearson"), 0.0)
    focal_threshold = _pos_or_default(cfg.get("focal_threshold"), 0.0)
    focal_gamma = _pos_or_default(cfg.get("focal_gamma"), 2.0)
    n_pairs = cfg.get("n_pairs", None)
    dh_delta = _pos_or_default(cfg.get("dir_huber_delta"), 2.0)
    dh_w_wrong = _pos_or_default(cfg.get("dir_huber_w_wrong"), 2.0)
    dh_w_extreme = _pos_or_default(cfg.get("dir_huber_w_extreme"), 3.0)
    # v5push Phase 3: BCE on sign_logit. Small weight (0.05-0.10) to avoid AP#10.
    lambda_cls = _pos_or_default(cfg.get("lambda_cls"), 0.0)
    # v5push Phase 3 (A2): uncertainty calibration loss. Encourages
    # (q90-q10) to correlate with |q50-y| → trust score |q50|/(q90-q10) more
    # reliable for DirAcc-gated trading. Loss = -corr(IQR, |residual|).
    lambda_unc = _pos_or_default(cfg.get("lambda_unc"), 0.0)
    # v5push Phase 3 (F): sign-correlation loss. Replaces BCE with continuous
    # corr(tanh(sign_logit), sign(y)) on samples with |y_z| > 0.3.
    lambda_signcorr = _pos_or_default(cfg.get("lambda_signcorr"), 0.0)
    # v5push Phase 3 (P): magnitude-focal Huber on `magnitude_abs` head output.
    # Loss = Huber(magnitude_abs, |y|) × clip(|y|/σ_y, 0.3, 3.0).
    # Tail-focal weight concentrates magnitude learning on informative samples
    # (anti-pattern #12 risk mitigated because applied to MAGNITUDE ONLY —
    # sign head sees uniform BCE → Spearman protected).
    lambda_mag_focal_huber = _pos_or_default(cfg.get("lambda_mag_focal_huber"), 0.0)
    mag_focal_clip_min = _pos_or_default(cfg.get("mag_focal_clip_min"), 0.3)
    mag_focal_clip_max = _pos_or_default(cfg.get("mag_focal_clip_max"), 3.0)
    # v5push Phase 3 (P): BCE weighting mode. "sigmoid" (default) uses
    # sigmoid((|y|−0.5)·5) weight (DAQH style); "uniform" uses no weight
    # (Track P: pure sign supervision uncoupled from magnitude).
    cls_weight_mode = str(cfg.get("cls_weight_mode", "sigmoid"))
    # v5push Phase 3 Track REG_loss: magnitude-conditional Pearson loss.
    # Computes Pearson(q50, y) on TAIL subset (|y| > σ_y) and adds
    # `lambda_pearson_tail * (1 - corr)` to total loss. Auxiliary direct
    # attack on tail Pearson (where signal concentrates). Pool P math:
    # pool cov dominated by tail samples, so maximizing tail Pearson →
    # higher pool P. AUXILIARY (typically λ≤0.10), original losses intact.
    lambda_pearson_tail = _pos_or_default(cfg.get("lambda_pearson_tail"), 0.0)
    # v5push Phase 3 Track REG_arch_v5: Sequence-level direction BCE (deep supervision).
    # Adds BCE at anchor timesteps t∈anchors on `seq_dir_logits` (B, T) against
    # sign(y_600). Forces intermediate temporal representations to encode the
    # direction signal — auxiliary task improves DA (target 0.58).
    # Requires model.use_seq_direction_head=True.
    lambda_seq_direction = _pos_or_default(cfg.get("lambda_seq_direction"), 0.0)
    seq_direction_anchors = cfg.get("seq_direction_anchors",
                                     [100, 200, 300, 400, 500, -1])

    def dul_loss_fn(outputs, target):
        # return_parts=False avoids per-component .item() syncs in the hot
        # training loop — under multi-horizon this would call .item() up to
        # 16× per step, draining the CUDA pipeline and pinning GPU util to
        # single-digit %. The trainer only needs the total loss tensor for
        # backward; per-component metrics are a diagnostic, not required.
        total, _ = compute_dul_loss(
            outputs["quantiles"], target,
            lambda_quantile=lambda_q,
            lambda_utility_rank=lambda_u,
            lambda_calib=lambda_c,
            lambda_dir_huber=lambda_dh,
            lambda_beta_calib=lambda_bc,
            lambda_diff_spearman=lambda_dsp,
            diff_spearman_temperature=diff_sp_temp,
            lambda_crps=lambda_crps_v,
            utility_alpha=alpha_u,
            n_pairs=n_pairs,
            return_parts=False,
            dir_huber_delta=dh_delta,
            dir_huber_w_wrong=dh_w_wrong,
            dir_huber_w_extreme=dh_w_extreme,
        )
        # v5push Phase 3 Track REG_loss: magnitude-conditional Pearson on tail.
        # Compute Pearson(q50, y) on subset where |y| > σ_y. Pool P math:
        # cov dominated by tail samples → maximize tail corr → higher pool P.
        # AUXILIARY (small λ), original losses intact.
        if lambda_pearson_tail > 0.0 and target.numel() >= 64:
            sigy = target.std() + 1e-6
            mask = target.abs() > sigy
            if mask.sum() >= 32:
                pred_t = outputs["point_pred"][mask]
                tgt_t = target[mask]
                p_c = pred_t - pred_t.mean()
                t_c = tgt_t - tgt_t.mean()
                denom = torch.norm(p_c) * torch.norm(t_c) + 1e-8
                corr_tail = (p_c * t_c).sum() / denom
                total = total + lambda_pearson_tail * (1.0 - corr_tail)
        # Direct Pearson auxiliary loss — negative because we MINIMISE.
        # Pearson is scale-invariant; acts as rank-preserving shaping force.
        # Complementary to pinball (magnitude) and utility_rank (pairwise).
        if lambda_pearson > 0.0:
            pred = outputs["point_pred"]
            # De-mean pred and target
            p_c = pred - pred.mean()
            t_c = target - target.mean()
            denom = torch.norm(p_c) * torch.norm(t_c) + 1e-8
            corr = (p_c * t_c).sum() / denom
            total = total - lambda_pearson * corr  # maximise corr = minimise -corr
        # v5push Phase 3 (A2): uncertainty calibration loss.
        # Make (q90-q10) reflect actual |q50-y| → trust score = |q50|/(q90-q10)
        # becomes meaningful confidence indicator. Needs batch ≥ 64 for stable corr.
        if lambda_unc > 0.0 and target.numel() >= 64:
            quantiles = outputs["quantiles"]
            iqr = quantiles[:, 2] - quantiles[:, 0]  # (B,) ≥ 0 by monotonic constraint
            abs_res = (quantiles[:, 1] - target).abs()  # (B,) ≥ 0
            iqr_c = iqr - iqr.mean()
            res_c = abs_res - abs_res.mean()
            denom = torch.norm(iqr_c) * torch.norm(res_c) + 1e-8
            unc_corr = (iqr_c * res_c).sum() / denom
            # Maximize corr → minimize -corr
            total = total - lambda_unc * unc_corr

        # v5push Phase 3: BCE on sign_logit (DirAcc dual-task).
        # Two modes:
        #   - lambda_cls > 0: weighted BCE (discrete, original)
        #   - lambda_signcorr > 0: continuous sign-correlation loss (smoother).
        # Both supervise sign_logit. signcorr avoids BCE saturation when logit large.
        if lambda_cls > 0.0 and "sign_logit" in outputs:
            sign_logit = outputs["sign_logit"]
            cls_target = (target > 0.0).to(sign_logit.dtype)
            bce_per = torch.nn.functional.binary_cross_entropy_with_logits(
                sign_logit, cls_target, reduction='none'
            )
            if cls_weight_mode == "uniform":
                bce = bce_per.mean()
            elif cls_weight_mode == "tail_focal_1p5":
                # Track S: focal weight = clip(|y|/σ, 0.3, 3.0)^1.5
                # Concentrate BCE gradient on tail samples where direction is reliable.
                sigy = target.std() + 1e-6
                cls_weight = (target.abs() / sigy).clamp(min=0.3, max=3.0).pow(1.5)
                denom = cls_weight.sum().clamp(min=1e-9)
                bce = (bce_per * cls_weight).sum() / denom
            else:  # "sigmoid" — default DAQH-style (Track A baseline)
                cls_weight = torch.sigmoid((target.abs() - 0.5) * 5.0)
                denom = cls_weight.sum().clamp(min=1e-9)
                bce = (bce_per * cls_weight).sum() / denom
            total = total + lambda_cls * bce
        # v5push Phase 3 (P): magnitude-focal Huber.
        # Decouples magnitude learning from sign: applies Huber on
        # |y| vs `magnitude_abs` head output. Focal weight clips |y|/σ to
        # [0.3, 3.0] — concentrates gradient on informative tail samples.
        if lambda_mag_focal_huber > 0.0 and "magnitude_abs" in outputs:
            mag_pred = outputs["magnitude_abs"]                # ≥ 0
            mag_target = target.abs()                          # ≥ 0
            # Huber on residual
            resid = mag_pred - mag_target
            delta_h = 2.0
            abs_resid = resid.abs()
            quad = torch.minimum(abs_resid, torch.tensor(delta_h, device=resid.device, dtype=resid.dtype))
            lin = abs_resid - quad
            huber_per = 0.5 * quad * quad + delta_h * lin
            # Focal weight from |y|/σ_y (σ_y ≈ 1 in z-space since y was normalized)
            sigy = target.std() + 1e-6
            focal_w = (mag_target / sigy).clamp(min=mag_focal_clip_min, max=mag_focal_clip_max)
            denom_f = focal_w.sum().clamp(min=1e-9)
            mag_focal = (huber_per * focal_w).sum() / denom_f
            total = total + lambda_mag_focal_huber * mag_focal
        if lambda_signcorr > 0.0 and "sign_logit" in outputs:
            sign_logit = outputs["sign_logit"]
            # Use samples where |y| above threshold so noise doesn't contribute
            mask = target.abs() > 0.3
            if mask.sum() >= 16:
                sl = sign_logit[mask]
                yt = target[mask]
                # Map sign_logit to (-1, 1) via tanh; supervise against sign(y)
                pred_sign = torch.tanh(sl)
                true_sign = torch.sign(yt)
                p_c = pred_sign - pred_sign.mean()
                t_c = true_sign - true_sign.mean()
                denom = torch.norm(p_c) * torch.norm(t_c) + 1e-8
                corr = (p_c * t_c).sum() / denom
                total = total - lambda_signcorr * corr
        # Focal weighting on tail samples — upweight |target| > threshold
        # This adds a secondary quantile loss on tail subset, pushing model
        # to fit large-magnitude targets better (where P&L lives).
        if focal_threshold > 0.0:
            with torch.no_grad():
                tail_mask = (target.abs() > focal_threshold).float()
            if tail_mask.sum() > 0:
                # Extra quantile loss on tail samples, weighted by magnitude
                tail_weight = (target.abs() / max(focal_threshold, 1e-3)) ** focal_gamma * tail_mask
                quantiles = outputs["quantiles"]
                # Pinball for q_50 only (median) on tail samples
                residual = target - quantiles[:, 1]
                pinball_50 = torch.where(residual >= 0, 0.5 * residual, -0.5 * residual)
                tail_loss = (pinball_50 * tail_weight).sum() / (tail_weight.sum() + 1e-8)
                total = total + tail_loss
        # Track REG_arch_v5: sequence-level direction BCE at anchor timesteps.
        if lambda_seq_direction > 0.0 and "seq_dir_logits" in outputs:
            seq_logits = outputs["seq_dir_logits"]  # (B, T)
            T = seq_logits.size(1)
            cls_target = (target > 0.0).to(seq_logits.dtype)  # (B,)
            anchor_losses = []
            for a in seq_direction_anchors:
                ai = T + a if a < 0 else a
                if ai < 0 or ai >= T:
                    continue
                logit_a = seq_logits[:, ai]
                bce_a = torch.nn.functional.binary_cross_entropy_with_logits(
                    logit_a, cls_target, reduction='mean')
                anchor_losses.append(bce_a)
            if anchor_losses:
                seq_dir_loss = torch.stack(anchor_losses).mean()
                total = total + lambda_seq_direction * seq_dir_loss
        return total

    return dul_loss_fn


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train_one_fold_v2(
    *,
    model: nn.Module,
    train_dataset: "torch.utils.data.Dataset",
    val_dataset: "torch.utils.data.Dataset",
    out_dir: str,
    device: str = "cpu",
    epochs: int = 50,
    batch_size: int = 64,
    lr: float = 3e-4,
    weight_decay: float = 1e-3,
    patience: int = 10,
    grad_clip: float = 1.0,
    warmup_steps_pct: float = 0.05,
    loss_fn: Optional[Callable[[Dict[str, torch.Tensor], torch.Tensor], torch.Tensor]] = None,
    seed: Optional[int] = None,
    dul_config: Optional[Dict[str, Any]] = None,
    num_workers: int = 4,
    prefetch_factor: int = 2,
    horizon_weights: Optional[List[float]] = None,
    val_metric: str = "val_corr",
    use_ema: bool = False,
    ema_decay: float = 0.999,
    primary_horizon_idx: int = 0,
    train_index_stride: int = 1,
    multi_horizon_loss_module: Optional[torch.nn.Module] = None,
    use_sam: bool = False,
    sam_rho: float = 0.05,
    # --- DANN (Domain Adversarial NN) -----------------------------------
    # When True, dataset must yield (..., domain) tuples (use DomainAwareDataset
    # wrapper). Trainer adds CE on domain_logits in outputs, with lambda_grl
    # scheduled per Ganin: 2/(1+exp(-10·p))-1 where p = epoch/total_epochs.
    use_dann: bool = False,
    lambda_dann_max: float = 1.0,
) -> Dict[str, Any]:
    """Train with quantile-only loss, dual-path support.

    The dataset ``__getitem__`` can return either:
      ``(x_feat, y, mask)``                    -- Path A only
      ``(x_feat, x_raw, y, mask)``             -- dual path
      ``(x_feat, x_raw, regime_prior, y, mask)`` -- dual path + regime prior

    Detection: uses ``dataset.has_raw`` attribute when available (set by
    ``LOBDatasetV2``), falling back to tuple-length probing.

    Note: when using trainer_v2 with a PPNet gate model, the caller must
    either set ``d_prior=0`` OR provide ``regime_prior`` in the dataset
    (5-tuple mode). The trainer does NOT auto-compute regime_prior.

    Parameters
    ----------
    model : nn.Module
        Any model whose ``forward`` returns a dict with keys
        ``quantiles`` (B, n_quantiles) and ``point_pred`` (B,).
    train_dataset, val_dataset : Dataset
        Each ``__getitem__`` returns 3-tuple or 4-tuple (see above).
    out_dir : str
        Directory for saving ``best_model.pt`` and ``metrics.json``.
    device : str
        ``'cpu'`` or ``'cuda'`` / ``'cuda:0'`` etc.
    epochs : int
        Maximum number of training epochs.
    batch_size : int
        Mini-batch size.
    lr : float
        Initial learning rate.
    weight_decay : float
        AdamW weight-decay coefficient.
    patience : int
        Early-stopping patience (epochs without improvement).
    grad_clip : float
        Max gradient norm for clipping.
    warmup_steps_pct : float
        Fraction of *total* optimizer steps (``epochs * steps_per_epoch``)
        used for linear LR warmup.  The LR is ramped from ``lr/100`` to
        ``lr`` over that many steps, then the main ``ReduceLROnPlateau``
        scheduler takes over.  Set to ``0`` to disable warmup.
    loss_fn : callable, optional
        Signature ``loss_fn(outputs_dict, target) -> scalar tensor``.  When
        ``None`` (default) the trainer uses pure quantile loss on
        ``outputs["quantiles"]``.  Useful to swap in IC / rank / combined
        losses without changing the training loop.
    seed : int, optional
        If provided, seed Python / NumPy / PyTorch for ensemble-friendly
        deterministic training.  ``None`` (default) leaves global RNGs
        untouched.
    dul_config : dict, optional
        If provided, overrides the default quantile loss with a DUL-composed
        loss (pinball + utility-rank + calibration). Schema:
          {"lambda_quantile": float, "lambda_utility_rank": float,
           "lambda_calib": float, "utility_alpha": float, "n_pairs": int | None}
        All keys optional; defaults: 1.0 / 0.3 / 0.0 / 1.0 / None.
        Incompatible with ``loss_fn`` -- if both are given, ``dul_config``
        wins and emits a warning.

    Returns
    -------
    dict
        Best validation metrics (val_loss, val_corr, val_r2, best_epoch).
    """
    # Seed *first* so DataLoader worker seeding / model init shuffle are
    # reproducible when the caller requested it.
    if seed is not None:
        _seed_everything(seed)

    os.makedirs(out_dir, exist_ok=True)
    device_obj = torch.device(device)
    model = model.to(device_obj)

    # Default loss: pure quantile on ``outputs["quantiles"]``.
    # dul_config, when supplied, replaces it with the DUL-composed loss.
    if dul_config is not None:
        if loss_fn is not None:
            import warnings
            warnings.warn(
                "Both loss_fn and dul_config supplied; dul_config wins "
                "(DUL composition overrides custom loss_fn).",
                stacklevel=2,
            )
        loss_fn = _build_loss_fn_for_dul(dul_config)
    elif loss_fn is None:
        def loss_fn(outputs, target):  # type: ignore[no-redef]
            return quantile_loss(outputs["quantiles"], target)

    # --- detect input mode from dataset attribute or first sample ------------
    if hasattr(train_dataset, 'has_raw'):
        dual_path = train_dataset.has_raw
    else:
        sample = train_dataset[0]
        dual_path = len(sample) >= 4

    # Detect DANN wrapper (DomainAwareDataset) — adds trailing domain element
    use_dann_dataset = hasattr(train_dataset, 'n_domains')
    # Detect 5-tuple mode (with regime_prior). When DANN wrapper is active,
    # the trailing element is domain (long tensor), so subtract 1 from length.
    sample = train_dataset[0]
    sample_len_no_domain = len(sample) - (1 if use_dann_dataset else 0)
    has_regime_prior = sample_len_no_domain == 5
    if use_dann_dataset:
        # has_raw True if remaining length ≥ 4
        dual_path = sample_len_no_domain >= 4

    # --- detect multi-horizon mode ------------------------------------------
    # Convention: LOBDatasetV2 with ``horizons=[...]`` returns per-item y /
    # mask of shape (n_horizons,) instead of scalar.  We detect this by
    # inspecting the first sample's y tensor rank.  When active, the trainer
    # calls ``model(..., all_horizons=True)`` so the model emits
    # ``quantiles_by_horizon`` (B, n_horizons, 3) for per-horizon loss.
    if has_regime_prior:
        y_sample = sample[3]
    elif dual_path:
        y_sample = sample[2]
    else:
        y_sample = sample[1]
    multi_horizon = torch.is_tensor(y_sample) and y_sample.ndim == 1 and y_sample.numel() > 1
    n_horizons = int(y_sample.numel()) if multi_horizon else 1
    if multi_horizon:
        print(
            f"[trainer_v2] Multi-horizon mode: n_horizons={n_horizons}. "
            f"Per-horizon quantile loss will be summed with per-horizon masks."
        )

    # --- data loaders --------------------------------------------------------
    # Use day-chunked sampling when the dataset has per-day structure
    # (LOBDatasetV2). With lazy per-day loading and an LRU cache of size
    # ~128, globally shuffled access across 500+ days thrashes the cache
    # (each batch of 256 spans ~256 distinct days, ~75% miss rate). A
    # day-chunked sampler iterates one day at a time (random day order per
    # epoch, random sample order within day), achieving ~100% cache hit
    # rate after the first sample of each day. Falls back to plain
    # shuffle=True for other datasets (legacy LOBDataset, _SlicedV2 from
    # single-day mode).
    use_day_sampler = (
        hasattr(train_dataset, "_offsets")
        and hasattr(train_dataset, "_day_paths")
    )

    if use_day_sampler:
        # chunk_size=32 balances cache efficiency (100% hit at cache_size=128)
        # with per-batch day diversity (~32 days per chunk → near-iid SGD).
        # Shuffling is LEAKAGE-SAFE: fold builder already enforces strict
        # train < val < test day ordering; DayChunkedSampler only reorders
        # samples WITHIN the train set.
        train_sampler: Optional[DayChunkedSampler] = DayChunkedSampler(
            train_dataset,
            chunk_size=32,
            shuffle_days=True,
            shuffle_within_day=True,
            seed=42,
            index_stride=train_index_stride,
        )
        if train_index_stride > 1:
            print(f"[trainer_v2] train_index_stride={train_index_stride} → "
                  f"subsampling train set to break label overlap "
                  f"(effective samples ≈ {len(train_dataset) // train_index_stride})")
        # num_workers=4 with persistent_workers parallelises NPZ loading from
        # FUSE-mounted volumes (RunPod /workspace) — biggest perf win for
        # GPU training when the bottleneck is per-batch I/O. Each worker forks
        # its own LRU cache; chunk_size shuffle still preserves leakage safety
        # since each worker sees a non-overlapping slice of indices.
        # Exception: if the dataset is preloaded, all data is in process
        # memory; workers would just fork the giant tensor, wasting RAM
        # and adding IPC overhead. Use num_workers=0 in that case.
        preloaded = getattr(train_dataset, "_preloaded", False)
        _train_nw = 0 if preloaded else num_workers
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            sampler=train_sampler,   # mutually exclusive with shuffle
            num_workers=_train_nw,
            persistent_workers=_train_nw > 0,
            prefetch_factor=prefetch_factor if _train_nw > 0 else None,
            pin_memory=torch.cuda.is_available(),
            drop_last=True,
        )
    else:
        train_sampler = None
        preloaded = getattr(train_dataset, "_preloaded", False)
        _train_nw = 0 if preloaded else num_workers
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=_train_nw,
            persistent_workers=_train_nw > 0,
            prefetch_factor=prefetch_factor if _train_nw > 0 else None,
            pin_memory=torch.cuda.is_available(),
            drop_last=True,
        )
    val_preloaded = getattr(val_dataset, "_preloaded", False)
    _val_nw = 0 if val_preloaded else max(num_workers // 2, 1)
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=_val_nw,
        persistent_workers=_val_nw > 0,
        prefetch_factor=prefetch_factor if _val_nw > 0 else None,
        pin_memory=torch.cuda.is_available(),
    )

    # --- optimizer & scheduler -----------------------------------------------
    # Register loss-module params (e.g. UNIT log_vars) with the optimizer so
    # they actually update. Otherwise UNIT degenerates to static weighting.
    _trainable_params = list(model.parameters())
    if multi_horizon_loss_module is not None:
        multi_horizon_loss_module = multi_horizon_loss_module.to(device_obj)
        _extra = [p for p in multi_horizon_loss_module.parameters() if p.requires_grad]
        _trainable_params.extend(_extra)
        if _extra:
            print(f"[trainer_v2] multi_horizon_loss_module adds {sum(p.numel() for p in _extra)} trainable params")
    if use_sam:
        # SAM (Sharpness-Aware Minimization) wraps AdamW; the inner AdamW owns
        # LR / weight-decay / state, SAM only injects the rho-perturbation
        # between two backward passes. Param groups are aliased so that the
        # warmup helper's LR mutation propagates to both. See
        # ``src/training/sam_optimizer.py`` for the algorithm derivation and
        # CLAUDE.md (low-SNR ceiling discussion) for motivation.
        optimizer = SAM(
            _trainable_params,
            torch.optim.AdamW,
            rho=sam_rho,
            lr=lr,
            weight_decay=weight_decay,
        )
        print(f"[trainer_v2] SAM optimizer active (rho={sam_rho}, base=AdamW); "
              f"per-step compute is ~2× (extra forward + backward).")
    else:
        optimizer = torch.optim.AdamW(
            _trainable_params, lr=lr, weight_decay=weight_decay,
        )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",       # maximize val_correlation
        factor=0.5,
        patience=max(patience // 2, 2),
        min_lr=1e-6,
    )

    # --- warmup bookkeeping --------------------------------------------------
    # ``drop_last=True`` above, so steps_per_epoch = len(train_ds) // batch_size.
    steps_per_epoch = max(len(train_dataset) // batch_size, 1)
    total_steps = steps_per_epoch * epochs
    # Warmup over at most 5 epochs (or fewer if training is short).
    # patience=10 means early-stop can fire by epoch ~15; warmup must complete
    # well before that so the model sees full base_lr for enough time.
    # ``warmup_steps_pct`` is retained in the signature for back-compat but
    # no longer drives the schedule — scaling with ``total_steps`` made
    # warmup too long when ``epochs`` was set high as a safety ceiling.
    warmup_epochs = min(5, epochs // 4)
    warmup_steps = warmup_epochs * steps_per_epoch
    global_step = 0

    # --- Optional EMA wrapper (Y600 push Block B, edit E3) ------------------
    # Polyak-averaged copy of model weights. Updated after every optimizer
    # step. Evaluated alongside the regular model each epoch. Saved separately
    # to ``ema_best.pt`` so downstream can pick whichever wins val composite.
    # Legacy configs that don't set ``use_ema`` get behaviour identical to
    # pre-patch trainer (ema_model stays None, all EMA branches skip).
    ema_model = None
    if use_ema:
        # AveragedModel uses a callable avg_fn(averaged_param, new_param, count).
        # Exponential moving average with given decay: avg = decay*avg + (1-decay)*new.
        _one_minus_decay = 1.0 - float(ema_decay)

        def _ema_avg(avg_param, new_param, num_averaged):  # noqa: ARG001
            return avg_param + _one_minus_decay * (new_param - avg_param)

        ema_model = torch.optim.swa_utils.AveragedModel(
            model, avg_fn=_ema_avg,
        ).to(device_obj)
        print(f"[trainer_v2] EMA wrapper active (decay={ema_decay})")

    # val_metric selector: "val_corr" (legacy, Pearson only) or
    # "composite" (0.5 * Pearson + 0.5 * Spearman). Composite is designed for
    # y_600 where Spearman is the trading-side primary metric and Pearson the
    # spec-compliance gate; selecting by composite targets both simultaneously.
    if val_metric not in ("val_corr", "composite"):
        raise ValueError(
            f"val_metric must be 'val_corr' or 'composite', got {val_metric!r}"
        )
    if val_metric == "composite":
        print("[trainer_v2] val_metric=composite (0.5*Pearson + 0.5*Spearman)")

    # --- tracking ------------------------------------------------------------
    best_metrics: Dict[str, Any] = {}
    best_ema_metrics: Dict[str, Any] = {}
    epochs_no_improve = 0

    # DANN: lambda_grl schedule per Ganin & Lempitsky 2015.
    # p = epoch/total_epochs ∈ [0,1]; lambda = 2/(1+exp(-10p)) - 1 ∈ [0,1].
    # Multiply by lambda_dann_max (config-controlled cap).
    if use_dann:
        if not hasattr(model, "lambda_grl"):
            raise AttributeError(
                "use_dann=True but model has no `lambda_grl` attribute "
                "(model must have `use_dann=True` in config)"
            )
        print(f"[trainer_v2] DANN active (lambda_dann_max={lambda_dann_max})")

    for epoch in range(1, epochs + 1):
        # Refresh day-chunked sampler RNG so day order varies per epoch.
        # No-op when falling back to shuffle=True DataLoader.
        if train_sampler is not None:
            train_sampler.set_epoch(epoch)

        # DANN: update lambda_grl for this epoch (model uses self.lambda_grl).
        if use_dann:
            p = (epoch - 1) / max(epochs - 1, 1)
            lambda_grl = lambda_dann_max * (2.0 / (1.0 + math.exp(-10.0 * p)) - 1.0)
            model.lambda_grl = float(lambda_grl)

        # ===== Training =====
        model.train()
        train_loss_sum = 0.0
        train_steps = 0
        domain_loss_sum = 0.0
        domain_acc_sum = 0.0
        domain_steps = 0

        for batch in train_loader:
            # Only pass ``all_horizons`` when multi-horizon is active.  This
            # keeps the kwarg invisible to V2 / legacy models (whose forward
            # doesn't know about it) and makes single-horizon runs
            # bit-identical to the pre-multi-horizon trainer.
            x_feat, x_raw, regime_prior, y, mask, domain = _unpack_batch(
                batch, dual_path, has_regime_prior, has_domain=use_dann,
            )
            if domain is not None:
                domain = domain.to(device_obj, non_blocking=True)
            x_feat = x_feat.to(device_obj, non_blocking=True)
            if x_raw is not None:
                x_raw = x_raw.to(device_obj, non_blocking=True)
            if regime_prior is not None:
                regime_prior = regime_prior.to(device_obj, non_blocking=True)
            y = y.to(device_obj, non_blocking=True)
            mask = mask.to(device_obj, non_blocking=True)

            outputs = _forward_with_regime(
                model, x_feat, x_raw, regime_prior, multi_horizon,
            )

            # Loss computation: multi-horizon sums per-horizon quantile loss
            # with per-horizon masks (so a row with some horizons masked
            # contributes only to the unmasked ones).  Single-horizon keeps
            # the existing masked-select + scalar-loss path, bit-identical
            # to pre-patch behaviour.
            if multi_horizon:
                if multi_horizon_loss_module is not None:
                    loss = multi_horizon_loss_module(outputs, y, mask)
                else:
                    loss = _multi_horizon_loss(outputs, y, mask, loss_fn, horizon_weights)
                if loss is None:
                    continue
            else:
                idx = mask.nonzero(as_tuple=True)[0]
                if len(idx) == 0:
                    continue
                m_outputs = {
                    k: v[idx] for k, v in outputs.items() if torch.is_tensor(v)
                }
                m_target = y[idx]
                loss = loss_fn(m_outputs, m_target)

            # DANN: domain CE loss on outputs["domain_logits"]. GRL in model
            # already reverses the gradient, so we ADD the domain loss (the
            # adversarial sign comes from GRL backward, not from negating here).
            if use_dann and domain is not None and "domain_logits" in outputs:
                d_logits = outputs["domain_logits"]
                if multi_horizon:
                    d_logits_sel, d_target_sel = d_logits, domain
                else:
                    d_logits_sel = d_logits[idx]
                    d_target_sel = domain[idx]
                if d_logits_sel.shape[0] > 0:
                    domain_loss = torch.nn.functional.cross_entropy(
                        d_logits_sel, d_target_sel
                    )
                    if torch.isfinite(domain_loss):
                        loss = loss + domain_loss
                        with torch.no_grad():
                            d_pred = d_logits_sel.argmax(dim=-1)
                            d_acc = (d_pred == d_target_sel).float().mean().item()
                        domain_loss_sum += float(domain_loss.item())
                        domain_acc_sum += d_acc
                        domain_steps += 1

            # NaN guard: skip pathological batches
            if not torch.isfinite(loss):
                optimizer.zero_grad()
                global_step += 1
                continue

            optimizer.zero_grad()
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            # Skip step if grad norm is inf/nan — clip_grad_norm_ can produce
            # NaN gradients when the original norm is huge (1e12+), which
            # corrupts model parameters on the next step.
            if not torch.isfinite(grad_norm):
                optimizer.zero_grad()
                global_step += 1
                continue
            # Apply linear LR warmup *before* the optimizer step. Once past
            # ``warmup_steps`` this is a no-op and ReduceLROnPlateau owns the LR.
            _apply_warmup(global_step, warmup_steps, lr, optimizer)
            if use_sam:
                # SAM two-pass: first_step perturbs params to theta+epsilon,
                # then we MUST recompute the *exact same* forward + loss
                # assembly at the perturbed parameters so g_SAM = grad
                # L(theta+eps). second_step rolls back theta and applies the
                # base AdamW step using g_SAM.
                #
                # Stochastic dropout introduces a small extra noise term in
                # the second pass (not the same dropout mask as pass 1); the
                # paper found this acceptable, and forcing identical masks
                # would require manual RNG state save/restore that is brittle
                # across model variants.
                optimizer.first_step(zero_grad=True)
                outputs2 = _forward_with_regime(
                    model, x_feat, x_raw, regime_prior, multi_horizon,
                )
                if multi_horizon:
                    if multi_horizon_loss_module is not None:
                        loss2 = multi_horizon_loss_module(outputs2, y, mask)
                    else:
                        loss2 = _multi_horizon_loss(
                            outputs2, y, mask, loss_fn, horizon_weights,
                        )
                    if loss2 is None:
                        # Should not happen (mask identical to first pass) but
                        # be defensive: skip second_step, restore params.
                        # Manual rollback because second_step requires grads.
                        for group in optimizer.param_groups:
                            for p in group["params"]:
                                e_w = optimizer.state[p].get("e_w", None)
                                if e_w is not None:
                                    p.data.sub_(e_w)
                                    optimizer.state[p].pop("e_w", None)
                        optimizer.zero_grad()
                        global_step += 1
                        continue
                else:
                    # Reuse ``idx`` and ``m_target`` from the first pass —
                    # they depend only on ``mask`` and ``y`` which are
                    # unchanged. Re-slice ``outputs2`` with the same idx.
                    m_outputs2 = {
                        k: v[idx] for k, v in outputs2.items()
                        if torch.is_tensor(v)
                    }
                    loss2 = loss_fn(m_outputs2, m_target)
                # Replicate DANN domain CE add-on at perturbed params.
                if use_dann and domain is not None and "domain_logits" in outputs2:
                    d_logits2 = outputs2["domain_logits"]
                    if multi_horizon:
                        d_logits_sel2, d_target_sel2 = d_logits2, domain
                    else:
                        d_logits_sel2 = d_logits2[idx]
                        d_target_sel2 = domain[idx]
                    if d_logits_sel2.shape[0] > 0:
                        domain_loss2 = torch.nn.functional.cross_entropy(
                            d_logits_sel2, d_target_sel2
                        )
                        if torch.isfinite(domain_loss2):
                            loss2 = loss2 + domain_loss2
                if not torch.isfinite(loss2):
                    # Pathological perturbed loss; rollback manually and skip.
                    for group in optimizer.param_groups:
                        for p in group["params"]:
                            e_w = optimizer.state[p].get("e_w", None)
                            if e_w is not None:
                                p.data.sub_(e_w)
                                optimizer.state[p].pop("e_w", None)
                    optimizer.zero_grad()
                    global_step += 1
                    continue
                loss2.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.second_step(zero_grad=True)
            else:
                optimizer.step()

            # EMA update after the parameter step. No-op when use_ema=False.
            if ema_model is not None:
                ema_model.update_parameters(model)

            train_loss_sum += loss.item()
            train_steps += 1
            global_step += 1

        avg_train_loss = train_loss_sum / max(train_steps, 1)

        # ===== Validation =====
        # Evaluate both the live model and (if enabled) the EMA model every
        # epoch so we can save whichever wins the selection metric separately.
        def _run_val(eval_model: nn.Module) -> Dict[str, Any]:
            eval_model.eval()
            loss_sum = 0.0
            steps = 0
            om = OnlineMetrics()
            preds_all: list = []
            targets_all: list = []
            with torch.no_grad():
                for batch in val_loader:
                    x_feat, x_raw, regime_prior, y, mask, _ = _unpack_batch(
                        batch, dual_path, has_regime_prior, has_domain=use_dann,
                    )
                    x_feat = x_feat.to(device_obj, non_blocking=True)
                    if x_raw is not None:
                        x_raw = x_raw.to(device_obj, non_blocking=True)
                    if regime_prior is not None:
                        regime_prior = regime_prior.to(device_obj, non_blocking=True)
                    y = y.to(device_obj, non_blocking=True)
                    mask = mask.to(device_obj, non_blocking=True)

                    outputs = _forward_with_regime(
                        eval_model, x_feat, x_raw, regime_prior, multi_horizon,
                    )

                    if multi_horizon:
                        if multi_horizon_loss_module is not None:
                            loss = multi_horizon_loss_module(outputs, y, mask)
                        else:
                            loss = _multi_horizon_loss(outputs, y, mask, loss_fn, horizon_weights)
                        if loss is None:
                            continue
                        loss_sum += loss.item()
                        steps += 1
                        # Track metrics on the PRIMARY horizon (defaults to
                        # index 0 = shortest horizon; Block D sets this to the
                        # index of horizon_sec in horizons_sec so selection
                        # targets y_600 even when shorter horizons are aux).
                        h_idx = primary_horizon_idx
                        m0 = mask[:, h_idx].nonzero(as_tuple=True)[0]
                        if len(m0) > 0:
                            pred_np = outputs["point_pred_by_horizon"][m0, h_idx].cpu().numpy()
                            target_np = y[m0, h_idx].cpu().numpy()
                            om.update(pred_np, target_np)
                            preds_all.append(pred_np); targets_all.append(target_np)
                    else:
                        idx = mask.nonzero(as_tuple=True)[0]
                        if len(idx) == 0:
                            continue
                        m_outputs = {k: v[idx] for k, v in outputs.items() if torch.is_tensor(v)}
                        m_target = y[idx]
                        loss = loss_fn(m_outputs, m_target)
                        loss_sum += loss.item()
                        steps += 1
                        pred_np = outputs["point_pred"][idx].cpu().numpy()
                        target_np = y[idx].cpu().numpy()
                        om.update(pred_np, target_np)
                        preds_all.append(pred_np); targets_all.append(target_np)

            avg_loss = loss_sum / max(steps, 1)
            pearson = om.corr()
            r2 = om.r2()

            # Compute Spearman from accumulated full arrays (memory ~4-5k
            # samples × 8 bytes ≈ 40 kB, trivial). Fallback to Pearson if
            # scipy is unavailable (should never happen in this repo).
            sigma_ratio = 0.0
            beta = 0.0
            if preds_all:
                p_full = np.concatenate(preds_all).astype(np.float64)
                t_full = np.concatenate(targets_all).astype(np.float64)
                try:
                    from scipy.stats import spearmanr
                    spearman = float(spearmanr(p_full, t_full).statistic)
                    if not np.isfinite(spearman):
                        spearman = 0.0
                except Exception:
                    spearman = pearson
                # σ_ŷ/σ_y and β diagnostics — variance-collapse early-warn.
                # Per CLAUDE.md anti-pattern #11: σ_ŷ/σ_y < 20% means model
                # is outputting near-constant; any IC is spurious.
                sp = float(np.std(p_full))
                st = float(np.std(t_full))
                sigma_ratio = sp / st if st > 1e-12 else 0.0
                if sp > 1e-12:
                    cov = float(np.mean((p_full - p_full.mean()) * (t_full - t_full.mean())))
                    beta = cov / (sp * sp)
            else:
                spearman = 0.0

            composite = 0.5 * pearson + 0.5 * spearman
            return {
                "val_loss": avg_loss,
                "val_corr": pearson,
                "val_spearman": spearman,
                "val_composite": composite,
                "val_r2": r2,
                "val_sigma_ratio": sigma_ratio,
                "val_beta": beta,
            }

        raw_val = _run_val(model)
        avg_val_loss = raw_val["val_loss"]
        val_corr = raw_val["val_corr"]
        val_spearman = raw_val["val_spearman"]
        val_composite = raw_val["val_composite"]
        val_r2 = raw_val["val_r2"]

        # Also evaluate the EMA snapshot (if enabled)
        ema_val = None
        if ema_model is not None:
            ema_val = _run_val(ema_model)

        # Scalar used for scheduler + checkpoint gate. "composite" targets
        # pooled Pearson AND Spearman simultaneously (y_600 push design).
        if val_metric == "composite":
            selector = val_composite
        else:
            selector = val_corr

        # ===== LR scheduler step =====
        scheduler.step(selector)

        # ===== Epoch summary =====
        current_lr = optimizer.param_groups[0]["lr"]
        line = (
            f"Epoch {epoch:3d}/{epochs} | "
            f"train_loss={avg_train_loss:.6f} | "
            f"val_loss={avg_val_loss:.6f} | "
            f"P={val_corr:+.4f} S={val_spearman:+.4f} C={val_composite:+.4f} | "
            f"σŷ/σy={raw_val.get('val_sigma_ratio', 0.0):.3f} β={raw_val.get('val_beta', 0.0):+.3f} | "
            f"r2={val_r2:.4f} | lr={current_lr:.2e}"
        )
        if ema_val is not None:
            line += (
                f" | EMA P={ema_val['val_corr']:+.4f} "
                f"S={ema_val['val_spearman']:+.4f} C={ema_val['val_composite']:+.4f} "
                f"σŷ/σy={ema_val.get('val_sigma_ratio', 0.0):.3f}"
            )
        print(line)

        # ===== Early stopping & checkpointing =====
        # σ-ratio gate: reject epochs with σŷ/σy < 0.02 — these are init-noise
        # epochs where Pearson is spuriously high due to ~0 predictions
        # accidentally correlating with y. Anti-pattern #11 mitigation.
        sigma_ratio = raw_val.get('val_sigma_ratio', 0.0)
        sigma_ok = sigma_ratio >= 0.02
        best_selector = (
            best_metrics.get("val_composite", -1.0) if val_metric == "composite"
            else best_metrics.get("val_corr", -1.0)
        )
        if sigma_ok and selector > best_selector + 5e-4:
            epochs_no_improve = 0
            best_metrics = {
                "best_epoch": epoch,
                "val_loss": avg_val_loss,
                "val_corr": val_corr,
                "val_spearman": val_spearman,
                "val_composite": val_composite,
                "val_r2": val_r2,
            }
            ckpt = {
                "state": model.state_dict(),
                "class": type(model).__name__,
                "config": _extract_model_config(model),
            }
            torch.save(ckpt, os.path.join(out_dir, "best_model.pt"))
        else:
            epochs_no_improve += 1

        # ===== EMA best-so-far tracking (separate checkpoint) =====
        if ema_val is not None:
            ema_selector = (
                ema_val["val_composite"] if val_metric == "composite"
                else ema_val["val_corr"]
            )
            best_ema_selector = (
                best_ema_metrics.get("val_composite", -1.0) if val_metric == "composite"
                else best_ema_metrics.get("val_corr", -1.0)
            )
            ema_sigma_ratio = ema_val.get('val_sigma_ratio', 0.0)
            ema_sigma_ok = ema_sigma_ratio >= 0.02
            if ema_sigma_ok and ema_selector > best_ema_selector + 5e-4:
                best_ema_metrics = {
                    "best_epoch": epoch,
                    "val_loss": ema_val["val_loss"],
                    "val_corr": ema_val["val_corr"],
                    "val_spearman": ema_val["val_spearman"],
                    "val_composite": ema_val["val_composite"],
                    "val_r2": ema_val["val_r2"],
                }
                ema_ckpt = {
                    "state": ema_model.module.state_dict(),
                    "class": type(ema_model.module).__name__,
                    "config": _extract_model_config(ema_model.module),
                }
                torch.save(ema_ckpt, os.path.join(out_dir, "ema_best.pt"))

        # ===== Top-K checkpoint capture (for SWA / median-ensemble) =====
        # Save each epoch's checkpoint into a per-fold topk/ folder tagged
        # by epoch and val_corr. scripts/ensemble_topk.py selects the K
        # epochs with highest val_corr and averages their test predictions.
        # Storage cost: ~300KB/epoch × ~25 epochs ≈ 7MB/fold — trivial.
        topk_dir = os.path.join(out_dir, "topk")
        os.makedirs(topk_dir, exist_ok=True)
        topk_ckpt = {
            "state": model.state_dict(),
            "class": type(model).__name__,
            "config": _extract_model_config(model),
            "epoch": epoch,
            "val_corr": float(val_corr),
            "val_loss": float(avg_val_loss),
        }
        torch.save(topk_ckpt, os.path.join(topk_dir, f"epoch_{epoch:03d}.pt"))

        if epochs_no_improve >= patience:
            print(f"Early stopping at epoch {epoch} (patience={patience}).")
            break

    # --- persist metrics -----------------------------------------------------
    out = dict(best_metrics)
    if best_ema_metrics:
        out["ema"] = best_ema_metrics
    out["val_metric"] = val_metric
    with open(os.path.join(out_dir, "metrics.json"), "w") as f:
        json.dump(out, f, indent=2)

    return out

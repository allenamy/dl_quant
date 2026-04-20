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
import os
import random
from typing import Any, Callable, Dict, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .dataset import DayChunkedSampler
from .dul_loss import compute_dul_loss
from .losses import quantile_loss


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
    """Seed Python's ``random``, NumPy and PyTorch for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


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
    ]
    config: Dict[str, Any] = {}
    for attr in candidate_attrs:
        if hasattr(model, attr):
            val = getattr(model, attr)
            # Only record simple primitive types (not nn.Modules / tensors)
            if isinstance(val, (int, float, bool, str)):
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
):
    """Normalize batch tuple to 5-slot form (x_feat, x_raw, regime_prior, y, mask).

    Absent parts are None. Supported shapes:
      - 3-tuple: (x_feat, y, mask)                        -> Path A only
      - 4-tuple: (x_feat, x_raw, y, mask)                 -> Dual path
      - 5-tuple: (x_feat, x_raw, regime_prior, y, mask)   -> Dual + prior
    """
    if has_regime_prior:
        x_feat, x_raw, regime_prior, y, mask = batch
        return x_feat, x_raw, regime_prior, y, mask
    if dual_path:
        x_feat, x_raw, y, mask = batch
        return x_feat, x_raw, None, y, mask
    x_feat, y, mask = batch
    return x_feat, None, None, y, mask


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
    alpha_u = _pos_or_default(cfg.get("utility_alpha"), 1.0)
    lambda_pearson = _pos_or_default(cfg.get("lambda_pearson"), 0.0)
    focal_threshold = _pos_or_default(cfg.get("focal_threshold"), 0.0)
    focal_gamma = _pos_or_default(cfg.get("focal_gamma"), 2.0)
    n_pairs = cfg.get("n_pairs", None)

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
            utility_alpha=alpha_u,
            n_pairs=n_pairs,
            return_parts=False,
        )
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

    # Detect 5-tuple mode (with regime_prior)
    sample = train_dataset[0]
    has_regime_prior = len(sample) == 5

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
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=lr, weight_decay=weight_decay,
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

    for epoch in range(1, epochs + 1):
        # Refresh day-chunked sampler RNG so day order varies per epoch.
        # No-op when falling back to shuffle=True DataLoader.
        if train_sampler is not None:
            train_sampler.set_epoch(epoch)

        # ===== Training =====
        model.train()
        train_loss_sum = 0.0
        train_steps = 0

        for batch in train_loader:
            # Only pass ``all_horizons`` when multi-horizon is active.  This
            # keeps the kwarg invisible to V2 / legacy models (whose forward
            # doesn't know about it) and makes single-horizon runs
            # bit-identical to the pre-multi-horizon trainer.
            x_feat, x_raw, regime_prior, y, mask = _unpack_batch(
                batch, dual_path, has_regime_prior,
            )
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
                    x_feat, x_raw, regime_prior, y, mask = _unpack_batch(
                        batch, dual_path, has_regime_prior,
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
            else:
                spearman = 0.0

            composite = 0.5 * pearson + 0.5 * spearman
            return {
                "val_loss": avg_loss,
                "val_corr": pearson,
                "val_spearman": spearman,
                "val_composite": composite,
                "val_r2": r2,
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
            f"r2={val_r2:.4f} | lr={current_lr:.2e}"
        )
        if ema_val is not None:
            line += (
                f" | EMA P={ema_val['val_corr']:+.4f} "
                f"S={ema_val['val_spearman']:+.4f} C={ema_val['val_composite']:+.4f}"
            )
        print(line)

        # ===== Early stopping & checkpointing =====
        best_selector = (
            best_metrics.get("val_composite", -1.0) if val_metric == "composite"
            else best_metrics.get("val_corr", -1.0)
        )
        if selector > best_selector + 5e-4:
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
            if ema_selector > best_ema_selector + 5e-4:
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

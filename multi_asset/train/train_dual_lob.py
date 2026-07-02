"""Standalone trainer for the DUAL-LOB model (Stage D2) — perp deep-book residual.

WHAT THIS IS
------------
A self-contained driver that reproduces ``run_pipeline_v3.py``'s multi-day
walk-forward wiring (fold construction with ``fold_test_starts``, per-fold
streaming stats + target normalisation, normalised dataset rebuild, checkpoint +
test eval) but:

  * instantiates ``DualLOBREGArch(use_perp_residual=True, ...)`` — the REG_arch
    subclass that fuses the PERP deep order book as a zero-init gated residual —
    instead of the plain ``DualPathLOBModelV3``; and
  * uses ``DualLOBDataset`` (data/npz_duallob), which returns the perp deep book
    ``x_raw_perp_deep`` as the trailing element of each batch tuple; and
  * threads ``x_raw_perp_deep=`` into the model on every train / val / test
    forward.

WHY A STANDALONE LOOP (not trainer_v2)
--------------------------------------
``src/training/trainer_v2.py::train_one_fold_v2`` is excellent but its forward
helper (``_forward_with_regime``) is hardcoded to ``model(x_feat, x_raw, ...)``
and has NO channel for the extra ``x_raw_perp_deep`` input, and its
``_unpack_batch`` only understands 3/4/5-tuples (ours is a 6-tuple). Editing
``src/`` is disallowed, so we REPLICATE the minimal single-horizon training loop
here (this experiment is single-horizon: horizons_sec=[600], n_horizons=1) while
REUSING, by import only, the exact loss/seed/checkpoint-config helpers from
``trainer_v2`` so the loss composition (dul_config), σ-gate best-ckpt rule, EMA,
LR warmup + ReduceLROnPlateau, and DayChunkedSampler are byte-for-byte the proven
ones. ``run_pipeline_v3.py`` is NOT imported or modified.

The minimal loop here intentionally covers only the single-horizon, dual-path +
regime-prior case (what perp_strong_duallob / perp_roll_duallob configs use). It
is NOT a general trainer.

CLI
---
  python multi_asset/train/train_dual_lob.py --config configs/v5push/perp_strong_duallob.json
  python multi_asset/train/train_dual_lob.py --config <cfg> --start-fold 0 --max-folds 1 --seed 42
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as osp
import sys
import time
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

_REPO = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# Import-only reuse of the proven trainer internals (no edits to src/).
from src.training.dataset import (  # noqa: E402
    DayChunkedSampler,
    LOBDatasetV2,
    build_time_series_folds,
)
from src.training.trainer import OnlineMetrics  # noqa: E402
from src.training.trainer_v2 import (  # noqa: E402
    _apply_warmup,
    _build_loss_fn_for_dul,
    _extract_model_config,
    _multi_horizon_loss,
    _seed_everything,
)

from multi_asset.data.dual_lob_dataset import DualLOBDataset  # noqa: E402
from multi_asset.data.sliced_lob_dataset import SlicedLOBDataset  # noqa: E402
from multi_asset.model.dual_lob_regarch import DualLOBREGArch  # noqa: E402


# --------------------------------------------------------------------------- #
# Model construction                                                          #
# --------------------------------------------------------------------------- #
# Base REG_arch kwargs accepted by DualPathLOBModelV3 (mirrors the allow-list in
# run_pipeline_v3.build_model so unknown legacy keys are dropped, not passed).
_BASE_ALLOWED = {
    "d_model", "d_raw", "n_mask_blocks", "n_cross_layers", "patch_size",
    "attn_nhead", "attn_d_ff", "d_prior", "dropout", "n_horizons", "n_symbols",
    "use_monotonic_quantile", "use_masknet", "use_gdcn", "use_raw_path",
    "use_attention", "use_conv", "use_revin", "use_channel_mix_conv",
    "use_level_attention_pool", "use_patch_attention_pool", "use_ppnet_gate",
    "use_multi_scale", "backbone_kind", "backbone_kwargs", "output_scale_init",
    "use_regime_film", "regime_film_hidden", "fusion_kind", "use_regime_bias",
    "regime_bias_hidden", "use_sign_head", "use_direction_aware_head",
    "use_decoupled_sign_mag_head", "use_multi_res_pool", "multi_res_recent",
    "multi_res_mid", "use_film_multistage", "use_tv_film", "n_tv_channels",
    "use_xattn_regime", "use_seq_direction_head", "film_gate_deeper_trunk",
    "use_se_block_input",
}
# Perp-residual extension kwargs (consumed by DualLOBREGArch only).
# ``use_snapshot_skip`` (linear last-timestep snapshot readout),
# ``use_rich_regime`` (14-feature regime FiLM extractor) and ``use_oi_regime``
# (regime FiLM ALSO consumes regime_prior -> OI/funding positioning modulates
# γ/β) are also DualLOBREGArch __init__ kwargs, so they ride the same routing
# set: both build_dual_lob_model and build_v2arch_model pass **perp to the
# constructor.
# ``use_regime_moe`` (K=2 soft-MoE on the FINAL pooled representation, routed by
# regime_prior so positioning/price STATE selects the functional form —
# momentum-expert vs reversion-expert) + ``moe_lb_weight`` (the ~0.01
# load-balance aux-loss coefficient surfaced as out["moe_lb_loss"]) are also
# DualLOBREGArch __init__ kwargs and ride the same routing set.
# ``use_regime_gated_mh`` / ``use_regime_gated_moe`` (REGIME-GATED lever
# activation: learnable sigmoid gates that turn the y_180 multi-horizon aux ON in
# strong / OFF in weak, and scale the regime-MoE residual up in weak / down in
# strong — resolving the diagnosed strong-vs-weak lever conflict in ONE model;
# both zero-init => byte-identical when off) are also DualLOBREGArch __init__
# kwargs and ride the same routing set.
_PERP_KEYS = {"use_perp_residual", "perp_n_levels", "d_perp", "perp_alpha_init",
              "use_snapshot_skip", "use_rich_regime", "use_oi_regime",
              "use_regime_moe", "moe_lb_weight",
              "use_regime_gated_mh", "use_regime_gated_moe",
              # Stage-0B D1 fixed-regime-state substrate (forwarded to DualLOBREGArch):
              "use_fixed_regime_state", "use_state_prior", "d_state_prior",
              "use_output_gain", "regime_state_fit_samples"}


def build_dual_lob_model(model_cfg: dict, n_features: int,
                         n_levels: int) -> DualLOBREGArch:
    """Instantiate ``DualLOBREGArch`` from a config ``model`` block.

    ``n_levels`` is the SPOT Path-B level count (from the data). The perp
    residual's level count comes from ``perp_n_levels`` in the config.
    """
    base = {k: v for k, v in model_cfg.items() if k in _BASE_ALLOWED}
    perp = {k: v for k, v in model_cfg.items() if k in _PERP_KEYS}
    # Respect the config: perp residual is ON only when explicitly requested.
    # When the key is absent (e.g. the spot-64 BASE config) the residual is OFF
    # and the model is byte-identical to the plain REG_arch parent.
    perp.setdefault("use_perp_residual", False)
    unknown = set(model_cfg) - _BASE_ALLOWED - _PERP_KEYS - {"_comment"}
    if unknown:
        print(f"[train_dual_lob] WARNING: unknown model_cfg keys ignored: "
              f"{sorted(unknown)}")
    print(f"[train_dual_lob] DualLOBREGArch base n_features={n_features} "
          f"n_levels={n_levels} perp={perp}")
    return DualLOBREGArch(n_features=n_features, n_levels=n_levels, **base, **perp)


# --------------------------------------------------------------------------- #
# Minimal single-horizon training loop (perp-residual aware)                   #
# --------------------------------------------------------------------------- #
def _forward_dual(model: nn.Module, x_feat, x_raw, regime_prior, x_perp,
                  all_horizons: bool = False):
    """Single forward threading the perp deep book into the model.

    ``x_perp`` is ``None`` for the perp-OFF arms (use_perp_residual=false): the
    model (``DualLOBREGArch``) treats ``x_raw_perp_deep=None`` as an exact no-op
    (the residual term is identically 0), so the SAME forward serves all 3 arms.

    ``all_horizons=True`` (mh180 multi-horizon) makes the model emit
    ``quantiles_by_horizon`` / ``point_pred_by_horizon`` for ``_multi_horizon_loss``.
    """
    kwargs: Dict[str, Any] = {"x_raw_perp_deep": x_perp, "all_horizons": all_horizons}
    if regime_prior is not None:
        kwargs["regime_prior"] = regime_prior
    return model(x_feat, x_raw, **kwargs)


def train_one_fold_dual(
    *,
    model: nn.Module,
    train_dataset,
    val_dataset,
    out_dir: str,
    device: str = "cpu",
    epochs: int = 16,
    batch_size: int = 1024,
    lr: float = 6e-4,
    weight_decay: float = 1e-3,
    patience: int = 10,
    grad_clip: float = 1.0,
    dul_config: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
    val_metric: str = "composite",
    use_ema: bool = False,
    ema_decay: float = 0.999,
    num_workers: int = 0,
    prefetch_factor: int = 2,
    max_steps_per_epoch: Optional[int] = None,
    has_perp: bool = True,
    save_epoch_ckpts: bool = False,
    tail_weight: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Replica of ``trainer_v2.train_one_fold_v2`` for the single-horizon,
    dual-path + regime-prior + (optional) perp-residual case.

    Reuses the proven loss (``_build_loss_fn_for_dul``), σ-gate best-ckpt rule,
    EMA, warmup + ReduceLROnPlateau and DayChunkedSampler. When ``has_perp`` is
    True every forward threads ``x_raw_perp_deep`` (the trailing batch element of
    a ``DualLOBDataset`` tuple); when False (the perp-OFF arms) the dataset is a
    plain ``LOBDatasetV2`` whose tuples carry NO perp element and the perp input
    is passed as ``None`` (an exact model no-op) so all 3 arms share this loop.

    CHECKPOINT GATE + FALLBACK (the bug this fixes)
    -----------------------------------------------
    The proven σ-gate (anti-pattern #24) only writes ``best_model.pt`` /
    ``ema_best.pt`` on epochs with σŷ/σy ≥ 0.02. On the LEAK-FREE perp target the
    raw point-pred σ can stay < 0.02 for ALL epochs (real-but-weak signal *or* a
    variance collapse — we are MEASURING, so we must not crash). In that case the
    σ-gate saves NOTHING and downstream eval dies with FileNotFoundError. We keep
    the σ-gate as the PRIMARY selector but ALSO track, across ALL epochs
    regardless of σ, the best-composite (0.5·P+0.5·S on val) state as a FALLBACK.
    After training, if the σ-gate never fired we persist the fallback to
    ``best_model.pt`` / ``ema_best.pt`` so eval always runs, and we record which
    path was used plus the saved checkpoint's σŷ/σy in ``metrics.json`` so the
    reader can judge whether a low-σ number is trustworthy.

    ``max_steps_per_epoch`` caps optimizer steps per epoch (smoke tests only;
    None = full epoch).
    """
    if seed is not None:
        _seed_everything(seed)

    os.makedirs(out_dir, exist_ok=True)
    device_obj = torch.device(device)
    model = model.to(device_obj)

    if dul_config is not None:
        loss_fn: Callable = _build_loss_fn_for_dul(dul_config)
    else:
        from src.training.losses import quantile_loss

        def loss_fn(outputs, target):  # type: ignore[misc]
            return quantile_loss(outputs["quantiles"], target)

    if val_metric not in ("val_corr", "composite"):
        raise ValueError(f"val_metric must be 'val_corr'|'composite', got {val_metric!r}")

    # --- multi-horizon (mh180) wiring ---------------------------------------
    # The model emits per-horizon outputs under all_horizons=True; the train loss
    # is the weighted per-horizon sum (_multi_horizon_loss with horizon_weights),
    # while VAL selection stays on the PRIMARY horizon (last = y_600) only (D6:
    # "val selector unchanged, composite on y_600"). Single-horizon path (n=1) is
    # byte-identical to before (all_horizons stays effectively off, primary=only).
    n_horizons = int(getattr(model, "n_horizons", 1) or 1)
    multi_horizon = n_horizons > 1
    primary_idx = n_horizons - 1
    horizon_weights = None
    if multi_horizon and dul_config is not None:
        hw = dul_config.get("horizon_weights")
        horizon_weights = list(hw) if hw is not None else [1.0] * n_horizons
    if multi_horizon:
        print(f"[train_dual_lob] MULTI-HORIZON: n_horizons={n_horizons} "
              f"primary_idx={primary_idx} horizon_weights={horizon_weights}")

    # --- loaders: DayChunkedSampler when preload is off, else plain order ----
    # WORKER SAFETY (the FUSE-deadlock constraint, MEMORY.md::pod_fuse_deadlock)
    # -------------------------------------------------------------------------
    # The historical reason num_workers was pinned to 0 here was a MooseFS/FUSE
    # mount deadlock: worker processes that lazily read .npz FROM the mount
    # (preload=False path → ``_load_day`` → disk) could wedge on a degraded
    # FUSE mount. With preload=True the fold is ALREADY fully resident in this
    # process's RAM (self._pre_X / _pre_X_raw / ... numpy arrays); fork()ed
    # workers inherit those pages COPY-ON-WRITE and ``__getitem__`` is a pure
    # in-RAM slice (NO disk, NO mount access) — so workers cannot touch FUSE and
    # the deadlock is structurally impossible. They also do NOT duplicate the
    # ~95 GB resident arrays (COW: read-only slicing never writes the pages, so
    # the OS shares one physical copy across all workers).
    #
    # Therefore the rule is INVERTED from the old code: workers are SAFE +
    # beneficial exactly when preloaded (data-bound main thread → overlap batch
    # assembly + pinned H2D copy with GPU compute), and UNSAFE when not (lazy
    # disk/mount reads). We force the ``fork`` start method so COW sharing of the
    # preloaded arrays actually happens (spawn would re-import + re-preload per
    # worker → 95 GB × N OOM). ``num_workers``/``prefetch_factor`` come from the
    # config; pin_memory + non_blocking (_to_dev) overlap the CPU→GPU copy.
    preloaded = getattr(train_dataset, "_preloaded", False)
    # ARM B (0C tail-weight): WeightedRandomSampler over the preloaded train targets
    # (w = 1 + k·1{|y|≥train top-quintile}); loss math UNCHANGED. Needs preload so the
    # per-sample targets are resident (_pre_y / _pre_mask).
    tail_sampler = None
    if tail_weight:
        if not preloaded:
            raise ValueError("tail_weight arm requires preload=True (needs _pre_y).")
        from multi_asset.train.arm_utils import tail_sample_weights
        w, thr = tail_sample_weights(
            train_dataset._pre_y, getattr(train_dataset, "_pre_mask", None),
            k=tail_weight.get("k", 2.0), quantile=tail_weight.get("quantile", 0.8))
        _g = torch.Generator(); _g.manual_seed(int(seed) if seed is not None else 42)
        tail_sampler = torch.utils.data.WeightedRandomSampler(
            torch.as_tensor(w, dtype=torch.double), num_samples=int((w > 0).sum()),
            replacement=True, generator=_g)
        print(f"[arm] tail_weight k={tail_weight.get('k', 2.0)} thr={thr:.4f} "
              f"tailfrac={(w > 1).mean():.3f} n={int((w > 0).sum())}", flush=True)
    if preloaded:
        _nw = num_workers          # COW-safe: workers read in-RAM tensors only
    else:
        _nw = 0                    # lazy disk/mount reads → keep single-process
    _mp_ctx = "fork" if _nw > 0 else None  # COW requires fork (not spawn)
    use_day_sampler = (
        not preloaded
        and hasattr(train_dataset, "_offsets")
        and hasattr(train_dataset, "_day_paths")
    )
    _loader_common = dict(
        num_workers=_nw,
        persistent_workers=_nw > 0,
        prefetch_factor=prefetch_factor if _nw > 0 else None,
        multiprocessing_context=_mp_ctx if _nw > 0 else None,
        pin_memory=torch.cuda.is_available(),
        drop_last=True,
    )
    if use_day_sampler:
        sampler = DayChunkedSampler(
            train_dataset, chunk_size=32, shuffle_days=True,
            shuffle_within_day=True, seed=42,
        )
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, sampler=sampler,
            **_loader_common,
        )
    elif tail_sampler is not None:
        # ARM B: weighted sampling REPLACES shuffle (never both together).
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, sampler=tail_sampler,
            **_loader_common,
        )
    else:
        # Explicit generator seeded from the fold seed pins the shuffle
        # permutation so it is IDENTICAL whether num_workers is 0 or >0 (the
        # permutation is drawn in THIS process by RandomSampler; workers only
        # parallelise the __getitem__ fetch, not index generation). This makes
        # the nw=0-vs-nw>0 correctness gate bit-for-bit on batch ORDER.
        _shuffle_gen = torch.Generator()
        _shuffle_gen.manual_seed(int(seed) if seed is not None else 42)
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True,
            generator=_shuffle_gen,
            **_loader_common,
        )
    print(f"[train_dual_lob] train_loader: preloaded={preloaded} num_workers={_nw} "
          f"mp_ctx={_mp_ctx} persistent={_nw > 0} pin_memory={torch.cuda.is_available()}",
          flush=True)
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=0, pin_memory=torch.cuda.is_available(),
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=max(patience // 2, 2), min_lr=1e-6,
    )

    steps_per_epoch = max(len(train_dataset) // batch_size, 1)
    warmup_epochs = min(5, epochs // 4)
    warmup_steps = warmup_epochs * steps_per_epoch
    # EMA-fallback warmup: the EMA shadow is dominated by the random init for the
    # first epoch(s) (decay 0.999 needs many updates to forget init). A flukey
    # high val-composite at epoch 1 (when the EMA ~= init and σŷ/σy~0) must NOT be
    # picked as the low-σ fallback checkpoint (the bug this fixes: my earlier run
    # saved EMA epoch-1, flat). We therefore only let the EMA FALLBACK tracker
    # accept epochs >= ema_warmup_epochs (>= LR-warmup, and at least epoch 2 so we
    # never pick the init-dominated first epoch). If no warmed EMA epoch exists,
    # the EMA fallback stays empty and we fall back to the RAW best (see the
    # post-loop persistence block). The σ-gate PRIMARY path is unaffected.
    ema_warmup_epochs = max(2, warmup_epochs)
    global_step = 0

    ema_model = None
    if use_ema:
        _omd = 1.0 - float(ema_decay)

        def _ema_avg(avg_p, new_p, n):  # noqa: ARG001
            return avg_p + _omd * (new_p - avg_p)

        ema_model = torch.optim.swa_utils.AveragedModel(model, avg_fn=_ema_avg).to(device_obj)
        print(f"[train_dual_lob] EMA active (decay={ema_decay})")

    best_metrics: Dict[str, Any] = {}
    best_ema_metrics: Dict[str, Any] = {}
    epochs_no_improve = 0
    train_loss_hist: List[float] = []
    # Stage-0b instrumentation: per-epoch val history (raw AND EMA) so drift-fold
    # selection health is auditable offline (D5). Backward-compatible extra key.
    val_hist: List[Dict[str, Any]] = []
    if save_epoch_ckpts:
        os.makedirs(osp.join(out_dir, "epoch_ckpts"), exist_ok=True)
    # FALLBACK trackers (best composite over ALL epochs, ignore σ-gate). Hold the
    # full state_dict + config in RAM so we can persist the fallback after the
    # loop IFF the σ-gate never fired (see docstring). Cheap for this model size.
    fb_raw_sel = -1.0
    fb_raw_payload: Optional[Dict[str, Any]] = None
    fb_raw_meta: Dict[str, Any] = {}
    fb_ema_sel = -1.0
    fb_ema_payload: Optional[Dict[str, Any]] = None
    fb_ema_meta: Dict[str, Any] = {}

    def _unpack(batch):
        # has_perp=True  -> DualLOBDataset tuples (trailing x_perp):
        #   dual + regime : (x_feat, x_raw, regime_prior, y, mask, x_perp)
        #   dual, no rp   : (x_feat, x_raw,               y, mask, x_perp)
        # has_perp=False -> plain LOBDatasetV2 tuples (NO x_perp; x_perp=None):
        #   raw + regime  : (x_feat, x_raw, regime_prior, y, mask)
        #   raw, no rp    : (x_feat, x_raw,               y, mask)
        #   no raw        : (x_feat,                      y, mask)
        # The 5-tuple is ambiguous across the two modes (perp+no-regime vs
        # no-perp+regime) so we disambiguate on the explicit ``has_perp`` flag,
        # NOT on arity.
        if has_perp:
            if len(batch) == 6:
                x_feat, x_raw, regime_prior, y, mask, x_perp = batch
            elif len(batch) == 5:
                x_feat, x_raw, y, mask, x_perp = batch
                regime_prior = None
            else:
                raise RuntimeError(
                    f"DualLOBDataset batch must be 5- or 6-tuple, got len={len(batch)}"
                )
        else:
            x_perp = None
            if len(batch) == 5:
                x_feat, x_raw, regime_prior, y, mask = batch
            elif len(batch) == 4:
                x_feat, x_raw, y, mask = batch
                regime_prior = None
            elif len(batch) == 3:
                x_feat, y, mask = batch
                x_raw = None
                regime_prior = None
            else:
                raise RuntimeError(
                    f"LOBDatasetV2 batch must be 3/4/5-tuple, got len={len(batch)}"
                )
        return x_feat, x_raw, regime_prior, y, mask, x_perp

    def _to_dev(*ts):
        out = []
        for t in ts:
            out.append(t.to(device_obj, non_blocking=True) if t is not None else None)
        return out

    def _run_val(eval_model: nn.Module) -> Dict[str, Any]:
        eval_model.eval()
        om = OnlineMetrics()
        loss_sum = 0.0
        steps = 0
        preds_all: List[np.ndarray] = []
        targets_all: List[np.ndarray] = []
        with torch.no_grad():
            for batch in val_loader:
                x_feat, x_raw, regime_prior, y, mask, x_perp = _unpack(batch)
                x_feat, x_raw, regime_prior, x_perp, y, mask = _to_dev(
                    x_feat, x_raw, regime_prior, x_perp, y, mask)
                outputs = _forward_dual(eval_model, x_feat, x_raw, regime_prior, x_perp,
                                        all_horizons=multi_horizon)
                if multi_horizon:
                    # val_loss = weighted per-horizon (consistent with train); but
                    # SELECTION metrics (P/S/σ/β) use ONLY the PRIMARY horizon
                    # (point_pred = y_600) — D6: aux never enters the selector.
                    mh_loss = _multi_horizon_loss(outputs, y, mask, loss_fn, horizon_weights)
                    if mh_loss is None:
                        continue
                    pidx = mask[:, primary_idx].nonzero(as_tuple=True)[0]
                    if len(pidx) == 0:
                        continue
                    loss_sum += float(mh_loss.item()); steps += 1
                    pred_np = outputs["point_pred"][pidx].cpu().numpy()
                    tgt_np = y[pidx, primary_idx].cpu().numpy()
                    om.update(pred_np, tgt_np)
                    preds_all.append(pred_np); targets_all.append(tgt_np)
                    continue
                idx = mask.nonzero(as_tuple=True)[0]
                if len(idx) == 0:
                    continue
                # SKIP batch-level scalars (0-dim, e.g. regime-MoE lb loss) which
                # have no per-sample axis to slice; the val loss ignores the aux.
                m_out = {k: v[idx] for k, v in outputs.items()
                         if torch.is_tensor(v) and v.dim() > 0}
                m_tgt = y[idx]
                loss = loss_fn(m_out, m_tgt)
                loss_sum += float(loss.item())
                steps += 1
                pred_np = outputs["point_pred"][idx].cpu().numpy()
                tgt_np = y[idx].cpu().numpy()
                om.update(pred_np, tgt_np)
                preds_all.append(pred_np)
                targets_all.append(tgt_np)
        pearson = om.corr()
        r2 = om.r2()
        spearman = 0.0
        sigma_ratio = 0.0
        beta = 0.0
        if preds_all:
            pf = np.concatenate(preds_all).astype(np.float64)
            tf = np.concatenate(targets_all).astype(np.float64)
            try:
                from scipy.stats import spearmanr
                spearman = float(spearmanr(pf, tf).statistic)
                if not np.isfinite(spearman):
                    spearman = 0.0
            except Exception:
                spearman = pearson
            sp, st = float(np.std(pf)), float(np.std(tf))
            sigma_ratio = sp / st if st > 1e-12 else 0.0
            if sp > 1e-12:
                cov = float(np.mean((pf - pf.mean()) * (tf - tf.mean())))
                beta = cov / (sp * sp)
        composite = 0.5 * pearson + 0.5 * spearman
        return {
            "val_loss": loss_sum / max(steps, 1),
            "val_corr": pearson, "val_spearman": spearman,
            "val_composite": composite, "val_r2": r2,
            "val_sigma_ratio": sigma_ratio, "val_beta": beta,
        }

    for epoch in range(1, epochs + 1):
        if use_day_sampler:
            train_loader.sampler.set_epoch(epoch)  # type: ignore[attr-defined]
        model.train()
        tl_sum = 0.0
        tl_steps = 0
        for batch in train_loader:
            x_feat, x_raw, regime_prior, y, mask, x_perp = _unpack(batch)
            x_feat, x_raw, regime_prior, x_perp, y, mask = _to_dev(
                x_feat, x_raw, regime_prior, x_perp, y, mask)
            outputs = _forward_dual(model, x_feat, x_raw, regime_prior, x_perp,
                                    all_horizons=multi_horizon)
            if multi_horizon:
                # y/mask are (B, n_h); weighted per-horizon quantile loss (aux y_180
                # at horizon_weights[0], primary y_600 at horizon_weights[-1]).
                loss = _multi_horizon_loss(outputs, y, mask, loss_fn, horizon_weights)
                if loss is None:   # every horizon fully masked this batch
                    global_step += 1
                    continue
            else:
                idx = mask.nonzero(as_tuple=True)[0]
                if len(idx) == 0:
                    global_step += 1
                    continue
                # Per-sample index every (B,...) tensor; SKIP batch-level scalars
                # (0-dim, e.g. the regime-MoE load-balance aux loss) which have no
                # sample axis to slice.
                m_out = {k: v[idx] for k, v in outputs.items()
                         if torch.is_tensor(v) and v.dim() > 0}
                loss = loss_fn(m_out, y[idx])
            # regime-MoE load-balancing aux (guard #4): add moe_lb_weight·CV^2 of
            # the batch-mean router weights so both experts stay used. Batch-level
            # (uses the full-batch router weights, not the masked subset). No-op
            # unless use_regime_moe is on (key absent otherwise).
            if "moe_lb_loss" in outputs:
                lb_w = float(getattr(model, "moe_lb_weight", 0.0))
                if lb_w > 0.0:
                    loss = loss + lb_w * outputs["moe_lb_loss"]
            if not torch.isfinite(loss):
                optimizer.zero_grad()
                global_step += 1
                continue
            optimizer.zero_grad()
            loss.backward()
            gnorm = torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            if not torch.isfinite(gnorm):
                optimizer.zero_grad()
                global_step += 1
                continue
            _apply_warmup(global_step, warmup_steps, lr, optimizer)
            optimizer.step()
            if ema_model is not None:
                ema_model.update_parameters(model)
            tl_sum += float(loss.item())
            tl_steps += 1
            global_step += 1
            if max_steps_per_epoch is not None and tl_steps >= max_steps_per_epoch:
                break
        avg_tl = tl_sum / max(tl_steps, 1)
        train_loss_hist.append(avg_tl)

        raw_val = _run_val(model)
        ema_val = _run_val(ema_model) if ema_model is not None else None
        selector = raw_val["val_composite"] if val_metric == "composite" else raw_val["val_corr"]
        scheduler.step(selector)

        cur_lr = optimizer.param_groups[0]["lr"]
        line = (
            f"Epoch {epoch:3d}/{epochs} | train_loss={avg_tl:.6f} | "
            f"val_loss={raw_val['val_loss']:.6f} | "
            f"P={raw_val['val_corr']:+.4f} S={raw_val['val_spearman']:+.4f} "
            f"C={raw_val['val_composite']:+.4f} | "
            f"sigR={raw_val['val_sigma_ratio']:.3f} b={raw_val['val_beta']:+.3f} | "
            f"perp_a={float(_perp_alpha(model)):+.4f} | lr={cur_lr:.2e}"
        )
        if ema_val is not None:
            line += (f" | EMA P={ema_val['val_corr']:+.4f} "
                     f"S={ema_val['val_spearman']:+.4f} C={ema_val['val_composite']:+.4f}")
        print(line, flush=True)

        # --- Stage-0b: record per-epoch val history (raw + EMA) + optional ckpt.
        # sigma_ok flags whether this epoch is eligible for the σ-gated selector.
        def _vslim(d):
            return None if d is None else {
                "P": d["val_corr"], "S": d["val_spearman"],
                "composite": d["val_composite"], "sigma_ratio": d["val_sigma_ratio"],
                "beta": d["val_beta"], "loss": d["val_loss"],
            }
        val_hist.append({
            "epoch": epoch, "train_loss": avg_tl,
            "raw": _vslim(raw_val), "ema": _vslim(ema_val),
            "sigma_ok": bool(raw_val["val_sigma_ratio"] >= 0.02),
        })
        # Stage-0b fix: persist val_hist INCREMENTALLY each epoch to a tiny sidecar
        # file so the queue-runner can read per-epoch P/S/C mid-run (for the epoch-5
        # early-abort decision) instead of parsing logs. metrics.json is only
        # written at fold completion; val_hist.json is live.
        try:
            with open(osp.join(out_dir, "val_hist.json"), "w") as _vf:
                json.dump({"val_hist": val_hist, "epochs_ran": epoch,
                           "patience": patience}, _vf)
        except Exception:
            pass
        if save_epoch_ckpts:
            ep_payload = {"state": model.state_dict(), "class": type(model).__name__,
                          "config": _extract_model_config(model)}
            torch.save(ep_payload, osp.join(out_dir, "epoch_ckpts", f"raw_ep{epoch:03d}.pt"))
            if ema_model is not None and epoch >= ema_warmup_epochs:
                torch.save({"state": ema_model.module.state_dict(),
                            "class": type(ema_model.module).__name__,
                            "config": _extract_model_config(ema_model.module)},
                           osp.join(out_dir, "epoch_ckpts", f"ema_ep{epoch:03d}.pt"))

        # --- FALLBACK tracker: best composite over ALL epochs, σ-gate ignored.
        # Updated every epoch BEFORE the σ-gate so a run that never crosses σ=0.02
        # still has a checkpoint to persist. We keep the raw point-pred σ of the
        # winning epoch so metrics.json can flag a possibly-unreliable low-σ pick.
        if selector > fb_raw_sel:
            fb_raw_sel = selector
            fb_raw_payload = {
                "state": {k: v.detach().cpu().clone()
                          for k, v in model.state_dict().items()},
                "class": type(model).__name__,
                "config": _extract_model_config(model),
            }
            fb_raw_meta = {
                "best_epoch": epoch, "val_loss": raw_val["val_loss"],
                "val_corr": raw_val["val_corr"], "val_spearman": raw_val["val_spearman"],
                "val_composite": raw_val["val_composite"], "val_r2": raw_val["val_r2"],
                "val_sigma_ratio": raw_val["val_sigma_ratio"],
            }

        # σ-gate best-ckpt: only accept epochs with σŷ/σy ≥ 0.02 (anti-pattern #24).
        sigma_ok = raw_val["val_sigma_ratio"] >= 0.02
        best_sel = (best_metrics.get("val_composite", -1.0) if val_metric == "composite"
                    else best_metrics.get("val_corr", -1.0))
        if sigma_ok and selector > best_sel + 5e-4:
            epochs_no_improve = 0
            best_metrics = {
                "best_epoch": epoch, "val_loss": raw_val["val_loss"],
                "val_corr": raw_val["val_corr"], "val_spearman": raw_val["val_spearman"],
                "val_composite": raw_val["val_composite"], "val_r2": raw_val["val_r2"],
                "val_sigma_ratio": raw_val["val_sigma_ratio"],
            }
            torch.save({"state": model.state_dict(), "class": type(model).__name__,
                        "config": _extract_model_config(model)},
                       osp.join(out_dir, "best_model.pt"))
        else:
            epochs_no_improve += 1

        if ema_val is not None:
            ema_sel = ema_val["val_composite"] if val_metric == "composite" else ema_val["val_corr"]
            # FALLBACK tracker for EMA: best composite over WARMED epochs only
            # (epoch >= ema_warmup_epochs), σ ignored. The warmup guard prevents
            # picking the init-dominated epoch-1 EMA (flat, σ~0) as the low-σ
            # fallback ckpt. If NO warmed epoch is ever reached (very short run)
            # this stays empty and the post-loop block falls back to the RAW best.
            if epoch >= ema_warmup_epochs and ema_sel > fb_ema_sel:
                fb_ema_sel = ema_sel
                fb_ema_payload = {
                    "state": {k: v.detach().cpu().clone()
                              for k, v in ema_model.module.state_dict().items()},
                    "class": type(ema_model.module).__name__,
                    "config": _extract_model_config(ema_model.module),
                }
                fb_ema_meta = {
                    "best_epoch": epoch, "val_loss": ema_val["val_loss"],
                    "val_corr": ema_val["val_corr"], "val_spearman": ema_val["val_spearman"],
                    "val_composite": ema_val["val_composite"], "val_r2": ema_val["val_r2"],
                    "val_sigma_ratio": ema_val["val_sigma_ratio"],
                }
            best_ema_sel = (best_ema_metrics.get("val_composite", -1.0) if val_metric == "composite"
                            else best_ema_metrics.get("val_corr", -1.0))
            if ema_val["val_sigma_ratio"] >= 0.02 and ema_sel > best_ema_sel + 5e-4:
                best_ema_metrics = {
                    "best_epoch": epoch, "val_loss": ema_val["val_loss"],
                    "val_corr": ema_val["val_corr"], "val_spearman": ema_val["val_spearman"],
                    "val_composite": ema_val["val_composite"], "val_r2": ema_val["val_r2"],
                    "val_sigma_ratio": ema_val["val_sigma_ratio"],
                }
                torch.save({"state": ema_model.module.state_dict(),
                            "class": type(ema_model.module).__name__,
                            "config": _extract_model_config(ema_model.module)},
                           osp.join(out_dir, "ema_best.pt"))

        if epochs_no_improve >= patience:
            print(f"Early stopping at epoch {epoch} (patience={patience}).", flush=True)
            break

    # --- Persist FALLBACK checkpoints when the σ-gate never fired ------------
    # If no epoch had σŷ/σy ≥ 0.02 the σ-gate saved nothing, so best_model.pt /
    # ema_best.pt do not exist and eval would crash. Write the best-composite
    # fallback (tracked over ALL epochs) so eval ALWAYS runs. We record which
    # source ("sigma_gate" vs "fallback_low_sigma") and the saved checkpoint's
    # σŷ/σy so the reader can judge whether a low-σ IC is trustworthy.
    ckpt_provenance: Dict[str, Any] = {}
    best_path = osp.join(out_dir, "best_model.pt")
    if not osp.exists(best_path) and fb_raw_payload is not None:
        torch.save(fb_raw_payload, best_path)
        best_metrics = dict(fb_raw_meta)
        ckpt_provenance["best_source"] = "fallback_low_sigma"
        print(f"[train_dual_lob] σ-gate never fired (best raw σŷ/σy="
              f"{fb_raw_meta.get('val_sigma_ratio', float('nan')):.4f} < 0.02); "
              f"saved FALLBACK best_model.pt @ epoch {fb_raw_meta.get('best_epoch')}.",
              flush=True)
    elif osp.exists(best_path):
        ckpt_provenance["best_source"] = "sigma_gate"
    else:
        ckpt_provenance["best_source"] = "none"  # no val epochs at all (smoke edge)

    ema_path = osp.join(out_dir, "ema_best.pt")
    if use_ema:
        if osp.exists(ema_path):
            # σ-gate fired for the EMA on >=1 warmed epoch: keep that checkpoint.
            ckpt_provenance["ema_source"] = "sigma_gate"
        elif fb_ema_payload is not None:
            # σ-gate never fired but a WARMED EMA epoch exists: persist the best
            # warmed-EMA composite as the fallback (low-σ; flagged for the reader).
            torch.save(fb_ema_payload, ema_path)
            best_ema_metrics = dict(fb_ema_meta)
            ckpt_provenance["ema_source"] = "fallback_low_sigma"
            print(f"[train_dual_lob] σ-gate never fired for EMA (best WARMED EMA "
                  f"σŷ/σy={fb_ema_meta.get('val_sigma_ratio', float('nan')):.4f} < 0.02); "
                  f"saved FALLBACK ema_best.pt @ epoch {fb_ema_meta.get('best_epoch')}.",
                  flush=True)
        elif fb_raw_payload is not None:
            # No warmed-EMA epoch AND σ-gate never fired (very short run): the EMA
            # shadow is still init-dominated, so the SPEC fallback is the RAW best
            # (NOT the flat early-EMA). Persist the raw-best state as ema_best.pt so
            # the EMA eval still runs but reflects the trained weights, not init.
            torch.save(fb_raw_payload, ema_path)
            best_ema_metrics = dict(fb_raw_meta)
            ckpt_provenance["ema_source"] = "fallback_raw_best_ema_cold"
            print(f"[train_dual_lob] EMA never warmed (< ep {ema_warmup_epochs}) and "
                  f"σ-gate never fired; saved RAW-best as ema_best.pt @ epoch "
                  f"{fb_raw_meta.get('best_epoch')} (spec fallback to raw best).",
                  flush=True)
        else:
            ckpt_provenance["ema_source"] = "none"

    out = dict(best_metrics)
    if best_ema_metrics:
        out["ema"] = best_ema_metrics
    out["val_metric"] = val_metric
    out["ckpt_provenance"] = ckpt_provenance
    # Convenience: surface the saved checkpoints' σŷ/σy at top level for the
    # report (MEASUREMENT discipline — a low number flags possible unreliability).
    out["best_ckpt_sigma_ratio"] = best_metrics.get("val_sigma_ratio")
    if best_ema_metrics:
        out["ema_ckpt_sigma_ratio"] = best_ema_metrics.get("val_sigma_ratio")
    out["train_loss_hist"] = train_loss_hist
    # --- Stage-0b: explicit selection provenance + per-epoch val history ------
    out["val_hist"] = val_hist                       # per-epoch raw+EMA P/S/comp/σ/β
    out["best_is_sigma_fallback"] = (ckpt_provenance.get("best_source") == "fallback_low_sigma")
    out["ema_is_sigma_fallback"] = (ckpt_provenance.get("ema_source") == "fallback_low_sigma")
    out["epochs_ran"] = len(train_loss_hist)
    out["patience"] = patience
    out["stopped_at_patience"] = (epochs_no_improve >= patience)  # early-stop crawl flag
    out["selection"] = {
        "best_epoch": best_metrics.get("best_epoch"),
        "ema_best_epoch": best_ema_metrics.get("best_epoch") if best_ema_metrics else None,
        "best_source": ckpt_provenance.get("best_source"),
        "ema_source": ckpt_provenance.get("ema_source"),
        "val_metric": val_metric,
        "epoch_ckpts_saved": bool(save_epoch_ckpts),
    }
    with open(osp.join(out_dir, "metrics.json"), "w") as f:
        json.dump(out, f, indent=2)
    return out


def _perp_alpha(model: nn.Module) -> float:
    """Current value of the perp master gate (for logging); 0 if disabled."""
    pa = getattr(model, "perp_alpha", None)
    if pa is None:
        return 0.0
    return float(pa.detach().cpu().item())


# --------------------------------------------------------------------------- #
# Test evaluation (perp-residual aware; mirrors run_pipeline_v3 single-horizon) #
# --------------------------------------------------------------------------- #
def _run_test_eval(model: nn.Module, fold_dir: str, test_ds,
                   batch_size: int, device: str, *, horizon_sec: int, stride: int,
                   y_sigma: float, y_median: float,
                   ckpt_name: str = "best_model.pt",
                   preds_name: str = "test_preds.npz",
                   results_name: str = "test_results.json",
                   has_perp: bool = True) -> None:
    device_obj = torch.device(device)
    ckpt_path = osp.join(fold_dir, ckpt_name)
    if not osp.exists(ckpt_path):
        print(f"[train_dual_lob] WARN: no checkpoint {ckpt_path}; skip eval.")
        return
    ckpt = torch.load(ckpt_path, map_location=device_obj, weights_only=False)
    model.load_state_dict(ckpt["state"] if isinstance(ckpt, dict) and "state" in ckpt else ckpt)
    model.to(device_obj)
    model.eval()
    loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    qs, tgts, masks = [], [], []
    with torch.no_grad():
        for batch in loader:
            if has_perp:
                if len(batch) == 6:
                    x_feat, x_raw, regime_prior, y, m, x_perp = batch
                else:
                    x_feat, x_raw, y, m, x_perp = batch
                    regime_prior = None
            else:
                x_perp = None
                if len(batch) == 5:
                    x_feat, x_raw, regime_prior, y, m = batch
                elif len(batch) == 4:
                    x_feat, x_raw, y, m = batch
                    regime_prior = None
                else:
                    x_feat, y, m = batch
                    x_raw = None
                    regime_prior = None
            x_feat = x_feat.to(device_obj)
            if x_raw is not None:
                x_raw = x_raw.to(device_obj)
            if x_perp is not None:
                x_perp = x_perp.to(device_obj)
            if regime_prior is not None:
                regime_prior = regime_prior.to(device_obj)
            outputs = _forward_dual(model, x_feat, x_raw, regime_prior, x_perp)
            qs.append(outputs["quantiles"].cpu().numpy())
            tgts.append(y.numpy())
            masks.append(m.numpy())

    predictions = np.concatenate(qs)   # top-level quantiles = PRIMARY (y_600) slice
    targets = np.concatenate(tgts)
    mask = np.concatenate(masks).astype(bool)
    # mh180: y/mask come back (N, n_h); eval is strictly the primary (y_600) head.
    if targets.ndim == 2:
        pidx = int(getattr(model, "n_horizons", targets.shape[1])) - 1
        targets = targets[:, pidx]
        mask = mask[:, pidx] if mask.ndim == 2 else mask
    preds_raw = predictions * y_sigma + y_median
    targets_raw = targets * y_sigma + y_median

    if hasattr(test_ds, "get_all_timestamps"):
        timestamps = test_ds.get_all_timestamps()
    else:
        timestamps = np.zeros(0, dtype=np.int64)

    np.savez(osp.join(fold_dir, preds_name), predictions=predictions, targets=targets,
             mask=mask, timestamps=timestamps, y_sigma=np.array(y_sigma),
             y_median=np.array(y_median))

    from src.evaluation.backtest_v2 import BacktestEngine
    overlap = max(1, int(round(horizon_sec / max(stride, 1))))
    engine = BacktestEngine(fee_bps=4.0, slippage_bps=1.0, max_position=1.0,
                            signal_threshold=0.0, confidence_sizing=True)
    result = engine.run(predictions=preds_raw, targets=targets_raw, mask=mask,
                        overlap_ratio=overlap)
    print(f"[train_dual_lob] --- {ckpt_name} ---")
    print(result.summary())
    with open(osp.join(fold_dir, results_name), "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)


# --------------------------------------------------------------------------- #
# Fold construction + stats (mirrors run_pipeline_v3 multi-day path)           #
# --------------------------------------------------------------------------- #
def _build_folds(days: List[str], train_cfg: dict, embargo_days: int) -> List[dict]:
    fold_test_starts = train_cfg.get("fold_test_starts")
    if fold_test_starts:
        folds = []
        for ts_str in fold_test_starts:
            if ts_str not in days:
                raise RuntimeError(f"fold_test_starts {ts_str} not in available days")
            ti = days.index(ts_str)
            test = days[ti:ti + train_cfg["test_days"]]
            val_end = ti - embargo_days
            val_start = val_end - train_cfg["val_days"]
            val = days[val_start:val_end]
            tr_end = val_start - embargo_days
            tr_start_req = tr_end - train_cfg["train_days"]
            tr_start = max(0, tr_start_req)
            train = days[tr_start:tr_end]
            # Stage-0b guard: silent-truncation trap. When the cache starts too late
            # the train window is shorter than train_days WITHOUT any error, so a
            # "700d" arm can secretly train on ~540d and fake a window verdict.
            if len(train) < train_cfg["train_days"]:
                msg = (f"[_build_folds] TRAIN-WINDOW TRUNCATED for test_start={ts_str}: "
                       f"requested train_days={train_cfg['train_days']} but only {len(train)}d "
                       f"available (cache starts too late; tr_start clipped {tr_start_req}->0).")
                print("WARNING: " + msg, flush=True)
                if train_cfg.get("assert_full_train_window", False):
                    raise RuntimeError(msg + " (assert_full_train_window=True)")
            folds.append({"train": train, "val": val, "test": test})
        return folds
    return build_time_series_folds(
        days, train_days=train_cfg["train_days"], val_days=train_cfg["val_days"],
        test_days=train_cfg["test_days"], stride=train_cfg["fold_stride"],
        embargo_days=embargo_days,
    )


def _common_ds_kwargs(data_cfg: dict, horizons_list) -> dict:
    kw = dict(
        smooth_target_dir=data_cfg.get("smooth_target_dir"),
        tradeflow_dir=data_cfg.get("tradeflow_dir"),
        intraday_regime_dir=data_cfg.get("intraday_regime_dir"),
        microprice_trajectory_dir=data_cfg.get("microprice_trajectory_dir"),
        use_smoothed_target=bool(data_cfg.get("use_smoothed_target", True)),
        use_time2vec=bool(data_cfg.get("use_time2vec", False)),
        y_rolling_sigma_path=data_cfg.get("y_rolling_sigma_path"),
    )
    if horizons_list is not None:
        kw["horizons"] = horizons_list
    # Stage-0B D1 state_prior overlay (only DualLOBDataset accepts this kwarg;
    # LOBDatasetV2/SlicedLOBDataset reject it) -> add ONLY when configured so the
    # non-perp BASE/dualsrc arms stay byte-compatible.
    if data_cfg.get("state_prior_dir"):
        kw["state_prior_dir"] = data_cfg["state_prior_dir"]
    # mh180 y_180 sidecar (Stage-3): only DualLOBDataset accepts it; add when set.
    if data_cfg.get("y180_sidecar_dir"):
        kw["y180_sidecar_dir"] = data_cfg["y180_sidecar_dir"]
    return kw


def main() -> None:
    ap = argparse.ArgumentParser(description="Standalone DUAL-LOB trainer (Stage D2)")
    ap.add_argument("--config", required=True, help="Path to config JSON")
    ap.add_argument("--start-fold", type=int, default=0)
    ap.add_argument("--max-folds", type=int, default=None)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)
    data_cfg = cfg["data"]
    model_cfg = cfg.get("model", {})
    train_cfg = cfg["training"]
    output_dir = cfg["output_dir"]

    device = ("cuda" if torch.cuda.is_available()
              else "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
              else "cpu")
    print(f"[train_dual_lob] device={device} config={args.config}")

    horizon_sec = int(data_cfg.get("horizon_sec", 600))
    stride = int(data_cfg.get("stride", 180))
    npz_dir = data_cfg["npz_dir"]
    embargo_days = int(train_cfg.get("embargo_days", 0))

    npz_files = sorted(__import__("pathlib").Path(npz_dir).glob("*.npz"))
    days = [p.stem for p in npz_files if p.stem[0].isdigit()]
    if not days:
        print(f"[train_dual_lob] ERROR: no NPZ under {npz_dir}")
        sys.exit(1)
    print(f"[train_dual_lob] {len(days)} day(s) in {npz_dir}")

    folds = _build_folds(days, train_cfg, embargo_days)
    print(f"[train_dual_lob] built {len(folds)} fold(s)")

    _hsec = data_cfg.get("horizons_sec")
    horizons_list = [f"y_{int(h)}" for h in _hsec] if _hsec else None

    # Perp residual ON => DualLOBDataset (requires X_raw_perp_deep in the cache);
    # OFF => plain LOBDatasetV2 (the perp-deep key need NOT be present), so the
    # spot-64 BASE and dual-source DUALSRC arms run through this SAME loop without
    # a perp cache. The model is byte-identical to the REG_arch parent when OFF.
    #
    # SLICE (Phase-2 bisection, disk-safe): when data.slice is present and perp is
    # OFF, use SlicedLOBDataset to keep only the leading x_channels of X and
    # prior_cols of regime_prior IN MEMORY (no extra NPZ on the 100%-full disk),
    # so a single npz_dualsrc cache serves the +SEQ-only (X=69,prior=6) and
    # +LVL-only (X=64,prior=10) single-axis arms. Slicing happens AFTER the
    # parent's per-channel normalize, which is exact (see SlicedLOBDataset docs).
    has_perp = bool(model_cfg.get("use_perp_residual", False))
    slice_cfg = data_cfg.get("slice") or {}
    slice_xc = slice_cfg.get("x_channels")
    slice_pc = slice_cfg.get("prior_cols")
    use_slice = (not has_perp) and (slice_xc is not None or slice_pc is not None)
    if use_slice:
        DatasetCls = SlicedLOBDataset
    elif has_perp:
        DatasetCls = DualLOBDataset
    else:
        DatasetCls = LOBDatasetV2
    slice_kw = (dict(x_channels=slice_xc, prior_cols=slice_pc) if use_slice else {})
    print(f"[train_dual_lob] use_perp_residual={has_perp} slice={slice_cfg or None} "
          f"-> dataset={DatasetCls.__name__}")

    for fold_idx, fold in enumerate(folds):
        if fold_idx < args.start_fold:
            continue
        if args.max_folds is not None and fold_idx >= args.max_folds:
            print(f"[train_dual_lob] --max-folds={args.max_folds} reached.")
            break
        fold_dir = osp.join(output_dir, f"fold_{fold_idx}")
        os.makedirs(fold_dir, exist_ok=True)
        print(f"\n{'='*60}\n[train_dual_lob] Fold {fold_idx}: "
              f"train={fold['train'][0]}..{fold['train'][-1]}({len(fold['train'])}d) "
              f"val={fold['val'][0]}..{fold['val'][-1]} "
              f"test={fold['test'][0]}..{fold['test'][-1]}\n{'='*60}")

        # --- streaming stats on un-normalised train days --------------------
        t0 = time.time()
        stats_kw = dict(normalize=False)
        if horizons_list is not None:
            stats_kw["horizons"] = horizons_list
        stats_kw["y_rolling_sigma_path"] = data_cfg.get("y_rolling_sigma_path")
        # mh180: give stats_ds the sidecar too so it intercepts horizons -> the
        # parent reads only y_600 (compute_y_stats uses y_600), never y_180.
        if data_cfg.get("y180_sidecar_dir"):
            stats_kw["y180_sidecar_dir"] = data_cfg["y180_sidecar_dir"]
        stats_kw.update(slice_kw)
        stats_ds = DatasetCls(npz_dir, fold["train"], **stats_kw)
        x_mean, x_std = stats_ds.compute_stats()
        y_median, y_sigma = stats_ds.compute_y_stats()
        stats_ds.clear_cache()
        del stats_ds
        print(f"[train_dual_lob] stats {time.time()-t0:.1f}s "
              f"y_median={y_median:.6e} y_sigma={y_sigma:.6e}")

        y_norm = (y_median, y_sigma, 5.0)
        preload = bool(data_cfg.get("preload", False))
        common = dict(normalize=True, x_mean=x_mean, x_std=x_std, y_norm=y_norm,
                      preload=preload, **slice_kw,
                      **_common_ds_kwargs(data_cfg, horizons_list))
        # ARM A (0C choppy-specialist): filter the TRAIN days to the LOW-TREND
        # (choppy) subset (ER ≤ train-quantile). VAL/TEST stay FULL (D6: checkpoint
        # selection on all-day val). Normalization stats above are computed on the
        # FULL train window (deploy-consistent); only the training SUBSET changes.
        train_days = fold["train"]
        df_cfg = train_cfg.get("day_filter")
        if df_cfg:
            from multi_asset.train.arm_utils import choppy_filter_days
            train_days, _st = choppy_filter_days(
                npz_dir, fold["train"], quantile=df_cfg.get("quantile", 0.34))
            print(f"[arm] day_filter kept {_st['n_kept']}/{_st['n_in']} train days "
                  f"(ER<={_st['threshold']:.3f})", flush=True)
        train_ds = DatasetCls(npz_dir, train_days, **common)
        val_ds = DatasetCls(npz_dir, fold["val"], **common)
        test_ds = DatasetCls(npz_dir, fold["test"], **common)

        sample0 = train_ds._load_day(0)
        n_features = int(sample0["X"].shape[-1])
        raw_levels = int(sample0["X_raw"].shape[-2])
        model = build_dual_lob_model(model_cfg, n_features, raw_levels)
        print(f"[train_dual_lob] params={sum(p.numel() for p in model.parameters()):,}")

        # Stage-0B D1: freeze the fixed-regime-state descriptor + prior stats on THIS
        # fold's normalised train dataset (FLAG-2 fix; buffers persist in the ckpt).
        # No-op unless use_fixed_regime_state is on.
        if getattr(model, "use_fixed_regime_state", False):
            model.fit_regime_state_stats(train_ds)

        best = train_one_fold_dual(
            model=model, train_dataset=train_ds, val_dataset=val_ds, out_dir=fold_dir,
            device=device, epochs=train_cfg["epochs"], batch_size=train_cfg["batch_size"],
            lr=train_cfg["lr"], weight_decay=train_cfg["weight_decay"],
            patience=train_cfg["patience"], grad_clip=train_cfg["grad_clip"],
            dul_config=train_cfg.get("dul_config"), seed=args.seed,
            val_metric=str(train_cfg.get("val_metric", "composite")),
            use_ema=bool(train_cfg.get("use_ema", False)),
            ema_decay=float(train_cfg.get("ema_decay", 0.999)),
            num_workers=int(train_cfg.get("num_workers", 0)),
            prefetch_factor=int(train_cfg.get("prefetch_factor", 2)),
            has_perp=has_perp,
            max_steps_per_epoch=(int(train_cfg["max_steps_per_epoch"])
                                 if train_cfg.get("max_steps_per_epoch") else None),
            save_epoch_ckpts=bool(train_cfg.get("save_epoch_ckpts", False)),
            tail_weight=train_cfg.get("tail_weight"),
        )
        print(f"[train_dual_lob] Fold {fold_idx} best: {best}")

        np.savez(osp.join(fold_dir, "norm_params.npz"), x_mean=x_mean, x_std=x_std,
                 y_median=np.array(y_median), y_sigma=np.array(y_sigma))

        _run_test_eval(model, fold_dir, test_ds, train_cfg["batch_size"], device,
                       horizon_sec=horizon_sec, stride=stride,
                       y_sigma=y_sigma, y_median=y_median, has_perp=has_perp)
        if osp.exists(osp.join(fold_dir, "ema_best.pt")):
            _run_test_eval(model, fold_dir, test_ds, train_cfg["batch_size"], device,
                           horizon_sec=horizon_sec, stride=stride,
                           y_sigma=y_sigma, y_median=y_median,
                           ckpt_name="ema_best.pt", preds_name="ema_test_preds.npz",
                           results_name="ema_test_results.json", has_perp=has_perp)

    print("\n[train_dual_lob] All done.")


if __name__ == "__main__":
    main()

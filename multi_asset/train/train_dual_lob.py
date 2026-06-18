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
    build_time_series_folds,
)
from src.training.trainer import OnlineMetrics  # noqa: E402
from src.training.trainer_v2 import (  # noqa: E402
    _apply_warmup,
    _build_loss_fn_for_dul,
    _extract_model_config,
    _seed_everything,
)

from multi_asset.data.dual_lob_dataset import DualLOBDataset  # noqa: E402
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
_PERP_KEYS = {"use_perp_residual", "perp_n_levels", "d_perp", "perp_alpha_init"}


def build_dual_lob_model(model_cfg: dict, n_features: int,
                         n_levels: int) -> DualLOBREGArch:
    """Instantiate ``DualLOBREGArch`` from a config ``model`` block.

    ``n_levels`` is the SPOT Path-B level count (from the data). The perp
    residual's level count comes from ``perp_n_levels`` in the config.
    """
    base = {k: v for k, v in model_cfg.items() if k in _BASE_ALLOWED}
    perp = {k: v for k, v in model_cfg.items() if k in _PERP_KEYS}
    perp.setdefault("use_perp_residual", True)
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
def _forward_dual(model: nn.Module, x_feat, x_raw, regime_prior, x_perp):
    """Single forward threading the perp deep book into the model."""
    kwargs: Dict[str, Any] = {"x_raw_perp_deep": x_perp}
    if regime_prior is not None:
        kwargs["regime_prior"] = regime_prior
    return model(x_feat, x_raw, **kwargs)


def train_one_fold_dual(
    *,
    model: nn.Module,
    train_dataset: DualLOBDataset,
    val_dataset: DualLOBDataset,
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
) -> Dict[str, Any]:
    """Replica of ``trainer_v2.train_one_fold_v2`` for the single-horizon,
    dual-path + regime-prior + perp-residual case.

    Reuses the proven loss (``_build_loss_fn_for_dul``), σ-gate best-ckpt rule,
    EMA, warmup + ReduceLROnPlateau and DayChunkedSampler. Differs ONLY in that
    every forward threads ``x_raw_perp_deep`` (the trailing batch element).

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

    # --- loaders: DayChunkedSampler when preload is off, else plain order ----
    preloaded = getattr(train_dataset, "_preloaded", False)
    _nw = 0 if preloaded else num_workers
    use_day_sampler = (
        not preloaded
        and hasattr(train_dataset, "_offsets")
        and hasattr(train_dataset, "_day_paths")
    )
    if use_day_sampler:
        sampler = DayChunkedSampler(
            train_dataset, chunk_size=32, shuffle_days=True,
            shuffle_within_day=True, seed=42,
        )
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, sampler=sampler,
            num_workers=_nw, persistent_workers=_nw > 0,
            prefetch_factor=prefetch_factor if _nw > 0 else None,
            pin_memory=torch.cuda.is_available(), drop_last=True,
        )
    else:
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True,
            num_workers=_nw, persistent_workers=_nw > 0,
            prefetch_factor=prefetch_factor if _nw > 0 else None,
            pin_memory=torch.cuda.is_available(), drop_last=True,
        )
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

    def _unpack(batch):
        # DualLOBDataset tuples (single-horizon):
        #   dual + regime : (x_feat, x_raw, regime_prior, y, mask, x_perp)
        #   dual, no rp   : (x_feat, x_raw,               y, mask, x_perp)
        if len(batch) == 6:
            x_feat, x_raw, regime_prior, y, mask, x_perp = batch
        elif len(batch) == 5:
            x_feat, x_raw, y, mask, x_perp = batch
            regime_prior = None
        else:
            raise RuntimeError(
                f"DualLOBDataset batch must be 5- or 6-tuple, got len={len(batch)}"
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
                outputs = _forward_dual(eval_model, x_feat, x_raw, regime_prior, x_perp)
                idx = mask.nonzero(as_tuple=True)[0]
                if len(idx) == 0:
                    continue
                m_out = {k: v[idx] for k, v in outputs.items() if torch.is_tensor(v)}
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
            outputs = _forward_dual(model, x_feat, x_raw, regime_prior, x_perp)
            idx = mask.nonzero(as_tuple=True)[0]
            if len(idx) == 0:
                global_step += 1
                continue
            m_out = {k: v[idx] for k, v in outputs.items() if torch.is_tensor(v)}
            loss = loss_fn(m_out, y[idx])
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
            }
            torch.save({"state": model.state_dict(), "class": type(model).__name__,
                        "config": _extract_model_config(model)},
                       osp.join(out_dir, "best_model.pt"))
        else:
            epochs_no_improve += 1

        if ema_val is not None:
            ema_sel = ema_val["val_composite"] if val_metric == "composite" else ema_val["val_corr"]
            best_ema_sel = (best_ema_metrics.get("val_composite", -1.0) if val_metric == "composite"
                            else best_ema_metrics.get("val_corr", -1.0))
            if ema_val["val_sigma_ratio"] >= 0.02 and ema_sel > best_ema_sel + 5e-4:
                best_ema_metrics = {
                    "best_epoch": epoch, "val_loss": ema_val["val_loss"],
                    "val_corr": ema_val["val_corr"], "val_spearman": ema_val["val_spearman"],
                    "val_composite": ema_val["val_composite"], "val_r2": ema_val["val_r2"],
                }
                torch.save({"state": ema_model.module.state_dict(),
                            "class": type(ema_model.module).__name__,
                            "config": _extract_model_config(ema_model.module)},
                           osp.join(out_dir, "ema_best.pt"))

        if epochs_no_improve >= patience:
            print(f"Early stopping at epoch {epoch} (patience={patience}).", flush=True)
            break

    out = dict(best_metrics)
    if best_ema_metrics:
        out["ema"] = best_ema_metrics
    out["val_metric"] = val_metric
    out["train_loss_hist"] = train_loss_hist
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
def _run_test_eval(model: nn.Module, fold_dir: str, test_ds: DualLOBDataset,
                   batch_size: int, device: str, *, horizon_sec: int, stride: int,
                   y_sigma: float, y_median: float,
                   ckpt_name: str = "best_model.pt",
                   preds_name: str = "test_preds.npz",
                   results_name: str = "test_results.json") -> None:
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
            if len(batch) == 6:
                x_feat, x_raw, regime_prior, y, m, x_perp = batch
            else:
                x_feat, x_raw, y, m, x_perp = batch
                regime_prior = None
            x_feat = x_feat.to(device_obj)
            x_raw = x_raw.to(device_obj)
            x_perp = x_perp.to(device_obj)
            if regime_prior is not None:
                regime_prior = regime_prior.to(device_obj)
            outputs = _forward_dual(model, x_feat, x_raw, regime_prior, x_perp)
            qs.append(outputs["quantiles"].cpu().numpy())
            tgts.append(y.numpy())
            masks.append(m.numpy())

    predictions = np.concatenate(qs)
    targets = np.concatenate(tgts)
    mask = np.concatenate(masks).astype(bool)
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
            tr_start = max(0, tr_end - train_cfg["train_days"])
            train = days[tr_start:tr_end]
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

        # --- streaming stats on un-normalised train days (DualLOBDataset) ----
        t0 = time.time()
        stats_kw = dict(normalize=False)
        if horizons_list is not None:
            stats_kw["horizons"] = horizons_list
        stats_kw["y_rolling_sigma_path"] = data_cfg.get("y_rolling_sigma_path")
        stats_ds = DualLOBDataset(npz_dir, fold["train"], **stats_kw)
        x_mean, x_std = stats_ds.compute_stats()
        y_median, y_sigma = stats_ds.compute_y_stats()
        stats_ds.clear_cache()
        del stats_ds
        print(f"[train_dual_lob] stats {time.time()-t0:.1f}s "
              f"y_median={y_median:.6e} y_sigma={y_sigma:.6e}")

        y_norm = (y_median, y_sigma, 5.0)
        preload = bool(data_cfg.get("preload", False))
        common = dict(normalize=True, x_mean=x_mean, x_std=x_std, y_norm=y_norm,
                      preload=preload, **_common_ds_kwargs(data_cfg, horizons_list))
        train_ds = DualLOBDataset(npz_dir, fold["train"], **common)
        val_ds = DualLOBDataset(npz_dir, fold["val"], **common)
        test_ds = DualLOBDataset(npz_dir, fold["test"], **common)

        sample0 = train_ds._load_day(0)
        n_features = int(sample0["X"].shape[-1])
        raw_levels = int(sample0["X_raw"].shape[-2])
        model = build_dual_lob_model(model_cfg, n_features, raw_levels)
        print(f"[train_dual_lob] params={sum(p.numel() for p in model.parameters()):,}")

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
        )
        print(f"[train_dual_lob] Fold {fold_idx} best: {best}")

        np.savez(osp.join(fold_dir, "norm_params.npz"), x_mean=x_mean, x_std=x_std,
                 y_median=np.array(y_median), y_sigma=np.array(y_sigma))

        _run_test_eval(model, fold_dir, test_ds, train_cfg["batch_size"], device,
                       horizon_sec=horizon_sec, stride=stride,
                       y_sigma=y_sigma, y_median=y_median)
        if osp.exists(osp.join(fold_dir, "ema_best.pt")):
            _run_test_eval(model, fold_dir, test_ds, train_cfg["batch_size"], device,
                           horizon_sec=horizon_sec, stride=stride,
                           y_sigma=y_sigma, y_median=y_median,
                           ckpt_name="ema_best.pt", preds_name="ema_test_preds.npz",
                           results_name="ema_test_results.json")

    print("\n[train_dual_lob] All done.")


if __name__ == "__main__":
    main()

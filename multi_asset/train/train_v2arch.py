"""Standalone trainer for the V2 dual-source ARCHITECTURE (DualLOBV2Arch).

WHAT THIS IS
------------
A focused fork of ``multi_asset/train/train_dual_lob.py`` that trains the FULL v2
architecture (``DualLOBV2Arch`` = REG_arch + perp gated residual + ModernTCN-lite
long-context FiLM) on ``data/npz_v2arch`` via the ``V2ArchDataset`` (which returns
``x_perp`` AND ``x_long`` as the two trailing batch elements). Everything proven —
fold construction, per-fold streaming stats + 5σ target normalisation, the singh
α=0 huber loss (dul_config), σ-gate best-ckpt + low-σ fallback, EMA, warmup +
ReduceLROnPlateau, COW-safe workers — is REUSED verbatim from the dual-LOB trainer
or imported from ``trainer_v2``; only the batch unpack (7-tuple) and the forward
(threads ``x_long=`` and ``x_raw_perp_deep=``) differ.

STAGING via config flags (no code change between stages)
-------------------------------------------------------
  S1 (multi-path + bounded cross): model.use_perp_residual=true,
      model.use_long_context=false  → Path A(72) + B + C residual, NO long branch.
  S2/S3 (+ long-context FiLM):      model.use_long_context=true → adds the
      ModernTCN-lite branch + zero-init FiLM.
  matched BASE (spot-only A+B):     model.use_perp_residual=false,
      model.use_long_context=false, data.slice.x_channels=64 (drop the 8 cross
      cols so Path A is the milestone spot-64) → the apples-to-apples reference.

CLI
---
  python multi_asset/train/train_v2arch.py --config <cfg> --start-fold 0 --max-folds 1 --seed 42
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as osp
import sys
import time
from typing import Any, Callable, Dict, List, Optional

# Fight CUDA fragmentation OOM on the 24GB box: the 3-tower multi-path model
# (Path A 88ch + spot raw-LOB + perp raw-LOB encoders) + EMA copy fragments the
# allocator across epochs. Must be set BEFORE torch initialises CUDA, so do it
# here unconditionally (idempotent if already exported by the launcher).
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

_REPO = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from src.training.dataset import (  # noqa: E402
    DayChunkedSampler,
    LOBDatasetV2,
)
from src.training.trainer import OnlineMetrics  # noqa: E402
from src.training.trainer_v2 import (  # noqa: E402
    _apply_warmup,
    _build_loss_fn_for_dul,
    _extract_model_config,
    _seed_everything,
)

from multi_asset.data.v2arch_dataset import V2ArchDataset  # noqa: E402
from multi_asset.data.dual_lob_dataset import DualLOBDataset  # noqa: E402
from multi_asset.data.sliced_lob_dataset import SlicedLOBDataset  # noqa: E402
from multi_asset.model.dual_lob_v2arch import DualLOBV2Arch  # noqa: E402
# reuse the proven, identical helpers (fold build, ds kwargs, perp-alpha log)
from multi_asset.train.train_dual_lob import (  # noqa: E402
    _BASE_ALLOWED,
    _PERP_KEYS,
    _build_folds,
    _common_ds_kwargs,
    _perp_alpha,
)

# Long-context branch kwargs (consumed by DualLOBV2Arch only).
_LONG_KEYS = {
    "use_long_context", "long_c_in", "long_steps", "long_d", "long_n_blocks",
    "long_kernel", "long_d_ctx", "long_film_alpha_init",
}


def build_v2arch_model(model_cfg: dict, n_features: int, n_levels: int) -> DualLOBV2Arch:
    base = {k: v for k, v in model_cfg.items() if k in _BASE_ALLOWED}
    perp = {k: v for k, v in model_cfg.items() if k in _PERP_KEYS}
    longk = {k: v for k, v in model_cfg.items() if k in _LONG_KEYS}
    perp.setdefault("use_perp_residual", False)
    longk.setdefault("use_long_context", False)
    unknown = set(model_cfg) - _BASE_ALLOWED - _PERP_KEYS - _LONG_KEYS - {"_comment"}
    if unknown:
        print(f"[train_v2arch] WARNING: unknown model_cfg keys ignored: {sorted(unknown)}")
    print(f"[train_v2arch] DualLOBV2Arch n_features={n_features} n_levels={n_levels} "
          f"perp={perp} long={longk}")
    return DualLOBV2Arch(n_features=n_features, n_levels=n_levels, **base, **perp, **longk)


def _long_alpha(model: nn.Module) -> float:
    lf = getattr(model, "long_film", None)
    if lf is None or getattr(lf, "film_alpha", None) is None:
        return 0.0
    return float(torch.tanh(lf.film_alpha).detach().cpu().item())


# --------------------------------------------------------------------------- #
# forward + unpack (7-tuple: ..., x_perp, x_long)                              #
# --------------------------------------------------------------------------- #
def _forward_v2(model, x_feat, x_raw, regime_prior, x_perp, x_long):
    kwargs: Dict[str, Any] = {"x_raw_perp_deep": x_perp, "x_long": x_long}
    if regime_prior is not None:
        kwargs["regime_prior"] = regime_prior
    return model(x_feat, x_raw, **kwargs)


def _unpack_v2(batch, has_perp: bool):
    """V2ArchDataset always carries (x_perp, x_long) as the two trailing elements
    (it subclasses DualLOBDataset). ``has_perp`` selects whether the model uses the
    perp residual (the tensor is still present in the batch either way; we pass it
    and the model no-ops it when use_perp_residual=False)."""
    if len(batch) == 7:
        x_feat, x_raw, regime_prior, y, mask, x_perp, x_long = batch
    elif len(batch) == 6:
        x_feat, x_raw, y, mask, x_perp, x_long = batch
        regime_prior = None
    else:
        raise RuntimeError(f"V2ArchDataset batch must be 6- or 7-tuple, got len={len(batch)}")
    if not has_perp:
        x_perp = None
    return x_feat, x_raw, regime_prior, y, mask, x_perp, x_long


# --------------------------------------------------------------------------- #
# Train one fold (mirror of train_one_fold_dual; 7-tuple + x_long threaded)    #
# --------------------------------------------------------------------------- #
def train_one_fold_v2(
    *, model, train_dataset, val_dataset, out_dir, device="cpu",
    epochs=25, batch_size=1024, lr=6e-4, weight_decay=1e-3, patience=12,
    grad_clip=1.0, dul_config=None, seed=None, val_metric="composite",
    use_ema=False, ema_decay=0.999, num_workers=0, prefetch_factor=2,
    max_steps_per_epoch=None, has_perp=True,
) -> Dict[str, Any]:
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

    preloaded = getattr(train_dataset, "_preloaded", False)
    _nw = num_workers if preloaded else 0
    _mp_ctx = "fork" if _nw > 0 else None
    use_day_sampler = (not preloaded and hasattr(train_dataset, "_offsets")
                       and hasattr(train_dataset, "_day_paths"))
    _loader_common = dict(
        num_workers=_nw, persistent_workers=_nw > 0,
        prefetch_factor=prefetch_factor if _nw > 0 else None,
        multiprocessing_context=_mp_ctx if _nw > 0 else None,
        pin_memory=torch.cuda.is_available(), drop_last=True,
    )
    if use_day_sampler:
        sampler = DayChunkedSampler(train_dataset, chunk_size=32, shuffle_days=True,
                                    shuffle_within_day=True, seed=42)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, sampler=sampler,
                                  **_loader_common)
    else:
        _g = torch.Generator(); _g.manual_seed(int(seed) if seed is not None else 42)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,
                                  generator=_g, **_loader_common)
    print(f"[train_v2arch] train_loader: preloaded={preloaded} num_workers={_nw} "
          f"mp_ctx={_mp_ctx}", flush=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False,
                            num_workers=0, pin_memory=torch.cuda.is_available())

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=max(patience // 2, 2), min_lr=1e-6)

    steps_per_epoch = max(len(train_dataset) // batch_size, 1)
    warmup_epochs = min(5, epochs // 4)
    warmup_steps = warmup_epochs * steps_per_epoch
    ema_warmup_epochs = max(2, warmup_epochs)
    global_step = 0

    ema_model = None
    if use_ema:
        _omd = 1.0 - float(ema_decay)
        def _ema_avg(avg_p, new_p, n):  # noqa: ARG001
            return avg_p + _omd * (new_p - avg_p)
        ema_model = torch.optim.swa_utils.AveragedModel(model, avg_fn=_ema_avg).to(device_obj)
        print(f"[train_v2arch] EMA active (decay={ema_decay})")

    best_metrics: Dict[str, Any] = {}
    best_ema_metrics: Dict[str, Any] = {}
    epochs_no_improve = 0
    train_loss_hist: List[float] = []
    fb_raw_sel = -1.0; fb_raw_payload = None; fb_raw_meta: Dict[str, Any] = {}
    fb_ema_sel = -1.0; fb_ema_payload = None; fb_ema_meta: Dict[str, Any] = {}

    def _to_dev(*ts):
        return [t.to(device_obj, non_blocking=True) if t is not None else None for t in ts]

    def _run_val(eval_model) -> Dict[str, Any]:
        eval_model.eval()
        om = OnlineMetrics(); loss_sum = 0.0; steps = 0
        preds_all: List[np.ndarray] = []; targets_all: List[np.ndarray] = []
        with torch.no_grad():
            for batch in val_loader:
                x_feat, x_raw, rp, y, mask, x_perp, x_long = _unpack_v2(batch, has_perp)
                x_feat, x_raw, rp, x_perp, x_long, y, mask = _to_dev(
                    x_feat, x_raw, rp, x_perp, x_long, y, mask)
                outputs = _forward_v2(eval_model, x_feat, x_raw, rp, x_perp, x_long)
                idx = mask.nonzero(as_tuple=True)[0]
                if len(idx) == 0:
                    continue
                m_out = {k: v[idx] for k, v in outputs.items() if torch.is_tensor(v)}
                loss = loss_fn(m_out, y[idx])
                loss_sum += float(loss.item()); steps += 1
                pred_np = outputs["point_pred"][idx].cpu().numpy()
                tgt_np = y[idx].cpu().numpy()
                om.update(pred_np, tgt_np)
                preds_all.append(pred_np); targets_all.append(tgt_np)
        pearson = om.corr(); r2 = om.r2()
        spearman = 0.0; sigma_ratio = 0.0; beta = 0.0
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
        return {"val_loss": loss_sum / max(steps, 1), "val_corr": pearson,
                "val_spearman": spearman, "val_composite": composite, "val_r2": r2,
                "val_sigma_ratio": sigma_ratio, "val_beta": beta}

    for epoch in range(1, epochs + 1):
        if use_day_sampler:
            train_loader.sampler.set_epoch(epoch)  # type: ignore[attr-defined]
        model.train(); tl_sum = 0.0; tl_steps = 0
        for batch in train_loader:
            x_feat, x_raw, rp, y, mask, x_perp, x_long = _unpack_v2(batch, has_perp)
            x_feat, x_raw, rp, x_perp, x_long, y, mask = _to_dev(
                x_feat, x_raw, rp, x_perp, x_long, y, mask)
            outputs = _forward_v2(model, x_feat, x_raw, rp, x_perp, x_long)
            idx = mask.nonzero(as_tuple=True)[0]
            if len(idx) == 0:
                global_step += 1; continue
            m_out = {k: v[idx] for k, v in outputs.items() if torch.is_tensor(v)}
            loss = loss_fn(m_out, y[idx])
            if not torch.isfinite(loss):
                optimizer.zero_grad(); global_step += 1; continue
            optimizer.zero_grad(); loss.backward()
            gnorm = torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            if not torch.isfinite(gnorm):
                optimizer.zero_grad(); global_step += 1; continue
            _apply_warmup(global_step, warmup_steps, lr, optimizer)
            optimizer.step()
            if ema_model is not None:
                ema_model.update_parameters(model)
            tl_sum += float(loss.item()); tl_steps += 1; global_step += 1
            if max_steps_per_epoch is not None and tl_steps >= max_steps_per_epoch:
                break
        avg_tl = tl_sum / max(tl_steps, 1); train_loss_hist.append(avg_tl)

        raw_val = _run_val(model)
        ema_val = _run_val(ema_model) if ema_model is not None else None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()   # release fragmented val blocks before next epoch
        selector = raw_val["val_composite"] if val_metric == "composite" else raw_val["val_corr"]
        scheduler.step(selector)
        cur_lr = optimizer.param_groups[0]["lr"]
        line = (f"Epoch {epoch:3d}/{epochs} | train_loss={avg_tl:.6f} | "
                f"val_loss={raw_val['val_loss']:.6f} | "
                f"P={raw_val['val_corr']:+.4f} S={raw_val['val_spearman']:+.4f} "
                f"C={raw_val['val_composite']:+.4f} | sigR={raw_val['val_sigma_ratio']:.3f} "
                f"b={raw_val['val_beta']:+.3f} | perp_a={_perp_alpha(model):+.4f} "
                f"long_g={_long_alpha(model):+.4f} | lr={cur_lr:.2e}")
        if ema_val is not None:
            line += (f" | EMA P={ema_val['val_corr']:+.4f} S={ema_val['val_spearman']:+.4f} "
                     f"C={ema_val['val_composite']:+.4f}")
        print(line, flush=True)

        if selector > fb_raw_sel:
            fb_raw_sel = selector
            fb_raw_payload = {"state": {k: v.detach().cpu().clone()
                                        for k, v in model.state_dict().items()},
                              "class": type(model).__name__,
                              "config": _extract_model_config(model)}
            fb_raw_meta = {"best_epoch": epoch, "val_loss": raw_val["val_loss"],
                           "val_corr": raw_val["val_corr"], "val_spearman": raw_val["val_spearman"],
                           "val_composite": raw_val["val_composite"], "val_r2": raw_val["val_r2"],
                           "val_sigma_ratio": raw_val["val_sigma_ratio"]}

        sigma_ok = raw_val["val_sigma_ratio"] >= 0.02
        best_sel = (best_metrics.get("val_composite", -1.0) if val_metric == "composite"
                    else best_metrics.get("val_corr", -1.0))
        if sigma_ok and selector > best_sel + 5e-4:
            epochs_no_improve = 0
            best_metrics = {"best_epoch": epoch, "val_loss": raw_val["val_loss"],
                            "val_corr": raw_val["val_corr"], "val_spearman": raw_val["val_spearman"],
                            "val_composite": raw_val["val_composite"], "val_r2": raw_val["val_r2"],
                            "val_sigma_ratio": raw_val["val_sigma_ratio"]}
            torch.save({"state": model.state_dict(), "class": type(model).__name__,
                        "config": _extract_model_config(model)},
                       osp.join(out_dir, "best_model.pt"))
        elif sigma_ok:
            epochs_no_improve += 1
        # σ<0.02 = warmup: do NOT count toward patience, so patience can be small
        # (e.g. 5) without early-stopping during the σ warmup before signal appears.

        if ema_val is not None:
            ema_sel = ema_val["val_composite"] if val_metric == "composite" else ema_val["val_corr"]
            if epoch >= ema_warmup_epochs and ema_sel > fb_ema_sel:
                fb_ema_sel = ema_sel
                fb_ema_payload = {"state": {k: v.detach().cpu().clone()
                                            for k, v in ema_model.module.state_dict().items()},
                                  "class": type(ema_model.module).__name__,
                                  "config": _extract_model_config(ema_model.module)}
                fb_ema_meta = {"best_epoch": epoch, "val_loss": ema_val["val_loss"],
                               "val_corr": ema_val["val_corr"], "val_spearman": ema_val["val_spearman"],
                               "val_composite": ema_val["val_composite"], "val_r2": ema_val["val_r2"],
                               "val_sigma_ratio": ema_val["val_sigma_ratio"]}
            best_ema_sel = (best_ema_metrics.get("val_composite", -1.0) if val_metric == "composite"
                            else best_ema_metrics.get("val_corr", -1.0))
            if ema_val["val_sigma_ratio"] >= 0.02 and ema_sel > best_ema_sel + 5e-4:
                best_ema_metrics = {"best_epoch": epoch, "val_loss": ema_val["val_loss"],
                                    "val_corr": ema_val["val_corr"], "val_spearman": ema_val["val_spearman"],
                                    "val_composite": ema_val["val_composite"], "val_r2": ema_val["val_r2"],
                                    "val_sigma_ratio": ema_val["val_sigma_ratio"]}
                torch.save({"state": ema_model.module.state_dict(),
                            "class": type(ema_model.module).__name__,
                            "config": _extract_model_config(ema_model.module)},
                           osp.join(out_dir, "ema_best.pt"))

        if epochs_no_improve >= patience:
            print(f"Early stopping at epoch {epoch} (patience={patience}).", flush=True)
            break

    ckpt_provenance: Dict[str, Any] = {}
    best_path = osp.join(out_dir, "best_model.pt")
    if not osp.exists(best_path) and fb_raw_payload is not None:
        torch.save(fb_raw_payload, best_path)
        best_metrics = dict(fb_raw_meta)
        ckpt_provenance["best_source"] = "fallback_low_sigma"
        print(f"[train_v2arch] σ-gate never fired (best raw σŷ/σy="
              f"{fb_raw_meta.get('val_sigma_ratio', float('nan')):.4f} < 0.02); "
              f"saved FALLBACK best_model.pt @ epoch {fb_raw_meta.get('best_epoch')}.", flush=True)
    elif osp.exists(best_path):
        ckpt_provenance["best_source"] = "sigma_gate"
    else:
        ckpt_provenance["best_source"] = "none"

    ema_path = osp.join(out_dir, "ema_best.pt")
    if use_ema:
        if osp.exists(ema_path):
            ckpt_provenance["ema_source"] = "sigma_gate"
        elif fb_ema_payload is not None:
            torch.save(fb_ema_payload, ema_path)
            best_ema_metrics = dict(fb_ema_meta)
            ckpt_provenance["ema_source"] = "fallback_low_sigma"
            print(f"[train_v2arch] σ-gate never fired for EMA; saved FALLBACK ema_best.pt "
                  f"@ epoch {fb_ema_meta.get('best_epoch')}.", flush=True)
        elif fb_raw_payload is not None:
            torch.save(fb_raw_payload, ema_path)
            best_ema_metrics = dict(fb_raw_meta)
            ckpt_provenance["ema_source"] = "fallback_raw_best_ema_cold"
        else:
            ckpt_provenance["ema_source"] = "none"

    out = dict(best_metrics)
    if best_ema_metrics:
        out["ema"] = best_ema_metrics
    out["val_metric"] = val_metric
    out["ckpt_provenance"] = ckpt_provenance
    out["best_ckpt_sigma_ratio"] = best_metrics.get("val_sigma_ratio")
    if best_ema_metrics:
        out["ema_ckpt_sigma_ratio"] = best_ema_metrics.get("val_sigma_ratio")
    out["train_loss_hist"] = train_loss_hist
    with open(osp.join(out_dir, "metrics.json"), "w") as f:
        json.dump(out, f, indent=2)
    return out


# --------------------------------------------------------------------------- #
# Test eval (7-tuple aware)                                                    #
# --------------------------------------------------------------------------- #
def _run_test_eval_v2(model, fold_dir, test_ds, batch_size, device, *, horizon_sec,
                      stride, y_sigma, y_median, has_perp, ckpt_name="best_model.pt",
                      preds_name="test_preds.npz", results_name="test_results.json"):
    device_obj = torch.device(device)
    ckpt_path = osp.join(fold_dir, ckpt_name)
    if not osp.exists(ckpt_path):
        print(f"[train_v2arch] WARN: no checkpoint {ckpt_path}; skip eval.")
        return
    ckpt = torch.load(ckpt_path, map_location=device_obj, weights_only=False)
    model.load_state_dict(ckpt["state"] if isinstance(ckpt, dict) and "state" in ckpt else ckpt)
    model.to(device_obj); model.eval()
    loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)
    qs, tgts, masks = [], [], []
    with torch.no_grad():
        for batch in loader:
            x_feat, x_raw, rp, y, m, x_perp, x_long = _unpack_v2(batch, has_perp)
            x_feat = x_feat.to(device_obj)
            x_raw = x_raw.to(device_obj) if x_raw is not None else None
            x_perp = x_perp.to(device_obj) if x_perp is not None else None
            x_long = x_long.to(device_obj) if x_long is not None else None
            rp = rp.to(device_obj) if rp is not None else None
            outputs = _forward_v2(model, x_feat, x_raw, rp, x_perp, x_long)
            qs.append(outputs["quantiles"].cpu().numpy())
            tgts.append(y.numpy()); masks.append(m.numpy())
    predictions = np.concatenate(qs); targets = np.concatenate(tgts)
    mask = np.concatenate(masks).astype(bool)
    preds_raw = predictions * y_sigma + y_median
    targets_raw = targets * y_sigma + y_median
    timestamps = (test_ds.get_all_timestamps() if hasattr(test_ds, "get_all_timestamps")
                  else np.zeros(0, dtype=np.int64))
    np.savez(osp.join(fold_dir, preds_name), predictions=predictions, targets=targets,
             mask=mask, timestamps=timestamps, y_sigma=np.array(y_sigma),
             y_median=np.array(y_median))
    from src.evaluation.backtest_v2 import BacktestEngine
    overlap = max(1, int(round(horizon_sec / max(stride, 1))))
    engine = BacktestEngine(fee_bps=4.0, slippage_bps=1.0, max_position=1.0,
                            signal_threshold=0.0, confidence_sizing=True)
    result = engine.run(predictions=preds_raw, targets=targets_raw, mask=mask,
                        overlap_ratio=overlap)
    print(f"[train_v2arch] --- {ckpt_name} ---"); print(result.summary())
    with open(osp.join(fold_dir, results_name), "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="V2 dual-source architecture trainer")
    ap.add_argument("--config", required=True)
    ap.add_argument("--start-fold", type=int, default=0)
    ap.add_argument("--max-folds", type=int, default=None)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)
    data_cfg = cfg["data"]; model_cfg = cfg.get("model", {})
    train_cfg = cfg["training"]; output_dir = cfg["output_dir"]

    device = ("cuda" if torch.cuda.is_available()
              else "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
              else "cpu")
    print(f"[train_v2arch] device={device} config={args.config}")

    horizon_sec = int(data_cfg.get("horizon_sec", 600))
    stride = int(data_cfg.get("stride", 180))
    npz_dir = data_cfg["npz_dir"]
    embargo_days = int(train_cfg.get("embargo_days", 0))

    npz_files = sorted(__import__("pathlib").Path(npz_dir).glob("*.npz"))
    days = [p.stem for p in npz_files if p.stem[0].isdigit()]
    if not days:
        print(f"[train_v2arch] ERROR: no NPZ under {npz_dir}"); sys.exit(1)
    print(f"[train_v2arch] {len(days)} day(s) in {npz_dir}")

    folds = _build_folds(days, train_cfg, embargo_days)
    print(f"[train_v2arch] built {len(folds)} fold(s)")

    _hsec = data_cfg.get("horizons_sec")
    horizons_list = [f"y_{int(h)}" for h in _hsec] if _hsec else None
    # DECISIVE root-cause option: train on an arbitrary target key (e.g.
    # "y_spot_600" — the SPOT 600s return, corr 0.998 with perp y_600 but ~5%
    # less label noise). When set, it OVERRIDES horizons_list with a single
    # horizon = target_key; the dataset auto-derives the matching mask key
    # ("y_mask_spot_600") via _derive_mask_key, and `_has_y600` becomes False so
    # no y_600-keyed overlay/smoothing fires. Eval still saves q50 + timestamps,
    # so an offline join can score the SAME predictions against BOTH targets.
    target_key = data_cfg.get("target_key")
    if target_key:
        horizons_list = [str(target_key)]
        print(f"[train_v2arch] TARGET OVERRIDE: training on horizon_key={target_key!r} "
              f"(mask auto-derived). horizons_list={horizons_list}")

    has_perp = bool(model_cfg.get("use_perp_residual", False))
    # x_channel slice (for the matched spot-64 BASE arm): keep leading 64 cols of X.
    slice_cfg = data_cfg.get("slice") or {}
    slice_xc = slice_cfg.get("x_channels")
    slice_kw = (dict(x_channels=slice_xc) if slice_xc is not None else {})
    print(f"[train_v2arch] use_perp_residual={has_perp} "
          f"use_long_context={bool(model_cfg.get('use_long_context', False))} "
          f"slice={slice_cfg or None}")

    for fold_idx, fold in enumerate(folds):
        if fold_idx < args.start_fold:
            continue
        if args.max_folds is not None and fold_idx >= args.max_folds:
            print(f"[train_v2arch] --max-folds={args.max_folds} reached."); break
        fold_dir = osp.join(output_dir, f"fold_{fold_idx}")
        os.makedirs(fold_dir, exist_ok=True)
        print(f"\n{'='*60}\n[train_v2arch] Fold {fold_idx}: "
              f"train={fold['train'][0]}..{fold['train'][-1]}({len(fold['train'])}d) "
              f"val={fold['val'][0]}..{fold['val'][-1]} "
              f"test={fold['test'][0]}..{fold['test'][-1]}\n{'='*60}", flush=True)

        # --- streaming stats (X + y) on un-normalised train days ----------------
        t0 = time.time()
        stats_kw = dict(normalize=False)
        if horizons_list is not None:
            stats_kw["horizons"] = horizons_list
        stats_kw["y_rolling_sigma_path"] = data_cfg.get("y_rolling_sigma_path")
        stats_kw.update(slice_kw)
        stats_ds = V2ArchDataset(npz_dir, fold["train"], **stats_kw)
        x_mean, x_std = stats_ds.compute_stats()
        y_median, y_sigma = stats_ds.compute_y_stats()
        xlong_mean, xlong_std = stats_ds.compute_long_stats()
        stats_ds.clear_cache(); del stats_ds
        print(f"[train_v2arch] stats {time.time()-t0:.1f}s y_median={y_median:.6e} "
              f"y_sigma={y_sigma:.6e} xlong_mean[:3]={np.round(xlong_mean[:3],4)}", flush=True)

        y_norm = (y_median, y_sigma, 5.0)
        preload = bool(data_cfg.get("preload", False))
        common = dict(normalize=True, x_mean=x_mean, x_std=x_std, y_norm=y_norm,
                      preload=preload, xlong_mean=xlong_mean, xlong_std=xlong_std,
                      **slice_kw, **_common_ds_kwargs(data_cfg, horizons_list))
        train_ds = V2ArchDataset(npz_dir, fold["train"], **common)
        val_ds = V2ArchDataset(npz_dir, fold["val"], **common)
        test_ds = V2ArchDataset(npz_dir, fold["test"], **common)

        sample0 = train_ds._load_day(0)
        n_features = int(sample0["X"].shape[-1])
        raw_levels = int(sample0["X_raw"].shape[-2])
        model = build_v2arch_model(model_cfg, n_features, raw_levels)
        print(f"[train_v2arch] params={sum(p.numel() for p in model.parameters()):,}", flush=True)

        best = train_one_fold_v2(
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
        )
        print(f"[train_v2arch] Fold {fold_idx} best: {best}", flush=True)

        np.savez(osp.join(fold_dir, "norm_params.npz"), x_mean=x_mean, x_std=x_std,
                 y_median=np.array(y_median), y_sigma=np.array(y_sigma),
                 xlong_mean=xlong_mean, xlong_std=xlong_std)

        _run_test_eval_v2(model, fold_dir, test_ds, train_cfg["batch_size"], device,
                          horizon_sec=horizon_sec, stride=stride,
                          y_sigma=y_sigma, y_median=y_median, has_perp=has_perp)
        if osp.exists(osp.join(fold_dir, "ema_best.pt")):
            _run_test_eval_v2(model, fold_dir, test_ds, train_cfg["batch_size"], device,
                              horizon_sec=horizon_sec, stride=stride,
                              y_sigma=y_sigma, y_median=y_median, has_perp=has_perp,
                              ckpt_name="ema_best.pt", preds_name="ema_test_preds.npz",
                              results_name="ema_test_results.json")

    print("\n[train_v2arch] All done.")


if __name__ == "__main__":
    main()

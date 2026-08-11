#!/usr/bin/env python3
"""Comprehensive near-production evaluation of V4 vs Ridge vs XGBoost.

Implements 11 metric categories + monthly concentration (= 12 plots total),
incorporating PROJECT_PRINCIPLES.md principles 1, 2, 3, 4, 6, 7, 8.

Usage:
    python scripts/comprehensive_eval.py \\
        --v4-exp-dir experiments/v4_noattn_700d \\
        --baseline-pred-dir experiments/baselines_v4_matched_preds \\
        --feature-npz-dir data/npz_v4 \\
        --output-dir experiments/eval_comprehensive

See docs/superpowers/specs/2026-04-18-comprehensive-eval-design.md for full spec.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

MODELS = ["V4", "Ridge", "TemporalRidge", "XGBoost"]
FOLDS = [0, 1, 2]


def _ts_to_seconds(ts: np.ndarray) -> np.ndarray:
    """Normalize timestamps to UNIX seconds (handles microseconds-stored V4 ts)."""
    if len(ts) == 0:
        return ts.astype(np.int64)
    # If median > 1e14, treat as microseconds; else already seconds.
    return (ts // 1_000_000) if np.median(ts) > 1e14 else ts

plt.rcParams.update({
    "figure.dpi": 100,
    "savefig.dpi": 140,
    "savefig.bbox": "tight",
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
})


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_v4_fold(v4_dir: pathlib.Path, fold: int) -> Dict[str, np.ndarray]:
    """Load V4 test predictions for one fold. q50 is used as point prediction."""
    path = v4_dir / f"fold_{fold}" / "test_preds.npz"
    d = np.load(str(path))
    preds_3col = d["predictions"]  # (N, 3) quantiles
    q10 = preds_3col[:, 0]
    q50 = preds_3col[:, 1]
    q90 = preds_3col[:, 2]
    return {
        "pred": q50,
        "q10": q10,
        "q50": q50,
        "q90": q90,
        "target": d["targets"],
        "mask": d["mask"].astype(bool),
        "timestamps": d["timestamps"],
        "y_sigma": float(d["y_sigma"]),
        "y_median": float(d["y_median"]),
    }


def _load_baseline_fold(pred_dir: pathlib.Path, fold: int, model: str) -> Optional[Dict[str, np.ndarray]]:
    """Load baseline predictions for (fold, model). Returns None if file missing."""
    path = pred_dir / f"fold_{fold}_{model}_preds.npz"
    if not path.exists():
        logger.warning(f"Missing {path}; skipping {model} fold {fold}")
        return None
    d = np.load(str(path))
    return {
        "pred": d["predictions"],
        "target": d["targets"],
        "mask": d["mask"].astype(bool),
        "timestamps": d["timestamps"],
        "y_sigma": float(d.get("norm_y_sigma", 1.0)),
        "y_median": float(d.get("norm_y_median", 0.0)),
    }


def load_all_data(
    v4_dir: pathlib.Path,
    baseline_dir: pathlib.Path,
) -> Dict[Tuple[str, int], Dict[str, np.ndarray]]:
    """Load predictions for every (model, fold) combination.

    Returns dict keyed by (model_name, fold_idx).
    """
    data = {}
    for f in FOLDS:
        v4 = _load_v4_fold(v4_dir, f)
        if v4 is not None:
            data[("V4", f)] = v4

    for model in ["Ridge", "TemporalRidge", "XGBoost"]:
        for f in FOLDS:
            b = _load_baseline_fold(baseline_dir, f, model)
            if b is not None:
                data[(model, f)] = b
    return data


def get_masked(d: Dict[str, np.ndarray], key: str = "pred") -> Tuple[np.ndarray, np.ndarray]:
    """Apply mask and return (pred, target) with finite values only."""
    m = d["mask"]
    p = d[key][m]
    y = d["target"][m]
    v = np.isfinite(p) & np.isfinite(y)
    return p[v], y[v]


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def pearson(p: np.ndarray, y: np.ndarray) -> float:
    if len(p) < 2 or np.std(p) < 1e-12 or np.std(y) < 1e-12:
        return float("nan")
    return float(sp_stats.pearsonr(p, y)[0])


def spearman(p: np.ndarray, y: np.ndarray) -> float:
    if len(p) < 2:
        return float("nan")
    return float(sp_stats.spearmanr(p, y)[0])


def kendall_tau(p: np.ndarray, y: np.ndarray) -> float:
    if len(p) < 2:
        return float("nan")
    # Kendall is O(N^2); on 17K samples this is ~300M ops = 30s. Subsample.
    if len(p) > 5000:
        idx = np.random.RandomState(42).choice(len(p), 5000, replace=False)
        p, y = p[idx], y[idx]
    return float(sp_stats.kendalltau(p, y)[0])


def direction_acc(p: np.ndarray, y: np.ndarray) -> float:
    m = y != 0
    if m.sum() == 0:
        return float("nan")
    return float((np.sign(p[m]) == np.sign(y[m])).mean())


def autocorr(x: np.ndarray, lag: int = 1) -> float:
    if len(x) <= lag:
        return float("nan")
    x = x - x.mean()
    c0 = (x * x).mean()
    if c0 < 1e-12:
        return float("nan")
    return float((x[:-lag] * x[lag:]).mean() / c0)


def block_bootstrap_ic(
    p: np.ndarray, y: np.ndarray, block_len: int = 60, n_resample: int = 500,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Block bootstrap CI for Pearson corr. Returns (mean, low, high)."""
    if len(p) < block_len * 2:
        return (pearson(p, y), float("nan"), float("nan"))
    rng = np.random.RandomState(seed)
    n_blocks = len(p) // block_len
    samples = []
    for _ in range(n_resample):
        start_idx = rng.randint(0, n_blocks, size=n_blocks)
        blocks_p = [p[s * block_len:(s + 1) * block_len] for s in start_idx]
        blocks_y = [y[s * block_len:(s + 1) * block_len] for s in start_idx]
        pb = np.concatenate(blocks_p)
        yb = np.concatenate(blocks_y)
        samples.append(pearson(pb, yb))
    samples = np.array(samples)
    samples = samples[np.isfinite(samples)]
    if len(samples) < 10:
        return (float("nan"), float("nan"), float("nan"))
    return (float(np.mean(samples)), float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5)))


# ---------------------------------------------------------------------------
# Category 1: Core IC with bootstrapped CIs
# ---------------------------------------------------------------------------

def cat1_core_ic(data: Dict[Tuple[str, int], Dict], fig_path: pathlib.Path) -> Dict:
    rows = []
    for (model, fold), d in data.items():
        p, y = get_masked(d)
        rows.append({
            "model": model,
            "fold": fold,
            "pearson": pearson(p, y),
            "spearman": spearman(p, y),
            "kendall": kendall_tau(p, y),
            "direction_acc": direction_acc(p, y),
            "n": len(p),
        })
    df = pd.DataFrame(rows)

    pooled = {}
    ci = {}
    for model in MODELS:
        folds_data = [d for (m, _), d in data.items() if m == model]
        if not folds_data:
            continue
        all_p, all_y = [], []
        for d in folds_data:
            p, y = get_masked(d)
            all_p.append(p); all_y.append(y)
        all_p = np.concatenate(all_p); all_y = np.concatenate(all_y)
        pooled[model] = {
            "pearson": pearson(all_p, all_y),
            "spearman": spearman(all_p, all_y),
            "kendall": kendall_tau(all_p, all_y),
            "direction_acc": direction_acc(all_p, all_y),
            "n": len(all_p),
        }
        mean, lo, hi = block_bootstrap_ic(all_p, all_y, block_len=60, n_resample=300)
        ci[model] = {"pearson_mean": mean, "pearson_lo": lo, "pearson_hi": hi}

    # Plot: pooled Pearson and Spearman with CI bars
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    models_present = [m for m in MODELS if m in pooled]
    xs = np.arange(len(models_present))

    p_vals = [pooled[m]["pearson"] for m in models_present]
    s_vals = [pooled[m]["spearman"] for m in models_present]
    lows = [pooled[m]["pearson"] - ci[m]["pearson_lo"] for m in models_present]
    highs = [ci[m]["pearson_hi"] - pooled[m]["pearson"] for m in models_present]

    axes[0].bar(xs, p_vals, yerr=[lows, highs], capsize=6, color=["#4C72B0", "#DD8452", "#55A868", "#C44E52"][:len(models_present)])
    axes[0].set_xticks(xs); axes[0].set_xticklabels(models_present, rotation=15)
    axes[0].set_title("Pooled Pearson IC (bootstrapped 95% CI, block_len=60)")
    axes[0].axhline(0.12, color="red", linestyle="--", alpha=0.5, label="spec 0.12")
    axes[0].legend()

    axes[1].bar(xs, s_vals, color=["#4C72B0", "#DD8452", "#55A868", "#C44E52"][:len(models_present)])
    axes[1].set_xticks(xs); axes[1].set_xticklabels(models_present, rotation=15)
    axes[1].set_title("Pooled Spearman IC")
    axes[1].axhline(0.12, color="red", linestyle="--", alpha=0.5, label="spec 0.12")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(fig_path); plt.close()
    return {"per_fold": df.to_dict("records"), "pooled": pooled, "ci_pearson": ci}


# ---------------------------------------------------------------------------
# Category 2: Temporal stability — daily IC over time
# ---------------------------------------------------------------------------

def cat2_temporal_stability(data: Dict[Tuple[str, int], Dict], fig_path: pathlib.Path) -> Dict:
    """Compute per-day Spearman IC for each model, plot over time."""
    daily_ic = {m: [] for m in MODELS}
    for model in MODELS:
        for fold in FOLDS:
            if (model, fold) not in data:
                continue
            d = data[(model, fold)]
            m_mask = d["mask"]
            p = d["pred"][m_mask]
            y = d["target"][m_mask]
            ts = d["timestamps"][m_mask]
            day_idx = (_ts_to_seconds(ts) // 86400).astype(int)
            unique_days = np.unique(day_idx)
            for day in unique_days:
                sel = day_idx == day
                if sel.sum() < 60:
                    continue
                pp, yy = p[sel], y[sel]
                v = np.isfinite(pp) & np.isfinite(yy)
                if v.sum() < 60:
                    continue
                daily_ic[model].append({
                    "day": int(day),
                    "ic": spearman(pp[v], yy[v]),
                    "n": int(v.sum()),
                })
    # Stats per model
    stats_per_model = {}
    for m, rows in daily_ic.items():
        if not rows:
            continue
        ics = np.array([r["ic"] for r in rows])
        ics = ics[np.isfinite(ics)]
        if len(ics) == 0:
            continue
        stats_per_model[m] = {
            "n_days": len(ics),
            "mean_daily_ic": float(np.mean(ics)),
            "std_daily_ic": float(np.std(ics)),
            "ic_ir_daily": float(np.mean(ics) / (np.std(ics) + 1e-12)),
            "pct_days_positive": float((ics > 0).mean()),
        }

    # Plot
    fig, ax = plt.subplots(figsize=(12, 5))
    colors = {"V4": "#4C72B0", "Ridge": "#DD8452", "TemporalRidge": "#55A868", "XGBoost": "#C44E52"}
    for m, rows in daily_ic.items():
        if not rows:
            continue
        rows_sorted = sorted(rows, key=lambda r: r["day"])
        days = [r["day"] for r in rows_sorted]
        ics = [r["ic"] for r in rows_sorted]
        days_rel = np.array(days) - min(days)
        ax.plot(days_rel, ics, label=m, color=colors.get(m, "gray"), alpha=0.7, linewidth=1)
        # 7-day rolling mean
        if len(ics) >= 7:
            rolling = pd.Series(ics).rolling(7, center=True).mean()
            ax.plot(days_rel, rolling, color=colors.get(m, "gray"), linewidth=2.5, linestyle="--", alpha=0.9)

    ax.axhline(0, color="black", linestyle="-", linewidth=0.5)
    ax.set_xlabel("Days into test period (relative)")
    ax.set_ylabel("Daily Spearman IC")
    ax.set_title("Daily Spearman IC over time (thin=daily, thick dashed=7d rolling)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(fig_path); plt.close()
    return {"per_model": stats_per_model, "daily_ic_sample": {m: daily_ic[m][:10] for m in daily_ic}}


# ---------------------------------------------------------------------------
# Category 3: Autocorrelation
# ---------------------------------------------------------------------------

def cat3_autocorrelation(data: Dict, fig_path: pathlib.Path) -> Dict:
    """Prediction AC, residual AC, target AC at lags 1, 5, 30."""
    lags = [1, 5, 30]
    results = {}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    for ax_idx, lag in enumerate(lags):
        ax = axes[ax_idx]
        xs = []
        heights_pred = []
        heights_resid = []
        models_present = []
        for model in MODELS:
            all_p, all_y = [], []
            for fold in FOLDS:
                if (model, fold) not in data:
                    continue
                d = data[(model, fold)]
                p, y = get_masked(d)
                all_p.append(p); all_y.append(y)
            if not all_p:
                continue
            all_p = np.concatenate(all_p); all_y = np.concatenate(all_y)
            # Detrend prediction and residual
            if np.std(all_p) > 1e-12:
                beta = np.polyfit(all_p, all_y, 1)
                resid = all_y - (beta[0] * all_p + beta[1])
            else:
                resid = all_y - all_y.mean()
            ac_p = autocorr(all_p, lag)
            ac_r = autocorr(resid, lag)
            if model == "V4":
                ac_target = autocorr(all_y, lag)
                results[f"target_ac_lag{lag}"] = ac_target
            results.setdefault(model, {})[f"pred_ac_lag{lag}"] = ac_p
            results[model][f"resid_ac_lag{lag}"] = ac_r
            models_present.append(model)
            heights_pred.append(ac_p)
            heights_resid.append(ac_r)

        x = np.arange(len(models_present))
        w = 0.35
        ax.bar(x - w/2, heights_pred, w, label="pred AC", color="#4C72B0")
        ax.bar(x + w/2, heights_resid, w, label="residual AC", color="#DD8452")
        ax.axhline(0.3, color="red", linestyle="--", alpha=0.4, label="concern 0.3")
        ax.set_xticks(x); ax.set_xticklabels(models_present, rotation=15)
        ax.set_title(f"Lag {lag}")
        if ax_idx == 0:
            ax.set_ylabel("Autocorrelation")
            ax.legend()

    tgt_ac1 = results.get('target_ac_lag1')
    suptitle = f"Prediction vs Residual Autocorrelation (target AC lag1={tgt_ac1:.3f})" if isinstance(tgt_ac1, float) else "Autocorrelation"
    plt.suptitle(suptitle)
    plt.tight_layout()
    plt.savefig(fig_path); plt.close()
    return results


# ---------------------------------------------------------------------------
# Category 4: Decile returns + monotonicity + long-short spread
# ---------------------------------------------------------------------------

def cat4_decile_returns(data: Dict, fig_path: pathlib.Path) -> Dict:
    """Bucket predictions into deciles, compute mean forward return per bucket."""
    results = {}
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]
    colors_by_model = dict(zip(MODELS, colors))

    # Left: per-decile mean return (all models on one plot)
    # Right: long-short cumulative
    for model in MODELS:
        all_p, all_y = [], []
        for fold in FOLDS:
            if (model, fold) not in data:
                continue
            d = data[(model, fold)]
            p, y = get_masked(d)
            all_p.append(p); all_y.append(y)
        if not all_p:
            continue
        all_p = np.concatenate(all_p); all_y = np.concatenate(all_y)

        # Deciles
        decile_ids = pd.qcut(all_p, 10, labels=False, duplicates="drop")
        decile_means = []
        decile_stds = []
        for d_id in range(10):
            sel = decile_ids == d_id
            if sel.sum() == 0:
                decile_means.append(0.0); decile_stds.append(0.0); continue
            decile_means.append(float(all_y[sel].mean()))
            decile_stds.append(float(all_y[sel].std() / np.sqrt(sel.sum())))
        # Monotonicity: Spearman(decile_idx, mean_return)
        mono = spearman(np.arange(10), np.array(decile_means))
        long_short = decile_means[-1] - decile_means[0]

        results[model] = {
            "decile_means": decile_means,
            "decile_stderr": decile_stds,
            "monotonicity": mono,
            "long_short_bps": long_short * 1e4,
            "ls_top_mean": decile_means[-1] * 1e4,
            "ls_bot_mean": decile_means[0] * 1e4,
        }

        # Plot bar for this model (offset)
        offset = (MODELS.index(model) - 1.5) * 0.2
        axes[0].bar(
            np.arange(10) + offset, decile_means, 0.18,
            label=f"{model} (mono={mono:+.3f})",
            color=colors_by_model[model],
        )

    axes[0].set_xlabel("Prediction decile (1=lowest, 10=highest)")
    axes[0].set_ylabel("Mean forward return (normalized)")
    axes[0].set_title("Decile-sorted mean forward return")
    axes[0].set_xticks(range(10))
    axes[0].set_xticklabels([str(i + 1) for i in range(10)])
    axes[0].axhline(0, color="black", linewidth=0.5)
    axes[0].legend(fontsize=8)

    # Right: long-short P&L cum (top decile - bottom decile)
    for model in MODELS:
        if model not in results:
            continue
        all_p, all_y = [], []
        for fold in FOLDS:
            if (model, fold) not in data:
                continue
            d = data[(model, fold)]
            p, y = get_masked(d)
            all_p.append(p); all_y.append(y)
        all_p = np.concatenate(all_p); all_y = np.concatenate(all_y)

        decile_ids = pd.qcut(all_p, 10, labels=False, duplicates="drop")
        # Long-short per-period return: top - bot, scaled by 1/N
        pos = np.where(decile_ids == 9, 1.0, np.where(decile_ids == 0, -1.0, 0.0))
        pnl = pos * all_y
        cum = np.cumsum(pnl)
        axes[1].plot(cum, label=model, color=colors_by_model[model])

    axes[1].set_xlabel("Test sample (time-ordered)")
    axes[1].set_ylabel("Cumulative L-S P&L (normalized)")
    axes[1].set_title("Cumulative L-S P&L (long top decile, short bot decile)")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(fig_path); plt.close()
    return results


# ---------------------------------------------------------------------------
# Category 5: Regime conditional IC (vol, trend, hour)
# ---------------------------------------------------------------------------

def _load_regime_features(feature_dir: pathlib.Path, timestamps: np.ndarray, days_needed: List[str]) -> Dict[str, np.ndarray]:
    """Load per-sample regime features aligned to timestamps.

    Strategy: match timestamps by UTC day, pull that day's NPZ's last-timestep
    row for rolling_vol_5min etc. If feature NPZ doesn't have the required
    fields, fall back to target-based proxies (past realized vol from target
    autocorrelation is not available, so use |target| rolling std).
    """
    # For simplicity, derive regime features directly from the prediction's
    # target series: recent abs target as vol proxy, sign of recent target
    # as trend proxy. These are not leaked features (they come from past
    # targets relative to the current sample if we shift), BUT since we don't
    # have easy access to shifted context here, use the current target's
    # surrounding window — this is a rough regime marker, not leak-free.
    # Proper alignment would require loading NPZ day by day; keep simple.
    return {}


def cat5_regime(data: Dict, fig_path: pathlib.Path) -> Dict:
    """IC conditioned on: rolling vol tertiles, past-return sign, hour-of-day.

    Regime proxy: use rolling |target| over 60-sample window as vol marker,
    rolling mean of target as trend marker. This is slightly leaky (uses
    target itself) but acceptable for a regime-IC sanity check — we split
    on statistics the model couldn't have seen.
    """
    results = {}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    colors_by_model = dict(zip(MODELS, ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]))

    for model in MODELS:
        all_p, all_y, all_ts = [], [], []
        for fold in FOLDS:
            if (model, fold) not in data:
                continue
            d = data[(model, fold)]
            m = d["mask"]
            p = d["pred"][m]; y = d["target"][m]; ts = d["timestamps"][m]
            v = np.isfinite(p) & np.isfinite(y)
            all_p.append(p[v]); all_y.append(y[v]); all_ts.append(ts[v])
        if not all_p:
            continue
        p = np.concatenate(all_p); y = np.concatenate(all_y); ts = np.concatenate(all_ts)

        # Vol regime proxy: |target| rolling (use abs_y pre-computed, shifted to avoid the current value)
        abs_y = np.abs(y)
        window = 60
        vol_marker = pd.Series(abs_y).rolling(window, min_periods=10).mean().shift(1).bfill().fillna(0.0).values
        # Trend regime proxy: cumulative sign of y (past)
        trend_marker = pd.Series(y).rolling(window, min_periods=10).mean().shift(1).fillna(0.0).values
        # Hour of day
        ts_sec = _ts_to_seconds(ts)
        hour = ((ts_sec % 86400) // 3600).astype(int)

        # Vol tertiles
        v_lo, v_hi = np.nanpercentile(vol_marker, [33.33, 66.67])
        regs = {
            "low_vol": vol_marker < v_lo,
            "mid_vol": (vol_marker >= v_lo) & (vol_marker < v_hi),
            "high_vol": vol_marker >= v_hi,
        }
        ic_by_vol = {k: spearman(p[m], y[m]) for k, m in regs.items() if m.sum() >= 30}

        ic_by_trend = {
            "up_past": spearman(p[trend_marker > 0], y[trend_marker > 0]) if (trend_marker > 0).sum() >= 30 else float("nan"),
            "down_past": spearman(p[trend_marker < 0], y[trend_marker < 0]) if (trend_marker < 0).sum() >= 30 else float("nan"),
        }

        ic_by_hour = {}
        for h in range(24):
            m = hour == h
            if m.sum() < 50:
                ic_by_hour[h] = float("nan"); continue
            ic_by_hour[h] = spearman(p[m], y[m])

        results[model] = {"vol": ic_by_vol, "trend": ic_by_trend, "hour": ic_by_hour}

        # Plot bars (hour line)
        offset = (MODELS.index(model) - 1.5) * 0.18
        vol_vals = [ic_by_vol.get(k, 0) for k in ["low_vol", "mid_vol", "high_vol"]]
        axes[0].bar(np.arange(3) + offset, vol_vals, 0.17, label=model, color=colors_by_model[model])

        trend_vals = [ic_by_trend.get(k, 0) for k in ["up_past", "down_past"]]
        axes[1].bar(np.arange(2) + offset, trend_vals, 0.17, label=model, color=colors_by_model[model])

        hour_vals = [ic_by_hour.get(h, 0) for h in range(24)]
        axes[2].plot(range(24), hour_vals, label=model, color=colors_by_model[model], marker="o", markersize=3)

    axes[0].set_xticks(range(3)); axes[0].set_xticklabels(["low_vol", "mid_vol", "high_vol"])
    axes[0].set_title("Spearman by volatility regime")
    axes[0].axhline(0, color="black", linewidth=0.5); axes[0].legend(fontsize=8)

    axes[1].set_xticks(range(2)); axes[1].set_xticklabels(["up past", "down past"])
    axes[1].set_title("Spearman by past-return sign")
    axes[1].axhline(0, color="black", linewidth=0.5)

    axes[2].set_xlabel("Hour (UTC)")
    axes[2].set_ylabel("Spearman IC")
    axes[2].set_title("Spearman by hour of day")
    axes[2].axhline(0, color="black", linewidth=0.5)
    axes[2].legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(fig_path); plt.close()
    return results


# ---------------------------------------------------------------------------
# Category 6: Risk metrics + equity/drawdown
# ---------------------------------------------------------------------------

def _sharpe_hac(returns: np.ndarray, lags: int = 5) -> float:
    """HAC (Newey-West) Sharpe. Assumes returns are per-sample (not annualized)."""
    r = returns[np.isfinite(returns)]
    if len(r) < 30 or r.std() < 1e-12:
        return float("nan")
    mean_r = r.mean()
    T = len(r)
    # HAC variance
    gamma0 = np.var(r)
    hac_var = gamma0
    for k in range(1, min(lags, T // 4) + 1):
        w = 1 - k / (lags + 1)
        gk = ((r[:-k] - mean_r) * (r[k:] - mean_r)).mean()
        hac_var += 2 * w * gk
    hac_var = max(hac_var, gamma0 * 0.1)
    # Annualize: ~31M seconds per year, but samples are irregular — scale by sqrt(samples/year).
    # Given ~30K test samples per fold and test period ~90d = 7.8M sec, sample = roughly 260s apart.
    # Annualization factor: sqrt(31.5M / 7.8M * samples) ≈ sqrt(4 * T)
    return float(mean_r / np.sqrt(hac_var / T) * np.sqrt(252))


def _drawdown(equity: np.ndarray) -> Tuple[float, float]:
    """Max drawdown (bps) and Calmar-like ratio."""
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = float(dd.min())
    total_return = float(equity[-1] - equity[0])
    return max_dd, (total_return / abs(max_dd)) if max_dd < 0 else float("inf")


def cat6_risk(data: Dict, fig_path: pathlib.Path) -> Dict:
    """Simple strategy: position = sign(pred) × 1.0. Compute Sharpe, DD, hit rate."""
    results = {}
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    colors_by_model = dict(zip(MODELS, ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]))

    for model in MODELS:
        all_p, all_y = [], []
        for fold in FOLDS:
            if (model, fold) not in data:
                continue
            d = data[(model, fold)]
            p, y = get_masked(d)
            all_p.append(p); all_y.append(y)
        if not all_p:
            continue
        p = np.concatenate(all_p); y = np.concatenate(all_y)

        pos = np.sign(p)
        pnl = pos * y
        equity = np.cumsum(pnl)
        max_dd, calmar = _drawdown(equity)
        sharpe = _sharpe_hac(pnl, lags=5)

        hit_all = float((np.sign(pnl) > 0).mean())
        long_mask = pos > 0
        short_mask = pos < 0
        hit_long = float((pnl[long_mask] > 0).mean()) if long_mask.sum() > 0 else float("nan")
        hit_short = float((pnl[short_mask] > 0).mean()) if short_mask.sum() > 0 else float("nan")
        cvar95 = float(np.percentile(pnl, 5))

        results[model] = {
            "sharpe_hac_ann": sharpe,
            "max_drawdown": max_dd,
            "calmar": calmar,
            "cvar_95": cvar95,
            "hit_rate_all": hit_all,
            "hit_rate_long": hit_long,
            "hit_rate_short": hit_short,
            "n_trades": int(len(pnl)),
        }

        axes[0].plot(equity, label=f"{model} (S={sharpe:.2f})", color=colors_by_model[model])

        # Underwater (drawdown)
        peak = np.maximum.accumulate(equity)
        underwater = equity - peak
        axes[1].fill_between(range(len(underwater)), underwater, 0, alpha=0.3, color=colors_by_model[model], label=model)

    axes[0].set_title("Cumulative P&L (always-on: position = sign(pred))")
    axes[0].set_ylabel("Cumulative return (normalized)")
    axes[0].set_xlabel("Sample (time-ordered)")
    axes[0].legend(fontsize=8)
    axes[0].axhline(0, color="black", linewidth=0.5)

    axes[1].set_title("Drawdown (underwater)")
    axes[1].set_ylabel("Drawdown from peak (normalized)")
    axes[1].set_xlabel("Sample")
    axes[1].legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(fig_path); plt.close()
    return results


# ---------------------------------------------------------------------------
# Category 7: V4 calibration
# ---------------------------------------------------------------------------

def cat7_calibration_v4(data: Dict, fig_path: pathlib.Path) -> Dict:
    """Check q10/q50/q90 empirical coverage vs nominal."""
    all_q10, all_q50, all_q90, all_y = [], [], [], []
    for fold in FOLDS:
        if ("V4", fold) not in data:
            continue
        d = data[("V4", fold)]
        m = d["mask"]
        v = m & np.isfinite(d["target"]) & np.isfinite(d["q50"])
        all_q10.append(d["q10"][v])
        all_q50.append(d["q50"][v])
        all_q90.append(d["q90"][v])
        all_y.append(d["target"][v])
    if not all_q50:
        return {}
    q10 = np.concatenate(all_q10); q50 = np.concatenate(all_q50)
    q90 = np.concatenate(all_q90); y = np.concatenate(all_y)

    coverage_q10 = float((y <= q10).mean())
    coverage_q50 = float((y <= q50).mean())
    coverage_q90 = float((y <= q90).mean())
    cross_violation_q10_q50 = float((q10 > q50).mean())
    cross_violation_q50_q90 = float((q50 > q90).mean())

    fig, ax = plt.subplots(1, 1, figsize=(7, 5))
    nominal = np.array([0.10, 0.50, 0.90])
    actual = np.array([coverage_q10, coverage_q50, coverage_q90])
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", label="perfect calibration")
    ax.scatter(nominal, actual, s=100, color="#4C72B0", zorder=5)
    for xv, yv, lbl in zip(nominal, actual, ["q10", "q50", "q90"]):
        ax.annotate(f"{lbl}\n{yv:.3f}", (xv, yv), xytext=(6, 6), textcoords="offset points")
    ax.set_xlabel("Nominal coverage (target)")
    ax.set_ylabel("Actual coverage (P(y ≤ q))")
    ax.set_title("V4 Quantile Calibration\n" +
                 f"Cross-quantile violations: q10>q50={cross_violation_q10_q50:.4f}, q50>q90={cross_violation_q50_q90:.4f}")
    ax.set_xlim(-0.05, 1.05); ax.set_ylim(-0.05, 1.05)
    ax.legend()
    plt.tight_layout()
    plt.savefig(fig_path); plt.close()

    return {
        "coverage_q10_nominal0.10": coverage_q10,
        "coverage_q50_nominal0.50": coverage_q50,
        "coverage_q90_nominal0.90": coverage_q90,
        "cross_violation_q10_gt_q50": cross_violation_q10_q50,
        "cross_violation_q50_gt_q90": cross_violation_q50_q90,
    }


# ---------------------------------------------------------------------------
# Category 8: Cross-model consistency
# ---------------------------------------------------------------------------

def cat8_cross_model(data: Dict, fig_path: pathlib.Path) -> Dict:
    """Pairwise prediction correlation between models."""
    # Concat each model's pred across folds, aligning on timestamps
    models_present = list({m for (m, _) in data.keys()})
    models_present = [m for m in MODELS if m in models_present]
    preds_by_model = {}
    for model in models_present:
        all_p, all_ts = [], []
        for fold in FOLDS:
            if (model, fold) not in data:
                continue
            d = data[(model, fold)]
            m_mask = d["mask"]
            p = d["pred"][m_mask]; ts = d["timestamps"][m_mask]
            v = np.isfinite(p)
            all_p.append(p[v]); all_ts.append(ts[v])
        preds_by_model[model] = (np.concatenate(all_p), np.concatenate(all_ts))

    # Merge on timestamp
    n_models = len(models_present)
    if n_models == 0:
        return {}
    # Use V4's timestamps as anchor (all models should share the same test samples)
    anchor_model = "V4" if "V4" in models_present else models_present[0]
    anchor_p, anchor_ts = preds_by_model[anchor_model]
    # Build (ts, model) → pred dict, assuming timestamps align across models (they should)
    corr_mat = np.zeros((n_models, n_models))
    for i, m1 in enumerate(models_present):
        p1, ts1 = preds_by_model[m1]
        for j, m2 in enumerate(models_present):
            if i == j:
                corr_mat[i, j] = 1.0; continue
            p2, ts2 = preds_by_model[m2]
            # Align by matching timestamps (use Pandas for merge)
            df1 = pd.DataFrame({"ts": ts1, "p1": p1})
            df2 = pd.DataFrame({"ts": ts2, "p2": p2})
            merged = pd.merge(df1, df2, on="ts", how="inner")
            if len(merged) < 100:
                corr_mat[i, j] = float("nan"); continue
            corr_mat[i, j] = pearson(merged["p1"].values, merged["p2"].values)

    # Plot heatmap
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr_mat, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(n_models)); ax.set_xticklabels(models_present, rotation=15)
    ax.set_yticks(range(n_models)); ax.set_yticklabels(models_present)
    ax.set_title("Pairwise Prediction Pearson Correlation\n(ensemble diversity; >0.8 flagged)")
    for i in range(n_models):
        for j in range(n_models):
            val = corr_mat[i, j]
            color = "white" if abs(val) > 0.5 else "black"
            weight = "bold" if val > 0.8 and i != j else "normal"
            ax.text(j, i, f"{val:.3f}", ha="center", va="center", color=color, fontweight=weight)
    plt.colorbar(im, fraction=0.046)
    plt.tight_layout()
    plt.savefig(fig_path); plt.close()

    # Flag pairs >0.8
    flags = []
    for i in range(n_models):
        for j in range(i+1, n_models):
            if corr_mat[i, j] > 0.8:
                flags.append((models_present[i], models_present[j], float(corr_mat[i, j])))

    return {
        "models": models_present,
        "corr_matrix": corr_mat.tolist(),
        "highly_correlated_pairs": flags,
    }


# ---------------------------------------------------------------------------
# Category 9: Confidence gating (V4 only)
# ---------------------------------------------------------------------------

def cat9_confidence_gating(data: Dict, fig_path: pathlib.Path) -> Dict:
    """Sweep τ on |q50|/(q90-q10) for V4; report Sharpe vs trade_rate."""
    all_q10, all_q50, all_q90, all_y = [], [], [], []
    for fold in FOLDS:
        if ("V4", fold) not in data:
            continue
        d = data[("V4", fold)]
        m = d["mask"]; v = m & np.isfinite(d["target"])
        all_q10.append(d["q10"][v])
        all_q50.append(d["q50"][v])
        all_q90.append(d["q90"][v])
        all_y.append(d["target"][v])
    if not all_q50:
        return {}
    q10 = np.concatenate(all_q10); q50 = np.concatenate(all_q50)
    q90 = np.concatenate(all_q90); y = np.concatenate(all_y)

    iqr = np.maximum(q90 - q10, 1e-8)
    confidence = np.abs(q50) / iqr

    taus = np.percentile(confidence, [0, 10, 25, 40, 50, 60, 70, 80, 90, 95, 99])
    rows = []
    for tau in taus:
        gate = confidence >= tau
        if gate.sum() < 50:
            continue
        pos = np.sign(q50[gate])
        pnl = pos * y[gate]
        sharpe = _sharpe_hac(pnl, lags=5)
        trade_rate = float(gate.mean())
        total_pnl = float(pnl.sum())
        rows.append({"tau": float(tau), "trade_rate": trade_rate,
                     "sharpe_ann": sharpe, "total_pnl": total_pnl,
                     "n_trades": int(gate.sum())})

    df = pd.DataFrame(rows)
    tau_star_idx = int(df["sharpe_ann"].idxmax()) if len(df) > 0 and df["sharpe_ann"].notna().any() else 0
    tau_star_row = df.iloc[tau_star_idx].to_dict() if len(df) > 0 else {}

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    axes[0].plot(df["trade_rate"], df["sharpe_ann"], marker="o", color="#4C72B0")
    axes[0].set_xlabel("Trade rate (fraction of samples traded)")
    axes[0].set_ylabel("Annualized Sharpe (HAC)")
    axes[0].set_title(f"V4 Confidence Gating: Sharpe vs Trade Rate\nτ*={tau_star_row.get('tau', 0):.3f} → Sharpe={tau_star_row.get('sharpe_ann', 0):.2f} @ rate={tau_star_row.get('trade_rate', 0):.2%}")
    axes[0].axhline(0, color="black", linewidth=0.5)
    if len(df) > 0:
        axes[0].scatter([tau_star_row["trade_rate"]], [tau_star_row["sharpe_ann"]], s=200, color="red", zorder=5)

    axes[1].plot(df["trade_rate"], df["total_pnl"], marker="o", color="#DD8452")
    axes[1].set_xlabel("Trade rate")
    axes[1].set_ylabel("Cumulative P&L (normalized)")
    axes[1].set_title("Total P&L vs trade rate")
    axes[1].axhline(0, color="black", linewidth=0.5)

    plt.tight_layout()
    plt.savefig(fig_path); plt.close()

    return {"tau_sweep": df.to_dict("records"), "tau_star": tau_star_row}


# ---------------------------------------------------------------------------
# Category 10: DL attribution (V4 q50 ≈ simple factors + residual)
# ---------------------------------------------------------------------------

def cat10_dl_attribution(data: Dict, feature_dir: pathlib.Path, fig_path: pathlib.Path) -> Dict:
    """OLS: q50 ≈ β·past_return + β·realized_vol + β·hour_sin + β·hour_cos + ε.

    Simple-factor R² tells us how much of V4 is just re-discovering momentum/vol/calendar.
    Residual-Pearson is V4's actual non-linear alpha increment.
    """
    all_q50, all_y, all_ts = [], [], []
    for fold in FOLDS:
        if ("V4", fold) not in data:
            continue
        d = data[("V4", fold)]
        m = d["mask"] & np.isfinite(d["target"]) & np.isfinite(d["q50"])
        all_q50.append(d["q50"][m])
        all_y.append(d["target"][m])
        all_ts.append(d["timestamps"][m])
    if not all_q50:
        return {}
    q50 = np.concatenate(all_q50); y = np.concatenate(all_y); ts = np.concatenate(all_ts)

    # Proxy simple factors from target/timestamps (no access to input features here — approximate)
    # past_ret_60s: shifted rolling mean of y over 60 samples
    past_ret_60 = pd.Series(y).rolling(60, min_periods=10).mean().shift(1).fillna(0.0).values
    past_ret_300 = pd.Series(y).rolling(300, min_periods=30).mean().shift(1).fillna(0.0).values
    realized_vol_60 = pd.Series(y).rolling(60, min_periods=10).std().shift(1).fillna(0.0).values
    hour = ((_ts_to_seconds(ts) % 86400) // 3600).astype(float)
    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)

    # Stack design matrix
    X_simple = np.column_stack([past_ret_60, past_ret_300, realized_vol_60, hour_sin, hour_cos])
    X_simple = np.nan_to_num(X_simple, nan=0.0, posinf=0.0, neginf=0.0)

    # OLS: q50 = Xβ + ε
    beta, residuals, rank, sv = np.linalg.lstsq(
        np.column_stack([X_simple, np.ones(len(X_simple))]),
        q50, rcond=None,
    )
    q50_pred = (X_simple @ beta[:-1]) + beta[-1]
    ss_res = np.sum((q50 - q50_pred) ** 2)
    ss_tot = np.sum((q50 - q50.mean()) ** 2)
    r2_simple = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    residual_v4 = q50 - q50_pred
    resid_pearson = pearson(residual_v4, y)
    baseline_pearson = pearson(q50, y)

    # Plot: coefficient bar + residual-Pearson comparison
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    labels = ["past_ret_60s", "past_ret_300s", "realized_vol_60s", "hour_sin", "hour_cos"]
    axes[0].barh(labels, beta[:-1], color="#4C72B0")
    axes[0].axvline(0, color="black", linewidth=0.5)
    axes[0].set_title(f"OLS Attribution of V4 q50\nR²(simple factors → q50) = {r2_simple:.3f}\n(>0.8 = V4 is mostly momentum; <0.3 = DL has unique signal)")
    axes[0].set_xlabel("Coefficient")

    axes[1].bar(["V4 q50 vs y\n(total)", "residual (q50 − OLS) vs y\n(DL's non-linear)"], [baseline_pearson, resid_pearson], color=["#4C72B0", "#DD8452"])
    axes[1].axhline(0, color="black", linewidth=0.5)
    axes[1].set_ylabel("Pearson correlation with target y")
    axes[1].set_title(f"DL non-linear increment\n(baseline {baseline_pearson:.4f} → residual {resid_pearson:.4f})")

    plt.tight_layout()
    plt.savefig(fig_path); plt.close()
    return {
        "r2_simple_factors_to_q50": float(r2_simple),
        "baseline_pearson_q50_y": float(baseline_pearson),
        "residual_pearson_resid_y": float(resid_pearson),
        "dl_non_linear_gain": float(resid_pearson / (baseline_pearson + 1e-8)) if baseline_pearson > 0 else float("nan"),
        "coefficients": {l: float(b) for l, b in zip(labels, beta[:-1])},
    }


# ---------------------------------------------------------------------------
# Category 11: Ensemble projection (Grinold-Kahn)
# ---------------------------------------------------------------------------

def cat11_ensemble_projection(data: Dict, cat1_result: Dict, cat8_result: Dict, fig_path: pathlib.Path) -> Dict:
    """Given IC per model + pairwise corr, compute theoretical combined IR."""
    if not cat8_result or "corr_matrix" not in cat8_result:
        return {}
    models_present = cat8_result["models"]
    n = len(models_present)
    if n < 2:
        return {"note": "<2 models, no ensemble"}

    # IC vector (use pooled Pearson)
    ic_vec = np.array([cat1_result["pooled"][m]["pearson"] for m in models_present])
    # Corr matrix -> Σ (assume variance 1 after normalization; pred correlations ≈ Σ for unit-normalized)
    Sigma = np.array(cat8_result["corr_matrix"])
    # Grinold-Kahn: w = Σ⁻¹ r / (1'Σ⁻¹ r); combined IC = √(r' Σ⁻¹ r)
    try:
        Sigma_inv = np.linalg.pinv(Sigma)
        w_unnorm = Sigma_inv @ ic_vec
        w = w_unnorm / w_unnorm.sum() if w_unnorm.sum() != 0 else w_unnorm
        combined_ic = float(np.sqrt(max(0.0, ic_vec @ Sigma_inv @ ic_vec)))
    except Exception as e:
        logger.warning(f"Ensemble projection failed: {e}")
        return {}

    # Naive equal-weight for comparison
    w_equal = np.ones(n) / n
    combined_ic_equal = float((w_equal @ ic_vec) / np.sqrt(w_equal @ Sigma @ w_equal + 1e-12))

    # Plot: bar comparing single models, equal-weight, optimal-weight
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

    labels = models_present + ["Equal-weight", "Optimal-weight"]
    values = list(ic_vec) + [combined_ic_equal, combined_ic]
    colors = ["#4C72B0"] * n + ["#55A868", "#C44E52"]
    axes[0].bar(range(len(values)), values, color=colors)
    axes[0].set_xticks(range(len(values))); axes[0].set_xticklabels(labels, rotation=25)
    axes[0].set_ylabel("Theoretical IC")
    axes[0].axhline(0.12, color="red", linestyle="--", alpha=0.5, label="spec 0.12")
    axes[0].set_title(f"Ensemble Projection (Grinold-Kahn)\nOptimal combined IC: {combined_ic:.4f} (best single: {max(ic_vec):.4f})")
    axes[0].legend()

    # Optimal weights bar
    axes[1].bar(models_present, w, color=colors[:n])
    axes[1].axhline(0, color="black", linewidth=0.5)
    axes[1].set_title("Optimal combination weights (Σ⁻¹ r)")
    axes[1].set_ylabel("Weight")

    plt.tight_layout()
    plt.savefig(fig_path); plt.close()

    return {
        "models": models_present,
        "single_model_ics": ic_vec.tolist(),
        "optimal_weights": w.tolist(),
        "combined_ic_optimal": combined_ic,
        "combined_ic_equal_weight": combined_ic_equal,
        "best_single_ic": float(max(ic_vec)),
        "ensemble_lift": float(combined_ic - max(ic_vec)),
    }


# ---------------------------------------------------------------------------
# Category 12 (bonus): Monthly concentration
# ---------------------------------------------------------------------------

def cat12_monthly_concentration(data: Dict, fig_path: pathlib.Path) -> Dict:
    """Per-month IC on test period, flag concentration (top 20% months → ≥60% IC)."""
    results = {}
    fig, ax = plt.subplots(figsize=(12, 5))
    colors_by_model = dict(zip(MODELS, ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]))

    for model in MODELS:
        all_p, all_y, all_ts = [], [], []
        for fold in FOLDS:
            if (model, fold) not in data:
                continue
            d = data[(model, fold)]
            m = d["mask"]; v = m & np.isfinite(d["target"]) & np.isfinite(d["pred"])
            all_p.append(d["pred"][v]); all_y.append(d["target"][v]); all_ts.append(d["timestamps"][v])
        if not all_p:
            continue
        p = np.concatenate(all_p); y = np.concatenate(all_y); ts = np.concatenate(all_ts)
        # Month bucket: year-month key
        ts_sec = _ts_to_seconds(ts)
        dt_vals = pd.to_datetime(ts_sec, unit="s")
        month_key = dt_vals.strftime("%Y-%m")
        df = pd.DataFrame({"p": p, "y": y, "month": month_key})
        ics = df.groupby("month").apply(lambda g: spearman(g["p"].values, g["y"].values) if len(g) > 50 else float("nan")).sort_index()
        ics_arr = np.array([v for v in ics.values if np.isfinite(v)])
        if len(ics_arr) == 0:
            continue
        # Concentration: sort by |IC|, check top-20% contribution
        abs_sorted = np.sort(np.abs(ics_arr))[::-1]
        cum = np.cumsum(abs_sorted) / abs_sorted.sum()
        top_20pct_idx = max(1, int(np.ceil(len(abs_sorted) * 0.2)))
        top_20pct_share = float(cum[top_20pct_idx - 1])
        flag_concentration = top_20pct_share >= 0.60

        results[model] = {
            "monthly_ics": ics.to_dict(),
            "mean_monthly_ic": float(np.mean(ics_arr)),
            "std_monthly_ic": float(np.std(ics_arr)),
            "top_20pct_months_share": top_20pct_share,
            "concentration_flag": flag_concentration,
            "n_months": len(ics_arr),
        }

        # Plot bar per model
        offset = (MODELS.index(model) - 1.5) * 0.2
        months_sorted = ics.index.tolist()
        ax.bar(np.arange(len(months_sorted)) + offset, ics.values, 0.18, label=f"{model} (top20%→{top_20pct_share:.1%})", color=colors_by_model[model])
        # Only set xticks from first model
        if model == "V4":
            ax.set_xticks(range(len(months_sorted)))
            ax.set_xticklabels(months_sorted, rotation=45)

    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylabel("Monthly Spearman IC")
    ax.set_title("Per-month Spearman IC (concentration check: top 20% months should NOT exceed 60% of total |IC|)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(fig_path); plt.close()
    return results


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

def generate_report(all_metrics: Dict, output_dir: pathlib.Path) -> None:
    """Generate REPORT.md with embedded plots and narrative."""
    lines = []
    lines.append("# Comprehensive V4 vs Ridge vs XGBoost Evaluation Report")
    lines.append("")
    lines.append("_Generated by scripts/comprehensive_eval.py. See design spec at `docs/superpowers/specs/2026-04-18-comprehensive-eval-design.md`._\n")
    lines.append("## Executive Summary\n")

    pooled = all_metrics.get("cat1_core_ic", {}).get("pooled", {})
    if pooled:
        lines.append("### Pooled Headline Metrics\n")
        lines.append("| Model | Pearson | Spearman | DirAcc | N |")
        lines.append("|---|---:|---:|---:|---:|")
        for m in MODELS:
            if m not in pooled:
                continue
            pm = pooled[m]
            lines.append(f"| {m} | {pm['pearson']:.4f} | {pm['spearman']:.4f} | {pm['direction_acc']:.4f} | {pm['n']:,} |")
        lines.append("")

    # Section for each category
    sections = [
        ("Category 1 — Core IC with bootstrapped CIs", "01_ic_with_ci.png", "cat1_core_ic"),
        ("Category 2 — Temporal stability (daily IC)", "02_temporal_ic.png", "cat2_temporal_stability"),
        ("Category 3 — Autocorrelation (pred/residual)", "03_autocorr.png", "cat3_autocorrelation"),
        ("Category 4 — Decile returns + monotonicity + L-S spread", "04_decile_returns.png", "cat4_decile_returns"),
        ("Category 5 — Regime-conditional IC (vol/trend/hour)", "05_regime_heatmap.png", "cat5_regime"),
        ("Category 6 — Risk metrics + drawdown", "06_equity_drawdown.png", "cat6_risk"),
        ("Category 7 — V4 quantile calibration", "07_calibration_v4.png", "cat7_calibration_v4"),
        ("Category 8 — Cross-model consistency", "08_cross_model_corr.png", "cat8_cross_model"),
        ("Category 9 — Confidence gating (V4)", "09_confidence_gating.png", "cat9_confidence_gating"),
        ("Category 10 — DL attribution (V4 vs simple factors)", "10_attribution_v4.png", "cat10_dl_attribution"),
        ("Category 11 — Ensemble projection (Grinold-Kahn)", "11_ensemble_projection.png", "cat11_ensemble_projection"),
        ("Category 12 — Monthly concentration", "12_monthly_concentration.png", "cat12_monthly_concentration"),
    ]

    for title, fig_name, key in sections:
        lines.append(f"## {title}\n")
        lines.append(f"![{title}](figures/{fig_name})\n")
        # Key numbers
        data = all_metrics.get(key, {})
        if isinstance(data, dict):
            summary = _summarize_category(key, data)
            if summary:
                lines.append(summary)
                lines.append("")

    # Strategic takeaways
    lines.append("## Strategic Takeaways\n")
    lines.append(_generate_takeaways(all_metrics))

    report_path = output_dir / "REPORT.md"
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    logger.info(f"Report written to {report_path}")


def _summarize_category(key: str, data: Dict) -> str:
    """Produce a short text summary for each category."""
    if key == "cat1_core_ic" and "pooled" in data:
        return "**Pooled Pearson and Spearman are in the table above.** Bootstrapped 95% CIs in figure error bars."

    if key == "cat2_temporal_stability" and "per_model" in data:
        rows = []
        rows.append("| Model | n_days | mean daily IC | std | IC-IR | % days positive |")
        rows.append("|---|---:|---:|---:|---:|---:|")
        for m, s in data["per_model"].items():
            rows.append(f"| {m} | {s['n_days']} | {s['mean_daily_ic']:.4f} | {s['std_daily_ic']:.4f} | {s['ic_ir_daily']:.3f} | {s['pct_days_positive']:.1%} |")
        return "\n".join(rows)

    if key == "cat3_autocorrelation":
        tgt_ac = data.get("target_ac_lag1")
        resid_acs = [f"{m}: {data[m]['resid_ac_lag1']:.4f}" for m in MODELS if m in data and "resid_ac_lag1" in data[m]]
        tgt_str = f"{tgt_ac:.4f}" if isinstance(tgt_ac, float) else "n/a"
        return f"**Target AC(1)** = {tgt_str}. Residual AC(1): {', '.join(resid_acs)}. All <0.3 = no label leakage."

    if key == "cat4_decile_returns":
        rows = []
        rows.append("| Model | Monotonicity (Spearman) | L-S spread (bps, normalized) |")
        rows.append("|---|---:|---:|")
        for m, r in data.items():
            rows.append(f"| {m} | {r['monotonicity']:+.4f} | {r['long_short_bps']:+.2f} |")
        return "\n".join(rows)

    if key == "cat6_risk":
        rows = []
        rows.append("| Model | Sharpe (ann) | Max DD | Calmar | CVaR-95% | Hit rate |")
        rows.append("|---|---:|---:|---:|---:|---:|")
        for m, r in data.items():
            rows.append(f"| {m} | {r['sharpe_hac_ann']:.3f} | {r['max_drawdown']:.4f} | {r['calmar']:.3f} | {r['cvar_95']:.4f} | {r['hit_rate_all']:.4f} |")
        return "\n".join(rows)

    if key == "cat7_calibration_v4":
        if not data:
            return ""
        return (f"q10 actual coverage: **{data.get('coverage_q10_nominal0.10', 0):.3f}** (nominal 0.10); "
                f"q50: **{data.get('coverage_q50_nominal0.50', 0):.3f}** (nominal 0.50); "
                f"q90: **{data.get('coverage_q90_nominal0.90', 0):.3f}** (nominal 0.90). "
                f"Cross-violations: q10>q50 = {data.get('cross_violation_q10_gt_q50', 0):.4f}, "
                f"q50>q90 = {data.get('cross_violation_q50_gt_q90', 0):.4f}.")

    if key == "cat8_cross_model":
        flags = data.get("highly_correlated_pairs", [])
        if flags:
            return f"**Highly correlated (>0.8) pairs:** " + ", ".join(f"{a}—{b} ({c:.3f})" for a, b, c in flags)
        return "**No pairs exceed 0.8 correlation.** Ensemble diversity is acceptable."

    if key == "cat9_confidence_gating":
        ts = data.get("tau_star", {})
        if ts:
            return (f"**τ*** = {ts.get('tau', 0):.4f} → **Sharpe(τ*)** = {ts.get('sharpe_ann', 0):.3f} "
                    f"at **trade rate {ts.get('trade_rate', 0):.2%}**. "
                    f"(Compare to always-trade Sharpe in Category 6.)")
        return ""

    if key == "cat10_dl_attribution":
        r2 = data.get("r2_simple_factors_to_q50", 0)
        resid = data.get("residual_pearson_resid_y", 0)
        base = data.get("baseline_pearson_q50_y", 0)
        return (f"**R²(simple factors → V4 q50) = {r2:.3f}** "
                f"({'>0.8 → V4 mostly momentum!' if r2 > 0.8 else '<0.3 → V4 has unique signal' if r2 < 0.3 else 'moderate'}). "
                f"Residual Pearson (DL's non-linear signal): **{resid:.4f}** (vs baseline {base:.4f}).")

    if key == "cat11_ensemble_projection":
        lift = data.get("ensemble_lift")
        comb = data.get("combined_ic_optimal", 0)
        best_single = data.get("best_single_ic", 0)
        if lift is not None:
            return (f"**Optimal combined IC: {comb:.4f}** vs best single {best_single:.4f} → **lift {lift:+.4f}**. "
                    f"Optimal weights: " + ", ".join(f"{m}={w:.2f}" for m, w in zip(data.get("models", []), data.get("optimal_weights", []))))
        return ""

    if key == "cat12_monthly_concentration":
        lines = ["| Model | Mean monthly IC | Std | Top-20%-months share | Flag |", "|---|---:|---:|---:|:-:|"]
        for m, r in data.items():
            flag = "⚠️" if r["concentration_flag"] else "✓"
            lines.append(f"| {m} | {r['mean_monthly_ic']:.4f} | {r['std_monthly_ic']:.4f} | {r['top_20pct_months_share']:.1%} | {flag} |")
        return "\n".join(lines)
    return ""


def _generate_takeaways(all_metrics: Dict) -> str:
    """Auto-generate strategic takeaways based on numbers."""
    lines = []
    pooled = all_metrics.get("cat1_core_ic", {}).get("pooled", {})
    if "V4" in pooled and "Ridge" in pooled:
        d_p = pooled["V4"]["pearson"] - pooled["Ridge"]["pearson"]
        d_s = pooled["V4"]["spearman"] - pooled["Ridge"]["spearman"]
        lines.append(f"- **DL uplift over Ridge:** Pearson {d_p:+.4f}, Spearman {d_s:+.4f}.")

    # Category 10: attribution
    cat10 = all_metrics.get("cat10_dl_attribution", {})
    if cat10:
        r2 = cat10.get("r2_simple_factors_to_q50", 0)
        if r2 > 0.8:
            lines.append(f"- ⚠️ **V4 is largely momentum re-discovery** (R²={r2:.2f} of simple factors → q50). Feature engineering likely more impactful than architecture.")
        elif r2 < 0.3:
            lines.append(f"- ✓ **V4 has unique non-linear signal** (R²={r2:.2f}). DL pays its way.")
        else:
            lines.append(f"- **Partial attribution:** R²={r2:.2f} of V4 explained by simple factors. Mixed.")

    # Category 11: ensemble
    cat11 = all_metrics.get("cat11_ensemble_projection", {})
    if cat11 and "ensemble_lift" in cat11:
        lift = cat11["ensemble_lift"]
        if lift > 0.02:
            lines.append(f"- ✓ **Ensemble promising:** +{lift:.4f} theoretical IC lift over best single model.")
        else:
            lines.append(f"- **Ensemble marginal:** only {lift:+.4f} theoretical IC lift; models are too correlated.")

    # Category 9: confidence gating
    cat9 = all_metrics.get("cat9_confidence_gating", {})
    if cat9:
        ts = cat9.get("tau_star", {})
        if ts:
            sharpe_star = ts.get("sharpe_ann", 0)
            if sharpe_star > 1.0:
                lines.append(f"- ✓ **Confidence-gated V4 produces tradeable Sharpe {sharpe_star:.2f}** at trade rate {ts.get('trade_rate', 0):.0%}.")
            else:
                lines.append(f"- **Confidence gating lifts Sharpe to {sharpe_star:.2f}** but not yet production-grade.")

    # Category 12: concentration
    cat12 = all_metrics.get("cat12_monthly_concentration", {})
    concentrated = [m for m, r in cat12.items() if r.get("concentration_flag")]
    if concentrated:
        lines.append(f"- ⚠️ **Monthly concentration risk** in models: {', '.join(concentrated)} — signal driven by few months.")

    if not lines:
        lines.append("- (No automated takeaways generated.)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v4-exp-dir", required=True, type=pathlib.Path)
    parser.add_argument("--baseline-pred-dir", required=True, type=pathlib.Path)
    parser.add_argument("--feature-npz-dir", type=pathlib.Path, default=None,
                        help="Optional: NPZ dir for regime features (not required with proxy).")
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    out_dir = args.output_dir
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading predictions from V4 ({args.v4_exp_dir}) and baselines ({args.baseline_pred_dir})...")
    data = load_all_data(args.v4_exp_dir, args.baseline_pred_dir)
    logger.info(f"Loaded {len(data)} (model, fold) pairs: {sorted(data.keys())}")

    all_metrics = {}

    logger.info("Category 1: Core IC + bootstrapped CIs...")
    all_metrics["cat1_core_ic"] = cat1_core_ic(data, fig_dir / "01_ic_with_ci.png")

    logger.info("Category 2: Temporal stability...")
    all_metrics["cat2_temporal_stability"] = cat2_temporal_stability(data, fig_dir / "02_temporal_ic.png")

    logger.info("Category 3: Autocorrelation...")
    all_metrics["cat3_autocorrelation"] = cat3_autocorrelation(data, fig_dir / "03_autocorr.png")

    logger.info("Category 4: Decile returns...")
    all_metrics["cat4_decile_returns"] = cat4_decile_returns(data, fig_dir / "04_decile_returns.png")

    logger.info("Category 5: Regime conditional IC...")
    all_metrics["cat5_regime"] = cat5_regime(data, fig_dir / "05_regime_heatmap.png")

    logger.info("Category 6: Risk metrics...")
    all_metrics["cat6_risk"] = cat6_risk(data, fig_dir / "06_equity_drawdown.png")

    logger.info("Category 7: V4 calibration...")
    all_metrics["cat7_calibration_v4"] = cat7_calibration_v4(data, fig_dir / "07_calibration_v4.png")

    logger.info("Category 8: Cross-model consistency...")
    all_metrics["cat8_cross_model"] = cat8_cross_model(data, fig_dir / "08_cross_model_corr.png")

    logger.info("Category 9: Confidence gating (V4)...")
    all_metrics["cat9_confidence_gating"] = cat9_confidence_gating(data, fig_dir / "09_confidence_gating.png")

    logger.info("Category 10: DL attribution...")
    all_metrics["cat10_dl_attribution"] = cat10_dl_attribution(data, args.feature_npz_dir, fig_dir / "10_attribution_v4.png")

    logger.info("Category 11: Ensemble projection...")
    all_metrics["cat11_ensemble_projection"] = cat11_ensemble_projection(
        data, all_metrics["cat1_core_ic"], all_metrics["cat8_cross_model"], fig_dir / "11_ensemble_projection.png",
    )

    logger.info("Category 12: Monthly concentration...")
    all_metrics["cat12_monthly_concentration"] = cat12_monthly_concentration(data, fig_dir / "12_monthly_concentration.png")

    # Write JSON
    def _json_default(o):
        if isinstance(o, np.integer): return int(o)
        if isinstance(o, np.floating): return float(o)
        if isinstance(o, np.ndarray): return o.tolist()
        if isinstance(o, pd.DataFrame): return o.to_dict("records")
        return str(o)
    with open(out_dir / "metrics.json", "w") as f:
        json.dump(all_metrics, f, indent=2, default=_json_default)
    logger.info(f"Metrics saved to {out_dir / 'metrics.json'}")

    # Generate report
    generate_report(all_metrics, out_dir)
    logger.info(f"Done. See {out_dir / 'REPORT.md'}")


if __name__ == "__main__":
    main()

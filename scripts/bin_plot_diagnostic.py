#!/usr/bin/env python3
"""Bin plot diagnostic: E[ŷ | y in bin_k] vs y bin center.

Tests model's magnitude calibration in reverse direction:
  - X axis: y binned (actual return deciles / quantiles)
  - Y axis: mean of ŷ within each y bin
  - Expected for good model: monotonic line passing through origin with slope ~IC

Generates this plot for V4 y_180 (3 folds pooled) and saves to
experiments/eval_comprehensive/figures/21_bin_plot_yhat_given_y.png.
"""
from __future__ import annotations

import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr

EXP_DIR = pathlib.Path("experiments/v4_noattn_700d")
XGB_DIR = pathlib.Path("experiments/baselines_v4_matched_preds")
OUT_DIR = pathlib.Path("experiments/eval_comprehensive/figures")


def load_v4_pooled():
    """Load V4 q50 + targets pooled across 3 folds."""
    all_p, all_y, all_m = [], [], []
    for f in range(3):
        d = np.load(EXP_DIR / f"fold_{f}/test_preds.npz")
        p = d["predictions"][:, 1]  # q50
        y = d["targets"]
        m = d["mask"].astype(bool)
        all_p.append(p[m]); all_y.append(y[m])
    return np.concatenate(all_p), np.concatenate(all_y)


def load_xgb_pooled():
    all_p, all_y = [], []
    for f in range(3):
        d = np.load(XGB_DIR / f"fold_{f}_XGBoost_preds.npz")
        p = d["predictions"]
        y = d["targets"]
        m = d["mask"].astype(bool)
        all_p.append(p[m]); all_y.append(y[m])
    return np.concatenate(all_p), np.concatenate(all_y)


def compute_bin_stats(y: np.ndarray, yhat: np.ndarray, n_bins: int = 10, method: str = "quantile"):
    """Bin y into n_bins, compute mean ŷ per bin.

    method: 'quantile' (equal count) or 'equal_width'
    """
    if method == "quantile":
        edges = np.quantile(y, np.linspace(0, 1, n_bins + 1))
        edges[0] = -np.inf; edges[-1] = np.inf  # extend edges
    else:
        edges = np.linspace(np.percentile(y, 1), np.percentile(y, 99), n_bins + 1)
        edges[0] = -np.inf; edges[-1] = np.inf

    bin_centers = []
    bin_mean_yhat = []
    bin_se_yhat = []
    bin_n = []
    for i in range(n_bins):
        sel = (y >= edges[i]) & (y < edges[i + 1])
        if sel.sum() < 10:
            continue
        y_sel = y[sel]
        yhat_sel = yhat[sel]
        bin_centers.append(float(y_sel.mean()))
        bin_mean_yhat.append(float(yhat_sel.mean()))
        bin_se_yhat.append(float(yhat_sel.std() / np.sqrt(sel.sum())))
        bin_n.append(int(sel.sum()))
    return (np.array(bin_centers), np.array(bin_mean_yhat),
            np.array(bin_se_yhat), np.array(bin_n))


def make_plot(datasets, out_path: pathlib.Path, n_bins: int = 10):
    """datasets: list of (label, yhat, y) tuples."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    colors = ["#4C72B0", "#DD8452", "#55A868"]

    # ---- Left: quantile bins (equal count) ----
    ax = axes[0]
    for (label, yhat, y), c in zip(datasets, colors):
        centers, means, ses, ns = compute_bin_stats(y, yhat, n_bins, "quantile")
        ax.errorbar(centers, means, yerr=1.96 * ses, marker="o", markersize=7,
                     capsize=4, linewidth=1.5, label=label, color=c)

    # Bin centers tell us the useful range (percentile 5-95 of y)
    # Identity line only drawn in this viewable range
    xlim = max(abs(min(d[2].min() for d in datasets)), abs(max(d[2].max() for d in datasets)))
    # Use 99th percentile of y for plot range — ignore outliers
    xlim = 2.5  # z-score viewable range
    ax.plot([-xlim, xlim], [-xlim, xlim], "k:", alpha=0.25, label="identity ŷ=y", linewidth=1)
    ax.set_xlim(-xlim, xlim)
    # Auto-scale y on actual bin values (what matters)
    all_means = [compute_bin_stats(d[2], d[1], n_bins, "quantile")[1] for d in datasets]
    ymax_bins = max(max(np.abs(m)) for m in all_means) * 1.8
    ax.set_ylim(-ymax_bins, ymax_bins)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axvline(0, color="black", linewidth=0.5)

    ax.set_xlabel("y bin center (actual return, z-score)")
    ax.set_ylabel("E[ŷ | y in bin] (95% CI)")
    ax.set_title(f"Bin Plot: Conditional Mean of Predictions\n(quantile bins, n={n_bins})")
    ax.legend()

    # ---- Right: same but with fit line ----
    ax = axes[1]
    for (label, yhat, y), c in zip(datasets, colors):
        centers, means, ses, ns = compute_bin_stats(y, yhat, n_bins, "quantile")
        ax.errorbar(centers, means, yerr=1.96 * ses, marker="o", markersize=7,
                     capsize=4, linewidth=0, label=f"{label} (raw bins)", color=c, alpha=0.4)
        # Ridge-style slope fit: β = Cov(ŷ,y) / Var(y)
        beta = np.cov(yhat, y)[0, 1] / np.var(y)
        intercept = np.mean(yhat) - beta * np.mean(y)
        x_line = np.linspace(centers.min(), centers.max(), 100)
        y_line = beta * x_line + intercept
        pearson = pearsonr(yhat, y)[0]
        ax.plot(x_line, y_line, "-", color=c,
                 label=f"{label}: slope={beta:.4f}, Pearson={pearson:.4f}", linewidth=2)

    xlim2 = 2.5
    ax.plot([-xlim2, xlim2], [-xlim2, xlim2], "k:", alpha=0.25, label="identity", linewidth=1)
    ax.set_xlim(-xlim2, xlim2)
    ax.set_ylim(-ymax_bins, ymax_bins)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axvline(0, color="black", linewidth=0.5)
    ax.set_xlabel("y bin center (actual return, z-score)")
    ax.set_ylabel("E[ŷ | y in bin]")
    ax.set_title("With OLS slope β = Cov(ŷ,y)/Var(y) ≈ Pearson IC")
    ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(out_path); plt.close()
    print(f"✓ Saved: {out_path}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading V4 y_180 predictions...")
    v4_p, v4_y = load_v4_pooled()
    print(f"  V4: {len(v4_p):,} samples, Pearson={pearsonr(v4_p, v4_y)[0]:.4f}")

    print("Loading XGBoost y_180 predictions...")
    xgb_p, xgb_y = load_xgb_pooled()
    print(f"  XGB: {len(xgb_p):,} samples, Pearson={pearsonr(xgb_p, xgb_y)[0]:.4f}")

    # Note: V4 and XGB use different target normalizations (V4 clips at ±5)
    # We plot each on its own normalized scale. Both are z-scored.

    # Standardize ŷ within each model for visual comparison
    def standardize(x):
        return (x - x.mean()) / (x.std() + 1e-12)

    v4_p_z = standardize(v4_p)
    v4_y_z = standardize(v4_y)
    xgb_p_z = standardize(xgb_p)
    xgb_y_z = standardize(xgb_y)

    datasets = [
        ("V4 y_180 (q50)", v4_p_z, v4_y_z),
        ("XGBoost y_180", xgb_p_z, xgb_y_z),
    ]

    out = OUT_DIR / "21_bin_plot_yhat_given_y.png"
    make_plot(datasets, out, n_bins=10)

    # Print bin table for V4
    print("\nV4 y_180 — per-quantile-bin statistics:")
    centers, means, ses, ns = compute_bin_stats(v4_y_z, v4_p_z, 10, "quantile")
    print(f"{'bin':>4} | {'y center':>10} | {'E[ŷ|y]':>10} | {'95% CI':>18} | {'N':>8}")
    for i, (c, m, se, n) in enumerate(zip(centers, means, ses, ns)):
        lo, hi = m - 1.96*se, m + 1.96*se
        print(f"{i+1:>4} | {c:>+10.4f} | {m:>+10.4f} | [{lo:>+6.4f}, {hi:>+6.4f}] | {n:>8,}")

    # Check monotonicity
    mono_corr = spearmanr(np.arange(len(centers)), means)[0]
    through_origin = abs(means[len(means)//2]) < 0.05  # middle bin close to 0
    print(f"\nMonotonicity (Spearman bin_idx vs E[ŷ|y]): {mono_corr:+.4f}")
    print(f"Middle bin E[ŷ|y] (proxy for origin): {means[len(means)//2]:+.4f}")
    print(f"Passes through origin (middle bin < 0.05): {'✓' if through_origin else '✗'}")


if __name__ == "__main__":
    main()

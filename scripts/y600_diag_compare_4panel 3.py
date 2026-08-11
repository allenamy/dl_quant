"""Generate 2x2 side-by-side bin-plot comparison of 4 key configs.

Configs compared:
  - seed42_SWA (proposed winner)
  - 3seed_median_EMA (current production)
  - 3seed_mean_SWA (mid-option ensemble)
  - seed42_EMA (top-bin maximalist)
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
import pandas as pd

NUM_FOLDS = 3
NUM_BINS = 10
GROUND_TRUTH_CSV = Path("exports/y600_baseline_plus_BEST_3seed_median.csv")
SEED_DIRS = {
    42: Path("experiments/y600_push/baseline_plus"),
    7: Path("experiments/y600_baseline_seed7"),
    13: Path("experiments/y600_baseline_seed13"),
}
CKPT_TO_FILE = {"BEST": "test_preds.npz", "EMA": "ema_test_preds.npz", "SWA": "swa_test_preds.npz"}


def load_pred_lr(seed, fold, ckpt):
    d = np.load(SEED_DIRS[seed] / f"fold_{fold}" / CKPT_TO_FILE[ckpt])
    return d["predictions"][:, 1].astype(np.float64) * float(d["y_sigma"])


def get_pred_lr_for_config(label):
    """Returns concatenated pred_lr across folds (after dense filter applied externally)."""
    df_csv = pd.read_csv(GROUND_TRUTH_CSV)
    pred_pieces = []
    y_pieces = []
    m_pieces = []
    for f in range(NUM_FOLDS):
        sub = df_csv[df_csv["fold"] == f]
        y = sub["y_true_logret"].values
        m = sub["mask"].astype(bool).values
        if label == "seed42_SWA":
            p = load_pred_lr(42, f, "SWA")
        elif label == "seed42_EMA":
            p = load_pred_lr(42, f, "EMA")
        elif label == "3seed_median_EMA":
            stack = np.stack([load_pred_lr(s, f, "EMA") for s in [7, 13, 42]], axis=0)
            p = np.median(stack, axis=0)
        elif label == "3seed_mean_SWA":
            stack = np.stack([load_pred_lr(s, f, "SWA") for s in [7, 13, 42]], axis=0)
            p = np.mean(stack, axis=0)
        else:
            raise ValueError(label)
        pred_pieces.append(p)
        y_pieces.append(y)
        m_pieces.append(m)
    return (np.concatenate(y_pieces), np.concatenate(pred_pieces), np.concatenate(m_pieces))


def compute_bin(y, yp, mask):
    valid = mask & np.isfinite(y) & np.isfinite(yp)
    y, yp = y[valid], yp[valid]
    edges = np.quantile(y, np.linspace(0, 1, NUM_BINS + 1))
    edges[0] -= 1e-12
    edges[-1] += 1e-12
    idx = np.clip(np.searchsorted(edges, y, side="right") - 1, 0, NUM_BINS - 1)
    bin_y = np.array([y[idx == i].mean() for i in range(NUM_BINS)]) * 1e4
    bin_yp = np.array([yp[idx == i].mean() for i in range(NUM_BINS)]) * 1e4
    P = float(np.corrcoef(y, yp)[0, 1])
    S = float(spearmanr(y, yp).correlation)
    cov = np.mean((y - y.mean()) * (yp - yp.mean()))
    var_yp = np.var(yp)
    beta = cov / var_yp if var_yp > 0 else float("nan")
    sigma_ratio = np.std(yp) / np.std(y)
    bs = float(spearmanr(bin_y, bin_yp).correlation)
    return bin_y, bin_yp, dict(P=P, S=S, beta=beta, sigma_ratio=sigma_ratio,
                                bin_S=bs, top_bin=bin_yp[-1], mean_yhat=yp.mean()*1e4)


configs = [
    ("seed42_SWA", "PROPOSED WINNER", "tab:green"),
    ("3seed_median_EMA", "CURRENT PRODUCTION", "tab:red"),
    ("3seed_mean_SWA", "ENSEMBLE UPGRADE", "tab:blue"),
    ("seed42_EMA", "TOP-BIN MAXIMALIST", "tab:purple"),
]

fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True, sharey=True)
axes = axes.ravel()

# Compute global lim
all_vals = []
for label, _, _ in configs:
    y, yp, m = get_pred_lr_for_config(label)
    bin_y, bin_yp, _ = compute_bin(y, yp, m)
    all_vals.extend(bin_y.tolist())
    all_vals.extend(bin_yp.tolist())
ylim = (-1.5 * abs(min(all_vals)), 1.5 * max(all_vals))
xlim = (min(all_vals) * 1.1, max(all_vals) * 1.1)

for ax, (label, role, color) in zip(axes, configs):
    y, yp, m = get_pred_lr_for_config(label)
    bin_y, bin_yp, mm = compute_bin(y, yp, m)
    ax.plot(bin_y, bin_yp, "o-", lw=2.2, ms=9, color=color)
    ax.axhline(0, color="gray", ls=":", lw=0.8)
    ax.axvline(0, color="gray", ls=":", lw=0.8)
    ax.plot([min(all_vals), max(all_vals)], [min(all_vals), max(all_vals)],
             "k--", lw=0.6, alpha=0.4, label="y=ŷ identity")
    # Annotate top-bin point
    ax.annotate(f"top: {bin_yp[-1]:+.3f}", xy=(bin_y[-1], bin_yp[-1]),
                xytext=(8, -8), textcoords="offset points", fontsize=9,
                color=color, fontweight="bold")
    title = f"{label}  [{role}]"
    subtitle = (f"P={mm['P']:+.4f}  S={mm['S']:+.4f}  β={mm['beta']:+.3f}  "
                f"σ_ŷ/σ_y={mm['sigma_ratio']:.3f}  bin-Sp={mm['bin_S']:+.3f}\n"
                f"mean(ŷ)={mm['mean_yhat']:+.3f}bps   top-bin ŷ={mm['top_bin']:+.3f}bps")
    ax.set_title(title + "\n" + subtitle, fontsize=10)
    ax.set_xlabel("y_true bin mean (bps)")
    ax.set_ylabel("ŷ bin mean (bps)")
    ax.grid(alpha=0.3)
    ax.set_ylim(-0.4, 0.3)
    ax.set_xlim(-30, 30)
    ax.legend(loc="upper left", fontsize=7)

fig.suptitle("y_600 bin-plot 4-panel comparison — top-bin ŷ should pass 0 for tradeable level signal",
             fontsize=12, fontweight="bold")
fig.tight_layout()
out_path = Path("exports/y600_diag_bin_plots/COMPARE_4panel.png")
fig.savefig(out_path, dpi=120)
plt.close(fig)
print(f"Wrote {out_path}")

"""Trading view bin-plot: bin by ŷ_predicted, compute E[y | ŷ_bin].

This answers the production-critical question:
  "If I trade on the top decile of model predictions, what's my expected return?"

If top-bin E[y | ŷ_bin] > 0 → buying top decile makes money (long signal works)
If bottom-bin E[y | ŷ_bin] < 0 → shorting bottom decile makes money (short signal works)

If both fail → model is anti-correlated (would lose money), but Pearson > 0 is impossible if so.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata, norm
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LinearRegression

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NUM_FOLDS = 3
NUM_BINS = 10
GROUND_TRUTH_CSV = Path("exports/y600_baseline_plus_BEST_3seed_median.csv")


def load_pred_lr(seed_dir, fold, ckpt_file):
    d = np.load(f"experiments/y600_push/{seed_dir}/fold_{fold}/{ckpt_file}")
    return d["predictions"][:, 1].astype(np.float64) * float(d["y_sigma"])


def get_gt():
    df = pd.read_csv(GROUND_TRUTH_CSV)
    return {f: df[df["fold"] == f].reset_index(drop=True) for f in range(NUM_FOLDS)}


def make_rank_blend_lr(swa_lr, ema_lr, sigma_lr):
    s_rank = norm.ppf(rankdata(swa_lr) / (len(swa_lr) + 1))
    e_rank = norm.ppf(rankdata(ema_lr) / (len(ema_lr) + 1))
    return 0.5 * (s_rank + e_rank) * sigma_lr


def trading_bin_metrics(y_lr, yp_lr, mask, n_bins=10):
    """Bin by yp, compute E[y | yp_bin]. The TRADING VIEW.

    Returns: bin_yp_means (x-axis), bin_y_means (y-axis), bin counts.
    """
    valid = mask.astype(bool) & np.isfinite(y_lr) & np.isfinite(yp_lr)
    y, yp = y_lr[valid], yp_lr[valid]
    edges = np.quantile(yp, np.linspace(0, 1, n_bins + 1))
    edges[0] -= 1e-12
    edges[-1] += 1e-12
    idx = np.clip(np.searchsorted(edges, yp, side="right") - 1, 0, n_bins - 1)
    bin_yp = np.array([yp[idx == i].mean() for i in range(n_bins)])
    bin_y = np.array([y[idx == i].mean() for i in range(n_bins)])
    counts = np.array([int((idx == i).sum()) for i in range(n_bins)])
    # Top/bottom bin signal-to-noise
    top_se = y[idx == n_bins - 1].std() / np.sqrt(max(1, counts[-1])) if counts[-1] > 0 else float("nan")
    bot_se = y[idx == 0].std() / np.sqrt(max(1, counts[0])) if counts[0] > 0 else float("nan")
    return bin_yp, bin_y, counts, {
        "top_y_mean_bps": bin_y[-1] * 1e4,
        "top_y_se_bps": top_se * 1e4,
        "top_y_t_stat": bin_y[-1] / max(top_se, 1e-12),
        "bottom_y_mean_bps": bin_y[0] * 1e4,
        "bottom_y_se_bps": bot_se * 1e4,
        "bottom_y_t_stat": bin_y[0] / max(bot_se, 1e-12),
    }


def main():
    gt = get_gt()
    fold_data = {}
    for f in range(NUM_FOLDS):
        sigma_f = float(np.load(f"experiments/y600_push/baseline_plus/fold_{f}/test_preds.npz")["y_sigma"])
        swa = load_pred_lr("baseline_plus", f, "swa_test_preds.npz")
        ema = load_pred_lr("baseline_plus", f, "ema_test_preds.npz")
        rb = make_rank_blend_lr(swa, ema, sigma_f)
        y = gt[f]["y_true_logret"].values.astype(np.float64)
        m = gt[f]["mask"].astype(bool).values
        fold_data[f] = {"swa": swa, "ema": ema, "rb": rb, "y": y, "m": m, "sigma": sigma_f}

    # Build configs to evaluate (all 3-fold pooled)
    configs = {}

    # 1. seed42_SWA raw (3-fold pool)
    swa_pool = np.concatenate([fold_data[f]["swa"] for f in range(NUM_FOLDS)])
    configs["seed42_SWA raw"] = swa_pool

    # 2. Walk-forward LINEAR cal rank-blend
    pieces = []
    for f in range(NUM_FOLDS):
        if f == 0:
            pieces.append(fold_data[0]["swa"])
        else:
            train_rb = np.concatenate([fold_data[k]["rb"][fold_data[k]["m"]] for k in range(f)])
            train_y = np.concatenate([fold_data[k]["y"][fold_data[k]["m"]] for k in range(f)])
            lin = LinearRegression().fit(train_rb.reshape(-1, 1), train_y)
            pieces.append(lin.predict(fold_data[f]["rb"].reshape(-1, 1)).flatten())
    configs["wf LINEAR cal rank-blend"] = np.concatenate(pieces)

    # 3. Walk-forward ISOTONIC cal rank-blend
    pieces = []
    for f in range(NUM_FOLDS):
        if f == 0:
            pieces.append(fold_data[0]["swa"])
        else:
            train_rb = np.concatenate([fold_data[k]["rb"][fold_data[k]["m"]] for k in range(f)])
            train_y = np.concatenate([fold_data[k]["y"][fold_data[k]["m"]] for k in range(f)])
            iso = IsotonicRegression(out_of_bounds="clip").fit(train_rb, train_y)
            pieces.append(iso.predict(fold_data[f]["rb"]))
    configs["wf ISOTONIC cal rank-blend"] = np.concatenate(pieces)

    # 4. 3-seed median EMA (CURRENT production)
    pieces = []
    seeds = [42, 7, 13]
    for f in range(NUM_FOLDS):
        stk = []
        for s in seeds:
            if s == 42:
                e = fold_data[f]["ema"]
            else:
                seed_dir = f"y600_baseline_seed{s}" if s != 42 else "baseline_plus"
                e = np.load(f"experiments/{seed_dir}/fold_{f}/ema_test_preds.npz")
                e = e["predictions"][:, 1].astype(np.float64) * float(e["y_sigma"])
            stk.append(e)
        pieces.append(np.median(np.stack(stk, axis=0), axis=0))
    configs["3seed median EMA (current)"] = np.concatenate(pieces)

    y_pool = np.concatenate([fold_data[f]["y"] for f in range(NUM_FOLDS)])
    m_pool = np.concatenate([fold_data[f]["m"] for f in range(NUM_FOLDS)])

    # Compute trading-view bin metrics
    print("=" * 130)
    print("TRADING VIEW: bin by ŷ_predicted, compute E[y_realized | ŷ_bin]")
    print("=" * 130)
    print(f"  → 'Top bin': samples where ŷ is in top 10% of predictions")
    print(f"  → 'Bottom bin': samples where ŷ is in bottom 10%")
    print(f"  → If top E[y] > 0 AND bottom E[y] < 0 → signal works directionally")
    print()
    print(f"{'config':<35} {'bot_E[y]_bps':>15} {'bot_t_stat':>12} {'top_E[y]_bps':>15} {'top_t_stat':>12} {'spread (top-bot) bps':>22}")
    print("-" * 130)
    fig, axes = plt.subplots(1, len(configs), figsize=(5 * len(configs), 4.5), sharey=True)
    if len(configs) == 1:
        axes = [axes]
    for ax, (label, yp_pool) in zip(axes, configs.items()):
        bin_yp, bin_y, counts, summary = trading_bin_metrics(y_pool, yp_pool, m_pool, n_bins=10)
        spread = (summary["top_y_mean_bps"] - summary["bottom_y_mean_bps"])
        print(f"{label:<35} {summary['bottom_y_mean_bps']:+15.4f} {summary['bottom_y_t_stat']:+12.2f} "
              f"{summary['top_y_mean_bps']:+15.4f} {summary['top_y_t_stat']:+12.2f} {spread:+22.4f}")

        # Plot
        ax.bar(range(10), bin_y * 1e4, color="tab:blue", alpha=0.7)
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xticks(range(10))
        ax.set_xticklabels([f"{i+1}" for i in range(10)], fontsize=8)
        ax.set_xlabel("ŷ decile (1=lowest pred, 10=highest)")
        ax.set_ylabel("E[y_realized] in decile (bps)")
        ax.set_title(f"{label}\nbot E[y]={summary['bottom_y_mean_bps']:+.3f}bps, "
                     f"top E[y]={summary['top_y_mean_bps']:+.3f}bps", fontsize=9)
        ax.grid(alpha=0.3)
    fig.suptitle("Trading view: E[y | ŷ_decile] — top decile should be POSITIVE (long signal works), bottom decile NEGATIVE (short signal works)",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    out_path = Path("exports/y600_diag_bin_plots/TRADING_VIEW_4panel.png")
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()

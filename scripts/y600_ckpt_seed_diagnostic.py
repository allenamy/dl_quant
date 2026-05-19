"""y_600 single-seed × ckpt diagnostic.

Compares 9 single-seed configs (3 seeds × 3 ckpts: BEST/EMA/SWA) + 6 ensemble configs
(3 ckpts × {median, mean}) on raw dense y_600 with consistent ground truth.

Methodology (locked, per anti-pattern #19):
  - Ground truth y: from existing patched CSV `y_true_logret` (raw bps via data/npz_v4)
  - Predictions: per-seed test_preds.npz q50 (z-space) × y_sigma → log-return → bps
  - Eval: dense (mask=1), per-fold breakdown + pooled across 3 folds
  - Metrics: P, S, β=cov/var(ŷ), σ_ŷ/σ_y, mean(ŷ), bin-Spearman(10 bins), top-bin-ŷ-mean

Output:
  exports/y600_ckpt_seed_diagnostic.md  (markdown table)
  exports/y600_diag_bin_plots/*.png    (per-config bin-plots, 9+6=15 plots)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Methodology config
NUM_FOLDS = 3
NUM_BINS = 10
CKPT_TO_FILE = {
    "BEST": "test_preds.npz",
    "EMA": "ema_test_preds.npz",
    "SWA": "swa_test_preds.npz",
}
SEED_DIRS = {
    42: Path("experiments/y600_push/baseline_plus"),
    7: Path("experiments/y600_baseline_seed7"),
    13: Path("experiments/y600_baseline_seed13"),
}
GROUND_TRUTH_CSV = Path("exports/y600_baseline_plus_BEST_3seed_median.csv")

OUT_MD = Path("exports/y600_ckpt_seed_diagnostic.md")
OUT_PLOTS = Path("exports/y600_diag_bin_plots")


def load_ground_truth() -> Dict[int, pd.DataFrame]:
    """Load patched CSV's y_true (raw log-return) keyed by fold.

    Returns: {fold: DataFrame[timestamp_us, y_true_logret, mask]}
    """
    df = pd.read_csv(GROUND_TRUTH_CSV)
    out = {}
    for f in range(NUM_FOLDS):
        sub = df[df["fold"] == f][["timestamp_us", "y_true_logret", "mask"]].reset_index(drop=True)
        out[f] = sub
    return out


def load_pred(seed: int, fold: int, ckpt: str) -> Tuple[np.ndarray, np.ndarray, float]:
    """Returns (timestamps, q50_z, y_sigma)."""
    fpath = SEED_DIRS[seed] / f"fold_{fold}" / CKPT_TO_FILE[ckpt]
    d = np.load(fpath)
    return (
        d["timestamps"].astype(np.int64),
        d["predictions"][:, 1].astype(np.float64),  # q50 z-space
        float(d["y_sigma"]),
    )


def compute_metrics(y_true_lr: np.ndarray, y_pred_lr: np.ndarray, mask: np.ndarray) -> Dict:
    """Pooled metrics on dense (mask=True). All in log-return units (×1e4 for bps later).

    Returns dict with: n, pearson, spearman, beta_y_on_yhat, sigma_ratio,
                       mean_yhat_bps, mean_y_bps, bin_spearman, top_bin_yhat_bps
    """
    valid = mask.astype(bool) & np.isfinite(y_true_lr) & np.isfinite(y_pred_lr)
    y = y_true_lr[valid]
    yp = y_pred_lr[valid]
    n = len(y)
    if n < 10:
        return {"n": n}

    pearson = float(np.corrcoef(y, yp)[0, 1])
    spearman = float(spearmanr(y, yp).correlation)
    cov = np.mean((y - y.mean()) * (yp - yp.mean()))
    var_yp = np.var(yp)
    beta = cov / var_yp if var_yp > 1e-20 else float("nan")
    sigma_ratio = (np.std(yp) / np.std(y)) if np.std(y) > 1e-20 else float("nan")

    # Bin-plot E[ŷ|y_bin] using equal-quantile bins on y
    bin_edges = np.quantile(y, np.linspace(0, 1, NUM_BINS + 1))
    bin_edges[0] -= 1e-12
    bin_edges[-1] += 1e-12
    bins_idx = np.searchsorted(bin_edges, y, side="right") - 1
    bins_idx = np.clip(bins_idx, 0, NUM_BINS - 1)
    bin_y_means = np.array([y[bins_idx == i].mean() if (bins_idx == i).any() else np.nan
                             for i in range(NUM_BINS)])
    bin_yp_means = np.array([yp[bins_idx == i].mean() if (bins_idx == i).any() else np.nan
                              for i in range(NUM_BINS)])
    valid_bins = np.isfinite(bin_y_means) & np.isfinite(bin_yp_means)
    if valid_bins.sum() >= 3:
        bin_spearman = float(spearmanr(bin_y_means[valid_bins], bin_yp_means[valid_bins]).correlation)
    else:
        bin_spearman = float("nan")
    top_bin_yp_bps = float(bin_yp_means[-1]) * 1e4 if np.isfinite(bin_yp_means[-1]) else float("nan")

    return {
        "n": n,
        "pearson": pearson,
        "spearman": spearman,
        "beta": beta,
        "sigma_ratio": sigma_ratio,
        "mean_yhat_bps": float(yp.mean()) * 1e4,
        "mean_y_bps": float(y.mean()) * 1e4,
        "bin_spearman": bin_spearman,
        "top_bin_yhat_bps": top_bin_yp_bps,
        "_bin_y_means": bin_y_means,
        "_bin_yp_means": bin_yp_means,
    }


def get_per_seed_pred_lr(fold: int, ckpt: str) -> Dict[int, np.ndarray]:
    """For a given fold and ckpt, return {seed: pred_lr_array}."""
    out = {}
    for seed in SEED_DIRS:
        ts, pred_z, sigma = load_pred(seed, fold, ckpt)
        out[seed] = pred_z * sigma  # log-return
    return out


def eval_config(label: str, get_pred_fn) -> Dict:
    """get_pred_fn(fold, ckpt) → pred_lr array aligned with ground truth."""
    raise NotImplementedError("inline below")


def evaluate_all() -> List[Dict]:
    """Returns list of dicts, one per config, with all metrics."""
    gt = load_ground_truth()  # {fold: df[timestamp_us, y_true_logret, mask]}
    results = []

    # Helper: per-fold metric arrays for triplet display
    def collect_per_fold_then_pool(label: str, ckpt: str, fold_pred_lr: Dict[int, np.ndarray]) -> Dict:
        """fold_pred_lr: {fold: pred_lr_aligned_to_gt}"""
        per_fold = []
        all_y = []
        all_yp = []
        all_m = []
        for f in range(NUM_FOLDS):
            df_gt = gt[f]
            y_lr = df_gt["y_true_logret"].values.astype(np.float64)
            mask = df_gt["mask"].values.astype(bool)
            pred_lr = fold_pred_lr[f]
            assert len(y_lr) == len(pred_lr), f"{label} fold {f}: len mismatch"
            m_per = compute_metrics(y_lr, pred_lr, mask)
            per_fold.append(m_per)
            all_y.append(y_lr)
            all_yp.append(pred_lr)
            all_m.append(mask)
        # Pool
        y_all = np.concatenate(all_y)
        yp_all = np.concatenate(all_yp)
        m_all = np.concatenate(all_m)
        m_pool = compute_metrics(y_all, yp_all, m_all)

        # Per-fold pearson list for std
        pf_p = [m["pearson"] for m in per_fold if "pearson" in m]
        pf_s = [m["spearman"] for m in per_fold if "spearman" in m]
        pf_beta = [m["beta"] for m in per_fold if "beta" in m]

        return {
            "label": label,
            "ckpt": ckpt,
            "pooled": m_pool,
            "per_fold_pearson": pf_p,
            "per_fold_spearman": pf_s,
            "per_fold_beta": pf_beta,
        }

    # 9 single-seed configs
    for seed in sorted(SEED_DIRS.keys()):
        for ckpt in ["BEST", "EMA", "SWA"]:
            label = f"seed{seed:02d}_{ckpt}"
            fold_pred_lr = {}
            for f in range(NUM_FOLDS):
                ts, pred_z, sigma = load_pred(seed, f, ckpt)
                fold_pred_lr[f] = pred_z * sigma
            r = collect_per_fold_then_pool(label, ckpt, fold_pred_lr)
            r["seed"] = seed
            r["agg"] = "single"
            results.append(r)
            print(f"[{label:18s}] P={r['pooled']['pearson']:+.4f} "
                  f"S={r['pooled']['spearman']:+.4f} "
                  f"β={r['pooled']['beta']:+.3f} "
                  f"σ_ŷ/σ_y={r['pooled']['sigma_ratio']:.3f} "
                  f"meanŷ={r['pooled']['mean_yhat_bps']:+.3f}bps "
                  f"top_ŷ={r['pooled']['top_bin_yhat_bps']:+.3f}bps "
                  f"binS={r['pooled']['bin_spearman']:+.3f}")

    # 6 ensemble configs (3 ckpt × 2 agg: median, mean)
    for ckpt in ["BEST", "EMA", "SWA"]:
        per_seed_per_fold = {f: get_per_seed_pred_lr(f, ckpt) for f in range(NUM_FOLDS)}
        for agg in ["median", "mean"]:
            label = f"3seed_{agg}_{ckpt}"
            fold_pred_lr = {}
            for f in range(NUM_FOLDS):
                stack = np.stack([per_seed_per_fold[f][s] for s in sorted(SEED_DIRS.keys())], axis=0)
                if agg == "median":
                    fold_pred_lr[f] = np.median(stack, axis=0)
                else:
                    fold_pred_lr[f] = np.mean(stack, axis=0)
            r = collect_per_fold_then_pool(label, ckpt, fold_pred_lr)
            r["seed"] = "ens"
            r["agg"] = agg
            results.append(r)
            print(f"[{label:18s}] P={r['pooled']['pearson']:+.4f} "
                  f"S={r['pooled']['spearman']:+.4f} "
                  f"β={r['pooled']['beta']:+.3f} "
                  f"σ_ŷ/σ_y={r['pooled']['sigma_ratio']:.3f} "
                  f"meanŷ={r['pooled']['mean_yhat_bps']:+.3f}bps "
                  f"top_ŷ={r['pooled']['top_bin_yhat_bps']:+.3f}bps "
                  f"binS={r['pooled']['bin_spearman']:+.3f}")

    return results


def write_markdown(results: List[Dict]):
    OUT_MD.parent.mkdir(exist_ok=True, parents=True)
    lines = []
    lines.append("# y_600 ckpt × seed diagnostic\n")
    lines.append("Methodology: raw dense y_600 (from patched CSV), per-fold-aware pool, q50 predictions\n")
    lines.append("- N_pooled = 48,678 valid (across 3 folds: 15,695 + 16,771 + 17,111)")
    lines.append("- Sample units in metric: log-return; bps = ×1e4")
    lines.append("- y_true_bps stats: mean ≈ -0.46 bps, std ≈ 9.5 bps (per fold), pooled std ~9.5 bps")
    lines.append("- σ_y_pool ≈ 9.5 bps means σ_ŷ/σ_y at 0.05 corresponds to σ_ŷ ≈ 0.5 bps\n")

    # Group A: per-seed per-ckpt
    lines.append("## Single-seed × ckpt (9 configs)\n")
    lines.append("| Config | P | S | β | σ_ŷ/σ_y | mean(ŷ) bps | top-bin ŷ bps | bin-Sp | per-fold P (std) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in results:
        if r["agg"] != "single":
            continue
        m = r["pooled"]
        pf_p_str = "[" + ", ".join(f"{p:+.4f}" for p in r["per_fold_pearson"]) + "]"
        pf_p_std = float(np.std(r["per_fold_pearson"]))
        lines.append(
            f"| {r['label']} | {m['pearson']:+.4f} | {m['spearman']:+.4f} | {m['beta']:+.3f} | "
            f"{m['sigma_ratio']:.3f} | {m['mean_yhat_bps']:+.3f} | {m['top_bin_yhat_bps']:+.3f} | "
            f"{m['bin_spearman']:+.3f} | {pf_p_str} σ={pf_p_std:.4f} |"
        )

    # Group B: ensembles
    lines.append("\n## Ensemble (median/mean × 3 ckpt = 6 configs)\n")
    lines.append("| Config | P | S | β | σ_ŷ/σ_y | mean(ŷ) bps | top-bin ŷ bps | bin-Sp | per-fold P (std) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in results:
        if r["agg"] == "single":
            continue
        m = r["pooled"]
        pf_p_str = "[" + ", ".join(f"{p:+.4f}" for p in r["per_fold_pearson"]) + "]"
        pf_p_std = float(np.std(r["per_fold_pearson"]))
        lines.append(
            f"| {r['label']} | {m['pearson']:+.4f} | {m['spearman']:+.4f} | {m['beta']:+.3f} | "
            f"{m['sigma_ratio']:.3f} | {m['mean_yhat_bps']:+.3f} | {m['top_bin_yhat_bps']:+.3f} | "
            f"{m['bin_spearman']:+.3f} | {pf_p_str} σ={pf_p_std:.4f} |"
        )

    # Comparison summary by ckpt
    lines.append("\n## Aggregate by ckpt type (across 3 single seeds + 2 ensembles per ckpt)\n")
    by_ckpt = {"BEST": [], "EMA": [], "SWA": []}
    for r in results:
        by_ckpt[r["ckpt"]].append(r)
    lines.append("| ckpt | mean(P) | min/max(P) | mean(σ_ŷ/σ_y) | mean(\\|mean(ŷ)\\|) bps | mean(top-bin ŷ) bps | mean(bin-Sp) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for ckpt in ["BEST", "EMA", "SWA"]:
        rs = by_ckpt[ckpt]
        Ps = [r["pooled"]["pearson"] for r in rs]
        sigs = [r["pooled"]["sigma_ratio"] for r in rs]
        meanyhats = [abs(r["pooled"]["mean_yhat_bps"]) for r in rs]
        topbins = [r["pooled"]["top_bin_yhat_bps"] for r in rs]
        binsps = [r["pooled"]["bin_spearman"] for r in rs]
        lines.append(
            f"| {ckpt} | {np.mean(Ps):+.4f} | {np.min(Ps):+.4f}/{np.max(Ps):+.4f} | "
            f"{np.mean(sigs):.3f} | {np.mean(meanyhats):.3f} | {np.mean(topbins):+.3f} | "
            f"{np.mean(binsps):+.3f} |"
        )

    # Decision tree
    lines.append("\n## Decision criteria\n")
    lines.append("Looking for the config that maximizes:")
    lines.append("- **trading-side calibration**: |mean(ŷ)| close to 0, top-bin ŷ > 0, β close to 1.0")
    lines.append("- **statistical IC**: P, S high")
    lines.append("- **stability**: per-fold P std small")
    lines.append("- **σ_ŷ expression**: σ_ŷ/σ_y as high as possible without sacrificing P")
    lines.append("\nProduction candidate decision rules:")
    lines.append("1. If a single seed clearly wins on level metrics + P/S not worse → use it (defensible vs anti-pattern #14 if pre-declared seed=42 is the winner)")
    lines.append("2. If 3seed_mean ≥ 3seed_median on P/S AND level metrics → switch to mean (linear, no tail squeeze)")
    lines.append("3. If BEST has best β/top-bin ŷ + similar P/S → switch from EMA to BEST")

    OUT_MD.write_text("\n".join(lines))
    print(f"\nWrote {OUT_MD}")


def make_bin_plots(results: List[Dict]):
    OUT_PLOTS.mkdir(exist_ok=True, parents=True)
    # Plot per config; group by ckpt for easier visual scanning
    for r in results:
        m = r["pooled"]
        if "_bin_y_means" not in m:
            continue
        ymean = m["_bin_y_means"] * 1e4  # bps
        ypmean = m["_bin_yp_means"] * 1e4
        bins = np.arange(NUM_BINS)
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(ymean, ypmean, "o-", lw=2, ms=7)
        ax.axhline(0, color="gray", ls=":", lw=0.7)
        ax.axvline(0, color="gray", ls=":", lw=0.7)
        # Identity line for reference
        lim = max(abs(ymean).max(), abs(ypmean).max())
        ax.plot([-lim, lim], [-lim, lim], "k--", lw=0.5, alpha=0.4, label="y=ŷ")
        ax.set_xlabel("y_true bin mean (bps)")
        ax.set_ylabel("ŷ bin mean (bps)")
        ax.set_title(f"{r['label']}: P={m['pearson']:+.4f} S={m['spearman']:+.4f} β={m['beta']:+.3f} bin-Sp={m['bin_spearman']:+.3f}")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper left", fontsize=8)
        fig.tight_layout()
        out_path = OUT_PLOTS / f"{r['label']}.png"
        fig.savefig(out_path, dpi=110)
        plt.close(fig)
    print(f"Wrote {len(results)} plots to {OUT_PLOTS}")


def main():
    print("=== y_600 ckpt × seed diagnostic ===\n")
    results = evaluate_all()
    write_markdown(results)
    make_bin_plots(results)
    print("\nDone.")


if __name__ == "__main__":
    main()

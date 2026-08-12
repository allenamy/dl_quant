"""V5 comprehensive evaluation: calibration view + trading view + V5 gate check.

Usage:
  python scripts/v5_eval_comprehensive.py \
      --exp-dir experiments/v5_screen/B1/v4base \
      --n-folds 1 \
      --out exports/v5_screen_B1_v4base.md

Methodology (anti-pattern #19 strict):
  - Ground truth: raw y_600 reconstructed from test_preds.npz as (target_z * y_sigma + y_median)
    (matches trainer's normalization; CODEX FIX: include y_median)
  - Eval: dense (mask=1), per-fold-aware pool across N folds
  - Reports calibration view (bin by y) AND trading view (bin by ŷ)
  - Hard pass/fail gates G1-G6 per docs/V5_DESIGN_v2.md
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Dict
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def compute_v5_metrics(y: np.ndarray, yp: np.ndarray, mask: np.ndarray, n_bins: int = 10) -> Dict:
    """Compute V5-relevant metrics on (y, yp) with mask. All inputs in raw log-return units."""
    valid = mask.astype(bool) & np.isfinite(y) & np.isfinite(yp)
    y, yp = y[valid], yp[valid]
    n = len(y)
    if n < 30:
        return {"n": n}

    P = float(np.corrcoef(y, yp)[0, 1])
    S = float(spearmanr(y, yp).correlation)
    cov = np.mean((y - y.mean()) * (yp - yp.mean()))
    var_yp = np.var(yp)
    beta = cov / var_yp if var_yp > 1e-30 else float("nan")
    sigma_ratio = float(np.std(yp) / np.std(y)) if np.std(y) > 1e-30 else float("nan")

    # Calibration view: bin by y, E[ŷ | y_bin]
    edges_y = np.quantile(y, np.linspace(0, 1, n_bins + 1))
    edges_y[0] -= 1e-12
    edges_y[-1] += 1e-12
    idx_y = np.clip(np.searchsorted(edges_y, y, side="right") - 1, 0, n_bins - 1)
    bin_y_means = np.array([y[idx_y == i].mean() for i in range(n_bins)])
    bin_yp_means_calib = np.array([yp[idx_y == i].mean() for i in range(n_bins)])
    bin_S = float(spearmanr(bin_y_means, bin_yp_means_calib).correlation) if not np.isnan(bin_y_means).any() else float("nan")
    top_bin_yhat_bps = float(bin_yp_means_calib[-1]) * 1e4

    # Trading view: bin by yp, E[y | yp_bin]
    edges_yp = np.quantile(yp, np.linspace(0, 1, n_bins + 1))
    edges_yp[0] -= 1e-12
    edges_yp[-1] += 1e-12
    idx_yp = np.clip(np.searchsorted(edges_yp, yp, side="right") - 1, 0, n_bins - 1)
    top_decile_y = y[idx_yp == n_bins - 1]
    bot_decile_y = y[idx_yp == 0]
    top_decile_y_bps = float(top_decile_y.mean()) * 1e4 if len(top_decile_y) > 0 else float("nan")
    bot_decile_y_bps = float(bot_decile_y.mean()) * 1e4 if len(bot_decile_y) > 0 else float("nan")
    top_t_stat = top_decile_y.mean() / (top_decile_y.std() / np.sqrt(max(1, len(top_decile_y)))) if len(top_decile_y) > 1 else float("nan")
    bot_t_stat = bot_decile_y.mean() / (bot_decile_y.std() / np.sqrt(max(1, len(bot_decile_y)))) if len(bot_decile_y) > 1 else float("nan")
    spread_bps = top_decile_y_bps - bot_decile_y_bps if not (np.isnan(top_decile_y_bps) or np.isnan(bot_decile_y_bps)) else float("nan")

    return {
        "n": n,
        "P": P,
        "S": S,
        "beta": beta,
        "sigma_ratio": sigma_ratio,
        "mean_yhat_bps": float(yp.mean()) * 1e4,
        "mean_y_bps": float(y.mean()) * 1e4,
        "bin_S": bin_S,
        "top_bin_yhat_bps": top_bin_yhat_bps,
        "top_decile_y_bps": top_decile_y_bps,
        "top_decile_t_stat": float(top_t_stat),
        "bottom_decile_y_bps": bot_decile_y_bps,
        "bottom_decile_t_stat": float(bot_t_stat),
        "top_minus_bottom_bps": spread_bps,
    }


def check_v5_gates(metrics: Dict) -> Dict[str, bool]:
    """V5 hard gates G1-G6 per docs/V5_DESIGN_v2.md + stretch S1-S2."""
    return {
        "G1_P_no_regression": metrics.get("P", -1) >= 0.045,
        "G2_sigma_ratio_2x": metrics.get("sigma_ratio", 0) >= 0.10,
        "G3_beta_calibrated": abs(metrics.get("beta", 999) - 1.0) <= 0.20,
        "G4_trading_top_pos": (
            metrics.get("top_decile_y_bps", -1) >= 0.5
            and metrics.get("top_decile_t_stat", 0) >= 2.0
        ),
        "G5_bin_S_monotonic": metrics.get("bin_S", -1) >= 0.85,
        "G6_no_bias": abs(metrics.get("mean_yhat_bps", 999)) <= 0.10,
        "S1_P_strong": metrics.get("P", 0) >= 0.055,
        "S2_sigma_strong": metrics.get("sigma_ratio", 0) >= 0.20,
    }


def load_fold(npz_path: Path) -> Dict:
    """Load test_preds.npz with codex-correct de-normalization (z*sigma+median).

    Returns dict with y_lr, yp_lr, mask, ts (all log-return space, raw).
    Handles both V4 (predictions[:, 1]) and V5 (mu) prediction formats.
    """
    d = np.load(npz_path)
    sigma_train = float(d["y_sigma"]) if "y_sigma" in d.files else 1.0
    y_median = float(d["y_median"]) if "y_median" in d.files else 0.0
    # V5: 'mu' stored; V4: predictions[:, 1] = q50
    if "mu" in d.files:
        pred_z = d["mu"].astype(np.float64).ravel()
        log_sigma_z = d["log_sigma"].astype(np.float64).ravel() if "log_sigma" in d.files else None
    else:
        pred_z = d["predictions"][:, 1].astype(np.float64)
        log_sigma_z = None
    targets_z = d["targets"].astype(np.float64).ravel() if "targets" in d.files else None
    # Raw log-return: z * sigma + median (codex fix — DO NOT drop median)
    yp_lr = pred_z * sigma_train + y_median
    y_lr = (targets_z * sigma_train + y_median) if targets_z is not None else None
    mask = d["mask"].astype(bool) if "mask" in d.files else np.ones_like(yp_lr, dtype=bool)
    ts = d["timestamps"].astype(np.int64) if "timestamps" in d.files else None
    return {
        "y_lr": y_lr,
        "yp_lr": yp_lr,
        "mask": mask,
        "ts": ts,
        "sigma_train": sigma_train,
        "y_median": y_median,
        "log_sigma_z": log_sigma_z,  # available for V5 NLL models
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exp-dir", required=True)
    p.add_argument("--n-folds", type=int, default=1)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    exp = Path(args.exp_dir)
    pieces_y, pieces_yp, pieces_m = [], [], []
    per_fold_metrics = []
    for f in range(args.n_folds):
        npz_path = exp / f"fold_{f}" / "test_preds.npz"
        if not npz_path.exists():
            # Try ema or swa variant
            for variant in ["ema_test_preds.npz", "swa_test_preds.npz"]:
                alt = exp / f"fold_{f}" / variant
                if alt.exists():
                    npz_path = alt
                    print(f"[INFO] using {variant} for fold {f}")
                    break
            else:
                print(f"[WARN] missing fold {f} test_preds.npz")
                continue

        data = load_fold(npz_path)
        m = compute_v5_metrics(data["y_lr"], data["yp_lr"], data["mask"])
        m["fold"] = f
        per_fold_metrics.append(m)
        pieces_y.append(data["y_lr"])
        pieces_yp.append(data["yp_lr"])
        pieces_m.append(data["mask"])
        print(f"fold {f}: P={m.get('P', float('nan')):+.4f} S={m.get('S', float('nan')):+.4f} "
              f"β={m.get('beta', float('nan')):+.3f} σŷ/σy={m.get('sigma_ratio', float('nan')):.3f} "
              f"top E[y]={m.get('top_decile_y_bps', float('nan')):+.3f}bps")

    if not pieces_y:
        print("[FAIL] no fold predictions found")
        return 1

    y_pool = np.concatenate(pieces_y)
    yp_pool = np.concatenate(pieces_yp)
    m_pool = np.concatenate(pieces_m)
    pooled = compute_v5_metrics(y_pool, yp_pool, m_pool)
    gates = check_v5_gates(pooled)

    # Console summary
    print("\n=== POOLED ===")
    for k in ["P", "S", "beta", "sigma_ratio", "bin_S", "mean_yhat_bps",
              "top_bin_yhat_bps", "top_decile_y_bps", "top_decile_t_stat",
              "bottom_decile_y_bps", "top_minus_bottom_bps"]:
        v = pooled.get(k, "NA")
        print(f"  {k}: {v if isinstance(v, str) else f'{v:+.4f}'}")
    print("\n=== GATES ===")
    required = [k for k in gates if k.startswith("G")]
    for k, v in gates.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    n_pass = sum(gates[k] for k in required)
    verdict = f"{'PASS' if n_pass == len(required) else 'PARTIAL'} {n_pass}/{len(required)}"
    print(f"\nVerdict: {verdict}")

    # Markdown report
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# V5 eval: `{exp}`\n", f"N folds: {args.n_folds}, n_pooled: {pooled['n']:,}\n"]
        lines.append("## Pooled metrics\n")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        for k in ["P", "S", "beta", "sigma_ratio", "bin_S", "mean_yhat_bps",
                  "top_bin_yhat_bps", "top_decile_y_bps", "top_decile_t_stat",
                  "bottom_decile_y_bps", "bottom_decile_t_stat", "top_minus_bottom_bps"]:
            v = pooled.get(k, "NA")
            lines.append(f"| {k} | {v if isinstance(v, str) else f'{v:+.4f}'} |")
        lines.append("\n## V5 Gates\n")
        lines.append("| Gate | Pass | Description |")
        lines.append("|---|---|---|")
        descs = {
            "G1_P_no_regression": "P ≥ 0.045 (no regression vs V4)",
            "G2_sigma_ratio_2x": "σ_ŷ/σ_y ≥ 0.10 (2× wider than V4)",
            "G3_beta_calibrated": "|β-1| ≤ 0.20",
            "G4_trading_top_pos": "top decile E[y] ≥ +0.5 bps with t≥2",
            "G5_bin_S_monotonic": "bin-Spearman ≥ 0.85",
            "G6_no_bias": "|mean(ŷ)| ≤ 0.10 bps",
            "S1_P_strong": "(stretch) P ≥ 0.055",
            "S2_sigma_strong": "(stretch) σ_ŷ/σ_y ≥ 0.20",
        }
        for k, v in gates.items():
            lines.append(f"| {k} | {'PASS' if v else 'FAIL'} | {descs.get(k, '')} |")
        lines.append(f"\n**Verdict: {verdict}**")
        if per_fold_metrics:
            lines.append("\n## Per-fold breakdown\n")
            lines.append("| fold | P | S | β | σŷ/σy | bin_S | top_E[y]_bps |")
            lines.append("|---|---|---|---|---|---|---|")
            for m in per_fold_metrics:
                lines.append(f"| {m['fold']} | {m.get('P', float('nan')):+.4f} | "
                             f"{m.get('S', float('nan')):+.4f} | "
                             f"{m.get('beta', float('nan')):+.3f} | "
                             f"{m.get('sigma_ratio', float('nan')):.3f} | "
                             f"{m.get('bin_S', float('nan')):+.3f} | "
                             f"{m.get('top_decile_y_bps', float('nan')):+.3f} |")
        Path(args.out).write_text("\n".join(lines))
        print(f"\nWrote {args.out}")

    return 0 if all(gates[k] for k in required) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

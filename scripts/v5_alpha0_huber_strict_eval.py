"""V5 dualh α=0+Huber — strict comprehensive self-test.

Runs all metric categories on the production CSV:
  1. Sample IC (per-fold + pooled): Pearson, Spearman, regression R², ρ²
  2. Bootstrap CI (95%, stationary block, B=2000, block_len=60)
  3. Calibration: β both directions, σŷ/σy, bias bps
  4. Trading view: deciles by ŷ → y_mean, top/bot t-stats, top-minus-bot spread
  5. Calibration view: deciles by y → ŷ_mean, top y-bin ŷ_mean ≥ 0 check
  6. Monotonicity: bin-Spearman both views
  7. Direction accuracy: overall + tail (|y|>2σ) + top decile
  8. Residual auto-correlation: lag 1, 5, 10, 30
  9. Stability: per-fold P/S std, β CoV
 10. Quantile coverage: q10 below 10%, q90 above 90%
 11. Bin plot E[ŷ|y_bin] — written to PNG

Usage:
  python scripts/v5_alpha0_huber_strict_eval.py \
      --csv exports/v5_alpha0_huber/y600_predictions_all_folds.csv \
      --out exports/v5_alpha0_huber/STRICT_EVAL.md
"""
from __future__ import annotations
import argparse
import pathlib
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

HAS_MPL = False  # plot generation disabled (mpl import hangs on this machine; numeric data is in markdown)


# ---------------------------------------------------------------------------
# Metric primitives
# ---------------------------------------------------------------------------

def regression_r2(y: np.ndarray, yhat: np.ndarray) -> float:
    """1 - SS_res/SS_tot. Negative if predictor worse than mean."""
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return float(1 - ss_res / max(ss_tot, 1e-12))


def stationary_block_bootstrap_ci(
    y: np.ndarray, yhat: np.ndarray, stat_fn, B: int = 2000, block_len: int = 60, seed: int = 42
) -> Tuple[float, float]:
    """95% CI on stat_fn(y, yhat) via stationary block bootstrap (vectorized).

    Uses fixed-block-size circular bootstrap for speed (close to stationary
    bootstrap; preserves serial dependence at lag <= block_len).
    """
    n = len(y)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_len))
    out = np.empty(B)
    for b in range(B):
        starts = rng.integers(0, n, size=n_blocks)
        idx = (starts[:, None] + np.arange(block_len)[None, :]).ravel() % n
        idx = idx[:n]
        out[b] = stat_fn(y[idx], yhat[idx])
    return float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975))


def directional_accuracy(y: np.ndarray, yhat: np.ndarray) -> float:
    """Fraction of samples where sign(yhat) == sign(y), zero excluded."""
    nz = (y != 0) & (yhat != 0)
    if nz.sum() < 1:
        return float("nan")
    return float(np.mean(np.sign(y[nz]) == np.sign(yhat[nz])))


def per_decile_stats(
    y: np.ndarray, yhat: np.ndarray, bin_by: str = "yhat", n_bins: int = 10
) -> pd.DataFrame:
    """Bin samples into n_bins deciles by `bin_by` (yhat or y). Return per-decile aggregates."""
    z = yhat if bin_by == "yhat" else y
    edges = np.quantile(z, np.linspace(0, 1, n_bins + 1))
    edges[0] -= 1e-12
    edges[-1] += 1e-12
    idx = np.clip(np.searchsorted(edges, z, side="right") - 1, 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        m = idx == b
        ys, qs = y[m], yhat[m]
        n = m.sum()
        rows.append({
            "bin": b,
            "n": int(n),
            "yhat_mean_bps": float(qs.mean()),
            "y_mean_bps": float(ys.mean()),
            "y_std_bps": float(ys.std()),
            "y_t_stat": float(ys.mean() / (ys.std() / np.sqrt(max(1, n)))) if n > 1 else float("nan"),
            "diracc": float(np.mean(np.sign(ys) == np.sign(qs))),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bootstrap-b", type=int, default=2000)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df[df["mask"] == 1].reset_index(drop=True)

    # All in bps
    y = df["y_true_bps"].to_numpy()
    q10 = df["y_pred_q10_logret"].to_numpy() * 1e4
    q50 = df["y_pred_q50_bps"].to_numpy()
    q90 = df["y_pred_q90_logret"].to_numpy() * 1e4
    fold = df["fold"].to_numpy()
    ts = df["timestamp_us"].to_numpy()

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    md = lines.append

    md("# V5 dualh α=0+Huber — Strict Comprehensive Self-Test")
    md(f"\n**CSV:** `{args.csv}` ({len(df):,} valid rows, mask=1, raw bps)")
    md(f"**Folds:** {sorted(set(fold))}")
    md(f"**Time range:** {df['datetime_utc'].min()} → {df['datetime_utc'].max()}\n")

    # ------------------------------------------------------------------
    # 1. Sample IC: per-fold + pooled
    # ------------------------------------------------------------------
    md("## 1. Sample IC — Pearson / Spearman / R²")
    md("\n| Slice | n | Pearson | Spearman | reg R² | ρ² (Pearson²) |")
    md("|---|---:|---:|---:|---:|---:|")
    fold_p, fold_s = [], []
    for f in sorted(set(fold)):
        m = fold == f
        ys, qs = y[m], q50[m]
        p = pearsonr(qs, ys)[0]
        s = spearmanr(qs, ys)[0]
        r2_reg = regression_r2(ys, qs)
        md(f"| fold {f} | {m.sum():,} | {p:+.4f} | {s:+.4f} | {r2_reg:+.5f} | {p*p:+.5f} |")
        fold_p.append(p); fold_s.append(s)
    p_pool = pearsonr(q50, y)[0]
    s_pool = spearmanr(q50, y)[0]
    r2_pool = regression_r2(y, q50)
    md(f"| **POOLED** | **{len(y):,}** | **{p_pool:+.4f}** | **{s_pool:+.4f}** | **{r2_pool:+.5f}** | **{p_pool*p_pool:+.5f}** |")
    md(f"| per-fold std | | {np.std(fold_p):.4f} | {np.std(fold_s):.4f} | | |")

    # ------------------------------------------------------------------
    # 2. Bootstrap CI on pooled P / S
    # ------------------------------------------------------------------
    md("\n## 2. Bootstrap 95% CI (stationary block, block_len=60, B={})".format(args.bootstrap_b))
    if args.bootstrap_b > 0:
        p_lo, p_hi = stationary_block_bootstrap_ci(y, q50, lambda a, b: pearsonr(a, b)[0], B=args.bootstrap_b)
        s_lo, s_hi = stationary_block_bootstrap_ci(y, q50, lambda a, b: spearmanr(a, b).correlation, B=args.bootstrap_b)
        md(f"\n- Pearson: **{p_pool:+.4f}** [{p_lo:+.4f}, {p_hi:+.4f}]")
        md(f"- Spearman: **{s_pool:+.4f}** [{s_lo:+.4f}, {s_hi:+.4f}]")
        sign_p = "✓ (lower bound > 0)" if p_lo > 0 else "✗ (CI crosses 0)"
        sign_s = "✓ (lower bound > 0)" if s_lo > 0 else "✗ (CI crosses 0)"
        md(f"- Significance — Pearson: {sign_p}; Spearman: {sign_s}")
    else:
        md("\n- (bootstrap skipped: --bootstrap-b 0)")
        p_lo = p_hi = s_lo = s_hi = float('nan')

    # ------------------------------------------------------------------
    # 3. Calibration metrics
    # ------------------------------------------------------------------
    md("\n## 3. Calibration — β (both directions), σ ratio, bias")
    cov_qy = np.cov(q50, y)[0, 1]
    var_q = q50.var()
    var_y = y.var()
    beta_y_on_q = cov_qy / max(var_q, 1e-12)  # E[y | yhat] slope
    beta_q_on_y = cov_qy / max(var_y, 1e-12)  # = ρ * σ_q/σ_y (shrinkage)
    sigma_ratio = q50.std() / y.std()
    md("")
    md(f"- **β_y_on_ŷ** (trading slope; perfect=1.0) = `{beta_y_on_q:+.3f}`")
    md(f"- β_ŷ_on_y (shrinkage, = ρ·σŷ/σy) = `{beta_q_on_y:+.6f}`")
    md(f"- σŷ/σy = `{sigma_ratio:.4f}` (model expresses {sigma_ratio*100:.1f}% of y's amplitude)")
    md(f"- ŷ_mean = `{q50.mean():+.4f}` bps; y_mean = `{y.mean():+.4f}` bps; bias (ŷ-y) = `{(q50.mean()-y.mean()):+.4f}` bps")

    # ------------------------------------------------------------------
    # 4. Trading view: bin by ŷ
    # ------------------------------------------------------------------
    md("\n## 4. Trading View — deciles by ŷ → y_mean")
    df_trade = per_decile_stats(y, q50, bin_by="yhat", n_bins=10)
    md("\n| ŷ bin | n | ŷ_mean | y_mean | y_t_stat | dirAcc |")
    md("|---:|---:|---:|---:|---:|---:|")
    for _, r in df_trade.iterrows():
        md(f"| {int(r.bin)} | {int(r.n):,} | {r.yhat_mean_bps:+.3f} | {r.y_mean_bps:+.3f} | {r.y_t_stat:+.2f} | {r.diracc:.3f} |")
    spread = df_trade.iloc[-1].y_mean_bps - df_trade.iloc[0].y_mean_bps
    md(f"\n- Top-minus-bottom spread: **{spread:+.3f}** bps (target ≥ 1.0 bps)")
    md(f"- Top decile y_t_stat: **{df_trade.iloc[-1].y_t_stat:+.2f}** (target ≥ 2.0)")
    md(f"- Bottom decile y_t_stat: **{df_trade.iloc[0].y_t_stat:+.2f}** (target ≤ -2.0)")

    # ------------------------------------------------------------------
    # 5. Calibration view: bin by y
    # ------------------------------------------------------------------
    md("\n## 5. Calibration View — deciles by y → ŷ_mean (USER PRIMARY)")
    df_calib = per_decile_stats(y, q50, bin_by="y", n_bins=10)
    md("\n| y bin | n | y_mean | ŷ_mean | sign |")
    md("|---:|---:|---:|---:|:-:|")
    all_pos = True
    for _, r in df_calib.iterrows():
        sign = "✓" if r.yhat_mean_bps >= 0 else "✗ NEG"
        if r.yhat_mean_bps < 0:
            all_pos = False
        md(f"| {int(r.bin)} | {int(r.n):,} | {r.y_mean_bps:+.3f} | {r.yhat_mean_bps:+.3f} | {sign} |")
    top_y_bin_yhat = df_calib.iloc[-1].yhat_mean_bps
    md(f"\n- **Top y-bin ŷ_mean = `{top_y_bin_yhat:+.3f}` bps** (USER REQUIRED ≥ 0): {'✓ PASS' if top_y_bin_yhat >= 0 else '✗ FAIL'}")
    md(f"- ALL deciles ŷ_mean ≥ 0: {'✓' if all_pos else '✗'}")

    # ------------------------------------------------------------------
    # 6. Monotonicity (bin-Spearman both views)
    # ------------------------------------------------------------------
    md("\n## 6. Monotonicity — bin-Spearman")
    bin_S_calib = spearmanr(df_calib.y_mean_bps, df_calib.yhat_mean_bps).correlation
    bin_S_trade = spearmanr(df_trade.yhat_mean_bps, df_trade.y_mean_bps).correlation
    md(f"\n- Calibration view (bin by y): bin-Spearman = `{bin_S_calib:+.4f}` (target ≥ 0.85)")
    md(f"- Trading view (bin by ŷ): bin-Spearman = `{bin_S_trade:+.4f}` (target ≥ 0.85)")

    # ------------------------------------------------------------------
    # 7. Direction accuracy
    # ------------------------------------------------------------------
    md("\n## 7. Direction Accuracy")
    da_overall = directional_accuracy(y, q50)
    sigma_y = y.std()
    tail_mask = np.abs(y) > 2 * sigma_y
    da_tail = directional_accuracy(y[tail_mask], q50[tail_mask])
    top_dec_mask = q50 >= np.quantile(q50, 0.9)
    bot_dec_mask = q50 <= np.quantile(q50, 0.1)
    da_top = directional_accuracy(y[top_dec_mask], q50[top_dec_mask])
    da_bot = directional_accuracy(y[bot_dec_mask], q50[bot_dec_mask])
    md(f"\n- Overall DirAcc: **{da_overall:.4f}** (target > 0.5)")
    md(f"- Tail DirAcc (|y| > 2σ_y, n={tail_mask.sum():,}): **{da_tail:.4f}** (target ≥ 0.52)")
    md(f"- Top-decile-ŷ DirAcc: **{da_top:.4f}** (signals model TRUSTS most)")
    md(f"- Bottom-decile-ŷ DirAcc: **{da_bot:.4f}**")

    # ------------------------------------------------------------------
    # 8. Residual auto-correlation
    # ------------------------------------------------------------------
    md("\n## 8. Residual Auto-Correlation (lag 1, 5, 10, 30)")
    md("\nResiduals = (y - ŷ) per fold, then concatenated. ŷ-only auto-correlation also reported (predictions shouldn't repeat prev signal too tightly).")
    resid = y - q50
    md("\n| lag | resid AC | ŷ AC | y AC (reference) |")
    md("|---:|---:|---:|---:|")
    for lag in [1, 5, 10, 30]:
        if len(resid) > lag:
            ac_r = float(np.corrcoef(resid[:-lag], resid[lag:])[0, 1])
            ac_q = float(np.corrcoef(q50[:-lag], q50[lag:])[0, 1])
            ac_y = float(np.corrcoef(y[:-lag], y[lag:])[0, 1])
            md(f"| {lag} | {ac_r:+.4f} | {ac_q:+.4f} | {ac_y:+.4f} |")
    md("\n- Residual AC ≪ y AC = model captures real dynamics (not just lagged y).")
    md("- ŷ AC ≪ y AC = model not just echoing previous signal (no trivial extrapolation).")

    # ------------------------------------------------------------------
    # 9. Stability across folds
    # ------------------------------------------------------------------
    md("\n## 9. Stability — per-fold variance + β stability")
    md(f"\n- per-fold Pearson std = `{np.std(fold_p):.4f}`, CoV = `{np.std(fold_p)/np.mean(fold_p):.3f}`")
    md(f"- per-fold Spearman std = `{np.std(fold_s):.4f}`, CoV = `{np.std(fold_s)/np.mean(fold_s):.3f}`")
    fold_betas = []
    for f in sorted(set(fold)):
        m = fold == f
        cov = np.cov(q50[m], y[m])[0, 1]
        v = q50[m].var()
        fold_betas.append(cov / max(v, 1e-12))
    md(f"- per-fold β = {[f'{b:+.3f}' for b in fold_betas]} (all should be in [0.5, 2.0])")
    md(f"- β CoV = `{np.std(fold_betas)/np.abs(np.mean(fold_betas)):.3f}`")

    # ------------------------------------------------------------------
    # 10. Quantile coverage (q10 / q90)
    # ------------------------------------------------------------------
    md("\n## 10. Quantile Coverage (q10 / q90)")
    cov_q10 = float(np.mean(y < q10))
    cov_q90 = float(np.mean(y > q90))
    cov_q50 = float(np.mean(y < q50))
    md(f"\n- Empirical P(y < q10) = `{cov_q10:.3f}` (target ≈ 0.10)")
    md(f"- Empirical P(y < q50) = `{cov_q50:.3f}` (target ≈ 0.50)")
    md(f"- Empirical P(y > q90) = `{cov_q90:.3f}` (target ≈ 0.10)")
    md("\n- These check the *quantile head* calibration. Big deviations = miscalibrated head, but doesn't necessarily affect q50 trading utility.")

    # ------------------------------------------------------------------
    # 11. Bin plot (PNG)
    # ------------------------------------------------------------------
    if HAS_MPL:
        png_path = out_path.with_suffix(".png")
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        # Calibration view
        ax = axes[0]
        ax.plot(df_calib.y_mean_bps, df_calib.yhat_mean_bps, "o-", label="α=0+Huber")
        ax.axhline(0, color="grey", lw=0.5)
        ax.axvline(0, color="grey", lw=0.5)
        ax.plot([df_calib.y_mean_bps.min(), df_calib.y_mean_bps.max()],
                [df_calib.y_mean_bps.min(), df_calib.y_mean_bps.max()],
                "--", color="black", alpha=0.3, label="y=x ideal")
        ax.set_xlabel("y bin mean (bps)"); ax.set_ylabel("ŷ mean per bin (bps)")
        ax.set_title("Calibration view — E[ŷ | y_bin]"); ax.legend(); ax.grid(alpha=0.3)
        # Trading view
        ax = axes[1]
        ax.plot(df_trade.yhat_mean_bps, df_trade.y_mean_bps, "o-", color="orange", label="α=0+Huber")
        ax.axhline(0, color="grey", lw=0.5)
        ax.axvline(0, color="grey", lw=0.5)
        ax.set_xlabel("ŷ bin mean (bps)"); ax.set_ylabel("y mean per bin (bps)")
        ax.set_title("Trading view — E[y | ŷ_bin]"); ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(png_path, dpi=120)
        plt.close(fig)
        md(f"\n## 11. Bin plots\n\nSaved to: `{png_path.name}`")
    else:
        md("\n## 11. Bin plots — matplotlib unavailable, skipped")

    # ------------------------------------------------------------------
    # 12. Summary scorecard
    # ------------------------------------------------------------------
    md("\n## 12. PASS/FAIL Scorecard")
    gates = {
        "Pearson > 0.04 (above V4 baseline)": p_pool >= 0.04,
        "Spearman > 0.04 (above V4 baseline)": s_pool >= 0.04,
        "Bootstrap CI lower bound > 0 (Pearson)": (not np.isnan(p_lo)) and p_lo > 0,
        "Bootstrap CI lower bound > 0 (Spearman)": (not np.isnan(s_lo)) and s_lo > 0,
        "β_y_on_ŷ in [0.5, 2.0]": 0.5 <= beta_y_on_q <= 2.0,
        "σŷ/σy ≥ 0.02": sigma_ratio >= 0.02,
        "|bias| < 0.5 bps": abs(q50.mean() - y.mean()) < 0.5,
        "Top y-bin ŷ_mean ≥ 0 (USER PRIMARY)": top_y_bin_yhat >= 0,
        "ALL deciles ŷ_mean ≥ 0": all_pos,
        "Bin-Spearman ≥ 0.85 (calib)": bin_S_calib >= 0.85,
        "Bin-Spearman ≥ 0.85 (trade)": bin_S_trade >= 0.85,
        "Tail DirAcc ≥ 0.52": da_tail >= 0.52,
        "Top-bot spread ≥ 1.0 bps": spread >= 1.0,
        "per-fold P CoV < 0.20": (np.std(fold_p)/np.mean(fold_p)) < 0.20,
        "per-fold S CoV < 0.20": (np.std(fold_s)/np.mean(fold_s)) < 0.20,
    }
    md("\n| Gate | PASS |")
    md("|---|:-:|")
    for name, ok in gates.items():
        md(f"| {name} | {'✓' if ok else '✗'} |")
    pass_count = sum(gates.values())
    md(f"\n**Score: {pass_count} / {len(gates)} gates PASS**")

    out_path.write_text("\n".join(lines))
    print(f"→ {out_path}")
    print(f"\nScorecard: {pass_count}/{len(gates)} gates PASS")


if __name__ == "__main__":
    main()

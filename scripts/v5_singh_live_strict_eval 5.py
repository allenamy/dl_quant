"""Strict comprehensive eval on live-calibrated V5 singh predictions.

Mirrors v5_alpha0_huber_strict_eval.py but operates on the
`y_pred_q50_bps_live` (causal EMA-demeaned) column. Filters out
warmup rows. All 12 metric categories + 15-gate scorecard.

Usage:
  python scripts/v5_singh_live_strict_eval.py \
      --csv exports/v5_singh_alpha0_huber/y600_predictions_live.csv \
      --out exports/v5_singh_alpha0_huber/STRICT_EVAL_LIVE.md
"""
from __future__ import annotations
import argparse
import pathlib
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


def regression_r2(y, yhat):
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return float(1 - ss_res / max(ss_tot, 1e-12))


def stationary_block_bootstrap_ci(y, yhat, stat_fn, B=1000, block_len=60, seed=42):
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


def directional_accuracy(y, yhat):
    nz = (y != 0) & (yhat != 0)
    if nz.sum() < 1:
        return float("nan")
    return float(np.mean(np.sign(y[nz]) == np.sign(yhat[nz])))


def per_decile_stats(y, yhat, bin_by="yhat", n_bins=10):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bootstrap-b", type=int, default=1000)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df[(df["mask"] == 1) & (df["warmup"] == False)].reset_index(drop=True)

    y = df["y_true_bps"].to_numpy()
    q50 = df["y_pred_q50_bps_live"].to_numpy()  # ★ live-calibrated column
    q10 = df["y_pred_q10_logret"].to_numpy() * 1e4
    q90 = df["y_pred_q90_logret"].to_numpy() * 1e4
    fold = df["fold"].to_numpy()

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    md = lines.append

    md("# V5 singh α=0+Huber — Strict Eval on LIVE-CALIBRATED q50")
    md(f"\n**CSV:** `{args.csv}` ({len(df):,} rows after mask=1 + warmup=False filter, raw bps)")
    md(f"**Calibration:** causal rolling EMA-demean (α=0.01, HL≈69 samples≈11.5h, per-fold reset, 50-sample warmup excluded)")
    md(f"**Time range:** {df['datetime_utc'].min()} → {df['datetime_utc'].max()}\n")

    # 1. Sample IC
    md("## 1. Sample IC — Pearson / Spearman / R²")
    md("\n| Slice | n | Pearson | Spearman | reg R² |")
    md("|---|---:|---:|---:|---:|")
    fold_p, fold_s = [], []
    for f in sorted(set(fold)):
        m = fold == f
        ys, qs = y[m], q50[m]
        p, s = pearsonr(qs, ys)[0], spearmanr(qs, ys).correlation
        r2 = regression_r2(ys, qs)
        md(f"| fold {f} | {m.sum():,} | {p:+.4f} | {s:+.4f} | {r2:+.5f} |")
        fold_p.append(p); fold_s.append(s)
    p_pool, s_pool = pearsonr(q50, y)[0], spearmanr(q50, y).correlation
    r2_pool = regression_r2(y, q50)
    md(f"| **POOLED** | **{len(y):,}** | **{p_pool:+.4f}** | **{s_pool:+.4f}** | **{r2_pool:+.5f}** |")
    md(f"| per-fold std | | {np.std(fold_p):.4f} | {np.std(fold_s):.4f} | |")

    # 2. Bootstrap CI
    md("\n## 2. Bootstrap 95% CI (stationary block)")
    if args.bootstrap_b > 0:
        p_lo, p_hi = stationary_block_bootstrap_ci(y, q50, lambda a, b: pearsonr(a, b)[0], B=args.bootstrap_b)
        s_lo, s_hi = stationary_block_bootstrap_ci(y, q50, lambda a, b: spearmanr(a, b).correlation, B=args.bootstrap_b)
        md(f"\n- Pearson: **{p_pool:+.4f}** [{p_lo:+.4f}, {p_hi:+.4f}]")
        md(f"- Spearman: **{s_pool:+.4f}** [{s_lo:+.4f}, {s_hi:+.4f}]")
        sign_p = "✓" if p_lo > 0 else "✗"
        sign_s = "✓" if s_lo > 0 else "✗"
        md(f"- Significance — Pearson lower bound > 0: {sign_p}; Spearman lower bound > 0: {sign_s}")
    else:
        p_lo = p_hi = s_lo = s_hi = float("nan")

    # 3. Calibration metrics
    md("\n## 3. Calibration — β / σ / bias")
    cov_qy = np.cov(q50, y)[0, 1]
    var_q = q50.var()
    beta_y_on_q = cov_qy / max(var_q, 1e-12)
    sigma_ratio = q50.std() / y.std()
    bias = q50.mean() - y.mean()
    md(f"\n- β_y_on_ŷ (trading slope; perfect=1.0) = `{beta_y_on_q:+.3f}`")
    md(f"- σŷ/σy = `{sigma_ratio:.4f}` (model expresses {sigma_ratio*100:.1f}% of y's amplitude)")
    md(f"- ŷ_mean = `{q50.mean():+.4f}` bps, y_mean = `{y.mean():+.4f}` bps, bias = `{bias:+.4f}` bps")

    # 4. Trading view
    md("\n## 4. Trading View — deciles by ŷ → y_mean")
    df_trade = per_decile_stats(y, q50, bin_by="yhat", n_bins=10)
    md("\n| ŷ bin | n | ŷ_mean | y_mean | y_t_stat | dirAcc |")
    md("|---:|---:|---:|---:|---:|---:|")
    for _, r in df_trade.iterrows():
        md(f"| {int(r.bin)} | {int(r.n):,} | {r.yhat_mean_bps:+.3f} | {r.y_mean_bps:+.3f} | {r.y_t_stat:+.2f} | {r.diracc:.3f} |")
    spread = df_trade.iloc[-1].y_mean_bps - df_trade.iloc[0].y_mean_bps
    md(f"\n- Top-bot spread: **{spread:+.3f}** bps")
    md(f"- Top decile y_t_stat: **{df_trade.iloc[-1].y_t_stat:+.2f}**")
    md(f"- Bot decile y_t_stat: **{df_trade.iloc[0].y_t_stat:+.2f}**")

    # 5. Calibration view (THE KEY TEST)
    md("\n## 5. Calibration View — deciles by y → ŷ_mean (USER PRIMARY)")
    df_calib = per_decile_stats(y, q50, bin_by="y", n_bins=10)
    md("\n| y bin | n | y_mean | ŷ_mean | sign |")
    md("|---:|---:|---:|---:|:-:|")
    bin_y = []; bin_q = []
    for _, r in df_calib.iterrows():
        bin_y.append(r.y_mean_bps); bin_q.append(r.yhat_mean_bps)
        if r.y_mean_bps < 0:
            sign = "✓ NEG" if r.yhat_mean_bps < 0 else ("≈0" if abs(r.yhat_mean_bps) < 0.05 else "✗ POS")
        else:
            sign = "✓ POS" if r.yhat_mean_bps > 0 else ("≈0" if abs(r.yhat_mean_bps) < 0.05 else "✗ NEG")
        md(f"| {int(r.bin)} | {int(r.n):,} | {r.y_mean_bps:+.3f} | {r.yhat_mean_bps:+.3f} | {sign} |")

    bin_S = spearmanr(bin_y, bin_q).correlation
    top_y_bin = df_calib.iloc[-1].yhat_mean_bps
    bot_y_bin = df_calib.iloc[0].yhat_mean_bps
    md(f"\n- **Top y-bin ŷ_mean = `{top_y_bin:+.3f}` bps** (target ≥ 0): {'✓ PASS' if top_y_bin >= 0 else '✗ FAIL'}")
    md(f"- **Bottom y-bin ŷ_mean = `{bot_y_bin:+.3f}` bps** (target ≤ 0): {'✓ PASS' if bot_y_bin <= 0 else '✗ FAIL'}")
    md(f"- Bin-Spearman (calibration view): `{bin_S:+.4f}`")
    md(f"- **Calibration line passes through origin**: {'✓' if (top_y_bin > 0 and bot_y_bin < 0) else '✗'}")

    # 6. Trading view bin-S
    bin_S_trade = spearmanr(df_trade.yhat_mean_bps, df_trade.y_mean_bps).correlation
    md(f"\n## 6. Monotonicity — bin-Spearman")
    md(f"\n- Calibration view: `{bin_S:+.4f}`")
    md(f"- Trading view: `{bin_S_trade:+.4f}`")

    # 7. DirAcc
    md("\n## 7. Direction Accuracy")
    da_overall = directional_accuracy(y, q50)
    sigma_y = y.std()
    tail_mask = np.abs(y) > 2 * sigma_y
    da_tail = directional_accuracy(y[tail_mask], q50[tail_mask])
    md(f"\n- Overall: **{da_overall:.4f}**")
    md(f"- Tail (|y| > 2σ_y, n={tail_mask.sum():,}): **{da_tail:.4f}**")

    # 8. Residual AC
    md("\n## 8. Residual Auto-Correlation")
    resid = y - q50
    md("\n| lag | resid AC | ŷ AC | y AC |")
    md("|---:|---:|---:|---:|")
    for lag in [1, 5, 10, 30]:
        if len(resid) > lag:
            ac_r = float(np.corrcoef(resid[:-lag], resid[lag:])[0, 1])
            ac_q = float(np.corrcoef(q50[:-lag], q50[lag:])[0, 1])
            ac_y = float(np.corrcoef(y[:-lag], y[lag:])[0, 1])
            md(f"| {lag} | {ac_r:+.4f} | {ac_q:+.4f} | {ac_y:+.4f} |")

    # 9. Stability
    md("\n## 9. Per-fold Stability")
    md(f"\n- per-fold Pearson std: `{np.std(fold_p):.4f}` (CoV {np.std(fold_p)/np.mean(fold_p):.3f})")
    md(f"- per-fold Spearman std: `{np.std(fold_s):.4f}` (CoV {np.std(fold_s)/np.mean(fold_s):.3f})")

    # 10. Quantile coverage (uses raw q10/q90 since live calibration only adjusts q50)
    md("\n## 10. Quantile Coverage (raw q10/q90)")
    cov_q10 = float(np.mean(y < q10))
    cov_q90 = float(np.mean(y > q90))
    md(f"\n- P(y < q10) = `{cov_q10:.3f}` (target 0.10)")
    md(f"- P(y > q90) = `{cov_q90:.3f}` (target 0.10)")

    # Scorecard
    md("\n## 11. PASS/FAIL Scorecard (live-calibrated)")
    gates = {
        "Pearson > 0.04": p_pool >= 0.04,
        "Spearman > 0.04": s_pool >= 0.04,
        "Bootstrap CI Pearson > 0": (not np.isnan(p_lo)) and p_lo > 0,
        "Bootstrap CI Spearman > 0": (not np.isnan(s_lo)) and s_lo > 0,
        "β_y_on_ŷ in [0.5, 2.0]": 0.5 <= beta_y_on_q <= 2.0,
        "σŷ/σy ≥ 0.02": sigma_ratio >= 0.02,
        "|bias| < 0.05 bps (live should be near-zero)": abs(bias) < 0.05,
        "Top y-bin ŷ_mean > 0 (USER PRIMARY)": top_y_bin > 0,
        "Bottom y-bin ŷ_mean < 0 (USER PRIMARY)": bot_y_bin < 0,
        "Calibration line crosses origin": top_y_bin > 0 and bot_y_bin < 0,
        "Bin-Spearman calib ≥ 0.85": bin_S >= 0.85,
        "Bin-Spearman trade ≥ 0.85": bin_S_trade >= 0.85,
        "Tail DirAcc ≥ 0.52": da_tail >= 0.52,
        "Top-bot spread ≥ 1.0 bps": spread >= 1.0,
        "per-fold P CoV < 0.20": (np.std(fold_p) / np.mean(fold_p)) < 0.20,
    }
    md("\n| Gate | PASS |")
    md("|---|:-:|")
    for name, ok in gates.items():
        md(f"| {name} | {'✓' if ok else '✗'} |")
    pass_count = sum(gates.values())
    md(f"\n**Score: {pass_count} / {len(gates)} gates PASS**")

    out_path.write_text("\n".join(lines))
    print(f"→ {out_path}")
    print(f"\nScore: {pass_count}/{len(gates)} gates PASS")
    print(f"Top y-bin ŷ: {top_y_bin:+.3f} bps  Bot y-bin ŷ: {bot_y_bin:+.3f} bps")


if __name__ == "__main__":
    main()

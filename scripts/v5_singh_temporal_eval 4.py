"""Phase A — Temporal stability eval for V5 singh α=0+Huber predictions.

Exposes regime non-adaptation hidden by pool-level metrics. Computes:
  1. Monthly + weekly IC trajectory (worst period highlighted)
  2. Rolling 30d ŷ_mean vs y_mean correlation (regime adaptation proxy)
  3. Worst rolling 30-day IC
  4. Vol-regime stratified IC (3 buckets by realized vol)
  5. Static-prediction detector (var ratio: ŷ_mean variance / y_mean variance)

Operates on raw (uncalibrated) q50 — temporal eval should test the model
itself, not the EMA-demean overlay. Live-calibrated column tested separately.

Usage:
  python scripts/v5_singh_temporal_eval.py \
      --csv exports/v5_singh_alpha0_huber/y600_predictions_all_folds.csv \
      --out exports/v5_singh_alpha0_huber/STRICT_EVAL_TEMPORAL.md
"""
from __future__ import annotations
import argparse
import pathlib
import warnings

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

warnings.simplefilter("ignore", category=UserWarning)


def safe_pearson(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if len(a) < 30 or a.std() < 1e-12 or b.std() < 1e-12:
        return float("nan")
    return float(pearsonr(a, b)[0])


def safe_spearman(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if len(a) < 30:
        return float("nan")
    return float(spearmanr(a, b).correlation)


def compute_per_period(df, period_col, y_col="y_true_bps", q_col="y_pred_q50_bps"):
    """Per-period {Pearson, Spearman, n, ŷ_mean, y_mean, DirAcc}."""
    rows = []
    for p, g in df.groupby(period_col):
        if len(g) < 30:
            continue
        y = g[y_col].to_numpy()
        q = g[q_col].to_numpy()
        rows.append({
            "period": str(p),
            "n": len(g),
            "y_mean_bps": float(y.mean()),
            "yhat_mean_bps": float(q.mean()),
            "Pearson": safe_pearson(q, y),
            "Spearman": safe_spearman(q, y),
            "DirAcc": float(np.mean(np.sign(y) == np.sign(q))),
        })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df[df["mask"] == 1].copy()
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"])
    df = df.sort_values("datetime_utc").reset_index(drop=True)
    df["month"] = df["datetime_utc"].dt.to_period("M").astype(str)
    df["week"] = df["datetime_utc"].dt.to_period("W").astype(str)
    df["day"] = df["datetime_utc"].dt.date.astype(str)

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    md = lines.append

    md("# V5 singh α=0+Huber — Phase A Temporal Stability Evaluation")
    md(f"\n**Input:** `{args.csv}` ({len(df):,} valid samples)")
    md(f"**Time range:** {df['datetime_utc'].min()} → {df['datetime_utc'].max()}")
    md("**Model output column:** `y_pred_q50_bps` (raw, uncalibrated). Live calibration tested separately.\n")

    # ---------- 1. Monthly IC trajectory ----------
    md("## 1. Monthly IC trajectory")
    monthly = compute_per_period(df, "month")
    md("\n| Month | n | y_mean | ŷ_mean | Pearson | Spearman | DirAcc |")
    md("|---|---:|---:|---:|---:|---:|---:|")
    for _, r in monthly.iterrows():
        md(f"| {r.period} | {int(r.n):,} | {r.y_mean_bps:+.3f} | {r.yhat_mean_bps:+.3f} | {r.Pearson:+.4f} | {r.Spearman:+.4f} | {r.DirAcc:.3f} |")

    md(f"\n**Worst-month Pearson:** `{monthly.Pearson.min():+.4f}` ({monthly.loc[monthly.Pearson.idxmin(), 'period']})")
    md(f"**Worst-month Spearman:** `{monthly.Spearman.min():+.4f}` ({monthly.loc[monthly.Spearman.idxmin(), 'period']})")
    md(f"**Best-month Pearson:** `{monthly.Pearson.max():+.4f}` ({monthly.loc[monthly.Pearson.idxmax(), 'period']})")
    md(f"**Pearson std across months:** `{monthly.Pearson.std():.4f}` (CoV {monthly.Pearson.std()/monthly.Pearson.mean():.3f})")
    md(f"**Spearman std across months:** `{monthly.Spearman.std():.4f}` (CoV {monthly.Spearman.std()/monthly.Spearman.mean():.3f})")
    md(f"**Months with Pearson < 0.03:** {(monthly.Pearson < 0.03).sum()} / {len(monthly)}")

    # ---------- 2. Regime adaptation: rolling 30d ŷ_mean vs y_mean ----------
    md("\n## 2. Regime adaptation — rolling-mean correlation")
    md("\nDoes ŷ_mean track y_mean over time? Strong correlation = model adapts to regime.")

    # Compute per-day mean (smaller noise than per-sample), then rolling
    daily = df.groupby("day").agg(
        y_mean=("y_true_bps", "mean"),
        yhat_mean=("y_pred_q50_bps", "mean"),
        n=("y_true_bps", "size"),
    ).reset_index()
    daily["day_dt"] = pd.to_datetime(daily["day"])

    # Rolling 30-day means
    daily = daily.sort_values("day_dt").reset_index(drop=True)
    daily["roll30_y"] = daily["y_mean"].rolling(window=30, min_periods=15).mean()
    daily["roll30_yhat"] = daily["yhat_mean"].rolling(window=30, min_periods=15).mean()

    md(f"\nDaily n: {len(daily)} days. Rolling 30-day window applied.")
    valid = daily.dropna(subset=["roll30_y", "roll30_yhat"])
    if len(valid) >= 30:
        regime_corr = float(np.corrcoef(valid.roll30_y, valid.roll30_yhat)[0, 1])
        md(f"\n**Rolling 30d ŷ_mean ↔ y_mean correlation: `{regime_corr:+.4f}`**")
        md(f"- Target for regime adaptation: ≥ 0.3 ✓")
        md(f"- 0.0 ~ 0.1: model does not adapt to regime")
        md(f"- < 0: model adapts in WRONG direction")

        # Show subset of rolling means
        md(f"\n5-row sample (rolling 30d means, bps):")
        md("| day | roll30_y | roll30_ŷ |")
        md("|---|---:|---:|")
        for _, r in valid.iloc[::max(1, len(valid)//5)].head(6).iterrows():
            md(f"| {r.day} | {r.roll30_y:+.4f} | {r.roll30_yhat:+.4f} |")

    # ---------- 3. Worst rolling 30-day IC ----------
    md("\n## 3. Worst rolling 30-day Pearson")
    md("\nFor each day, compute Pearson over [day-30, day] window. Find worst.")
    # Strip tz for comparison consistency
    df["dt_naive"] = df["datetime_utc"].dt.tz_localize(None)
    days_sorted = sorted(daily["day_dt"].unique())
    rolling_p = []
    for d in days_sorted:
        d_ts = pd.Timestamp(d)
        window_start = d_ts - pd.Timedelta(days=30)
        sub = df[(df.dt_naive >= window_start) & (df.dt_naive <= d_ts)]
        if len(sub) >= 200:
            p = safe_pearson(sub["y_pred_q50_bps"], sub["y_true_bps"])
            rolling_p.append({"day": str(d_ts.date()), "n": len(sub), "Pearson": p})
    rolling_p = pd.DataFrame(rolling_p).dropna()
    if len(rolling_p) > 0:
        md(f"\n**Worst rolling-30d Pearson: `{rolling_p.Pearson.min():+.4f}`** ({rolling_p.loc[rolling_p.Pearson.idxmin(), 'day']})")
        md(f"**Best rolling-30d Pearson: `{rolling_p.Pearson.max():+.4f}`** ({rolling_p.loc[rolling_p.Pearson.idxmax(), 'day']})")
        md(f"**Days with rolling-30d Pearson < 0.03:** {(rolling_p.Pearson < 0.03).sum()} / {len(rolling_p)} ({100*(rolling_p.Pearson < 0.03).mean():.1f}%)")
        md(f"**Days with rolling-30d Pearson < 0:** {(rolling_p.Pearson < 0).sum()} / {len(rolling_p)} ({100*(rolling_p.Pearson < 0).mean():.1f}%)")

    # ---------- 4. Vol-regime stratified IC ----------
    md("\n## 4. Vol-regime stratified IC")
    md("\nSplit samples by absolute realized return into 3 vol buckets, report IC per bucket.")
    df["abs_y"] = df["y_true_bps"].abs()
    vol_qlo, vol_qhi = df.abs_y.quantile([1/3, 2/3])
    df["vol_bucket"] = pd.cut(
        df["abs_y"], bins=[-1, vol_qlo, vol_qhi, 1e9],
        labels=["low_vol", "mid_vol", "high_vol"],
    )
    md(f"\nVol bucket cutoffs: [low ≤ {vol_qlo:.2f}, mid ≤ {vol_qhi:.2f}, high > {vol_qhi:.2f}] bps |y|.")
    md("\n| Bucket | n | y_mean | ŷ_mean | Pearson | Spearman |")
    md("|---|---:|---:|---:|---:|---:|")
    for bucket in ["low_vol", "mid_vol", "high_vol"]:
        sub = df[df.vol_bucket == bucket]
        y, q = sub.y_true_bps.to_numpy(), sub.y_pred_q50_bps.to_numpy()
        md(f"| {bucket} | {len(sub):,} | {y.mean():+.3f} | {q.mean():+.3f} | {safe_pearson(q,y):+.4f} | {safe_spearman(q,y):+.4f} |")

    # ---------- 5. Static-prediction detector ----------
    md("\n## 5. Static-prediction detector")
    md("\nIf model adapts, monthly ŷ_mean variance should be commensurate with monthly y_mean variance scaled by ρ.\n"
       "Specifically: `var(monthly_ŷ_mean) / var(monthly_y_mean)` should be ≈ ρ² ~ 0.005 (since ρ ~ 0.07).\n"
       "Much smaller → model output is too static (doesn't adapt). Much larger → over-extrapolating.")

    var_y = monthly.y_mean_bps.var()
    var_yhat = monthly.yhat_mean_bps.var()
    var_ratio = var_yhat / max(var_y, 1e-12)
    md(f"\n- var(monthly y_mean): `{var_y:.4f}` bps²")
    md(f"- var(monthly ŷ_mean): `{var_yhat:.4f}` bps²")
    md(f"- **Ratio (ŷ/y): `{var_ratio:.4f}`** (target ≥ ρ² ~ 0.005)")
    if var_ratio < 0.001:
        md("- ❌ Model output is essentially static across months — no regime adaptation")
    elif var_ratio < 0.005:
        md("- ⚠️ Model output adapts WEAKLY")
    elif var_ratio <= 0.05:
        md("- ✓ Model output adapts proportionally to ρ")
    else:
        md("- ⚠️ Model output adapts STRONGLY (may over-extrapolate)")

    # ---------- 6. Summary scorecard ----------
    md("\n## 6. Temporal scorecard")
    gates = {
        "Worst-month Pearson > 0.03": monthly.Pearson.min() > 0.03,
        "Worst-month Spearman > 0.03": monthly.Spearman.min() > 0.03,
        "Months with P > 0.03: ≥ 80%": (monthly.Pearson > 0.03).mean() >= 0.8,
        "Pearson CoV < 0.5": (monthly.Pearson.std() / monthly.Pearson.mean()) < 0.5,
        "Regime adaptation corr ≥ 0.3": (regime_corr if 'regime_corr' in dir() else 0) >= 0.3,
        "Worst rolling-30d P > 0.02": (rolling_p.Pearson.min() if len(rolling_p) > 0 else 0) > 0.02,
        "Days with rolling-30d P < 0: ≤ 5%": ((rolling_p.Pearson < 0).mean() if len(rolling_p) > 0 else 1) <= 0.05,
        "Static-detector ratio in [0.005, 0.05]": 0.005 <= var_ratio <= 0.05,
        "Vol regime: all 3 buckets P > 0.04": all(
            safe_pearson(df[df.vol_bucket==b].y_pred_q50_bps, df[df.vol_bucket==b].y_true_bps) > 0.04
            for b in ["low_vol", "mid_vol", "high_vol"]
        ),
    }
    md("\n| Gate | PASS |")
    md("|---|:-:|")
    for k, v in gates.items():
        md(f"| {k} | {'✓' if v else '✗'} |")
    pass_n = sum(gates.values())
    md(f"\n**Score: {pass_n} / {len(gates)} gates PASS**")

    out_path.write_text("\n".join(lines))
    print(f"→ {out_path}")
    print(f"\nTemporal score: {pass_n}/{len(gates)} gates PASS")
    print(f"Worst-month P: {monthly.Pearson.min():+.4f}")
    print(f"Regime adapt corr: {regime_corr if 'regime_corr' in dir() else 'N/A'}")
    print(f"Static-detector ratio: {var_ratio:.4f}")


if __name__ == "__main__":
    main()

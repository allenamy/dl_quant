"""Phase A.5.1 — Feature audit: do existing 64 features carry regime info?

For each of 64 features (X) + 6 regime_prior features:
  1. Aggregate per day (mean / median) over all samples
  2. Compute correlation with NEXT-30-day y_600 mean (causal: only use t < window_start)
  3. Rank features by |corr| with rolling future y_mean

If any feature has |corr| > 0.10 with future regime → architecture issue
  (model has access but doesn't use)
If all features have |corr| < 0.05 → feature issue
  (need new lookback features)

Also computes per-day median y_600 to verify regime exists in train period.

Output: docs/Y600_REGIME_FEATURE_AUDIT.md
"""
from __future__ import annotations
import argparse
import pathlib
from typing import List

import numpy as np
import pandas as pd
from scipy.stats import pearsonr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz-dir", default="data/npz_v4")
    ap.add_argument("--out", default="docs/Y600_REGIME_FEATURE_AUDIT.md")
    ap.add_argument("--start-date", default="2024-01-01",
                    help="audit period start (use train tail for relevance)")
    ap.add_argument("--end-date", default="2025-09-09",
                    help="audit period end")
    args = ap.parse_args()

    npz_dir = pathlib.Path(args.npz_dir)
    days = sorted(p.stem for p in npz_dir.glob("20??-??-??.npz"))
    days = [d for d in days if args.start_date <= d <= args.end_date]
    print(f"Audit period: {days[0]} → {days[-1]}, n={len(days)} days")

    # Load feature names from one day
    sample = np.load(npz_dir / f"{days[0]}.npz", allow_pickle=True)
    feature_names: List[str] = [
        n.decode() if isinstance(n, bytes) else str(n)
        for n in sample["features"]
    ]
    n_features = len(feature_names)
    print(f"Features per sample: {n_features}")

    # Per-day aggregation: mean over all samples × all timesteps for each feature
    # Plus per-day y_600 mean (using y_mask)
    rows = []
    for d in days:
        try:
            arr = np.load(npz_dir / f"{d}.npz", allow_pickle=True)
            X = arr["X"]  # (N_samples, T, n_features)
            y = arr["y_600"]
            m = arr["y_mask_600"].astype(bool)

            # Aggregate features: mean over (samples × timesteps), valid samples only
            # For simplicity, mean over all samples (no per-sample mask on features)
            X_day = X.mean(axis=(0, 1))  # (n_features,)
            y_day = float(y[m & np.isfinite(y)].mean()) if m.any() else float("nan")
            n_valid = int(m.sum())

            # Also regime_prior (per-sample, mean over samples)
            rp = arr["regime_prior"].mean(axis=0) if arr["regime_prior"].ndim == 2 else arr["regime_prior"].mean()

            row = {"day": d, "y_600_mean": y_day, "n_valid": n_valid}
            for i, name in enumerate(feature_names):
                row[f"feat_{i:02d}_{name}"] = float(X_day[i])
            for i, v in enumerate(np.atleast_1d(rp)):
                row[f"rp_{i}"] = float(v)
            rows.append(row)
        except Exception as e:
            print(f"  skip {d}: {e}")
            continue

    daily = pd.DataFrame(rows).dropna(subset=["y_600_mean"])
    print(f"Loaded {len(daily)} days with valid y_600.")

    # Compute next-30-day y mean (causal forward window)
    daily = daily.sort_values("day").reset_index(drop=True)
    daily["y_next30_mean"] = daily["y_600_mean"][::-1].rolling(window=30, min_periods=15).mean()[::-1].shift(-1)
    # Equivalent: for each day d, mean(y_600 from day d+1 to day d+30)
    # Simpler: compute as forward rolling
    fwd = []
    for i in range(len(daily)):
        end = min(i + 30, len(daily))
        if end - i >= 15:
            fwd.append(daily["y_600_mean"].iloc[i + 1:end].mean() if end > i + 1 else float("nan"))
        else:
            fwd.append(float("nan"))
    daily["y_next30_mean"] = fwd

    # Filter rows with valid forward window
    valid = daily.dropna(subset=["y_next30_mean"])
    print(f"Valid rows for forward correlation: {len(valid)}")

    # Compute corr of each feature with y_next30_mean
    feature_cols = [c for c in daily.columns if c.startswith("feat_") or c.startswith("rp_")]
    corrs = {}
    for c in feature_cols:
        x = valid[c].values
        y = valid["y_next30_mean"].values
        if x.std() < 1e-9:
            corrs[c] = 0.0
            continue
        try:
            corrs[c] = float(pearsonr(x, y)[0])
        except Exception:
            corrs[c] = float("nan")

    corr_df = pd.DataFrame([
        {"feature": c, "corr_with_y_next30": v, "abs_corr": abs(v)}
        for c, v in corrs.items()
    ]).sort_values("abs_corr", ascending=False)

    # Write report
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    md = lines.append

    md("# Phase A.5.1 — V5 Singh Feature Regime-Adaptation Audit")
    md(f"\n**Audit period:** {days[0]} → {days[-1]} ({len(daily)} days, {len(valid)} with forward window)")
    md(f"**Question:** Do existing 64 features (or 6 regime_prior) at daily-aggregation level predict next-30-day y_600 mean?")
    md(f"**Method:** For each feature, compute Pearson(daily_mean(feature), next_30d_y_mean). All causal (uses t-end < forward window start).")
    md(f"\n**Hypothesis:**")
    md(f"- If any feature |corr| ≥ 0.10: existing input has regime info → ARCHITECTURE issue (model can't use additive baseline)")
    md(f"- If all |corr| < 0.05: regime info missing → FEATURE issue (need lookback features)")
    md(f"- 0.05-0.10 region: marginal, prefer architecture fix\n")

    md("## Top 20 features by |corr| with next-30d y_mean\n")
    md("| Rank | Feature | corr | |corr| |")
    md("|---:|---|---:|---:|")
    for rank, (_, r) in enumerate(corr_df.head(20).iterrows(), start=1):
        md(f"| {rank} | `{r.feature}` | {r.corr_with_y_next30:+.4f} | {r.abs_corr:.4f} |")

    md(f"\n## Statistics\n")
    md(f"- **Max |corr|:** `{corr_df.abs_corr.max():.4f}` (feature: `{corr_df.iloc[0]['feature']}`)")
    md(f"- **Median |corr|:** `{corr_df.abs_corr.median():.4f}`")
    md(f"- **Features with |corr| ≥ 0.10:** {(corr_df.abs_corr >= 0.10).sum()} / {len(corr_df)}")
    md(f"- **Features with |corr| ≥ 0.05:** {(corr_df.abs_corr >= 0.05).sum()} / {len(corr_df)}")
    md(f"- **Mean |corr|:** `{corr_df.abs_corr.mean():.4f}`\n")

    # Diagnostic
    max_abs = corr_df.abs_corr.max()
    md("## Diagnostic\n")
    if max_abs >= 0.10:
        md(f"**Architecture issue likely**: {(corr_df.abs_corr >= 0.10).sum()} features carry regime info but model output is regime-anti-correlated (-0.21).")
        md(f"PPNetGate is multiplicative-only (gates magnitude, can't shift baseline). Need additive head bias from regime features.")
    elif max_abs >= 0.05:
        md(f"**Marginal**: top |corr| = {max_abs:.3f}. Architecture fix could help, but feature engineering also useful.")
    else:
        md(f"**Feature issue confirmed**: top |corr| = {max_abs:.3f}, all features near-uncorrelated with future regime.")
        md(f"Need new lookback features (recent_y_mean / recent_y_vol / recent_funding_rate / etc.).")

    # Also compute baseline: just using past y_600 itself
    md("\n## Baseline: past y_600 as feature\n")
    daily["y_600_past_30d"] = daily["y_600_mean"].rolling(window=30, min_periods=15).mean()
    valid_past = daily.dropna(subset=["y_next30_mean", "y_600_past_30d"])
    if len(valid_past) >= 30:
        c = float(pearsonr(valid_past["y_600_past_30d"], valid_past["y_next30_mean"])[0])
        md(f"- Past 30-day y_600_mean → next 30-day y_600_mean: corr = `{c:+.4f}`")
        md(f"  - This is the SIMPLEST regime feature. Should be ≥ 0.20 for regime to be predictable.\n")
    daily["y_600_past_7d"] = daily["y_600_mean"].rolling(window=7, min_periods=4).mean()
    valid_past7 = daily.dropna(subset=["y_next30_mean", "y_600_past_7d"])
    if len(valid_past7) >= 30:
        c7 = float(pearsonr(valid_past7["y_600_past_7d"], valid_past7["y_next30_mean"])[0])
        md(f"- Past 7-day y_600_mean → next 30-day y_600_mean: corr = `{c7:+.4f}`\n")

    out_path.write_text("\n".join(lines))
    print(f"\n→ {out_path}")
    print(f"Top 5 features by |corr|:")
    for _, r in corr_df.head(5).iterrows():
        print(f"  {r.feature}: {r.corr_with_y_next30:+.4f}")
    print(f"\nMax |corr|: {corr_df.abs_corr.max():.4f}")
    print(f"Features with |corr| ≥ 0.10: {(corr_df.abs_corr >= 0.10).sum()}")
    print(f"Features with |corr| ≥ 0.05: {(corr_df.abs_corr >= 0.05).sum()}")


if __name__ == "__main__":
    main()

"""Diagnostic plots + regime-stratified eval for v5push ensemble.

Generates:
- E[ŷ|y_decile] bin-plot (monotonicity check)
- Regime-stratified IC by realized vol tercile
- Per-fold breakdown
- Bootstrap CI on pooled metrics (block bootstrap)

Usage:
    python scripts/v5push_diagnostic_plots.py \
        --csv exports/v5push_ensemble_track_a_v5prod/y600_predictions_ensemble_w040.csv \
        --out-dir reports/v5push_ensemble_w040
"""
from __future__ import annotations
import argparse
import json
import pathlib
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


def block_bootstrap_ic(q, y, n_boot=1000, block=60, seed=0):
    rng = np.random.default_rng(seed)
    n = len(q)
    n_blocks = (n + block - 1) // block
    Ps, Ss = [], []
    for _ in range(n_boot):
        starts = rng.integers(0, max(1, n - block + 1), size=n_blocks)
        idx = np.concatenate([np.arange(s, min(s + block, n)) for s in starts])[:n]
        Ps.append(pearsonr(q[idx], y[idx])[0])
        Ss.append(spearmanr(q[idx], y[idx]).correlation)
    return (np.percentile(Ps, [2.5, 50, 97.5]), np.percentile(Ss, [2.5, 50, 97.5]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df[(df["mask"] == 1) & (df["warmup"] == False)].copy()
    print(f"n={len(df):,}")

    y = df["y_true_bps"].values
    q = df["y_pred_q50_bps_live"].values
    folds = df["fold"].values

    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Pooled metrics
    P = pearsonr(q, y)[0]
    S = spearmanr(q, y).correlation
    sq, sy = q.std(), y.std()
    beta = np.cov(q, y)[0, 1] / max(sq ** 2, 1e-12)
    bias = q.mean() - y.mean()
    da_all = float(np.mean(np.sign(q) == np.sign(y)))
    hy = np.abs(y) > sy
    da_hy = float(np.mean(np.sign(q[hy]) == np.sign(y[hy])))
    abs_thr = np.percentile(np.abs(q), 90)
    top_mask = np.abs(q) >= abs_thr
    top_spread = float((np.sign(q[top_mask]) * y[top_mask]).mean())

    # 2. Bin-monotonicity: E[ŷ|y_decile]
    deciles = np.percentile(y, np.linspace(0, 100, 11))
    bin_records = []
    for i in range(10):
        mask = (y >= deciles[i]) & (y <= deciles[i + 1])
        if mask.sum() > 0:
            bin_records.append({
                "decile": i + 1,
                "y_mean_bps": float(y[mask].mean()),
                "q_mean_bps": float(q[mask].mean()),
                "n": int(mask.sum()),
                "dir_acc": float(np.mean(np.sign(q[mask]) == np.sign(y[mask]))),
            })
    bin_df = pd.DataFrame(bin_records)
    bin_df.to_csv(out / "bin_plot.csv", index=False)
    bin_mono = spearmanr(bin_df["y_mean_bps"], bin_df["q_mean_bps"]).correlation
    print(f"Bin monotonicity (ρ): {bin_mono:+.3f}")
    print(bin_df.to_string())

    # 3. Regime-stratified by realized vol (use |y| as crude vol proxy per sample)
    # Better: rolling vol from y, but we don't have time. Use |y| terciles.
    vol_proxy = np.abs(y)
    vol_lo = np.percentile(vol_proxy, 33.3)
    vol_hi = np.percentile(vol_proxy, 66.7)
    regimes = np.where(vol_proxy <= vol_lo, "lo",
                       np.where(vol_proxy <= vol_hi, "mid", "hi"))
    regime_records = []
    for r in ["lo", "mid", "hi"]:
        m = regimes == r
        if m.sum() < 100:
            continue
        Pr = pearsonr(q[m], y[m])[0]
        Sr = spearmanr(q[m], y[m]).correlation
        dar = float(np.mean(np.sign(q[m]) == np.sign(y[m])))
        regime_records.append({
            "regime": r, "n": int(m.sum()),
            "P": Pr, "S": Sr, "DirAcc": dar,
            "y_abs_mean_bps": float(vol_proxy[m].mean()),
        })
    regime_df = pd.DataFrame(regime_records)
    regime_df.to_csv(out / "regime_stratified.csv", index=False)
    print(f"\nRegime stratified:")
    print(regime_df.to_string())

    # 4. Per-fold
    fold_records = []
    for f in range(3):
        m = folds == f
        if m.sum() == 0:
            continue
        Pf = pearsonr(q[m], y[m])[0]
        Sf = spearmanr(q[m], y[m]).correlation
        sqf, syf = q[m].std(), y[m].std()
        betaf = np.cov(q[m], y[m])[0, 1] / max(sqf ** 2, 1e-12)
        daf = float(np.mean(np.sign(q[m]) == np.sign(y[m])))
        hyf = np.abs(y[m]) > syf
        dahyf = float(np.mean(np.sign(q[m][hyf]) == np.sign(y[m][hyf])))
        fold_records.append({
            "fold": f, "n": int(m.sum()),
            "P": Pf, "S": Sf, "beta": betaf,
            "sigma_ratio": sqf / syf, "DirAcc_all": daf,
            "DirAcc_high_y": dahyf,
        })
    fold_df = pd.DataFrame(fold_records)
    fold_df.to_csv(out / "per_fold.csv", index=False)
    print(f"\nPer-fold:")
    print(fold_df.to_string())

    # 5. Bootstrap CI (pooled)
    Pci, Sci = block_bootstrap_ic(q, y, n_boot=500, block=60, seed=42)

    summary = {
        "n_samples": int(len(y)),
        "pooled": {
            "Pearson": float(P), "Pearson_CI95": [float(Pci[0]), float(Pci[2])],
            "Spearman": float(S), "Spearman_CI95": [float(Sci[0]), float(Sci[2])],
            "beta": float(beta), "sigma_ratio": float(sq / sy),
            "bias_bps": float(bias),
            "DirAcc_all": float(da_all), "DirAcc_high_y": float(da_hy),
            "TopDecileSpread_bps": float(top_spread),
            "bin_monotonicity": float(bin_mono),
        },
        "regime_stratified": regime_records,
        "per_fold": fold_records,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n=== POOLED ===")
    print(f"  P={P:+.4f} (CI95 [{Pci[0]:+.4f},{Pci[2]:+.4f}])")
    print(f"  S={S:+.4f} (CI95 [{Sci[0]:+.4f},{Sci[2]:+.4f}])")
    print(f"  β={beta:+.3f} σŷ/σy={sq / sy:.3f} bias={bias:+.3f}bps")
    print(f"  DA_all={da_all:.4f} DA_|y|>σ={da_hy:.4f} TopSpread={top_spread:+.3f}bps")
    print(f"  BinMono={bin_mono:+.3f}")
    print(f"\nSummary written to {out / 'summary.json'}")


if __name__ == "__main__":
    main()

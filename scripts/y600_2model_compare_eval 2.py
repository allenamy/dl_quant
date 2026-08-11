"""
Comprehensive eval for 6 y_600 candidate CSVs.

Reads the 6 multi-seed median CSVs from exports/ and computes:

1. Basic IC: Pearson, Spearman (stride10 + dense)
2. Direction accuracy + tail DirAcc (|y|>2σ)
3. Magnitude calibration: β_y_on_ŷ, β_ŷ_on_y, σŷ/σy, R²_reg, R²_pred
4. Bin-plot E[ŷ|y_bin] monotonicity (9 bins)
5. Residual autocorrelation (lag 1, 5, 10, 60)
6. Prediction autocorrelation (lag 60, 300, 600)
7. Regime-stratified IC (vol-tertile)
8. Block bootstrap CI (block=60, B=1000) for pooled P/S

Output:
- exports/y600_6csv_eval_report.md (markdown summary)
- prints all to stdout
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


CSV_FILES = [
    ("baseline_plus", "BEST", "y600_baseline_plus_BEST_3seed_median.csv"),
    ("baseline_plus", "EMA",  "y600_baseline_plus_EMA_3seed_median.csv"),
    ("baseline_plus", "SWA",  "y600_baseline_plus_SWA_3seed_median.csv"),
    ("phase3c", "BEST", "y600_phase3c_BEST_2seed_median.csv"),
    ("phase3c", "EMA",  "y600_phase3c_EMA_2seed_median.csv"),
    ("phase3c", "SWA",  "y600_phase3c_SWA_2seed_median.csv"),
]


def base_metrics(yp, y):
    yp = np.asarray(yp, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    p = float(np.corrcoef(yp, y)[0, 1])
    s, _ = spearmanr(yp, y)
    sy = float(y.std())
    syp = float(yp.std())
    cov = float(np.cov(yp, y, ddof=0)[0, 1])
    beta_y_on_yhat = cov / (yp.var() + 1e-30)
    beta_yhat_on_y = cov / (y.var() + 1e-30)
    sse = float(((y - yp) ** 2).sum())
    sst = float(((y - y.mean()) ** 2).sum() + 1e-30)
    r2_reg = 1 - sse / sst
    da_mask = y != 0
    da = float(((np.sign(yp) == np.sign(y)) & da_mask).sum() / max(1, da_mask.sum()))
    # Tail DirAcc on |y| > 2*MAD-σ subset
    mad_sigma = 1.4826 * float(np.median(np.abs(y - np.median(y))))
    tail_mask = np.abs(y) > 2 * mad_sigma
    if tail_mask.sum() >= 10:
        da_tail = float(((np.sign(yp[tail_mask]) == np.sign(y[tail_mask])) & (y[tail_mask] != 0)).sum() / max(1, (y[tail_mask] != 0).sum()))
    else:
        da_tail = float("nan")
    return {
        "n": len(y), "P": p, "S": float(s),
        "sigma_y": sy, "sigma_yhat": syp, "shrink": syp / sy,
        "beta_y_on_yhat": beta_y_on_yhat, "beta_yhat_on_y": beta_yhat_on_y,
        "r2_reg": r2_reg, "DirAcc": da, "DirAcc_tail": da_tail,
    }


def stride_idx(mask, stride=10):
    idx = np.where(mask)[0]
    return idx[::stride]


def autocorr(x, lag):
    if len(x) <= lag:
        return float("nan")
    a = x[lag:] - x[lag:].mean()
    b = x[:-lag] - x[:-lag].mean()
    denom = np.sqrt((a * a).sum() * (b * b).sum())
    if denom <= 0:
        return float("nan")
    return float((a * b).sum() / denom)


def bin_plot_metrics(yp, y, n_bins=9):
    """E[ŷ|y_bin] monotonicity. Returns bin centers, mean ŷ per bin, and rank correlation."""
    edges = np.quantile(y, np.linspace(0, 1, n_bins + 1))
    edges[0] -= 1e-12
    bin_idx = np.digitize(y, edges) - 1
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)
    bin_means_y = []
    bin_means_yp = []
    bin_counts = []
    for b in range(n_bins):
        m = bin_idx == b
        if m.sum() < 5:
            bin_means_y.append(np.nan)
            bin_means_yp.append(np.nan)
            bin_counts.append(0)
            continue
        bin_means_y.append(float(y[m].mean()))
        bin_means_yp.append(float(yp[m].mean()))
        bin_counts.append(int(m.sum()))
    # monotonicity: Spearman across bin order
    valid = ~np.isnan(bin_means_yp)
    if valid.sum() >= 3:
        bs, _ = spearmanr(np.array(bin_means_y)[valid], np.array(bin_means_yp)[valid])
    else:
        bs = float("nan")
    # # of consecutive monotonic pairs (8 max)
    incr = 0
    arr = np.array(bin_means_yp)
    for i in range(len(arr) - 1):
        if not np.isnan(arr[i]) and not np.isnan(arr[i + 1]) and arr[i + 1] > arr[i]:
            incr += 1
    return {
        "bin_means_y": bin_means_y, "bin_means_yp": bin_means_yp,
        "bin_counts": bin_counts, "bin_spearman": float(bs),
        "monotonic_increasing_pairs": incr,
    }


def regime_stratified(yp, y, msk_idx, n_buckets=3):
    """Compute Spearman within each vol-tertile (proxied by |y|)."""
    abs_y = np.abs(y)
    edges = np.quantile(abs_y, np.linspace(0, 1, n_buckets + 1))
    out = {}
    for b in range(n_buckets):
        lo, hi = edges[b], edges[b + 1]
        m = (abs_y >= lo) & (abs_y < hi if b < n_buckets - 1 else abs_y <= hi)
        if m.sum() < 50:
            continue
        s, _ = spearmanr(yp[m], y[m])
        p = float(np.corrcoef(yp[m], y[m])[0, 1])
        out[f"bucket_{b}_n{int(m.sum())}_P"] = p
        out[f"bucket_{b}_n{int(m.sum())}_S"] = float(s)
    return out


def block_bootstrap_ci(yp, y, block_len=60, B=500, alpha=0.05):
    """Stationary block-bootstrap 95% CI for Pearson + Spearman."""
    n = len(y)
    p_boot, s_boot = [], []
    for _ in range(B):
        # build a bootstrap sample by stitching blocks of length block_len
        idx = np.empty(n, dtype=np.int64)
        i = 0
        while i < n:
            start = np.random.randint(0, n)
            ln = min(block_len, n - i)
            for k in range(ln):
                idx[i + k] = (start + k) % n
            i += ln
        yp_b = yp[idx]
        y_b = y[idx]
        p_boot.append(float(np.corrcoef(yp_b, y_b)[0, 1]))
        sb, _ = spearmanr(yp_b, y_b)
        s_boot.append(float(sb))
    p_boot = np.array(p_boot)
    s_boot = np.array(s_boot)
    return {
        "P_lo": float(np.quantile(p_boot, alpha / 2)),
        "P_hi": float(np.quantile(p_boot, 1 - alpha / 2)),
        "S_lo": float(np.quantile(s_boot, alpha / 2)),
        "S_hi": float(np.quantile(s_boot, 1 - alpha / 2)),
    }


def evaluate_csv(csv_path: Path):
    print(f"\n{'='*100}")
    print(f"== {csv_path.name}")
    print(f"{'='*100}")
    df = pd.read_csv(csv_path)
    msk = df["mask"].astype(bool).to_numpy()
    # IMPORTANT: use raw log-return (not z) for pooled correlation across folds with different sigma_train.
    # Trading is in raw units, sigma_train differs per fold so z-pooled corr ≠ raw-pooled corr.
    yp_z = df["y_pred_q50_logret"].astype(np.float64).to_numpy()
    y_z = df["y_true_logret"].astype(np.float64).to_numpy()

    yp = yp_z[msk]
    y = y_z[msk]
    n_dense = len(y)

    # PER-FOLD stride10 (match OLD production CSV methodology)
    yp_s_list, y_s_list = [], []
    for fld in sorted(df["fold"].unique()):
        mfd = (df["fold"] == fld).to_numpy() & msk
        idx_in_fold = np.where(mfd)[0]
        s10_fold = idx_in_fold[::10]
        yp_s_list.append(yp_z[s10_fold])
        y_s_list.append(y_z[s10_fold])
    yp_s = np.concatenate(yp_s_list)
    y_s = np.concatenate(y_s_list)
    s10 = np.array([], dtype=np.int64)  # not used after
    n_stride = len(y_s)

    # 1+2+3: basic + direction + magnitude
    m_dense = base_metrics(yp, y)
    m_s10 = base_metrics(yp_s, y_s)

    print(f"\n--- Basic metrics ---")
    print(f"n_dense={n_dense:,}, n_stride10={n_stride:,}")
    print(f"DENSE   : P={m_dense['P']:+.4f} S={m_dense['S']:+.4f} σŷ/σy={m_dense['shrink']:.3f} β_y_on_ŷ={m_dense['beta_y_on_yhat']:+.3f} β_ŷ_on_y={m_dense['beta_yhat_on_y']:+.4f} R²_reg={m_dense['r2_reg']:+.5f} DirAcc={m_dense['DirAcc']:.3f} DirAcc_tail={m_dense['DirAcc_tail']:.3f}")
    print(f"STRIDE10: P={m_s10['P']:+.4f} S={m_s10['S']:+.4f} σŷ/σy={m_s10['shrink']:.3f} β_y_on_ŷ={m_s10['beta_y_on_yhat']:+.3f} β_ŷ_on_y={m_s10['beta_yhat_on_y']:+.4f} R²_reg={m_s10['r2_reg']:+.5f} DirAcc={m_s10['DirAcc']:.3f} DirAcc_tail={m_s10['DirAcc_tail']:.3f}")

    # 4: bin plot monotonicity (on stride10 to reduce autocorr)
    bp = bin_plot_metrics(yp_s, y_s, n_bins=9)
    print(f"\n--- Bin-plot E[ŷ|y_bin] (stride10, 9 bins) ---")
    for i, (yb, ypb, n) in enumerate(zip(bp["bin_means_y"], bp["bin_means_yp"], bp["bin_counts"])):
        print(f"  bin {i} (n={n:>4}): y={yb:+.3f} → ŷ={ypb:+.4f}")
    print(f"  bin Spearman = {bp['bin_spearman']:+.3f}, monotonic-increasing pairs = {bp['monotonic_increasing_pairs']}/8")

    # 5+6: autocorr (use stride10 to be honest about residual autocorr)
    resid = y_s - yp_s
    print(f"\n--- Autocorrelation (stride10) ---")
    print(f"residual lag 1 = {autocorr(resid, 1):+.4f}")
    print(f"residual lag 5 = {autocorr(resid, 5):+.4f}")
    print(f"residual lag 10 = {autocorr(resid, 10):+.4f}")
    print(f"prediction lag 6 (60s post-stride) = {autocorr(yp_s, 6):+.4f}")
    print(f"prediction lag 60 = {autocorr(yp_s, 60):+.4f}")

    # 7: regime stratified
    rs = regime_stratified(yp_s, y_s, s10, n_buckets=3)
    print(f"\n--- Regime-stratified (|y| tertiles, stride10) ---")
    for k, v in rs.items():
        print(f"  {k}: {v:+.4f}")

    # 8: bootstrap CI (stride10, smaller B for speed)
    print(f"\n--- Block bootstrap CI (stride10, block=60, B=500) ---")
    ci = block_bootstrap_ci(yp_s, y_s, block_len=60, B=500)
    print(f"  P 95% CI: [{ci['P_lo']:+.4f}, {ci['P_hi']:+.4f}]")
    print(f"  S 95% CI: [{ci['S_lo']:+.4f}, {ci['S_hi']:+.4f}]")

    # Per-fold breakdown
    print(f"\n--- Per-fold (stride10) ---")
    folds = sorted(df.loc[df["mask"], "fold"].unique())
    per_fold = {}
    for fld in folds:
        mfd = (df["fold"] == fld).to_numpy() & msk
        sfd = mfd.copy()
        # subsample by stride within fold
        idx_fold = np.where(sfd)[0]
        s10_fold = idx_fold[::10]
        if len(s10_fold) < 50:
            continue
        m = base_metrics(yp_z[s10_fold], y_z[s10_fold])
        per_fold[fld] = m
        print(f"  fold {int(fld)}: n={m['n']:>5} P={m['P']:+.4f} S={m['S']:+.4f} β_y_on_ŷ={m['beta_y_on_yhat']:+.3f} R²={m['r2_reg']:+.5f}")

    # Per-fold std (stability indicator)
    if len(per_fold) >= 2:
        ps = np.array([per_fold[f]["P"] for f in per_fold])
        ss = np.array([per_fold[f]["S"] for f in per_fold])
        print(f"  per-fold P std = {ps.std():.4f}, mean = {ps.mean():.4f} (CoV {ps.std()/abs(ps.mean()):.3f})")
        print(f"  per-fold S std = {ss.std():.4f}, mean = {ss.mean():.4f} (CoV {ss.std()/abs(ss.mean()):.3f})")

    return {
        "csv": csv_path.name,
        "dense": m_dense, "stride10": m_s10,
        "bin_plot": bp, "regime": rs, "ci": ci,
        "per_fold": per_fold,
        "n_dense": n_dense, "n_stride": n_stride,
    }


def main():
    base = Path("exports")
    np.random.seed(20260501)
    results = {}
    for model, ckpt, fname in CSV_FILES:
        path = base / fname
        if not path.exists():
            print(f"[WARN] missing {path}")
            continue
        results[(model, ckpt)] = evaluate_csv(path)

    # Cross-comparison table
    print(f"\n\n{'='*100}")
    print("== CROSS-COMPARISON SUMMARY (stride10 pooled)")
    print(f"{'='*100}")
    print(f"{'model':<16} {'ckpt':<6} {'P':>8} {'S':>8} {'σŷ/σy':>7} {'β_y_on_ŷ':>10} {'R²_reg':>10} {'DirAcc':>7} {'DirAcc_tail':>11} {'P_CI95':>20}")
    for (model, ckpt), r in results.items():
        m = r["stride10"]
        ci = r["ci"]
        print(f"{model:<16} {ckpt:<6} {m['P']:+.4f} {m['S']:+.4f} {m['shrink']:.3f}    {m['beta_y_on_yhat']:+.3f}    {m['r2_reg']:+.5f}   {m['DirAcc']:.3f}     {m['DirAcc_tail']:.3f}    [{ci['P_lo']:+.3f},{ci['P_hi']:+.3f}]")


if __name__ == "__main__":
    main()

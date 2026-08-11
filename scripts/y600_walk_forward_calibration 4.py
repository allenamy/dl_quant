"""Walk-forward post-hoc calibration: respects no-test-leakage discipline.

Setup:
  - Fold 0: RAW predictions (no calibrator available — would use train tail in production,
            but we don't have train inference). Documents the production reality:
            "first deployment month before live calibration accumulates."
  - Fold 1: calibrated using fold 0 only.
  - Fold 2: calibrated using fold 0 + fold 1.
  - Pool all 3 folds for production-style metrics.

This matches walk-forward backtest discipline: each test point is predicted using
ONLY data available before its timestamp. Calibrator never peeks at future.

Compare 3 strategies:
  (A) Raw seed42_SWA (no calibration, current proposed winner)
  (B) Walk-forward LINEAR calibration of rank-blend
  (C) Walk-forward ISOTONIC calibration of rank-blend
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata, norm
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LinearRegression

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
    """Per-array rank → blend → inv-CDF → scale by sigma. Output in log-return."""
    s_rank = norm.ppf(rankdata(swa_lr) / (len(swa_lr) + 1))
    e_rank = norm.ppf(rankdata(ema_lr) / (len(ema_lr) + 1))
    return 0.5 * (s_rank + e_rank) * sigma_lr


def compute_metrics(y_lr, yp_lr, mask, label=""):
    valid = mask.astype(bool) & np.isfinite(y_lr) & np.isfinite(yp_lr)
    y, yp = y_lr[valid], yp_lr[valid]
    if len(y) < 30:
        return {}
    P = float(np.corrcoef(y, yp)[0, 1])
    S = float(spearmanr(y, yp).correlation)
    cov = np.mean((y - y.mean()) * (yp - yp.mean()))
    var_yp = np.var(yp)
    beta = cov / var_yp if var_yp > 1e-30 else float("nan")
    sigma_ratio = np.std(yp) / np.std(y)
    edges = np.quantile(y, np.linspace(0, 1, NUM_BINS + 1))
    edges[0] -= 1e-12
    edges[-1] += 1e-12
    idx = np.clip(np.searchsorted(edges, y, side="right") - 1, 0, NUM_BINS - 1)
    by = np.array([y[idx == i].mean() for i in range(NUM_BINS)])
    byp = np.array([yp[idx == i].mean() for i in range(NUM_BINS)])
    bs = float(spearmanr(by, byp).correlation)
    return dict(n=len(y), P=P, S=S, beta=beta, sigma_ratio=sigma_ratio,
                bin_S=bs, top_bin_bps=byp[-1] * 1e4, mean_yhat_bps=yp.mean() * 1e4,
                std_yhat_bps=yp.std() * 1e4)


def fit_linear(yp_train, y_train):
    """Returns linear calibrator: ŷ_cal = β·ŷ + α."""
    return LinearRegression().fit(yp_train.reshape(-1, 1), y_train)


def fit_isotonic(yp_train, y_train):
    """Returns isotonic calibrator."""
    return IsotonicRegression(out_of_bounds="clip").fit(yp_train, y_train)


def main():
    gt = get_gt()
    print("=" * 130)
    print("Walk-forward post-hoc calibration of rank-blend (no test leakage)")
    print("=" * 130)
    print()
    print("Setup:")
    print("  Fold 0: RAW predictions (no prior data for calibrator)")
    print("  Fold 1: calibrated using fold 0 ONLY")
    print("  Fold 2: calibrated using fold 0 + fold 1")
    print()

    # Load all 3 fold prediction sources
    fold_data = {}
    for f in range(NUM_FOLDS):
        sigma_f = float(np.load(f"experiments/y600_push/baseline_plus/fold_{f}/test_preds.npz")["y_sigma"])
        swa = load_pred_lr("baseline_plus", f, "swa_test_preds.npz")
        ema = load_pred_lr("baseline_plus", f, "ema_test_preds.npz")
        rb = make_rank_blend_lr(swa, ema, sigma_f)
        y = gt[f]["y_true_logret"].values.astype(np.float64)
        m = gt[f]["mask"].astype(bool).values
        fold_data[f] = {"swa": swa, "ema": ema, "rb": rb, "y": y, "m": m, "sigma": sigma_f}
        print(f"  Fold {f}: N={len(y):,}  N_valid={m.sum():,}  σ_y={y.std()*1e4:.3f} bps  σ_rb={rb.std()*1e4:.3f} bps")

    # Walk-forward calibration apply
    pooled = {"raw_swa": [], "wf_linear_rb": [], "wf_isotonic_rb": [], "y": [], "m": []}

    for f in range(NUM_FOLDS):
        y_f = fold_data[f]["y"]
        m_f = fold_data[f]["m"]
        rb_f = fold_data[f]["rb"]
        swa_f = fold_data[f]["swa"]

        # Build calibrator from prior folds (none for fold 0)
        if f == 0:
            # No prior data → no calibration possible
            rb_lin_f = rb_f.copy()  # placeholder, unused
            rb_iso_f = rb_f.copy()
            print(f"\n  Fold 0: no prior data → using RAW rank-blend (production reality without prior calibration)")
        else:
            # Concatenate all prior folds for calibration training
            train_rb = np.concatenate([fold_data[k]["rb"][fold_data[k]["m"]] for k in range(f)])
            train_y = np.concatenate([fold_data[k]["y"][fold_data[k]["m"]] for k in range(f)])
            print(f"\n  Fold {f}: calibrating using folds 0..{f-1} ({len(train_rb):,} samples)")

            lin = fit_linear(train_rb, train_y)
            iso = fit_isotonic(train_rb, train_y)
            print(f"    Linear: β={lin.coef_[0]:.4f}, α={lin.intercept_:+.6f}")
            rb_lin_f = lin.predict(rb_f.reshape(-1, 1)).flatten()
            rb_iso_f = iso.predict(rb_f)

        pooled["raw_swa"].append(swa_f)
        pooled["wf_linear_rb"].append(rb_lin_f if f > 0 else swa_f)  # for f=0, use SWA (no cal possible)
        pooled["wf_isotonic_rb"].append(rb_iso_f if f > 0 else swa_f)
        pooled["y"].append(y_f)
        pooled["m"].append(m_f)

    # Pool 3-fold metrics
    print()
    print("=" * 130)
    print("3-FOLD POOLED METRICS (production-style, raw fold 0 + walk-forward calibrated fold 1, 2)")
    print("=" * 130)
    print(f"{'config':<55} {'n':>6} {'P':>8} {'S':>8} {'β':>8} {'σŷ/σy':>8} {'binS':>7} {'topŷ_bps':>10} {'meanŷ':>10} {'σŷ_bps':>8}")
    print("-" * 130)
    y_pool = np.concatenate(pooled["y"])
    m_pool = np.concatenate(pooled["m"])
    for label, key in [
        ("seed42_SWA raw (3-fold pool, baseline)", "raw_swa"),
        ("walk-forward LINEAR calibrated rank-blend", "wf_linear_rb"),
        ("walk-forward ISOTONIC calibrated rank-blend", "wf_isotonic_rb"),
    ]:
        yp_pool = np.concatenate(pooled[key])
        m = compute_metrics(y_pool, yp_pool, m_pool, label=label)
        if not m:
            continue
        print(f"{label:<55} {m['n']:>6} {m['P']:+8.4f} {m['S']:+8.4f} {m['beta']:+8.3f} "
              f"{m['sigma_ratio']:>8.3f} {m['bin_S']:+7.3f} {m['top_bin_bps']:+10.4f} "
              f"{m['mean_yhat_bps']:+10.4f} {m['std_yhat_bps']:>8.3f}")
    print("=" * 130)

    # Per-fold breakdown for the calibrated versions
    print()
    print("Per-fold breakdown (P, S, β, σŷ/σy):")
    print(f"{'Fold':<6} {'raw_SWA':<35} {'wf_LINEAR_rb':<35} {'wf_ISOTONIC_rb':<35}")
    for f in range(NUM_FOLDS):
        line = f"{f:<6} "
        for key in ["raw_swa", "wf_linear_rb", "wf_isotonic_rb"]:
            yp_f = pooled[key][f]
            m = compute_metrics(fold_data[f]["y"], yp_f, fold_data[f]["m"])
            if m:
                line += f"P={m['P']:+.4f} S={m['S']:+.4f} β={m['beta']:+.2f} σ={m['sigma_ratio']:.3f}  "
            else:
                line += "(no data)" + " " * 27
        print(line)


if __name__ == "__main__":
    main()

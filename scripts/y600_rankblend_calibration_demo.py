"""Test post-hoc calibration of rank-blend predictions.

Hypothesis: applying isotonic regression to rank-blend on fold 0 (train tail proxy)
and evaluating on folds 1+2 will give:
  - β = 1 (calibrated)
  - σ_ŷ ≈ 0.05·σ_y (shrunken back to single-seed scale)
  - P slightly higher than raw value-blend (rank-transform's outlier suppression)
  - bin-Spearman > raw value-blend (rank still preserved)

Methodology:
  - Fit on fold 0 only (closest available "train tail" without retraining)
  - Evaluate on fold 1 + fold 2 (true out-of-fit)
  - Compare 3 calibrators: linear (affine), isotonic, identity (no calibration)
  - Compare to baseline seed42_SWA (no rank, raw value)
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


def make_rank_blend(swa, ema):
    """SWA + EMA rank-blend, scaled to log-return units (matches final_stack)."""
    s_rank = norm.ppf(rankdata(swa) / (len(swa) + 1))
    e_rank = norm.ppf(rankdata(ema) / (len(ema) + 1))
    return 0.5 * s_rank + 0.5 * e_rank


def compute_metrics(y_lr, yp_lr, mask):
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


def main():
    gt = get_gt()
    print("=" * 110)
    print("Post-hoc calibration of rank-blend: train on fold 0, eval on folds 1+2 OOS")
    print("=" * 110)

    # Get fold 0 (calibration training)
    swa_0 = load_pred_lr("baseline_plus", 0, "swa_test_preds.npz")
    ema_0 = load_pred_lr("baseline_plus", 0, "ema_test_preds.npz")
    y_0 = gt[0]["y_true_logret"].values.astype(np.float64)
    m_0 = gt[0]["mask"].astype(bool).values

    # Convert rank-blend back to log-return units (same scaling as final_stack)
    sigma_0 = float(np.load("experiments/y600_push/baseline_plus/fold_0/test_preds.npz")["y_sigma"])
    rank_blend_0_unitless = make_rank_blend(swa_0, ema_0)
    rank_blend_0_lr = rank_blend_0_unitless * sigma_0  # in log-return scale

    # Fit calibrators on fold 0 (valid samples only)
    valid_0 = m_0 & np.isfinite(y_0) & np.isfinite(rank_blend_0_lr)
    rb_train = rank_blend_0_lr[valid_0]
    y_train = y_0[valid_0]
    print(f"Calibration training: fold 0, {len(rb_train):,} valid samples")
    print(f"  rank-blend scale: σ={rb_train.std()*1e4:.3f} bps, range=[{rb_train.min()*1e4:.2f}, {rb_train.max()*1e4:.2f}] bps")
    print(f"  y_target scale:   σ={y_train.std()*1e4:.3f} bps")

    # Calibrator 1: Affine (linear regression β + intercept)
    lin = LinearRegression().fit(rb_train.reshape(-1, 1), y_train)
    print(f"\nLinear calibrator: y_cal = {lin.coef_[0]:.4f} * ŷ_rank + {lin.intercept_:+.6f}")

    # Calibrator 2: Isotonic
    iso = IsotonicRegression(out_of_bounds="clip").fit(rb_train, y_train)
    iso_pred_train = iso.predict(rb_train)
    print(f"Isotonic calibrator: σ(iso(ŷ_train))={iso_pred_train.std()*1e4:.3f} bps (vs σ_y_train={y_train.std()*1e4:.3f})")

    # Eval on fold 1 + fold 2 (OOS for calibrator)
    print()
    print("=" * 110)
    print("OOS evaluation: fold 1 + fold 2 (calibrator never saw these)")
    print("=" * 110)
    print(f"{'config':<55} {'n':>6} {'P':>8} {'S':>8} {'β':>8} {'σŷ/σy':>8} {'binS':>7} {'topŷ_bps':>10} {'meanŷ':>10} {'σŷ_bps':>8}")
    print("-" * 110)

    test_pieces_y = []
    test_pieces_rb = []
    test_pieces_swa = []
    test_pieces_emaval = []
    test_pieces_m = []
    for f in [1, 2]:
        swa = load_pred_lr("baseline_plus", f, "swa_test_preds.npz")
        ema = load_pred_lr("baseline_plus", f, "ema_test_preds.npz")
        sigma_f = float(np.load(f"experiments/y600_push/baseline_plus/fold_{f}/test_preds.npz")["y_sigma"])
        # Rank-blend per fold (same procedure as final_stack — rank within each fold)
        rb_f_unitless = make_rank_blend(swa, ema)
        rb_f_lr = rb_f_unitless * sigma_f
        y_f = gt[f]["y_true_logret"].values.astype(np.float64)
        m_f = gt[f]["mask"].astype(bool).values
        # Value-blend SWA+EMA (no rank)
        valblend = 0.5 * swa + 0.5 * ema
        test_pieces_y.append(y_f); test_pieces_rb.append(rb_f_lr); test_pieces_swa.append(swa); test_pieces_emaval.append(valblend); test_pieces_m.append(m_f)

    y_test = np.concatenate(test_pieces_y)
    rb_test = np.concatenate(test_pieces_rb)
    swa_test = np.concatenate(test_pieces_swa)
    valblend_test = np.concatenate(test_pieces_emaval)
    m_test = np.concatenate(test_pieces_m)

    # Configs to evaluate on test
    rb_lin_test = lin.predict(rb_test.reshape(-1, 1)).flatten()
    rb_iso_test = iso.predict(rb_test)

    configs = [
        ("seed42_SWA (raw, no calibration)", swa_test),
        ("seed42 SWA+EMA value-blend (no rank, no cal)", valblend_test),
        ("rank-blend (no calibration, like final_stack)", rb_test),
        ("rank-blend + LINEAR calibration", rb_lin_test),
        ("rank-blend + ISOTONIC calibration", rb_iso_test),
    ]
    for label, yp in configs:
        m = compute_metrics(y_test, yp, m_test)
        if not m:
            continue
        print(f"{label:<55} {m['n']:>6} {m['P']:+8.4f} {m['S']:+8.4f} {m['beta']:+8.3f} "
              f"{m['sigma_ratio']:>8.3f} {m['bin_S']:+7.3f} {m['top_bin_bps']:+10.4f} "
              f"{m['mean_yhat_bps']:+10.4f} {m['std_yhat_bps']:>8.3f}")
    print("=" * 110)

    # Per-fold breakdown for calibrated rank-blend
    print()
    print("Per-fold breakdown for calibrated rank-blend (isotonic):")
    for f in [1, 2]:
        swa = load_pred_lr("baseline_plus", f, "swa_test_preds.npz")
        ema = load_pred_lr("baseline_plus", f, "ema_test_preds.npz")
        sigma_f = float(np.load(f"experiments/y600_push/baseline_plus/fold_{f}/test_preds.npz")["y_sigma"])
        rb_f_lr = make_rank_blend(swa, ema) * sigma_f
        rb_iso_f = iso.predict(rb_f_lr)
        y_f = gt[f]["y_true_logret"].values.astype(np.float64)
        m_f = gt[f]["mask"].astype(bool).values
        m_p = compute_metrics(y_f, rb_iso_f, m_f)
        print(f"  fold {f}: P={m_p['P']:+.4f} S={m_p['S']:+.4f} β={m_p['beta']:+.3f} σŷ/σy={m_p['sigma_ratio']:.3f}")


if __name__ == "__main__":
    main()

"""Compare V4 y_600 calibrated training vs final_stack baseline.

Pulls per-fold predictions from:
  - experiments/y600_push/final_stack/fold_{0,1,2}/test_preds.npz (baseline)
  - experiments/y600_calib/baseline_calib/fold_{0,1,2}/test_preds.npz (Track A)

Reports pooled clean (stride-10-then-mask) metrics and decides Track A
gate per plan: Pearson within 0.02 of baseline AND β >= 0.5.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
from scipy.stats import pearsonr, spearmanr


def load_pooled(exp_dir: pathlib.Path):
    """Load 3 folds of test_preds.npz, return (yp, y) pooled clean (stride-10)."""
    yps, ys = [], []
    for f in range(3):
        p = exp_dir / f"fold_{f}" / "test_preds.npz"
        if not p.exists():
            sys.exit(f"ERROR: missing {p}")
        d = np.load(p)
        yp_all = d["predictions"]
        yp = yp_all[:, 1] if yp_all.ndim == 2 and yp_all.shape[-1] >= 2 else yp_all.squeeze()
        y = d["targets"].squeeze()
        m = d["mask"].astype(bool).squeeze()
        # Canonical clean: stride-10 BEFORE mask filter (matches y600_final_eval.py).
        yp_s, y_s, m_s = yp[::10], y[::10], m[::10]
        yps.append(yp_s[m_s]); ys.append(y_s[m_s])
    return np.concatenate(yps), np.concatenate(ys)


def metrics(yp, y, label, ref_p=None, ref_b=None):
    rho = pearsonr(yp, y)[0]
    sp = spearmanr(yp, y)[0]
    beta = float(np.cov(yp, y, ddof=0)[0, 1] / (np.var(yp) + 1e-12))
    sr = float(yp.std() / (y.std() + 1e-12))
    line = f"\n=== {label} (N={len(y)}) ==="
    print(line)
    print(f"  Pearson  = {rho:+.4f}" +
          (f"  Δref {rho - ref_p:+.4f}" if ref_p is not None else ""))
    print(f"  Spearman = {sp:+.4f}")
    print(f"  β        = {beta:+.4f}" +
          (f"  Δref {beta - ref_b:+.4f}" if ref_b is not None else ""))
    print(f"  σ_ŷ/σ_y  = {sr:.4f}")
    return rho, sp, beta, sr


def main():
    baseline_dir = pathlib.Path("experiments/y600_push/final_stack")
    calib_dir = pathlib.Path("experiments/y600_calib/baseline_calib")

    yp_ref, y_ref = load_pooled(baseline_dir)
    ref_p, ref_s, ref_b, ref_sr = metrics(yp_ref, y_ref, "BASELINE final_stack")

    yp_cal, y_cal = load_pooled(calib_dir)
    cal_p, cal_s, cal_b, cal_sr = metrics(
        yp_cal, y_cal, "CALIBRATED (Track A)", ref_p=ref_p, ref_b=ref_b
    )

    print("\n=== Track A Gate Decision ===")
    ok_pearson = cal_p >= ref_p - 0.02
    ok_beta = cal_b >= 0.5
    ok_no_ps_div = (cal_s - ref_s) >= -0.02  # don't trade Spearman for β
    print(f"  Pearson >= ref − 0.02 ({ref_p - 0.02:+.4f})? "
          f"got {cal_p:+.4f} — {'PASS' if ok_pearson else 'FAIL'}")
    print(f"  β >= 0.50?                                got {cal_b:+.4f} — "
          f"{'PASS' if ok_beta else 'FAIL'}")
    print(f"  Spearman >= ref − 0.02?                   got {cal_s:+.4f} — "
          f"{'PASS' if ok_no_ps_div else 'FAIL'}")
    overall = ok_pearson and ok_beta and ok_no_ps_div
    print(f"  OVERALL: {'PASS — proceed to Track B' if overall else 'FAIL — tune λ_β / λ_dh'}")


if __name__ == "__main__":
    main()

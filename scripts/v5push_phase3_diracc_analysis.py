"""Phase 3 Stage A: post-hoc DirAcc analysis on V5 production predictions.

Tests 4 fixes WITHOUT retraining:
  A1. Bias correction: sign(q50 - mean(q50))
  A2. |q50| confidence gating (decile-by-decile DirAcc)
  A3. Uncertainty gating: DirAcc on samples with low (q90-q10)
  A4. Combined trustworthiness: |q50| / (q90-q10) — model-internal score

Goal: identify any free DirAcc improvement before considering retrain.
Reports 3-fold pool DirAcc + per-fold breakdown.
"""
from __future__ import annotations
import pathlib
import numpy as np
from scipy.stats import pearsonr, spearmanr


def load_preds(exp_dir: pathlib.Path, use_ema: bool = True):
    """Pool q10/q50/q90/y_true/mask across 3 folds."""
    qs = []  # list of (n, 3)
    ys = []
    ms = []
    for f in range(3):
        fname = "ema_test_preds.npz" if use_ema else "test_preds.npz"
        p = exp_dir / f"fold_{f}" / fname
        z = np.load(p, allow_pickle=True)
        pred = z["predictions"]  # (n, 3) = q10, q50, q90
        y = z["targets"].reshape(-1)
        m = z["mask"].reshape(-1).astype(bool)
        ysig = float(z["y_sigma"])
        ymed = float(z["y_median"])
        # Denorm to bps
        pred_bps = (pred * ysig + ymed) * 1e4
        y_bps = (y * ysig + ymed) * 1e4
        qs.append(pred_bps[m])
        ys.append(y_bps[m])
        ms.append(np.full(int(m.sum()), f, dtype=np.int8))
    q = np.concatenate(qs)
    y = np.concatenate(ys)
    fold = np.concatenate(ms)
    return q, y, fold


def diracc(pred_sign, y, mask=None):
    """DirAcc with optional mask."""
    if mask is not None:
        pred_sign = pred_sign[mask]
        y = y[mask]
    valid = (y != 0) & (pred_sign != 0)
    if valid.sum() == 0:
        return float("nan"), 0
    return float(np.mean(np.sign(pred_sign[valid]) == np.sign(y[valid]))), int(valid.sum())


def main():
    exp = pathlib.Path("experiments/v5_final/singleh_alpha0_huber")
    print("=" * 70)
    print("V5 production singh α=0+Huber — DirAcc post-hoc analysis")
    print("=" * 70)

    for use_ema in [False, True]:
        tag = "EMA" if use_ema else "BEST"
        print(f"\n=========== {tag} predictions ===========")
        q, y, fold = load_preds(exp, use_ema=use_ema)
        q10, q50, q90 = q[:, 0], q[:, 1], q[:, 2]
        n = len(q50)

        # Baseline DirAcc
        da_raw, n_raw = diracc(q50, y)
        print(f"\nBaseline: DirAcc=sign(q50) vs sign(y)")
        print(f"  Pool: DirAcc={da_raw:.4f}  n={n_raw:,}  (theoretical max ~0.546 at ρ=0.058)")

        # Per-fold baseline
        for f in range(3):
            da_f, nf = diracc(q50, y, fold == f)
            print(f"  fold {f}: DirAcc={da_f:.4f}  n={nf:,}")

        # ====================================================================
        # A1. Bias correction
        # ====================================================================
        bias = q50.mean()
        q50_demean = q50 - bias
        da_demean, _ = diracc(q50_demean, y)
        print(f"\nA1. Bias correction (sign(q50 - mean(q50)={bias:+.3f}bps))")
        print(f"  Pool: DirAcc={da_demean:.4f}  ΔDirAcc={da_demean-da_raw:+.4f}")
        # Per-fold bias correction
        for f in range(3):
            f_mask = fold == f
            bias_f = q50[f_mask].mean()
            da_f1, nf = diracc(q50 - bias_f, y, f_mask)
            print(f"  fold {f}: bias={bias_f:+.3f}bps  DirAcc={da_f1:.4f}  Δ={da_f1-diracc(q50, y, f_mask)[0]:+.4f}")

        # ====================================================================
        # A2. Confidence gating by |q50|
        # ====================================================================
        print(f"\nA2. |q50| confidence gating (decile-by-decile)")
        abs_q50 = np.abs(q50)
        deciles = np.percentile(abs_q50, [0, 50, 70, 80, 90, 95, 99])
        print(f"  threshold |    DirAcc | n      | %_of_pool")
        for thr in deciles:
            mask = abs_q50 >= thr
            da_g, nf = diracc(q50, y, mask)
            print(f"  {thr:>8.2f}bps |   {da_g:.4f} | {nf:>6,} | {nf/n*100:>4.1f}%")

        # ====================================================================
        # A3. Uncertainty gating: DirAcc on samples with TIGHT (q90-q10)
        # ====================================================================
        print(f"\nA3. Uncertainty gating (q90-q10 below threshold)")
        uncertainty = q90 - q10
        u_pct = np.percentile(uncertainty, [10, 25, 50, 75, 90])
        print(f"  uncertainty p10/25/50/75/90 = {u_pct[0]:.3f} / {u_pct[1]:.3f} / {u_pct[2]:.3f} / {u_pct[3]:.3f} / {u_pct[4]:.3f} bps")
        print(f"  IQR thr     |    DirAcc | n      | %")
        for thr in u_pct:
            mask = uncertainty <= thr
            da_u, nf = diracc(q50, y, mask)
            print(f"  ≤{thr:>5.2f}bps |   {da_u:.4f} | {nf:>6,} | {nf/n*100:>4.1f}%")

        # ====================================================================
        # A4. Trustworthiness score: |q50| / (q90-q10)
        # ====================================================================
        print(f"\nA4. Trustworthiness score = |q50| / (q90-q10) — model-internal SNR")
        trust = np.abs(q50) / (uncertainty + 1e-9)
        t_pct = np.percentile(trust, [50, 70, 80, 90, 95, 99])
        print(f"  trust p50/70/80/90/95/99 = {t_pct[0]:.3f} / {t_pct[1]:.3f} / {t_pct[2]:.3f} / {t_pct[3]:.3f} / {t_pct[4]:.3f} / {t_pct[5]:.3f}")
        print(f"  trust thr   |    DirAcc | n      | %")
        for thr in t_pct:
            mask = trust >= thr
            da_t, nf = diracc(q50, y, mask)
            print(f"  ≥{thr:>5.3f} |   {da_t:.4f} | {nf:>6,} | {nf/n*100:>4.1f}%")

        # Combined: confidence + bias correction
        print(f"\nA5. (combined) sign(q50_demean) × confidence top-X gating")
        for top_pct in [50, 30, 20, 10, 5, 2]:
            thr = np.percentile(abs_q50, 100 - top_pct)
            mask = abs_q50 >= thr
            da, nf = diracc(q50 - bias, y, mask)
            print(f"  top {top_pct:>2}% |q50|+bias-corrected: DirAcc={da:.4f}  n={nf:,}")

    print("\n" + "=" * 70)
    print("Summary insight:")
    print("  - If A4 trust-gated DirAcc reaches 0.58+ at reasonable n (>20% of pool), no retrain needed")
    print("  - If A1 bias correction gives >0.005 boost free, apply immediately")
    print("  - If best gating < 0.55, retrain with confidence-weighted sign head warranted")


if __name__ == "__main__":
    main()

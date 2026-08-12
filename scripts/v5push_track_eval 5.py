"""Generic Track A/E/G/H/J 3-fold eval vs V5 prod BEST baseline.

Usage:
    python scripts/v5push_track_eval.py --track-dir experiments/v5push/singh_daqh_tv --name "Track A (DAQH+TV)"

Apples-to-apples comparison:
- Pool 3 folds raw → causal EMA-demean (α=0.01) live calibration
- Eval on live-calibrated q50 (same as V5 prod CSV)
- Per-fold breakdown + pooled headline
- V5 prod BEST is anchor baseline (per CLAUDE.md current production)
"""
from __future__ import annotations
import argparse
import numpy as np
import pathlib
from scipy.stats import pearsonr, spearmanr

EMA_ALPHA = 0.01
WARMUP = 50


def causal_ema_demean(q50_bps: np.ndarray) -> np.ndarray:
    n = len(q50_bps)
    ema = np.zeros(n)
    cur = 0.0
    for i in range(n):
        if i > 0:
            cur = EMA_ALPHA * q50_bps[i - 1] + (1 - EMA_ALPHA) * cur
        ema[i] = cur if i >= WARMUP else 0.0
    return q50_bps - ema


def load_and_calibrate(exp_dir: pathlib.Path, fname: str = "test_preds.npz"):
    all_q50_raw, all_q50_live, all_y, all_q10, all_q90, all_fold = [], [], [], [], [], []
    for f in range(3):
        p = exp_dir / f"fold_{f}" / fname
        if not p.exists():
            print(f"[WARN] missing {p}")
            continue
        z = np.load(p, allow_pickle=True)
        pred = z["predictions"]; y = z["targets"].reshape(-1); m = z["mask"].reshape(-1).astype(bool)
        ts = z["timestamps"]
        ysig = float(z["y_sigma"]); ymed = float(z["y_median"])
        q10 = (pred[:, 0] * ysig + ymed) * 1e4
        q50 = (pred[:, 1] * ysig + ymed) * 1e4
        q90 = (pred[:, 2] * ysig + ymed) * 1e4
        y_bps = (y * ysig + ymed) * 1e4
        order = np.argsort(ts)
        q50, q10, q90, y_bps, m = q50[order], q10[order], q90[order], y_bps[order], m[order]
        q50_live = causal_ema_demean(q50)
        v = m
        all_q50_raw.append(q50[v]); all_q50_live.append(q50_live[v])
        all_y.append(y_bps[v]); all_q10.append(q10[v]); all_q90.append(q90[v])
        all_fold.append(np.full(int(v.sum()), f, dtype=np.int8))
    return (np.concatenate(all_q50_raw), np.concatenate(all_q50_live),
            np.concatenate(all_y), np.concatenate(all_q10),
            np.concatenate(all_q90), np.concatenate(all_fold))


def eval_metrics(q, y, q10=None, q90=None):
    P = pearsonr(q, y)[0]; S = spearmanr(q, y).correlation
    sq, sy = q.std(), y.std()
    beta = np.cov(q, y)[0, 1] / max(sq ** 2, 1e-12)
    bias = q.mean() - y.mean()
    da_all = float(np.mean(np.sign(q) == np.sign(y)))
    sigy = sy
    high_y_mask = np.abs(y) > sigy
    da_high_y = float(np.mean(np.sign(q[high_y_mask]) == np.sign(y[high_y_mask])))
    # top-decile spread (|q| top 10% mean y vs |q| bottom 10% mean y)
    abs_thr_top = np.percentile(np.abs(q), 90)
    top_mask = np.abs(q) >= abs_thr_top
    top_y_signed = np.sign(q[top_mask]) * y[top_mask]
    top_spread = float(top_y_signed.mean()) if top_mask.sum() > 0 else 0.0
    # bin-monotonicity (E[ŷ|y_decile])
    y_deciles = np.percentile(y, np.linspace(0, 100, 11))
    bin_means = []
    for i in range(10):
        bin_mask = (y >= y_deciles[i]) & (y <= y_deciles[i + 1])
        if bin_mask.sum() > 0:
            bin_means.append(q[bin_mask].mean())
    if len(bin_means) > 1:
        rho_bin = spearmanr(np.arange(len(bin_means)), bin_means).correlation
    else:
        rho_bin = 0.0
    return {
        "P": P, "S": S, "beta": beta, "sigma_ratio": sq / sy, "bias": bias,
        "DirAcc_all": da_all, "DirAcc_high_y": da_high_y,
        "n_high_y": int(high_y_mask.sum()),
        "top_decile_spread_bps": top_spread,
        "bin_monotonicity": rho_bin,
    }


def print_metrics(label, m, n):
    print(f"\n  -- {label} (n={n:,}) --")
    print(f"  P={m['P']:+.4f}  S={m['S']:+.4f}  β={m['beta']:+.3f}  σŷ/σy={m['sigma_ratio']:.3f}  bias={m['bias']:+.3f}bps")
    print(f"  DirAcc_all={m['DirAcc_all']:.4f}  DirAcc_|y|>σ={m['DirAcc_high_y']:.4f} (n={m['n_high_y']:,})")
    print(f"  TopDecileSpread={m['top_decile_spread_bps']:+.3f}bps  BinMono(ρ)={m['bin_monotonicity']:+.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track-dir", required=True)
    ap.add_argument("--name", default="Track")
    ap.add_argument("--baseline-dir", default="experiments/v5_final/singleh_alpha0_huber")
    ap.add_argument("--baseline-name", default="V5 prod singh α=0+Huber")
    args = ap.parse_args()

    print("=" * 80)
    print(f"  {args.name}  vs  {args.baseline_name}")
    print("=" * 80)

    for label_prefix, exp_dir in [(args.name, args.track_dir), (args.baseline_name, args.baseline_dir)]:
        d = pathlib.Path(exp_dir)
        print(f"\n=========== {label_prefix} ({d}) ===========")
        for tag, fname in [("BEST", "test_preds.npz"), ("EMA", "ema_test_preds.npz")]:
            p0 = d / "fold_0" / fname
            if not p0.exists():
                continue
            q_raw, q_live, y, q10, q90, fold = load_and_calibrate(d, fname)
            m = eval_metrics(q_live, y, q10, q90)
            print_metrics(f"{tag} (live)", m, len(y))
            for f in range(3):
                fm = fold == f
                if fm.sum() == 0:
                    continue
                mf = eval_metrics(q_live[fm], y[fm])
                print(f"    fold {f}: P={mf['P']:+.4f} S={mf['S']:+.4f} β={mf['beta']:+.3f} σŷ/σy={mf['sigma_ratio']:.3f} DA={mf['DirAcc_all']:.4f}")


if __name__ == "__main__":
    main()

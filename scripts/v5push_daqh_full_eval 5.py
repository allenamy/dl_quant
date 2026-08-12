"""DAQH 3-fold full eval with V5 production live-calibration parity.

For fair DirAcc comparison:
- V5 production: y_pred_q50_bps_live = q50 - causal_EMA(q50, α=0.01)
- DAQH: apply SAME live calibration to test_preds, compare like-for-like

Per fold:
- Pool predictions in raw bps
- Apply causal EMA-demean (α=0.01, per-fold reset, 50-sample warmup skip)
- Eval IC + DirAcc on calibrated predictions

Compare to V5 production baseline values (from memory).
"""
from __future__ import annotations
import numpy as np
import pathlib
from scipy.stats import pearsonr, spearmanr


EMA_ALPHA = 0.01
WARMUP_SAMPLES = 50


def causal_ema_demean(q50_bps: np.ndarray, alpha: float = EMA_ALPHA, warmup: int = WARMUP_SAMPLES) -> np.ndarray:
    """Per-fold causal EMA-demean (lag-1 to avoid leak)."""
    n = len(q50_bps)
    ema = np.zeros(n)
    cur = 0.0
    # warmup phase: build EMA but don't subtract yet
    for i in range(n):
        if i > 0:
            cur = alpha * q50_bps[i - 1] + (1 - alpha) * cur
        ema[i] = cur if i >= warmup else 0.0
    return q50_bps - ema


def load_and_calibrate(exp_dir: pathlib.Path, tag_fname: str):
    """Load 3-fold preds, apply per-fold live calibration, return pooled + per-fold arrays."""
    all_q50_raw, all_q50_live, all_y, all_q10, all_q90, all_fold = [], [], [], [], [], []
    for f in range(3):
        p = exp_dir / f"fold_{f}" / tag_fname
        z = np.load(p, allow_pickle=True)
        pred = z["predictions"]; y = z["targets"].reshape(-1); m = z["mask"].reshape(-1).astype(bool)
        ts = z["timestamps"]
        ysig = float(z["y_sigma"]); ymed = float(z["y_median"])
        q10 = (pred[:, 0] * ysig + ymed) * 1e4
        q50 = (pred[:, 1] * ysig + ymed) * 1e4
        q90 = (pred[:, 2] * ysig + ymed) * 1e4
        y_bps = (y * ysig + ymed) * 1e4
        # Sort by timestamp (preds are already ordered but make sure)
        order = np.argsort(ts)
        q50_sorted = q50[order]
        q10_sorted = q10[order]
        q90_sorted = q90[order]
        y_sorted = y_bps[order]
        m_sorted = m[order]
        # Apply per-fold causal EMA-demean
        q50_live_sorted = causal_ema_demean(q50_sorted)
        # Apply mask
        v = m_sorted
        all_q50_raw.append(q50_sorted[v])
        all_q50_live.append(q50_live_sorted[v])
        all_y.append(y_sorted[v])
        all_q10.append(q10_sorted[v])
        all_q90.append(q90_sorted[v])
        all_fold.append(np.full(int(v.sum()), f, dtype=np.int8))
    return (
        np.concatenate(all_q50_raw),
        np.concatenate(all_q50_live),
        np.concatenate(all_y),
        np.concatenate(all_q10),
        np.concatenate(all_q90),
        np.concatenate(all_fold),
    )


def eval_metrics(q, y, fold=None, trust_topk: float = 0.1, label: str = ""):
    """Compute P, S, DirAcc, top-k trust DirAcc, conditional DirAcc."""
    P = pearsonr(q, y)[0]
    S = spearmanr(q, y).correlation
    sq, sy = q.std(), y.std()
    beta = np.cov(q, y)[0, 1] / max(sq ** 2, 1e-12)
    bias = q.mean() - y.mean()
    da_all = float(np.mean(np.sign(q) == np.sign(y)))
    # |q| top-k confidence
    abs_thr = np.percentile(np.abs(q), 100 * (1 - trust_topk))
    abs_mask = np.abs(q) >= abs_thr
    da_q_top = float(np.mean(np.sign(q[abs_mask]) == np.sign(y[abs_mask])))
    # Conditional DirAcc on |y| > σ_y (tradeable samples)
    sigy = y.std()
    high_y_mask = np.abs(y) > sigy
    da_high_y = float(np.mean(np.sign(q[high_y_mask]) == np.sign(y[high_y_mask])))
    return {
        "P": P, "S": S, "beta": beta, "sigma_ratio": sq / sy, "bias": bias,
        "DirAcc_all": da_all,
        "DirAcc_q_top10": da_q_top,
        "DirAcc_high_y": da_high_y,
        "n_high_y": int(high_y_mask.sum()),
    }


def main():
    print("=" * 75)
    print("DAQH vs V5 production: full 3-fold pool + live calibration parity")
    print("=" * 75)

    # DAQH
    print("\n=========== DAQH (singh α=0+Huber + DAQH head + λ_cls=0.05) ===========")
    daqh_dir = pathlib.Path("experiments/v5push/singh_daqh")
    for tag, fname in [("BEST", "test_preds.npz"), ("EMA", "ema_test_preds.npz")]:
        q_raw, q_live, y, q10, q90, fold = load_and_calibrate(daqh_dir, fname)
        # Use q_live for fair DirAcc comparison (post EMA-demean)
        print(f"\n  -- {tag} (n={len(y):,}) --")
        m = eval_metrics(q_live, y)
        print(f"  P={m['P']:+.4f}  S={m['S']:+.4f}  β={m['beta']:+.3f}  σŷ/σy={m['sigma_ratio']:.3f}  bias={m['bias']:+.3f}bps")
        print(f"  DirAcc_all={m['DirAcc_all']:.4f}  DirAcc_|q|top10%={m['DirAcc_q_top10']:.4f}  DirAcc_|y|>σ={m['DirAcc_high_y']:.4f} (n={m['n_high_y']:,})")
        # Trust gating (use q10, q90 of LIVE preds = q10_raw, q90_raw shifted by EMA — but for simplicity use raw q10/q90 distances)
        trust = np.abs(q_live) / (q90 - q10 + 1e-9)
        thr = np.percentile(trust, 90)
        sel = trust >= thr
        da_trust = float(np.mean(np.sign(q_live[sel]) == np.sign(y[sel])))
        print(f"  DirAcc_trust_top10%={da_trust:.4f}  (n={sel.sum():,})")
        # Per-fold
        for f in range(3):
            fm = fold == f
            mf = eval_metrics(q_live[fm], y[fm])
            print(f"    fold {f}: P={mf['P']:+.4f} S={mf['S']:+.4f} DirAcc_all={mf['DirAcc_all']:.4f}")

    # V5 production
    print("\n\n=========== V5 production singh α=0+Huber (baseline) ===========")
    v5_dir = pathlib.Path("experiments/v5_final/singleh_alpha0_huber")
    for tag, fname in [("BEST", "test_preds.npz"), ("EMA", "ema_test_preds.npz")]:
        q_raw, q_live, y, q10, q90, fold = load_and_calibrate(v5_dir, fname)
        print(f"\n  -- {tag} (n={len(y):,}) --")
        m = eval_metrics(q_live, y)
        print(f"  P={m['P']:+.4f}  S={m['S']:+.4f}  β={m['beta']:+.3f}  σŷ/σy={m['sigma_ratio']:.3f}  bias={m['bias']:+.3f}bps")
        print(f"  DirAcc_all={m['DirAcc_all']:.4f}  DirAcc_|q|top10%={m['DirAcc_q_top10']:.4f}  DirAcc_|y|>σ={m['DirAcc_high_y']:.4f} (n={m['n_high_y']:,})")
        trust = np.abs(q_live) / (q90 - q10 + 1e-9)
        thr = np.percentile(trust, 90)
        sel = trust >= thr
        da_trust = float(np.mean(np.sign(q_live[sel]) == np.sign(y[sel])))
        print(f"  DirAcc_trust_top10%={da_trust:.4f}  (n={sel.sum():,})")
        for f in range(3):
            fm = fold == f
            mf = eval_metrics(q_live[fm], y[fm])
            print(f"    fold {f}: P={mf['P']:+.4f} S={mf['S']:+.4f} DirAcc_all={mf['DirAcc_all']:.4f}")


if __name__ == "__main__":
    main()

"""Compare retired final_stack (rank-transformed blend) vs current candidates.

Purpose: confirm whether final_stack had higher P/S/monotonicity than current single
seed42_SWA, and quantify the trade-off.

Methodology: same as y600_ckpt_seed_diagnostic.py — raw dense, per-fold-aware pool.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

NUM_FOLDS = 3
NUM_BINS = 10
GROUND_TRUTH_CSV = Path("exports/y600_baseline_plus_BEST_3seed_median.csv")
SEED_DIRS = {
    42: Path("experiments/y600_push/baseline_plus"),
    7: Path("experiments/y600_baseline_seed7"),
    13: Path("experiments/y600_baseline_seed13"),
}
CKPT_TO_FILE = {"BEST": "test_preds.npz", "EMA": "ema_test_preds.npz", "SWA": "swa_test_preds.npz"}


def load_pred_lr(seed, fold, ckpt):
    d = np.load(SEED_DIRS[seed] / f"fold_{fold}" / CKPT_TO_FILE[ckpt])
    return d["timestamps"].astype(np.int64), d["predictions"][:, 1].astype(np.float64) * float(d["y_sigma"])


def load_final_stack_pred_lr(fold):
    """Load final_stack rank-blend predictions, multiply by y_sigma → log-return."""
    d = np.load(f"experiments/y600_push/final_stack/fold_{fold}/test_preds.npz")
    return d["timestamps"].astype(np.int64), d["predictions"][:, 1].astype(np.float64) * float(d["y_sigma"])


def get_gt():
    df = pd.read_csv(GROUND_TRUTH_CSV)
    return {f: df[df["fold"] == f].reset_index(drop=True) for f in range(NUM_FOLDS)}


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
                mean_y_bps=y.mean() * 1e4, std_yhat_bps=yp.std() * 1e4)


def evaluate(label, fold_pred_lr, gt):
    pieces_y, pieces_yp, pieces_m = [], [], []
    per_fold = []
    for f in range(NUM_FOLDS):
        df = gt[f]
        y_lr = df["y_true_logret"].values.astype(np.float64)
        m = df["mask"].astype(bool).values
        yp_lr = fold_pred_lr[f]
        # Sanity: lengths match
        assert len(y_lr) == len(yp_lr), f"{label} fold {f}: y len {len(y_lr)} vs yp {len(yp_lr)}"
        per_fold.append(compute_metrics(y_lr, yp_lr, m))
        pieces_y.append(y_lr); pieces_yp.append(yp_lr); pieces_m.append(m)
    pooled = compute_metrics(
        np.concatenate(pieces_y), np.concatenate(pieces_yp), np.concatenate(pieces_m))
    pf_p = [m["P"] for m in per_fold if m]
    return label, pooled, pf_p


def main():
    gt = get_gt()
    configs = []

    # 1. final_stack (retired rank-blend)
    fp = {f: load_final_stack_pred_lr(f)[1] for f in range(NUM_FOLDS)}
    configs.append(evaluate("final_stack (rank-blend, RETIRED)", fp, gt))

    # 2. seed42_SWA (proposed winner)
    fp = {f: load_pred_lr(42, f, "SWA")[1] for f in range(NUM_FOLDS)}
    configs.append(evaluate("seed42_SWA (proposed)", fp, gt))

    # 3. seed42_EMA (level-positive)
    fp = {f: load_pred_lr(42, f, "EMA")[1] for f in range(NUM_FOLDS)}
    configs.append(evaluate("seed42_EMA", fp, gt))

    # 4. 3seed_median_EMA (current production)
    fp = {}
    for f in range(NUM_FOLDS):
        stack = np.stack([load_pred_lr(s, f, "EMA")[1] for s in [7, 13, 42]], axis=0)
        fp[f] = np.median(stack, axis=0)
    configs.append(evaluate("3seed_median_EMA (CURRENT)", fp, gt))

    # 5. 3seed_mean_SWA (alt ensemble)
    fp = {}
    for f in range(NUM_FOLDS):
        stack = np.stack([load_pred_lr(s, f, "SWA")[1] for s in [7, 13, 42]], axis=0)
        fp[f] = np.mean(stack, axis=0)
    configs.append(evaluate("3seed_mean_SWA", fp, gt))

    # 6. Custom: 0.5*SWA + 0.5*EMA seed42 raw value-blend (NOT rank-blend) — closest analog to final_stack but value
    fp = {}
    for f in range(NUM_FOLDS):
        s = load_pred_lr(42, f, "SWA")[1]
        e = load_pred_lr(42, f, "EMA")[1]
        fp[f] = 0.5 * s + 0.5 * e
    configs.append(evaluate("seed42_SWA+EMA value-blend", fp, gt))

    # 7. CONSTRUCT rank-blend on the fly from current seed42 SWA+EMA, see if rank transform alone explains gap
    def rank_transform(arr):
        # Per-array rank → quantile → inv-Gaussian (similar to final_stack)
        from scipy.stats import rankdata, norm
        ranks = rankdata(arr) / (len(arr) + 1)  # uniform [0,1]
        return norm.ppf(ranks)
    fp = {}
    for f in range(NUM_FOLDS):
        s = load_pred_lr(42, f, "SWA")[1]
        e = load_pred_lr(42, f, "EMA")[1]
        # SWA rank-blend + EMA rank-blend, then average ranks
        s_rank = rank_transform(s)
        e_rank = rank_transform(e)
        blend = 0.5 * s_rank + 0.5 * e_rank
        # Scale back by y_sigma so it lands in similar units (final_stack does this)
        d = np.load(SEED_DIRS[42] / f"fold_{f}" / "test_preds.npz")
        sigma = float(d["y_sigma"])
        fp[f] = blend * sigma  # rank-blend in log-return units (high σ_ŷ)
    configs.append(evaluate("seed42_SWA+EMA RANK-BLEND (reconstructed)", fp, gt))

    print("=" * 100)
    print(f"{'config':<48} {'N':>6} {'P':>8} {'S':>8} {'β':>8} {'σŷ/σy':>8} {'binS':>7} {'topŷ_bps':>10} {'meanŷ_bps':>10} {'σŷ_bps':>8}")
    print("-" * 100)
    for label, m, pf_p in configs:
        if not m:
            continue
        print(f"{label:<48} {m['n']:>6} {m['P']:>+8.4f} {m['S']:>+8.4f} {m['beta']:>+8.3f} "
              f"{m['sigma_ratio']:>8.3f} {m['bin_S']:>+7.3f} {m['top_bin_bps']:>+10.4f} "
              f"{m['mean_yhat_bps']:>+10.4f} {m['std_yhat_bps']:>8.3f}")
        if pf_p:
            print(f"  per-fold P: [{', '.join(f'{p:+.4f}' for p in pf_p)}], σ={np.std(pf_p):.4f}")
    print("=" * 100)


if __name__ == "__main__":
    main()

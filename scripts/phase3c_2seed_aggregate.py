"""
Phase3c 2-seed × 4-fold aggregation analysis.

For each fold:
- Compute per-fold metrics for seed=42 BEST/EMA, seed=7 BEST/EMA
- 2-seed value-blend median (anti-pattern #16: value-blend not rank-blend)

Then 4-fold pooled stride10 metrics for:
- single-seed (seed=42 BEST/EMA, seed=7 BEST/EMA)
- 2-seed median (BEST/EMA)

Compare to baseline_plus 3-seed median pooled (production CSV anchor):
- pooled stride10: P=+0.0577, S=+0.0751
- pooled dense:    P=+0.0497, S=+0.0586

Phase3c gate (per anti-pattern #17 anchor+0.005):
- P >= 0.063 AND S >= 0.080
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr


SEEDS = {
    "seed42": Path("experiments/y600_phase3c_pure/baseline"),
    "seed7":  Path("experiments/y600_phase3c_pure_seed7/baseline"),
}
FOLDS = [0, 1, 2, 3]


def load_fold(seed_dir: Path, fold: int, ckpt: str):
    """Load per-fold predictions. ckpt in {'best','ema'}."""
    fname = "test_preds.npz" if ckpt == "best" else "ema_test_preds.npz"
    path = seed_dir / f"fold_{fold}" / fname
    d = np.load(path)
    pred = d["predictions"][:, 1].astype(np.float64)  # q50
    tgt = d["targets"].astype(np.float64)
    msk = d["mask"].astype(bool)
    ts = d["timestamps"].astype(np.int64)
    return {"pred": pred, "tgt": tgt, "msk": msk, "ts": ts}


def metrics(yp: np.ndarray, y: np.ndarray):
    yp = yp.astype(np.float64)
    y = y.astype(np.float64)
    p = float(np.corrcoef(yp, y)[0, 1])
    s, _ = spearmanr(yp, y)
    sy = float(y.std())
    syp = float(yp.std())
    cov = float(np.cov(yp, y, ddof=0)[0, 1])
    beta_y_on_yhat = cov / (yp.var() + 1e-30)  # trading slope
    beta_yhat_on_y = cov / (y.var() + 1e-30)   # shrinkage
    r2_reg = 1 - float(((y - yp) ** 2).sum()) / float(((y - y.mean()) ** 2).sum() + 1e-30)
    da_mask = y != 0
    da = float(((np.sign(yp) == np.sign(y)) & da_mask).sum() / max(1, da_mask.sum()))
    return {
        "n": len(y), "P": p, "S": float(s),
        "sigma_yhat": syp, "sigma_y": sy, "shrink": syp / sy,
        "beta_y_on_yhat": beta_y_on_yhat, "beta_yhat_on_y": beta_yhat_on_y,
        "r2_reg": r2_reg, "DirAcc": da,
    }


def stride_subsample(arr: np.ndarray, mask: np.ndarray, stride: int = 10) -> np.ndarray:
    """Return indices of every stride-th masked entry."""
    idx = np.where(mask)[0]
    return idx[::stride]


def per_fold_table(ckpt: str) -> dict:
    """Per-fold metrics for each seed + 2-seed median, for given ckpt (best|ema)."""
    out = {}
    for fold in FOLDS:
        d42 = load_fold(SEEDS["seed42"], fold, ckpt)
        d7 = load_fold(SEEDS["seed7"], fold, ckpt)

        # Sanity: timestamps should match between seeds
        assert (d42["ts"] == d7["ts"]).all(), f"ts mismatch fold {fold}"
        assert (d42["msk"] == d7["msk"]).all(), f"mask mismatch fold {fold}"

        msk = d42["msk"]
        s10 = stride_subsample(np.zeros_like(msk), msk, stride=10)

        # 2-seed value-blend median (anti-pattern #16)
        med = np.median(np.stack([d42["pred"], d7["pred"]], axis=0), axis=0)

        # All metrics computed on stride10 subsample (clean)
        m42 = metrics(d42["pred"][s10], d42["tgt"][s10])
        m7 = metrics(d7["pred"][s10], d7["tgt"][s10])
        mmed = metrics(med[s10], d42["tgt"][s10])

        out[fold] = {
            "n_stride10": len(s10),
            "seed42": m42,
            "seed7": m7,
            "median_2seed": mmed,
            # Need raw arrays for pooling
            "_pred42_s10": d42["pred"][s10],
            "_pred7_s10":  d7["pred"][s10],
            "_predmed_s10": med[s10],
            "_tgt_s10":    d42["tgt"][s10],
            "_pred42_dense": d42["pred"][msk],
            "_pred7_dense":  d7["pred"][msk],
            "_predmed_dense": med[msk],
            "_tgt_dense":    d42["tgt"][msk],
        }
    return out


def pooled_metrics(per_fold: dict, key_preds: str, key_tgt: str = "_tgt_s10") -> dict:
    preds = np.concatenate([per_fold[f][key_preds] for f in FOLDS])
    tgts = np.concatenate([per_fold[f][key_tgt] for f in FOLDS])
    return metrics(preds, tgts)


def fmt_metric_row(label: str, m: dict) -> str:
    return (
        f"{label:<32} | n={m['n']:>5} | "
        f"P={m['P']:+.4f} S={m['S']:+.4f} | "
        f"σŷ/σy={m['shrink']:.3f} β_y_on_ŷ={m['beta_y_on_yhat']:+.3f} | "
        f"R²_reg={m['r2_reg']:+.5f} DirAcc={m['DirAcc']:.3f}"
    )


def main():
    print("=" * 110)
    print("PHASE3C 2-SEED × 4-FOLD AGGREGATION (stride10 unless noted)")
    print("=" * 110)
    print()

    for ckpt in ("best", "ema"):
        print(f"\n{'#' * 110}")
        print(f"# CHECKPOINT: {ckpt.upper()}")
        print(f"{'#' * 110}")
        per_fold = per_fold_table(ckpt)

        # Per-fold table
        print(f"\n--- Per-fold {ckpt.upper()} stride10 ---")
        for fold in FOLDS:
            f = per_fold[fold]
            print(f"\nFold {fold} (n={f['n_stride10']}):")
            print("  " + fmt_metric_row(f"seed=42 {ckpt}", f["seed42"]))
            print("  " + fmt_metric_row(f"seed=7  {ckpt}", f["seed7"]))
            print("  " + fmt_metric_row(f"median  {ckpt}", f["median_2seed"]))

        # Pooled across 4 folds
        print(f"\n--- POOLED 4-FOLD {ckpt.upper()} ---")
        pool42 = pooled_metrics(per_fold, "_pred42_s10")
        pool7 = pooled_metrics(per_fold, "_pred7_s10")
        poolmed = pooled_metrics(per_fold, "_predmed_s10")
        pool42_dense = pooled_metrics(per_fold, "_pred42_dense", "_tgt_dense")
        pool7_dense = pooled_metrics(per_fold, "_pred7_dense", "_tgt_dense")
        poolmed_dense = pooled_metrics(per_fold, "_predmed_dense", "_tgt_dense")

        print("\nstride10 pooled (clean):")
        print("  " + fmt_metric_row(f"seed=42 {ckpt}", pool42))
        print("  " + fmt_metric_row(f"seed=7  {ckpt}", pool7))
        print("  " + fmt_metric_row(f"median  {ckpt}", poolmed))

        print("\ndense pooled:")
        print("  " + fmt_metric_row(f"seed=42 {ckpt}", pool42_dense))
        print("  " + fmt_metric_row(f"seed=7  {ckpt}", pool7_dense))
        print("  " + fmt_metric_row(f"median  {ckpt}", poolmed_dense))

        # Per-fold P stability (baseline_plus had std=0.0181)
        per_fold_P = [per_fold[f]["median_2seed"]["P"] for f in FOLDS]
        per_fold_S = [per_fold[f]["median_2seed"]["S"] for f in FOLDS]
        print(f"\nPer-fold {ckpt} median P: [{per_fold_P[0]:.4f}, {per_fold_P[1]:.4f}, {per_fold_P[2]:.4f}, {per_fold_P[3]:.4f}]")
        print(f"  std={np.std(per_fold_P):.4f} mean={np.mean(per_fold_P):.4f} CoV={np.std(per_fold_P)/abs(np.mean(per_fold_P)):.3f}")
        print(f"Per-fold {ckpt} median S: [{per_fold_S[0]:.4f}, {per_fold_S[1]:.4f}, {per_fold_S[2]:.4f}, {per_fold_S[3]:.4f}]")
        print(f"  std={np.std(per_fold_S):.4f} mean={np.mean(per_fold_S):.4f} CoV={np.std(per_fold_S)/abs(np.mean(per_fold_S)):.3f}")

    # Anchor + gate
    print()
    print("=" * 110)
    print("ANCHOR (baseline_plus 3-seed median, production CSV)")
    print("=" * 110)
    print("  pooled stride10: P=+0.0577 S=+0.0751")
    print("  pooled dense:    P=+0.0497 S=+0.0586")
    print("  per-fold P [0.090, 0.066, 0.054] std=0.0181 CoV=0.27 (baseline_plus seed=42)")
    print()
    print("GATE (anti-pattern #17, anchor+0.005):")
    print("  pooled stride10 P>=0.063 AND S>=0.080 → PASS production replacement")
    print("  OR per-fold std drops > 50% with mean within ±0.005 → STABILITY WIN")


if __name__ == "__main__":
    main()

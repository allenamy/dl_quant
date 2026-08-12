"""Dump Ridge coefficient magnitudes per feature to understand where signal lives.

Reads per-day NPZs, does 80/20 temporal split, fits Ridge on flattened
last-timestep features, ranks features by |coef| / target_sigma to get
standardized effect size.  Also computes the per-feature marginal
correlation with y as a sanity check against multicollinearity.

CLI:
    python scripts/analyze_ridge_weights.py --npz-dir data/npz_full \
        --out experiments/v3_full/ridge_weights.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import List, Dict

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


def load_days(npz_dir: str) -> Dict:
    files = sorted(Path(npz_dir).glob("*.npz"))
    xs, ys, masks, days = [], [], [], []
    feature_names = None
    for p in files:
        d = np.load(p, allow_pickle=True)
        if "X" not in d.files or d["X"].shape[0] == 0:
            continue
        xs.append(d["X"][:, -1, :])  # last timestep only, matches Ridge baseline
        ys.append(d["y"])
        masks.append(d["y_mask"])
        days.append(p.stem)
        if feature_names is None and "features" in d.files:
            feature_names = [str(f) for f in d["features"]]
    return {
        "X": np.concatenate(xs, axis=0).astype(np.float64),
        "y": np.concatenate(ys, axis=0).astype(np.float64),
        "mask": np.concatenate(masks, axis=0).astype(bool),
        "days": days,
        "feature_names": feature_names or [f"f{i}" for i in range(xs[0].shape[-1])],
    }


def temporal_split(n: int, train_frac: float = 0.8) -> tuple[np.ndarray, np.ndarray]:
    cut = int(n * train_frac)
    idx = np.arange(n)
    return idx[:cut], idx[cut:]


def main(npz_dir: str, out_path: str, top_k: int = 20, alpha: float = 1.0) -> None:
    data = load_days(npz_dir)
    X, y, mask = data["X"], data["y"], data["mask"]
    valid = mask
    X, y = X[valid], y[valid]

    tr_idx, te_idx = temporal_split(len(X))
    scaler = StandardScaler().fit(X[tr_idx])
    X_tr = scaler.transform(X[tr_idx])
    X_te = scaler.transform(X[te_idx])

    ridge = Ridge(alpha=alpha, fit_intercept=True).fit(X_tr, y[tr_idx])
    coefs = ridge.coef_
    target_sigma = float(np.std(y[tr_idx]))

    # Standardized effect size = |coef| because X is standardized
    pred_te = ridge.predict(X_te)
    test_corr = float(np.corrcoef(pred_te, y[te_idx])[0, 1])

    # Per-feature marginal correlation for multicollinearity sanity check
    marginal = np.array([
        np.corrcoef(X_tr[:, i], y[tr_idx])[0, 1] for i in range(X_tr.shape[1])
    ])

    order = np.argsort(-np.abs(coefs))[:top_k]
    top_features = []
    for rank, i in enumerate(order, start=1):
        top_features.append({
            "rank": rank,
            "feature": data["feature_names"][i],
            "coef": float(coefs[i]),
            "abs_coef": float(abs(coefs[i])),
            "marginal_corr_with_y": float(marginal[i]),
        })

    report = {
        "n_train": int(len(tr_idx)),
        "n_test": int(len(te_idx)),
        "target_sigma": target_sigma,
        "test_correlation": test_corr,
        "top_features": top_features,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Ridge test_corr={test_corr:.4f} | top-{top_k} saved to {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--alpha", type=float, default=1.0)
    args = ap.parse_args()
    main(args.npz_dir, args.out, args.top_k, args.alpha)

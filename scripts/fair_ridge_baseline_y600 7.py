"""Fair Ridge baseline: includes BOTH 64 hand-crafted features AND raw LOB tensor.

V5 singh uses X (64 features) + X_raw (25 levels × 4 channels) via Path A + Path B.
Existing Ridge baseline only used X[t=-1, :] = 64 features per sample.
Not apples-to-apples.

This script: build Ridge with X[t=-1, :] (64) + X_raw[t=-1, :, :].flatten() (100)
                                          = 164-dim per-sample features.

Compare to V5 singh's 0.0617 P pool + Ridge_old 0.0352 P pool.

Ridge_LOB (164 dim) tests whether *linear* model can exploit raw LOB info
that V5 currently only DL can see.
"""
from __future__ import annotations
import argparse
import os
import pathlib
import json
from datetime import datetime, timedelta

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge


def get_fold_splits(npz_dir: pathlib.Path,
                     train_days_n: int = 700,
                     val_days_n: int = 60,
                     test_days_n: int = 90,
                     fold_stride: int = 60,
                     embargo: int = 1,
                     n_folds: int = 3):
    """Replicate walk-forward fold splits used by V5 singh."""
    all_days = sorted(p.stem for p in npz_dir.glob("20??-??-??.npz"))
    n_total = len(all_days)
    folds = []
    # The test sets we want match V5 singh's:
    # fold 0: test 2025-02-09..2025-05-11
    # fold 1: test 2025-04-10..2025-07-10
    # fold 2: test 2025-06-11..2025-09-09
    # Build by walk-forward
    test_starts = [
        all_days.index("2025-02-09"),
        all_days.index("2025-04-10"),
        all_days.index("2025-06-11"),
    ]
    for i, ts_idx in enumerate(test_starts):
        test = all_days[ts_idx:ts_idx + test_days_n]
        val_end = ts_idx - embargo
        val_start = val_end - val_days_n
        val = all_days[val_start:val_end]
        train_end = val_start - embargo
        train_start = max(0, train_end - train_days_n)
        train = all_days[train_start:train_end]
        folds.append({"train": train, "val": val, "test": test})
        print(f"Fold {i}: train {train[0]}..{train[-1]} ({len(train)}d), val {val[0]}..{val[-1]} ({len(val)}d), test {test[0]}..{test[-1]} ({len(test)}d)")
    return folds


def load_features(days, npz_dir, include_raw=True, raw_levels=25):
    """Load features for given days, return (X_features, y, mask, timestamps).

    X_features: (N, F) where F = 64 (X last) + 100 (X_raw last flattened) if include_raw.
    """
    Xs, ys, masks, tss = [], [], [], []
    for day in days:
        path = npz_dir / f"{day}.npz"
        if not path.exists():
            continue
        try:
            d = np.load(path, allow_pickle=True)
            X = d["X"]  # (N, T, 64)
            y = d["y_600"]
            m = d["y_mask_600"]
            ts = d["timestamps"] if "timestamps" in d.files else np.zeros(len(y), dtype=np.int64)
            # Last timestep features
            X_last = X[:, -1, :]  # (N, 64)
            if include_raw:
                X_raw = d["X_raw"]  # (N, T, L, 4)
                # truncate / pad to raw_levels
                L = X_raw.shape[2]
                if L >= raw_levels:
                    X_raw_use = X_raw[:, -1, :raw_levels, :]  # (N, raw_levels, 4)
                else:
                    pad = np.zeros((X_raw.shape[0], raw_levels - L, 4), dtype=X_raw.dtype)
                    X_raw_use = np.concatenate([X_raw[:, -1, :, :], pad], axis=1)
                X_raw_flat = X_raw_use.reshape(X_raw_use.shape[0], -1)  # (N, 100)
                X_combined = np.concatenate([X_last, X_raw_flat.astype(np.float32)], axis=1)
            else:
                X_combined = X_last
            Xs.append(X_combined)
            ys.append(y)
            masks.append(m)
            tss.append(ts)
        except Exception as e:
            print(f"  skip {day}: {e}")
            continue
    if not Xs:
        return None, None, None, None
    return (np.concatenate(Xs, axis=0).astype(np.float32),
            np.concatenate(ys, axis=0),
            np.concatenate(masks, axis=0),
            np.concatenate(tss, axis=0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz-dir", default="data/npz_v4")
    ap.add_argument("--out", default="experiments/baselines_fair_ridge_y600/results.json")
    ap.add_argument("--alpha", type=float, default=1.0)
    args = ap.parse_args()

    npz_dir = pathlib.Path(args.npz_dir)
    folds = get_fold_splits(npz_dir)

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = {}
    for variant_name, include_raw in [("Ridge_X_only_64dim", False), ("Ridge_X_LOB_164dim", True)]:
        print(f"\n=== {variant_name} ===")
        per_fold_results = []
        all_q, all_y = [], []
        for fold_idx, fold in enumerate(folds):
            print(f"  Fold {fold_idx}: loading train ({len(fold['train'])} days)...")
            X_train, y_train, m_train, _ = load_features(fold["train"], npz_dir, include_raw=include_raw)
            if X_train is None:
                continue
            # Normalize y (median + MAD-σ from train, like V5 does)
            train_valid = m_train.astype(bool)
            y_train_v = y_train[train_valid]
            y_med = np.median(y_train_v)
            y_mad = np.median(np.abs(y_train_v - y_med)) * 1.4826
            y_sigma = max(y_mad, 1e-9)
            y_train_z = np.clip((y_train - y_med) / y_sigma, -10, 10)
            # Drop masked rows
            X_train_use = X_train[train_valid]
            y_train_use = y_train_z[train_valid]
            print(f"    Fitting Ridge α={args.alpha} on (n={len(X_train_use)}, F={X_train.shape[1]})...")
            # Standardize features
            x_mean = X_train_use.mean(axis=0)
            x_std = X_train_use.std(axis=0)
            x_std = np.where(x_std < 1e-9, 1.0, x_std)
            X_train_norm = (X_train_use - x_mean) / x_std
            ridge = Ridge(alpha=args.alpha)
            ridge.fit(X_train_norm, y_train_use)
            # Test
            print(f"  Fold {fold_idx}: loading test ({len(fold['test'])} days)...")
            X_test, y_test, m_test, ts_test = load_features(fold["test"], npz_dir, include_raw=include_raw)
            test_valid = m_test.astype(bool)
            X_test_norm = (X_test - x_mean) / x_std
            q_z = ridge.predict(X_test_norm)
            # Convert to raw bps
            q = (q_z * y_sigma + y_med) * 1e4
            y = y_test * 1e4  # raw log-ret -> bps
            qm, ym = q[test_valid], y[test_valid]
            p = float(pearsonr(qm, ym)[0])
            s = float(spearmanr(qm, ym).correlation)
            sq, sy = qm.std(), ym.std()
            beta = float(np.cov(qm, ym)[0, 1] / max(sq**2, 1e-12))
            bias = float(qm.mean() - ym.mean())
            n = int(test_valid.sum())
            print(f"    test: P={p:+.4f} S={s:+.4f} β={beta:+.3f} σŷ/σy={sq/sy:.3f} bias={bias:+.3f}bps n={n}")
            per_fold_results.append({"fold": fold_idx, "n": n, "P": p, "S": s, "beta": beta,
                                       "sigma_ratio": float(sq/sy), "bias_bps": bias})
            all_q.append(qm); all_y.append(ym)
        # Pool
        Q = np.concatenate(all_q); Y = np.concatenate(all_y)
        Pp = float(pearsonr(Q, Y)[0])
        Sp = float(spearmanr(Q, Y).correlation)
        SQ, SY = Q.std(), Y.std()
        Bp = float(np.cov(Q, Y)[0, 1] / max(SQ**2, 1e-12))
        bias_p = float(Q.mean() - Y.mean())
        print(f"  POOLED n={len(Q)} P={Pp:+.4f} S={Sp:+.4f} β={Bp:+.3f} σŷ/σy={SQ/SY:.3f} bias={bias_p:+.3f}bps")
        per_fold_p_std = float(np.std([r["P"] for r in per_fold_results]))
        results[variant_name] = {
            "per_fold": per_fold_results,
            "pool": {"n": int(len(Q)), "P": Pp, "S": Sp, "beta": Bp,
                       "sigma_ratio": float(SQ/SY), "bias_bps": bias_p,
                       "per_fold_P_std": per_fold_p_std},
        }
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\n→ {out_path}")


if __name__ == "__main__":
    main()

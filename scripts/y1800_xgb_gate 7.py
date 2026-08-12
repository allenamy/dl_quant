"""XGBoost walk-forward gate on y_1800 (mirror of y1800_ridge_gate.py).

Establishes non-linear ceiling on the V4 49-feat handcrafted feature space.
Comparison ladder:
  Ridge      — linear ceiling
  XGBoost    — non-linear (tree) ceiling   ← THIS SCRIPT
  V4 DL      — sequence model

If XGB ≈ Ridge: feature space exhausted, non-linear gives nothing.
If XGB > Ridge significantly but DL ≤ XGB: DL architecture is wasting capacity.
If DL > XGB: sequence/representation learning extracts beyond static features.

Usage:
  python scripts/y1800_xgb_gate.py --feats v4 --npz-dir data/npz_v4_y1800 \\
      --out experiments/y1800_calib/xgb_gate_v4.txt
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

import numpy as np
from scipy.stats import pearsonr, spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

try:
    import xgboost as xgb
except ImportError:
    sys.exit("ERROR: xgboost not installed. pip install xgboost")


def load_features(npz_dir: pathlib.Path, day_str: str):
    f = npz_dir / f"{day_str}.npz"
    if not f.exists():
        return None
    d = np.load(f, allow_pickle=True)
    X = d["X"]
    y = d.get("y_1800")
    m = d.get("y_mask_1800")
    if y is None or m is None:
        return None
    X_last = np.asarray(X[:, -1, :], dtype=np.float32)
    y = np.asarray(y, dtype=np.float32).ravel()
    m = np.asarray(m).astype(bool).ravel()
    return X_last, y, m


def walk_forward_folds(days, train_days=700, val_days=30, test_days=90, stride=60):
    folds = []
    n = len(days)
    start = 0
    while start + train_days + val_days + test_days <= n:
        tr = days[start:start + train_days]
        va = days[start + train_days:start + train_days + val_days]
        te = days[start + train_days + val_days:start + train_days + val_days + test_days]
        folds.append((tr, va, te))
        start += stride
    return folds


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz-dir", type=pathlib.Path, default=pathlib.Path("data/npz_v4_y1800"))
    ap.add_argument("--out", type=pathlib.Path,
                    default=pathlib.Path("experiments/y1800_calib/xgb_gate_v4.txt"))
    ap.add_argument("--max-depth", type=int, default=5)
    ap.add_argument("--n-estimators", type=int, default=2000)
    ap.add_argument("--learning-rate", type=float, default=0.02)
    ap.add_argument("--subsample", type=float, default=0.8)
    ap.add_argument("--colsample-bytree", type=float, default=0.7)
    ap.add_argument("--early-stopping-rounds", type=int, default=50)
    ap.add_argument("--reg-lambda", type=float, default=1.0)
    ap.add_argument("--n-jobs", type=int, default=8)
    args = ap.parse_args()

    days = sorted(p.stem for p in args.npz_dir.glob("*.npz")
                  if p.stem != "BUILD_INFO")
    print(f"NPZ dir: {args.npz_dir}")
    print(f"Total days: {len(days)}")
    if not days:
        sys.exit(f"ERROR: no NPZ files in {args.npz_dir}")

    folds = walk_forward_folds(days)
    print(f"Folds built: {len(folds)}")
    if not folds:
        sys.exit("ERROR: not enough days for walk-forward")

    pooled_yp, pooled_y = [], []
    fold_results = []
    for fi, (tr, va, te) in enumerate(folds):
        t0 = time.time()
        # Train
        Xs, ys = [], []
        for d in tr:
            r = load_features(args.npz_dir, d)
            if r is None: continue
            X, y, m = r
            Xs.append(X[m]); ys.append(y[m])
        # Val
        Xs_v, ys_v = [], []
        for d in va:
            r = load_features(args.npz_dir, d)
            if r is None: continue
            X, y, m = r
            Xs_v.append(X[m]); ys_v.append(y[m])
        # Test
        Xs_te, ys_te = [], []
        for d in te:
            r = load_features(args.npz_dir, d)
            if r is None: continue
            X, y, m = r
            Xs_te.append(X[m]); ys_te.append(y[m])
        if not Xs or not Xs_te:
            print(f"Fold {fi}: empty, skip"); continue
        Xtr = np.concatenate(Xs); ytr = np.concatenate(ys)
        Xv = np.concatenate(Xs_v) if Xs_v else None
        yv = np.concatenate(ys_v) if ys_v else None
        Xte = np.concatenate(Xs_te); yte = np.concatenate(ys_te)
        # Standardize on train moments (helps XGB convergence consistency)
        mu = Xtr.mean(axis=0, dtype=np.float64)
        sd = Xtr.std(axis=0, dtype=np.float64) + 1e-9
        Xtr = ((Xtr - mu) / sd).astype(np.float32)
        if Xv is not None:
            Xv = ((Xv - mu) / sd).astype(np.float32)
        Xte = ((Xte - mu) / sd).astype(np.float32)

        model = xgb.XGBRegressor(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            learning_rate=args.learning_rate,
            subsample=args.subsample,
            colsample_bytree=args.colsample_bytree,
            reg_lambda=args.reg_lambda,
            objective="reg:squarederror",
            tree_method="hist",
            n_jobs=args.n_jobs,
            early_stopping_rounds=args.early_stopping_rounds,
        )
        eval_set = [(Xv, yv)] if Xv is not None else None
        model.fit(Xtr, ytr, eval_set=eval_set, verbose=False)
        yp = model.predict(Xte)

        rho_d = pearsonr(yp, yte)[0]; sp_d = spearmanr(yp, yte)[0]
        ix = np.arange(0, len(yp), 10)
        rho_c = pearsonr(yp[ix], yte[ix])[0]; sp_c = spearmanr(yp[ix], yte[ix])[0]
        n_iter = model.best_iteration if hasattr(model, "best_iteration") else args.n_estimators
        fold_results.append((fi, rho_c, sp_c, rho_d, sp_d, len(Xte), n_iter, time.time() - t0))
        print(f"Fold {fi}: tr={len(Xtr):>7d} te={len(Xte):>7d} | "
              f"dense P={rho_d:+.4f} S={sp_d:+.4f} | "
              f"clean P={rho_c:+.4f} S={sp_c:+.4f} | "
              f"best_iter={n_iter} | {time.time()-t0:.1f}s")
        pooled_yp.append(yp); pooled_y.append(yte)

    if not pooled_yp:
        sys.exit("ERROR: no folds produced predictions")

    yp_all = np.concatenate(pooled_yp); y_all = np.concatenate(pooled_y)
    rho_d, sp_d = pearsonr(yp_all, y_all)[0], spearmanr(yp_all, y_all)[0]
    ix = np.arange(0, len(yp_all), 10)
    rho_c, sp_c = pearsonr(yp_all[ix], y_all[ix])[0], spearmanr(yp_all[ix], y_all[ix])[0]
    summary = (
        f"POOLED XGB (v4-49feat, N_clean={len(ix)}, N_dense={len(yp_all)}): "
        f"clean P={rho_c:+.4f} S={sp_c:+.4f} | dense P={rho_d:+.4f} S={sp_d:+.4f}"
    )
    print(f"\n{summary}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        f.write(summary + "\n")
        f.write(f"clean_P {rho_c:.6f}\n")
        f.write(f"clean_S {sp_c:.6f}\n")
        f.write(f"dense_P {rho_d:.6f}\n")
        f.write(f"dense_S {sp_d:.6f}\n")
        f.write(f"N_clean {len(ix)}\n")
        f.write(f"N_dense {len(yp_all)}\n")
        f.write(f"hyperparams max_depth={args.max_depth} n_est={args.n_estimators} "
                f"lr={args.learning_rate} subsample={args.subsample} "
                f"colsample={args.colsample_bytree} reg_lambda={args.reg_lambda}\n")
        for fi, rc, sc, rd, sd, n, it, t in fold_results:
            f.write(f"fold_{fi} clean_P {rc:.6f} clean_S {sc:.6f} dense_P {rd:.6f} "
                    f"dense_S {sd:.6f} N {n} best_iter {it} time_s {t:.1f}\n")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

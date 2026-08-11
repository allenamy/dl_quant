"""Ridge walk-forward gate on y_1800.

Two stages:
  --feats v4    : Ridge on V4 64 handcrafted features only (last timestep).
  --feats v4_lc : Ridge on V4 64 + 6 long-context features (from
                  data/npz_v4_smooth/<date>.npz overlay if present per day).

Pre-declared pass gates:
  Stage 1 (v4): pooled clean Pearson >= 0.012  → proceed to V4 DL training.
  Stage 2 (v4_lc): ΔP vs Stage 1 >= +0.005     → include LC features in DL.

Output: per-fold + pooled metrics. Writes a one-line summary to
experiments/y1800_calib/ridge_gate_<feats>.txt for downstream comparison.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


def load_features(npz_dir: pathlib.Path, day_str: str, feat_mode: str):
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

    if feat_mode == "v4":
        return X_last, y, m
    elif feat_mode == "v4_lc":
        ov = pathlib.Path("data/npz_v4_smooth") / f"{day_str}.npz"
        if not ov.exists():
            return X_last, y, m
        d2 = np.load(ov, allow_pickle=True)
        lc = d2.get("long_context_feats")
        if lc is None or lc.shape[0] != X_last.shape[0]:
            return X_last, y, m
        X_full = np.concatenate([X_last, np.asarray(lc, dtype=np.float32)], axis=1)
        return X_full, y, m
    else:
        raise ValueError(f"unknown feat_mode {feat_mode!r}")


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
    ap.add_argument("--feats", choices=["v4", "v4_lc"], default="v4")
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="Write summary line to this file. Default: "
                         "experiments/y1800_calib/ridge_gate_<feats>.txt")
    ap.add_argument("--alpha", type=float, default=10.0,
                    help="Ridge alpha. Default 10.0.")
    args = ap.parse_args()

    days = sorted(p.stem for p in args.npz_dir.glob("*.npz")
                  if p.stem != "BUILD_INFO")
    print(f"NPZ dir: {args.npz_dir}")
    print(f"Total days: {len(days)}")
    if not days:
        sys.exit(f"ERROR: no NPZ files found in {args.npz_dir}")

    folds = walk_forward_folds(days)
    print(f"Folds built: {len(folds)}")
    if not folds:
        sys.exit("ERROR: not enough days for any walk-forward fold")

    pooled_yp, pooled_y = [], []
    for fi, (tr, va, te) in enumerate(folds):
        Xs_tr, ys_tr = [], []
        for d in tr:
            r = load_features(args.npz_dir, d, args.feats)
            if r is None: continue
            X, y, m = r
            Xs_tr.append(X[m]); ys_tr.append(y[m])
        Xs_te, ys_te = [], []
        for d in te:
            r = load_features(args.npz_dir, d, args.feats)
            if r is None: continue
            X, y, m = r
            Xs_te.append(X[m]); ys_te.append(y[m])
        if not Xs_tr or not Xs_te:
            print(f"Fold {fi}: empty, skip"); continue
        Xtr = np.concatenate(Xs_tr); ytr = np.concatenate(ys_tr)
        Xte = np.concatenate(Xs_te); yte = np.concatenate(ys_te)
        # Standardize on train moments
        mu = Xtr.mean(axis=0, dtype=np.float64)
        sd = Xtr.std(axis=0, dtype=np.float64) + 1e-9
        Xtr = ((Xtr - mu) / sd).astype(np.float32)
        Xte = ((Xte - mu) / sd).astype(np.float32)
        # Ridge fit + predict
        model = Ridge(alpha=args.alpha).fit(Xtr, ytr)
        yp = model.predict(Xte)
        rho_d = pearsonr(yp, yte)[0]; sp_d = spearmanr(yp, yte)[0]
        ix = np.arange(0, len(yp), 10)
        rho_c = pearsonr(yp[ix], yte[ix])[0]; sp_c = spearmanr(yp[ix], yte[ix])[0]
        print(f"Fold {fi}: tr={len(Xtr):>7d} te={len(Xte):>7d} | "
              f"dense P={rho_d:+.4f} S={sp_d:+.4f} | "
              f"clean P={rho_c:+.4f} S={sp_c:+.4f}")
        pooled_yp.append(yp); pooled_y.append(yte)

    if not pooled_yp:
        sys.exit("ERROR: no folds produced predictions")

    yp_all = np.concatenate(pooled_yp); y_all = np.concatenate(pooled_y)
    rho_d, sp_d = pearsonr(yp_all, y_all)[0], spearmanr(yp_all, y_all)[0]
    ix = np.arange(0, len(yp_all), 10)
    rho_c, sp_c = pearsonr(yp_all[ix], y_all[ix])[0], spearmanr(yp_all[ix], y_all[ix])[0]
    summary = (
        f"POOLED ({args.feats}, N_clean={len(ix)}, N_dense={len(yp_all)}): "
        f"clean P={rho_c:+.4f} S={sp_c:+.4f} | dense P={rho_d:+.4f} S={sp_d:+.4f}"
    )
    print(f"\n{summary}")

    gate = 0.012
    print(f"Gate Stage 1 (clean P >= {gate:+.4f}): "
          f"{'PASS' if rho_c >= gate else 'FAIL'}")

    out = args.out or pathlib.Path(f"experiments/y1800_calib/ridge_gate_{args.feats}.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        f.write(summary + "\n")
        f.write(f"clean_P {rho_c:.6f}\n")
        f.write(f"clean_S {sp_c:.6f}\n")
        f.write(f"dense_P {rho_d:.6f}\n")
        f.write(f"dense_S {sp_d:.6f}\n")
        f.write(f"N_clean {len(ix)}\n")
        f.write(f"N_dense {len(yp_all)}\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

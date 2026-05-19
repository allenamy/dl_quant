"""V5-push Phase 1B: Ridge train-window length ablation.

Question: 700 days is V5's current train. Is shorter window better for current regime?
Spans far past (FTX → ETF → halving → 2025 mature). Distant past may dilute recent regime signal.

Run 4 variants: train_days ∈ {200, 400, 700, 1000} × 3-fold walk-forward.
Holding val=60, test=90, embargo=1 fixed.

Hypothesis to falsify: pool P drops monotonically as train_days shrinks.
Hypothesis to support: 200-400d ≥ 700d on current regime tests.

Uses V5's 64 features only (no novel features here — keep this ablation clean).
"""
from __future__ import annotations
import argparse
import json
import pathlib
import time
from typing import List

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge

NPZ_DIR = pathlib.Path("data/npz_v4")


def get_v5_fold_with_window(npz_dir, test_starts, train_days_n, val_days_n=60,
                              test_days_n=90, embargo=1):
    all_days = sorted(p.stem for p in npz_dir.glob("20??-??-??.npz"))
    folds = []
    for ts_str in test_starts:
        if ts_str not in all_days:
            raise RuntimeError(f"test start {ts_str} not in NPZ dir")
        ts_idx = all_days.index(ts_str)
        test = all_days[ts_idx:ts_idx + test_days_n]
        val_end = ts_idx - embargo
        val_start = val_end - val_days_n
        val = all_days[val_start:val_end]
        train_end = val_start - embargo
        train_start = max(0, train_end - train_days_n)
        train = all_days[train_start:train_end]
        folds.append({"train": train, "val": val, "test": test, "ts": ts_str})
    return folds


def load(days, label="?"):
    Xs, ys, ms = [], [], []
    t0 = time.time()
    for i, day in enumerate(days):
        p = NPZ_DIR / f"{day}.npz"
        if not p.exists(): continue
        z = np.load(p, allow_pickle=True)
        Xs.append(z["X"][:, -1, :].astype(np.float32))
        ys.append(z["y_600"])
        ms.append(z["y_mask_600"])
        if (i+1) % 200 == 0:
            print(f"  [{label}] loaded {i+1}/{len(days)} ({time.time()-t0:.0f}s)", flush=True)
    return (np.concatenate(Xs).astype(np.float32),
            np.concatenate(ys).astype(np.float32),
            np.concatenate(ms).astype(np.float32))


def fit_eval(Xtr, ytr_z, Xte, yte, mte, y_med, y_sigma, alpha=1.0):
    xm, xs = Xtr.mean(0), Xtr.std(0)
    xs = np.where(xs < 1e-9, 1.0, xs)
    Xtn = ((Xtr - xm) / xs).astype(np.float32)
    Xen = ((Xte - xm) / xs).astype(np.float32)
    Xtn = np.nan_to_num(Xtn, nan=0.0, posinf=0.0, neginf=0.0)
    Xen = np.nan_to_num(Xen, nan=0.0, posinf=0.0, neginf=0.0)
    r = Ridge(alpha=alpha).fit(Xtn, ytr_z)
    qz = r.predict(Xen)
    qbps = (qz * y_sigma + y_med) * 1e4
    ybps = yte * 1e4
    v = mte.astype(bool)
    qm, ym = qbps[v], ybps[v]
    P = float(pearsonr(qm, ym)[0])
    S = float(spearmanr(qm, ym).correlation)
    sq, sy = qm.std(), ym.std()
    beta = float(np.cov(qm, ym)[0,1] / max(sq**2, 1e-12))
    return {"P": P, "S": S, "beta": beta, "sigma_ratio": float(sq/sy), "n": int(v.sum()), "qm": qm, "ym": ym}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="experiments/v5push_phase1b/train_window_ablation.json")
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--windows", default="200,400,700,1000")
    args = ap.parse_args()
    windows = [int(x) for x in args.windows.split(",")]
    test_starts = ("2025-02-09", "2025-04-10", "2025-06-11")

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {"alpha": args.alpha, "windows": {}}
    print(f"Ridge train-window ablation: {windows} days × 3 folds × 64 features")
    for w in windows:
        print(f"\n=== train_days = {w} ===")
        folds = get_v5_fold_with_window(NPZ_DIR, test_starts, w)
        per_fold = []
        pool_q, pool_y = [], []
        for fi, fold in enumerate(folds):
            print(f"  fold {fi} (test {fold['ts']}): train {fold['train'][0] if fold['train'] else 'EMPTY'}..{fold['train'][-1] if fold['train'] else 'EMPTY'} ({len(fold['train'])}d)")
            if not fold["train"]:
                print(f"    SKIP fold {fi}: insufficient train days for window={w}")
                continue
            Xtr, ytr, mtr = load(fold["train"], label=f"w{w}-f{fi}-tr")
            Xte, yte, mte = load(fold["test"], label=f"w{w}-f{fi}-te")
            vtr = mtr.astype(bool)
            y_med = float(np.median(ytr[vtr]))
            y_sigma = max(float(np.median(np.abs(ytr[vtr]-y_med)) * 1.4826), 1e-9)
            ytr_z = np.clip((ytr - y_med) / y_sigma, -10, 10).astype(np.float32)
            r = fit_eval(Xtr[vtr], ytr_z[vtr], Xte, yte, mte, y_med, y_sigma, alpha=args.alpha)
            print(f"    Ridge w={w} fold {fi}: P={r['P']:+.4f} S={r['S']:+.4f} β={r['beta']:+.3f} σŷ/σy={r['sigma_ratio']:.3f} n={r['n']:,}", flush=True)
            per_fold.append({k:v for k,v in r.items() if k not in ('qm','ym')})
            pool_q.append(r["qm"]); pool_y.append(r["ym"])

        if not pool_q:
            summary["windows"][str(w)] = {"per_fold": [], "pool": None}
            continue
        Q = np.concatenate(pool_q); Y = np.concatenate(pool_y)
        Pp = float(pearsonr(Q, Y)[0]); Sp = float(spearmanr(Q, Y).correlation)
        sq, sy = Q.std(), Y.std()
        bp = float(np.cov(Q, Y)[0,1] / max(sq**2, 1e-12))
        std_P = float(np.std([r["P"] for r in per_fold]))
        print(f"  POOL w={w}: P={Pp:+.4f} S={Sp:+.4f} β={bp:+.3f} σŷ/σy={sq/sy:.3f} per-fold P-std={std_P:.4f}")
        summary["windows"][str(w)] = {
            "per_fold": per_fold,
            "pool": {"P": Pp, "S": Sp, "beta": bp, "sigma_ratio": float(sq/sy),
                       "n": int(len(Q)), "per_fold_P_std": std_P},
        }
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2, default=float)

    print(f"\n=== WINDOW ABLATION SUMMARY ===")
    for w in windows:
        p = summary["windows"].get(str(w), {}).get("pool")
        if p is None: print(f"  w={w:>5}: SKIPPED"); continue
        print(f"  w={w:>5}: pool P={p['P']:+.4f} S={p['S']:+.4f} σŷ/σy={p['sigma_ratio']:.3f} std_P={p['per_fold_P_std']:.4f}")
    print(f"\n→ {out_path}")


if __name__ == "__main__":
    main()

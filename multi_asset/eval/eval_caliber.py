"""Dual-caliber RAW perp eval: DENSE (all windows) + CLEAN (non-overlap >=600s, multi-offset).

> **created:** 2026-06-23 | **Session:** v2-dual-source-arch (caliber audit) | **状态:** in-progress

Anti-pattern #2/#19: the project's HONEST caliber is CLEAN (stride >= horizon, no
overlapping label windows). Dense (stride 180) overlaps labels -> correlated samples.
clean>dense is UNUSUAL and demands scrutiny. This reports BOTH for every preds file:
  DENSE : all test windows (q50 vs raw perp y, Pearson/Spearman/beta/sigma)
  CLEAN : greedy non-overlapping subsample (next ts >= last_kept_ts + horizon),
          averaged over `n_offsets` start offsets for robustness.

Usage: python multi_asset/eval/eval_caliber.py --preds <fold_0/test_preds.npz> [--horizon 600]
"""
from __future__ import annotations

import argparse
import os.path as p

import numpy as np


def _score(q, y):
    q = np.asarray(q, np.float64); y = np.asarray(y, np.float64)
    if q.size < 5 or q.std() < 1e-15 or y.std() < 1e-15:
        return dict(N=int(q.size), P=0.0, S=0.0, beta=0.0, sigma=0.0)
    from scipy.stats import spearmanr
    P = float(np.corrcoef(q, y)[0, 1])
    S = float(spearmanr(q, y).statistic)
    if not np.isfinite(S):
        S = 0.0
    beta = float(np.cov(q, y)[0, 1] / np.var(q))
    sigma = float(q.std() / y.std())
    return dict(N=int(q.size), P=P, S=S, beta=beta, sigma=sigma)


def _clean_indices(ts_sorted, horizon_us, offset):
    """Greedy non-overlapping selection starting from window `offset`."""
    keep = []
    last = -np.inf
    for i in range(offset, ts_sorted.size):
        if ts_sorted[i] >= last + horizon_us:
            keep.append(i); last = ts_sorted[i]
    return np.array(keep, dtype=np.int64)


def eval_file(preds_path, horizon_sec=600, n_offsets=4):
    z = np.load(preds_path)
    preds = z["predictions"]; q = (preds[:, 1] if preds.ndim == 2 else preds).astype(np.float64)
    t = z["targets"].astype(np.float64)
    m = z["mask"].astype(bool) if "mask" in z else np.ones(q.shape, bool)
    ts = z["timestamps"].astype(np.int64) if "timestamps" in z else np.arange(q.size)
    q, t, ts = q[m], t[m], ts[m]
    o = np.argsort(ts); q, t, ts = q[o], t[o], ts[o]

    dense = _score(q, t)
    # clean: multi-offset non-overlapping
    hus = horizon_sec * 1_000_000
    # offsets spaced across the stride span
    span = max(1, int(np.median(np.diff(ts)) // 1_000_000)) if ts.size > 1 else 1
    offs = [int(round(k * (ts.size / max(n_offsets, 1)) / 50)) for k in range(n_offsets)]
    offs = sorted(set([0] + [min(o_, 5) for o_ in range(n_offsets)]))[:n_offsets]
    cleans = []
    for off in range(n_offsets):
        idx = _clean_indices(ts, hus, off)
        if idx.size >= 5:
            cleans.append(_score(q[idx], t[idx]))
    if cleans:
        clean = {k: float(np.mean([c[k] for c in cleans])) for k in ("P", "S", "beta", "sigma")}
        clean["N"] = int(np.mean([c["N"] for c in cleans]))
        clean["n_off"] = len(cleans)
        clean["P_std"] = float(np.std([c["P"] for c in cleans]))
    else:
        clean = dict(N=0, P=0.0, S=0.0, beta=0.0, sigma=0.0, n_off=0, P_std=0.0)
    return dense, clean


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True)
    ap.add_argument("--horizon", type=int, default=600)
    ap.add_argument("--ema", action="store_true")
    args = ap.parse_args()
    targets = [args.preds]
    if args.ema:
        e = p.join(p.dirname(args.preds), "ema_test_preds.npz")
        if p.exists(e):
            targets.append(e)
    for tp in targets:
        if not p.exists(tp):
            print(f"MISSING {tp}"); continue
        dense, clean = eval_file(tp, args.horizon)
        tag = "EMA " if "ema" in p.basename(tp) else "BEST"
        print(f"{tag} {p.dirname(tp).split('/')[-2]}")
        print(f"  DENSE: N={dense['N']:5d} P={dense['P']:+.4f} S={dense['S']:+.4f} "
              f"beta={dense['beta']:+.3f} sigma={dense['sigma']:.3f}")
        print(f"  CLEAN: N={clean['N']:5d} P={clean['P']:+.4f} (off-std {clean.get('P_std',0):.4f}) "
              f"S={clean['S']:+.4f} beta={clean['beta']:+.3f} sigma={clean['sigma']:.3f} "
              f"[{clean.get('n_off',0)} offsets]")


if __name__ == "__main__":
    main()

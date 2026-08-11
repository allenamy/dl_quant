"""eval_dual_target — score one fold's test_preds.npz against BOTH spot & perp y_600.

> **created:** 2026-06-22 | **Session:** v2-dual-source-arch | **状态:** in-progress

The decisive root-cause test: a model trained on EITHER target (perp y_600 OR the
cleaner y_spot_600) emits q50 predictions whose RAW Pearson we want to read off
against BOTH labels — using the SAME predictions, joined by exact timestamp to the
npz_v2arch cache (which carries y_600 + y_spot_600 + their masks).

RAW caliber (matches the user's snippet): q50 = predictions[:, 1] (DAQH [q10,q50,q90]);
de-standardize q to raw via q*y_sigma + y_median; join target by ts; mask both
preds-mask AND the target's own mask; sort by ts; then
  P = corr(q_raw, y_raw)
  S = spearman(q_raw, y_raw)
  beta = cov(q_raw, y_raw) / var(q_raw)
  sigma = std(q_raw) / std(y_raw)
Pearson/Spearman/beta/sigma are affine-invariant so the de-standardize is optional
for P/S but keeps beta/sigma in raw units.

Usage:
  python multi_asset/eval/eval_dual_target.py \
      --preds experiments/v2arch/<run>/fold_0/test_preds.npz \
      --cache data/npz_v2arch
  # add --ema to also score fold_0/ema_test_preds.npz
"""
from __future__ import annotations

import argparse
import glob
import os.path as p

import numpy as np


def _load_target_lut(cache_dir: str, ykey: str, mkey: str):
    lut = {}
    files = sorted(glob.glob(p.join(cache_dir, "*.npz")))
    for f in files:
        if not p.basename(f)[0].isdigit():
            continue
        z = np.load(f, allow_pickle=True)
        if ykey not in z.files or "timestamps" not in z.files:
            continue
        ts = z["timestamps"].astype(np.int64)
        y = z[ykey].astype(np.float64)
        if mkey in z.files:
            m = z[mkey].astype(bool)
        else:
            m = np.ones(y.shape, bool)
        m = m & np.isfinite(y)
        for t, yy in zip(ts[m], y[m]):
            lut[int(t)] = float(yy)
    return lut


def _score(q_raw, y_raw):
    q = np.asarray(q_raw, np.float64)
    y = np.asarray(y_raw, np.float64)
    if q.size < 5 or np.std(q) < 1e-15 or np.std(y) < 1e-15:
        return dict(N=int(q.size), P=0.0, S=0.0, beta=0.0, sigma=0.0)
    P = float(np.corrcoef(q, y)[0, 1])
    # spearman via rank corr
    from scipy.stats import spearmanr
    S = float(spearmanr(q, y).statistic)
    if not np.isfinite(S):
        S = 0.0
    cov = float(np.mean((q - q.mean()) * (y - y.mean())))
    beta = cov / float(np.var(q))
    sigma = float(np.std(q) / np.std(y))
    return dict(N=int(q.size), P=P, S=S, beta=beta, sigma=sigma)


def eval_one(preds_path: str, cache_dir: str):
    z = np.load(preds_path)
    preds = z["predictions"]
    q50 = preds[:, 1] if preds.ndim == 2 else preds
    ts = z["timestamps"].astype(np.int64)
    mask = z["mask"].astype(bool) if "mask" in z else np.ones(ts.shape, bool)
    y_sigma = float(z["y_sigma"]) if "y_sigma" in z else 1.0
    y_median = float(z["y_median"]) if "y_median" in z else 0.0
    q_raw_all = q50.astype(np.float64) * y_sigma + y_median

    out = {}
    for name, ykey, mkey in (("PERP", "y_600", "y_mask_600"),
                             ("SPOT", "y_spot_600", "y_mask_spot_600")):
        lut = _load_target_lut(cache_dir, ykey, mkey)
        y_raw = np.full(ts.shape, np.nan, np.float64)
        hit = np.zeros(ts.shape, bool)
        for i, t in enumerate(ts):
            v = lut.get(int(t))
            if v is not None:
                y_raw[i] = v
                hit[i] = True
        keep = hit & mask & np.isfinite(q_raw_all)
        order = np.argsort(ts[keep])
        sc = _score(q_raw_all[keep][order], y_raw[keep][order])
        sc["hit_frac"] = float(keep.sum() / max(ts.size, 1))
        out[name] = sc
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True, help="fold_*/test_preds.npz")
    ap.add_argument("--cache", default="data/npz_v2arch")
    ap.add_argument("--ema", action="store_true",
                    help="also score the sibling ema_test_preds.npz")
    args = ap.parse_args()

    targets = [args.preds]
    if args.ema:
        ema = p.join(p.dirname(args.preds), "ema_test_preds.npz")
        if p.exists(ema):
            targets.append(ema)

    for tp in targets:
        if not p.exists(tp):
            print(f"[eval] MISSING {tp}")
            continue
        res = eval_one(tp, args.cache)
        tag = "EMA " if "ema" in p.basename(tp) else "BEST"
        print(f"\n=== {tag} {tp} ===")
        for name in ("PERP", "SPOT"):
            r = res[name]
            print(f"  ->{name}: N={r['N']:6d} hit={r['hit_frac']:.2f} | "
                  f"P={r['P']:+.4f} S={r['S']:+.4f} beta={r['beta']:+.3f} "
                  f"sigma={r['sigma']:.3f}")


if __name__ == "__main__":
    main()

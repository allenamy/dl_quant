"""Shuffle-null on the DL trajectory's own saved predictions (RIGOR: confirm the per-month Pearson is not an
artifact of overlapping-window autocorrelation / chance alignment). For a chosen month, take the saved
(pred q50, target) pair and compute:
  - REAL DENSE Pearson (all windows) + REAL per-day-CLEAN Pearson.
  - NULL: permute targets N times and recompute DENSE Pearson -> null mean+-sd, z-stat, empirical p.
  - BLOCK-NULL: permute targets in contiguous blocks (preserves y autocorrelation) -> stricter null;
    if real >> block-null too, the signal is not just y-AR1 aligning with slow preds.
Decisive: real Pearson must be > ~3 sigma above the iid-null AND above the block-null mean.
Run on SERVER: PYTHONPATH=. python multi_asset/eval/shuffle_null_preds.py --month 2025_11 [--ema] [--nperm 200]
"""
from __future__ import annotations
import numpy as np, os, argparse
from scipy.stats import pearsonr
HZ = 600 * 1_000_000

def clean_perday_P(q, y, ts):
    daykey = ts // (86400 * 1_000_000); rs = []
    for dk in np.unique(daykey):
        m = daykey == dk
        o = np.argsort(ts[m]); tsm = ts[m][o]; qm = q[m][o]; ym = y[m][o]
        keep = []; last = -1e18
        for i in range(len(tsm)):
            if tsm[i] - last >= HZ: keep.append(i); last = tsm[i]
        if len(keep) > 20:
            qk = qm[keep]; yk = ym[keep]
            if qk.std() > 1e-12:
                r = pearsonr(qk, yk)[0]
                if np.isfinite(r): rs.append(r)
    return float(np.mean(rs)) if rs else np.nan

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--ema", action="store_true")
    ap.add_argument("--nperm", type=int, default=200)
    ap.add_argument("--dir", default="experiments/wfEMA_lq05")
    a = ap.parse_args()
    fn = f"{a.dir}/wf_{a.month}/fold_0/{'ema_' if a.ema else ''}test_preds.npz"
    if not os.path.exists(fn):
        print(f"MISSING {fn}"); return
    z = np.load(fn, allow_pickle=True)
    pr = z["predictions"]; q = (pr[:, 1] if pr.ndim == 2 else pr).astype(np.float64)
    y = z["targets"].astype(np.float64); ts = z["timestamps"].astype(np.int64)
    o = np.argsort(ts); q, y, ts = q[o], y[o], ts[o]
    realD = pearsonr(q, y)[0]; realC = clean_perday_P(q, y, ts)
    rng = np.random.default_rng(0)
    # iid null
    iid = np.array([pearsonr(q, rng.permutation(y))[0] for _ in range(a.nperm)])
    # block null: permute in contiguous blocks (~1h = 3600 windows at stride180 -> ~20 windows/block; use 500-window blocks)
    bs = 500; nb = int(np.ceil(len(y) / bs))
    blk = []
    for _ in range(a.nperm):
        order = rng.permutation(nb)
        yp = np.concatenate([y[b*bs:(b+1)*bs] for b in order])[:len(y)]
        blk.append(pearsonr(q, yp)[0])
    blk = np.array(blk)
    zi = (realD - iid.mean()) / (iid.std() + 1e-12)
    zb = (realD - blk.mean()) / (blk.std() + 1e-12)
    pi = float(np.mean(iid >= realD)); pb = float(np.mean(blk >= realD))
    print(f"=== SHUFFLE-NULL {a.month} ({'EMA' if a.ema else 'BEST'}) N={len(y)} nperm={a.nperm} ===")
    print(f"  REAL   : DENSE-P={realD:+.4f}  per-day-CLEAN-P={realC:+.4f}")
    print(f"  IID-null  : mean={iid.mean():+.4f} sd={iid.std():.4f}  z={zi:+.2f}  p(>=real)={pi:.3f}")
    print(f"  BLOCK-null: mean={blk.mean():+.4f} sd={blk.std():.4f}  z={zb:+.2f}  p(>=real)={pb:.3f}")
    verdict = "REAL (>3 sigma over both nulls)" if (zi > 3 and zb > 3) else ("WEAK/SUSPECT" if (zi < 2 or zb < 2) else "marginal")
    print(f"  VERDICT: {verdict}")

if __name__ == "__main__":
    main()

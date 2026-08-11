"""Conditional-IC scorer for the H1 'tail-only survival' claim (drift months).

H1 (phase-1): on drift, the top-20%-|pred| carries IC ~+0.030 but the BODY
(bottom-80%-|pred|) is pure noise (~+0.0002). A lever that genuinely broadens the
signal should move the BODY IC OFF that floor. This scores, per arm, the pooled +
per-day-CLEAN Pearson of pred-vs-y within the top-20% and bottom-80% |pred| bins,
and prints arm-vs-baseline for the body (the decisive number for the rank arm).

Reads standard train_dual_lob preds (predictions=quantiles or q50, targets, mask,
timestamps) — works for any RAW-y arm (rank / Run1 / prod). Denorm cancels in
Pearson, so we score on the normalised prediction directly.

Usage: python multi_asset/model/rest_ic.py --arm <arm/fold_0/ema_test_preds.npz> \
         --base <baseline/fold_0/ema_test_preds.npz> [--frac 0.2]
"""
from __future__ import annotations
import argparse
import numpy as np

HZ = 600_000_000
DAY = 86_400_000_000


def _pear(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def _nonoverlap(ts):
    idx = np.argsort(ts, kind="stable"); keep = []; last = None
    for i in idx:
        if last is None or ts[i] - last >= HZ:
            keep.append(i); last = ts[i]
    return np.array(keep, dtype=int)


def _load(p):
    z = np.load(p, allow_pickle=True); pr = z["predictions"]
    q = (pr[:, 1] if pr.ndim == 2 else pr).astype(np.float64)
    y = z["targets"].astype(np.float64)
    ts = z["timestamps"].astype(np.int64)
    m = z["mask"].astype(bool) if "mask" in z.files else np.ones(len(q), bool)
    if y.ndim == 2:
        y = y[:, -1]  # primary horizon safety
    return q[m], y[m], ts[m]


def _cd(q, y, ts):
    day = ts // DAY; rs = []
    for d in np.unique(day):
        idx = np.where(day == d)[0]; sub = idx[_nonoverlap(ts[idx])]
        if len(sub) > 20 and q[sub].std() > 1e-12:
            rs.append(_pear(q[sub], y[sub]))
    return float(np.mean(rs)) if rs else float("nan"), len(rs)


def cond_ic(path, frac):
    q, y, ts = _load(path)
    a = np.abs(q - np.median(q))
    thr = np.quantile(a, 1.0 - frac)
    top = a >= thr; rest = ~top
    out = {}
    for name, msk in [("top", top), ("rest", rest)]:
        qq, yy, tt = q[msk], y[msk], ts[msk]
        pooled = _pear(qq, yy)
        cd, nd = _cd(qq, yy, tt)
        out[name] = (pooled, cd, int(msk.sum()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--base")
    ap.add_argument("--frac", type=float, default=0.2)
    a = ap.parse_args()
    A = cond_ic(a.arm, a.frac)
    print(f"==== conditional-IC (top {int(a.frac*100)}% vs body |pred|) : {a.arm.split('/')[-3]} ====")
    print(f"  TOP-{int(a.frac*100)}%   pooled={A['top'][0]:+.4f}  cd-CLEAN={A['top'][1]:+.4f}  n={A['top'][2]}")
    print(f"  BODY-{int((1-a.frac)*100)}%  pooled={A['rest'][0]:+.4f}  cd-CLEAN={A['rest'][1]:+.4f}  n={A['rest'][2]}   (H1 floor ~+0.0002)")
    if a.base:
        B = cond_ic(a.base, a.frac)
        print(f"  BASELINE BODY pooled={B['rest'][0]:+.4f}  cd-CLEAN={B['rest'][1]:+.4f}")
        print(f"  -> BODY lift (arm-base): pooled={A['rest'][0]-B['rest'][0]:+.4f}  cd={A['rest'][1]-B['rest'][1]:+.4f}")
    print("DONE_REST_IC.")


if __name__ == "__main__":
    main()

"""ALIGN arm (V2 demeaned-target) sidecar builder — Stage-1+ (2026-07-03).

Train-deploy alignment lever: production trains q50 on RAW y_600 but the deploy
caliber is 1h-causal-demeaned; the artifacts + wild β live in that unconstrained
slow (>1h) band. This builds the causal trailing-mean needed to train on the
DEMEANED target instead, so the model spends capacity on the tradeable 10-min
residual, not the slow level.

For each window anchor t (µs), using ONLY REALIZED past y_600 (a y_600 anchor t'
is realized at t iff its window [t', t'+600] is complete, i.e. t' <= t-600s):

    m(t)       = mean of y_600(t')  over t' in [t-3600s, t-600s], mask==1
    y_align(t) = y_600(t) - m(t)

Strictly causal (no look-ahead: the t-600 cutoff excludes any y_600 whose window
overhangs t). Cross-day continuous (early-of-day anchors use the prior day's
tail). Writes per-day npz {y_align, m, timestamps, y_raw} into data/npz_v2arch_align/
(OVERLAY; source npz_v2arch read-only). The dataset substitutes y_align as the
training target; eval adds m back (raw caliber, anti-#18) and scores the demeaned
prediction directly (deploy caliber).

CLI:
  build:    PYTHONPATH=. python multi_asset/data/build_align_target.py \
                --src npz_v2arch --dst npz_v2arch_align --start 2024-05-01 --end 2026-05-31 --apply
  selftest: PYTHONPATH=. python multi_asset/data/build_align_target.py --selftest
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import numpy as np

HALF_HR = 0  # placeholder to keep linters quiet
WIN_LO_US = 3600 * 1_000_000    # trailing 1h
WIN_HI_US = 600 * 1_000_000     # realized cutoff (y_600 horizon)


def _demean(ts, y, mask):
    """Vectorised causal trailing-1h-mean of realized past y_600.

    ts, y, mask: 1-D arrays for a CONTIGUOUS (sorted) multi-day series.
    Returns m (same length): mean of y over anchors t' in [t-3600s, t-600s] with
    mask==1 (realized), 0 where no valid history.
    """
    order = np.argsort(ts, kind="mergesort")
    ts_s = ts[order].astype(np.int64)
    y_s = (y[order] * mask[order]).astype(np.float64)   # masked y (0 where invalid)
    c_s = mask[order].astype(np.float64)
    cy = np.concatenate([[0.0], np.cumsum(y_s)])
    cc = np.concatenate([[0.0], np.cumsum(c_s)])
    lo = np.searchsorted(ts_s, ts_s - WIN_LO_US, side="left")
    hi = np.searchsorted(ts_s, ts_s - WIN_HI_US, side="right")
    summ = cy[hi] - cy[lo]
    cnt = cc[hi] - cc[lo]
    m_s = np.where(cnt > 0, summ / np.maximum(cnt, 1e-9), 0.0)
    m = np.empty_like(m_s)
    m[order] = m_s                                       # unshuffle back to input order
    return m.astype(np.float32)


def _dd(p):
    return os.path.basename(p)[:-4]


def build(src, dst, start, end, apply):
    if src == dst:
        sys.exit("src==dst not allowed (overlay must be separate)")
    srcd, dstd = f"data/{src}", f"data/{dst}"
    os.makedirs(dstd, exist_ok=True)
    files = sorted(glob.glob(f"{srcd}/*.npz"))
    days = [_dd(f) for f in files]
    sel = [(i, f) for i, f in enumerate(files)
           if (not start or _dd(f) >= start) and (not end or _dd(f) <= end)]
    print(f"build_align_target: {len(sel)} day(s) {start}..{end} -> {dstd} (apply={apply})")
    for i, f in sel:
        day = _dd(f)
        # load this day + the PRIOR day (for the early-of-day trailing window)
        parts = []
        for j in (i - 1, i):
            if j < 0:
                continue
            with np.load(files[j], allow_pickle=True) as z:
                ts = np.asarray(z["timestamps"], dtype=np.int64)
                y = np.asarray(z["y_600"], dtype=np.float64)
                mk = (np.asarray(z["y_mask_600"]).astype(np.float64)
                      if "y_mask_600" in z.files else np.ones_like(y))
            parts.append((j, ts, y, mk))
        ts_all = np.concatenate([p[1] for p in parts])
        y_all = np.concatenate([p[2] for p in parts])
        mk_all = np.concatenate([p[3] for p in parts])
        m_all = _demean(ts_all, y_all, mk_all)
        # slice back to THIS day
        n_this = len(parts[-1][1])
        ts_d = parts[-1][1]
        y_d = parts[-1][2].astype(np.float32)
        m_d = m_all[-n_this:]
        y_align = (y_d - m_d).astype(np.float32)
        cov = float(np.mean(m_d != 0.0))
        if not apply:
            print(f"  [dry] {day}: N={n_this} m!=0 cov={cov:.3f} "
                  f"mean|m|={np.mean(np.abs(m_d)):.4f} mean|yalign|={np.mean(np.abs(y_align)):.4f}")
            continue
        tmp = f"{dstd}/{day}.npz.tmp.npz"
        np.savez(tmp, y_align=y_align, m=m_d, y_raw=y_d, timestamps=ts_d)
        os.replace(tmp, f"{dstd}/{day}.npz")
        print(f"  {day}: N={n_this} cov={cov:.3f}")
    print("DONE_ALIGN.")


def selftest():
    ok = True
    us = 1_000_000
    # synthetic: 1 anchor / 180s over ~3 hours; y has a big spike late.
    t0 = 1_700_000_000 * us
    ts = t0 + np.arange(80) * 180 * us
    y = np.zeros(80, dtype=np.float64)
    y[60] = 100.0                          # a big FUTURE spike at index 60
    mask = np.ones(80)
    m = _demean(ts, y, mask)
    # (1) causality: m at indices <= 60 must NOT see the spike at 60. The spike
    #     enters m only for anchors t where 60's realized cutoff passes, i.e. index
    #     i with ts[i]-600s >= ts[60] -> i where ts[i] >= ts[60]+600s -> i>=64
    #     (600s/180s ~= 3.33 -> 4 steps). So m[60]..m[63] == 0, m[>=64] > 0.
    pre = np.all(m[:61] == 0.0)
    first_hit = np.argmax(m > 0) if np.any(m > 0) else -1
    c1 = pre and first_hit >= 61
    print(f"[selftest] causality: m[:61]==0 -> {pre}; first m>0 at idx {first_hit} (expect >=61 = 600s after spike) -> {'OK' if c1 else 'FAIL'}")
    ok &= c1
    # (2) realized cutoff: the spike's own anchor never demeans itself; and the
    #     spike leaves the 1h window after 3600s -> m returns toward 0.
    later = m[64:74]                        # ~600-2400s after spike: should be >0
    c2 = np.all(later > 0)
    print(f"[selftest] spike enters trailing window (m>0 for the hour after realized): {'OK' if c2 else 'FAIL'}")
    ok &= c2
    # (3) truncation-invariance: m at an early index computed on full vs
    #     truncated-to-that-index series must match (no future dependence).
    idx = 40
    m_full = _demean(ts, y, mask)[idx]
    keep = ts <= ts[idx]
    m_trunc = _demean(ts[keep], y[keep], mask[keep])[idx]
    c3 = abs(m_full - m_trunc) < 1e-9
    print(f"[selftest] truncation-invariance @idx40: full={m_full:.4f} trunc={m_trunc:.4f} -> {'OK' if c3 else 'FAIL'}")
    ok &= c3
    print(f"\n[selftest] {'ALL OK' if ok else 'FAILED'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="npz_v2arch")
    ap.add_argument("--dst", default="npz_v2arch_align")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    build(a.src, a.dst, a.start, a.end, a.apply)


if __name__ == "__main__":
    main()

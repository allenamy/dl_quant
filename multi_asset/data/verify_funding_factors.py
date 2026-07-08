#!/usr/bin/env python3
"""Phase-0b/A — funding-factor LEAK + COVERAGE verification (0B), run before trusting ICs.

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

Three gates, in order:
  1. CAUSALITY SENTINEL on the ffill≤t primitive (the sole causal core of every factor):
     synthetic + corrupt-future — future source values must NOT alter any panel value at t'≤t.
  2. COVERAGE — per-asset per-factor finite fraction on the 180s panel grid.
  3. SHUFFLE-FUTURE NULL — permute Y across timestamps (break factor→future-return alignment),
     recompute the standalone xsec rank-ICs N times; leak-free ⇒ the null brackets 0 and the
     real IC sits outside it (|z| large only for genuinely predictive factors).

Usage: PYTHONPATH=. python multi_asset/data/verify_funding_factors.py [nperm]
"""
from __future__ import annotations
import argparse, os.path as p
import numpy as np

from multi_asset.data.build_funding_factors import _ffill_to_panel
from multi_asset.baselines.xsec_ridge_h import build_panel_h, _standalone_ic
from multi_asset.baselines.xsec_ridge import SYMBOLS

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
CACHE = ROOT + "/funding_factor_cache"
HORIZON = 3600


def sentinel():
    # last src value with src_ts ≤ panel_ts; panel before first src -> NaN.
    src_ts = np.array([0, 10, 20, 30], np.int64)
    src_v = np.array([1., 2., 3., 4.])
    panel = np.array([-5, 5, 15, 25, 35], np.int64)
    out = _ffill_to_panel(src_ts, src_v, panel)
    assert np.isnan(out[0]), out
    assert out[1] == 1 and out[2] == 2 and out[3] == 3 and out[4] == 4, out
    # corrupt the FUTURE-most source value; every panel value at ts < that source ts must be unchanged.
    src_v2 = src_v.copy(); src_v2[3] = 9.9e9
    out2 = _ffill_to_panel(src_ts, src_v2, panel)
    assert np.array_equal(np.nan_to_num(out[:4]), np.nan_to_num(out2[:4])), (out, out2)  # ts ≤ 25 frozen
    assert out2[4] == 9.9e9, out2                                                        # ts ≥ 30 sees it
    # boundary: panel exactly on a source ts sees that ts (≤ is inclusive) — causal, no peek forward.
    assert _ffill_to_panel(src_ts, src_v, np.array([10], np.int64))[0] == 2
    print("[1/3 SENTINEL] ffill≤t causal: PASS — future source corruption never leaks to t'≤t", flush=True)


def coverage(cache=CACHE):
    print("[2/3 COVERAGE] per-asset per-factor finite fraction on the 180s panel grid:", flush=True)
    fn = None
    for s in SYMBOLS:
        z = np.load(p.join(cache, f"{s}.npz"), allow_pickle=True)
        X = z["X"]
        if fn is None:
            fn = [str(x) for x in z["factor_names"]]
            print("  factors: " + ", ".join(fn), flush=True)
        cov = np.isfinite(X).mean(0)
        print(f"  {s:8s} " + " ".join(f"{fn[i]}={cov[i]:.3f}" for i in range(len(fn))), flush=True)


def shuffle_null(nperm=15, cache=CACHE):
    ts, day, X, Y, CL, fnames = build_panel_h(HORIZON, cache)
    uniq = np.unique(day)
    real = _standalone_ic(X, Y, CL, day, uniq, fnames)
    rng = np.random.default_rng(0)
    null = {k: [] for k in real}
    for _ in range(nperm):
        Yp = Y[rng.permutation(len(Y))]            # scramble which cross-section sits at each ts
        n = _standalone_ic(X, Yp, CL, day, uniq, fnames)
        for k, v in n.items():
            if v is not None:
                null[k].append(v)
    print(f"[3/3 SHUFFLE-NULL] real xsec rank-IC vs {nperm}-perm time-shuffled null:", flush=True)
    print(f"  {'factor':18s} {'real':>8s} {'null_mu':>9s} {'null_sd':>8s} {'z':>7s}", flush=True)
    for k in real:
        arr = np.array(null[k]) if null[k] else np.array([np.nan])
        rv = real[k]
        z = (rv - arr.mean()) / (arr.std() + 1e-9) if rv is not None else float("nan")
        star = " *" if rv is not None and abs(z) >= 2 else ""
        print(f"  {k:18s} {('%.4f'%rv) if rv is not None else 'None':>8s} "
              f"{arr.mean():>+9.4f} {arr.std():>8.4f} {z:>+7.2f}{star}", flush=True)
    return real


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nperm", type=int, default=15)
    ap.add_argument("--cache", default=CACHE)
    ap.add_argument("--no-sentinel", action="store_true",
                    help="skip the ffill≤t sentinel (only meaningful for the funding cache)")
    a = ap.parse_args()
    if not a.no_sentinel:
        sentinel()   # tests the funding ffill≤t primitive; order-flow causality is bucket-assignment (tested separately)
    coverage(a.cache)
    shuffle_null(a.nperm, a.cache)


if __name__ == "__main__":
    main()

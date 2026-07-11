"""Re-derive the empirical-null z bar at N=110 for the Engine-A wide-universe leaderboard.

At N=14 the within-ts shuffle-null MEAN ≠ 0 (small-N bias) → we gated on empirical-null z≥2.5 not
IC-vs-0. At N≈110 the null-mean should shrink and the null-std tighten. Measure the null distribution
of the pooled mean-per-ts rank-IC statistic (incremental target = YR4, residual-on-[funding+zoo]) under
within-ts permutation, on the live-member cross-section (CL4 & MEMBER110). Report null-mean, null-std,
the IC needed for z=2.5, and the FWER-corrected bar for the arm count.

Usage: PYTHONPATH=. python multi_asset/eval/wide_null_calib.py
"""
from __future__ import annotations
import sys, numpy as np
from scipy.stats import rankdata, norm

W = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl.npz"
MIN = 8
N_SHUF = 200
N_ARMS = 36   # ~6 backbones × K=6 heads (family-wise correction)


def _ric(f, y):
    rf = rankdata(f); ry = rankdata(y); rf = rf - rf.mean(); ry = ry - ry.mean()
    d = np.sqrt((rf * rf).sum() * (ry * ry).sum()); return (rf * ry).sum() / d if d > 1e-12 else np.nan


def main():
    z = np.load(W, allow_pickle=True)
    YR, CL, MEM = z["YR4"], z["CL4"].astype(bool), z["MEMBER110"].astype(bool)
    T, N = YR.shape
    rng = np.random.default_rng(0)
    # usable rows: cross-section of live members with finite residual target
    rows = []
    for t in range(T):
        v = CL[t] & MEM[t] & np.isfinite(YR[t])
        if v.sum() >= MIN:
            rows.append((t, np.where(v)[0]))
    breadth = np.median([len(idx) for _, idx in rows])
    print(f"wide panel: T={T} N={N} | usable ts={len(rows)} | median breadth={breadth:.0f} assets/ts")

    # a fixed random factor; the NULL shuffles it within-ts, so its identity is irrelevant to the null
    F = rng.standard_normal((T, N))
    null_means = []
    for s in range(N_SHUF):
        ics = []
        for t, idx in rows:
            f = F[t, idx][rng.permutation(len(idx))]
            ic = _ric(f, YR[t, idx])
            if np.isfinite(ic):
                ics.append(ic)
        null_means.append(np.mean(ics))
    nm, ns = float(np.mean(null_means)), float(np.std(null_means))
    print(f"\nN≈110 empirical null of pooled mean-rank-IC ({N_SHUF} within-ts shuffles):")
    print(f"  null_mean = {nm:+.5f}   null_std = {ns:.5f}   (vs N=14: null_mean was materially ≠0)")
    ic_25 = nm + 2.5 * ns
    z_fwer = norm.ppf(1 - 0.05 / N_ARMS)
    ic_fwer = nm + z_fwer * ns
    print(f"  IC needed for z=2.5 (per-arm)      : {ic_25:+.5f}")
    print(f"  FWER z for {N_ARMS} arms (0.05/{N_ARMS})  : {z_fwer:.2f}  -> IC needed {ic_fwer:+.5f}")
    print(f"\n★ RE-DERIVED BAR: per-arm empirical-null z≥2.5 (necessary); leaderboard WINNER must also clear "
          f"FWER z≥{z_fwer:.1f} (arm-count corrected) AND walk-forward gate-d + per-fold sign.")
    print("DONE_WIDE_NULL_CALIB")


if __name__ == "__main__":
    main()

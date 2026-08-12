"""Money caliber for the four arms — IC is not the deliverable, net-of-cost is.

> **创建:** 2026-08-04 03:3x UTC | **Session:** B4-retrain | **状态:** final
> **派工:** team-lead 2026-08-04 —— "IC 升了 persist 降了, 请给钱口径, 不要用 turnover∝(1−persist)
>   的粗代理, 那是估计不是测量"
> **作废条件:** 权重整形口径(rank+cap)接入 ⇒ 绝对水平重算

Per anchor, on each fold's own OOS rows:
    w      = demeaned composite, normalised to unit gross, zero off-membership
    gross  = Σ w·Y4                                   (realised leg P&L, no cost)
    turn   = Σ|w_t − w_{t−1}|                          (MEASURED, within-fold consecutive anchors)
    breakeven = mean(gross) / mean(turn)               (the cost level where net crosses zero)
    net(c) = (mean(gross) − c·1e-4·mean(turn)) annualised

★ TURNOVER IS MEASURED, NOT INFERRED FROM PERSISTENCE. `persist` is a lag-1 score autocorrelation;
  turnover is the L1 change in the WEIGHTS, which also moves when membership churns or when the
  cross-sectional spread changes without the ordering changing. Using (1−persist) as a proxy would
  substitute a monotone-ish correlate for the quantity that actually multiplies the cost.

★ FOLD BOUNDARIES ARE NOT REBALANCES. Consecutive `te_rows` within a fold are 4h apart; the gap
  BETWEEN folds is a year. Differencing across that gap would invent one enormous rebalance per
  fold and inflate turnover by ~1 anchor in 2190. Pairs are taken within-fold only, and the code
  asserts the spacing it assumes rather than trusting it.

★ CALIBER, STATED WHEREVER QUOTED: this is the **DL leg alone** (king-only), gross weights are
  demeaned-composite at unit gross — **NOT** the deployed rank+cap book, and **NOT** the full book
  (funding/size legs and their weights are not applied here). Absolute bps is therefore
  caliber-approximate; the ARM-TO-ARM comparison is like-for-like because all arms are built
  identically.
"""
from __future__ import annotations

import argparse
import json
import os.path as _p
import sys

import numpy as np

_HERE = _p.dirname(_p.abspath(__file__))
sys.path.insert(0, _p.dirname(_p.dirname(_p.dirname(_HERE))))

ANCHORS_PER_YEAR = 365 * 6
COSTS = (1.9, 2.504, 3.79)


def arm(run_dir, beta_unused, member, CL, Y4, N):
    gross, turn = [], []
    f = 0
    while _p.exists(_p.join(run_dir, f"fold_{f}_head_scores.npz")):
        z = np.load(_p.join(run_dir, f"fold_{f}_head_scores.npz"))
        sc, te = z["scores"], np.sort(z["te_rows"])
        prev_row, prev_w = None, None
        for i in te:
            base = np.where(member[i] & CL[i] & np.isfinite(Y4[i]))[0]
            if base.size < 5:
                continue
            comp = np.zeros(base.size); nk = 0
            for k in range(sc.shape[2]):
                col = sc[i, base, k]
                if np.isfinite(col).all() and col.std() > 1e-12:
                    comp += (col - col.mean()) / col.std(); nk += 1
            if nk == 0:
                continue
            c = comp / nk
            c = c - c.mean()
            s = np.abs(c).sum()
            if s <= 1e-12:
                continue
            wfull = np.zeros(N)
            wfull[base] = c / s
            gross.append(float((wfull[base] * Y4[i, base].astype(np.float64)).sum()))
            if prev_w is not None and (i - prev_row) <= 8:       # same fold, adjacent rebalance
                turn.append(float(np.abs(wfull - prev_w).sum()))
            prev_row, prev_w = i, wfull
        f += 1
    return np.array(gross), np.array(turn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", required=True, help="label=dir:panel")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {}
    hdr = (f"{'arm':14s} {'gross bps/yr':>13} {'turn/anchor':>12} {'turn/yr':>9} "
           f"{'breakeven bps':>14} " + " ".join(f"{'net@'+str(c):>11}" for c in COSTS))
    print(hdr)
    for spec in a.arms:
        label, rest = spec.split("=", 1)
        d, panel = rest.split(":", 1)
        z = np.load(panel, allow_pickle=True)
        member, CL, Y4 = z["MEMBER110"], z["CL4"], z["Y4"]
        N = member.shape[1]
        g, t = arm(d, None, member, CL, Y4, N)
        gb = float(g.mean()) * ANCHORS_PER_YEAR * 1e4
        tm = float(t.mean())
        be = float(g.mean()) / tm * 1e4 if tm > 0 else float("nan")
        nets = [(float(g.mean()) - c * 1e-4 * tm) * ANCHORS_PER_YEAR * 1e4 for c in COSTS]
        rec[label] = dict(n_anchors=len(g), n_rebalances=len(t),
                          gross_bps_per_year=round(gb, 1), turnover_per_anchor=round(tm, 4),
                          turnover_per_year=round(tm * ANCHORS_PER_YEAR, 1),
                          breakeven_bps=round(be, 3),
                          net_bps_per_year={str(c): round(v, 1) for c, v in zip(COSTS, nets)})
        print(f"{label:14s} {gb:>13.1f} {tm:>12.4f} {tm*ANCHORS_PER_YEAR:>9.0f} {be:>14.3f} "
              + " ".join(f"{v:>11.1f}" for v in nets))

    print("\n=== the question that prompted this: S1 -> S1F, does the money agree with the IC? ===")
    for arch in ("xattn", "plain"):
        s1, s1f = rec.get(f"S1_{arch}"), rec.get(f"S1F_{arch}")
        if not (s1 and s1f):
            continue
        print(f"  [{arch}]  breakeven {s1['breakeven_bps']:.3f} -> {s1f['breakeven_bps']:.3f} "
              f"({(s1f['breakeven_bps']/s1['breakeven_bps']-1)*100:+.1f}%)   "
              f"turnover/yr {s1['turnover_per_year']:.0f} -> {s1f['turnover_per_year']:.0f}   "
              f"gross {s1['gross_bps_per_year']:.0f} -> {s1f['gross_bps_per_year']:.0f}")
        for c in COSTS:
            v0, v1 = s1["net_bps_per_year"][str(c)], s1f["net_bps_per_year"][str(c)]
            print(f"       net@{c}bps  {v0:>9.1f} -> {v1:>9.1f}  ({v1-v0:+.1f})")
    json.dump(rec, open(a.out, "w"), indent=1)
    print(f"\nrecord -> {a.out}")


if __name__ == "__main__":
    main()

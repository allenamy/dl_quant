"""Price the tilt-timing channel — what plain's BEYOND quirk actually COSTS, in bps of gross/year.

> **创建:** 2026-08-04 02:0x UTC | **Session:** B4-retrain | **状态:** final
> **裁定:** team-lead 2026-08-04 —— 阈值【先于数字】定死: plain 相对 xattn 的年化拖累
>          **> 2bps of gross ⇒ 跟查失败 ⇒ 启用预写死回退**; ≤2bps ⇒ plain 照常部署。
> **作废条件:** 部署 sizing 口径改变 ⇒ 绝对水平须重算(相对比较不受影响)

The mechanism behind plain's −0.038 may never be found. Its PRICE can be measured today.

    per anchor:  w_i  = gross-normalised cross-sectional weights (demeaned composite, Σ|w| = 1)
                 netβ = Σ w_i · beta_24h_i          ← the book's net market exposure that anchor
                 pnl  = netβ · (market return over the HOLDING window)
    annualise over 2190 anchors/yr, report in bps of gross.

★★ WHICH WINDOW EARNS THE MONEY, AND WHY THE ANOMALY'S OWN WINDOW DOES NOT.
   The book holds ~4h (the Y4 horizon), so P&L accrues over **t+1…t+4**. The anomaly was measured on
   **t+5…t+11** — a window the book has already exited. A correlation there is structurally worth
   ZERO P&L on its own. What makes it matter is that the SAME tilt behaviour also shows up inside
   the traded window (clean plain measured −0.036 there too). So this prices the TRADED window and
   reports the beyond window alongside as diagnosis, never as cost.
   ⇒ Pricing the beyond window as if it were P&L would be inventing a loss the book cannot take.

★ CALIBER, STATED. Weights here are demeaned-composite normalised to unit gross — NOT the deployed
  rank+cap book (`engine_v1` CANONICAL). So the ABSOLUTE bps is caliber-approximate. The ruling's
  threshold is on the plain-vs-xattn DIFFERENCE, and both arms are built identically here, so the
  comparison the threshold judges is unaffected by that approximation. Absolute figures carry the
  caveat wherever they are quoted.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os.path as _p
import sys

import numpy as np

_HERE = _p.dirname(_p.abspath(__file__))
sys.path.insert(0, _p.dirname(_p.dirname(_p.dirname(_HERE))))

_spec = importlib.util.spec_from_file_location(
    "lx", _p.join(_HERE, "measure_lookahead_exploitation_s1.py"))
LX = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(LX)

ANCHORS_PER_YEAR = 365 * 6          # 4h anchors
HOLD_LO, HOLD_HI = 1, 4             # the traded window
BEYOND_LO, BEYOND_HI = 5, 11        # the anomaly window — diagnosis only, never priced


def window(m, lo, hi):
    T = len(m)
    pref = np.concatenate([[0.0], np.cumsum(m)])
    return np.array([pref[min(T, t + hi + 1)] - pref[min(T, t + lo)] for t in range(T)])


def netbeta_series(run_dir, beta, member, CL, Y):
    rows, nb = [], []
    f = 0
    while _p.exists(_p.join(run_dir, f"fold_{f}_head_scores.npz")):
        z = np.load(_p.join(run_dir, f"fold_{f}_head_scores.npz"))
        sc, te = z["scores"], z["te_rows"]
        for i in te:
            base = np.where(member[i] & CL[i] & np.isfinite(Y[i]) & np.isfinite(beta[i]))[0]
            if base.size < 5:
                continue
            comp = np.zeros(base.size); nk = 0
            for k in range(sc.shape[2]):
                col = sc[i, base, k]
                if np.isfinite(col).all() and col.std() > 1e-12:
                    comp += (col - col.mean()) / col.std(); nk += 1
            if nk == 0:
                continue
            w = comp / nk
            w = w - w.mean()                      # market-neutral by construction
            s = np.abs(w).sum()
            if s <= 1e-12:
                continue
            w = w / s                             # unit gross
            nb.append(float((w * beta[i, base].astype(np.float64)).sum()))
            rows.append(int(i))
        f += 1
    return np.array(rows), np.array(nb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--panel", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    z = np.load(a.panel, allow_pickle=True)
    chn = [str(x) for x in z["ch_names"]]
    beta = z["CH"][:, :, chn.index("beta_24h")]
    member, CL, Y = z["MEMBER110"], z["CL4"], z["Y4"]
    m = LX.market_series(a.source)
    hold, beyond = window(m, HOLD_LO, HOLD_HI), window(m, BEYOND_LO, BEYOND_HI)

    rec = {}
    print(f"{'run':16s} {'n':>6} {'mean netβ':>11} {'sd netβ':>9} "
          f"{'STATIC':>12} {'TIMING':>12} {'TOTAL':>12} {'(beyond,diag)':>14}")
    for spec in a.runs:
        name, d = spec.split("=", 1)
        rows, nb = netbeta_series(d, beta, member, CL, Y)
        pnl_hold = nb * hold[rows]
        pnl_beyond = nb * beyond[rows]
        h = hold[rows]
        per_anchor = float(pnl_hold.mean())
        bps_yr = per_anchor * ANCHORS_PER_YEAR * 1e4
        bps_yr_beyond = float(pnl_beyond.mean()) * ANCHORS_PER_YEAR * 1e4
        # ★★ THE SPLIT DECIDES THE VERDICT, AND MY FIRST VERSION GOT IT WRONG.
        #   total = STATIC (persistent beta exposure × the sample's realised drift)
        #         + TIMING (covariance of net-beta with the future market)
        #   The ruling names the TILT-TIMING CHANNEL. Only the timing term is that channel; the
        #   static term is a directional bet whose sign is set by which way this sample happened to
        #   drift. v1 of this script judged the TOTAL and printed "within tolerance -> deploy";
        #   on the named quantity the answer reverses. Pricing the wrong decomposition term is the
        #   same error family as pricing the wrong window — an answer to a question nobody asked.
        static = float(nb.mean() * h.mean()) * ANCHORS_PER_YEAR * 1e4
        timing = float(np.mean((nb - nb.mean()) * (h - h.mean()))) * ANCHORS_PER_YEAR * 1e4
        se = pnl_hold.std(ddof=1) / np.sqrt(len(pnl_hold))
        rec[name] = dict(n=len(rows), mean_netbeta=round(float(nb.mean()), 6),
                         sd_netbeta=round(float(nb.std()), 6),
                         traded_total_bps_per_year=round(bps_yr, 4),
                         traded_STATIC_bps_per_year=round(static, 4),
                         traded_TIMING_bps_per_year=round(timing, 4),
                         traded_t=round(float(per_anchor / se) if se > 0 else float("nan"), 2),
                         beyond_bps_per_year_DIAGNOSTIC_ONLY=round(bps_yr_beyond, 4))
        print(f"{name:16s} {len(rows):>6} {nb.mean():>+11.6f} {nb.std():>9.6f} "
              f"{static:>+12.1f} {timing:>+12.1f} {bps_yr:>+12.1f} {bps_yr_beyond:>+14.1f}")

    print("\n=== the ruling's quantity: the TILT-TIMING CHANNEL, plain MINUS xattn ===")
    if "CLEAN_plain" in rec and "CLEAN_xattn" in rec:
        drag = (rec["CLEAN_plain"]["traded_TIMING_bps_per_year"]
                - rec["CLEAN_xattn"]["traded_TIMING_bps_per_year"])
        tot = (rec["CLEAN_plain"]["traded_total_bps_per_year"]
               - rec["CLEAN_xattn"]["traded_total_bps_per_year"])
        print(f"  TOTAL difference (NOT the criterion) = {tot:+.3f} bps/yr — plain looks better here,"
              f" but that is the STATIC leg: a short-beta book in a sample that drifted down.")
        verdict = ("FOLLOW-UP FAILED -> activate the pre-committed fallback (xattn-clean)"
                   if drag < -2.0 else
                   "within tolerance -> plain deploys; BEYOND-corr becomes a standing shadow monitor")
        print(f"  TIMING: plain {rec['CLEAN_plain']['traded_TIMING_bps_per_year']:+.1f} - "
              f"xattn {rec['CLEAN_xattn']['traded_TIMING_bps_per_year']:+.1f} = "
              f"**{drag:+.1f} bps/yr of gross**")
        print(f"  threshold: drag worse than -2.0 bps/yr => fallback")
        print(f"  ⇒ {verdict}")
        rec["_verdict"] = dict(drag_bps_per_year=round(drag, 4), threshold_bps=-2.0,
                               fallback_triggered=bool(drag < -2.0), verdict=verdict)
    json.dump(rec, open(a.out, "w"), indent=1)
    print(f"\nrecord -> {a.out}")


if __name__ == "__main__":
    main()

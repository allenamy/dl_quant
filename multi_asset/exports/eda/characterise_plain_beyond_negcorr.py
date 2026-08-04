"""`plain_beyond_negcorr` — characterise the −0.038 BEYOND-window correlation. DEPLOYMENT PREREQ.

> **创建:** 2026-08-04 01:5x UTC | **Session:** B4-retrain | **状态:** final
> **裁定:** team-lead 2026-08-04(S1-plain 走部署链 ⇒ 该跟查项提前为部署前置)
> **作废条件:** BEYOND 判据定义改变 ⇒ 重跑

THE OPEN ITEM. On the clean panel, `plain`'s beta-tilt correlates **−0.038** (95% CI excluding 0)
with `Σ market[t+5 … t+11]` — the window beyond its own prediction horizon, which has no legitimate
reason to correlate at all. `xattn` is −0.0002 (CI ∋ 0) there. NO-GO#2 was ruled not triggered
because a profitable leak path must be POSITIVE, but "not a leak" is not the same as "explained",
and an unexplained significant association in front of a deployment is worth an hour.

TWO ROUTES, and they answer different questions:

  (1) MULTI-WINDOW PARTIAL. My earlier partial controlled ONE trailing window (24h) and the effect
      survived. But the model reads many horizons — mom_{4,8,24,72,168}h, rvol, ret_{1,4,12,24}h.
      So control a BASIS of trailing market sums {4,12,24,48,72,168}h at once and ask what is left.

  (2) MEAN-REVERSION MECHANISM. If market returns mean-revert, a model that legitimately responds
      to the RECENT PAST inherits a negative correlation with the NEAR FUTURE for free — no future
      information required. This is measurable without any model: compute corr(trailing-window,
      BEYOND-window) directly on the market series. Then the part of the tilt that is a linear
      response to trailing windows has a PREDICTED beyond-correlation, and we compare that
      prediction to the observed −0.038.

      decomposition:  tilt = tilt_hat (explained by trailing windows) + tilt_resid
                      corr(tilt_hat,  BEYOND)  <- what causal market response alone would produce
                      corr(tilt_resid, BEYOND) <- what is NOT explained by any causal response

★ The verdict that matters is the RESIDUAL one. If `corr(tilt_resid, BEYOND)` has a CI containing 0,
  the −0.038 is fully accounted for by legitimate response to a mean-reverting market. If it does
  not, something is unexplained and that is a deployment finding, not a footnote.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os.path as _p
import sys

import numpy as np

_HERE = _p.dirname(_p.abspath(__file__))
_ROOT = _p.dirname(_p.dirname(_p.dirname(_HERE)))
sys.path.insert(0, _ROOT)

_spec = importlib.util.spec_from_file_location(
    "lx", _p.join(_HERE, "measure_lookahead_exploitation_s1.py"))
LX = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(LX)

TRAIL_WINDOWS = (4, 12, 24, 48, 72, 168)
BEYOND_LO, BEYOND_HI = 5, 11


def wins(m, T):
    pref = np.concatenate([[0.0], np.cumsum(m)])
    trail = {w: np.array([pref[t + 1] - pref[max(0, t + 1 - w)] for t in range(T)])
             for w in TRAIL_WINDOWS}
    beyond = np.array([pref[min(T, t + BEYOND_HI + 1)] - pref[min(T, t + BEYOND_LO)]
                       for t in range(T)])
    return trail, beyond


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
    trail, beyond = wins(m, len(m))

    print("=== the mechanism, measured on the MARKET SERIES ALONE (no model involved) ===")
    mech = {}
    for w in TRAIL_WINDOWS:
        r = float(np.corrcoef(trail[w], beyond)[0, 1])
        mech[f"trail{w}h_vs_beyond"] = round(r, 5)
        print(f"   corr( Σmarket[t-{w-1}..t] , Σmarket[t+5..t+11] ) = {r:+.5f}")
    print("   ⇒ negative here means: any model responding to the recent past inherits a negative\n"
          "     beyond-correlation for free, with no future information.\n")

    rec = {"mechanism": mech, "runs": {}}
    for spec in a.runs:
        name, d = spec.split("=", 1)
        rows, tilt = LX.tilt_series(d, beta, member, CL, Y)
        X = np.column_stack([trail[w][rows] for w in TRAIL_WINDOWS])
        X = np.column_stack([np.ones(len(rows)), X])
        coef, *_ = np.linalg.lstsq(X, tilt, rcond=None)
        hat = X @ coef
        resid = tilt - hat
        b = beyond[rows]
        r_raw = float(np.corrcoef(tilt, b)[0, 1])
        r_hat = float(np.corrcoef(hat, b)[0, 1])
        r_res = float(np.corrcoef(resid, b)[0, 1])
        lo, hi = LX.block_boot_ci(resid, b)
        r2 = 1 - resid.var() / tilt.var()
        print(f"[{name}]  n={len(rows)}  R²(tilt ~ trailing windows) = {r2:.4f}")
        print(f"   corr(tilt,        BEYOND) = {r_raw:+.5f}   (observed)")
        print(f"   corr(tilt_hat,    BEYOND) = {r_hat:+.5f}   (predicted by causal market response)")
        print(f"   corr(tilt_resid,  BEYOND) = {r_res:+.5f}   95%CI [{lo:+.5f}, {hi:+.5f}]"
              f"   {'CI∋0 ⇒ FULLY EXPLAINED' if lo <= 0 <= hi else '★ CI excludes 0 ⇒ UNEXPLAINED'}")
        rec["runs"][name] = dict(n=len(rows), r2_tilt_on_trailing=round(float(r2), 5),
                                 corr_observed=round(r_raw, 5), corr_explained=round(r_hat, 5),
                                 corr_residual=round(r_res, 5), residual_ci95=[round(lo, 5),
                                                                               round(hi, 5)],
                                 residual_ci_contains_zero=bool(lo <= 0 <= hi))
    json.dump(rec, open(a.out, "w"), indent=1)
    print(f"\nrecord -> {a.out}")


if __name__ == "__main__":
    main()

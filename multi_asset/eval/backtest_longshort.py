"""Economic long-short backtest for the cross-sectional residual model.

Turns the rank-IC signal into the $ deliverable: a market-neutral long-short
portfolio, net of fees, with the eval-framework metrics (annualized Sharpe,
quantile-spread monotonicity, turnover, market-neutrality, breadth).

Loads per-fold saved test predictions + panel_ref (raw y, clean mask) from
EXPORT/<tag>/. At each CLEAN (>=600s non-overlap) test timestamp with >=K valid
assets: cross-sectionally rank the residual predictions, form demeaned dollar-
neutral rank weights (long the predicted out-performers, short the under-
performers), and realise w . y over the next 600s. Net return subtracts
per-side cost * turnover. Annualised at the 600s rebalance cadence.

Usage: python3 multi_asset/eval/backtest_longshort.py --tag R1_residual_saved [--cost_bps 2.0]
"""
from __future__ import annotations

import argparse
import glob
import json
import os.path as p

import numpy as np
from scipy.stats import spearmanr

EXPORT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
          "multi_asset/exports/train")
SEC_PER_YEAR = 365 * 24 * 3600
HORIZON = 600
MIN_ASSETS = 5


def rank_weights(scores):
    """Demeaned cross-sectional ranks -> dollar-neutral weights (sum|w|=2, sum w=0)."""
    n = len(scores)
    r = scores.argsort().argsort().astype(np.float64)        # 0..n-1
    r = r - r.mean()                                         # demean (long top/short bottom)
    s = np.abs(r).sum()
    return r / s * 2.0 if s > 0 else r                       # |long|=|short|=1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--cost_bps", type=float, default=2.0,
                    help="per-side trading cost in bps (round-trip = 2x via turnover)")
    args = ap.parse_args()
    d = p.join(EXPORT, args.tag)
    ref = np.load(p.join(d, "panel_ref.npz"), allow_pickle=True)
    ts, day, Y, CL = ref["ts"], ref["day"], ref["Y"], ref["CL"]
    syms = [str(s) for s in ref["symbols"]]
    T, S = Y.shape

    # merge per-fold test preds into one (T,S) array (folds cover disjoint test days)
    pred = np.full((T, S), np.nan, np.float32)
    for f in sorted(glob.glob(p.join(d, "fold_*_preds.npz"))):
        z = np.load(f)
        rows = z["te_rows"]
        pred[rows] = z["pred"][rows]
    cov = np.isfinite(pred).any(1).sum()
    print(f"[bt] {args.tag}: {cov} test timestamps with preds, {S} assets, cost={args.cost_bps}bps/side")

    # precompute per-period target weights + gross + IC (signal-only, cost-free)
    per_yr = SEC_PER_YEAR / HORIZON
    ann_factor = np.sqrt(per_yr)
    targ_w, gross_only, ics, breadth = [], [], [], []
    n_q = 5; qbucket_y = [[] for _ in range(n_q)]
    for t in range(T):
        v = CL[t] & np.isfinite(pred[t]) & np.isfinite(Y[t])
        if v.sum() < MIN_ASSETS:
            continue
        idx = np.where(v)[0]
        sc = pred[t, idx]; yv = Y[t, idx]
        wfull = np.zeros(S); wfull[idx] = rank_weights(sc)
        targ_w.append(wfull); gross_only.append(float((wfull * np.where(v, Y[t], 0)).sum()))
        ic = spearmanr(sc, yv).correlation
        if np.isfinite(ic):
            ics.append(ic)
        breadth.append(len(idx))
        order = sc.argsort()
        for qi in range(n_q):
            lo = qi*len(order)//n_q; hi = (qi+1)*len(order)//n_q
            if hi > lo: qbucket_y[qi].append(yv[order[lo:hi]].mean())
    targ_w = np.array(targ_w); gross_only = np.array(gross_only); ics = np.array(ics)
    Yrows = np.array([Y[t] for t in range(T) if (CL[t] & np.isfinite(pred[t]) & np.isfinite(Y[t])).sum() >= MIN_ASSETS])

    def run(alpha):
        """EMA-held weights: w_t = a*target + (1-a)*w_{t-1}; only trade the delta.
        alpha=1.0 = naive full-turnover. Lower = slower holding, less turnover/cost."""
        held = np.zeros(S); rets = []
        for k in range(len(targ_w)):
            new = alpha * targ_w[k] + (1 - alpha) * held
            turn = float(np.abs(new - held).sum())
            yk = np.nan_to_num(Yrows[k], nan=0.0)
            gross = float((new * yk).sum())
            rets.append(gross - turn * (args.cost_bps * 1e-4))
            held = new
        rets = np.array(rets)
        return (float(rets.mean()/rets.std()*ann_factor) if rets.std() > 0 else float("nan"),
                float(rets.mean()*per_yr*1e4))

    sweep = {}
    for a in (1.0, 0.5, 0.3, 0.2, 0.1, 0.05, 0.02):
        sh, ar = run(a); sweep[a] = dict(net_sharpe=round(sh, 3), net_ann_bps=round(ar, 1))
    best_a = max(sweep, key=lambda a: sweep[a]["net_sharpe"])
    qmeans = [float(np.mean(b)) if b else float("nan") for b in qbucket_y]
    gross_sh = float(gross_only.mean()/gross_only.std()*ann_factor) if gross_only.std() > 0 else None
    out = dict(
        tag=args.tag, n_periods=int(len(targ_w)), cost_bps=args.cost_bps,
        mean_rank_ic=round(float(ics.mean()), 4),
        ic_ir=round(float(ics.mean()/ics.std()*np.sqrt(len(ics))), 2) if ics.std() > 0 else None,
        gross_sharpe_ann_zerocost=round(gross_sh, 3) if gross_sh else None,
        gross_edge_bps_per_period=round(float(gross_only.mean()*1e4), 4),
        holding_sweep=sweep, best_alpha=best_a, best_net_sharpe=sweep[best_a]["net_sharpe"],
        quantile_mean_y_bps=[round(q*1e4, 3) for q in qmeans],
        quantile_monotonicity=round(float(spearmanr(np.arange(n_q), qmeans).correlation), 3),
        avg_breadth=round(float(np.mean(breadth)), 1),
    )
    print(json.dumps(out, indent=2))
    json.dump(out, open(p.join(d, "backtest_longshort.json"), "w"), indent=2)
    print(f"saved -> {p.join(d, 'backtest_longshort.json')}")


if __name__ == "__main__":
    main()

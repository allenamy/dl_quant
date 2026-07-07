"""1h cross-sectional LONG-SHORT GO/NO-GO gate — multi-asset v2 north star: net-cost tradeability.

Reuses backtest_longshort.py's engine (rank_weights, EMA-held turnover, panel/pred loader) but reports
the GATE-defining numbers the single-cost tool doesn't: a COST × TURNOVER sweep, the BREAK-EVEN per-side
cost (gross-edge / turnover), and the cost tier at which the book is net-positive — for a configurable
HORIZON (default 3600s = 1h; only affects annualisation, the non-overlap cadence is inherited from the
panel's CL mask, which MUST be built at the same horizon).

THE QUESTION: is a 1h cross-sectional L/S crypto-perp book net-cost tradeable? (y180 concluded 180s was
NOT — per-trade edge < 3bps floor.) Realistic perp cost: maker ~0–2 bps/side, taker ~2.5–5 bps/side.
GO if break-even per-side clears an achievable tier; else escalate horizon (2h/4h).

Usage: python multi_asset/eval/ls_gate.py --tag <y3600_baseline_tag> [--horizon 3600]
"""
from __future__ import annotations
import argparse, glob, json, os, sys, os.path as op
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))   # repo root on path
from multi_asset.eval.backtest_longshort import rank_weights, EXPORT, MIN_ASSETS

SEC_PER_YEAR = 365 * 24 * 3600
COST_GRID = (0.0, 1.0, 2.0, 2.5, 4.0, 5.0, 8.0, 10.0)      # per-side bps
ALPHA_GRID = (1.0, 0.5, 0.3, 0.2, 0.1, 0.05, 0.02)         # EMA turnover (1=full turnover, lower=slower)


def load(tag, export):
    d = op.join(export, tag)
    ref = np.load(op.join(d, "panel_ref.npz"), allow_pickle=True)
    Y, CL = ref["Y"], ref["CL"]
    T, S = Y.shape
    pred = np.full((T, S), np.nan, np.float32)
    for f in sorted(glob.glob(op.join(d, "fold_*_preds.npz"))):
        z = np.load(f); pred[z["te_rows"]] = z["pred"][z["te_rows"]]
    return d, ref["ts"], Y, CL, pred, [str(s) for s in ref["symbols"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--horizon", type=int, default=3600, help="rebalance horizon (s); must match the panel CL non-overlap")
    ap.add_argument("--export", default=EXPORT)
    a = ap.parse_args()
    d, ts, Y, CL, pred, syms = load(a.tag, a.export)
    T, S = Y.shape
    per_yr = SEC_PER_YEAR / a.horizon; ann = np.sqrt(per_yr)
    cov = np.isfinite(pred).any(1).sum()
    print(f"[gate] {a.tag}: {cov} pred-ts, {S} assets, horizon={a.horizon}s, per_yr={per_yr:.0f}")

    # per-period target weights, gross(signal), rank-IC, quantile buckets, breadth
    targ_w, Yrows, ics, breadth = [], [], [], []
    n_q = 5; qy = [[] for _ in range(n_q)]
    for t in range(T):
        v = CL[t] & np.isfinite(pred[t]) & np.isfinite(Y[t])
        if v.sum() < MIN_ASSETS:
            continue
        idx = np.where(v)[0]; sc = pred[t, idx]; yv = Y[t, idx]
        w = np.zeros(S); w[idx] = rank_weights(sc)
        targ_w.append(w); Yrows.append(np.where(v, Y[t], 0.0))
        ic = spearmanr(sc, yv).correlation
        if np.isfinite(ic): ics.append(ic)
        breadth.append(len(idx))
        order = sc.argsort()
        for qi in range(n_q):
            lo = qi*len(order)//n_q; hi = (qi+1)*len(order)//n_q
            if hi > lo: qy[qi].append(yv[order[lo:hi]].mean())
    targ_w = np.array(targ_w); Yrows = np.array(Yrows); ics = np.array(ics)
    n = len(targ_w)
    if n == 0:
        print("NO usable periods — check panel/preds coverage."); return

    # per-alpha gross & turnover SERIES (cost-independent), then sweep cost analytically
    def series(alpha):
        held = np.zeros(S); g = np.empty(n); tn = np.empty(n)
        for k in range(n):
            new = alpha*targ_w[k] + (1-alpha)*held
            tn[k] = np.abs(new - held).sum()
            g[k] = float((new * Yrows[k]).sum())
            held = new
        return g, tn

    print(f"\n=== COST × TURNOVER SWEEP (net Sharpe | net ann bps), n={n} periods ===")
    print(f"{'alpha':>6s} {'turn/prd':>8s} {'gross_bps':>9s} {'BE/side':>8s} | " +
          "  ".join(f"c={c}" for c in COST_GRID))
    best = dict(be=-1)
    for al in ALPHA_GRID:
        g, tn = series(al)
        gm = g.mean(); tm = tn.mean()
        be = gm / tm * 1e4 if tm > 1e-12 else np.inf         # break-even per-side cost (bps)
        cells = []
        for c in COST_GRID:
            net = g - tn * (c*1e-4)
            sh = net.mean()/net.std()*ann if net.std() > 0 else np.nan
            cells.append(f"{sh:+.2f}")
        print(f"{al:6.2f} {tm:8.3f} {gm*1e4:9.4f} {be:8.3f} | " + "  ".join(f"{x:>6s}" for x in cells))
        if be > best["be"]:
            best = dict(be=float(be), alpha=al, turn=float(tm), gross_bps=float(gm*1e4))
    # net ann bps at the most cost-tolerant alpha
    g, tn = series(best["alpha"])
    print(f"\n★ BREAK-EVEN per-side = {best['be']:.3f} bps  (at alpha={best['alpha']}, turnover={best['turn']:.3f}/prd, gross={best['gross_bps']:.4f} bps/prd)")
    print(f"  net ann bps @ cost:  " + "  ".join(f"c{c}={float((g-tn*(c*1e-4)).mean()*per_yr*1e4):.0f}" for c in COST_GRID))
    gross_sh = g.mean()/g.std()*ann if g.std() > 0 else np.nan
    qmeans = [float(np.mean(b)) if b else np.nan for b in qy]
    mono = float(spearmanr(np.arange(n_q), qmeans).correlation)
    print(f"\n  mean rank-IC={ics.mean():+.4f}  IC-IR={ics.mean()/ics.std()*np.sqrt(len(ics)):.2f}  "
          f"gross Sharpe(0-cost)={gross_sh:.2f}  avg breadth={np.mean(breadth):.1f}")
    print(f"  quantile mean-y (bps): {[round(q*1e4,3) for q in qmeans]}  monotonicity={mono:+.3f}")

    # GO/NO-GO framing
    tiers = {"maker~1": 1.0, "maker~2": 2.0, "taker~2.5": 2.5, "taker~5": 5.0}
    verdict = {k: ("GO" if best["be"] > c else "underwater") for k, c in tiers.items()}
    print(f"\n★ GO/NO-GO (break-even {best['be']:.2f} bps/side vs tiers): " +
          "  ".join(f"{k}({c})→{verdict[k]}" for k, c in tiers.items()))
    out = dict(tag=a.tag, horizon=a.horizon, n_periods=n, mean_rank_ic=round(float(ics.mean()), 4),
               ic_ir=round(float(ics.mean()/ics.std()*np.sqrt(len(ics))), 2),
               breakeven_per_side_bps=round(best["be"], 3), best_alpha=best["alpha"],
               gross_sharpe_zerocost=round(float(gross_sh), 2), quantile_monotonicity=round(mono, 3),
               avg_breadth=round(float(np.mean(breadth)), 1), tier_verdict=verdict)
    json.dump(out, open(op.join(d, "ls_gate.json"), "w"), indent=2)
    print(f"\nsaved -> {op.join(d, 'ls_gate.json')}\nDONE_LS_GATE")


if __name__ == "__main__":
    main()

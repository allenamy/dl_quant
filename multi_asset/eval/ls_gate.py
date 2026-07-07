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
    ap.add_argument("--lags", default="0,60,180,300,600", help="execution-lag grid (s) for latency-aware break-even")
    ap.add_argument("--export", default=EXPORT)
    a = ap.parse_args()
    d, ts, Y, CL, pred, syms = load(a.tag, a.export)
    ts = ts.astype(np.int64)
    T, S = Y.shape
    per_yr = SEC_PER_YEAR / a.horizon; ann = np.sqrt(per_yr)
    # infer the raw ts grid (unit-agnostic: detect ns/µs/ms/s) -> ns-per-second for lag snapping
    ts_unit = 1e9 if ts[0] > 1e17 else (1e6 if ts[0] > 1e14 else (1e3 if ts[0] > 1e11 else 1.0))
    grid = float(np.median(np.diff(np.unique(ts)))) / ts_unit                 # raw grid (s)
    cov = np.isfinite(pred).any(1).sum()
    print(f"[gate] {a.tag}: {cov} pred-ts, {S} assets, horizon={a.horizon}s, per_yr={per_yr:.0f}, raw grid≈{grid:.0f}s")

    # per-period target weights, gross(signal), rank-IC, quantile buckets, breadth; KEEP panel row idx
    rows_idx, targ_w, Yrows, ics, breadth = [], [], [], [], []
    n_q = 5; qy = [[] for _ in range(n_q)]
    for t in range(T):
        v = CL[t] & np.isfinite(pred[t]) & np.isfinite(Y[t])
        if v.sum() < MIN_ASSETS:
            continue
        idx = np.where(v)[0]; sc = pred[t, idx]; yv = Y[t, idx]
        w = np.zeros(S); w[idx] = rank_weights(sc)
        rows_idx.append(t); targ_w.append(w); Yrows.append(np.where(v, Y[t], 0.0))
        ic = spearmanr(sc, yv).correlation
        if np.isfinite(ic): ics.append(ic)
        breadth.append(len(idx))
        order = sc.argsort()
        for qi in range(n_q):
            lo = qi*len(order)//n_q; hi = (qi+1)*len(order)//n_q
            if hi > lo: qy[qi].append(yv[order[lo:hi]].mean())
    rows_idx = np.array(rows_idx); targ_w = np.array(targ_w); Yrows = np.array(Yrows); ics = np.array(ics)
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
    g, tn = series(best["alpha"]); best_turn = best["turn"]
    print(f"\n★ BREAK-EVEN per-side = {best['be']:.3f} bps  (at alpha={best['alpha']}, turnover={best['turn']:.3f}/prd, gross={best['gross_bps']:.4f} bps/prd)")
    print(f"  net ann bps @ cost:  " + "  ".join(f"c{c}={float((g-tn*(c*1e-4)).mean()*per_yr*1e4):.0f}" for c in COST_GRID))
    gross_sh = g.mean()/g.std()*ann if g.std() > 0 else np.nan
    qmeans = [float(np.mean(b)) if b else np.nan for b in qy]
    mono = float(spearmanr(np.arange(n_q), qmeans).correlation)
    print(f"\n  mean rank-IC={ics.mean():+.4f}  IC-IR={ics.mean()/ics.std()*np.sqrt(len(ics)):.2f}  "
          f"gross Sharpe(0-cost)={gross_sh:.2f}  avg breadth={np.mean(breadth):.1f}")
    print(f"  quantile mean-y (bps): {[round(q*1e4,3) for q in qmeans]}  monotonicity={mono:+.3f}")

    # ---- LATENCY-AWARE decay: enter Δ seconds late on the FRESH signal (full turnover) ----
    # Uses the fresh per-period target weights (act on pred(t) each period) and realises the H-forward
    # return from the panel row nearest ts_k+Δ. This cleanly isolates the SIGNAL's intrinsic latency
    # tolerance (a heavily-EMA-smoothed book confounds it: stale weights align with later returns).
    # decay(Δ)=gross(Δ)/gross(0); full-turnover BE(Δ)=gross(Δ)/turnover_full; and the operating-point
    # (low-turnover, headline BE) latency-aware estimate = headline_BE · decay(Δ). Snap to raw grid;
    # a requested lag finer than the panel grid is skipped.
    tn_full = np.empty(n); prev = np.zeros(S)
    for k in range(n):
        tn_full[k] = np.abs(targ_w[k] - prev).sum(); prev = targ_w[k]
    full_turn = float(tn_full.mean()); tol = grid * 0.75
    lag_list = [int(x) for x in a.lags.split(",")]

    def realized(lag):
        tgt = ts + int(round(lag * ts_unit)); out = np.full(n, np.nan)
        for k, ri in enumerate(rows_idx):
            j = np.searchsorted(ts, tgt[ri]); cand = [c for c in (j - 1, j, j + 1) if 0 <= c < T]
            bj = min(cand, key=lambda c: abs(ts[c] - tgt[ri])) if cand else None
            if bj is not None and abs(ts[bj] - tgt[ri]) / ts_unit <= tol and np.isfinite(Y[bj]).any():
                out[k] = float((targ_w[k] * np.where(np.isfinite(Y[bj]), Y[bj], 0.0)).sum())
        return out

    g0m = float(np.nanmean(realized(0))); lat = {}
    for lag in lag_list:
        gl = realized(lag); m = np.isfinite(gl)
        if m.sum() < 0.5 * n:
            lat[lag] = None; continue
        gm = float(np.nanmean(gl)); dec = gm / g0m if g0m else np.nan
        be_full = gm / full_turn * 1e4 if full_turn > 1e-12 else np.inf
        be_op = best["be"] * dec                                             # operating-point BE scaled by signal decay
        net2 = gl[m] - tn_full[m] * (2.0 * 1e-4)
        sh2 = float(net2.mean() / net2.std() * ann) if net2.std() > 0 else np.nan
        lat[lag] = dict(gross_bps=round(gm * 1e4, 4), decay_vs_lag0=round(float(dec), 2),
                        be_full_turn=round(be_full, 3), be_operating_est=round(float(be_op), 3),
                        net_sharpe_c2_fullturn=round(sh2, 2), matched=round(float(m.mean()), 2))
    print(f"\n=== LATENCY-AWARE (fresh signal; full turnover={full_turn:.3f}; headline operating BE={best['be']:.3f}) ===")
    print(f"{'lag(s)':>7s} {'gross_bps':>9s} {'decay':>6s} {'BE_full':>8s} {'BE_op·dec':>9s} {'netSh_full@c2':>13s} {'matched':>8s}")
    for lag in lag_list:
        r = lat.get(lag)
        if r is None:
            print(f"{lag:7d}   (grid≈{grid:.0f}s too coarse for this lag — needs a finer panel)"); continue
        print(f"{lag:7d} {r['gross_bps']:9.4f} {r['decay_vs_lag0']:6.2f} {r['be_full_turn']:8.3f} "
              f"{r['be_operating_est']:9.3f} {r['net_sharpe_c2_fullturn']:13.2f} {r['matched']:8.2f}")

    # GO/NO-GO framing
    tiers = {"maker~1": 1.0, "maker~2": 2.0, "taker~2.5": 2.5, "taker~5": 5.0}
    verdict = {k: ("GO" if best["be"] > c else "underwater") for k, c in tiers.items()}
    print(f"\n★ GO/NO-GO (break-even {best['be']:.2f} bps/side vs tiers): " +
          "  ".join(f"{k}({c})→{verdict[k]}" for k, c in tiers.items()))
    out = dict(tag=a.tag, horizon=a.horizon, n_periods=n, mean_rank_ic=round(float(ics.mean()), 4),
               ic_ir=round(float(ics.mean()/ics.std()*np.sqrt(len(ics))), 2),
               breakeven_per_side_bps=round(best["be"], 3), best_alpha=best["alpha"],
               gross_sharpe_zerocost=round(float(gross_sh), 2), quantile_monotonicity=round(mono, 3),
               avg_breadth=round(float(np.mean(breadth)), 1), tier_verdict=verdict,
               raw_grid_s=round(grid, 1), latency=lat)
    json.dump(out, open(op.join(d, "ls_gate.json"), "w"), indent=2)
    print(f"\nsaved -> {op.join(d, 'ls_gate.json')}\nDONE_LS_GATE")


if __name__ == "__main__":
    main()

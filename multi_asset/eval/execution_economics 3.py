"""EXECUTION-ECONOMICS re-verdict — are the 'not tradeable' calls just TAKER-cost-conditional?

Top props execute maker/rebate ~0.2-1 bps effective; our verdicts assumed 1.7-5 bps taker. Re-score
the key candidates on a PROP-GRADE cost grid {0.2,0.5,1.0,1.7} bps/side. KEY: the operating point is
cost-dependent — book_stats picks the net-Sh-optimal α AT EACH COST, so at cheap cost it flips from
EMA-hold (taker) to full-turnover (maker), exactly where a fast signal (M0 2023/24) can come alive.
Deliverable: per candidate × cost × year net-Sh + the flip point ("tradeable below X bps effective").
Plus a NETTING quick-test (funding + λ0.3-M0 as ONE book vs two costed separately).

Usage: PYTHONPATH=. python multi_asset/eval/execution_economics.py
"""
from __future__ import annotations
import sys, os.path as op, datetime as dt, numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.eval.factor_pipeline import load_panel
from multi_asset.eval.portfolio_scorecard import book_stats, MIN_ASSETS
from multi_asset.eval.backtest_longshort import rank_weights

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
COSTS = [0.2, 0.5, 1.0, 1.7]


def _years(ts):
    u = 1e9 if ts[0] > 1e17 else (1e6 if ts[0] > 1e14 else 1e3)
    return np.array([dt.datetime.utcfromtimestamp(int(t) / u).year for t in ts])


def _netsh_at(sig, Y, CL, ts, day, cost):
    st = book_stats(sig, Y, CL, ts, day, 3600, cost_bps=cost)
    return st["net_sh_c2"], st["alpha"]


def _flip(row):
    """highest cost tier with net-Sh > 0 (the 'tradeable below' point)."""
    pos = [c for c in COSTS if row[c] is not None and row[c] > 0]
    return f"≤{max(pos)}bps" if pos else "never(>1.7)"


def score(name, sig, Y, CL, ts, day, years):
    yr = _years(ts)
    print(f"\n{name}")
    for y in years:
        rows = np.where(yr == y)[0]
        clean = [t for t in rows if (CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t])).sum() >= MIN_ASSETS]
        if len(clean) < 100:
            print(f"  {y} | (no OOS preds in this window)")
            continue
        r = {}
        for c in COSTS:
            ns, al = _netsh_at(sig[rows], Y[rows], CL[rows], ts[rows], day[rows], c)
            r[c] = round(ns, 2) if np.isfinite(ns) else None
        cells = "  ".join(f"{c}:{r[c]:+.2f}" if r[c] is not None else f"{c}:na" for c in COSTS)
        print(f"  {y} | net-Sh@ {cells}  | flip: {_flip(r)}")


def main():
    # --- fullhist candidates (per-year 2023/24/25), each on its OWN >=3600-CL grid ---
    print("=" * 90)
    print("EXECUTION-ECONOMICS TABLE — net-Sh at prop-grade cost {0.2,0.5,1.0,1.7} bps/side (cost-optimal α)")
    print("=" * 90)
    for name, tag in [("M0 (fullhist)", "m0_fullhist_wf"), ("λ0.3-M0 (fullhist)", "P1b_lambda03"),
                      ("funding (fullhist)", "fund_ema_fullhist")]:
        P = load_panel(tag, E)
        score(name, P["pred"], P["Y"], P["CL"].astype(bool), P["ts"].astype(np.int64), P["day"].astype(np.int64),
              [2023, 2024, 2025])

    # --- 487-window candidates (ensemble + fast-micro): grid = fund_ema_h3600 >=3600 CL ---
    G = load_panel("fund_ema_h3600", E)
    Yg, CLg, tsg, dayg = G["Y"], G["CL"].astype(bool), G["ts"].astype(np.int64), G["day"].astype(np.int64)

    def _al(tag):
        P = load_panel(tag, E); p = P["pred"]; pts = P["ts"].astype(np.int64)
        if p.shape[0] == len(tsg) and np.array_equal(pts, tsg):
            return p
        out = np.full((len(tsg), p.shape[1]), np.nan); common, ig, io = np.intersect1d(tsg, pts, return_indices=True)
        out[ig] = p[io]; return out
    ens = np.nanmean(np.stack([_al("fund_resid_h3600"), _al("fund_resid_h3600_s43"), _al("fund_resid_h3600_s44")]), axis=0)
    score("3-seed ENSEMBLE (487≈2025)", ens, Yg, CLg, tsg, dayg, [2024, 2025])
    score("fast-micro baseline (487≈2025)", _al("h3600"), Yg, CLg, tsg, dayg, [2024, 2025])

    # --- NETTING test: funding + λ0.3-M0 as ONE book vs two costed separately (fullhist, full-turnover) ---
    print("\n" + "=" * 90)
    print("NETTING TEST — combined book (funding + λ0.3-M0) turnover vs sum-of-separate (full rebalance)")
    print("=" * 90)
    F = load_panel("fund_ema_fullhist", E); M = load_panel("P1b_lambda03", E)
    Y, CL, ts = F["Y"], F["CL"].astype(bool), F["ts"].astype(np.int64)
    fu, m0 = F["pred"], (M["pred"] if np.array_equal(M["ts"].astype(np.int64), ts) else None)
    if m0 is None:
        common, iF, iM = np.intersect1d(ts, M["ts"].astype(np.int64), return_indices=True)
        Y, CL, ts = Y[iF], CL[iF], ts[iF]; fu = fu[iF]; m0 = M["pred"][iM]
    yr = _years(ts)
    for y in [2023, 2024, 2025]:
        rows = np.where(yr == y)[0]
        Wf = []; Wm = []; Wc = []
        for t in rows:
            v = CL[t] & np.isfinite(fu[t]) & np.isfinite(m0[t]) & np.isfinite(Y[t])
            if v.sum() < MIN_ASSETS:
                continue
            idx = np.where(v)[0]; S = Y.shape[1]
            wf = np.zeros(S); wm = np.zeros(S)
            wf[idx] = rank_weights(fu[t, idx]); wm[idx] = rank_weights(m0[t, idx])
            Wf.append(wf); Wm.append(wm); Wc.append(wf + wm)                 # combined = netted book
        Wf, Wm, Wc = np.array(Wf), np.array(Wm), np.array(Wc)
        tf = np.abs(np.diff(Wf, axis=0)).sum(1).mean(); tm = np.abs(np.diff(Wm, axis=0)).sum(1).mean()
        tc = np.abs(np.diff(Wc, axis=0)).sum(1).mean()
        save = 1 - tc / (tf + tm) if (tf + tm) > 0 else 0
        print(f"  {y} | turnover funding {tf:.3f} + M0 {tm:.3f} = {tf+tm:.3f} separate | combined {tc:.3f} | "
              f"nets out {save*100:.0f}%")
    print("DONE_EXEC_ECON")


if __name__ == "__main__":
    main()

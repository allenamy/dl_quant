"""P1b terminal verdict — did the Δpred-penalty (persistence-aware) training FIX M0's fast-signal defect?

Two DECISIVE pre-registered reads on the fullhist walk-forward preds (2023/24/25), vs the M0 baseline:
  (1) ★ per-year weight-autocorr (persistence): rose to >=0.5 on 2023 AND 2024? (M0 was 0.26/0.18/0.51)
  (2) per-year EMA-hold net-cost@5 (deployable, net-Sh-optimal operating alpha): flips positive on
      >=2/3 years? (M0 was -2.1/-1.7/+1.2)
IC criterion (degradation <20%) already confirmed by trainer (te2023 -11% / te2024 +30% / te2025 -17%).

LADDER decision (locked): all pass -> ACCEPT (+ seed check); autocorr up but <0.5 & IC alive -> λ=0.3 arm;
autocorr unmoved -> STOP ("M0 intrinsically fast"). Grid = the tag's own panel_ref (>=3600 CL).

Usage: PYTHONPATH=. python multi_asset/eval/p1b_verdict.py --tag P1b_lambda01
"""
from __future__ import annotations
import sys, os.path as op, argparse, datetime as dt, numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.eval.factor_pipeline import load_panel
from multi_asset.eval.factor_scorer import _perts_ic
from multi_asset.eval.portfolio_scorecard import book_stats, MIN_ASSETS
from multi_asset.eval.backtest_longshort import rank_weights

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
M0_AC = {2023: 0.26, 2024: 0.18, 2025: 0.51}
M0_N5 = {2023: -2.05, 2024: -1.77, 2025: 1.37}
M0_IC = {2023: 0.0430, 2024: 0.0333, 2025: 0.0333}
YEARS = [2023, 2024, 2025]


def _persist(sig, Y, CL, rows):
    S = Y.shape[1]; W = []
    for t in rows:
        v = CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t])
        if v.sum() >= MIN_ASSETS and np.std(sig[t, v]) > 1e-12:
            w = np.zeros(S); idx = np.where(v)[0]; w[idx] = rank_weights(sig[t, idx]); W.append(w)
    W = np.array(W); a, b = W[:-1].ravel(), W[1:].ravel(); m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 10 else np.nan


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="P1b_lambda01"); a = ap.parse_args()
    P = load_panel(a.tag, E)
    Y, CL, ts, day = P["Y"], P["CL"].astype(bool), P["ts"].astype(np.int64), P["day"].astype(np.int64)
    pred = P["pred"]
    u = 1e9 if ts[0] > 1e17 else (1e6 if ts[0] > 1e14 else 1e3)
    yr = np.array([dt.datetime.utcfromtimestamp(int(t) / u).year for t in ts])
    print(f"tag={a.tag}: T={len(ts)} CL-frac={CL.mean():.3f} "
          f"[{'≥3600 OK' if CL.mean() < 0.15 else 'WARN dense-CL'}]")
    print(f"\n{'year':4s} | rank-IC (ΔvsM0)   | persistence (M0→P1b)  | net-Sh@5 EMA-hold (M0→P1b) α")
    ac = {}; n5 = {}; ic = {}
    for y in YEARS:
        rows = np.where(yr == y)[0]
        if len(rows) < 100:
            continue
        Yr, CLr, tsr, dayr = Y[rows], CL[rows], ts[rows], day[rows]; pr = pred[rows]
        icv, _ = _perts_ic(pr, Yr, CLr); ic[y] = icv.mean()
        acv = _persist(pr, Yr, CLr, np.arange(len(rows))); ac[y] = acv
        st = book_stats(pr, Yr, CLr, tsr, dayr, 3600); n5[y] = st["net_sh_grid"][5.0]
        dic = (ic[y] - M0_IC[y]) / abs(M0_IC[y]) * 100
        print(f"{y} | {ic[y]:+.4f} ({dic:+.0f}%) | {M0_AC[y]:.2f} → {acv:+.3f}       | "
              f"{M0_N5[y]:+.2f} → {n5[y]:+.2f}  (α{st['alpha']})")

    # ---- ladder verdict ----
    ac_pass = (ac.get(2023, 0) >= 0.5) and (ac.get(2024, 0) >= 0.5)
    ac_moved = (ac.get(2023, 0) > M0_AC[2023] + 0.08) and (ac.get(2024, 0) > M0_AC[2024] + 0.08)
    n5_pass = sum(1 for y in YEARS if n5.get(y, -9) > 0) >= 2
    ic_alive = all((ic.get(y, 0) - M0_IC[y]) / abs(M0_IC[y]) > -0.20 for y in YEARS)
    print("\n" + "=" * 70)
    print(f"READ 1 — persistence ≥0.5 on 2023 AND 2024: {ac_pass}  (2023 {ac.get(2023):.2f}, 2024 {ac.get(2024):.2f})")
    print(f"READ 2 — EMA-hold net-Sh@5 positive ≥2/3 years: {n5_pass}  ({[round(n5.get(y,float('nan')),2) for y in YEARS]})")
    print(f"IC alive (no year < −20%): {ic_alive}")
    if ac_pass and n5_pass and ic_alive:
        verdict = "★ ACCEPT — P1b FIXES M0's persistence defect. Next: 3-seed confirm, then re-admit to Book-1."
    elif ac_moved and ic_alive:
        verdict = "PARTIAL — autocorr moved up but <0.5 and IC alive → escalate to λ=0.3 arm."
    elif abs(ac.get(2023, 0) - M0_AC[2023]) < 0.08 and abs(ac.get(2024, 0) - M0_AC[2024]) < 0.08:
        verdict = "STOP — autocorr unmoved → M0 is intrinsically fast; the DL leg does not generalize net-cost."
    else:
        verdict = "MIXED — see per-year; ladder rule ambiguous, report raw for lead decision."
    print(f"\n★ LADDER VERDICT: {verdict}")
    print("DONE_P1B_VERDICT")


if __name__ == "__main__":
    main()

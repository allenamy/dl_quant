"""y180 (3-min) book RE-PRICE under execution-open economics — Part A: net-cost at the new cost grid.

The old y180 book (R1_y180, cs-rank-IC 0.0734) was shelved 2026-06-14: per-trade ~0.5 bps < the 3 bps
taker floor. Execution-economics reopens it: at prop maker/rebate {0.2,0.5,1.0} bps/side does the
gross flip net-positive? (Part B = the decisive fill-window-decay physics check, separate script —
a 3-min signal lives INSIDE the 5s-5min adverse-selection window, so passive-fill decay may kill it
even if Part A flips positive.)

Usage: PYTHONPATH=. python multi_asset/eval/y180_reprice.py --tag R1_y180
"""
from __future__ import annotations
import sys, os.path as op, argparse, datetime as dt, numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.eval.factor_pipeline import load_panel
from multi_asset.eval.factor_scorer import _perts_ic
from multi_asset.eval.portfolio_scorecard import book_stats

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
COSTS = [0.2, 0.5, 1.0, 3.0]   # prop-grade + the old 3 bps taker floor for reference


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="R1_y180"); a = ap.parse_args()
    P = load_panel(a.tag, E)
    Y, CL, ts, day = P["Y"], P["CL"].astype(bool), P["ts"].astype(np.int64), P["day"].astype(np.int64)
    pred = P["pred"]
    grid = int(np.median(np.diff(np.unique(ts))))
    u = 1e9 if ts[0] > 1e17 else (1e6 if ts[0] > 1e14 else 1e3)
    d0 = dt.datetime.utcfromtimestamp(int(ts[0]) / u); d1 = dt.datetime.utcfromtimestamp(int(ts[-1]) / u)
    ic, _ = _perts_ic(pred, Y, CL)
    print(f"tag={a.tag} | T={len(ts)} CL-frac={CL.mean():.3f} | ts-grid≈{grid/ (1e6 if u==1e6 else 1e3 if u==1e3 else 1):.0f}?units "
          f"| {d0:%Y-%m} .. {d1:%Y-%m}")
    print(f"pooled cs-rank-IC = {ic.mean():+.4f} (IR {ic.mean()/(ic.std()+1e-12):.2f}, n_ts={len(ic)})  [shelved number ~0.0734]")

    print(f"\nNET-COST L/S (180s rebalance, EMA-hold operating-α at each cost):")
    print(f"  {'cost bps/side':>13} | {'net-Sh':>7} {'BE/side':>8} {'turnover':>9} {'α':>5} {'gross-Sh':>9}")
    for c in COSTS:
        st = book_stats(pred, Y, CL, ts, day, 180, cost_bps=c)
        print(f"  {c:>13} | {st['net_sh_c2']:>+7.2f} {st['be']:>8.2f} {st['turnover']:>9.3f} {st['alpha']:>5} {st['gross_sh']:>+9.2f}")
    # flip point = highest cost with net-Sh>0
    flips = [c for c in COSTS if book_stats(pred, Y, CL, ts, day, 180, cost_bps=c)['net_sh_c2'] > 0]
    print(f"\n  → net-positive at cost ≤ {max(flips) if flips else 'never'} bps/side  "
          f"(shelved because per-trade > the OLD 3 bps taker floor; the question is whether ≤0.5 bps prop cost clears it)")
    print("DONE_Y180_REPRICE")


if __name__ == "__main__":
    main()

"""Day-block bootstrap + LOMO of the EXACT cost-aware @taker-1.7 state-machine path (the +1801/+1725
'positive' the lead flagged). Is it distinguishable from 0, or one-month-driven?  Imports the audited
engine (no re-implementation)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.eval.taker_backtest import (load_preds, nonoverlap_grid, decision_center,
                                             calibrate_offtest, run_strategy, DAY, MONTHS)

CFG = dict(W=12, cost=1.7, buf_long=1.0, buf_short=0.5, exit_frac=0.3, min_hold=1)  # cost-AWARE @1.7

def path_pnl(csv):
    df = load_preds(csv); G = nonoverlap_grid(df)
    ts = G.ts.values.astype(np.int64); y = G.y.values; p = G.p.values; mon = G.month.values
    d = p - decision_center(p, CFG["W"]); eh = calibrate_offtest(d, y, mon)
    pnl, pos, dpis = run_strategy(eh, y, CFG["cost"], CFG["buf_long"], CFG["buf_short"],
                                  CFG["exit_frac"], CFG["min_hold"])
    return ts, pnl, mon

def report(label, csv, nboot=5000, seed=0):
    ts, pnl, mon = path_pnl(csv)
    day = ts // DAY
    tot = float(pnl.sum())
    dser = pd.Series(pnl).groupby(day).sum().values; nd = len(dser)
    rng = np.random.default_rng(seed)
    boots = np.array([dser[rng.integers(0, nd, nd)].sum() for _ in range(nboot)])
    fpos = float(np.mean(boots > 0)); lo, hi = np.percentile(boots, [2.5, 97.5])
    z = tot / (boots.std() + 1e-12)
    print(f"\n[{label}] cost-aware @1.7 net = {tot:.1f} bps  ({nd} days)")
    print(f"  day-block bootstrap: mean={boots.mean():.0f}  95%CI=[{lo:.0f},{hi:.0f}]  frac>0={fpos:.3f}  z={z:.2f}"
          f"  -> {'distinguishable>0' if lo > 0 else 'STRADDLES 0 (not distinguishable)'}")
    # per-month + LOMO
    print("  per-month net | LOMO (drop month):")
    permo = {}
    for mk in MONTHS:
        sm = mon == mk
        if sm.sum() == 0: continue
        permo[mk] = float(pnl[sm].sum())
    for mk, v in permo.items():
        print(f"    {mk}: {v:8.1f}   drop-{mk}: {tot - v:8.1f}")
    worst = min(tot - v for v in permo.values())
    best_mk = max(permo, key=permo.get)
    print(f"  total={tot:.1f}  best month={best_mk}({permo[best_mk]:.0f})  worst-LOMO={worst:.1f}"
          f"  -> {'SURVIVES' if worst > 0 else 'DIES'} leave-one-month-out")

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
report("PROD", f"{MA}/exports/prod_commonY.csv")
report("RUN1", f"{MA}/exports/run1_commonY.csv")

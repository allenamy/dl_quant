#!/usr/bin/env python3
"""Export per-rebalance funding_ema L/S return series for a given YEAR (0C's 2024 sub-check).

> **created:** 2026-07-08 | **Session:** multi-asset-v2 hardening (0B) | **状态:** in-progress

2024 has the STRONGEST funding IC (z5.64) but NEGATIVE gross-Sh (−1.11) — rank-right, magnitude-wrong.
This dumps the per-hour L/S gross+net return series so 0C can see if it's a tail-event (few extreme
days) or a persistent regime. Reuses megacap_funding_replay.build_panel (14 mega-caps full history).
Usage: PYTHONPATH=. python multi_asset/data/build_funding_year_series.py [year=2024]
"""
from __future__ import annotations
import csv, os.path as p, sys
import numpy as np, pandas as pd

from multi_asset.data.megacap_funding_replay import build_panel, COST, E, HOUR_MS


def main(year=2024):
    grid, syms, CLOSE, FUND = build_panel()
    logc = np.log(np.where(CLOSE > 0, CLOSE, np.nan))
    Y = np.full_like(logc, np.nan); Y[:-1] = logc[1:] - logc[:-1]
    yr = pd.to_datetime(grid, unit="ms", utc=True).year
    rows = np.where(yr == year)[0]
    out = []
    prevW = None
    for i in rows:
        v = np.isfinite(FUND[i]) & np.isfinite(Y[i])
        if v.sum() < 5:
            continue
        f = -FUND[i, v]
        z = (f - f.mean()) / (f.std() + 1e-12); z -= z.mean()
        W = np.zeros(FUND.shape[1]); s = np.abs(z).sum()
        if s > 0:
            W[np.where(v)[0]] = z / s
        gross = float(np.nansum(W * np.nan_to_num(Y[i])))
        turn = float(np.abs(W - (prevW if prevW is not None else 0)).sum()); prevW = W
        net = gross - COST * turn
        out.append((int(grid[i]), gross, net, turn))
    arr = np.array([(g, n) for _, g, n, _ in out])
    fn = p.join(E, f"eda/funding_{year}_series.csv")
    with open(fn, "w", newline="") as fp:
        w = csv.writer(fp); w.writerow(["ts_ms", "gross_ret", "net_ret", "turnover"])
        w.writerows(out)
    g = arr[:, 0]; n = arr[:, 1]
    # tail diagnosis: worst-5-day share of the total loss
    daily = pd.Series(g, index=pd.to_datetime([o[0] for o in out], unit="ms", utc=True)).resample("1D").sum()
    worst = daily.nsmallest(5)
    print(f"[{year}] {len(out)} hrs | gross sum={g.sum():+.4f} net sum={n.sum():+.4f} | "
          f"gross mean/hr={g.mean():+.2e} std={g.std():.2e}", flush=True)
    print(f"  worst-5-DAY gross = {worst.values.round(4).tolist()} (sum {worst.sum():+.4f}) "
          f"vs full-year gross {daily.sum():+.4f} -> worst-5-day share {worst.sum()/daily.sum()*100 if daily.sum()!=0 else float('nan'):.0f}%", flush=True)
    print(f"  -> {fn}", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2024)

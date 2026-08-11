"""A1 — the 7-year funding_ema DEPLOYABLE (EMA-hold) table + A3 coverage check.

The megacap replay scored per-year on FIXED full-turnover only; 0C's grid showed 2024 flips
−1.52 (fixed) → +0.85 (EMA-hold). This re-scores ALL years 2020-2026 on BOTH calibers so we have
the honest number to size real money on. Same 14-mega-cap hourly panel + z-weighted crowding-reversion
book as megacap_funding_replay; adds the EMA-hold operating-alpha sweep (deployable = net-Sh-optimal).

Usage: PYTHONPATH=. python multi_asset/eval/funding_7yr_emahold.py
"""
from __future__ import annotations
import sys, os.path as op, numpy as np, pandas as pd
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.data.megacap_funding_replay import build_panel, HOUR_MS

COST = {2: 2e-4, 5: 5e-4}
ANN = np.sqrt(24 * 365)
ALPHA_GRID = (1.0, 0.5, 0.3, 0.2, 0.1, 0.05, 0.02)
MIN = 5


def zw(fvec):
    """crowding-reversion z-weights: long low funding / short high (sign −1), dollar-neutral gross~2."""
    z = (fvec - fvec.mean()) / (fvec.std() + 1e-12); z -= z.mean()
    s = np.abs(z).sum()
    return z / s if s > 0 else z * 0.0


def held_stats(Wt, Yr, cost):
    """EMA-hold sweep -> operating alpha = max net-Sh at `cost`; return that + fixed-turnover(alpha=1)."""
    S = Wt.shape[1]

    def run(alpha):
        h = np.zeros(S); n = len(Wt); g = np.empty(n); tn = np.empty(n)
        for k in range(n):
            new = alpha * Wt[k] + (1 - alpha) * h
            tn[k] = np.abs(new - h).sum(); g[k] = float(np.nansum(new * Yr[k])); h = new
        net = g - tn * cost
        nsh = float(net.mean() / net.std() * ANN) if net.std() > 0 else np.nan
        be = float(g.mean() / tn.mean() * 1e4) if tn.mean() > 1e-12 else np.nan
        return nsh, be, float(tn.mean())
    best = max(ALPHA_GRID, key=lambda al: (run(al)[0] if np.isfinite(run(al)[0]) else -1e9))
    return dict(ema=run(best), ema_alpha=best, fixed=run(1.0))


def main():
    grid, syms, CLOSE, FUND = build_panel()
    logc = np.log(np.where(CLOSE > 0, CLOSE, np.nan))
    Y = np.full_like(logc, np.nan); Y[:-1] = logc[1:] - logc[:-1]
    gap = np.zeros(len(grid), bool); gap[:-1] = (grid[1:] - grid[:-1]) > 2 * HOUR_MS; Y[gap] = np.nan
    yr = pd.to_datetime(grid, unit="ms", utc=True).year
    dmax = pd.to_datetime(grid[-1], unit="ms", utc=True)
    print(f"panel: {len(syms)} syms, {pd.to_datetime(grid[0],unit='ms',utc=True):%Y-%m-%d} .. {dmax:%Y-%m-%d} "
          f"(A3 coverage: through {dmax:%Y-%m})")
    print(f"\n{'year':4s} | fixed-turnover net-Sh@2/@5 | EMA-hold net-Sh@2/@5 (α, BE, turn) | flip?")
    rows_out = {}
    for y in sorted(set(int(v) for v in yr)):
        idx = np.where(yr == y)[0]
        Wt = []; Yr = []
        for t in idx:
            v = np.isfinite(FUND[t]) & np.isfinite(Y[t])
            if v.sum() < MIN:
                continue
            w = np.zeros(FUND.shape[1]); w[np.where(v)[0]] = zw(-FUND[t, v])   # sign −1 baked via −FUND
            Wt.append(w); Yr.append(np.where(np.isfinite(Y[t]), Y[t], 0.0))
        if len(Wt) < 100:
            continue
        Wt = np.array(Wt); Yr = np.array(Yr)
        f2 = held_stats(Wt, Yr, COST[2])["fixed"]; f5 = held_stats(Wt, Yr, COST[5])["fixed"]
        e = held_stats(Wt, Yr, COST[2]); e2 = e["ema"]; e5 = held_stats(Wt, Yr, COST[5])["ema"]
        flip = "★FLIP" if (f5[0] < 0) and (e5[0] > 0) else ("worse" if e5[0] < f5[0] else "")
        rows_out[y] = dict(fixed2=f2[0], fixed5=f5[0], ema2=e2[0], ema5=e5[0], alpha=e["ema_alpha"], be=e2[1], turn=e2[2], n=len(Wt))
        print(f"{y} | {f2[0]:+6.2f} / {f5[0]:+6.2f}          | {e2[0]:+6.2f} / {e5[0]:+6.2f}  "
              f"(α{e['ema_alpha']}, BE{e2[1]:.1f}, tn{e2[2]:.3f}) | {flip}")
    ev = [rows_out[y]["ema5"] for y in rows_out]; fv = [rows_out[y]["fixed5"] for y in rows_out]
    print(f"\nDEPLOYABLE (EMA-hold) net-Sh@5: mean {np.mean(ev):+.2f}  median {np.median(ev):+.2f}  "
          f"min {np.min(ev):+.2f}  pos-years {sum(1 for x in ev if x>0)}/{len(ev)}")
    print(f"FIXED-turnover   net-Sh@5: mean {np.mean(fv):+.2f}  median {np.median(fv):+.2f}  "
          f"pos-years {sum(1 for x in fv if x>0)}/{len(fv)}")
    print("DONE_7YR_EMAHOLD")


if __name__ == "__main__":
    main()

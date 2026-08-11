"""A2 — funding_ema tail-squeeze mitigation: do causal risk overlays compress the worst-5-day loss
without eating the good years? Overlays (all causal, past-only):
  (a) per-NAME cap: clip |w_i| to cap/N (de-concentrate the extreme-funding names = squeeze risk)
  (b) portfolio VOL-TARGET: scale book by target/trailing-24h realized vol
  (c) SQUEEZE-DAY de-risk: de-lever (×0.5) when trailing-24h cap-wtd |market move| > threshold
Per year (2020-2026): net-Sh@5 (EMA-hold operating alpha) + worst-5-DAY gross loss, base vs each overlay.

Usage: PYTHONPATH=. python multi_asset/eval/funding_riskoverlay.py
"""
from __future__ import annotations
import sys, os.path as op, numpy as np, pandas as pd
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.data.megacap_funding_replay import build_panel, HOUR_MS
from multi_asset.eval.funding_7yr_emahold import zw, held_stats, COST, ALPHA_GRID

MIN = 5


def worst5day(grid_idx, grid, g):
    """worst-5-DAY sum of the per-ts gross series g (aligned to grid_idx)."""
    days = pd.to_datetime(grid[grid_idx], unit="ms", utc=True).date
    s = pd.Series(g, index=days).groupby(level=0).sum().sort_values()
    return float(s.head(5).sum()), float(s.sum())


def build_book(FUND, Y, CLOSE, idx, overlay, thr=0.05, cap=1.5, tvol=None):
    """Return (Wt, Yr, grid_idx_used, gross_series) for the given overlay over rows idx."""
    S = FUND.shape[1]; logc = np.log(np.where(CLOSE > 0, CLOSE, np.nan))
    Wt = []; Yr = []; used = []
    # trailing 24h book-vol + market-move need a running history; compute causally over idx order
    gross_hist = []
    for t in idx:
        v = np.isfinite(FUND[t]) & np.isfinite(Y[t])
        if v.sum() < MIN:
            continue
        w = np.zeros(S); w[np.where(v)[0]] = zw(-FUND[t, v])
        if overlay == "cap":
            lim = cap / v.sum()
            w = np.clip(w, -lim, lim)
            s = np.abs(w).sum();  w = w / s * 1.0 if s > 0 else w      # renorm gross~1 (cap changes gross)
        elif overlay == "voltarget":
            if len(gross_hist) >= 24:
                rv = np.std(gross_hist[-24:]) + 1e-9
                w = w * min(1.5, (tvol / rv))
        elif overlay == "squeeze":
            # trailing 24h max |asset 1h move| across the book (causal proxy for a squeeze cascade)
            if len(used) >= 24:
                recent = [r for r in used[-24:]]
                mm = np.nanmax([np.nanmax(np.abs(Y[r])) for r in recent])
                if mm > thr:
                    w = w * 0.5
        g_now = float(np.nansum(w * np.where(np.isfinite(Y[t]), Y[t], 0.0)))
        gross_hist.append(g_now)
        Wt.append(w); Yr.append(np.where(np.isfinite(Y[t]), Y[t], 0.0)); used.append(t)
    return np.array(Wt), np.array(Yr), np.array(used), np.array(gross_hist)


def main():
    grid, syms, CLOSE, FUND = build_panel()
    logc = np.log(np.where(CLOSE > 0, CLOSE, np.nan))
    Y = np.full_like(logc, np.nan); Y[:-1] = logc[1:] - logc[:-1]
    gap = np.zeros(len(grid), bool); gap[:-1] = (grid[1:] - grid[:-1]) > 2 * HOUR_MS; Y[gap] = np.nan
    yr = pd.to_datetime(grid, unit="ms", utc=True).year
    # target vol = median trailing book vol of the BASE book (for voltarget scale)
    _, _, _, gbase_all = build_book(FUND, Y, CLOSE, np.where(np.isfinite(yr))[0], "base")
    tvol = float(np.median(np.abs(gbase_all))) * 1.2 if len(gbase_all) else 2e-3

    print(f"{'year':4s} | overlay      | net-Sh@5(EMA) | worst-5day loss | (base->overlay Δ)")
    for y in sorted(set(int(v) for v in yr)):
        idx = np.where(yr == y)[0]
        base_w5 = None
        for ov in ["base", "cap", "voltarget", "squeeze"]:
            Wt, Yr, used, gser = build_book(FUND, Y, CLOSE, idx, ov, tvol=tvol)
            if len(Wt) < 100:
                continue
            e5 = held_stats(Wt, Yr, COST[5])["ema"]
            w5, _tot = worst5day(used, grid, gser)
            if ov == "base":
                base_w5 = w5
            d = f"(Δw5 {w5-base_w5:+.4f})" if (base_w5 is not None and ov != "base") else ""
            print(f"{y} | {ov:11s} | {e5[0]:+7.2f}       | {w5:+.4f}         {d}")
        print()
    print("DONE_RISKOVERLAY")


if __name__ == "__main__":
    main()

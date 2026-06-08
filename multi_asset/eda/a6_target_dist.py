"""A6 — Per-asset target distribution.

Sample ~26 days. Per asset, on y_600:
  - MAD-sigma in bps (MAD * 1.4826), pooled over clean (non-overlap) samples.
  - excess kurtosis (Fisher) on clean y_600.
  - Hill tail index on |y| top 5% (alpha = 1 / mean(log(x_i / x_min)) over the top tail).
  - sign balance = mean(y>0) on clean y_600.
  - clean autocorr(y_600, lag) for lag in {600,1200,3600}s using NON-OVERLAP samples
    at that lag (so labels are disjoint; a high value flags stale-mid / overlap artifact).

GOAL: validate per-asset MAD-sigma normalization makes assets comparable; flag
stale-mid autocorr artifacts.

Read-only. Clean = non-overlap stride>=600.
"""
from __future__ import annotations

import json
import os.path as p

import numpy as np
from scipy import stats

from _eda_common import (SYMBOLS, HORIZON, list_all_days, sample_days_spread,
                         col, y600_full, clean_mask, mad_sigma, day_exists,
                         ensure_export_dir)

AC_LAGS = [600, 1200, 3600]


def hill_index(absy: np.ndarray, top_frac: float = 0.05) -> float:
    """Hill estimator of tail index alpha on the top `top_frac` of |y|.
    alpha = 1 / mean(log(x_i) - log(x_min)) over the order stats above the threshold.
    Higher alpha => thinner tail; alpha<~3 => heavy (infinite 3rd+ moments)."""
    x = np.sort(absy[np.isfinite(absy) & (absy > 0)])
    if x.size < 200:
        return np.nan
    k = max(int(round(top_frac * x.size)), 50)
    tail = x[-k:]
    xmin = tail[0]
    if xmin <= 0:
        return np.nan
    logs = np.log(tail / xmin)
    denom = np.mean(logs)
    if denom <= 0:
        return np.nan
    return float(1.0 / denom)


def main():
    all_days = list_all_days()
    days = sample_days_spread(all_days, n=26, start=20230101, end=20251130)
    days = [d for d in days if day_exists(d)]
    print("# A6 — Per-asset target distribution")
    print(f"Sampling: {len(days)} days spread 2023-2025: {days[0]}..{days[-1]}.\n")

    # pooled clean y per symbol, plus per-day clean series for autocorr at lags
    clean_y = {s: [] for s in SYMBOLS}
    # for autocorr we keep, per day, the dense y (for shifting) and build non-overlap pairs
    ac_pairs = {s: {lag: ([], []) for lag in AC_LAGS} for s in SYMBOLS}

    for d in days:
        try:
            from multi_asset.data.bar_loader import load_day_panel
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            print(f"  [warn] day {d} load failed: {e}")
            continue
        T = dp.ts.shape[0]
        cm = clean_mask(T, HORIZON, stride=HORIZON)
        cidx = np.where(cm)[0]
        for s in SYMBOLS:
            mid = col(dp, s, "mid")
            y = y600_full(mid, HORIZON)
            yc = y[cidx]
            clean_y[s].append(yc[np.isfinite(yc)])
            # autocorr at lag L: pair y[t] with y[t+L] where both windows are disjoint
            # use stride=HORIZON sampling; lag must be multiple of HORIZON for disjoint.
            for lag in AC_LAGS:
                if lag % HORIZON != 0:
                    # fall back: still non-overlap because we sample on stride=600 grid
                    pass
                step = HORIZON  # disjoint sample spacing
                base = np.arange(0, T - HORIZON - lag, step)
                a = y[base]
                b = y[base + lag]
                m = np.isfinite(a) & np.isfinite(b)
                ac_pairs[s][lag][0].append(a[m])
                ac_pairs[s][lag][1].append(b[m])

    out = {}
    for s in SYMBOLS:
        y = np.concatenate(clean_y[s]) if clean_y[s] else np.array([])
        if y.size < 200:
            out[s] = {"n_clean": int(y.size), "note": "insufficient_clean_samples"}
            continue
        mad_bps = mad_sigma(y) * 1e4
        exk = float(stats.kurtosis(y, fisher=True, bias=False))
        hill = hill_index(np.abs(y), 0.05)
        signbal = float(np.mean(y > 0))
        ac = {}
        for lag in AC_LAGS:
            a = np.concatenate(ac_pairs[s][lag][0]) if ac_pairs[s][lag][0] else np.array([])
            b = np.concatenate(ac_pairs[s][lag][1]) if ac_pairs[s][lag][1] else np.array([])
            if a.size >= 50 and np.std(a) > 0 and np.std(b) > 0:
                ac[lag] = round(float(np.corrcoef(a, b)[0, 1]), 4)
            else:
                ac[lag] = None
        out[s] = {
            "n_clean": int(y.size),
            "mad_sigma_bps": round(mad_bps, 3),
            "excess_kurtosis": round(exk, 2),
            "hill_alpha_top5pct": round(hill, 3) if np.isfinite(hill) else None,
            "sign_balance_mean_pos": round(signbal, 4),
            "autocorr": {str(k): v for k, v in ac.items()},
        }

    result = {
        "analysis": "A6_target_dist",
        "sampling": f"{len(days)} days spread 2023-2025: {days[0]}..{days[-1]}",
        "clean_grid": "non-overlap stride>=600",
        "autocorr_def": "disjoint-sample corr(y[t],y[t+lag]) on stride=600 grid; high => stale-mid/overlap artifact",
        "per_symbol": out,
    }
    ed = ensure_export_dir()
    with open(p.join(ed, "a6_target_dist.json"), "w") as f:
        json.dump(result, f, indent=2)

    print("| sym | n_clean | MAD-sigma(bps) | exc_kurt | Hill_a(top5%) | sign_bal | "
          "ac@600 | ac@1200 | ac@3600 |")
    print("|-----|---------|----------------|----------|---------------|----------|"
          "--------|---------|---------|")
    for s in SYMBOLS:
        o = out[s]
        if "mad_sigma_bps" not in o:
            print(f"| {s} | {o.get('n_clean')} | - | - | - | - | - | - | - |")
            continue
        ac = o["autocorr"]
        print(f"| {s} | {o['n_clean']} | {o['mad_sigma_bps']} | {o['excess_kurtosis']} | "
              f"{o['hill_alpha_top5pct']} | {o['sign_balance_mean_pos']} | "
              f"{ac.get('600')} | {ac.get('1200')} | {ac.get('3600')} |")
    print(f"\nWrote {p.join(ed, 'a6_target_dist.json')}")


if __name__ == "__main__":
    main()

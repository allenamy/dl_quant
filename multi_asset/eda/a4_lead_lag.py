"""A4 — BTC -> alt lead-lag.

Sample ~28 days spread across 2023-2025. On the synchronous 1s grid, per alt:
  (a) contemporaneous: corr and beta of alt_y600 vs BTC_y600 (clean stride>=600).
  (b) lagged: corr( BTC trailing-return over k , alt forward y600 ) for
      k in {30,60,120,300,600}s. trailing-return at t = log(mid_btc[t]) - log(mid_btc[t-k])
      (causal, uses only past). Evaluated on the SAME clean non-overlap grid.
  (c) residual test: does lagged BTC trailing-return predict the alt residual
      r = alt_y600 - beta_contemp * BTC_y600 ? Report corr(BTC_trail_k, residual).

beta_contemp is estimated per-day pooled (contemporaneous OLS slope alt_y600 ~ BTC_y600)
on the clean grid, then applied. All correlations pooled across days on the clean grid.
n reported; block-bootstrap (day-block) CI on the headline contemporaneous corr and the
strongest lagged residual corr.

Read-only. Strict causality on trailing features.
"""
from __future__ import annotations

import json
import os.path as p

import numpy as np

from _eda_common import (SYMBOLS, BTC, HORIZON, list_all_days, sample_days_spread,
                         col, y600_full, clean_mask, day_exists, ensure_export_dir)

LAGS = [30, 60, 120, 300, 600]
ALTS = [s for s in SYMBOLS if s != BTC]


def trailing_return(mid: np.ndarray, k: int) -> np.ndarray:
    """Causal trailing log-return over k bars: r[t]=log(mid[t])-log(mid[t-k]); first k NaN."""
    r = np.full(mid.shape, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        lm = np.log(mid)
    r[k:] = lm[k:] - lm[:-k]
    return r


def safe_corr(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 30:
        return np.nan, int(m.sum())
    aa, bb = a[m], b[m]
    if np.std(aa) == 0 or np.std(bb) == 0:
        return np.nan, int(m.sum())
    return float(np.corrcoef(aa, bb)[0, 1]), int(m.sum())


def main():
    all_days = list_all_days()
    days = sample_days_spread(all_days, n=28, start=20230101, end=20251130)
    days = [d for d in days if day_exists(d)]
    print("# A4 — BTC -> alt lead-lag")
    print(f"Sampling: {len(days)} days spread 2023-01..2025-11: {days[0]}..{days[-1]}.\n")

    # Per-alt pooled arrays on the clean grid:
    # collect btc_y600, alt_y600, and btc trailing returns at the clean indices.
    pooled = {a: {"btc_y": [], "alt_y": [], **{f"trail_{k}": [] for k in LAGS},
                  "day_id": []} for a in ALTS}

    for dday, d in enumerate(days):
        try:
            from multi_asset.data.bar_loader import load_day_panel
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            print(f"  [warn] day {d} load failed: {e}")
            continue
        T = dp.ts.shape[0]
        btc_mid = col(dp, BTC, "mid")
        btc_y = y600_full(btc_mid, HORIZON)
        btc_trail = {k: trailing_return(btc_mid, k) for k in LAGS}
        cm = clean_mask(T, HORIZON, stride=HORIZON)
        cidx = np.where(cm)[0]

        for a in ALTS:
            alt_mid = col(dp, a, "mid")
            alt_y = y600_full(alt_mid, HORIZON)
            pooled[a]["btc_y"].append(btc_y[cidx])
            pooled[a]["alt_y"].append(alt_y[cidx])
            for k in LAGS:
                pooled[a][f"trail_{k}"].append(btc_trail[k][cidx])
            pooled[a]["day_id"].append(np.full(cidx.shape, dday))

    out = {}
    for a in ALTS:
        btc_y = np.concatenate(pooled[a]["btc_y"])
        alt_y = np.concatenate(pooled[a]["alt_y"])
        day_id = np.concatenate(pooled[a]["day_id"])
        trails = {k: np.concatenate(pooled[a][f"trail_{k}"]) for k in LAGS}

        # contemporaneous
        ccorr, n = safe_corr(alt_y, btc_y)
        m = np.isfinite(alt_y) & np.isfinite(btc_y)
        if m.sum() >= 30 and np.std(btc_y[m]) > 0:
            beta = float(np.polyfit(btc_y[m], alt_y[m], 1)[0])
        else:
            beta = np.nan

        # residual
        resid = alt_y - beta * btc_y

        lag_corr = {}
        resid_corr = {}
        for k in LAGS:
            lc, _ = safe_corr(trails[k], alt_y)
            rc, _ = safe_corr(trails[k], resid)
            lag_corr[k] = lc
            resid_corr[k] = rc

        # block bootstrap (day-block) on contemporaneous corr and best |resid_corr|
        uniq_days = np.unique(day_id)
        best_lag = max(LAGS, key=lambda k: abs(resid_corr[k]) if np.isfinite(resid_corr[k]) else 0)
        rng = np.random.default_rng(7)
        boot_c, boot_r = [], []
        for _ in range(500):
            samp = rng.choice(uniq_days, size=uniq_days.size, replace=True)
            sel = np.concatenate([np.where(day_id == dd)[0] for dd in samp])
            bc, _ = safe_corr(alt_y[sel], btc_y[sel])
            br, _ = safe_corr(trails[best_lag][sel], resid[sel])
            if np.isfinite(bc):
                boot_c.append(bc)
            if np.isfinite(br):
                boot_r.append(br)
        ci_c = [round(float(np.percentile(boot_c, 2.5)), 4),
                round(float(np.percentile(boot_c, 97.5)), 4)] if boot_c else None
        ci_r = [round(float(np.percentile(boot_r, 2.5)), 4),
                round(float(np.percentile(boot_r, 97.5)), 4)] if boot_r else None

        out[a] = {
            "n_clean": int(n),
            "contemp_corr": round(ccorr, 4) if np.isfinite(ccorr) else None,
            "contemp_beta": round(beta, 4) if np.isfinite(beta) else None,
            "contemp_corr_ci95": ci_c,
            "lag_corr": {str(k): (round(v, 4) if np.isfinite(v) else None) for k, v in lag_corr.items()},
            "resid_corr": {str(k): (round(v, 4) if np.isfinite(v) else None) for k, v in resid_corr.items()},
            "best_resid_lag": best_lag,
            "best_resid_corr": round(resid_corr[best_lag], 4) if np.isfinite(resid_corr[best_lag]) else None,
            "best_resid_corr_ci95": ci_r,
        }

    result = {
        "analysis": "A4_lead_lag",
        "sampling": f"{len(days)} days spread 2023-2025: {days[0]}..{days[-1]}",
        "clean_grid": "non-overlap stride>=600 (label-disjoint)",
        "lags_s": LAGS,
        "btc_trailing_causal": "r_btc[t]=log(mid[t])-log(mid[t-k]) (past-only)",
        "residual_def": "alt_y600 - beta_contemp * btc_y600",
        "per_alt": out,
    }
    ed = ensure_export_dir()
    with open(p.join(ed, "a4_lead_lag.json"), "w") as f:
        json.dump(result, f, indent=2)

    # markdown
    print("| alt | n | contemp_corr | contemp_beta | corr_ci95 | lag30 | lag60 | lag120 | "
          "lag300 | lag600 | best_resid_lag | best_resid_corr | resid_ci95 |")
    print("|-----|---|--------------|--------------|-----------|-------|-------|--------|"
          "--------|--------|----------------|-----------------|------------|")
    for a in ALTS:
        o = out[a]
        lc = o["resid_corr"]
        print(f"| {a} | {o['n_clean']} | {o['contemp_corr']} | {o['contemp_beta']} | "
              f"{o['contemp_corr_ci95']} | {lc['30']} | {lc['60']} | {lc['120']} | "
              f"{lc['300']} | {lc['600']} | {o['best_resid_lag']} | "
              f"{o['best_resid_corr']} | {o['best_resid_corr_ci95']} |")
    print("\n(lag columns above show RESIDUAL corr = lagged-BTC vs alt residual; "
          "raw lag_corr is in JSON)")
    print(f"\nWrote {p.join(ed, 'a4_lead_lag.json')}")


if __name__ == "__main__":
    main()

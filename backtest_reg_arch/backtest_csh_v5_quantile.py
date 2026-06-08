"""CSH v5 — Quantile-aware variants.

Tests 4 ways to incorporate q10/q90 beyond using q50_live alone.

V0 BASELINE (v4 best): T_open=2.0, T_close=-2.0, max_hold=10, no quantile use
  → Sharpe +4.38, Ann +44.7% @ fee_rt=5.8

V1 NARROW BAND FILTER: only enter when band_width < threshold
  Intuition: narrow band = high confidence, more reliable.

V2 CONFIDENCE SCORE: q50 / band_width > min_ratio
  Intuition: signal-to-uncertainty ratio (Sharpe-per-trade proxy).

V3 SOFT Q10/Q90 AGREEMENT: q10 in top 30% of its distribution (per fold) for long
  Intuition: "model unusually confident in downside protection".

V4 BAYES EXPECTED VALUE: E[r·position] - fee > 0
  Intuition: probabilistic expected utility using Gaussian fit to q10/q50/q90.
  std_est = (q90 - q10) / 2.56  (10/90 quantile spread = 2.56σ)
  Trade only when |q50| > fee × (1 + risk_aversion × std_est/|q50|).

V5 ADAPTIVE T_open BY BAND WIDTH: high uncertainty → require higher q50
  T_open_eff = T_open_base + 0.5 × max(0, band_width - median_band)

All variants share v4 base structure: T_close=-2, T_flip=3, max_hold=10.
Tested at fee_rt=5.8 (realistic maker USDT) — the practical anchor.
"""
import numpy as np
import pandas as pd
import itertools
from pathlib import Path

CSV = Path("predictions_all_folds.csv")
SUBSAMPLE_K = 4
DECISIONS_PER_YEAR = 365 * 24 * 60 / 12


def run_strategy(df, *, T_open, T_close, T_flip, fee_per_leg, max_hold_bars,
                 # Quantile-aware knobs:
                 band_filter=None,          # max band_width (q90-q10) for entry. None=off.
                 conf_ratio_min=None,       # min q50/band_width. None=off.
                 q10_pct_min=None,          # min q10 percentile (for long). None=off.
                 q90_pct_max=None,          # max q90 percentile (for short). None=off.
                 bayes_lambda=None,         # risk aversion for Bayes EV. None=off.
                 adaptive_T=False):         # adapt T_open by band_width
    n = len(df)
    q10 = df["y_pred_q10_bps"].values
    q50 = df["y_pred_q50_bps_live"].values
    q90 = df["y_pred_q90_bps"].values
    y = df["y_true_bps"].values
    band = q90 - q10
    band_median = np.median(band)

    # Pre-compute fold-aware q10/q90 percentile ranks
    df_local = df.reset_index(drop=True)
    if "fold" in df_local.columns:
        q10_pct = np.zeros(n)
        q90_pct = np.zeros(n)
        for f in df_local["fold"].unique():
            mask = (df_local["fold"] == f).values
            q10_pct[mask] = pd.Series(q10[mask]).rank(pct=True).values
            q90_pct[mask] = pd.Series(q90[mask]).rank(pct=True).values
    else:
        q10_pct = pd.Series(q10).rank(pct=True).values
        q90_pct = pd.Series(q90).rank(pct=True).values

    state = 0; held_bars = 0
    pnl = np.zeros(n); slog = np.zeros(n, dtype=np.int8); flog = np.zeros(n); tlog = np.zeros(n, dtype=np.int8)

    for i in range(n):
        # Effective T_open (may adapt to band width)
        T_eff = T_open
        if adaptive_T and band[i] > band_median:
            T_eff = T_open + 0.5 * (band[i] - band_median) / band_median

        cl_q50 = q50[i] >= T_eff
        cs_q50 = q50[i] <= -T_eff

        # Layered filters
        cl = cl_q50
        cs = cs_q50
        if band_filter is not None:
            cl = cl and (band[i] <= band_filter)
            cs = cs and (band[i] <= band_filter)
        if conf_ratio_min is not None:
            cl = cl and (q50[i] / band[i] >= conf_ratio_min)
            cs = cs and (-q50[i] / band[i] >= conf_ratio_min)
        if q10_pct_min is not None:
            cl = cl and (q10_pct[i] >= q10_pct_min)   # q10 in top (1-q10_pct_min) for long
        if q90_pct_max is not None:
            cs = cs and (q90_pct[i] <= q90_pct_max)   # q90 in bottom q90_pct_max for short
        if bayes_lambda is not None:
            # E[r·position] - fee > λ × std_est
            std_est = max(band[i] / 2.56, 0.1)
            edge_long = q50[i] - 2*fee_per_leg
            edge_short = -q50[i] - 2*fee_per_leg
            cl = cl and (edge_long > bayes_lambda * std_est)
            cs = cs and (edge_short > bayes_lambda * std_est)

        wl = q50[i] > T_close
        ws = q50[i] < -T_close
        fl = q50[i] >= T_flip
        fs = q50[i] <= -T_flip

        ns = state
        if state == 0:
            if cl: ns = +1; flog[i] += fee_per_leg; tlog[i] += 1
            elif cs: ns = -1; flog[i] += fee_per_leg; tlog[i] += 1
        elif state == +1:
            if fs: ns = -1; flog[i] += 2*fee_per_leg; tlog[i] += 2
            elif (not wl) or held_bars >= max_hold_bars:
                ns = 0; flog[i] += fee_per_leg; tlog[i] += 1
        elif state == -1:
            if fl: ns = +1; flog[i] += 2*fee_per_leg; tlog[i] += 2
            elif (not ws) or held_bars >= max_hold_bars:
                ns = 0; flog[i] += fee_per_leg; tlog[i] += 1

        if ns != state and ns != 0: held_bars = 1
        elif ns == state and ns != 0: held_bars += 1
        else: held_bars = 0
        pnl[i] = ns * y[i] - flog[i]; slog[i] = ns
        state = ns
    return pnl, slog, flog, tlog


def metrics(pnl, slog, tlog):
    n = len(pnl); total = pnl.sum(); m, s = pnl.mean(), pnl.std()
    sh = m/s*np.sqrt(DECISIONS_PER_YEAR) if s > 0 else 0
    cum = np.cumsum(pnl); dd = (np.maximum.accumulate(cum)-cum).max() if n else 0
    yrs = n/DECISIONS_PER_YEAR
    ann = total/1e4/yrs*100 if yrs > 0 else 0
    nt = int(np.ceil(tlog.sum()/2))
    in_mkt = slog != 0
    wr = (pnl[in_mkt] > 0).mean() if in_mkt.sum() else 0
    return dict(total=total, ann=ann, sharpe=sh, dd=dd, n_trades=nt,
                tim=100*in_mkt.mean(), win=wr,
                pnl_per_trade=total/max(1,nt))


def per_fold_breakdown(df, pnl, slog):
    """Return Sharpe and total PnL per fold."""
    df_d = df.copy()
    df_d["pnl"] = pnl; df_d["state"] = slog
    out = {}
    for f in [0, 1, 2]:
        sub = df_d[df_d["fold"]==f]
        if len(sub) == 0: out[f] = (0, 0); continue
        ds = sub["pnl"].values; m, s = ds.mean(), ds.std()
        sh = m/s*np.sqrt(DECISIONS_PER_YEAR) if s>0 else 0
        out[f] = (ds.sum(), sh)
    return out


def main():
    df_raw = pd.read_csv(CSV)
    valid = df_raw[df_raw["mask"].astype(bool) & ~df_raw["warmup"].astype(bool)].copy()
    valid = valid.sort_values("timestamp_us").reset_index(drop=True)
    df = valid.iloc[::SUBSAMPLE_K].reset_index(drop=True)
    print(f"Decisions: {len(df)} | Period: {df['datetime_utc'].iloc[0][:10]}→{df['datetime_utc'].iloc[-1][:10]}")
    print(f"σ_y={df['y_true_bps'].std():.2f} σ_q50={df['y_pred_q50_bps_live'].std():.3f}")
    print(f"band_width (q90-q10): mean={(df['y_pred_q90_bps']-df['y_pred_q10_bps']).mean():.2f}  median={(df['y_pred_q90_bps']-df['y_pred_q10_bps']).median():.2f}  std={(df['y_pred_q90_bps']-df['y_pred_q10_bps']).std():.2f}")
    print()

    FEE_RT = 5.8  # realistic maker USDT
    base = dict(T_open=2.0, T_close=-2.0, T_flip=3.0, fee_per_leg=FEE_RT/2, max_hold_bars=10)

    print(f"All variants at fee_rt={FEE_RT} bps (realistic maker USDT, ~70/30 fill)")
    print()
    print("="*110)
    print(f"{'Variant':<55} {'Sharpe':>8} {'Ann.%':>8} {'Total':>9} {'DD':>8} {'Trades':>7} {'PnL/T':>7} {'Win%':>6} {'F0':>7} {'F1':>7} {'F2':>7}")
    print("="*110)

    variants = [
        ("V0 BASELINE (no quantile)", {}),
        # V1 narrow band filter
        ("V1a band<22 (tightest 25%)", dict(band_filter=22.0)),
        ("V1b band<26 (median)",      dict(band_filter=26.0)),
        ("V1c band<30 (75%-ile)",     dict(band_filter=30.0)),
        # V2 confidence ratio
        ("V2a q50/band > 0.05",        dict(conf_ratio_min=0.05)),
        ("V2b q50/band > 0.08",        dict(conf_ratio_min=0.08)),
        ("V2c q50/band > 0.12",        dict(conf_ratio_min=0.12)),
        # V3 quantile percentile agreement
        ("V3a q10≥P50/q90≤P50",        dict(q10_pct_min=0.50, q90_pct_max=0.50)),
        ("V3b q10≥P70/q90≤P30",        dict(q10_pct_min=0.70, q90_pct_max=0.30)),
        ("V3c q10≥P85/q90≤P15",        dict(q10_pct_min=0.85, q90_pct_max=0.15)),
        # V4 Bayes EV with risk aversion
        ("V4a Bayes λ=0",              dict(bayes_lambda=0.0)),
        ("V4b Bayes λ=0.5",            dict(bayes_lambda=0.5)),
        ("V4c Bayes λ=1.0",            dict(bayes_lambda=1.0)),
        # V5 adaptive T_open
        ("V5 adaptive T_open by band", dict(adaptive_T=True)),
        # V6 combinations of best variants
        ("V6a V1b + V3b",              dict(band_filter=26.0, q10_pct_min=0.70, q90_pct_max=0.30)),
        ("V6b V1a + V2b",              dict(band_filter=22.0, conf_ratio_min=0.08)),
        ("V6c V3b + V2b",              dict(q10_pct_min=0.70, q90_pct_max=0.30, conf_ratio_min=0.08)),
    ]

    rows = []
    for name, kwargs in variants:
        all_args = {**base, **kwargs}
        pnl, slog, flog, tlog = run_strategy(df, **all_args)
        m = metrics(pnl, slog, tlog)
        pf = per_fold_breakdown(df, pnl, slog)
        print(f"{name:<55} {m['sharpe']:>+8.3f} {m['ann']:>+8.2f} {m['total']:>+9.0f} {m['dd']:>+8.1f} "
              f"{m['n_trades']:>7d} {m['pnl_per_trade']:>+7.2f} {m['win']*100:>+6.1f} "
              f"{pf[0][0]:>+7.0f} {pf[1][0]:>+7.0f} {pf[2][0]:>+7.0f}")
        rows.append({"variant": name, **m, "f0_pnl": pf[0][0], "f1_pnl": pf[1][0], "f2_pnl": pf[2][0]})

    res = pd.DataFrame(rows)
    res.to_csv("backtest_quantile_variants.csv", index=False)
    print()
    print("="*110)
    print("Sorted by Sharpe:")
    print("="*110)
    print(res.sort_values("sharpe", ascending=False)[["variant", "sharpe", "ann", "dd", "n_trades", "pnl_per_trade", "win", "f0_pnl", "f1_pnl", "f2_pnl"]]
          .to_string(index=False, float_format=lambda x: f"{x:+.2f}"))

    # ============================================================
    # Diagnostic: is band_width predictive of accuracy?
    # ============================================================
    print()
    print("="*110)
    print("DIAGNOSTIC: does band width predict accuracy?")
    print("="*110)
    df_diag = df.copy()
    df_diag["band"] = df_diag["y_pred_q90_bps"] - df_diag["y_pred_q10_bps"]
    df_diag["q50"] = df_diag["y_pred_q50_bps_live"]
    df_diag["y"] = df_diag["y_true_bps"]
    df_diag["abs_q50"] = df_diag["q50"].abs()

    # Filter strong q50 signals (|q50| > 1) and split by band tertile
    strong = df_diag[df_diag["abs_q50"] > 1.0]
    if len(strong) > 100:
        tert = pd.qcut(strong["band"], 3, labels=["narrow", "medium", "wide"])
        for t in ["narrow", "medium", "wide"]:
            sub = strong[tert == t]
            sig_y = np.sign(sub["q50"]) * sub["y"]
            p = np.corrcoef(sub["q50"], sub["y"])[0, 1]
            da = (np.sign(sub["q50"]) == np.sign(sub["y"])).mean()
            print(f"  band tertile {t:>6} (n={len(sub):>4}):  "
                  f"E[sign(ŷ)·y]={sig_y.mean():+.3f} bps  Pearson={p:+.4f}  DA={da:.4f}")
    print()
    print("If narrow > wide: band width IS useful as filter.")
    print("If similar: model's q10/q90 don't separate noise-vs-signal samples well.")


if __name__ == "__main__":
    main()

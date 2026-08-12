"""0C — TAIL CO-RISK专项 (four-leg daily returns, book_assembly_4leg caliber). CPU-only.
(a) crisis-day corr convergence: stratify by BTC daily-return quantile (worst 5/10%), recompute pairwise corr + combined.
(b) combined worst-day / worst-week. (c) named windows LUNA 2022-05 / FTX 2022-11 / yen 2024-08-05 per-day 4-leg table.
(d) verdict: does equal-risk hold in the tail; crisis-overlay (BTC rvol gate)?  Writes exports/eda/tail_corisk_raw.json.
"""
import os
import sys, numpy as np, pandas as pd, json
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA + "/exports/eda")
import build_4leg as b4
TR = "multi_asset/exports/train/"; EDA = "multi_asset/exports/eda/"; WPF = "multi_asset/exports/wide_panel_full.npz"
ANN = np.sqrt(365.0)


def sh(s): s = np.asarray(s); return float(s.mean() / s.std() * ANN) if s.std() > 0 else np.nan


def btc_daily():
    z = np.load(WPF, allow_pickle=True); syms = list(z["symbols"]); ts = z["ts"].astype(np.int64)
    bi = syms.index("BTCUSDT"); C = z["CLOSE"][:, bi].astype(np.float64)
    lc = np.log(np.where(C > 0, C, np.nan)); r = np.full_like(lc, np.nan); r[1:] = lc[1:] - lc[:-1]
    dd = pd.to_datetime(ts, unit="ms", utc=True).floor("D")
    ser = pd.Series(r, index=dd)
    dret = ser.groupby(level=0).sum(min_count=1)
    # 24h realized vol (hourly abs-ret rolling std) -> daily
    rv = pd.Series(r, index=pd.to_datetime(ts, unit="ms", utc=True)).rolling(24).std()
    rvd = rv.resample("D").last()
    rvd.index = rvd.index.tz_convert("UTC")
    return dret, rvd


if __name__ == "__main__":
    funding = b4.leg_funding(); size = b4.leg_size()
    king = b4.leg_dl_or_s2(None, None, True, 5.0); s2 = b4.leg_dl_or_s2(None, TR + "wideA_s2_y24_5yr", False, 5.0)
    J = pd.concat([funding, king, size, s2], axis=1, join="inner").dropna(); J.columns = ["funding", "king", "size", "s2"]
    J.index = pd.to_datetime(J.index).tz_localize(None) if J.index.tz is None else pd.to_datetime(J.index).tz_convert("UTC").tz_localize(None)
    Jn = J / J.std()
    comb = 0.25 * (Jn["funding"] + Jn["king"] + Jn["size"] + Jn["s2"])          # equal-risk
    combW = 0.30 * Jn["funding"] + 0.30 * Jn["king"] + 0.30 * Jn["size"] + 0.10 * Jn["s2"]  # accepted book weights
    print(f"joint {J.index.min().date()}..{J.index.max().date()} n={len(J)}  equal-risk Sh {sh(comb):.2f}  bookW Sh {sh(combW):.2f}", flush=True)

    btc, rvd = btc_daily()
    btc.index = pd.to_datetime(btc.index).tz_convert("UTC").tz_localize(None)
    rvd.index = pd.to_datetime(rvd.index).tz_localize(None)
    df = pd.concat([Jn, comb.rename("comb"), combW.rename("combW"), btc.rename("btc"), rvd.rename("rvol")], axis=1, join="inner").dropna(subset=["funding", "king", "size", "s2", "comb", "btc"])
    print(f"aligned with BTC: n={len(df)}", flush=True)

    full_corr = df[["funding", "king", "size", "s2"]].corr().round(3)

    def strat(q):
        thr = df["btc"].quantile(q); sub = df[df["btc"] <= thr]
        cc = sub[["funding", "king", "size", "s2"]].corr().round(3)
        return dict(q=q, thr_btc_ret=round(float(thr), 4), n_days=int(len(sub)),
                    pairwise_corr=cc.to_dict(),
                    leg_mean_ret={c: round(float(sub[c].mean()), 4) for c in ["funding", "king", "size", "s2"]},
                    comb_mean=round(float(sub["comb"].mean()), 4), comb_neg_frac=round(float((sub["comb"] < 0).mean()), 3),
                    all4_neg_frac=round(float(((sub[["funding", "king", "size", "s2"]] < 0).all(1)).mean()), 3),
                    combW_mean=round(float(sub["combW"].mean()), 4))
    crisis = {f"worst_{int(q*100)}pct": strat(q) for q in (0.05, 0.10)}
    # benchmark: full-sample & best 10%
    full_stats = dict(comb_mean=round(float(df["comb"].mean()), 4), comb_neg_frac=round(float((df["comb"] < 0).mean()), 3),
                      all4_neg_frac=round(float(((df[["funding", "king", "size", "s2"]] < 0).all(1)).mean()), 3),
                      avg_pairwise_corr=round(float(full_corr.values[np.triu_indices(4, 1)].mean()), 3))

    # (b) worst day / worst week
    wd = comb.sort_values().head(5); wk = comb.rolling(7).sum().sort_values().head(5)
    wdW = combW.sort_values().head(5); wkW = combW.rolling(7).sum().sort_values().head(5)
    worst = dict(equal_risk=dict(worst_days={str(k.date()): round(float(v), 4) for k, v in wd.items()},
                                 worst_weeks_7d={str(k.date()): round(float(v), 4) for k, v in wk.items()}),
                 book_weights=dict(worst_days={str(k.date()): round(float(v), 4) for k, v in wdW.items()},
                                   worst_weeks_7d={str(k.date()): round(float(v), 4) for k, v in wkW.items()}))

    # (c) named stress windows
    def window(a, b):
        w = df.loc[a:b]
        return {str(idx.date()): dict(btc=round(float(r["btc"]), 4), funding=round(float(r["funding"]), 3),
                                      king=round(float(r["king"]), 3), size=round(float(r["size"]), 3),
                                      s2=round(float(r["s2"]), 3), comb=round(float(r["comb"]), 3), rvol=round(float(r["rvol"]), 4))
                for idx, r in w.iterrows()}
    named = dict(LUNA_2022_05=window("2022-05-07", "2022-05-16"), FTX_2022_11=window("2022-11-06", "2022-11-15"),
                 yen_2024_08=window("2024-08-01", "2024-08-08"))

    # (d) overlay feasibility: does high BTC rvol precede bad comb days? corr(rvol_{t-1}, comb_t) + tail-day rvol
    df["rvol_lag1"] = df["rvol"].shift(1)
    dd2 = df.dropna(subset=["rvol_lag1"])
    corr_rvol_comb = round(float(np.corrcoef(dd2["rvol_lag1"], dd2["comb"])[0, 1]), 3)
    hi = dd2[dd2["rvol_lag1"] >= dd2["rvol_lag1"].quantile(0.90)]
    lo = dd2[dd2["rvol_lag1"] < dd2["rvol_lag1"].quantile(0.90)]
    overlay = dict(corr_rvol_lag1_vs_comb=corr_rvol_comb,
                   comb_sh_high_rvol=round(sh(hi["comb"]), 2), comb_sh_low_rvol=round(sh(lo["comb"]), 2),
                   comb_mean_high_rvol=round(float(hi["comb"].mean()), 4), comb_mean_low_rvol=round(float(lo["comb"].mean()), 4),
                   worst_days_in_hi_rvol_frac=round(float(dd2.loc[comb.sort_values().head(int(len(dd2) * 0.05)).index.intersection(dd2.index), "rvol_lag1"].ge(dd2["rvol_lag1"].quantile(0.90)).mean()), 3))

    res = dict(title="Tail co-risk (4-leg, book_assembly_4leg caliber)", created="2026-07-15", auditor="0C",
               joint=[str(J.index.min().date()), str(J.index.max().date()), int(len(df))],
               full_sample=dict(pairwise_corr=full_corr.to_dict(), **full_stats),
               crisis_days=crisis, worst=worst, named_windows=named, overlay_feasibility=overlay,
               leg_sharpe={c: round(sh(J[c]), 2) for c in J.columns}, equal_risk_sharpe=round(sh(comb), 2), bookW_sharpe=round(sh(combW), 2))
    json.dump(res, open(EDA + "tail_corisk_raw.json", "w"), indent=2, default=str)
    print("\n=== full-sample avg pairwise corr", full_stats["avg_pairwise_corr"], "comb neg-frac", full_stats["comb_neg_frac"], "all4-neg", full_stats["all4_neg_frac"], flush=True)
    for k, v in crisis.items():
        acc = np.mean([v["pairwise_corr"][a][b] for a in ["funding", "king", "size", "s2"] for b in ["funding", "king", "size", "s2"] if a != b])
        print(f"{k}: n={v['n_days']} avg-pair-corr {acc:.3f} comb-mean {v['comb_mean']:+.4f} comb-neg {v['comb_neg_frac']} all4-neg {v['all4_neg_frac']}", flush=True)
    print("overlay: corr(rvol_lag1,comb)", corr_rvol_comb, "| comb-Sh hi-rvol", overlay["comb_sh_high_rvol"], "lo-rvol", overlay["comb_sh_low_rvol"], flush=True)
    print("SAVED " + EDA + "tail_corisk_raw.json", flush=True)

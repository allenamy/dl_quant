"""(3b) price consistency + (3c) funding transferability: Hyperliquid vs Binance.

(3b) Do HL and Binance 4h returns agree? If yes, a price/return-based signal transfers unchanged.
     Test: per-coin Pearson/Spearman of 4h log returns on our CL4 anchor grid, HL vs Binance.

(3c) Does the funding leg transfer? Our funding factor is "Binance crowding", and the engine
     consumes it through _rank_centered -- so ONLY THE CROSS-SECTIONAL ORDERING MATTERS, level and
     scale wash out. The decisive metric is therefore the per-anchor cross-sectional rank
     correlation between HL-funding and Binance-funding over the shared names, plus the resulting
     leg-position agreement.
     HL funding is HOURLY; Binance is 8h-settled. Both are put through the same 24h-equivalent EMA
     (Binance span=3 over 8h stamps, HL span=24 over 1h stamps) so the smoothing matches.

Out: exports/eda/hl_transfer.json
"""
import json, sys
import numpy as np
import pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.signal_chain import _rank_centered, _l1


def spear(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 8:
        return np.nan
    return float(np.corrcoef(rankdata(a[ok]), rankdata(b[ok]))[0, 1])


def pear(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 8:
        return np.nan
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def main():
    H = np.load(MA + "/exports/eda/hl_hist.npz", allow_pickle=True)
    src = PanelSource()
    W = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)
    CLOSE = W["CLOSE"].astype(np.float64)
    FE = W["FUND_EMA"].astype(np.float64)
    ts = src.ts
    syms = src.symbols
    T, N = CLOSE.shape
    tpos = {int(t): i for i, t in enumerate(ts)}

    def hl2b(n):
        return ("1000" + n[1:] + "USDT") if n.startswith("k") else (n + "USDT")

    # ---- HL hourly close aligned onto our grid ----
    HC = np.full((T, N), np.nan)
    for c, arr in zip(H["coins"], H["candles"]):
        s = hl2b(str(c))
        if s not in syms:
            continue
        j = syms.index(s)
        for row in arr:
            i = tpos.get(int(row[0]))
            if i is not None:
                HC[i, j] = row[4]                      # close
    cov = np.isfinite(HC).sum(0)
    print(f"[3b] HL close aligned: {int((cov > 0).sum())} coins, "
          f"median hours/coin {int(np.median(cov[cov > 0]))}", flush=True)

    # ---- HL funding -> 24h-equivalent EMA, causal ffill onto our grid ----
    HF = np.full((T, N), np.nan)
    for c, arr in zip(H["fcoins"], H["funding"]):
        s = hl2b(str(c))
        if s not in syms:
            continue
        j = syms.index(s)
        a = arr[np.argsort(arr[:, 0])]
        ema = pd.Series(a[:, 1]).ewm(span=24, adjust=False).mean().values   # 24h-equiv (hourly)
        idx = np.searchsorted(a[:, 0], ts, side="right") - 1
        ok = idx >= 0
        HF[ok, j] = ema[idx[ok]]
        HF[ts < a[0, 0], j] = np.nan
    hcov = np.isfinite(HF).sum(0)
    print(f"[3b/c] HL funding aligned: {int((hcov > 0).sum())} coins", flush=True)

    out = {"caveats": {
        "window": "HL candles reach back 210d (API 5000-row cap); funding pulled for the 60d "
                  "window ending at the panel's last timestamp",
        "3c_metric": "engine rank-centres funding, so cross-sectional ORDER is what must transfer",
        "sample": "short window -> IC-style numbers are indicative, correlations are well-powered"}}

    # ================= (3b) price consistency =================
    anchors = np.where(src.CL4.any(1) & np.isfinite(HC).any(1))[0]
    anchors = anchors[anchors >= 4]
    lb = np.log(np.where(CLOSE > 0, CLOSE, np.nan))
    lh = np.log(np.where(HC > 0, HC, np.nan))
    rb4 = np.full((T, N), np.nan); rh4 = np.full((T, N), np.nan)
    rb4[4:] = lb[4:] - lb[:-4]
    rh4[4:] = lh[4:] - lh[:-4]
    per = []
    for j in range(N):
        a, b = rh4[anchors, j], rb4[anchors, j]
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() >= 200:
            per.append({"sym": syms[j], "n": int(ok.sum()),
                        "pearson": round(pear(a, b), 5), "spearman": round(spear(a, b), 5),
                        "hl_vol_ratio": round(float(np.nanstd(a) / (np.nanstd(b) + 1e-12)), 3)})
    p = np.array([d["pearson"] for d in per])
    per_sorted = sorted(per, key=lambda d: d["pearson"])
    out["price_consistency_4h"] = {
        "n_coins": len(per), "n_anchors": int(len(anchors)),
        "pearson_median": round(float(np.median(p)), 5),
        "pearson_p05": round(float(np.percentile(p, 5)), 5),
        "pearson_min": round(float(p.min()), 5),
        "frac_above_0.99": round(float((p > 0.99).mean()), 3),
        "frac_above_0.95": round(float((p > 0.95).mean()), 3),
        "worst10": per_sorted[:10], "best3": per_sorted[-3:]}
    print(f"[3b] 4h return corr: median {np.median(p):.5f}, "
          f">0.99 in {100*(p>0.99).mean():.0f}% of coins, min {p.min():.4f}", flush=True)

    # ================= (3c) funding transferability =================
    fa = np.where(np.isfinite(HF).sum(1) >= 10)[0]
    fa = np.array([t for t in fa if src.CL4[t].any()])
    xs, xs_p, nsh = [], [], []
    pos_corr = []
    for t in fa:
        m = np.where(src.member[t] & np.isfinite(HF[t]) & np.isfinite(FE[t]))[0]
        if len(m) < 10:
            continue
        a, b = HF[t, m], FE[t, m]
        xs.append(spear(a, b)); xs_p.append(pear(a, b)); nsh.append(len(m))
        # leg positions the engine would actually hold, from each source
        pa = _l1(-_rank_centered(a)); pb = _l1(-_rank_centered(b))
        pos_corr.append(pear(pa, pb))
    xs = np.array([v for v in xs if np.isfinite(v)])
    pos_corr = np.array([v for v in pos_corr if np.isfinite(v)])
    # per-coin time-series
    tsc = []
    for j in range(N):
        a, b = HF[fa, j], FE[fa, j]
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() >= 200:
            tsc.append({"sym": syms[j], "spearman": round(spear(a, b), 4),
                        "hl_mean_8h_equiv_bps": round(float(np.nanmean(a) * 8 * 1e4), 3),
                        "bnc_mean_8h_bps": round(float(np.nanmean(b) * 1e4), 3)})
    tsc_sorted = sorted(tsc, key=lambda d: d["spearman"])
    out["funding_transfer"] = {
        "n_anchors": int(len(xs)), "median_names_per_anchor": int(np.median(nsh)) if nsh else 0,
        "xsec_spearman_mean": round(float(np.mean(xs)), 4),
        "xsec_spearman_median": round(float(np.median(xs)), 4),
        "xsec_spearman_p10": round(float(np.percentile(xs, 10)), 4),
        "xsec_spearman_p90": round(float(np.percentile(xs, 90)), 4),
        "frac_anchors_above_0.7": round(float((xs > 0.7).mean()), 3),
        "frac_anchors_above_0.5": round(float((xs > 0.5).mean()), 3),
        "frac_anchors_negative": round(float((xs < 0).mean()), 3),
        "leg_position_corr_mean": round(float(np.mean(pos_corr)), 4),
        "leg_position_corr_p10": round(float(np.percentile(pos_corr, 10)), 4),
        "per_coin_timeseries_spearman": {
            "median": round(float(np.median([d["spearman"] for d in tsc])), 4),
            "worst10": tsc_sorted[:10], "best3": tsc_sorted[-3:]}}
    print(f"[3c] xsec funding rank-corr: mean {np.mean(xs):.4f} median {np.median(xs):.4f} "
          f"| >0.7 in {100*(xs>0.7).mean():.0f}% of anchors | leg-position corr "
          f"{np.mean(pos_corr):.4f}", flush=True)

    json.dump(out, open(MA + "/exports/eda/hl_transfer.json", "w"), indent=1)
    print("-> hl_transfer.json")


if __name__ == "__main__":
    main()

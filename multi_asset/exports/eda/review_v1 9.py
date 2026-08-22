"""0C — INDEPENDENT REVIEW of engine v1 (funding z->rank + isotonic-in-P&L). My own reimplementation
of the rank_C5on canonical P&L (rank funding, L1 legs, 4h cadence netting, walk-forward isotonic fit
on PRIOR year, 99% cap, renorm-to-gross) + isotonic lookahead/oracle bound + IC invariance + mechanism
(daily vol) + rank-funding vs book_assembly-funding corr + tail-corisk on rank engine legs.
Writes exports/eda/engine_v1_review_raw.json.
"""
import os
import sys, json, numpy as np, pandas as pd
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/exports/eda")
from engine.panel_source import PanelSource
from scipy.stats import rankdata
from sklearn.isotonic import IsotonicRegression
import build_4leg as b4

COST = 1.9; CAD = {"king": 4, "s2": 24, "funding": 8, "size": 24}
W = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
SIGN = {"king": 1, "s2": 1, "funding": -1, "size": 1}
src = PanelSource(); N = src.N
months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if not (y == 2026 and m > 6)]
anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
yr = pd.to_datetime(src.ts[anchors], unit="ms", utc=True).year.to_numpy()
day = (src.ts[anchors] // 86400000).astype(np.int64)
years = sorted(set(int(y) for y in yr))


def _z(x):
    x = np.asarray(x, float); m = np.isfinite(x); o = np.zeros_like(x)
    if m.sum() >= 3 and x[m].std() > 1e-12: o[m] = (x[m] - x[m].mean()) / x[m].std()
    return o


def _rank(x):
    x = np.asarray(x, float); m = np.isfinite(x); o = np.zeros_like(x)
    if m.sum() >= 3:
        r = rankdata(x[m]); k = len(r); o[m] = 2.0 * (r - 1) / (k - 1) - 1.0 if k > 1 else 0.0
    return o


def _l1(x):
    g = np.abs(x).sum(); return x / g if g > 1e-9 else x


def leg_pos(t, funding_mode):
    m = src.tradeable(t)
    fb = _rank(src.CH[t, m, src.fund_idx].astype(float)) if funding_mode == "rank" else _z(src.CH[t, m, src.fund_idx].astype(float))
    return {"king": _l1(SIGN["king"] * _z(src.king[t, m])), "s2": _l1(SIGN["s2"] * _z(src.s2[t, m])),
            "funding": _l1(SIGN["funding"] * fb), "size": _l1(SIGN["size"] * _z(src.CH[t, m, src.size_idx].astype(float)))}, m


def dsh(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.mean(x) / (np.std(x) + 1e-12) * np.sqrt(365.0)) if len(x) > 2 else np.nan


def combined_series(funding_mode):
    """per-anchor: combined active vector, m, realized bps — for fitting isotonic + P&L."""
    out = {}
    held = {k: np.zeros(N) for k in W}
    for i, t in enumerate(anchors):
        ti = int(t); lp, m = leg_pos(ti, funding_mode)
        for k in W:
            if i == 0 or ti % CAD[k] == 0:
                nw = np.zeros(N); nw[m] = lp[k]; held[k] = nw
        combo = sum(W[k] * held[k] for k in W)
        out[ti] = (m, combo[m].copy())
    return out


def fit_iso(train_anchors, combo_by_t):
    S, Y = [], []
    for t in train_anchors:
        m, c = combo_by_t[int(t)]; r = src.Y4[int(t), m] * 1e4
        ok = np.isfinite(c) & np.isfinite(r)
        if ok.any(): S.append(c[ok]); Y.append(r[ok])
    if not S: return None
    S = np.concatenate(S); Y = np.concatenate(Y)
    if len(S) < 200: return None
    return IsotonicRegression(out_of_bounds="clip", increasing=True).fit(S, Y)


def run(funding_mode="rank", shaping="iso_wf", cap=99.0):
    """shaping: 'iso_wf' walk-forward | 'iso_oracle' same-year fit | 'cap_only' | 'none'."""
    combo_by_t = combined_series(funding_mode)
    calib = {}
    if shaping.startswith("iso"):
        for y in years:
            tr = anchors[yr == y] if shaping == "iso_oracle" else anchors[yr == (y - 1)]
            calib[y] = fit_iso(tr, combo_by_t)
    pnl = np.zeros(len(anchors)); turn = np.zeros(len(anchors)); prev = np.zeros(N); ics = np.full(len(anchors), np.nan)
    for i, t in enumerate(anchors):
        ti = int(t); m, combo = combo_by_t[ti]
        base = combo - combo.mean(); gref = np.abs(base).sum()
        iso = calib.get(int(yr[i])) if shaping.startswith("iso") else None
        mag = iso.transform(combo) if iso is not None else combo.astype(float)
        mag = np.nan_to_num(mag)
        if cap and mag.size >= 10:
            lo, hi = np.nanpercentile(mag, 100 - cap), np.nanpercentile(mag, cap); mag = np.clip(mag, lo, hi)
        shaped = mag - mag.mean(); gsh = np.abs(shaped).sum()
        if gsh > 1e-12 and gref > 1e-12: shaped = shaped * (gref / gsh)
        net = np.zeros(N); net[m] = shaped
        ret = src.Y4[ti]; ok = np.isfinite(ret[m])
        pnl[i] = float(np.nansum(shaped[ok] * ret[m][ok]))
        turn[i] = float(np.abs(net - prev).sum()); prev = net
        c = shaped[ok]; y_ = ret[m][ok]
        if ok.sum() >= 5 and c.std() > 1e-12: ics[i] = np.corrcoef(rankdata(c), rankdata(y_))[0, 1]
    cost = turn * COST * 1e-4
    dfp = pd.DataFrame({"day": day, "yr": yr, "net": pnl - cost, "gross": pnl})
    dl = dfp.groupby("day").agg(net=("net", "sum"), gross=("gross", "sum"), yr=("yr", "first")).reset_index()
    tab = {int(y): round(dsh(dl[dl.yr == y]["net"].values), 2) for y in years}
    return dict(per_year=tab, avg=round(float(np.mean(list(tab.values()))), 2),
                daily_gross_vol=float(dl["gross"].std()), mean_ic=round(float(np.nanmean(ics)), 4),
                daily=dl)


if __name__ == "__main__":
    print("=== independent recompute ===", flush=True)
    rk = run("rank", "iso_wf"); print("rank C5off iso-WF :", rk["per_year"], "avg", rk["avg"], "IC", rk["mean_ic"], flush=True)
    rk_cap = run("rank", "cap_only"); print("rank cap-only    :", rk_cap["per_year"], "avg", rk_cap["avg"], "IC", rk_cap["mean_ic"], flush=True)
    rk_none = run("rank", "none", cap=None); print("rank no-shape    :", rk_none["per_year"], "avg", rk_none["avg"], "IC", rk_none["mean_ic"], flush=True)
    rk_or = run("rank", "iso_oracle"); print("rank iso-ORACLE  :", rk_or["per_year"], "avg", rk_or["avg"], "(lookahead bound)", flush=True)
    zz = run("z", "iso_wf"); print("z    C5off iso-WF :", zz["per_year"], "avg", zz["avg"], flush=True)
    print(f"\nISOTONIC mechanism: daily gross vol no-shape {rk_none['daily_gross_vol']:.4f} -> cap {rk_cap['daily_gross_vol']:.4f} -> iso-WF {rk['daily_gross_vol']:.4f}", flush=True)
    print(f"  iso lift avg: cap-only {rk_cap['avg']} -> iso-WF {rk['avg']} = {rk['avg']-rk_cap['avg']:+.2f}; oracle {rk_or['avg']} (WF vs oracle gap {rk_or['avg']-rk['avg']:+.2f})", flush=True)
    print(f"  IC invariance: no-shape {rk_none['mean_ic']} vs iso-WF {rk['mean_ic']} (should be ~equal)", flush=True)

    # rank-funding leg (engine) vs book_assembly funding — daily return corr
    print("\n=== rank-funding (engine) vs book_assembly funding ===", flush=True)
    held_f = np.zeros(N); ser = {}
    for i, t in enumerate(anchors):
        ti = int(t); lp, m = leg_pos(ti, "rank")
        if i == 0 or ti % CAD["funding"] == 0:
            held_f = np.zeros(N); held_f[m] = lp["funding"]
        ret = src.Y4[ti]; ok = np.isfinite(ret[m])
        d = int(src.ts[ti] // 86400000)
        ser[d] = ser.get(d, 0.0) + float(np.nansum(held_f[m][ok] * ret[m][ok]))
    ef = pd.Series(ser).sort_index(); ef.index = pd.to_datetime(ef.index, unit="D")
    baf = b4.leg_funding()  # megacap raw z-weight daily
    baf.index = pd.to_datetime(baf.index).tz_localize(None)
    J = pd.concat([ef.rename("engine_rankfund"), baf.rename("book_megacap")], axis=1, join="inner").dropna()
    fcorr = round(float(J["engine_rankfund"].corr(J["book_megacap"])), 3)
    print(f"engine rank-funding vs book_assembly megacap-raw funding: daily corr {fcorr} (n={len(J)})", flush=True)

    # tail co-risk on rank engine legs
    print("\n=== tail co-risk (rank engine legs) ===", flush=True)
    legser = {k: {} for k in W}; held = {k: np.zeros(N) for k in W}
    for i, t in enumerate(anchors):
        ti = int(t); lp, m = leg_pos(ti, "rank"); ret = src.Y4[ti]; ok = np.isfinite(ret[m]); d = int(src.ts[ti] // 86400000)
        for k in W:
            if i == 0 or ti % CAD[k] == 0:
                held[k] = np.zeros(N); held[k][m] = lp[k]
            legser[k][d] = legser[k].get(d, 0.0) + float(np.nansum(held[k][m][ok] * ret[m][ok]))
    L = pd.DataFrame({k: pd.Series(legser[k]) for k in W}).dropna()
    Ln = L / L.std(); comb = Ln.mean(1)
    # BTC daily
    bi = src.symbols.index("BTCUSDT"); btcr = pd.Series(src.btc_r, index=pd.to_datetime(src.ts, unit="ms").floor("D"))
    btc = btcr.groupby(level=0).sum(min_count=1); btc.index = (btc.index.astype(np.int64) // 86400000 // 1)
    Lb = L.copy(); Lb.index = L.index
    df = pd.concat([Ln, comb.rename("comb")], axis=1); df["btc"] = pd.Series({d: btc.get(pd.Timestamp(d, unit="D").floor("D").value // 86400000 // 1, np.nan) for d in L.index})
    full_corr = round(float(Ln.corr().values[np.triu_indices(4, 1)].mean()), 3)
    dd = df.dropna(subset=["btc"])
    tail = {}
    for q in (0.05, 0.10):
        sub = dd[dd["btc"] <= dd["btc"].quantile(q)]
        cc = round(float(sub[list(W)].corr().values[np.triu_indices(4, 1)].mean()), 3)
        tail[f"worst{int(q*100)}"] = dict(n=int(len(sub)), avg_pair_corr=cc, comb_mean=round(float(sub["comb"].mean()), 4),
                                          comb_pos_frac=round(float((sub["comb"] > 0).mean()), 3))
    print(f"full-sample avg pair-corr {full_corr}; crisis:", tail, flush=True)

    out = dict(title="Engine v1 review (rank + isotonic)", created="2026-07-15", auditor="0C",
               recompute_rank_iso_wf=rk["per_year"], recompute_avg=rk["avg"],
               rank_cap_only_avg=rk_cap["avg"], rank_noshape_avg=rk_none["avg"],
               iso_lift=round(rk["avg"] - rk_cap["avg"], 2), iso_oracle_avg=rk_or["avg"],
               iso_wf_vs_oracle_gap=round(rk_or["avg"] - rk["avg"], 2),
               ic_invariance=dict(noshape=rk_none["mean_ic"], iso_wf=rk["mean_ic"]),
               daily_vol_noshape=round(rk_none["daily_gross_vol"], 4), daily_vol_caponly=round(rk_cap["daily_gross_vol"], 4),
               daily_vol_iso=round(rk["daily_gross_vol"], 4),
               engine_rankfund_vs_book_megacap_corr=fcorr, tail_corisk_rank=dict(full_avg_pair_corr=full_corr, crisis=tail))
    json.dump(out, open(MA + "/exports/eda/engine_v1_review_raw.json", "w"), indent=1, default=str)
    print("\nSAVED engine_v1_review_raw.json", flush=True)

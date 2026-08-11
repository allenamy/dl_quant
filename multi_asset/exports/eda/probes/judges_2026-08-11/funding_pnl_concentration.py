"""0C addendum — is the +5.2%/yr funding harvest broad-based or a small-coin / extreme-rate tail?

Decision-relevant for a personal account: if the carry lives in illiquid extreme-funding names it is
NOT capturable (those are exactly the names with the worst maker-fill economics and the tightest
capacity). Re-runs the canonical book loop and buckets each settlement cash-flow by (a) coin
liquidity tier (median hourly notional, same tiers as makerfill: calib >= $4M/h, mega+mid >= 33pct,
small), (b) |funding rate| decile, (c) coin. Merges into funding_pnl_backfill_raw.json.
"""
import sys, json, os.path as p
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
WIDE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/wide"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource

CAD = {"king": 4, "s2": 24, "funding": 8, "size": 24}
W = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
HOUR_MS = 3600000
CALIB_FLOOR = 4.0e6      # makerfill calibration liquidity floor ($/h)

src = PanelSource(); N = src.N; symbols = src.symbols
months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if not (y == 2026 and m > 6)]
anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
day = (src.ts[anchors] // 86400000).astype(np.int64)
T = len(src.ts); t0 = int(src.ts[0])

FR = np.full((T, N), np.nan)
for j, s in enumerate(symbols):
    f = p.join(WIDE, f"{s}_funding.csv")
    if not p.exists(f):
        continue
    d = pd.read_csv(f)
    tms = (d["fundingTime_ms"].values.astype(np.int64) // HOUR_MS) * HOUR_MS
    rate = pd.to_numeric(d["fundingRate"], errors="coerce").values.astype(np.float64)
    idx = (tms - t0) // HOUR_MS
    ok = (idx >= 0) & (idx < T) & np.isfinite(rate)
    FR[idx[ok], j] = rate[ok]

QV = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)["QVOL"].astype(np.float64)
notl = np.nanmedian(np.where(src.member, QV, np.nan), axis=0)
small_cut = np.nanpercentile(notl[np.isfinite(notl)], 33)
tier = np.where(notl >= CALIB_FLOOR, 0, np.where(notl >= small_cut, 1, 2))   # 0 calib,1 mid,2 small
TIERN = ["calib_ge4M/h", "mid", "small"]
print(f"tiers: calib {int((tier==0).sum())} / mid {int((tier==1).sum())} / small {int((tier==2).sum())} "
      f"(small_cut ${small_cut/1e6:.2f}M/h)", flush=True)


def _z(x):
    x = np.asarray(x, float); m = np.isfinite(x); o = np.zeros_like(x)
    if m.sum() >= 3 and x[m].std() > 1e-12:
        o[m] = (x[m] - x[m].mean()) / x[m].std()
    return o


def _rank(x):
    x = np.asarray(x, float); m = np.isfinite(x); o = np.zeros_like(x)
    if m.sum() >= 3:
        r = rankdata(x[m]); k = len(r); o[m] = 2.0 * (r - 1) / (k - 1) - 1.0 if k > 1 else 0.0
    return o


def _l1(x):
    g = np.abs(x).sum(); return x / g if g > 1e-9 else x


held = {k: np.zeros(N) for k in W}; prev_unit = np.zeros(N)
ev_pnl = []; ev_rate = []; ev_coin = []; ev_day = []
n = len(anchors); daily_f = np.zeros(n)
for i, t in enumerate(anchors):
    ti = int(t); m = src.tradeable(ti)
    lp = {"king": _l1(_z(src.king[ti, m])), "s2": _l1(_z(src.s2[ti, m])),
          "funding": _l1(-_rank(src.CH[ti, m, src.fund_idx].astype(float))),
          "size": _l1(_z(src.CH[ti, m, src.size_idx].astype(float)))}
    for k in W:
        if i == 0 or ti % CAD[k] == 0:
            nw = np.zeros(N); nw[m] = lp[k]; held[k] = nw
    combo = sum(W[k] * held[k] for k in W); base = combo - combo.mean()
    lo, hi = np.nanpercentile(base, 1), np.nanpercentile(base, 99)
    mag = np.clip(base, lo, hi); pos = mag - mag.mean(); g = np.abs(pos).sum()
    unit = pos / g if g > 1e-9 else pos
    fr = FR[ti]; okf = np.where(np.isfinite(fr) & (np.abs(prev_unit) > 1e-12))[0]
    if okf.size:
        c = -prev_unit[okf] * fr[okf]
        ev_pnl.append(c); ev_rate.append(fr[okf]); ev_coin.append(okf)
        ev_day.append(np.full(okf.size, day[i]))
        daily_f[i] = float(c.sum())
    prev_unit = unit

ev_pnl = np.concatenate(ev_pnl); ev_rate = np.concatenate(ev_rate)
ev_coin = np.concatenate(ev_coin); ev_day = np.concatenate(ev_day)
ndays = len(np.unique(day))
SC = 365.0 / ndays * len(np.unique(day)) / len(np.unique(day))   # ann factor = 365/ndays_total
ANN = 365.0 / ndays

print(f"settlement cash-flow events: {len(ev_pnl):,} over {ndays} days", flush=True)
tot = ev_pnl.sum() * ANN
print(f"total funding ann {tot*100:.2f}%/gross  (cross-check vs backfill 5.17%)", flush=True)

# ---- (a) by liquidity tier ----
by_tier = {}
for tv, name in enumerate(TIERN):
    m = tier[ev_coin] == tv
    by_tier[name] = dict(ann_pct=round(float(ev_pnl[m].sum() * ANN * 100), 3),
                         share_pct=round(float(ev_pnl[m].sum() / ev_pnl.sum() * 100), 1),
                         n_events=int(m.sum()))
# ---- (b) by |rate| decile ----
q = np.abs(ev_rate)
edges = np.percentile(q, np.arange(0, 101, 10))
by_dec = {}
for b in range(10):
    m = (q >= edges[b]) & (q <= edges[b + 1] if b == 9 else q < edges[b + 1])
    by_dec[f"d{b+1}"] = dict(rate_bps_lo=round(edges[b] * 1e4, 2), rate_bps_hi=round(edges[b + 1] * 1e4, 2),
                             ann_pct=round(float(ev_pnl[m].sum() * ANN * 100), 3),
                             share_pct=round(float(ev_pnl[m].sum() / ev_pnl.sum() * 100), 1))
# ---- (c) top coins ----
cs = np.bincount(ev_coin, weights=ev_pnl, minlength=N) * ANN
order = np.argsort(-np.abs(cs))[:12]
top = [dict(sym=symbols[j], ann_pct=round(float(cs[j] * 100), 3),
            share_pct=round(float(cs[j] / (ev_pnl.sum() * ANN) * 100), 1),
            tier=TIERN[int(tier[j])], notl_Mh=round(float(notl[j] / 1e6), 2) if np.isfinite(notl[j]) else None)
       for j in order]
# ---- (d) daily robustness ----
dfd = pd.DataFrame(dict(day=day, f=daily_f)).groupby("day")["f"].sum()
dr = dict(frac_days_positive=round(float((dfd > 0).mean()), 3),
          median_daily_bps=round(float(np.median(dfd) * 1e4), 3),
          mean_daily_bps=round(float(np.mean(dfd) * 1e4), 3),
          worst_day_bps=round(float(dfd.min() * 1e4), 2), best_day_bps=round(float(dfd.max() * 1e4), 2),
          ann_excl_top1pct_days=round(float(np.sort(dfd.values)[:-int(len(dfd) * 0.01)].mean() * 365 * 100), 3))

# ---- (e) counterfactual: funding harvest of the funding LEG alone, per tier ----
out = dict(by_liquidity_tier=by_tier, by_abs_rate_decile=by_dec, top_coins=top, daily_robustness=dr,
           total_ann_pct=round(float(tot * 100), 3), n_events=int(len(ev_pnl)),
           tier_def=f"calib >= $4M/h (makerfill calibration floor); mid >= ${small_cut/1e6:.2f}M/h (33pct); small below")
print(json.dumps(dict(by_tier=by_tier, top6=top[:6], daily=dr), indent=1), flush=True)

RAW = MA + "/exports/eda/funding_pnl_backfill_raw.json"
j = json.load(open(RAW)); j["concentration"] = out
json.dump(j, open(RAW, "w"), indent=1, default=str)
print("MERGED into funding_pnl_backfill_raw.json", flush=True)

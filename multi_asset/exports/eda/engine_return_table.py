"""0C — canonical (rank+cap) return-on-gross table. Per-anchor position normalized to UNIT L1 gross
($1 gross = $0.5 long + $0.5 short) so P&L reads directly as return-on-gross; aggregate to daily,
per-year (a) ann net return-on-gross (mean daily x365), (b) ann daily vol (std x sqrt365), (c) Sharpe
check, (d) $5-10M gross dollar P&L + 3-5x-leverage return-on-capital. STRUCTURAL caliber (1.9bps only).
Writes exports/eda/engine_return_table_raw.json.
"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
from engine.panel_source import PanelSource
from scipy.stats import rankdata

COST = 1.9; CAD = {"king": 4, "s2": 24, "funding": 8, "size": 24}
W = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}; SIGN = {"king": 1, "s2": 1, "funding": -1, "size": 1}
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


held = {k: np.zeros(N) for k in W}; prev_unit = np.zeros(N)
rog = np.zeros(len(anchors)); rog_gross = np.zeros(len(anchors))
for i, t in enumerate(anchors):
    ti = int(t); m = src.tradeable(ti)
    lp = {"king": _l1(_z(src.king[ti, m])), "s2": _l1(_z(src.s2[ti, m])),
          "funding": _l1(-_rank(src.CH[ti, m, src.fund_idx].astype(float))),
          "size": _l1(_z(src.CH[ti, m, src.size_idx].astype(float)))}
    for k in W:
        if i == 0 or ti % CAD[k] == 0:
            nw = np.zeros(N); nw[m] = lp[k]; held[k] = nw
    combo = sum(W[k] * held[k] for k in W); base = combo - combo.mean()
    # 99% pos cap
    mag = base.copy(); lo, hi = np.nanpercentile(mag, 1), np.nanpercentile(mag, 99); mag = np.clip(mag, lo, hi)
    pos = mag - mag.mean(); g = np.abs(pos).sum()
    unit = pos / g if g > 1e-9 else pos            # UNIT gross ($1 = 0.5L+0.5S)
    ret = src.Y4[ti]; ok = np.isfinite(ret)
    gross_ret = float(np.nansum(unit[ok] * ret[ok]))      # return on $1 gross this 4h slot
    turn_unit = float(np.abs(unit - prev_unit).sum()); prev_unit = unit
    cost = turn_unit * COST * 1e-4
    rog[i] = gross_ret - cost; rog_gross[i] = gross_ret

df = pd.DataFrame({"day": day, "yr": yr, "net": rog, "gross": rog_gross})
dl = df.groupby("day").agg(net=("net", "sum"), gross=("gross", "sum"), yr=("yr", "first")).reset_index()

table = {}
for y in years:
    d = dl[dl.yr == y]["net"].values
    ann_ret = float(np.mean(d) * 365); ann_vol = float(np.std(d) * np.sqrt(365)); sh = ann_ret / ann_vol if ann_vol > 0 else np.nan
    table[int(y)] = dict(ann_return_on_gross=round(ann_ret, 4), ann_daily_vol=round(ann_vol, 4),
                         sharpe_check=round(sh, 2), trading_days=int(len(d)),
                         mean_daily_ret=round(float(np.mean(d)), 5))
alld = dl["net"].values
overall = dict(ann_return_on_gross=round(float(np.mean(alld) * 365), 4), ann_daily_vol=round(float(np.std(alld) * np.sqrt(365)), 4),
               sharpe_check=round(float(np.mean(alld) / np.std(alld) * np.sqrt(365)), 2))

print("YEAR | ann-return-on-gross | ann-vol | Sharpe-check | days", flush=True)
for y in years:
    r = table[y]; print(f"{y} | {r['ann_return_on_gross']*100:6.1f}% | {r['ann_daily_vol']*100:5.1f}% | {r['sharpe_check']:5.2f} | {r['trading_days']}", flush=True)
print(f"ALL | {overall['ann_return_on_gross']*100:6.1f}% | {overall['ann_daily_vol']*100:5.1f}% | {overall['sharpe_check']:.2f}", flush=True)

# (d) conversions
roG = overall["ann_return_on_gross"]
usd = {f"${g}M_gross": {"ann_pnl_usd_M": round(g * roG, 2)} for g in (5, 10)}
roc = {f"{L}x_leverage": {"ann_return_on_capital_pct": round(L * roG * 100, 1)} for L in (3, 5)}
out = dict(title="Canonical (rank+cap) return-on-gross table", created="2026-07-15", auditor="0C",
           caliber="STRUCTURAL: unit L1 gross ($1=0.5L+0.5S), net of 1.9bps explicit cost ONLY, daily x365, NO maker-fill/adverse-selection/impact/capacity",
           per_year=table, overall=overall,
           dollar_pnl=usd, return_on_capital_by_leverage=roc,
           WARNING="STRUCTURAL-caliber upper bound; deployment maker-fill stack (markout -1/-3.2/-5.3bps, fill<1, queue, impact, capacity) materially haircuts these; not a deployable return")
json.dump(out, open("/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/engine_return_table_raw.json", "w"), indent=1, default=str)
print(f"\n(d) roG={roG*100:.1f}%/yr | $5M gross -> ${5*roG:.2f}M/yr, $10M -> ${10*roG:.2f}M/yr | 3x lev RoC {3*roG*100:.0f}%, 5x {5*roG*100:.0f}%", flush=True)
print("SAVED engine_return_table_raw.json", flush=True)

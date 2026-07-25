"""0C — FUNDING P&L BACKFILL onto the canonical (rank+cap) engine book.

> created 2026-07-25 | Session: 0C personal-deployability audit | 状态: final

WHY: every backtest label in this project is a PURE PRICE return (Y4 = 4h close-to-close logret).
The book trades USDT-perps, holds 4-6h, and the 4h rebalance grid (00/04/08/12/16/20 UTC) lands
EXACTLY on every funding settlement (8h coins 00/08/16; 4h coins all six). So funding cash-flows
have never been in the P&L. This backfills them from the RAW fundingRate archive
(data/wide/<SYM>_funding.csv, 140/140 panel coins, per-row funding_interval_h) x the engine's
own position series.

CALIBER: reproduces engine_return_table.py exactly (canonical rank+cap, unit-L1-gross positions,
1.9bps explicit cost, daily x365) and adds funding on the SAME positions, so the delta is
apples-to-apples against the shipped 144.2%/yr return-on-gross table.

SIGN: perp funding is paid by longs to shorts when rate>0. Position w (long=+) => P&L = -w * rate.

SETTLEMENT ALIGNMENT (the one real approximation, both sides reported):
  base   'prev' — the position IN FORCE at the settlement instant is the PREVIOUS anchor's book
                  (the anchor-t rebalance is worked over the following k=300-900s window).
  sens   'new'  — the anchor-t book pays instead (instantaneous rebalance at the settlement tick).
The truth is between; both are printed.

ATTRIBUTION: per-leg contribution_k = (w_k*held_k - mean)/g, which sums to the un-capped book;
the 99pct cap residual is reported as its own line so the parts add to the total exactly.

Writes exports/eda/funding_pnl_backfill_raw.json.
"""
import sys, json, os.path as p
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
WIDE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/wide"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource

COST = 1.9
CAD = {"king": 4, "s2": 24, "funding": 8, "size": 24}
W = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
HOUR_MS = 3600000

src = PanelSource()
N = src.N
symbols = src.symbols
months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if not (y == 2026 and m > 6)]
anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
yr = pd.to_datetime(src.ts[anchors], unit="ms", utc=True).year.to_numpy()
day = (src.ts[anchors] // 86400000).astype(np.int64)
years = sorted(set(int(y) for y in yr))
T = len(src.ts)
t0 = int(src.ts[0])

# ---------- raw funding-rate event panel on the hourly grid ----------
FR = np.full((T, N), np.nan)
cov_rows = []
for j, s in enumerate(symbols):
    f = p.join(WIDE, f"{s}_funding.csv")
    if not p.exists(f):
        cov_rows.append({"sym": s, "n": 0}); continue
    d = pd.read_csv(f)
    tms = (d["fundingTime_ms"].values.astype(np.int64) // HOUR_MS) * HOUR_MS
    rate = pd.to_numeric(d["fundingRate"], errors="coerce").values.astype(np.float64)
    idx = (tms - t0) // HOUR_MS
    ok = (idx >= 0) & (idx < T) & np.isfinite(rate)
    FR[idx[ok], j] = rate[ok]
    cov_rows.append({"sym": s, "n": int(ok.sum()), "ih": float(np.median(d["funding_interval_h"].values)),
                     "d0": str(pd.to_datetime(tms.min(), unit="ms").date()),
                     "d1": str(pd.to_datetime(tms.max(), unit="ms").date())})
print(f"[funding panel] events={int(np.isfinite(FR).sum())} coins={sum(1 for c in cov_rows if c['n']>0)}/{N}", flush=True)


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


LEGS = list(W)
held = {k: np.zeros(N) for k in W}
prev_unit = np.zeros(N); prev_contrib = {k: np.zeros(N) for k in W}; prev_resid = np.zeros(N)
n = len(anchors)
price_net = np.zeros(n); price_gross = np.zeros(n); turn_s = np.zeros(n)
f_prev = np.zeros(n); f_new = np.zeros(n)
f_leg = {k: np.zeros(n) for k in W}; f_resid = np.zeros(n)
touched = np.zeros(n)          # |gross| of the book that had a settlement this anchor
nsett = np.zeros(n)

for i, t in enumerate(anchors):
    ti = int(t); m = src.tradeable(ti)
    lp = {"king": _l1(_z(src.king[ti, m])), "s2": _l1(_z(src.s2[ti, m])),
          "funding": _l1(-_rank(src.CH[ti, m, src.fund_idx].astype(float))),
          "size": _l1(_z(src.CH[ti, m, src.size_idx].astype(float)))}
    for k in W:
        if i == 0 or ti % CAD[k] == 0:
            nw = np.zeros(N); nw[m] = lp[k]; held[k] = nw
    combo = sum(W[k] * held[k] for k in W)
    base = combo - combo.mean()
    mag = base.copy()
    lo, hi = np.nanpercentile(mag, 1), np.nanpercentile(mag, 99)
    mag = np.clip(mag, lo, hi)
    pos = mag - mag.mean(); g = np.abs(pos).sum()
    unit = pos / g if g > 1e-9 else pos
    contrib = {}
    for k in W:
        c = W[k] * held[k]
        contrib[k] = (c - c.mean()) / g if g > 1e-9 else c * 0.0
    resid = unit - sum(contrib.values())

    # ---- price P&L + cost (identical to engine_return_table.py) ----
    ret = src.Y4[ti]; ok = np.isfinite(ret)
    gr = float(np.nansum(unit[ok] * ret[ok]))
    tu = float(np.abs(unit - prev_unit).sum())
    price_gross[i] = gr; price_net[i] = gr - tu * COST * 1e-4; turn_s[i] = tu

    # ---- funding cash-flow at this settlement instant ----
    fr = FR[ti]; okf = np.isfinite(fr)
    if okf.any():
        f_prev[i] = -float(np.sum(prev_unit[okf] * fr[okf]))
        f_new[i] = -float(np.sum(unit[okf] * fr[okf]))
        for k in W:
            f_leg[k][i] = -float(np.sum(prev_contrib[k][okf] * fr[okf]))
        f_resid[i] = -float(np.sum(prev_resid[okf] * fr[okf]))
        touched[i] = float(np.abs(prev_unit[okf]).sum()); nsett[i] = int(okf.sum())

    prev_unit = unit; prev_contrib = contrib; prev_resid = resid

# ---------- daily aggregation -> per-year ----------
cols = {"price_net": price_net, "price_gross": price_gross, "f_prev": f_prev, "f_new": f_new,
        "f_resid": f_resid, "touched": touched}
for k in W:
    cols["f_" + k] = f_leg[k]
df = pd.DataFrame(dict(day=day, yr=yr, **cols))
dl = df.groupby("day").agg(**{c: (c, "sum") for c in cols}, yr=("yr", "first")).reset_index()


def ann(x):
    return float(np.mean(x) * 365)


def sharpe(x):
    s = np.std(x)
    return float(np.mean(x) / s * np.sqrt(365)) if s > 0 else float("nan")


table = {}
for y in years:
    d = dl[dl.yr == y]
    pn = d["price_net"].values; fp = d["f_prev"].values; fn = d["f_new"].values
    tot = pn + fp
    table[int(y)] = dict(
        trading_days=int(len(d)),
        price_net_ann=round(ann(pn), 4), price_net_sharpe=round(sharpe(pn), 2),
        funding_ann=round(ann(fp), 4), funding_ann_newpos=round(ann(fn), 4),
        funding_vol_ann=round(float(np.std(fp) * np.sqrt(365)), 4),
        total_ann=round(ann(tot), 4), total_sharpe=round(sharpe(tot), 2),
        funding_pct_of_price=round(100 * ann(fp) / ann(pn), 1),
        legs={k: round(ann(d["f_" + k].values), 4) for k in W},
        cap_resid=round(ann(d["f_resid"].values), 5),
        gross_touched_per_day=round(float(np.mean(d["touched"].values)), 3))

pn = dl["price_net"].values; fp = dl["f_prev"].values; fn = dl["f_new"].values; tot = pn + fp
overall = dict(price_net_ann=round(ann(pn), 4), price_net_sharpe=round(sharpe(pn), 2),
               funding_ann=round(ann(fp), 4), funding_ann_newpos=round(ann(fn), 4),
               funding_vol_ann=round(float(np.std(fp) * np.sqrt(365)), 4),
               total_ann=round(ann(tot), 4), total_sharpe=round(sharpe(tot), 2),
               total_vol_ann=round(float(np.std(tot) * np.sqrt(365)), 4),
               price_vol_ann=round(float(np.std(pn) * np.sqrt(365)), 4),
               corr_price_funding=round(float(np.corrcoef(pn, fp)[0, 1]), 3),
               funding_pct_of_price=round(100 * ann(fp) / ann(pn), 1),
               legs={k: round(ann(dl["f_" + k].values), 4) for k in W},
               cap_resid=round(ann(dl["f_resid"].values), 5),
               gross_touched_per_day=round(float(np.mean(dl["touched"].values)), 3),
               mean_turnover_per_anchor=round(float(turn_s.mean()), 4),
               ann_turnover=round(float(turn_s.sum() / ((src.ts[anchors[-1]] - src.ts[anchors[0]]) / (86400000 * 365.25))), 1))

print("\nYEAR |  price-net |  funding  |   total   | price-Sh | total-Sh | days", flush=True)
for y in years:
    r = table[y]
    print(f"{y} | {r['price_net_ann']*100:9.1f}% | {r['funding_ann']*100:8.2f}% | {r['total_ann']*100:8.1f}% |"
          f" {r['price_net_sharpe']:8.2f} | {r['total_sharpe']:8.2f} | {r['trading_days']}", flush=True)
print(f"ALL  | {overall['price_net_ann']*100:9.1f}% | {overall['funding_ann']*100:8.2f}% | "
      f"{overall['total_ann']*100:8.1f}% | {overall['price_net_sharpe']:8.2f} | {overall['total_sharpe']:8.2f}", flush=True)
print("\nleg attribution (ann %/gross):", {k: round(v * 100, 3) for k, v in overall["legs"].items()},
      "cap_resid", round(overall["cap_resid"] * 100, 4), flush=True)
print(f"sensitivity newpos: {overall['funding_ann_newpos']*100:.2f}%/yr  (base prevpos {overall['funding_ann']*100:.2f}%)", flush=True)

out = dict(title="Funding P&L backfill onto canonical (rank+cap) engine book", created="2026-07-25",
           auditor="0C",
           caliber=("unit L1 gross ($1 = $0.5L + $0.5S); price P&L = engine_return_table.py canonical "
                    "(rank+cap, 1.9bps explicit cost only); funding = raw fundingRate archive x the SAME "
                    "position series; daily x365. STRUCTURAL caliber -- no maker-fill/adverse/impact."),
           settlement_alignment=("base = position in force at the settlement instant is the PREVIOUS "
                                 "anchor's book (rebalance worked over the following k=300-900s); "
                                 "sensitivity 'newpos' = the anchor-t book pays. All settlements land "
                                 "exactly on 4h anchors (8h coins 00/08/16, 4h coins all six), so this "
                                 "is a real choice, not an edge case."),
           per_year=table, overall=overall,
           funding_coverage=dict(coins_with_archive=int(sum(1 for c in cov_rows if c.get("n", 0) > 0)),
                                 n_panel_coins=int(N),
                                 n_interval_8h=int(sum(1 for c in cov_rows if c.get("ih") == 8)),
                                 n_interval_4h=int(sum(1 for c in cov_rows if c.get("ih") == 4)),
                                 total_settlement_events=int(np.isfinite(FR).sum()),
                                 note=("gross_touched_per_day = daily sum of |position| that had a "
                                       "settlement; ~3.0 would mean an all-8h book fully covered")),
           per_coin_coverage=cov_rows)
json.dump(out, open(MA + "/exports/eda/funding_pnl_backfill_raw.json", "w"), indent=1, default=str)
print("\nSAVED exports/eda/funding_pnl_backfill_raw.json", flush=True)

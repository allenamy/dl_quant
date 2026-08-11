"""0C — FEE x FILL-RATE sensitivity surface on the canonical (rank+cap) engine book.

> created 2026-07-25 | Session: 0C personal-deployability audit | 状态: final

QUESTION: the shipped table charges a FLAT 1.9 bps/side. That number came from the tick-corrected
maker-fill stack with TAKER_FEE=1.5 bps and NO exchange maker fee at all (apply_tickcorrected.py:
eff_if_fill = max(0, -adverse - half_spread) -- pure execution, zero fee). A Singapore personal
account at Binance VIP 0 pays maker 2.0 bps (1.8 with BNB) / taker 5.0 (4.5 with BNB). An on-chain
orderbook DEX may pay ~0-1 bps maker. So: what does the book earn across the real fee x fill surface?

COST MODEL (per unit notional traded, per coin j):
    c_j = phi * (maker_fee + max(0, ADV - hs_j*credit_j))  +  (1-phi) * (taker_fee + hs_j)
  - hs_j          per-coin half-spread, log10(hourly-notional) interpolation of the 14-coin
                  makerfill calibration (makerfill_calib_raw.json)
  - ADV           tick-measured adverse-selection markout, bps: 2.0 normal / 3.2 stress
                  (makerfill_deepdive: BTC tick markout mean -1.71 normal / -3.24 stress / -5.30 crash)
  - credit_j      spread-capture credit: 1.0 for calibrated coins (>= $4M/h), 0.5 below (extrapolated)
  - max(0, .)     conservative floor: never book market-making profit as negative execution cost.
                  The EXCHANGE FEE is added on top of that floor -- a fee is a real outflow.

TWO FILL CONVENTIONS (both reported -- they answer different questions):
  A 'taker_topup'  the pilot spec: work passive for k=300-900s, sweep the residual with a taker
                   order. Position is ALWAYS on target => alpha unchanged, cost is the blend above.
                   This is what the makerfill series actually simulated.
  B 'partial'      no top-up: w_t = w_{t-1} + phi*(w*_t - w_{t-1}). Only phi of each delta gets done,
                   the book LAGS the signal. Turnover falls with phi, but so does alpha -- and this
                   captures the signal-decay cost that naive "scale alpha and cost by phi" misses.
                   P&L and cost are divided by the realized L1 gross each anchor, so the number stays
                   'return on deployed gross' and is comparable to convention A.

Position series depends only on phi (not on fees), so 4 simulations cover the whole surface exactly.
Funding cash-flow (funding_pnl_backfill.py) is carried on the SAME simulated position, so every cell
is reported price-only AND price+funding.

Writes exports/eda/fee_fill_sensitivity_raw.json.
"""
import sys, json, os.path as p
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
EDA = MA + "/exports/eda/"
WIDE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/wide"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource

CAD = {"king": 4, "s2": 24, "funding": 8, "size": 24}
W = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
HOUR_MS = 3600000
CALIB_FLOOR = 4.0e6
MAKER_FEES = [0.0, 1.0, 1.8, 2.0, 5.0]
FILLS = [0.4, 0.51, 0.7, 1.0]
TAKERS = {"canonical_1.5": 1.5, "vip0_bnb_4.5": 4.5, "vip0_5.0": 5.0}
ADV = {"normal": 2.0, "stress": 3.2}

src = PanelSource(); N = src.N; symbols = src.symbols
months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if not (y == 2026 and m > 6)]
anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
yr = pd.to_datetime(src.ts[anchors], unit="ms", utc=True).year.to_numpy()
day = (src.ts[anchors] // 86400000).astype(np.int64)
years = sorted(set(int(y) for y in yr))
T = len(src.ts); t0 = int(src.ts[0])

# ---- raw funding events ----
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

# ---- per-coin half-spread law + spread-capture credit ----
cal = json.load(open(EDA + "makerfill_calib_raw.json"))["per_coin"]
cc = sorted(cal, key=lambda x: cal[x]["hourly_notl_usd"])
logN = np.array([np.log10(cal[c]["hourly_notl_usd"]) for c in cc])
half = np.array([cal[c]["half_spread_bps"] for c in cc])
QV = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)["QVOL"].astype(np.float64)
notl = np.nanmedian(np.where(src.member, QV, np.nan), axis=0)
notl = np.where(np.isfinite(notl) & (notl > 1e3), notl, 1e5)
HS = np.interp(np.log10(notl), logN, half)                  # (N,) bps
CREDIT = np.where(notl >= CALIB_FLOOR, 1.0, 0.5)
print(f"half-spread: BTC {HS[symbols.index('BTCUSDT')]:.3f} | median {np.median(HS):.3f} | "
      f"max {HS.max():.3f} bps; {int((notl<CALIB_FLOOR).sum())}/{N} below calib floor", flush=True)
MAKER_EXEC = {k: np.maximum(0.0, a - HS * CREDIT) for k, a in ADV.items()}   # (N,) per adverse scenario


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


def simulate(phi, partial):
    """Returns per-anchor arrays: gross price return-on-gross, funding, turnover, S_hs, S_me[adv].
    partial=False -> canonical book (position independent of phi). partial=True -> lagged book."""
    held = {k: np.zeros(N) for k in W}
    w = np.zeros(N); prev_w = np.zeros(N)
    n = len(anchors)
    R = np.zeros(n); F = np.zeros(n); TU = np.zeros(n); SHS = np.zeros(n)
    SME = {k: np.zeros(n) for k in ADV}
    UTIL = np.zeros(n)
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
        target = pos / g if g > 1e-9 else pos                    # unit-L1-gross target

        # funding is settled on the position IN FORCE at the settlement instant = previous book
        fr = FR[ti]; okf = np.isfinite(fr)
        gprev = np.abs(prev_w).sum()
        if okf.any() and gprev > 1e-12:
            F[i] = -float(np.sum(prev_w[okf] * fr[okf])) / gprev

        if partial:
            traded = phi * (target - w)                          # only phi of the delta gets done
            w = w + traded
        else:
            traded = target - w
            w = target
        gw = np.abs(w).sum(); UTIL[i] = gw
        if gw < 1e-12:
            prev_w = w; continue
        ad = np.abs(traded) / gw                                 # turnover per unit DEPLOYED gross
        TU[i] = float(ad.sum()); SHS[i] = float((ad * HS).sum())
        for k in ADV:
            SME[k][i] = float((ad * MAKER_EXEC[k]).sum())
        ret = src.Y4[ti]; ok = np.isfinite(ret)
        R[i] = float(np.nansum(w[ok] * ret[ok])) / gw
        prev_w = w
    return dict(R=R, F=F, TU=TU, SHS=SHS, SME=SME, UTIL=UTIL)


def stats(R, F, cost, include_funding):
    """daily-aggregate -> overall + per-year ann return-on-gross, vol, Sharpe."""
    net = R - cost + (F if include_funding else 0.0)
    d = pd.DataFrame(dict(day=day, yr=yr, x=net)).groupby("day").agg(x=("x", "sum"), yr=("yr", "first"))
    out = dict(ann_return=round(float(d["x"].mean() * 365), 4),
               ann_vol=round(float(d["x"].std() * np.sqrt(365)), 4),
               sharpe=round(float(d["x"].mean() / d["x"].std() * np.sqrt(365)), 2))
    out["per_year"] = {int(y): dict(ann_return=round(float(dy["x"].mean() * 365), 4),
                                    sharpe=round(float(dy["x"].mean() / dy["x"].std() * np.sqrt(365)), 2))
                       for y, dy in d.groupby("yr")}
    return out


SIMS = {}
SIMS[("topup", 1.0)] = simulate(1.0, partial=False)
for phi in FILLS:
    if phi < 1.0:
        SIMS[("partial", phi)] = simulate(phi, partial=True)
SIMS[("partial", 1.0)] = SIMS[("topup", 1.0)]
print("simulations done", flush=True)

base = SIMS[("topup", 1.0)]
YRS = (int(src.ts[anchors[-1]]) - int(src.ts[anchors[0]])) / (86400000 * 365.25)
ann_turn = float(base["TU"].sum() / YRS)
gross_only = stats(base["R"], base["F"], 0.0, False)
print(f"[anchor] gross(no-cost) {gross_only['ann_return']*100:.1f}%/yr Sh {gross_only['sharpe']:.2f} | "
      f"ann turnover {ann_turn:.0f} unit-gross/yr => 1 bps of cost = {ann_turn*1e-4*100:.2f}%/yr", flush=True)
chk = stats(base["R"], base["F"], base["TU"] * 1.9e-4, False)
print(f"[calibration check @flat 1.9bps] {chk['ann_return']*100:.1f}%/yr Sh {chk['sharpe']:.2f} "
      f"(shipped canonical: 144.2% / 12.24)", flush=True)
be_cost = gross_only["ann_return"] / (ann_turn * 1e-4)
print(f"[break-even] effective cost {be_cost:.2f} bps/side (price-only)", flush=True)


def cell(conv, phi, m, tk, adv):
    s = SIMS[(conv, phi)]
    c = phi * (m * s["TU"] + s["SME"][adv]) + (1 - phi) * (tk * s["TU"] + s["SHS"])
    eff = float(np.sum(c) / np.sum(s["TU"]))                     # turnover-weighted effective bps
    c = c * 1e-4
    r = dict(eff_cost_bps=round(eff, 3), turnover_ann=round(float(s["TU"].sum() / YRS), 1),
             gross_util=round(float(np.mean(s["UTIL"])), 3))
    r["price_only"] = stats(s["R"], s["F"], c, False)
    r["with_funding"] = stats(s["R"], s["F"], c, True)
    return r


grid = {}
for conv in ("topup", "partial"):
    for tname, tk in TAKERS.items():
        for adv in ADV:
            for m in MAKER_FEES:
                for phi in FILLS:
                    grid[f"{conv}|taker={tname}|adv={adv}|maker={m}|fill={phi}"] = cell(conv, phi, m, tk, adv)
print(f"grid cells: {len(grid)}", flush=True)


def show(conv, tname, adv, key):
    print(f"\n=== {conv} | taker {tname} | adverse {adv} | {key} :: ann return-on-gross % (net Sharpe) ===", flush=True)
    print("maker\\fill  " + "".join(f"{f:>16}" for f in FILLS), flush=True)
    for m in MAKER_FEES:
        row = f"{m:>5.1f} bps  "
        for phi in FILLS:
            c = grid[f"{conv}|taker={tname}|adv={adv}|maker={m}|fill={phi}"][key]
            row += f"{c['ann_return']*100:>9.1f} ({c['sharpe']:>4.1f})"
        print(row, flush=True)


for k in ("price_only", "with_funding"):
    show("topup", "vip0_5.0", "normal", k)
show("topup", "canonical_1.5", "normal", "price_only")
show("partial", "vip0_5.0", "normal", "with_funding")
show("topup", "vip0_5.0", "stress", "with_funding")

out = dict(title="Fee x fill-rate sensitivity surface -- canonical (rank+cap) engine book",
           created="2026-07-25", auditor="0C",
           caliber=("unit-L1-gross positions ($1 = $0.5L + $0.5S); return-on-gross, daily x365; "
                    "canonical rank+cap book; funding cash-flow from the raw fundingRate archive on "
                    "the SAME positions. Explicit-cost caliber only -- market impact, queue position "
                    "and capacity are NOT modelled (immaterial at personal-account size, material above "
                    "~$40-80M gross)."),
           cost_model=("c_j = phi*(maker_fee + max(0, ADV - hs_j*credit_j)) + (1-phi)*(taker_fee + hs_j); "
                       "hs_j = log10(hourly-notional) interp of the 14-coin makerfill calibration; "
                       "ADV = tick-measured adverse markout 2.0 normal / 3.2 stress; credit_j = 1.0 for "
                       ">= $4M/h coins, 0.5 below (extrapolated); max(0,.) = never book MM profit, the "
                       "exchange fee is then added on top."),
           conventions=dict(
               topup="passive work k=300-900s + residual TAKER sweep; position always on target; alpha unchanged (this is what the makerfill series simulated)",
               partial="no top-up: w_t = w_{t-1} + phi*(w*_t - w_{t-1}); book lags the signal; P&L and cost normalized by realized L1 gross"),
           axes=dict(maker_fee_bps=MAKER_FEES, fill_rate=FILLS, taker_fee_bps=TAKERS, adverse_bps=ADV),
           anchors=dict(gross_no_cost=gross_only, flat_1p9_check=chk, ann_turnover_unit_gross=round(ann_turn, 1),
                        pct_per_bps_of_cost=round(ann_turn * 1e-4 * 100, 3),
                        break_even_eff_cost_bps_price_only=round(be_cost, 2),
                        break_even_eff_cost_bps_with_funding=round(
                            (gross_only["ann_return"] + 0.0517) / (ann_turn * 1e-4), 2)),
           grid=grid)
json.dump(out, open(EDA + "fee_fill_sensitivity_raw.json", "w"), indent=1, default=str)
print("\nSAVED exports/eda/fee_fill_sensitivity_raw.json", flush=True)

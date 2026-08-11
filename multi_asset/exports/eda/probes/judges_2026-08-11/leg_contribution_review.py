"""0C — LEG CONTRIBUTION REVIEW: does the 4-leg book's weighting survive once funding carry is
priced in, and once the comparison is made at deployment fees / on the tails?

> created 2026-07-25 | Session: 0C leg-contribution review | 状态: final

TRIGGER: 0B's single-leg replay (price-only) showed king solo 15.45 > the 4-leg book 12.21, with
funding (-1.34) and size (0.53) individually near/below zero -- i.e. ~60% of book weight on legs
that look like dead weight. But 0B's replay carries NO funding cash-flow, and the funding leg is a
CARRY trade: 0C's funding_pnl_backfill measured +7.00%/yr of carry from that leg inside the book.
This re-runs every leg and every candidate book with the funding cash-flow ON, at two cost regimes,
and judges on tails + walk-forward weight selection rather than full-sample average Sharpe.

CALIBER: unit-L1-gross positions ($1 = $0.5L + $0.5S), canonical rank+cap chain, daily x365,
STRUCTURAL (no impact/queue/capacity). Reproduces engine_return_table.py for the 4-leg book.
Two cost regimes:
  canon = flat 1.9 bps/side (the shipped assumption == maker fee 0 + taker 1.5 + fill ~0.51)
  vip0  = per-coin  phi*(1.8 + max(0, 2.0 - hs_j*credit_j)) + (1-phi)*(4.5 + hs_j), phi=0.7
          (Binance VIP 0 + BNB, tick-normal adverse -- see fee_fill_sensitivity.md)

Writes exports/eda/leg_contribution_review_raw.json.
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
LEGS = ["king", "s2", "funding", "size"]
CUR = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
HOUR_MS = 3600000
CALIB_FLOOR = 4.0e6
VIP0 = dict(maker=1.8, taker=4.5, adv=2.0, phi=0.7)
BLOCK = 10          # day-block bootstrap block length
NBOOT = 2000
RNG = np.random.default_rng(20260725)

src = PanelSource(); N = src.N; symbols = src.symbols
months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if not (y == 2026 and m > 6)]
anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
dt = pd.to_datetime(src.ts[anchors], unit="ms", utc=True)
yr = dt.year.to_numpy(); day = (src.ts[anchors] // 86400000).astype(np.int64)
ym = np.array([f"{a}-{b:02d}" for a, b in zip(dt.year.to_numpy(), dt.month.to_numpy())])
years = sorted(set(int(y) for y in yr))
T = len(src.ts); t0 = int(src.ts[0]); n = len(anchors)

# ---------------- funding events ----------------
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

# ---------------- per-coin execution cost law ----------------
cal = json.load(open(EDA + "makerfill_calib_raw.json"))["per_coin"]
cc = sorted(cal, key=lambda x: cal[x]["hourly_notl_usd"])
logN = np.array([np.log10(cal[c]["hourly_notl_usd"]) for c in cc])
half = np.array([cal[c]["half_spread_bps"] for c in cc])
QV = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)["QVOL"].astype(np.float64)
notl = np.nanmedian(np.where(src.member, QV, np.nan), axis=0)
notl = np.where(np.isfinite(notl) & (notl > 1e3), notl, 1e5)
HS = np.interp(np.log10(notl), logN, half)
CREDIT = np.where(notl >= CALIB_FLOOR, 1.0, 0.5)
MEXEC = np.maximum(0.0, VIP0["adv"] - HS * CREDIT)
# per-unit-traded cost vector, bps, for each regime
COSTV = {"canon": np.full(N, 1.9),
         "vip0": VIP0["phi"] * (VIP0["maker"] + MEXEC) + (1 - VIP0["phi"]) * (VIP0["taker"] + HS)}
print(f"[cost] canon 1.900 flat | vip0 mean {COSTV['vip0'].mean():.3f} "
      f"BTC {COSTV['vip0'][symbols.index('BTCUSDT')]:.3f} bps", flush=True)


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


# ---------------- PASS 1: cadence-held per-leg L1 sub-portfolios ----------------
HELD = np.zeros((n, 4, N), np.float32)
RET = np.zeros((n, N)); RETOK = np.zeros((n, N), bool); FRA = np.full((n, N), np.nan)
held = {k: np.zeros(N) for k in LEGS}
for i, t in enumerate(anchors):
    ti = int(t); m = src.tradeable(ti)
    lp = {"king": _l1(_z(src.king[ti, m])), "s2": _l1(_z(src.s2[ti, m])),
          "funding": _l1(-_rank(src.CH[ti, m, src.fund_idx].astype(float))),
          "size": _l1(_z(src.CH[ti, m, src.size_idx].astype(float)))}
    for k in LEGS:
        if i == 0 or ti % CAD[k] == 0:
            nw = np.zeros(N); nw[m] = lp[k]; held[k] = nw
    for a, k in enumerate(LEGS):
        HELD[i, a] = held[k]
    r = src.Y4[ti]; ok = np.isfinite(r)
    RET[i, ok] = r[ok]; RETOK[i] = ok
    FRA[i] = FR[ti]
print(f"[pass1] HELD built {HELD.nbytes/1e6:.0f} MB", flush=True)
FROK = np.isfinite(FRA); FRZ = np.where(FROK, FRA, 0.0)


def run(w):
    """w: dict leg->weight. Returns per-anchor price return-on-gross, funding, and cost-basis sums."""
    wv = np.array([w.get(k, 0.0) for k in LEGS], np.float64)
    R = np.zeros(n); F = np.zeros(n)
    CST = {rg: np.zeros(n) for rg in COSTV}
    TU = np.zeros(n)
    prev = np.zeros(N)
    for i in range(n):
        combo = (HELD[i].astype(np.float64) * wv[:, None]).sum(0)
        base = combo - combo.mean()
        lo, hi = np.percentile(base, 1), np.percentile(base, 99)
        pos = np.clip(base, lo, hi); pos = pos - pos.mean()
        g = np.abs(pos).sum()
        unit = pos / g if g > 1e-9 else pos
        F[i] = -float(np.sum(prev * FRZ[i]))                 # prev book pays at the settlement instant
        ad = np.abs(unit - prev)
        TU[i] = ad.sum()
        for rg, cv in COSTV.items():
            CST[rg][i] = float((ad * cv).sum()) * 1e-4
        R[i] = float(np.sum(unit * RET[i]))
        prev = unit
    return dict(R=R, F=F, CST=CST, TU=TU)


YRS = (int(src.ts[anchors[-1]]) - int(src.ts[anchors[0]])) / (86400000 * 365.25)


def daily(x):
    return pd.DataFrame(dict(day=day, x=x)).groupby("day")["x"].sum()


def sh(v):
    v = np.asarray(v, float); s = v.std()
    return float(v.mean() / s * np.sqrt(365)) if s > 1e-12 else np.nan


def evaluate(res, regime, with_funding):
    net = res["R"] - res["CST"][regime] + (res["F"] if with_funding else 0.0)
    d = pd.DataFrame(dict(day=day, yr=yr, ym=ym, x=net))
    dl = d.groupby("day").agg(x=("x", "sum"), yr=("yr", "first"), ym=("ym", "first")).reset_index()
    ml = dl.groupby("ym").agg(x=("x", "sum"), yr=("yr", "first")).reset_index()
    eq = np.cumsum(dl["x"].values); dd = float((eq - np.maximum.accumulate(eq)).min())
    per_year = {int(y): dict(sharpe=round(sh(g["x"].values), 2),
                             ann_return=round(float(g["x"].mean() * 365), 4))
                for y, g in dl.groupby("yr")}
    return dict(sharpe=round(sh(dl["x"].values), 2),
                ann_return=round(float(dl["x"].mean() * 365), 4),
                ann_vol=round(float(dl["x"].std() * np.sqrt(365)), 4),
                per_year=per_year,
                worst_year_sharpe=round(min(v["sharpe"] for v in per_year.values()), 2),
                worst_year=int(min(per_year, key=lambda y: per_year[y]["sharpe"])),
                worst_month_ret=round(float(ml["x"].min()), 4),
                worst_month=str(ml.loc[ml["x"].idxmin(), "ym"]),
                n_neg_months=int((ml["x"] < 0).sum()), n_months=int(len(ml)),
                worst_day=round(float(dl["x"].min()), 4),
                max_drawdown=round(dd, 4),
                calmar=round(float(dl["x"].mean() * 365 / abs(dd)), 2) if dd < 0 else None,
                turnover_ann=round(float(res["TU"].sum() / YRS), 1),
                eff_cost_bps=round(float(res["CST"][regime].sum() / res["TU"].sum() * 1e4), 3),
                _daily=dl["x"].values)


# ---------------- BTC daily return for the crisis profile ----------------
btc_h = pd.DataFrame(dict(d=(src.ts // 86400000).astype(np.int64), r=src.btc_r))
btc_d = btc_h.groupby("d")["r"].sum()


def crisis(dvals, dday):
    b = btc_d.reindex(dday).values
    ok = np.isfinite(b)
    q5, q10 = np.nanpercentile(b[ok], 5), np.nanpercentile(b[ok], 10)
    out = dict(mean_all=round(float(np.mean(dvals)), 5),
               mean_btc_worst5pct=round(float(np.mean(dvals[ok][b[ok] <= q5])), 5),
               mean_btc_worst10pct=round(float(np.mean(dvals[ok][b[ok] <= q10])), 5),
               frac_neg_all=round(float((dvals < 0).mean()), 3),
               frac_neg_btc_worst5pct=round(float((dvals[ok][b[ok] <= q5] < 0).mean()), 3))
    for name, ds in [("FTX_2022-11-09", "2022-11-09"), ("LUNA_2022-05-12", "2022-05-12"),
                     ("yencarry_2024-08-05", "2024-08-05")]:
        k = int(pd.Timestamp(ds, tz="UTC").timestamp() // 86400)
        w = np.where(dday == k)[0]
        out[name] = round(float(dvals[w[0]]), 4) if len(w) else None
    return out


# ---------------- configs ----------------
def mix(king_w):
    """king at king_w, the other three kept at their current RELATIVE proportions."""
    rest = 1 - king_w; base = {"s2": 0.10, "funding": 0.30, "size": 0.30}; s = sum(base.values())
    d = {k: v / s * rest for k, v in base.items()}; d["king"] = king_w; return d


CONFIGS = {
    "solo_king": {"king": 1.0}, "solo_s2": {"s2": 1.0},
    "solo_funding": {"funding": 1.0}, "solo_size": {"size": 1.0},
    "book_current_30_10_30_30": dict(CUR),
    "king_s2_75_25": {"king": 0.75, "s2": 0.25},
    "king_funding_50_50": {"king": 0.5, "funding": 0.5},
    "king_size_50_50": {"king": 0.5, "size": 0.5},
    "king_fund_size_equal": {"king": 1 / 3, "funding": 1 / 3, "size": 1 / 3},
    "equal4": {k: 0.25 for k in LEGS},
    "king40": mix(0.40), "king50": mix(0.50), "king60": mix(0.60), "king70": mix(0.70),
    "king80": mix(0.80),
}
RES = {}
for name, w in CONFIGS.items():
    RES[name] = run(w)
    e = evaluate(RES[name], "canon", True)
    print(f"  {name:26s} canon+fund Sh {e['sharpe']:6.2f} ret {e['ann_return']*100:7.1f}% "
          f"turn {e['turnover_ann']:6.0f}", flush=True)

TABLE = {}
for name in CONFIGS:
    TABLE[name] = {"weights": {k: round(CONFIGS[name].get(k, 0.0), 4) for k in LEGS}}
    for rg in COSTV:
        for wf in (False, True):
            e = evaluate(RES[name], rg, wf)
            dvals = e.pop("_daily")
            if rg == "canon" and wf:
                e["crisis"] = crisis(dvals, np.array(sorted(set(day.tolist()))))
            TABLE[name][f"{rg}_{'with_funding' if wf else 'price_only'}"] = e

# ---------------- funding-carry delta per leg (the headline of Q1) ----------------
CARRY = {}
for name in CONFIGS:
    a = evaluate(RES[name], "canon", False); b = evaluate(RES[name], "canon", True)
    CARRY[name] = dict(price_only_sharpe=a["sharpe"], with_funding_sharpe=b["sharpe"],
                       d_sharpe=round(b["sharpe"] - a["sharpe"], 2),
                       funding_ann_pct=round((b["ann_return"] - a["ann_return"]) * 100, 3),
                       flips_sign=bool(a["sharpe"] < 0 <= b["sharpe"]))

# ---------------- paired day-block bootstrap: ΔSharpe vs the current book ----------------
def series(name, rg="canon", wf=True):
    r = RES[name]
    net = r["R"] - r["CST"][rg] + (r["F"] if wf else 0.0)
    return daily(net).values


base_s = series("book_current_30_10_30_30")
D = len(base_s); nb = int(np.ceil(D / BLOCK))
BOOT = {}
for name in CONFIGS:
    if name == "book_current_30_10_30_30":
        continue
    a = series(name); diffs = np.empty(NBOOT)
    for b in range(NBOOT):
        st = RNG.integers(0, D - BLOCK, nb)
        idx = (st[:, None] + np.arange(BLOCK)[None, :]).ravel()[:D]
        diffs[b] = sh(a[idx]) - sh(base_s[idx])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    BOOT[name] = dict(d_sharpe_point=round(sh(a) - sh(base_s), 2),
                      ci95=[round(float(lo), 2), round(float(hi), 2)],
                      p_better=round(float((diffs > 0).mean()), 3),
                      significant=bool(lo > 0 or hi < 0))
    print(f"  boot {name:26s} dSh {BOOT[name]['d_sharpe_point']:+6.2f} "
          f"CI[{lo:+.2f},{hi:+.2f}] p={BOOT[name]['p_better']:.3f}", flush=True)

# ---------------- walk-forward weight selection (the decisive test) ----------------
CANDS = [c for c in CONFIGS]
yearly = {c: {} for c in CANDS}
for c in CANDS:
    r = RES[c]; net = r["R"] - r["CST"]["canon"] + r["F"]
    dl = pd.DataFrame(dict(day=day, yr=yr, x=net)).groupby("day").agg(
        x=("x", "sum"), yr=("yr", "first")).reset_index()
    for y, gg in dl.groupby("yr"):
        yearly[c][int(y)] = gg["x"].values

WF = {"picks": {}, "per_year": {}}
chain, chain_cur, chain_king = [], [], []
for y in years:
    prior = [q for q in years if q < y]
    if not prior:
        pick = "book_current_30_10_30_30"
    else:
        pick = max(CANDS, key=lambda c: np.mean([sh(yearly[c][q]) for q in prior]))
    WF["picks"][y] = pick
    WF["per_year"][y] = dict(pick=pick, sharpe=round(sh(yearly[pick][y]), 2),
                             current=round(sh(yearly["book_current_30_10_30_30"][y]), 2),
                             king=round(sh(yearly["solo_king"][y]), 2))
    chain.append(sh(yearly[pick][y])); chain_cur.append(sh(yearly["book_current_30_10_30_30"][y]))
    chain_king.append(sh(yearly["solo_king"][y]))
WF["avg_walkforward_selected"] = round(float(np.mean(chain)), 2)
WF["avg_always_current"] = round(float(np.mean(chain_cur)), 2)
WF["avg_always_king"] = round(float(np.mean(chain_king)), 2)
print("\n[walk-forward weight selection]", json.dumps(WF["per_year"]), flush=True)
print(f"  wf-selected {WF['avg_walkforward_selected']} | always-current {WF['avg_always_current']} "
      f"| always-king {WF['avg_always_king']}", flush=True)

out = dict(title="Leg contribution review -- funding-carry-corrected, deployment-fee, tail-aware",
           created="2026-07-25", auditor="0C",
           caliber=("unit-L1-gross, canonical rank+cap chain, daily x365, STRUCTURAL (no impact/queue/"
                    "capacity). canon = flat 1.9bps (shipped); vip0 = per-coin Binance VIP0+BNB maker 1.8 / "
                    "taker 4.5 / fill 0.7 / tick-normal adverse. Funding cash-flow = raw fundingRate archive "
                    "on the same positions, prev-position settlement convention (the conservative side)."),
           configs=TABLE, funding_carry_delta=CARRY, bootstrap_vs_current=BOOT,
           walk_forward_weight_selection=WF,
           bootstrap_spec=dict(method="paired day-block bootstrap on daily P&L", block_days=BLOCK,
                               n_resamples=NBOOT, seed=20260725, caliber="canon + funding"))
json.dump(out, open(EDA + "leg_contribution_review_raw.json", "w"), indent=1, default=str)
print("\nSAVED exports/eda/leg_contribution_review_raw.json", flush=True)

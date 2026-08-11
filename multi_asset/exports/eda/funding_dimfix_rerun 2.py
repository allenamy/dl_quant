"""0C — re-run of the three funding-dependent conclusions on the DIMENSION-FIXED funding factor.

> created 2026-07-25 | Session: 0C re-run | 状态: final

Every configuration is run TWICE -- shipped funding channel vs normalised (8h-equivalent) channel --
so every number below is a paired before/after on identical positions machinery.

NOTE ON WHAT THE BUG DOES AND DOES NOT TOUCH: the funding CASH-FLOW is computed from the raw
per-settlement fundingRate x position, which is correct as-is (a 4h settlement really does pay the 4h
rate). The bug only affects the SIGNAL, hence the POSITIONS. So the funding P&L changes only through
the position change, never through the cash-flow arithmetic.

Sections:
 (1) solo-leg books: price drift vs carry decomposition, before/after
 (2) carry concentration by 8h-EQUIVALENT |rate| decile (the shipped decile analysis bucketed by the
     mis-dimensioned per-period rate, so it needed redoing too) + liquidity tier
 (3) king-weight sweep + bootstrap + walk-forward, before/after
 (4) king-decay surface on the corrected factor -> max-regret recheck
 (5) tails / crisis attribution, before/after

Writes exports/eda/funding_dimfix_rerun_raw.json.
"""
import os
import sys, json, os.path as p
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
EDA = MA + "/exports/eda/"
WIDE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/wide"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource

CAD = {"king": 4, "s2": 24, "funding": 8, "size": 24}
LEGS = ["king", "s2", "funding", "size"]
CUR = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
HOUR_MS = 3600000; CALIB_FLOOR = 4.0e6
VIP0 = dict(maker=1.8, taker=4.5, adv=2.0, phi=0.7)
KW = [0.0, 0.15, 0.30, 0.40, 0.50, 0.60, 0.70, 0.85, 1.0]
DELTAS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3]
BLOCK, NBOOT = 10, 2000
RNG = np.random.default_rng(20260725)

src = PanelSource(); N = src.N; symbols = src.symbols
FX = np.load(EDA + "funding_ema_normfix.npz", allow_pickle=True)
assert [str(s) for s in FX["symbols"]] == symbols and np.array_equal(FX["ts"].astype(np.int64), src.ts)
FUND = {"shipped": src.CH[:, :, src.fund_idx].astype(np.float64),
        "normfix": FX["FN"].astype(np.float64)}
IH = FX["IH"].astype(np.float64)

months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if not (y == 2026 and m > 6)]
anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
dt = pd.to_datetime(src.ts[anchors], unit="ms", utc=True)
yr = dt.year.to_numpy(); day = (src.ts[anchors] // 86400000).astype(np.int64)
ym = np.array([f"{a}-{b:02d}" for a, b in zip(dt.year.to_numpy(), dt.month.to_numpy())])
years = sorted(set(int(y) for y in yr)); T = len(src.ts); t0 = int(src.ts[0]); n = len(anchors)
YRS = (int(src.ts[anchors[-1]]) - int(src.ts[anchors[0]])) / (86400000 * 365.25)

# ---- raw funding cash-flow events (UNCHANGED by the bug) + 8h-equivalent rate for bucketing ----
FR = np.full((T, N), np.nan); FR8 = np.full((T, N), np.nan)
for j, s in enumerate(symbols):
    f = p.join(WIDE, f"{s}_funding.csv")
    if not p.exists(f):
        continue
    d = pd.read_csv(f)
    tms = (d["fundingTime_ms"].values.astype(np.int64) // HOUR_MS) * HOUR_MS
    rate = pd.to_numeric(d["fundingRate"], errors="coerce").values.astype(np.float64)
    ihr = pd.to_numeric(d["funding_interval_h"], errors="coerce").values.astype(np.float64)
    idx = (tms - t0) // HOUR_MS
    ok = (idx >= 0) & (idx < T) & np.isfinite(rate) & np.isfinite(ihr) & (ihr > 0)
    FR[idx[ok], j] = rate[ok]; FR8[idx[ok], j] = rate[ok] * (8.0 / ihr[ok])

cal = json.load(open(EDA + "makerfill_calib_raw.json"))["per_coin"]
cc = sorted(cal, key=lambda x: cal[x]["hourly_notl_usd"])
logN = np.array([np.log10(cal[c]["hourly_notl_usd"]) for c in cc])
half = np.array([cal[c]["half_spread_bps"] for c in cc])
QV = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)["QVOL"].astype(np.float64)
notl = np.nanmedian(np.where(src.member, QV, np.nan), axis=0)
notl = np.where(np.isfinite(notl) & (notl > 1e3), notl, 1e5)
HS = np.interp(np.log10(notl), logN, half)
CREDIT = np.where(notl >= CALIB_FLOOR, 1.0, 0.5)
COSTV = {"canon": np.full(N, 1.9),
         "vip0": VIP0["phi"] * (VIP0["maker"] + np.maximum(0.0, VIP0["adv"] - HS * CREDIT))
                 + (1 - VIP0["phi"]) * (VIP0["taker"] + HS)}
small_cut = np.nanpercentile(notl, 33)
TIER = np.where(notl >= CALIB_FLOOR, 0, np.where(notl >= small_cut, 1, 2))
TIERN = ["calib_ge4M/h", "mid", "small"]


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


# ---------------- PASS 1: cadence-held legs, per variant, per king-decay ----------------
RET = np.zeros((n, N))
FRZ = np.zeros((n, N)); FR8A = np.full((n, N), np.nan)
HELD = {}
rng = np.random.default_rng(20260725)
for var in FUND:
    for d in (DELTAS if var == "normfix" else [1.0]):
        HELD[(var, d)] = np.zeros((n, 4, N), np.float32)
held = {k: {kk: np.zeros(N) for kk in LEGS} for k in HELD}
for i, t in enumerate(anchors):
    ti = int(t); m = src.tradeable(ti)
    kz = _z(src.king[ti, m]); perm = rng.permutation(len(kz)); kzs = kz[perm]
    s2p = _l1(_z(src.s2[ti, m])); szp = _l1(_z(src.CH[ti, m, src.size_idx].astype(float)))
    for var in FUND:
        fdp = _l1(-_rank(FUND[var][ti, m]))
        for d in (DELTAS if var == "normfix" else [1.0]):
            key = (var, d)
            keff = _l1(_z(d * kz + np.sqrt(max(0.0, 1 - d * d)) * kzs)) if d < 1.0 else _l1(kz)
            lp = {"king": keff, "s2": s2p, "funding": fdp, "size": szp}
            for k in LEGS:
                if i == 0 or ti % CAD[k] == 0:
                    nw = np.zeros(N); nw[m] = lp[k]; held[key][k] = nw
            for a, k in enumerate(LEGS):
                HELD[key][i, a] = held[key][k]
    r = src.Y4[ti]; ok = np.isfinite(r); RET[i, ok] = r[ok]
    fr = FR[ti]; FRZ[i] = np.where(np.isfinite(fr), fr, 0.0); FR8A[i] = FR8[ti]
print(f"[pass1] {len(HELD)} held tensors built", flush=True)


def run(w, var="shipped", d=1.0):
    wv = np.array([w.get(k, 0.0) for k in LEGS], np.float64)
    H = HELD[(var, d)]
    R = np.zeros(n); F = np.zeros(n); TU = np.zeros(n)
    CST = {rg: np.zeros(n) for rg in COSTV}
    POS = np.zeros((n, N), np.float32)
    prev = np.zeros(N)
    for i in range(n):
        combo = (H[i].astype(np.float64) * wv[:, None]).sum(0)
        base = combo - combo.mean()
        lo, hi = np.percentile(base, 1), np.percentile(base, 99)
        pos = np.clip(base, lo, hi); pos = pos - pos.mean()
        g = np.abs(pos).sum()
        unit = pos / g if g > 1e-9 else pos
        F[i] = -float(np.sum(prev * FRZ[i]))
        ad = np.abs(unit - prev); TU[i] = ad.sum()
        for rg, cv in COSTV.items():
            CST[rg][i] = float((ad * cv).sum()) * 1e-4
        R[i] = float(np.sum(unit * RET[i]))
        POS[i] = prev            # position IN FORCE at this settlement instant
        prev = unit
    return dict(R=R, F=F, CST=CST, TU=TU, POS=POS)


def sh(v):
    v = np.asarray(v, float); s = v.std()
    return float(v.mean() / s * np.sqrt(365)) if s > 1e-12 else np.nan


def daily(x):
    return pd.DataFrame(dict(day=day, x=x)).groupby("day")["x"].sum()


def ev(res, rg="canon", wf=True, tails=False):
    net = res["R"] - res["CST"][rg] + (res["F"] if wf else 0.0)
    d = pd.DataFrame(dict(day=day, yr=yr, ym=ym, x=net))
    dl = d.groupby("day").agg(x=("x", "sum"), yr=("yr", "first"), ym=("ym", "first")).reset_index()
    py = {int(y): round(sh(g["x"].values), 2) for y, g in dl.groupby("yr")}
    o = dict(sharpe=round(sh(dl["x"].values), 2), per_year=py,
             worst_year_sharpe=round(min(py.values()), 2),
             ann_return=round(float(dl["x"].mean() * 365), 4),
             ann_vol=round(float(dl["x"].std() * np.sqrt(365)), 4),
             turnover_ann=round(float(res["TU"].sum() / YRS), 1))
    if tails:
        ml = dl.groupby("ym")["x"].sum()
        eq = np.cumsum(dl["x"].values); dd = float((eq - np.maximum.accumulate(eq)).min())
        o.update(worst_month_ret=round(float(ml.min()), 4), worst_month=str(ml.idxmin()),
                 n_neg_months=int((ml < 0).sum()), worst_day=round(float(dl["x"].min()), 4),
                 max_drawdown=round(dd, 4))
    return o


# ---------------- (1) solo legs: drift vs carry, before/after ----------------
SOLO = {}
for var in FUND:
    for leg in LEGS:
        r = run({leg: 1.0}, var)
        a = ev(r, "canon", False); b = ev(r, "canon", True, tails=True)
        SOLO[f"{var}|{leg}"] = dict(price_only_sharpe=a["sharpe"], price_only_ann=a["ann_return"],
                                    with_funding_sharpe=b["sharpe"], with_funding_ann=b["ann_return"],
                                    carry_ann=round(b["ann_return"] - a["ann_return"], 4),
                                    per_year_with_funding=b["per_year"],
                                    worst_year=b["worst_year_sharpe"], worst_day=b["worst_day"],
                                    max_drawdown=b["max_drawdown"], n_neg_months=b["n_neg_months"],
                                    turnover_ann=b["turnover_ann"])
        if leg == "funding":
            print(f"  [{var}] funding solo: price {a['sharpe']:+6.2f} ({a['ann_return']*100:+7.2f}%/yr) "
                  f"-> +carry {b['sharpe']:+6.2f} ({b['ann_return']*100:+7.2f}%/yr), carry "
                  f"{(b['ann_return']-a['ann_return'])*100:+6.2f}%/yr", flush=True)

# ---------------- (2) carry concentration on the CORRECTED leg, by 8h-EQUIV |rate| ----------------
CONC = {}
for var in FUND:
    r = run({"funding": 1.0}, var)
    P = r["POS"]
    okf = np.isfinite(FR8A) & (np.abs(P) > 1e-12)
    ev_pnl = -(P * np.where(np.isfinite(FRZ), FRZ, 0.0))[okf]     # real cash-flow (raw rate)
    ev_r8 = np.abs(FR8A[okf])                                      # bucket by 8h-equivalent |rate|
    ev_coin = np.tile(np.arange(N), (n, 1))[okf]
    ANN = 365.0 / len(np.unique(day))
    tot = ev_pnl.sum() * ANN
    qs = np.percentile(ev_r8, [50, 80, 90, 95])
    buckets = {}
    labels = ["<p50", "p50-80", "p80-90", "p90-95", ">p95"]
    edges = [-np.inf] + list(qs) + [np.inf]
    for a2 in range(5):
        mm = (ev_r8 >= edges[a2]) & (ev_r8 < edges[a2 + 1])
        buckets[labels[a2]] = dict(rate_bps_lo=round(float(edges[a2] * 1e4), 2) if a2 else None,
                                   ann_pct=round(float(ev_pnl[mm].sum() * ANN * 100), 3),
                                   share_pct=round(float(ev_pnl[mm].sum() / ev_pnl.sum() * 100), 1))
    tiers = {}
    for tv, nm in enumerate(TIERN):
        mm = TIER[ev_coin] == tv
        tiers[nm] = dict(ann_pct=round(float(ev_pnl[mm].sum() * ANN * 100), 3),
                         share_pct=round(float(ev_pnl[mm].sum() / ev_pnl.sum() * 100), 1))
    CONC[var] = dict(total_ann_pct=round(float(tot * 100), 3), by_abs_rate8h_bucket=buckets,
                     by_liquidity_tier=tiers)
    print(f"  [{var}] funding-leg carry {tot*100:+.2f}%/yr | top-5% |rate8h| share "
          f"{buckets['>p95']['share_pct']}% | tiers " +
          " ".join(f"{k}:{v['share_pct']}%" for k, v in tiers.items()), flush=True)

# ---------------- (3) king-weight sweep + bootstrap + walk-forward, before/after ----------------
def mix(kw):
    rest = 1 - kw; b = {"s2": 0.10, "funding": 0.30, "size": 0.30}; s = sum(b.values())
    d = {k: v / s * rest for k, v in b.items()}; d["king"] = kw; return d


SWEEP = {}; RESC = {}
for var in FUND:
    SWEEP[var] = {}
    for kw in KW:
        r = run(mix(kw), var); RESC[(var, kw)] = r
        SWEEP[var][str(kw)] = {rg: ev(r, rg, True, tails=(rg == "canon")) for rg in COSTV}
    best = max(KW, key=lambda k: SWEEP[var][str(k)]["canon"]["sharpe"])
    print(f"  [{var}] kw sweep canon: " + " ".join(f"{k}:{SWEEP[var][str(k)]['canon']['sharpe']:.2f}" for k in KW)
          + f"  argmax {best}", flush=True)

BOOT = {}
for var in FUND:
    base = daily(RESC[(var, 0.30)]["R"] - RESC[(var, 0.30)]["CST"]["canon"] + RESC[(var, 0.30)]["F"]).values
    D = len(base); nb = int(np.ceil(D / BLOCK))
    BOOT[var] = {}
    for kw in [0.40, 0.50, 0.60, 1.0]:
        a = daily(RESC[(var, kw)]["R"] - RESC[(var, kw)]["CST"]["canon"] + RESC[(var, kw)]["F"]).values
        diffs = np.empty(NBOOT)
        for b in range(NBOOT):
            st = RNG.integers(0, D - BLOCK, nb)
            idx = (st[:, None] + np.arange(BLOCK)[None, :]).ravel()[:D]
            diffs[b] = sh(a[idx]) - sh(base[idx])
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        BOOT[var][str(kw)] = dict(d_sharpe=round(sh(a) - sh(base), 2),
                                  ci95=[round(float(lo), 2), round(float(hi), 2)],
                                  significant=bool(lo > 0 or hi < 0))
    print(f"  [{var}] boot vs kw0.30: " + " ".join(
        f"{k}:{v['d_sharpe']:+.2f}{v['ci95']}" for k, v in BOOT[var].items()), flush=True)

WF = {}
for var in FUND:
    yearly = {}
    for kw in KW:
        r = RESC[(var, kw)]; net = r["R"] - r["CST"]["canon"] + r["F"]
        dl = pd.DataFrame(dict(day=day, yr=yr, x=net)).groupby("day").agg(
            x=("x", "sum"), yr=("yr", "first")).reset_index()
        yearly[kw] = {int(y): g["x"].values for y, g in dl.groupby("yr")}
    picks, chain, cur = {}, [], []
    for y in years:
        prior = [q for q in years if q < y]
        pick = 0.30 if not prior else max(KW, key=lambda k: np.mean([sh(yearly[k][q]) for q in prior]))
        picks[y] = pick; chain.append(sh(yearly[pick][y])); cur.append(sh(yearly[0.30][y]))
    WF[var] = dict(picks={str(k): v for k, v in picks.items()},
                   avg_walkforward=round(float(np.mean(chain)), 2),
                   avg_always_current=round(float(np.mean(cur)), 2))
    print(f"  [{var}] walk-forward picks {picks} -> {WF[var]['avg_walkforward']} "
          f"vs always-0.30 {WF[var]['avg_always_current']}", flush=True)

# ---------------- (4) king-decay surface on the CORRECTED factor ----------------
SURF = {}
print("\n[decay surface, normfix] canon Sharpe", flush=True)
print("delta\\kw " + "".join(f"{k:>7.2f}" for k in KW) + "   argmax", flush=True)
for d in DELTAS:
    row = {kw: ev(run(mix(kw), "normfix", d), "canon", True)["sharpe"] for kw in KW}
    best = max(row, key=lambda k: row[k])
    SURF[str(d)] = dict(by_kw={str(k): row[k] for k in row}, argmax_kw=best, argmax_sharpe=row[best])
    print(f"{d:5.1f}   " + "".join(f"{row[k]:7.2f}" for k in KW) + f"   {best:.2f}", flush=True)
REGRET = {}
for kw in KW:
    REGRET[str(kw)] = round(max(SURF[str(d)]["argmax_sharpe"] - SURF[str(d)]["by_kw"][str(kw)]
                                for d in DELTAS), 2)
print("max regret by kw:", REGRET, flush=True)

# ---------------- (5) tails / crisis, before/after ----------------
btc_d = pd.DataFrame(dict(d=(src.ts // 86400000).astype(np.int64), r=src.btc_r)).groupby("d")["r"].sum()
dday = np.array(sorted(set(day.tolist())))


def crisis(res):
    net = res["R"] - res["CST"]["canon"] + res["F"]
    dv = daily(net).values
    b = btc_d.reindex(dday).values; ok = np.isfinite(b)
    q5 = np.nanpercentile(b[ok], 5)
    o = dict(mean_all_bps=round(float(dv.mean() * 1e4), 1),
             mean_btc_worst5pct_bps=round(float(dv[ok][b[ok] <= q5].mean() * 1e4), 1),
             frac_neg_all=round(float((dv < 0).mean()), 3))
    for nm, ds in [("FTX_2022-11-09", "2022-11-09"), ("LUNA_2022-05-12", "2022-05-12"),
                   ("yencarry_2024-08-05", "2024-08-05")]:
        k = int(pd.Timestamp(ds, tz="UTC").timestamp() // 86400)
        w = np.where(dday == k)[0]
        o[nm] = round(float(dv[w[0]]), 4) if len(w) else None
    return o


TAILS = {}
for var in FUND:
    TAILS[f"{var}|solo_funding"] = crisis(run({"funding": 1.0}, var))
    for kw in (0.30, 0.50):
        TAILS[f"{var}|kw{kw}"] = crisis(RESC[(var, kw)])
for k, v in TAILS.items():
    print(f"  {k:26s} all {v['mean_all_bps']:6.1f} | BTCw5% {v['mean_btc_worst5pct_bps']:7.1f} | "
          f"FTX {v['FTX_2022-11-09']*100 if v['FTX_2022-11-09'] else 0:+6.2f}%", flush=True)

json.dump(dict(title="Re-run of funding-dependent conclusions on the dimension-fixed factor",
               created="2026-07-25", auditor="0C",
               caliber="unit-L1-gross, canonical rank+cap, daily x365, STRUCTURAL; canon=1.9bps flat, "
                       "vip0=per-coin Binance VIP0+BNB maker1.8/taker4.5/fill0.7/adverse-normal",
               note="funding CASH-FLOW uses the raw per-settlement rate (correct as shipped); only the "
                    "SIGNAL is re-dimensioned, so P&L changes only via positions",
               solo_legs=SOLO, carry_concentration=CONC, king_weight_sweep=SWEEP,
               bootstrap_vs_kw030=BOOT, walk_forward=WF,
               decay_surface_normfix=SURF, max_regret_by_kw=REGRET, tails=TAILS),
          open(EDA + "funding_dimfix_rerun_raw.json", "w"), indent=1, default=str)
print("\nSAVED exports/eda/funding_dimfix_rerun_raw.json", flush=True)

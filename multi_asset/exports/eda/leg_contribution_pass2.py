"""0C leg-contribution review, pass 2 — two questions pass 1 could not answer.

(A) COMPANION DIAGNOSTIC: at a FIXED king weight, which of the other three legs actually carries the
    diversification? (pass 1's subsets confounded companion identity with king weight.)
(B) ★ KING-DECAY STRESS: the whole case for the current 30% king weight is insurance against the DL
    leg decaying. So: degrade king's cross-sectional signal to delta x its measured strength
    (king_eff = d*z(king) + sqrt(1-d^2)*z(shuffled king) -- same scale, IC ~ d*IC) and re-solve the
    optimal king weight. Answers "how far must king fall before 0.30 is the right weight?" with a
    real re-simulation instead of an assertion.

Caliber identical to leg_contribution_review.py. Merges into leg_contribution_review_raw.json.
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
HOUR_MS = 3600000; CALIB_FLOOR = 4.0e6
VIP0 = dict(maker=1.8, taker=4.5, adv=2.0, phi=0.7)
DELTAS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3]
KW = [0.0, 0.15, 0.30, 0.40, 0.50, 0.60, 0.70, 0.85, 1.0]
SEED = 20260725

src = PanelSource(); N = src.N; symbols = src.symbols
months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13) if not (y == 2026 and m > 6)]
anchors = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))
dt = pd.to_datetime(src.ts[anchors], unit="ms", utc=True)
yr = dt.year.to_numpy(); day = (src.ts[anchors] // 86400000).astype(np.int64)
years = sorted(set(int(y) for y in yr)); T = len(src.ts); t0 = int(src.ts[0]); n = len(anchors)

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
COSTV = {"canon": np.full(N, 1.9),
         "vip0": VIP0["phi"] * (VIP0["maker"] + MEXEC) + (1 - VIP0["phi"]) * (VIP0["taker"] + HS)}


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


# ---------- PASS 1: cadence-held legs, for each king-decay level ----------
rng = np.random.default_rng(SEED)
RET = np.zeros((n, N)); FRA = np.full((n, N), np.nan)
HELD = {d: np.zeros((n, 4, N), np.float32) for d in DELTAS}
held = {d: {k: np.zeros(N) for k in LEGS} for d in DELTAS}
for i, t in enumerate(anchors):
    ti = int(t); m = src.tradeable(ti)
    kz = _z(src.king[ti, m])
    perm = rng.permutation(len(kz)); kzs = kz[perm]          # cross-sectionally shuffled king (IC~0)
    other = {"s2": _l1(_z(src.s2[ti, m])),
             "funding": _l1(-_rank(src.CH[ti, m, src.fund_idx].astype(float))),
             "size": _l1(_z(src.CH[ti, m, src.size_idx].astype(float)))}
    for d in DELTAS:
        keff = _l1(_z(d * kz + np.sqrt(max(0.0, 1 - d * d)) * kzs))
        lp = dict(other); lp["king"] = keff
        for k in LEGS:
            if i == 0 or ti % CAD[k] == 0:
                nw = np.zeros(N); nw[m] = lp[k]; held[d][k] = nw
        for a, k in enumerate(LEGS):
            HELD[d][i, a] = held[d][k]
    r = src.Y4[ti]; ok = np.isfinite(r)
    RET[i, ok] = r[ok]; FRA[i] = FR[ti]
FRZ = np.where(np.isfinite(FRA), FRA, 0.0)
print("[pass1] held built for %d decay levels" % len(DELTAS), flush=True)


def run(w, d=1.0):
    wv = np.array([w.get(k, 0.0) for k in LEGS], np.float64)
    H = HELD[d]
    R = np.zeros(n); F = np.zeros(n); TU = np.zeros(n)
    CST = {rg: np.zeros(n) for rg in COSTV}
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
        prev = unit
    return dict(R=R, F=F, CST=CST, TU=TU)


def sh(v):
    v = np.asarray(v, float); s = v.std()
    return float(v.mean() / s * np.sqrt(365)) if s > 1e-12 else np.nan


def ev(res, rg):
    net = res["R"] - res["CST"][rg] + res["F"]
    dl = pd.DataFrame(dict(day=day, yr=yr, x=net)).groupby("day").agg(
        x=("x", "sum"), yr=("yr", "first")).reset_index()
    py = {int(y): round(sh(g["x"].values), 2) for y, g in dl.groupby("yr")}
    return dict(sharpe=round(sh(dl["x"].values), 2), per_year=py,
                worst_year_sharpe=round(min(py.values()), 2),
                ann_return=round(float(dl["x"].mean() * 365), 4),
                turnover_ann=round(float(res["TU"].sum() / ((int(src.ts[anchors[-1]]) - int(src.ts[anchors[0]])) / (86400000 * 365.25))), 1))


# ---------- (A) companion diagnostic at fixed king weight ----------
COMP = {}
for kw in (0.5, 0.6):
    for comp in ("s2", "funding", "size", "even"):
        if comp == "even":
            w = {"king": kw, "s2": (1 - kw) / 3, "funding": (1 - kw) / 3, "size": (1 - kw) / 3}
        else:
            w = {"king": kw, comp: 1 - kw}
        name = f"king{int(kw*100)}_{comp}"
        r = run(w)
        COMP[name] = {"weights": {k: round(w.get(k, 0.0), 4) for k in LEGS},
                      "canon": ev(r, "canon"), "vip0": ev(r, "vip0")}
        print(f"  {name:18s} canon {COMP[name]['canon']['sharpe']:6.2f} "
              f"(worst yr {COMP[name]['canon']['worst_year_sharpe']:5.2f}) | "
              f"vip0 {COMP[name]['vip0']['sharpe']:6.2f} | turn {COMP[name]['canon']['turnover_ann']:.0f}", flush=True)
# drop-one-leg variants at the CURRENT relative proportions
DROP = {}
for drop in ("funding", "size", "s2", None):
    base = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}
    if drop:
        base.pop(drop)
    s = sum(base.values()); w = {k: v / s for k, v in base.items()}
    name = f"current_drop_{drop}" if drop else "current"
    r = run(w)
    DROP[name] = {"weights": {k: round(w.get(k, 0.0), 4) for k in LEGS},
                  "canon": ev(r, "canon"), "vip0": ev(r, "vip0")}
    print(f"  {name:20s} canon {DROP[name]['canon']['sharpe']:6.2f} | vip0 {DROP[name]['vip0']['sharpe']:6.2f}", flush=True)

# ---------- (B) king-decay x king-weight surface ----------
SURF = {}
print("\n[decay surface] canon Sharpe; rest of book at current relative proportions", flush=True)
hdr = "delta\\kw " + "".join(f"{k:>7.2f}" for k in KW) + "   argmax"
print(hdr, flush=True)
for d in DELTAS:
    row = {}
    for kw in KW:
        rest = 1 - kw; b = {"s2": 0.10, "funding": 0.30, "size": 0.30}; s = sum(b.values())
        w = {k: v / s * rest for k, v in b.items()}; w["king"] = kw
        row[kw] = ev(run(w, d), "canon")
    best = max(row, key=lambda k: row[k]["sharpe"])
    SURF[d] = {"by_king_weight": {str(k): row[k] for k in row}, "argmax_king_weight": best,
               "argmax_sharpe": row[best]["sharpe"], "sharpe_at_current_0.30": row[0.30]["sharpe"]}
    print(f"{d:5.1f}   " + "".join(f"{row[k]['sharpe']:7.2f}" for k in KW) + f"   {best:.2f}", flush=True)

out = dict(companion_at_fixed_king=COMP, drop_one_leg=DROP,
           king_decay_surface=dict(
               spec=("king_eff = d*z(king) + sqrt(1-d^2)*z(cross-sectionally shuffled king); same scale, "
                     "IC ~ d x measured IC. Rest of book held at the CURRENT relative proportions "
                     "(s2 0.10 : funding 0.30 : size 0.30). canon cost, funding P&L on. seed %d" % SEED),
               deltas=DELTAS, king_weights=KW, surface={str(k): v for k, v in SURF.items()}))
RAW = EDA + "leg_contribution_review_raw.json"
j = json.load(open(RAW)); j.update(out)
json.dump(j, open(RAW, "w"), indent=1, default=str)
print("\nMERGED pass-2 into leg_contribution_review_raw.json", flush=True)

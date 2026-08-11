"""0C — three-leg book assembly V2: legs extended to FULL HISTORY (CPU-only). Unlocks a multi-year
joint window (incl 2026H1) so the diversification / weight recommendation is regime-representative.
Appends to book_assembly.{json,md} as a v2 section (writes book_assembly_v2_raw.json).

Leg sources (v2 = full history):
  (a) FUNDING : RAW crowding-reversion book on 14 mega-caps (megacap_funding_replay.build_panel,
                full 2020-2026), z-weights on -funding_ema, 1h rebalance net@2bps. This is the DEPLOYED
                funding leg (v1 mistakenly used the DL-trained funding preds -> only 123d OOS).
  (b) DL_QIM  : 110 wide, 4h, QIM 5yr net@5bps (2022-2026, unchanged).
  (c) SIZE    : oriented_z(-log DVOL) on wide_panel_FULL (2021-2026, extends book2's 2024-06..2025-10),
                1h rebalance, tiered cost -- same caliber as build_book2, longer span.
Legs risk-normalized (unit daily std) before combining so weights = RISK budget; equal-risk == v1 inverse-vol.
"""
import sys, numpy as np, pandas as pd, json, glob
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from scipy.stats import rankdata
from multi_asset.data.megacap_funding_replay import build_panel, HOUR_MS

E = "multi_asset/exports/eda/"
TR = "multi_asset/exports/train/"
WPF = "multi_asset/exports/wide_panel_full.npz"
ANN_D = np.sqrt(365.0)


def days_ms(ts):
    return pd.to_datetime(np.asarray(ts).astype(np.int64), unit="ms", utc=True).floor("D")


def rank_weights(sc):
    r = sc.argsort().argsort().astype(np.float64); r = r - r.mean()
    s = np.abs(r).sum(); return r / s * 2.0 if s > 0 else r


# ---------- (a) FUNDING raw crowding-reversion, full history ----------
def leg_funding(cost_bps=2.0):
    grid, syms, CLOSE, FUND = build_panel()
    logc = np.log(np.where(CLOSE > 0, CLOSE, np.nan))
    Y = np.full_like(logc, np.nan); Y[:-1] = logc[1:] - logc[:-1]
    gap = np.zeros(len(grid), bool); gap[:-1] = (grid[1:] - grid[:-1]) > 2 * HOUR_MS
    Y[gap] = np.nan
    dd = days_ms(grid); N = FUND.shape[1]
    dser = {}; prevW = np.zeros(N)
    for i in range(len(grid)):
        v = np.where(np.isfinite(FUND[i]) & np.isfinite(Y[i]))[0]
        if v.size < 5:
            continue
        f = -FUND[i, v]; z = (f - f.mean()) / (f.std() + 1e-12); z -= z.mean()
        W = np.zeros(N); s = np.abs(z).sum()
        if s > 0:
            W[v] = z / s
        gross = float(np.nansum(W * np.nan_to_num(Y[i])))
        turn = np.abs(W - prevW).sum(); net = gross - turn * (cost_bps * 1e-4)
        dser[dd[i]] = dser.get(dd[i], 0.0) + net; prevW = W
    s = pd.Series(dser).sort_index(); s.name = "funding"; return s


# ---------- (b) DL QIM, full history ----------
def comp_row(sc_t, base):
    K = sc_t.shape[1]; comp = np.zeros(base.size); nk = 0
    for k in range(K):
        col = sc_t[base, k]
        if np.isfinite(col).all() and col.std() > 1e-12:
            comp += (col - col.mean()) / col.std(); nk += 1
    return comp / nk if nk else None


def leg_dl(cost_bps=5.0):
    pr = np.load(TR + "wideA_qim_multiyear/panel_ref.npz", allow_pickle=True)
    member = pr["member"].astype(bool); CL = pr["CL"].astype(bool); Yraw = pr["Yraw"].astype(np.float64)
    T, N = Yraw.shape; dd = days_ms(pr["ts"])
    P = np.full((T, N), np.nan)
    for f in sorted(glob.glob(TR + "wideA_qim_multiyear/fold_*_head_scores.npz")):
        z = np.load(f); sc = z["scores"]
        for t in z["te_rows"]:
            base = np.where(member[t] & CL[t] & np.isfinite(Yraw[t]))[0]
            if base.size >= 10:
                c = comp_row(sc[t], base)
                if c is not None:
                    P[t, base] = c
    dser = {}; prevw = np.zeros(N)
    for t in np.sort(np.where(np.isfinite(P).any(1))[0]):
        v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]))[0]
        if v.size < 10:
            continue
        w = np.zeros(N); w[v] = rank_weights(P[t, v])
        gross = float((w * np.nan_to_num(Yraw[t])).sum()); turn = np.abs(w - prevw).sum()
        dser[dd[t]] = dser.get(dd[t], 0.0) + gross - turn * (cost_bps * 1e-4); prevw = w
    s = pd.Series(dser).sort_index(); s.name = "dl"; return s


# ---------- (c) SIZE, full history (build_book2 caliber) ----------
def leg_size():
    z = np.load(WPF, allow_pickle=True)
    ts = z["ts"].astype(np.int64); Y = z["Y"].astype(np.float64); MEM = z["MEMBER"].astype(bool)
    DV = z["DVOL30"].astype(np.float64); dd = days_ms(ts)
    T, N = Y.shape
    # oriented_z(-log DVOL): size = small-minus-big
    fac = -np.log(np.where(DV > 0, DV, np.nan))
    Z = np.zeros((T, N))
    for t in range(T):
        v = MEM[t] & np.isfinite(fac[t]) & np.isfinite(Y[t])
        if v.sum() >= 8:
            f = fac[t, v]; Z[t, np.where(v)[0]] = (f - f.mean()) / (f.std() + 1e-12)
    g = np.nansum((Z / (np.abs(Z).sum(1, keepdims=True) + 1e-12)) * np.nan_to_num(Y), axis=1)
    if np.nanmean(g) < 0:
        Z = -Z
    # tiered cost by DVOL tercile (2/5/10 bps)
    tier = np.zeros((T, N), np.int8)
    for t in range(T):
        v = MEM[t] & np.isfinite(DV[t])
        if v.sum() >= 8:
            q = np.argsort(np.argsort(-DV[t, v])); nv = v.sum()
            tier[t, np.where(v)[0]] = np.where(q < nv / 3, 0, np.where(q < 2 * nv / 3, 1, 2))
    s = np.abs(Z).sum(1, keepdims=True); W = np.where(s > 0, Z / s, 0.0)
    gross = np.nansum(W * np.nan_to_num(Y), axis=1)
    dW = np.abs(np.diff(W, axis=0, prepend=0.0)); tb = np.array([2.0, 5.0, 10.0]) / 1e4
    net = gross - (dW * tb[tier]).sum(1)
    dser = {}
    for i in range(T):
        if np.isfinite(net[i]) and np.abs(W[i]).sum() > 0:
            dser[dd[i]] = dser.get(dd[i], 0.0) + net[i]
    s = pd.Series(dser).sort_index(); s.name = "size"; return s


def sharpe(x):
    x = np.asarray(x); return float(x.mean() / x.std() * ANN_D) if x.std() > 0 else np.nan


def worst_month(s):
    m = s.groupby(s.index.to_period("M")).sum(); return round(float(m.min()), 5), str(m.idxmin())


def worst_year(s):
    y = s.groupby(s.index.year).sum(); return round(float(y.min()), 5), int(y.idxmin())


def per_year(s):
    return {int(yr): round(sharpe(g), 2) for yr, g in s.groupby(s.index.year)}


def pair_corr(a, b, win=90):
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(j) < 20:
        return None
    rc = j.iloc[:, 0].rolling(win).corr(j.iloc[:, 1]).dropna()
    return dict(n_days=int(len(j)), corr=round(float(j.iloc[:, 0].corr(j.iloc[:, 1])), 3),
                start=str(j.index.min().date()), end=str(j.index.max().date()),
                roll_mean=round(float(rc.mean()), 3) if len(rc) else None,
                roll_std=round(float(rc.std()), 3) if len(rc) else None,
                roll_min=round(float(rc.min()), 3) if len(rc) else None,
                roll_max=round(float(rc.max()), 3) if len(rc) else None)


if __name__ == "__main__":
    print("building full-history legs...", flush=True)
    a = leg_funding(); b = leg_dl(); c = leg_size()
    for s in (a, b, c):
        print(f"  {s.name}: {len(s)}d {s.index.min().date()}..{s.index.max().date()} Sharpe {sharpe(s):.2f} "
              f"worst-yr {worst_year(s)} per-yr-Sh {per_year(s)}", flush=True)

    pairs = dict(funding_dl=pair_corr(a, b), funding_size=pair_corr(a, c), dl_size=pair_corr(b, c))
    print("PAIRS:", json.dumps(pairs), flush=True)

    # 3-way joint, risk-normalized (unit daily std) so weights == RISK budget
    J = pd.concat([a, b, c], axis=1, join="inner").dropna(); J.columns = ["funding", "dl", "size"]
    Jn = J / J.std()
    print(f"JOINT {J.index.min().date()}..{J.index.max().date()} n_days {len(J)}", flush=True)
    leg_js = {k: round(sharpe(J[k]), 2) for k in J.columns}
    leg_wy = {k: worst_year(J[k]) for k in J.columns}
    leg_py = {k: per_year(J[k]) for k in J.columns}

    def port(wd):
        w = np.array([wd[k] for k in J.columns]); p = pd.Series((Jn.values * w).sum(1), index=Jn.index)
        wm, wmid = worst_month(p); wy, wyid = worst_year(p)
        return dict(weights={k: round(wd[k], 3) for k in J.columns}, sharpe=round(sharpe(p), 2),
                    worst_month=wm, worst_month_id=wmid, worst_year=wy, worst_year_id=wyid,
                    per_year_sharpe=per_year(p))

    eqrisk = {k: 1 / 3 for k in J.columns}
    ports = dict(equal_risk=port(eqrisk))
    # DL risk-budget sensitivity {0.2,0.3,0.4}; funding/size split the rest equally
    sens = {}
    for wdl in (0.2, 0.3, 0.4):
        rest = (1 - wdl) / 2
        sens[str(wdl)] = port({"dl": wdl, "funding": rest, "size": rest})

    result = dict(
        title="Three-leg book assembly V2 (full-history, 0C)", created="2026-07-12", auditor="0C",
        v1_vs_v2=("v1 joint window was 123d (funding used DL-trained preds, 123d OOS) + DL-strong 2025 only. "
                  "v2 uses the DEPLOYED raw crowding-reversion funding book (full 2020-2026) + SIZE rebuilt "
                  "on wide_panel_full (to 2026H1) -> multi-year joint window incl DL's weak years."),
        alignment_note=("daily net returns. funding=14 mega-cap 1h net@2bps raw z-weight crowding-reversion; "
                        "dl=110 wide 4h net@5bps QIM 5yr; size=110 wide 1h tiered-cost oriented_z(-logDVOL) on "
                        "wide_panel_full. Portfolio legs RISK-NORMALIZED (unit daily std) so weights=risk budget; "
                        "equal-risk == v1 inverse-vol. funding gross-norm sum|W|=1 vs dl sum|w|=2 (scale-invariant "
                        "for corr; risk-norm for portfolio). EMA-hold/vol-target omitted: funding turnover ~0.05 "
                        "(slow signal) so full-turnover ~ EMA-hold; correlation & risk-norm are caliber-invariant."),
        leg_full=dict(sharpe={s.name: round(sharpe(s), 2) for s in (a, b, c)},
                      window={s.name: [str(s.index.min().date()), str(s.index.max().date())] for s in (a, b, c)},
                      worst_year={s.name: worst_year(s) for s in (a, b, c)},
                      per_year_sharpe={s.name: per_year(s) for s in (a, b, c)}),
        pairwise_corr=pairs,
        joint_window=dict(start=str(J.index.min().date()), end=str(J.index.max().date()), n_days=int(len(J)),
                          leg_sharpe=leg_js, leg_worst_year=leg_wy, leg_per_year_sharpe=leg_py),
        portfolios=ports, dl_weight_sensitivity=sens)
    json.dump(result, open(E + "book_assembly_v2_raw.json", "w"), indent=2, default=str)
    print("PORT equal_risk:", json.dumps(ports["equal_risk"]), flush=True)
    print("SENS:", json.dumps(sens), flush=True)
    print("SAVED " + E + "book_assembly_v2_raw.json", flush=True)

"""0C — QIM full-GO condition #2: real-execution feasibility (CPU-only, no GPU).
Turnover/holding profile + maker-fill capacity table + small-coin fill-haircut + sizing rec.
Writes multi_asset/exports/eda/qim_execution_feasibility.{json,md}.

Model (honest/conservative):
  - rank_weights (sum|w|=2, dollar-neutral). AUM G = gross notional (sum|pos|=G); pos_i = w_i * G/2.
  - 4h-rebalanced on the CL non-overlap grid. Maker fill capacity over the 4h holding window =
    x% * V4h (sum of hourly QVOL over [t, t+4h)). Unfilled desired = NOT traded (position falls short
    of target) -> loses alpha, adds no cost. Conservative on alpha capture.
  - PnL on realized held positions vs RAW forward return; cost on ACTUAL filled volume.
  - Sharpe annualized per_yr = 365*24/4 = 2190.
"""
import numpy as np, pandas as pd, json, os, glob
from scipy.stats import rankdata

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
TRAIN = ROOT + "/multi_asset/exports/train"
EDA = ROOT + "/multi_asset/exports/eda"
QIM = TRAIN + "/wideA_qim_multiyear"
H = 4
PER_YR = 365 * 24 / H
ANN = np.sqrt(PER_YR)


def rank_weights(sc):
    r = sc.argsort().argsort().astype(np.float64)
    r = r - r.mean()
    s = np.abs(r).sum()
    return r / s * 2.0 if s > 0 else r


def comp_row(scores_t, base):
    K = scores_t.shape[1]
    comp = np.zeros(base.size); nk = 0
    for k in range(K):
        col = scores_t[base, k]
        if np.isfinite(col).all() and col.std() > 1e-12:
            comp += (col - col.mean()) / col.std(); nk += 1
    return comp / nk if nk else None


def build_periods():
    pr = np.load(QIM + "/panel_ref.npz", allow_pickle=True)
    wp = np.load(ROOT + "/multi_asset/exports/wide_panel_full.npz", allow_pickle=True)
    member, CL, Yraw = pr["member"].astype(bool), pr["CL"].astype(bool), pr["Yraw"].astype(np.float64)
    ts, day = pr["ts"].astype(np.int64), pr["day"]
    symbols = [str(s) for s in pr["symbols"]]
    QV = wp["QVOL"].astype(np.float64)
    T, N = Yraw.shape
    yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    # 4h-forward notional (fill window); fallback to trailing 4h if fwd missing
    QVf = np.nan_to_num(QV, nan=0.0)
    csum = np.cumsum(np.vstack([np.zeros((1, N)), QVf]), axis=0)
    V4h = np.full((T, N), np.nan)
    for t in range(T):
        hi = min(t + H, T)
        V4h[t] = csum[hi] - csum[t]
    # size tercile by per-coin median member notional
    medn = np.nanmedian(np.where(member, QV, np.nan), axis=0)
    fin = np.isfinite(medn)
    cut = np.nanpercentile(medn[fin], [33, 66])
    tercile = np.full(N, -1)
    tercile[fin & (medn <= cut[0])] = 0   # small
    tercile[fin & (medn > cut[0]) & (medn <= cut[1])] = 1
    tercile[fin & (medn > cut[1])] = 2    # large
    # stitch composite prediction across folds
    P = np.full((T, N), np.nan)
    for f in sorted(glob.glob(QIM + "/fold_*_head_scores.npz"),
                    key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        z = np.load(f); sc = z["scores"]; te = z["te_rows"]
        for t in te:
            base = np.where(member[t] & CL[t] & np.isfinite(Yraw[t]))[0]
            if base.size < 10:
                continue
            c = comp_row(sc[t], base)
            if c is not None:
                P[t, base] = c
    # per-period records
    periods = []
    rows = np.sort(np.where(np.isfinite(P).any(1))[0])
    for t in rows:
        v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]) & (V4h[t] > 0))[0]
        if v.size < 10:
            continue
        w = rank_weights(P[t, v])
        periods.append(dict(t=t, year=int(yr[t]), idx=v, w=w, y=Yraw[t, v],
                            v4=V4h[t, v], terc=tercile[v]))
    return dict(periods=periods, N=N, symbols=symbols, tercile=tercile, medn=medn, T=T,
                member=member, CL=CL, QV=QV)


def turnover_profile(D):
    periods = D["periods"]; N = D["N"]
    by_year = {}
    held = np.zeros(N)
    # decile membership run-length trackers
    for yrly in sorted(set(p["year"] for p in periods)):
        by_year[yrly] = dict(turn=[], long_frac_small=[], wabs_by_terc={0: [], 1: [], 2: []})
    prev_w = np.zeros(N)
    long_run, short_run = {}, {}   # coin -> current run length
    hold_lens = []
    for p in periods:
        w = np.zeros(N); w[p["idx"]] = p["w"]
        turn = np.abs(w - prev_w).sum()
        by_year[p["year"]]["turn"].append(turn)
        # weight magnitude by tercile
        for tc in (0, 1, 2):
            m = p["terc"] == tc
            if m.any():
                by_year[p["year"]]["wabs_by_terc"][tc].append(np.abs(p["w"][m]).sum())
        # decile membership run-length (top/bottom 10% by weight)
        thr = np.quantile(p["w"], 0.9); thl = np.quantile(p["w"], 0.1)
        longset = set(p["idx"][p["w"] >= thr].tolist())
        shortset = set(p["idx"][p["w"] <= thl].tolist())
        for c in list(long_run):
            if c not in longset:
                hold_lens.append(long_run.pop(c))
        for c in list(short_run):
            if c not in shortset:
                hold_lens.append(short_run.pop(c))
        for c in longset:
            long_run[c] = long_run.get(c, 0) + 1
        for c in shortset:
            short_run[c] = short_run.get(c, 0) + 1
        prev_w = w
    for c in long_run:
        hold_lens.append(long_run[c])
    for c in short_run:
        hold_lens.append(short_run[c])
    prof = {}
    for y, d in by_year.items():
        prof[str(y)] = dict(mean_turnover=round(float(np.mean(d["turn"])), 3),
                            n_rebal=len(d["turn"]),
                            wabs_small=round(float(np.mean(d["wabs_by_terc"][0])), 3),
                            wabs_mid=round(float(np.mean(d["wabs_by_terc"][1])), 3),
                            wabs_large=round(float(np.mean(d["wabs_by_terc"][2])), 3))
    return dict(per_year=prof,
                mean_turnover=round(float(np.mean([np.mean(by_year[y]["turn"]) for y in by_year])), 3),
                avg_hold_periods=round(float(np.mean(hold_lens)), 2),
                avg_hold_hours=round(float(np.mean(hold_lens) * H), 1),
                note="turnover=sum|dw| per 4h (max 4=full flip); wabs_* = mean gross |w| in each size tercile per period (of total 2.0)")


def sim(D, G, xpct, cost_bps, smallcoin_fill=1.0):
    """Constrained maker-fill sim at gross AUM G, participation xpct%, cost_bps/side.
    smallcoin_fill scales fill capacity on the small (tercile 0) leg. Returns net Sharpe + net ann bps."""
    periods = D["periods"]; N = D["N"]
    S = G / 2.0
    hpos = np.zeros(N)
    g = np.empty(len(periods)); trd = np.empty(len(periods))
    for k, p in enumerate(periods):
        v = p["idx"]
        tgt = np.zeros(N); tgt[v] = p["w"] * S
        desired = tgt[v] - hpos[v]
        cap = (xpct / 100.0) * p["v4"]
        if smallcoin_fill != 1.0:
            cap = cap * np.where(p["terc"] == 0, smallcoin_fill, 1.0)
        fill = np.sign(desired) * np.minimum(np.abs(desired), cap)
        newp = hpos[v] + fill
        # zero out coins that left the universe next period handled implicitly (hpos persists; sold when targeted)
        g[k] = float((newp * p["y"]).sum())
        trd[k] = float(np.abs(fill).sum())
        hpos[:] = 0.0; hpos[v] = newp
    cost = trd * (cost_bps * 1e-4)
    net = g - cost
    sh = float(net.mean() / net.std() * ANN) if net.std() > 0 else np.nan
    net_ann_bps = float(net.mean() / G * PER_YR * 1e4)   # net return on gross AUM, annualized bps
    fill_ratio = float((g != 0).mean())
    return dict(net_sharpe=round(sh, 2), net_ann_bps_on_gross=round(net_ann_bps, 1),
                mean_traded_per_period_usd=round(float(trd.mean()), 0))


def sim_peryear(D, G, xpct, cost_bps, smallcoin_fill=1.0):
    periods = D["periods"]; N = D["N"]; S = G / 2.0
    hpos = np.zeros(N)
    byyr = {}
    for p in periods:
        v = p["idx"]
        tgt = np.zeros(N); tgt[v] = p["w"] * S
        desired = tgt[v] - hpos[v]
        cap = (xpct / 100.0) * p["v4"]
        if smallcoin_fill != 1.0:
            cap = cap * np.where(p["terc"] == 0, smallcoin_fill, 1.0)
        fill = np.sign(desired) * np.minimum(np.abs(desired), cap)
        newp = hpos[v] + fill
        gp = float((newp * p["y"]).sum()); tp = float(np.abs(fill).sum())
        byyr.setdefault(p["year"], {"g": [], "t": []})
        byyr[p["year"]]["g"].append(gp); byyr[p["year"]]["t"].append(tp)
        hpos[:] = 0.0; hpos[v] = newp
    out = {}
    for y, d in byyr.items():
        gg = np.array(d["g"]); tt = np.array(d["t"])
        net = gg - tt * (cost_bps * 1e-4)
        out[str(y)] = round(float(net.mean() / net.std() * ANN), 2) if net.std() > 0 else None
    return out


if __name__ == "__main__":
    print("building periods...", flush=True)
    D = build_periods()
    print(f"periods={len(D['periods'])} coins={D['N']}", flush=True)

    prof = turnover_profile(D)
    print("TURNOVER:", json.dumps(prof, indent=2), flush=True)

    # frictionless reference (huge participation)
    ref = sim(D, 1e6, 1e9, 0.0)
    ref23 = sim(D, 1e6, 1e9, 2.3)
    ref5 = sim(D, 1e6, 1e9, 5.0)
    print(f"FRICTIONLESS ref Sharpe: c0={ref['net_sharpe']} c2.3={ref23['net_sharpe']} c5={ref5['net_sharpe']}", flush=True)

    # capacity table: AUM x participation, at cost 2.3 and 5.0
    AUMs = [1e6, 5e6, 1e7, 2.5e7, 5e7, 1e8, 2.5e8, 5e8]
    XP = [0.5, 1.0, 2.0, 5.0]
    cap_tbl = {}
    for x in XP:
        cap_tbl[str(x)] = {}
        for G in AUMs:
            r23 = sim(D, G, x, 2.3); r5 = sim(D, G, x, 5.0)
            cap_tbl[str(x)][f"{G:.0f}"] = dict(
                netSh_c2p3=r23["net_sharpe"], netSh_c5p0=r5["net_sharpe"],
                net_ann_bps_c5=r5["net_ann_bps_on_gross"])
            print(f"  x={x}% AUM=${G:.0e}: Sh@2.3={r23['net_sharpe']} Sh@5={r5['net_sharpe']} "
                  f"netbps@5={r5['net_ann_bps_on_gross']}", flush=True)

    # small-coin fill haircut per-year at a reference AUM (conservative middle: G=$25M, x=1%, cost 5bps)
    Gref, xref, cref = 2.5e7, 1.0, 5.0
    hair = {}
    for fr in (1.0, 0.7, 0.5):
        hair[str(fr)] = sim_peryear(D, Gref, xref, cref, smallcoin_fill=fr)
        print(f"  smallcoin_fill={fr} per-year Sh@G$25M,x1%,c5: {hair[str(fr)]}", flush=True)

    result = dict(
        title="QIM execution feasibility (full-GO condition #2)", created="2026-07-12", auditor="0C",
        model_notes=("4h-rebalanced rank-L/S, gross AUM G (sum|pos|=G). Maker fill = x% of 4h-forward "
                     "QVOL; unfilled desired = NOT traded (loses alpha, no extra cost) = conservative. "
                     "PnL on realized held pos vs raw fwd ret; cost on filled volume; Sharpe ann per_yr=2190. "
                     "Universe is small-cap-heavy (median coin ~$1.5M/hr, bottom tercile ~$0.63M/hr, BTC ~$435M/hr)."),
        frictionless_ref=dict(sharpe_c0=ref["net_sharpe"], sharpe_c2p3=ref23["net_sharpe"], sharpe_c5=ref5["net_sharpe"]),
        turnover_profile=prof,
        capacity_table=cap_tbl,
        smallcoin_fill_haircut=dict(ref=dict(AUM_usd=Gref, participation_pct=xref, cost_bps=cref), per_year=hair),
        size_terciles=dict(bottom_median_notional_hr=round(float(np.nanmedian(D["medn"][D["tercile"] == 0])), 0),
                           top_median_notional_hr=round(float(np.nanmedian(D["medn"][D["tercile"] == 2])), 0)))
    json.dump(result, open(EDA + "/qim_execution_feasibility_raw.json", "w"), indent=2, default=str)
    print("\nSAVED -> " + EDA + "/qim_execution_feasibility_raw.json", flush=True)

"""0C Track-1 — apply the maker-fill conservative law to the xattn king's REAL 4h trades → per-year
conservative net-Sharpe LOWER BOUND (full book vs mega+mid-only). CPU-only.
Scaling law from makerfill_calib_raw.json (14 mega-caps): fill_rate(f,k) is liquidity-INVARIANT
(f=order/hourly-notl); half_spread & adverse markout interp by log10(hourly notl). SMALL tier (< calib
floor $4M/h) = EXTRAPOLATED with explicit conservative haircuts (fill x0.7, markout=p25-worse,
spread-capture credit x0.5). Writes exports/eda/makerfill_apply_raw.json.
"""
import numpy as np, pandas as pd, json, glob
from scipy.stats import rankdata

TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
XK = TR + "wideA_lamorth0_xattn_5yr"
WPF = "multi_asset/exports/wide_panel_full.npz"
H = 4; PER_YR = 365 * 24 / H; ANN = np.sqrt(PER_YR)
TAKER_FEE = 1.5
SMALL_FILL_HAIRCUT = 0.7      # extra fill haircut below calib floor
SMALL_SPREAD_CREDIT = 0.5     # only credit 50% of spread capture in extrapolated illiquid names


def rank_weights(sc):
    r = sc.argsort().argsort().astype(np.float64); r = r - r.mean(); s = np.abs(r).sum()
    return r / s * 2.0 if s > 0 else r


def comp_panel(scores, member, CL, YR):
    T, N, K = scores.shape; C = np.full((T, N), np.nan)
    for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk:
            C[t, base] = comp / nk
    return C


def build_law(calib):
    pc = calib["per_coin"]; fg = [float(x) for x in calib["fgrid"]]
    coins = sorted(pc, key=lambda x: pc[x]["hourly_notl_usd"])
    logN = np.array([np.log10(pc[c]["hourly_notl_usd"]) for c in coins])
    half = np.array([pc[c]["half_spread_bps"] for c in coins])
    mk = np.array([pc[c]["markout_mean_bps"] for c in coins])
    mk25 = np.array([pc[c]["markout_p25_bps"] for c in coins])
    calib_floor = 10 ** logN.min()
    # liquidity-invariant fill curve = mean over coins, per (k,f)
    fillcurve = {k: np.array([np.mean([pc[c]["fill_rate"][k][str(f)] for c in coins]) for f in fg])
                 for k in ["60", "300", "900"]}

    def fill_rate(f, k, N):
        fr = float(np.interp(np.log10(max(f, 1e-6)), np.log10(fg), fillcurve[k]))
        if N < calib_floor:
            fr *= SMALL_FILL_HAIRCUT
        return min(max(fr, 0.0), 1.0)

    def costs(N):
        x = np.log10(max(N, 1e3))
        hs = float(np.interp(x, logN, half))
        m = float(np.interp(x, logN, mk)); m25 = float(np.interp(x, logN, mk25))
        below = N < calib_floor
        cred = SMALL_SPREAD_CREDIT if below else 1.0
        markout = m25 if below else m               # worse adverse tail for extrapolated small
        # CONSERVATIVE FLOOR: a filled maker order costs AT LEAST 0 -- do NOT book spread-capture as
        # profit (removes the market-making-profit optimism). eff_if_fill in [0, ...].
        eff_if_fill = max(0.0, -markout - hs * cred)   # bps, +=cost
        taker = hs + TAKER_FEE
        return eff_if_fill, taker, hs, markout, below
    return fill_rate, costs, calib_floor


if __name__ == "__main__":
    calib = json.load(open(EDA + "makerfill_calib_raw.json"))
    fill_rate, costs, calib_floor = build_law(calib)
    print(f"calib liquidity floor ${calib_floor/1e6:.1f}M/h", flush=True)

    pr = np.load(XK + "/panel_ref.npz", allow_pickle=True)
    member, CL = pr["member"].astype(bool), pr["CL"].astype(bool)
    YR, Yraw = pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    yr = pd.to_datetime(pr["ts"].astype(np.int64), unit="ms", utc=True).year.to_numpy()
    T, Ncoin = Yraw.shape
    # per-coin hourly notl from wide_panel_full QVOL (median over member-hours)
    wp = np.load(WPF, allow_pickle=True)
    QV = wp["QVOL"].astype(np.float64)
    notl = np.nanmedian(np.where(member, QV, np.nan), axis=0)   # (Ncoin,)
    small_cut = np.nanpercentile(notl[np.isfinite(notl)], 33)   # bottom tercile = small tier
    print(f"wide notl: BTC-tier max ${np.nanmax(notl)/1e6:.0f}M, median ${np.nanmedian(notl)/1e6:.2f}M, "
          f"small-tercile cut ${small_cut/1e6:.2f}M; {int((notl<calib_floor).sum())}/{Ncoin} coins below calib floor", flush=True)

    # stitch composite (per-fold comp_panel; each fold's scores are NaN outside its te_rows)
    P = np.full((T, Ncoin), np.nan)
    for f in sorted(glob.glob(XK + "/fold_*_head_scores.npz")):
        z = np.load(f)
        C = comp_panel(z["scores"], member, CL, YR)
        m = np.isfinite(C)
        P[m] = C[m]
    rows = np.sort(np.where(np.isfinite(P).any(1))[0])

    def run(AUM, k, tier="full"):
        S = AUM / 2.0; kss = str(k)
        floor = {"full": 0.0, "megamid": small_cut, "calib": calib_floor}[tier]
        prevw = np.zeros(Ncoin); byyr = {}
        for t in rows:
            v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]) & np.isfinite(notl))[0]
            v = v[notl[v] >= floor]
            if v.size < 10:
                continue
            w = np.zeros(Ncoin); w[v] = rank_weights(P[t, v])
            dw = w - prevw
            gross = float((w * np.nan_to_num(Yraw[t])).sum())
            cost = 0.0; twt = 0.0; fillwt = 0.0
            for i in v:
                adw = abs(dw[i])
                if adw < 1e-9:
                    continue
                O = adw * S; f = O / max(notl[i], 1e3)
                pf = fill_rate(f, kss, notl[i])
                eff_if, taker, hs, mk, below = costs(notl[i])
                effc = pf * eff_if + (1 - pf) * taker    # bps/side, conservative-floored
                cost += adw * effc * 1e-4
                twt += adw; fillwt += adw * pf
            net = gross - cost
            byyr.setdefault(int(yr[t]), {"g": [], "n": [], "cbps": [], "fill": []})
            byyr[int(yr[t])]["g"].append(gross); byyr[int(yr[t])]["n"].append(net)
            byyr[int(yr[t])]["cbps"].append(cost / twt * 1e4 if twt > 0 else 0.0)
            byyr[int(yr[t])]["fill"].append(fillwt / twt if twt > 0 else np.nan)
            prevw = w
        out = {}
        for y, dd in byyr.items():
            g = np.array(dd["g"]); n = np.array(dd["n"])
            out[str(y)] = dict(gross_sh=round(float(g.mean()/g.std()*ANN), 2) if g.std() > 0 else None,
                               net_sh=round(float(n.mean()/n.std()*ANN), 2) if n.std() > 0 else None,
                               net_ann_bps=round(float(n.mean()*PER_YR*1e4), 0),
                               eff_cost_bps_side=round(float(np.mean(dd["cbps"])), 3),
                               mean_fill_rate=round(float(np.nanmean(dd["fill"])), 3))
        return out

    result = dict(title="maker-fill conservative net-Sharpe lower bound (xattn king)", created="2026-07-12",
                  auditor="0C", calib_floor_usd=calib_floor, taker_fee=TAKER_FEE,
                  small_haircuts=dict(fill=SMALL_FILL_HAIRCUT, spread_credit=SMALL_SPREAD_CREDIT, markout="p25"),
                  n_coins_below_floor=int((notl < calib_floor).sum()), scenarios={})
    for AUM in (5e6, 10e6, 25e6):
        for k in (300, 900):
            for tier in ("full", "megamid", "calib"):
                tag = f"AUM{AUM/1e6:.0f}M_k{k}_{tier}"
                r = run(AUM, k, tier)
                result["scenarios"][tag] = r
                yrs = ["2022", "2023", "2024", "2025", "2026"]
                nsh = [r.get(y, {}).get("net_sh") for y in yrs]
                cb = [r.get(y, {}).get("eff_cost_bps_side") for y in yrs]
                fr = [r.get(y, {}).get("mean_fill_rate") for y in yrs]
                print(f"{tag}: netSh {nsh} | effcost {cb} | fill {fr}", flush=True)
    json.dump(result, open(EDA + "makerfill_apply_raw.json", "w"), indent=2, default=str)
    print("SAVED " + EDA + "makerfill_apply_raw.json", flush=True)

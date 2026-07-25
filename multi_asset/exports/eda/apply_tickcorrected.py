"""0C Track-1 deepdive — TICK-CORRECTED book net-Sharpe bound. Replaces the 1s-bar fill/markout (proven
optimistic) with TICK-measured values: fill_rate = mean tick curve (BTC, liquidity-invariant); adverse
selection markout = tick-measured (regime scenarios -2 normal / -3 blend / -5 stress) instead of the
1s ~0. half_spread from the 14-coin calib (per liquidity). eff_if_fill = -adverse - half_spread (NO
floor; it's a real cost now). CPU-only. Writes exports/eda/tickcorrected_apply_raw.json.
"""
import numpy as np, pandas as pd, json, glob
from scipy.stats import rankdata

TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
XK = TR + "wideA_lamorth0_xattn_5yr"
WPF = "multi_asset/exports/wide_panel_full.npz"
H = 4; PER_YR = 365 * 24 / H; ANN = np.sqrt(PER_YR)
TAKER_FEE = 1.5
SMALL_FILL_HAIRCUT = 0.7


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


def tick_fill_curve():
    d = json.load(open(EDA + "tick_vs_1s_raw.json"))
    fg = [float(x) for x in d["fgrid"]]
    curve = {}
    for k in ["60", "300", "900"]:
        curve[k] = np.array([np.nanmean([d["per_day"][day]["tick"]["fill_rate"][k][str(f)]
                             for day in d["days"] if d["per_day"][day]["tick"]]) for f in fg])
    return fg, curve


def half_spread_law():
    c = json.load(open(EDA + "makerfill_calib_raw.json"))["per_coin"]
    coins = sorted(c, key=lambda x: c[x]["hourly_notl_usd"])
    logN = np.array([np.log10(c[x]["hourly_notl_usd"]) for x in coins])
    half = np.array([c[x]["half_spread_bps"] for x in coins])
    floor = 10 ** logN.min()
    return lambda N: float(np.interp(np.log10(max(N, 1e3)), logN, half)), floor


if __name__ == "__main__":
    fg, tcurve = tick_fill_curve()
    half_of, calib_floor = half_spread_law()
    print(f"tick fill curve k300: {[round(x,2) for x in tcurve['300']]} (f={fg})", flush=True)

    def fill_rate(f, k, N):
        fr = float(np.interp(np.log10(max(f, 1e-6)), np.log10(fg), tcurve[k]))
        if N < calib_floor:
            fr *= SMALL_FILL_HAIRCUT
        return min(max(fr, 0.0), 1.0)

    pr = np.load(XK + "/panel_ref.npz", allow_pickle=True)
    member, CL = pr["member"].astype(bool), pr["CL"].astype(bool)
    YR, Yraw = pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    yr = pd.to_datetime(pr["ts"].astype(np.int64), unit="ms", utc=True).year.to_numpy()
    T, Ncoin = Yraw.shape
    QV = np.load(WPF, allow_pickle=True)["QVOL"].astype(np.float64)
    notl = np.nanmedian(np.where(member, QV, np.nan), axis=0)
    small_cut = np.nanpercentile(notl[np.isfinite(notl)], 33)

    P = np.full((T, Ncoin), np.nan)
    for f in sorted(glob.glob(XK + "/fold_*_head_scores.npz")):
        C = comp_panel(np.load(f)["scores"], member, CL, YR); m = np.isfinite(C); P[m] = C[m]
    rows = np.sort(np.where(np.isfinite(P).any(1))[0])

    def run(AUM, k, tier, adverse_bps):
        S = AUM / 2.0; kss = str(k)
        floor = {"full": 0.0, "megamid": small_cut, "calib": calib_floor}[tier]
        prevw = np.zeros(Ncoin); byyr = {}
        for t in rows:
            v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]) & np.isfinite(notl))[0]
            v = v[notl[v] >= floor]
            if v.size < 10:
                continue
            w = np.zeros(Ncoin); w[v] = rank_weights(P[t, v]); dw = w - prevw
            gross = float((w * np.nan_to_num(Yraw[t])).sum())
            cost = 0.0; twt = 0.0; fwt = 0.0
            for i in v:
                adw = abs(dw[i])
                if adw < 1e-9:
                    continue
                O = adw * S; f = O / max(notl[i], 1e3)
                pf = fill_rate(f, kss, notl[i]); hs = half_of(notl[i])
                eff_if = max(0.0, -adverse_bps - hs)     # adverse_bps is negative (adverse); -adverse = cost
                taker = hs + TAKER_FEE
                effc = pf * eff_if + (1 - pf) * taker
                cost += adw * effc * 1e-4; twt += adw; fwt += adw * pf
            net = gross - cost
            byyr.setdefault(int(yr[t]), {"g": [], "n": [], "c": [], "fr": []})
            byyr[int(yr[t])]["g"].append(gross); byyr[int(yr[t])]["n"].append(net)
            byyr[int(yr[t])]["c"].append(cost / twt * 1e4 if twt > 0 else 0.0)
            byyr[int(yr[t])]["fr"].append(fwt / twt if twt > 0 else np.nan)
            prevw = w
        out = {}
        for y, dd in byyr.items():
            g = np.array(dd["g"]); n = np.array(dd["n"])
            out[str(y)] = dict(gross_sh=round(float(g.mean()/g.std()*ANN), 2) if g.std() > 0 else None,
                               net_sh=round(float(n.mean()/n.std()*ANN), 2) if n.std() > 0 else None,
                               eff_cost_bps=round(float(np.mean(dd["c"])), 3),
                               fill=round(float(np.nanmean(dd["fr"])), 3))
        return out

    result = dict(title="tick-corrected book net-Sharpe bound", created="2026-07-12", auditor="0C",
                  corrections="fill=tick curve (BTC liquidity-invariant); adverse markout=tick scenarios; half_spread=calib",
                  scenarios={})
    for adverse, aname in [(-2.0, "normal"), (-3.0, "blend"), (-5.0, "stress")]:
        for AUM in (5e6, 10e6):
            for k in (300, 900):
                for tier in ("full", "megamid", "calib"):
                    tag = f"adv{aname}_AUM{AUM/1e6:.0f}M_k{k}_{tier}"
                    r = run(AUM, k, tier, adverse)
                    result["scenarios"][tag] = r
                    yrs = ["2022", "2023", "2024", "2025", "2026"]
                    print(f"{tag}: net {[r.get(y,{}).get('net_sh') for y in yrs]} | "
                          f"cost {[r.get(y,{}).get('eff_cost_bps') for y in yrs]} | fill {r.get('2024',{}).get('fill')}", flush=True)
    json.dump(result, open(EDA + "tickcorrected_apply_raw.json", "w"), indent=2, default=str)
    print("SAVED " + EDA + "tickcorrected_apply_raw.json", flush=True)

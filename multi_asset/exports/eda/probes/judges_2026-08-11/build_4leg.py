"""0C — 4-LEG book assembly (funding / DL-king / SIZE / S2-24h). Daily net returns, book_assembly v2
caliber. king = xattn king (king_pred_panel, 4h). S2 = wideA_s2_y24_5yr composite (24h). Risk-normalized
(unit daily std). Pairwise corr (esp S2↔king, S2↔SIZE), 3-leg vs 4-leg Sharpe/worst-month/worst-year,
S2-weight sensitivity {0.05/0.1/0.15} + inverse-vol, worst-year protection (2026H1). CPU-only.
Writes exports/eda/book_assembly_4leg_raw.json.
"""
import sys, numpy as np, pandas as pd, json, glob
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from scipy.stats import rankdata
from multi_asset.data.megacap_funding_replay import build_panel, HOUR_MS

TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
WPF = "multi_asset/exports/wide_panel_full.npz"
ANN = np.sqrt(365.0)


def days_ms(ts):
    return pd.to_datetime(np.asarray(ts).astype(np.int64), unit="ms", utc=True).floor("D")


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


def sh(s):
    s = np.asarray(s); return float(s.mean() / s.std() * ANN) if s.std() > 0 else np.nan


def wm(s):
    m = s.groupby(s.index.to_period("M")).sum(); return round(float(m.min()), 4)


def wy(s):
    y = s.groupby(s.index.year).sum(); return round(float(y.min()), 4), int(y.idxmin())


def leg_funding(cost=2.0):
    grid, syms, CLOSE, FUND = build_panel()
    logc = np.log(np.where(CLOSE > 0, CLOSE, np.nan)); Y = np.full_like(logc, np.nan); Y[:-1] = logc[1:] - logc[:-1]
    gap = np.zeros(len(grid), bool); gap[:-1] = (grid[1:] - grid[:-1]) > 2 * HOUR_MS; Y[gap] = np.nan
    dd = days_ms(grid); N = FUND.shape[1]; dser = {}; prev = np.zeros(N)
    for i in range(len(grid)):
        v = np.where(np.isfinite(FUND[i]) & np.isfinite(Y[i]))[0]
        if v.size < 5:
            continue
        f = -FUND[i, v]; z = (f - f.mean()) / (f.std() + 1e-12); z -= z.mean(); W = np.zeros(N); s = np.abs(z).sum()
        if s > 0:
            W[v] = z / s
        g = float(np.nansum(W * np.nan_to_num(Y[i]))); tn = np.abs(W - prev).sum()
        dser[dd[i]] = dser.get(dd[i], 0.0) + g - tn * cost * 1e-4; prev = W
    return pd.Series(dser).sort_index()


def leg_size():
    z = np.load(WPF, allow_pickle=True); ts = z["ts"].astype(np.int64); Y = z["Y"].astype(np.float64)
    MEM = z["MEMBER"].astype(bool); DV = z["DVOL30"].astype(np.float64); dd = days_ms(ts); T, N = Y.shape
    fac = -np.log(np.where(DV > 0, DV, np.nan)); Z = np.zeros((T, N))
    for t in range(T):
        v = MEM[t] & np.isfinite(fac[t]) & np.isfinite(Y[t])
        if v.sum() >= 8:
            f = fac[t, v]; Z[t, np.where(v)[0]] = (f - f.mean()) / (f.std() + 1e-12)
    g0 = np.nansum((Z / (np.abs(Z).sum(1, keepdims=True) + 1e-12)) * np.nan_to_num(Y), axis=1)
    if np.nanmean(g0) < 0:
        Z = -Z
    tier = np.zeros((T, N), np.int8)
    for t in range(T):
        v = MEM[t] & np.isfinite(DV[t])
        if v.sum() >= 8:
            q = np.argsort(np.argsort(-DV[t, v])); nv = v.sum(); tier[t, np.where(v)[0]] = np.where(q < nv / 3, 0, np.where(q < 2 * nv / 3, 1, 2))
    s = np.abs(Z).sum(1, keepdims=True); W = np.where(s > 0, Z / s, 0.0)
    gross = np.nansum(W * np.nan_to_num(Y), axis=1); dW = np.abs(np.diff(W, axis=0, prepend=0.0)); tb = np.array([2.0, 5.0, 10.0]) / 1e4
    net = gross - (dW * tb[tier]).sum(1); dser = {}
    for i in range(T):
        if np.isfinite(net[i]) and np.abs(W[i]).sum() > 0:
            dser[dd[i]] = dser.get(dd[i], 0.0) + net[i]
    return pd.Series(dser).sort_index()


def leg_dl_or_s2(dir_tag, panel_ref, king_from_kp, cost):
    """4h king from king_pred_panel OR 24h S2 from its fold scores → daily net rank-L/S."""
    if king_from_kp:
        kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
        P = kp["king_pred"].astype(np.float64); member = kp["member"].astype(bool); CL = kp["CL"].astype(bool)
        Yraw = kp["Yraw"].astype(np.float64); ts = kp["ts"].astype(np.int64)
    else:
        pr = np.load(panel_ref + "/panel_ref.npz", allow_pickle=True)
        member = pr["member"].astype(bool); CL = pr["CL"].astype(bool); YR = pr["YR"].astype(np.float64)
        Yraw = pr["Yraw"].astype(np.float64); ts = pr["ts"].astype(np.int64); T, N = Yraw.shape
        P = np.full((T, N), np.nan)
        for f in sorted(glob.glob(panel_ref + "/fold_*_head_scores.npz")):
            C = comp_panel(np.load(f)["scores"], member, CL, YR); m = np.isfinite(C); P[m] = C[m]
    dd = days_ms(ts); rows = np.sort(np.where(np.isfinite(P).any(1))[0]); S = P.shape[1]; prev = np.zeros(S); dser = {}
    for t in rows:
        v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]))[0]
        if v.size < 10:
            continue
        w = np.zeros(S); w[v] = rank_weights(P[t, v]); g = float((w * np.nan_to_num(Yraw[t])).sum()); tn = np.abs(w - prev).sum()
        dser[dd[t]] = dser.get(dd[t], 0.0) + g - tn * cost * 1e-4; prev = w
    return pd.Series(dser).sort_index()


if __name__ == "__main__":
    funding = leg_funding(); size = leg_size()
    king = leg_dl_or_s2(None, None, True, 5.0)
    s2 = leg_dl_or_s2(TR + "wideA_s2_y24_5yr", None, False, 5.0)
    for nm, s in [("funding", funding), ("king", king), ("size", size), ("s2", s2)]:
        print(f"{nm}: {len(s)}d {s.index.min().date()}..{s.index.max().date()} Sh {sh(s):.2f}", flush=True)

    J = pd.concat([funding, king, size, s2], axis=1, join="inner").dropna(); J.columns = ["funding", "king", "size", "s2"]
    corr = J.corr().round(3).to_dict()
    Jn = J / J.std()
    print(f"JOINT {J.index.min().date()}..{J.index.max().date()} n={len(J)}", flush=True)

    def port(weights):
        w = np.array([weights[c] for c in J.columns]); p = pd.Series((Jn.values * w).sum(1), index=Jn.index)
        wyv, wyid = wy(p); return dict(weights={c: round(weights[c], 3) for c in J.columns}, sharpe=round(sh(p), 2),
            worst_month=wm(p), worst_year=wyv, worst_year_id=wyid,
            per_year={int(y): round(sh(g), 2) for y, g in p.groupby(p.index.year)})

    three = {"funding": 1/3, "king": 1/3, "size": 1/3, "s2": 0.0}
    ports = dict(three_leg_equalrisk=port(three))
    for ws2 in (0.05, 0.10, 0.15):
        rest = (1 - ws2) / 3
        ports[f"four_leg_s2w{ws2}"] = port({"funding": rest, "king": rest, "size": rest, "s2": ws2})
    # inverse-vol 4-leg
    iv = {c: 1 / J[c].std() for c in J.columns}; sv = sum(iv.values()); ports["four_leg_invvol"] = port({c: iv[c] / sv for c in J.columns})

    res = dict(title="4-leg book assembly (funding/DL-king/SIZE/S2-24h)", created="2026-07-14", auditor="0C",
               leg_full_sharpe={nm: round(sh(s), 2) for nm, s in [("funding", funding), ("king", king), ("size", size), ("s2", s2)]},
               joint=[str(J.index.min().date()), str(J.index.max().date()), int(len(J))],
               pairwise_corr=corr, s2_king_corr=round(float(J["s2"].corr(J["king"])), 3),
               s2_size_corr=round(float(J["s2"].corr(J["size"])), 3), portfolios=ports)
    json.dump(res, open(EDA + "book_assembly_4leg_raw.json", "w"), indent=2, default=str)
    print(f"\ncorr s2↔king {res['s2_king_corr']} s2↔size {res['s2_size_corr']}", flush=True)
    for k, p in ports.items():
        print(f"{k}: Sh {p['sharpe']} worstMo {p['worst_month']} worstYr {p['worst_year']}({p['worst_year_id']}) 2026 {p['per_year'].get(2026)}", flush=True)
    print("SAVED " + EDA + "book_assembly_4leg_raw.json", flush=True)

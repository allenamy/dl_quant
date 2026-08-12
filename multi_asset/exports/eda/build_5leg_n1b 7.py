"""0C — 5-LEG book test: does the N1b (4h multi-rel) sleeve improve the accepted 4-leg book?
N1b is 4h = SAME horizon/execution as king (the S1 situation). DAILY frequency (4-leg caliber, ANN sqrt365).
improve-rule + blend bootstrap + n1b<->king book-corr (S1 analog). CPU-only. Writes book_assembly_5leg_n1b_raw.json.
"""
import sys, numpy as np, pandas as pd, json, glob
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from scipy.stats import rankdata
from multi_asset.data.megacap_funding_replay import build_panel, HOUR_MS
TR = "multi_asset/exports/train/"; EDA = "multi_asset/exports/eda/"; WPF = "multi_asset/exports/wide_panel_full.npz"
ANN = np.sqrt(365.0); RNG = np.random.default_rng(0)


def days_ms(ts): return pd.to_datetime(np.asarray(ts).astype(np.int64), unit="ms", utc=True).floor("D")
def rank_weights(sc):
    r = sc.argsort().argsort().astype(np.float64); r = r - r.mean(); s = np.abs(r).sum()
    return r / s * 2.0 if s > 0 else r
def comp_panel(scores, member, CL, YR):
    T, N, K = scores.shape; C = np.full((T, N), np.nan)
    for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
        if base.size < 5: continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12: comp += (col - col.mean()) / col.std(); nk += 1
        if nk: C[t, base] = comp / nk
    return C
def sh(s): s = np.asarray(s); return float(s.mean() / s.std() * ANN) if s.std() > 0 else np.nan
def wm(s): m = s.groupby(s.index.to_period("M")).sum(); return round(float(m.min()), 4)


def leg_funding(cost=2.0):
    grid, syms, CLOSE, FUND = build_panel()
    logc = np.log(np.where(CLOSE > 0, CLOSE, np.nan)); Y = np.full_like(logc, np.nan); Y[:-1] = logc[1:] - logc[:-1]
    gap = np.zeros(len(grid), bool); gap[:-1] = (grid[1:] - grid[:-1]) > 2 * HOUR_MS; Y[gap] = np.nan
    dd = days_ms(grid); N = FUND.shape[1]; dser = {}; prev = np.zeros(N)
    for i in range(len(grid)):
        v = np.where(np.isfinite(FUND[i]) & np.isfinite(Y[i]))[0]
        if v.size < 5: continue
        f = -FUND[i, v]; z = (f - f.mean()) / (f.std() + 1e-12); z -= z.mean(); W = np.zeros(N); s = np.abs(z).sum()
        if s > 0: W[v] = z / s
        g = float(np.nansum(W * np.nan_to_num(Y[i]))); tn = np.abs(W - prev).sum()
        dser[dd[i]] = dser.get(dd[i], 0.0) + g - tn * cost * 1e-4; prev = W
    return pd.Series(dser).sort_index()


def leg_size():
    z = np.load(WPF, allow_pickle=True); ts = z["ts"].astype(np.int64); Y = z["Y"].astype(np.float64)
    MEM = z["MEMBER"].astype(bool); DV = z["DVOL30"].astype(np.float64); dd = days_ms(ts); T, N = Y.shape
    fac = -np.log(np.where(DV > 0, DV, np.nan)); Z = np.zeros((T, N))
    for t in range(T):
        v = MEM[t] & np.isfinite(fac[t]) & np.isfinite(Y[t])
        if v.sum() >= 8: f = fac[t, v]; Z[t, np.where(v)[0]] = (f - f.mean()) / (f.std() + 1e-12)
    g0 = np.nansum((Z / (np.abs(Z).sum(1, keepdims=True) + 1e-12)) * np.nan_to_num(Y), axis=1)
    if np.nanmean(g0) < 0: Z = -Z
    tier = np.zeros((T, N), np.int8)
    for t in range(T):
        v = MEM[t] & np.isfinite(DV[t])
        if v.sum() >= 8:
            q = np.argsort(np.argsort(-DV[t, v])); nv = v.sum(); tier[t, np.where(v)[0]] = np.where(q < nv / 3, 0, np.where(q < 2 * nv / 3, 1, 2))
    s = np.abs(Z).sum(1, keepdims=True); W = np.where(s > 0, Z / s, 0.0)
    gross = np.nansum(W * np.nan_to_num(Y), axis=1); dW = np.abs(np.diff(W, axis=0, prepend=0.0)); tb = np.array([2.0, 5.0, 10.0]) / 1e4
    net = gross - (dW * tb[tier]).sum(1); dser = {}
    for i in range(T):
        if np.isfinite(net[i]) and np.abs(W[i]).sum() > 0: dser[dd[i]] = dser.get(dd[i], 0.0) + net[i]
    return pd.Series(dser).sort_index()


def leg_dl(dir_tag, king_from_kp, cost):
    if king_from_kp:
        kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
        P = kp["king_pred"].astype(np.float64); member = kp["member"].astype(bool); CL = kp["CL"].astype(bool)
        Yraw = kp["Yraw"].astype(np.float64); ts = kp["ts"].astype(np.int64)
    else:
        pr = np.load(dir_tag + "/panel_ref.npz", allow_pickle=True)
        member = pr["member"].astype(bool); CL = pr["CL"].astype(bool); YR = pr["YR"].astype(np.float64)
        Yraw = pr["Yraw"].astype(np.float64); ts = pr["ts"].astype(np.int64); T, N = Yraw.shape
        P = np.full((T, N), np.nan)
        for f in sorted(glob.glob(dir_tag + "/fold_*_head_scores.npz")):
            C = comp_panel(np.load(f)["scores"], member, CL, YR); m = np.isfinite(C); P[m] = C[m]
    dd = days_ms(ts); rows = np.sort(np.where(np.isfinite(P).any(1))[0]); S = P.shape[1]; prev = np.zeros(S); dser = {}
    for t in rows:
        v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]))[0]
        if v.size < 10: continue
        w = np.zeros(S); w[v] = rank_weights(P[t, v]); g = float((w * np.nan_to_num(Yraw[t])).sum()); tn = np.abs(w - prev).sum()
        dser[dd[t]] = dser.get(dd[t], 0.0) + g - tn * cost * 1e-4; prev = w
    return pd.Series(dser).sort_index()


if __name__ == "__main__":
    funding = leg_funding(); size = leg_size()
    king = leg_dl(None, True, 5.0); s2 = leg_dl(TR + "wideA_s2_y24_5yr", False, 5.0)
    n1b = leg_dl(TR + "wideA_n1b_multirel_c1", False, 5.0)
    for nm, s in [("funding", funding), ("king", king), ("size", size), ("s2", s2), ("n1b", n1b)]:
        print(f"{nm}: {len(s)}d Sh {sh(s):.2f}", flush=True)

    J = pd.concat([funding, king, size, s2, n1b], axis=1, join="inner").dropna(); J.columns = ["funding", "king", "size", "s2", "n1b"]
    Jn = J / J.std(); yy = J.index.year
    corr = J.corr().round(3).to_dict()
    # accepted 4-leg book = funding/king/size 0.30 each + s2 0.10
    four = 0.30 * Jn["funding"] + 0.30 * Jn["king"] + 0.30 * Jn["size"] + 0.10 * Jn["s2"]
    n1bz = Jn["n1b"]
    rho = float(pd.concat([four, n1bz], axis=1).corr().iloc[0, 1])
    n1b_king_corr = round(float(J["n1b"].corr(J["king"])), 3)
    S4 = sh(four); Sn = sh(n1bz)
    print(f"\nJOINT {J.index.min().date()}..{J.index.max().date()} n={len(J)}", flush=True)
    print(f"n1b<->king book-corr {n1b_king_corr} | n1b<->4leg {rho:.3f} | S4 {S4:.2f} Sn1b {Sn:.2f} rho*S4 {rho*S4:.2f} improve {Sn>rho*S4}", flush=True)

    def peryear(series): return {int(y): round(sh(series.values[yy == y]), 2) for y in sorted(set(yy))}
    blends = {}
    for w in (0.05, 0.10, 0.15, 0.20):
        comb = (1 - w) * four + w * n1bz; base = four.values; cb = comb.values; idx = np.arange(len(cb))
        bt = np.array([sh(cb[bi := RNG.choice(idx, len(idx), True)]) - sh(base[bi]) for _ in range(3000)])
        blends[f"w{w}"] = dict(sharpe=round(sh(comb), 3), uplift=round(sh(comb) - S4, 3),
                               ci95=[round(float(np.percentile(bt, 2.5)), 3), round(float(np.percentile(bt, 97.5)), 3)],
                               sig=bool(np.percentile(bt, 2.5) > 0), worst_month=wm(comb), per_year=peryear(comb))
        print(f"[w{w}] 5leg Sh {sh(comb):.3f} uplift {sh(comb)-S4:+.3f} sig{np.percentile(bt,2.5)>0} CI[{np.percentile(bt,2.5):.3f},{np.percentile(bt,97.5):.3f}] worstMo {wm(comb)}", flush=True)

    res = dict(title="5-leg book test (N1b-4h multi-rel sleeve vs accepted 4-leg)", created="2026-07-15", auditor="0C",
               freq="daily", joint=[str(J.index.min().date()), str(J.index.max().date()), int(len(J))],
               leg_sharpe={c: round(sh(J[c]), 2) for c in J.columns}, pairwise_corr=corr,
               n1b_king_book_corr=n1b_king_corr, n1b_four_corr=round(rho, 3),
               four_leg_sharpe=round(S4, 2), n1b_sharpe=round(Sn, 2), rho_S4=round(rho * S4, 2),
               improve_rule=bool(Sn > rho * S4), blends=blends, four_leg_per_year=peryear(four))
    json.dump(res, open(EDA + "book_assembly_5leg_n1b_raw.json", "w"), indent=2, default=str)
    print("SAVED " + EDA + "book_assembly_5leg_n1b_raw.json", flush=True)

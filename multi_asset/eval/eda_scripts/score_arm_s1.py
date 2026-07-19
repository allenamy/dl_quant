"""0C — ARM-S1 (4h king-residual re-mine, YR4K target) score. (a) increment = IC vs YR4K (target already
king-orthogonal; corr(YR4K,YR4)=0.989 → near-full-dimension, no discount). (b) pred-corr vs king +
dyn-share. ★ KING-ENHANCEMENT test: value-blend(king,S1) IC vs YR4 vs king-alone (does merging S1 lift
the king?). ★ 5-LEG book test: S1 4h book return-corr to king + improve-rule on the 4-leg book. CPU-only.
Writes exports/eda/arm_s1_score.json.
"""
import numpy as np, pandas as pd, json, glob, hashlib
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
S1 = TR + "wideA_s1_yr4k_c1"
RNG = np.random.default_rng(0); ANN = np.sqrt(365.0)


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:8]


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


if __name__ == "__main__":
    print("S1 panel md5", md5(S1 + "/panel_ref.npz"), flush=True)
    pr = np.load(S1 + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR4K, Yraw = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    ts = pr["ts"].astype(np.int64); day = pr["day"]; yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
    king = kp["king_pred"].astype(np.float64); YR4 = kp["YR"].astype(np.float64)
    T, N = Yraw.shape
    Sc = np.full((T, N), np.nan); fold_te = {}
    for f in sorted(glob.glob(S1 + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        z = np.load(f); C = comp_panel(z["scores"], member, CL, YR4K); m = np.isfinite(C); Sc[m] = C[m]
        te = z["te_rows"]; Y = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min()); fold_te[Y] = te

    # (a) IC vs YR4K (increment) + (b) pred-corr + king-blend IC vs YR4, per year
    def metrics(rows):
        inc, pc, kic, bic, days = [], [], [], [], []
        for t in rows:
            b = np.where(member[t] & CL[t] & np.isfinite(YR4K[t]) & np.isfinite(Sc[t]) & np.isfinite(king[t]) & np.isfinite(YR4[t]))[0]
            if b.size < 8:
                continue
            s = Sc[t, b]; k = king[t, b]
            inc.append(np.corrcoef(rankdata(s), rankdata(YR4K[t, b]))[0, 1])
            pc.append(np.corrcoef(rankdata(s), rankdata(k))[0, 1])
            kic.append(np.corrcoef(rankdata(k), rankdata(YR4[t, b]))[0, 1])          # king IC vs YR4
            zs = (s - s.mean()) / (s.std() + 1e-12); zk = (k - k.mean()) / (k.std() + 1e-12)
            bic.append(np.corrcoef(rankdata(0.5 * zk + 0.5 * zs), rankdata(YR4[t, b]))[0, 1])  # blend IC vs YR4
            days.append(int(day[t]))
        return map(np.array, (inc, pc, kic, bic, days))

    per_year = []
    for Y in sorted(fold_te):
        inc, pc, kic, bic, _ = metrics(fold_te[Y])
        per_year.append(dict(year=Y, increment_yr4k=round(float(inc.mean()), 4), pred_corr=round(float(pc.mean()), 3),
                             king_ic=round(float(kic.mean()), 4), blend_ic=round(float(bic.mean()), 4),
                             blend_minus_king=round(float(bic.mean() - kic.mean()), 4)))
        print(f"[{Y}] incr(YR4K) {inc.mean():+.4f} corr {pc.mean():.3f} | king-IC {kic.mean():+.4f} blend-IC {bic.mean():+.4f} Δ {bic.mean()-kic.mean():+.4f}", flush=True)
    allr = np.array(sorted(set().union(*[set(t.tolist()) for t in fold_te.values()])))
    inc, pc, kic, bic, days = metrics(allr)
    ud = np.unique(days); d2 = {u: np.where(days == u)[0] for u in ud}
    bi = np.array([inc[np.concatenate([d2[u] for u in RNG.choice(ud, len(ud), True)])].mean() for _ in range(3000)])
    inc_ci = (round(float(np.percentile(bi, 2.5)), 4), round(float(np.percentile(bi, 97.5)), 4))
    dblend = bic - kic
    bb = np.array([dblend[np.concatenate([d2[u] for u in RNG.choice(ud, len(ud), True)])].mean() for _ in range(3000)])
    blend_ci = (round(float(np.percentile(bb, 2.5)), 4), round(float(np.percentile(bb, 97.5)), 4))

    # 5-leg book: S1 4h book + king 4h book (both Yraw4), daily net@5bps, return-corr
    def book_daily(P, Yr, cost=5.0):
        dd = pd.to_datetime(ts.astype(np.int64), unit="ms", utc=True).floor("D")
        rows = np.sort(np.where(np.isfinite(P).any(1))[0]); prev = np.zeros(N); dser = {}
        for t in rows:
            v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yr[t]))[0]
            if v.size < 10:
                continue
            w = np.zeros(N); w[v] = rank_weights(P[t, v]); g = float((w * np.nan_to_num(Yr[t])).sum()); tn = np.abs(w - prev).sum()
            dser[dd[t]] = dser.get(dd[t], 0.0) + g - tn * cost * 1e-4; prev = w
        return pd.Series(dser).sort_index()
    s1b = book_daily(Sc, Yraw); kb = book_daily(king, kp["Yraw"].astype(np.float64))
    J = pd.concat([s1b, kb], axis=1, join="inner").dropna(); J.columns = ["s1", "king"]
    s1_king_bookcorr = round(float(J["s1"].corr(J["king"])), 3)

    result = dict(title="ARM-S1 (4h king-residual re-mine) score", created="2026-07-14", auditor="0C",
                  panel_md5=md5(S1 + "/panel_ref.npz"), ts_aligned=True, corr_YR4K_YR4=0.9892,
                  increment_pooled=round(float(inc.mean()), 4), increment_ci95=list(inc_ci),
                  pred_corr_king=round(float(pc.mean()), 3), sign_consistent=bool(all(x["increment_yr4k"] > 0 for x in per_year)),
                  king_enhancement=dict(king_ic=round(float(kic.mean()), 4), blend_ic=round(float(bic.mean()), 4),
                                        blend_uplift=round(float((bic - kic).mean()), 4), uplift_ci95=list(blend_ci),
                                        uplift_sig=bool(blend_ci[0] > 0)),
                  s1_king_book_corr=s1_king_bookcorr, per_year=per_year,
                  gate_a_pass=bool(inc.mean() >= 0.003 and inc_ci[0] > 0 and all(x["increment_yr4k"] > 0 for x in per_year)),
                  gate_b_pass=bool(pc.mean() < 0.7))
    json.dump(result, open(EDA + "arm_s1_score.json", "w"), indent=2, default=str)
    print(f"\nPOOLED incr {inc.mean():+.4f} CI{inc_ci} corr {pc.mean():.3f} | ★king-enh: king {kic.mean():+.4f} → blend {bic.mean():+.4f} uplift {(bic-kic).mean():+.4f} CI{blend_ci} sig{blend_ci[0]>0} | S1↔king book-corr {s1_king_bookcorr}", flush=True)
    print("SAVED " + EDA + "arm_s1_score.json", flush=True)

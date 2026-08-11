"""0C — xattn_5yr regime confirmation: per-year pairing xattn_5yr vs lamorth0_5yr (does the +41%
edge hold in WEAK years 2022/2026?) + dynamic share + vs QIM_5yr. day-block bootstrap. CPU-only.
Writes multi_asset/exports/eda/xattn_5yr_pairing.json.
"""
import numpy as np, pandas as pd, json, glob, hashlib
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
XA = TR + "wideA_lamorth0_xattn_5yr"
LAM = TR + "wideA_lamorth0_5yr"
QIM = TR + "wideA_qim_multiyear"
RNG = np.random.default_rng(0)
QIM_Y = {2022: 0.0443, 2023: 0.0640, 2024: 0.0697, 2025: 0.0807, 2026: 0.0774}


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:8]


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


def yr_of(te, ty):
    y = ty[te]; return int(np.bincount(y - y.min()).argmax() + y.min())


if __name__ == "__main__":
    print("md5 xattn_5yr", md5(XA + "/panel_ref.npz"), "lamorth0_5yr", md5(LAM + "/panel_ref.npz"), flush=True)
    pr = np.load(XA + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64)
    day = pr["day"]; ty = pd.to_datetime(pr["ts"].astype(np.int64), unit="ms", utc=True).year.to_numpy()
    xf = {yr_of(np.load(f)["te_rows"], ty): f for f in glob.glob(XA + "/fold_*_head_scores.npz")}
    lf = {yr_of(np.load(f)["te_rows"], ty): f for f in glob.glob(LAM + "/fold_*_head_scores.npz")}

    def ic_at(P, rows):
        ics, days = [], []
        for t in rows:
            base = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(P[t]))[0]
            if base.size < 5:
                continue
            ic = np.corrcoef(rankdata(P[t, base]), rankdata(YR[t, base]))[0, 1]
            if np.isfinite(ic):
                ics.append(ic); days.append(int(day[t]))
        return np.array(ics), np.array(days)

    def dynshare(P, rows, nshuf=20):
        idxs = []
        for t in rows:
            base = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(P[t]))[0]
            idxs.append(base if base.size >= 5 else None)
        val = [i for i in range(len(rows)) if idxs[i] is not None]
        tot = np.nanmean([np.corrcoef(rankdata(P[rows[i], idxs[i]]), rankdata(YR[rows[i], idxs[i]]))[0, 1] for i in val])
        Ps = P[rows]; sh = []
        for _ in range(nshuf):
            Cs = Ps.copy()
            for a in range(P.shape[1]):
                fin = np.where(np.isfinite(Cs[:, a]))[0]
                if fin.size > 1:
                    Cs[fin, a] = Cs[fin[RNG.permutation(fin.size)], a]
            sh.append(np.nanmean([np.corrcoef(rankdata(Cs[i, idxs[i]][np.isfinite(Cs[i, idxs[i]])]),
                      rankdata(YR[rows[i], idxs[i]][np.isfinite(Cs[i, idxs[i]])]))[0, 1]
                      for i in val if np.isfinite(Cs[i, idxs[i]]).sum() >= 5]))
        return round((float(tot) - np.nanmean(sh)) / tot, 3)

    rows = []
    for Y in sorted(xf):
        Cx = comp_panel(np.load(xf[Y])["scores"], member, CL, YR)
        Cl = comp_panel(np.load(lf[Y])["scores"], member, CL, YR)
        r = np.where(np.isfinite(Cx).any(1) & np.isfinite(Cl).any(1))[0]
        icx, dx = ic_at(Cx, r); icl, _ = ic_at(Cl, r)
        d = icx - icl; ud = np.unique(dx); d2 = {u: np.where(dx == u)[0] for u in ud}
        boot = np.array([d[np.concatenate([d2[u] for u in RNG.choice(ud, len(ud), True)])].mean() for _ in range(3000)])
        ci = (round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4))
        rows.append(dict(year=Y, xattn_ic=round(float(icx.mean()), 4), lamorth0_ic=round(float(icl.mean()), 4),
                         qim_ic=QIM_Y.get(Y), delta_vs_lamorth0=round(float(d.mean()), 4), ci95=list(ci),
                         sig_positive=bool(ci[0] > 0), sig_negative=bool(ci[1] < 0), dyn_share=dynshare(Cx, r)))
        print(f"[{Y}] xattn {icx.mean():+.4f} lamorth0 {icl.mean():+.4f} QIM {QIM_Y.get(Y):+.4f} | "
              f"Δvs_lam {d.mean():+.4f} CI{ci} sig+={rows[-1]['sig_positive']} dyn={rows[-1]['dyn_share']}", flush=True)
    xm = round(float(np.mean([r["xattn_ic"] for r in rows])), 4)
    lm = round(float(np.mean([r["lamorth0_ic"] for r in rows])), 4)
    weak = [r for r in rows if r["year"] in (2022, 2026)]
    holds_weak = all(r["sig_positive"] for r in weak)
    res = dict(title="xattn_5yr regime confirmation", created="2026-07-12", auditor="0C",
               panel_md5=md5(XA + "/panel_ref.npz"), per_year=rows, xattn_mean=xm, lamorth0_mean=lm,
               mean_delta=round(xm - lm, 4),
               weak_year_edge_holds=holds_weak,
               verdict=("REGIME-ROBUST paradigm upgrade" if holds_weak else
                        "STRONG-REGIME-ONLY lever (weak-year edge not significant)"))
    json.dump(res, open(EDA + "xattn_5yr_pairing.json", "w"), indent=2, default=str)
    print(f"\nxattn 5yr mean {xm} vs lamorth0 {lm} (Δ {xm-lm:+.4f}); weak-year(2022/2026) edge holds={holds_weak}", flush=True)
    print("SAVED " + EDA + "xattn_5yr_pairing.json", flush=True)

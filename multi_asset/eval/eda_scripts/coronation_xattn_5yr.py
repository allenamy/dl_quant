"""0C — xattn_5yr CORONATION verdict: per-year pairing (vs lamorth0 & QIM, day-block bootstrap, focus
weak years 2022/2026) + per-year dynamic/static (esp 2025) + net-cost RECOMPUTED for the xattn book
(turnover may differ from QIM) + 3-way blend (QIM+lamorth0+xattn) + 2025 too-good deep look. CPU-only.
Writes multi_asset/exports/eda/xattn_5yr_coronation.json.
"""
import numpy as np, pandas as pd, json, glob, hashlib
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
X = TR + "wideA_lamorth0_xattn_5yr"; L = TR + "wideA_lamorth0_5yr"; Q = TR + "wideA_qim_multiyear"
RNG = np.random.default_rng(0)
H = 4; PER_YR = 365 * 24 / H; ANN = np.sqrt(PER_YR)


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


def rank_weights(sc):
    r = sc.argsort().argsort().astype(np.float64); r = r - r.mean(); s = np.abs(r).sum()
    return r / s * 2.0 if s > 0 else r


def yr_of(te, ty):
    y = ty[te]; return int(np.bincount(y - y.min()).argmax() + y.min())


if __name__ == "__main__":
    print("md5:", md5(X + "/panel_ref.npz"), md5(L + "/panel_ref.npz"), md5(Q + "/panel_ref.npz"), flush=True)
    pr = np.load(X + "/panel_ref.npz", allow_pickle=True)
    member, CL = pr["member"].astype(bool), pr["CL"].astype(bool)
    YR, Yraw = pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    day = pr["day"]; ty = pd.to_datetime(pr["ts"].astype(np.int64), unit="ms", utc=True).year.to_numpy()
    xf = {yr_of(np.load(f)["te_rows"], ty): f for f in glob.glob(X + "/fold_*_head_scores.npz")}
    lf = {yr_of(np.load(f)["te_rows"], ty): f for f in glob.glob(L + "/fold_*_head_scores.npz")}
    qf = {yr_of(np.load(f)["te_rows"], ty): f for f in glob.glob(Q + "/fold_*_head_scores.npz")}

    def ic_at(P, rows):
        ics, days = [], []
        for t in rows:
            b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(P[t]))[0]
            if b.size < 5:
                continue
            ic = np.corrcoef(rankdata(P[t, b]), rankdata(YR[t, b]))[0, 1]
            if np.isfinite(ic):
                ics.append(ic); days.append(int(day[t]))
        return np.array(ics), np.array(days)

    def boot_ci(d, days):
        ud = np.unique(days); d2 = {u: np.where(days == u)[0] for u in ud}
        b = np.array([d[np.concatenate([d2[u] for u in RNG.choice(ud, len(ud), True)])].mean() for _ in range(3000)])
        return round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)

    def dyn_static(P, rows, nshuf=25):
        idxs = [np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(P[t]))[0] for t in rows]
        idxs = [b if b.size >= 5 else None for b in idxs]
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
        st = float(np.nanmean(sh))
        return round(float(tot), 4), round(st, 4), round((float(tot) - st) / tot, 3)

    def book(P, rows, costs=(0.0, 2.3, 5.0, 9.5)):
        g, tn, prevw = [], [], np.zeros(P.shape[1])
        for t in rows:
            v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]))[0]
            if v.size < 10:
                continue
            w = np.zeros(P.shape[1]); w[v] = rank_weights(P[t, v])
            g.append(float((w * np.nan_to_num(Yraw[t])).sum())); tn.append(float(np.abs(w - prevw).sum())); prevw = w
        g, tn = np.array(g), np.array(tn)
        o = dict(turnover=round(float(tn.mean()), 3), be_bps=round(float(g.mean() / tn.mean() * 1e4), 2))
        for c in costs:
            net = g - tn * (c * 1e-4)
            o[f"nSh{c}"] = round(float(net.mean() / net.std() * ANN), 2) if net.std() > 0 else None
        return o

    per_year = []
    for Y in sorted(xf):
        Cx = comp_panel(np.load(xf[Y])["scores"], member, CL, YR)
        Cl = comp_panel(np.load(lf[Y])["scores"], member, CL, YR)
        Cq = comp_panel(np.load(qf[Y])["scores"], member, CL, YR)
        r = np.sort(np.where(np.isfinite(Cx).any(1) & np.isfinite(Cl).any(1) & np.isfinite(Cq).any(1))[0])
        icx, dx = ic_at(Cx, r); icl, _ = ic_at(Cl, r); icq, _ = ic_at(Cq, r)
        # align rows for pairing (ic_at uses same base def, same r -> same order)
        dl = icx - icl; dq = icx - icq
        ci_l = boot_ci(dl, dx); ci_q = boot_ci(dq, dx)
        tot, st, dyn = dyn_static(Cx, r)
        # 3-way blend
        B = np.full_like(Cx, np.nan)
        for t in r:
            b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(Cx[t]) & np.isfinite(Cl[t]) & np.isfinite(Cq[t]))[0]
            if b.size < 5:
                continue
            zx = (Cx[t, b] - Cx[t, b].mean()) / (Cx[t, b].std() + 1e-12)
            zl = (Cl[t, b] - Cl[t, b].mean()) / (Cl[t, b].std() + 1e-12)
            zq = (Cq[t, b] - Cq[t, b].mean()) / (Cq[t, b].std() + 1e-12)
            B[t, b] = (zx + zl + zq) / 3
        icb, _ = ic_at(B, r)
        # net-cost xattn vs QIM book
        bk_x = book(Cx, r); bk_q = book(Cq, r)
        per_year.append(dict(
            year=Y, xattn_ic=round(float(icx.mean()), 4), lamorth0_ic=round(float(icl.mean()), 4),
            qim_ic=round(float(icq.mean()), 4), blend3_ic=round(float(icb.mean()), 4),
            d_vs_lam=round(float(dl.mean()), 4), ci_vs_lam=list(ci_l), sig_vs_lam=bool(ci_l[0] > 0),
            d_vs_qim=round(float(dq.mean()), 4), ci_vs_qim=list(ci_q), sig_vs_qim=bool(ci_q[0] > 0),
            dyn_total=tot, static_shuffle=st, dyn_share=dyn,
            xattn_book=bk_x, qim_book=bk_q))
        print(f"[{Y}] xattn {icx.mean():+.4f} lam {icl.mean():+.4f} qim {icq.mean():+.4f} blend3 {icb.mean():+.4f} "
              f"| Δlam {dl.mean():+.4f}{ci_l} sig={ci_l[0]>0} | dyn {dyn} | turn x{bk_x['turnover']}/q{bk_q['turnover']} "
              f"BE x{bk_x['be_bps']}/q{bk_q['be_bps']} nSh@5 x{bk_x['nSh5.0']}/q{bk_q['nSh5.0']}", flush=True)

    weak = [r for r in per_year if r["year"] in (2022, 2026)]
    holds = all(r["sig_vs_lam"] for r in weak)
    res = dict(title="xattn_5yr coronation verdict", created="2026-07-12", auditor="0C",
               panel_md5_allthree=md5(X + "/panel_ref.npz"), per_year=per_year,
               xattn_mean=round(float(np.mean([r["xattn_ic"] for r in per_year])), 4),
               lamorth0_mean=round(float(np.mean([r["lamorth0_ic"] for r in per_year])), 4),
               qim_mean=round(float(np.mean([r["qim_ic"] for r in per_year])), 4),
               blend3_mean=round(float(np.mean([r["blend3_ic"] for r in per_year])), 4),
               weak_year_edge_holds=holds,
               dyn_share_mean=round(float(np.mean([r["dyn_share"] for r in per_year])), 3))
    json.dump(res, open(EDA + "xattn_5yr_coronation.json", "w"), indent=2, default=str)
    print(f"\nMEANS xattn {res['xattn_mean']} lam {res['lamorth0_mean']} qim {res['qim_mean']} "
          f"blend3 {res['blend3_mean']} | weak-holds {holds} | dyn {res['dyn_share_mean']}", flush=True)
    print("SAVED " + EDA + "xattn_5yr_coronation.json", flush=True)

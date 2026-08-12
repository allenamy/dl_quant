"""0C — QIM + lamorth0_5yr DOUBLE-IMPLEMENTATION blend scoring (CPU-only, no GPU).
Two mechanism-equivalent implementations (pred corr 0.63) = diversity pair. Value-blend (lesson #16:
value not rank), per-year ensemble resid IC + dynamic share + paired Δ vs single QIM (day-block boot)
+ net-cost/turnover vs single QIM. Pre-registered: blend mean >= QIM +0.003 AND no year sig-worse ->
"deployment-level consideration"; else "single impl sufficient, archive". Output is a SCORECARD for the
user's decision (post-training combo; user policy = production-phase, grounded + not val-fit).
Writes multi_asset/exports/eda/qim_blend_score.json.
"""
import numpy as np, pandas as pd, json, glob
from scipy.stats import rankdata

TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
QIM = TR + "wideA_qim_multiyear"
LAM = TR + "wideA_lamorth0_5yr"
RNG = np.random.default_rng(0)
H = 4; PER_YR = 365 * 24 / H; ANN = np.sqrt(PER_YR)


def comp_panel(scores, member, CL, YR):
    T, N, K = scores.shape
    C = np.full((T, N), np.nan)
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
    r = sc.argsort().argsort().astype(np.float64); r = r - r.mean()
    s = np.abs(r).sum(); return r / s * 2.0 if s > 0 else r


def year_of(te, ts_year):
    y = ts_year[te]; return int(np.bincount(y - y.min()).argmax() + y.min())


def book(P, member, CL, Yraw, costs=(0.0, 2.3, 5.0)):
    """4h rank-L/S full-turnover on Yraw. Returns BE, turnover, netSharpe per cost."""
    rows = np.sort(np.where(np.isfinite(P).any(1))[0]); S = P.shape[1]
    g = []; tn = []; prevw = np.zeros(S)
    for t in rows:
        v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]))[0]
        if v.size < 10:
            continue
        w = np.zeros(S); w[v] = rank_weights(P[t, v])
        g.append(float((w * np.nan_to_num(Yraw[t])).sum())); tn.append(float(np.abs(w - prevw).sum())); prevw = w
    g = np.array(g); tn = np.array(tn)
    out = dict(turnover=round(float(tn.mean()), 3), gross_bps=round(float(g.mean() * 1e4), 3),
               be_bps=round(float(g.mean() / tn.mean() * 1e4), 2) if tn.mean() > 0 else None)
    for c in costs:
        net = g - tn * (c * 1e-4)
        out[f"netSh_c{c}"] = round(float(net.mean() / net.std() * ANN), 2) if net.std() > 0 else None
    return out


if __name__ == "__main__":
    pr = np.load(QIM + "/panel_ref.npz", allow_pickle=True)
    member, CL = pr["member"].astype(bool), pr["CL"].astype(bool)
    YR, Yraw = pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    day = pr["day"]; ts_year = pd.to_datetime(pr["ts"].astype(np.int64), unit="ms", utc=True).year.to_numpy()
    qf = {year_of(np.load(f)["te_rows"], ts_year): f for f in glob.glob(QIM + "/fold_*_head_scores.npz")}
    lf = {year_of(np.load(f)["te_rows"], ts_year): f for f in glob.glob(LAM + "/fold_*_head_scores.npz")}

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

    def dyn_share(P, rows, nshuf=20):
        idxs, yr = [], []
        for t in rows:
            base = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(P[t]))[0]
            idxs.append(base if base.size >= 5 else None)
            yr.append(rankdata(YR[t, base]) if base.size >= 5 else None)
        val = [i for i in range(len(rows)) if idxs[i] is not None]
        tot = np.nanmean([np.corrcoef(rankdata(P[rows[i], idxs[i]]), yr[i])[0, 1] for i in val])
        Psub = P[rows]; sh = []
        for _ in range(nshuf):
            Cs = Psub.copy()
            for a in range(P.shape[1]):
                fin = np.where(np.isfinite(Cs[:, a]))[0]
                if fin.size > 1:
                    Cs[fin, a] = Cs[fin[RNG.permutation(fin.size)], a]
            rep = [np.corrcoef(rankdata(Cs[i, idxs[i]][np.isfinite(Cs[i, idxs[i]])]),
                               rankdata(YR[rows[i], idxs[i]][np.isfinite(Cs[i, idxs[i]])]))[0, 1]
                   for i in val if np.isfinite(Cs[i, idxs[i]]).sum() >= 5]
            sh.append(np.nanmean(rep))
        return float(tot), float(tot - np.nanmean(sh))

    per_year = []
    for Y in sorted(qf):
        zq = np.load(qf[Y]); zl = np.load(lf[Y])
        Cq = comp_panel(zq["scores"], member, CL, YR)
        Cl = comp_panel(zl["scores"], member, CL, YR)
        te = np.array(sorted(set(zq["te_rows"].tolist()) & set(zl["te_rows"].tolist())))
        B = np.full_like(Cq, np.nan)
        for t in te:
            base = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(Cq[t]) & np.isfinite(Cl[t]))[0]
            if base.size < 5:
                continue
            zqv = (Cq[t, base] - Cq[t, base].mean()) / (Cq[t, base].std() + 1e-12)
            zlv = (Cl[t, base] - Cl[t, base].mean()) / (Cl[t, base].std() + 1e-12)
            B[t, base] = 0.5 * zqv + 0.5 * zlv
        rows = np.where(np.isfinite(B).any(1))[0]
        icb, db = ic_at(B, rows); icq, dq = ic_at(Cq, rows)
        # paired Δ blend - qim, day-block bootstrap (align by matching rows -> icb & icq computed on same rows)
        d = icb - icq
        uday = np.unique(db); d2 = {u: np.where(db == u)[0] for u in uday}
        boot = np.array([d[np.concatenate([d2[u] for u in RNG.choice(uday, len(uday), True)])].mean()
                         for _ in range(3000)])
        ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
        tot, dyn = dyn_share(B, rows)
        bk_b = book(B, member, CL, Yraw); bk_q = book(Cq, member, CL, Yraw)
        per_year.append(dict(
            year=Y, blend_ic=round(float(icb.mean()), 4), qim_ic=round(float(icq.mean()), 4),
            delta=round(float(d.mean()), 4), delta_ci95=[round(ci[0], 4), round(ci[1], 4)],
            sig_worse=bool(ci[1] < 0), sig_better=bool(ci[0] > 0),
            dyn_share=round(dyn / tot, 3) if tot else None,
            blend_book=bk_b, qim_book=bk_q))
        print(f"[{Y}] blend {icb.mean():+.4f} vs QIM {icq.mean():+.4f} d={d.mean():+.4f} "
              f"CI[{ci[0]:+.4f},{ci[1]:+.4f}] | turn blend {bk_b['turnover']} vs QIM {bk_q['turnover']} "
              f"| BE blend {bk_b['be_bps']} vs QIM {bk_q['be_bps']} netSh@5 {bk_b['netSh_c5.0']} vs {bk_q['netSh_c5.0']}", flush=True)

    bmean = round(float(np.mean([r["blend_ic"] for r in per_year])), 4)
    qmean = round(float(np.mean([r["qim_ic"] for r in per_year])), 4)
    any_worse = any(r["sig_worse"] for r in per_year)
    passed = (bmean >= qmean + 0.003) and (not any_worse)
    result = dict(
        title="QIM + lamorth0_5yr double-implementation blend scorecard", created="2026-07-12", auditor="0C",
        method="per-ts z-score each pred (value, not rank), 50/50 value-blend, xsec rank-IC vs YR; same panel md5 185d3b65",
        per_year=per_year, blend_mean=bmean, qim_mean=qmean, mean_uplift=round(bmean - qmean, 4),
        preregistered_criterion="blend mean >= QIM +0.003 AND no year significantly worse",
        any_year_sig_worse=any_worse, criterion_met=passed,
        verdict=("WORTH DEPLOYMENT-LEVEL CONSIDERATION" if passed else "SINGLE IMPLEMENTATION SUFFICIENT — ARCHIVE"),
        policy_note=("post-training combination; user policy = production-phase grounded+not-val-fit ok. This is a "
                     "SCORECARD for the user's decision, NOT auto-deploy. Diversity-pair rationale (pred corr 0.63) "
                     "is theoretically grounded (cf single-asset V4<->XGB 0.68); 50/50 fixed weight = not val-fit."))
    json.dump(result, open(EDA + "qim_blend_score.json", "w"), indent=2, default=str)
    print(f"\nBLEND mean {bmean} vs QIM {qmean} (uplift {bmean-qmean:+.4f}); crit_met={passed} -> {result['verdict']}", flush=True)
    print("SAVED " + EDA + "qim_blend_score.json", flush=True)

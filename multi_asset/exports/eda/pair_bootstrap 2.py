"""0C — lamorth0_5yr vs QIM per-year PAIRED significance (day-block bootstrap) + prediction similarity.
Same-panel (md5 185d3b65), same te_rows -> per-ts paired IC differences. CPU-only.
Writes multi_asset/exports/eda/lamorth0_5yr_pairing.json.
"""
import numpy as np, pandas as pd, json, glob
from scipy.stats import rankdata

TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
LAM = TR + "wideA_lamorth0_5yr"
QIM = TR + "wideA_qim_multiyear"
RNG = np.random.default_rng(0)


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


def year_of(fold_te_rows, ts_year):
    yrs = ts_year[fold_te_rows]
    return int(np.bincount(yrs - yrs.min()).argmax() + yrs.min())


if __name__ == "__main__":
    pr = np.load(QIM + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64)
    day = pr["day"]; ts_year = pd.to_datetime(pr["ts"].astype(np.int64), unit="ms", utc=True).year.to_numpy()

    qf = {year_of(np.load(f)["te_rows"], ts_year): f
          for f in glob.glob(QIM + "/fold_*_head_scores.npz")}
    lf = {year_of(np.load(f)["te_rows"], ts_year): f
          for f in glob.glob(LAM + "/fold_*_head_scores.npz")}

    per_year = []
    for Y in sorted(qf):
        zq = np.load(qf[Y]); zl = np.load(lf[Y])
        teq, tel = set(zq["te_rows"].tolist()), set(zl["te_rows"].tolist())
        te = np.array(sorted(teq & tel))
        Cq = comp_panel(zq["scores"], member, CL, YR)
        Cl = comp_panel(zl["scores"], member, CL, YR)
        icq, icl, dd, sim, days = [], [], [], [], []
        for t in te:
            base = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(Cq[t]) & np.isfinite(Cl[t]))[0]
            if base.size < 5:
                continue
            yr_r = rankdata(YR[t, base])
            a = np.corrcoef(rankdata(Cq[t, base]), yr_r)[0, 1]
            b = np.corrcoef(rankdata(Cl[t, base]), yr_r)[0, 1]
            if np.isfinite(a) and np.isfinite(b):
                icq.append(a); icl.append(b); dd.append(a - b); days.append(int(day[t]))
                s = np.corrcoef(rankdata(Cq[t, base]), rankdata(Cl[t, base]))[0, 1]
                if np.isfinite(s):
                    sim.append(s)
        icq, icl, dd, days = map(np.array, (icq, icl, dd, days))
        # day-block bootstrap of mean(d): resample unique days with replacement
        uday = np.unique(days); day_to = {d: np.where(days == d)[0] for d in uday}
        boot = np.empty(3000)
        for r in range(3000):
            pick = RNG.choice(uday, size=len(uday), replace=True)
            idx = np.concatenate([day_to[d] for d in pick])
            boot[r] = dd[idx].mean()
        ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
        p_gt0 = float((boot > 0).mean())   # bootstrap prob QIM>lamorth0
        per_year.append(dict(
            year=Y, n_ts=int(len(dd)), n_days=int(len(uday)),
            qim_ic=round(float(icq.mean()), 4), lamorth0_ic=round(float(icl.mean()), 4),
            mean_delta=round(float(dd.mean()), 4),
            delta_ci95=[round(ci[0], 4), round(ci[1], 4)], ci_excludes_0=bool(ci[0] > 0 or ci[1] < 0),
            boot_prob_qim_gt=round(p_gt0, 3), frac_ts_qim_gt=round(float((dd > 0).mean()), 3),
            pred_xsec_rankcorr=round(float(np.mean(sim)), 3)))
        print(f"[{Y}] QIM {icq.mean():+.4f} vs lamorth0 {icl.mean():+.4f}  d={dd.mean():+.4f} "
              f"CI95[{ci[0]:+.4f},{ci[1]:+.4f}] excl0={per_year[-1]['ci_excludes_0']} "
              f"predCorr={per_year[-1]['pred_xsec_rankcorr']}", flush=True)

    lam_mean = float(np.mean([r["lamorth0_ic"] for r in per_year]))
    qim_mean = float(np.mean([r["qim_ic"] for r in per_year]))
    # sign-flip check: does delta sign track raw-IC regime strength? (2024 raw is strongest)
    result = dict(
        title="lamorth0_5yr vs QIM 5yr per-year paired verdict", created="2026-07-12", auditor="0C",
        panel_md5="185d3b65 (both, byte-identical)", per_year=per_year,
        qim_5yr_mean=round(qim_mean, 4), lamorth0_5yr_mean=round(lam_mean, 4),
        mean_delta=round(qim_mean - lam_mean, 4),
        pred_similarity_mean=round(float(np.mean([r["pred_xsec_rankcorr"] for r in per_year])), 3))
    json.dump(result, open(EDA + "lamorth0_5yr_pairing.json", "w"), indent=2, default=str)
    print(f"\nMEAN QIM {qim_mean:+.4f} vs lamorth0 {lam_mean:+.4f} (Δ {qim_mean-lam_mean:+.4f}) "
          f"predSim {result['pred_similarity_mean']}", flush=True)
    print("SAVED " + EDA + "lamorth0_5yr_pairing.json", flush=True)

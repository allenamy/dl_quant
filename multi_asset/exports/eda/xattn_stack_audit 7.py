"""0C — lamorth0+xattn stack AUDIT (3-fold, 'too good' arm). Dynamic/static (shuffle-future) FIRST
(prime suspect = xattn static-tilt inflation), then reproduce ensemble IC, paired significance vs
lamorth0, fold boundaries. Same panel md5 39f5cc4e. CPU-only. Prints per-fold live so the GPU 5yr
run can be killed early if static-inflated. Writes multi_asset/exports/eda/xattn_stack_audit.json.
"""
import numpy as np, pandas as pd, json, glob
from scipy.stats import rankdata

TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
XA = TR + "wideA_lamorth0_xattn"
LAM = TR + "wideA_lamorth0"
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


def ic_at(P, member, CL, YR, day):
    ics, days = [], []
    for t in np.where(np.isfinite(P).any(1))[0]:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(P[t]))[0]
        if base.size < 5:
            continue
        ic = np.corrcoef(rankdata(P[t, base]), rankdata(YR[t, base]))[0, 1]
        if np.isfinite(ic):
            ics.append(ic); days.append(int(day[t]))
    return np.array(ics), np.array(days)


def dyn_static(P, member, CL, YR, nshuf=25):
    rows = np.where(np.isfinite(P).any(1))[0]
    idxs, yr = [], []
    for t in rows:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(P[t]))[0]
        idxs.append(base if base.size >= 5 else None)
        yr.append(rankdata(YR[t, base]) if base.size >= 5 else None)
    val = [i for i in range(len(rows)) if idxs[i] is not None]
    tot = np.nanmean([np.corrcoef(rankdata(P[rows[i], idxs[i]]), yr[i])[0, 1] for i in val])
    # deterministic static = per-asset time-mean tilt
    N = P.shape[1]; mu = np.full(N, np.nan)
    for a in range(N):
        col = P[rows, a]; col = col[np.isfinite(col)]
        if col.size >= 5:
            mu[a] = col.mean()
    sm = []
    for i in val:
        b = idxs[i]; m = np.isfinite(mu[b])
        if m.sum() >= 5:
            sm.append(np.corrcoef(rankdata(mu[b][m]), rankdata(YR[rows[i], b][m]))[0, 1])
    stat_mean = float(np.nanmean(sm))
    # shuffle static
    Psub = P[rows]; sh = []
    for _ in range(nshuf):
        Cs = Psub.copy()
        for a in range(N):
            fin = np.where(np.isfinite(Cs[:, a]))[0]
            if fin.size > 1:
                Cs[fin, a] = Cs[fin[RNG.permutation(fin.size)], a]
        rep = [np.corrcoef(rankdata(Cs[i, idxs[i]][np.isfinite(Cs[i, idxs[i]])]),
                           rankdata(YR[rows[i], idxs[i]][np.isfinite(Cs[i, idxs[i]])]))[0, 1]
               for i in val if np.isfinite(Cs[i, idxs[i]]).sum() >= 5]
        sh.append(np.nanmean(rep))
    stat_s = float(np.nanmean(sh))
    return dict(total=round(float(tot), 4), static_shuffle=round(stat_s, 4), static_mean=round(stat_mean, 4),
                dynamic=round(float(tot) - stat_s, 4), dyn_share=round((float(tot) - stat_s) / tot, 3))


if __name__ == "__main__":
    pr = np.load(XA + "/panel_ref.npz", allow_pickle=True)
    member, CL = pr["member"].astype(bool), pr["CL"].astype(bool)
    YR, Yraw = pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    day = pr["day"]
    ts = pr["ts"].astype(np.int64)
    xf = sorted(glob.glob(XA + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0]))
    lf = sorted(glob.glob(LAM + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0]))

    per_fold = []
    for i, (xff, lff) in enumerate(zip(xf, lf)):
        zx = np.load(xff); zl = np.load(lff)
        Cx = comp_panel(zx["scores"], member, CL, YR)
        Cl = comp_panel(zl["scores"], member, CL, YR)
        # fold boundary: te day range + gap to train
        te_days = np.unique(day[zx["te_rows"]])
        icx, dx = ic_at(Cx, member, CL, YR, day)
        icl, dl = ic_at(Cl, member, CL, YR, day)
        ds_x = dyn_static(Cx, member, CL, YR)
        # paired xattn - lamorth0 (same rows)
        d = icx - icl
        uday = np.unique(dx); d2 = {u: np.where(dx == u)[0] for u in uday}
        boot = np.array([d[np.concatenate([d2[u] for u in RNG.choice(uday, len(uday), True)])].mean()
                         for _ in range(3000)])
        ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
        # pred similarity xattn vs lamorth0
        sim = []
        for t in np.where(np.isfinite(Cx).any(1) & np.isfinite(Cl).any(1))[0]:
            base = np.where(member[t] & CL[t] & np.isfinite(Cx[t]) & np.isfinite(Cl[t]))[0]
            if base.size >= 5:
                s = np.corrcoef(rankdata(Cx[t, base]), rankdata(Cl[t, base]))[0, 1]
                if np.isfinite(s):
                    sim.append(s)
        per_fold.append(dict(fold=i, te_day_range=[int(te_days.min()), int(te_days.max())], n_te_days=int(len(te_days)),
                             xattn_ens_ic=round(float(icx.mean()), 4), lamorth0_ens_ic=round(float(icl.mean()), 4),
                             delta=round(float(d.mean()), 4), delta_ci95=[round(ci[0], 4), round(ci[1], 4)],
                             sig=bool(ci[0] > 0 or ci[1] < 0), decomp=ds_x, pred_sim_vs_lamorth0=round(float(np.mean(sim)), 3)))
        print(f"[fold{i}] xattn ens={icx.mean():+.4f} vs lamorth0 {icl.mean():+.4f} Δ={d.mean():+.4f} "
              f"CI[{ci[0]:+.4f},{ci[1]:+.4f}] | ★DYN-SHARE={ds_x['dyn_share']} (tot {ds_x['total']} "
              f"statShuf {ds_x['static_shuffle']} statMean {ds_x['static_mean']}) | predSim {per_fold[-1]['pred_sim_vs_lamorth0']}", flush=True)

    xmean = round(float(np.mean([r["xattn_ens_ic"] for r in per_fold])), 4)
    lmean = round(float(np.mean([r["lamorth0_ens_ic"] for r in per_fold])), 4)
    dynshare_mean = round(float(np.mean([r["decomp"]["dyn_share"] for r in per_fold])), 3)
    result = dict(title="lamorth0+xattn stack audit (3-fold)", created="2026-07-12", auditor="0C",
                  panel_md5="39f5cc4e (== lamorth0 == qim 3-fold, byte-identical)",
                  xattn_mean=xmean, lamorth0_mean=lmean, mean_delta=round(xmean - lmean, 4),
                  mean_dyn_share=dynshare_mean, per_fold=per_fold)
    json.dump(result, open(EDA + "xattn_stack_audit.json", "w"), indent=2, default=str)
    print(f"\nMEAN xattn {xmean} vs lamorth0 {lmean} (Δ {xmean-lmean:+.4f}) | mean DYN-SHARE {dynshare_mean}", flush=True)
    print("SAVED " + EDA + "xattn_stack_audit.json", flush=True)

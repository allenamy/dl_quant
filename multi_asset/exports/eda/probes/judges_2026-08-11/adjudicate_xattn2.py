"""0C — adjudicate the xattn2 (n_xattn=2) depth arm vs single-layer xattn king. Recompute ensemble,
per-fold paired bootstrap, dyn-share, per-fold dispersion, seed-band z. CPU-only. Same panel 39f5cc4e.
Writes exports/eda/xattn2_adjudication.json.
"""
import numpy as np, json, glob, hashlib
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
X2 = "wideA_xattn2_c1"; KING = "wideA_lamorth0_xattn"
RNG = np.random.default_rng(0)
SEED_BAND = [0.0948, 0.0910, 0.0973]   # single-layer king seed42/43/44 (from G2, recomputed)


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


if __name__ == "__main__":
    pr = np.load(TR + X2 + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64)
    day = pr["day"]
    print("panel md5 x2", md5(TR + X2 + "/panel_ref.npz"), "king", md5(TR + KING + "/panel_ref.npz"), flush=True)
    x2f = sorted(glob.glob(TR + X2 + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0]))
    kf = sorted(glob.glob(TR + KING + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0]))

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

    def dyn(P, rows, nshuf=25):
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
        return round((float(tot) - np.nanmean(sh)) / tot, 3)

    perfold = []
    for fi in range(len(x2f)):
        Cx = comp_panel(np.load(x2f[fi])["scores"], member, CL, YR)
        Ck = comp_panel(np.load(kf[fi])["scores"], member, CL, YR)
        r = np.sort(np.where(np.isfinite(Cx).any(1) & np.isfinite(Ck).any(1))[0])
        icx, dd = ic_at(Cx, r); ick, _ = ic_at(Ck, r)
        d = icx - ick
        ud = np.unique(dd); d2 = {u: np.where(dd == u)[0] for u in ud}
        boot = np.array([d[np.concatenate([d2[u] for u in RNG.choice(ud, len(ud), True)])].mean() for _ in range(3000)])
        ci = (round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4))
        perfold.append(dict(fold=fi, xattn2=round(float(icx.mean()), 4), king=round(float(ick.mean()), 4),
                            delta=round(float(d.mean()), 4), ci95=list(ci), sig=bool(ci[0] > 0 or ci[1] < 0),
                            dyn_share=dyn(Cx, r)))
        print(f"[fold{fi}] x2 {icx.mean():+.4f} king {ick.mean():+.4f} Δ {d.mean():+.4f} CI{ci} sig={perfold[-1]['sig']} dyn={perfold[-1]['dyn_share']}", flush=True)

    x2_mean = float(np.mean([p["xattn2"] for p in perfold]))
    king_mean = float(np.mean([p["king"] for p in perfold]))
    sb = np.array(SEED_BAND)
    seed_z = float((x2_mean - sb.mean()) / sb.std())
    x2_disp = float(np.std([p["xattn2"] for p in perfold]))
    king_disp = float(np.std([p["king"] for p in perfold]))
    fold0_gain = perfold[0]["delta"]; fold2_delta = perfold[2]["delta"]
    # verdict logic
    no_fold_worse = all(p["delta"] >= -0.001 for p in perfold)
    within_seed = x2_mean <= (sb.max() + 0.5 * sb.std())   # <= single-layer seed ceiling + half-sigma
    verdict = ("FAIL/TIE (close, no 5yr): " if (not no_fold_worse or within_seed) else "PASS (queue 5yr): ")
    verdict += (f"mean Δ {x2_mean-king_mean:+.4f} (bar +0.003); no_fold_worse={no_fold_worse} "
                f"(fold2 Δ {fold2_delta:+.4f}); seed-band z {seed_z:+.2f} (x2 {x2_mean:.4f} vs single-layer "
                f"seeds mean {sb.mean():.4f} max {sb.max():.4f} std {sb.std():.4f}); fold0 gain {fold0_gain:+.4f} "
                f"at small-block (overfit-suspect); disp x2 {x2_disp:.4f} vs king {king_disp:.4f}.")
    res = dict(title="xattn2 depth-arm adjudication", created="2026-07-12", auditor="0C",
               panel_md5=md5(TR + X2 + "/panel_ref.npz"), per_fold=perfold,
               xattn2_mean=round(x2_mean, 4), king_mean=round(king_mean, 4),
               mean_delta=round(x2_mean - king_mean, 4), no_fold_worse=no_fold_worse,
               seed_band=SEED_BAND, seed_band_mean=round(float(sb.mean()), 4), seed_band_max=round(float(sb.max()), 4),
               seed_band_std=round(float(sb.std()), 4), seed_z=round(seed_z, 2),
               perfold_dispersion_x2=round(x2_disp, 4), perfold_dispersion_king=round(king_disp, 4),
               verdict=verdict)
    json.dump(res, open(EDA + "xattn2_adjudication.json", "w"), indent=2, default=str)
    print(f"\n{verdict}", flush=True)
    print("SAVED " + EDA + "xattn2_adjudication.json", flush=True)

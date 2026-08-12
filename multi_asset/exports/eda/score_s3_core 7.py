"""0C — ARM-S3 (168h weekly) CORE score. Horizon-ladder final arm.
(1) #18 raw专项: per-year raw-IC (vs Yraw) + resid-IC (vs YR) + corr(YR,Yraw) diagnostic — is fold0 raw
    negative a benign baseline-residualization product (residual ~orthogonal/opposite to raw) or a danger sign?
(2) small-sample power: ~52 weekly anchors/year → pooled per-ts + day-block bootstrap CI.
(3) king-orthogonal AND S2-orthogonal increment + pred-corr (S3 is a slow factor like S2; redundancy risk in S2).
CPU-only. Writes exports/eda/arm_s3_core.json.
"""
import numpy as np, pandas as pd, json, glob, hashlib
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
S3 = TR + "wideA_s3_y168_c1"
S2 = TR + "wideA_s2_y24_5yr"
RNG = np.random.default_rng(0)


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
    print("S3 panel md5", md5(S3 + "/panel_ref.npz"), flush=True)
    pr = np.load(S3 + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR, Yraw = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    ts = pr["ts"].astype(np.int64); day = pr["day"]; yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    T, N = Yraw.shape

    # king OOS preds
    kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
    king = kp["king_pred"].astype(np.float64)

    # S3 composite (stitched, test-rows-only → strictly OOS)
    S = np.full((T, N), np.nan); fold_te = {}
    for f in sorted(glob.glob(S3 + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        z = np.load(f); C = comp_panel(z["scores"], member, CL, YR); m = np.isfinite(C); S[m] = C[m]
        te = z["te_rows"]; Y = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min()); fold_te[Y] = te

    # S2 composite on same ts grid (its own CL/YR; test-rows-only → OOS)
    prs2 = np.load(S2 + "/panel_ref.npz", allow_pickle=True)
    CL2, YR2 = prs2["CL"].astype(bool), prs2["YR"].astype(np.float64)
    assert np.array_equal(prs2["ts"].astype(np.int64), ts)
    S2c = np.full((T, N), np.nan)
    for f in sorted(glob.glob(S2 + "/fold_*_head_scores.npz")):
        C = comp_panel(np.load(f)["scores"], member, CL2, YR2); m = np.isfinite(C); S2c[m] = C[m]

    def orth_one(s, k, y):
        """rank-IC of s residualized on k, vs y."""
        sd = s - s.mean(); kd = k - k.mean()
        beta = (sd @ kd) / (kd @ kd) if (kd @ kd) > 1e-12 else 0.0
        return np.corrcoef(rankdata(sd - beta * kd), rankdata(y))[0, 1]

    def metrics(rows):
        raw, resid, yy_corr, kinc, kpc, s2inc, s2pc, s2cov, days = [], [], [], [], [], [], [], 0, []
        for t in rows:
            b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(Yraw[t]) & np.isfinite(S[t]) & np.isfinite(king[t]))[0]
            if b.size < 8:
                continue
            s = S[t, b]; k = king[t, b]; y = YR[t, b]; yr_ = Yraw[t, b]
            raw.append(np.corrcoef(rankdata(s), rankdata(yr_))[0, 1])
            resid.append(np.corrcoef(rankdata(s), rankdata(y))[0, 1])
            yy_corr.append(np.corrcoef(rankdata(y), rankdata(yr_))[0, 1])   # #18 diagnostic: how aligned is resid target to raw
            kinc.append(orth_one(s, k, y))
            kpc.append(np.corrcoef(rankdata(s), rankdata(k))[0, 1])
            # S2-orthogonal on rows where S2 pred also present
            if np.isfinite(S2c[t, b]).all() and S2c[t, b].std() > 1e-12:
                s2v = S2c[t, b]
                s2inc.append(orth_one(s, s2v, y)); s2pc.append(np.corrcoef(rankdata(s), rankdata(s2v))[0, 1]); s2cov += 1
            days.append(int(day[t]))
        return dict(raw=np.array(raw), resid=np.array(resid), yy=np.array(yy_corr), kinc=np.array(kinc),
                    kpc=np.array(kpc), s2inc=np.array(s2inc), s2pc=np.array(s2pc), s2cov=s2cov, days=np.array(days))

    per_year = []
    for Y in sorted(fold_te):
        M = metrics(fold_te[Y])
        s2inc_m = float(M["s2inc"].mean()) if M["s2inc"].size else None
        s2pc_m = float(M["s2pc"].mean()) if M["s2pc"].size else None
        per_year.append(dict(year=Y, n_ts=len(M["raw"]),
                             raw_ic=round(float(M["raw"].mean()), 4), resid_ic=round(float(M["resid"].mean()), 4),
                             corr_YR_Yraw=round(float(M["yy"].mean()), 3),
                             king_orth_inc=round(float(M["kinc"].mean()), 4), king_pred_corr=round(float(M["kpc"].mean()), 3),
                             s2_orth_inc=None if s2inc_m is None else round(s2inc_m, 4),
                             s2_pred_corr=None if s2pc_m is None else round(s2pc_m, 3), s2_cov=M["s2cov"]))
        print(f"[{Y}] raw {M['raw'].mean():+.4f} resid {M['resid'].mean():+.4f} corr(YR,Yraw) {M['yy'].mean():+.3f} "
              f"| K-orth {M['kinc'].mean():+.4f} Kpc {M['kpc'].mean():.3f} | S2-orth {('%.4f'%s2inc_m) if s2inc_m is not None else 'NA'} "
              f"S2pc {('%.3f'%s2pc_m) if s2pc_m is not None else 'NA'} (n={len(M['raw'])} s2cov={M['s2cov']})", flush=True)

    allr = np.array(sorted(set().union(*[set(t.tolist()) for t in fold_te.values()])))
    A = metrics(allr)
    ud = np.unique(A["days"]); d2 = {u: np.where(A["days"] == u)[0] for u in ud}

    def boot(series, days):
        udl = np.unique(days); dd = {u: np.where(days == u)[0] for u in udl}
        bs = np.array([series[np.concatenate([dd[u] for u in RNG.choice(udl, len(udl), True)])].mean() for _ in range(3000)])
        return (round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4))

    kinc_ci = boot(A["kinc"], A["days"]); raw_ci = boot(A["raw"], A["days"]); resid_ci = boot(A["resid"], A["days"])
    # S2-orth days: rebuild days aligned to s2inc entries
    s2_days = []
    for t in allr:
        b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(Yraw[t]) & np.isfinite(S[t]) & np.isfinite(king[t]))[0]
        if b.size < 8:
            continue
        if np.isfinite(S2c[t, b]).all() and S2c[t, b].std() > 1e-12:
            s2_days.append(int(day[t]))
    s2_days = np.array(s2_days)
    s2inc_ci = boot(A["s2inc"], s2_days) if A["s2inc"].size else None

    sign_king = all(x["king_orth_inc"] > 0 for x in per_year)
    sign_s2 = all((x["s2_orth_inc"] is None) or (x["s2_orth_inc"] > 0) for x in per_year)
    result = dict(title="ARM-S3 (168h weekly) core score", created="2026-07-14", auditor="0C",
                  panel_md5=md5(S3 + "/panel_ref.npz"), ts_aligned_king_s2=True, weekly_anchors_per_year=[len(fold_te[Y]) for Y in sorted(fold_te)],
                  raw_ic_pooled=round(float(A["raw"].mean()), 4), raw_ci95=list(raw_ci),
                  resid_ic_pooled=round(float(A["resid"].mean()), 4), resid_ci95=list(resid_ci),
                  king_orth_inc_pooled=round(float(A["kinc"].mean()), 4), king_orth_ci95=list(kinc_ci),
                  king_pred_corr_pooled=round(float(A["kpc"].mean()), 3),
                  s2_orth_inc_pooled=round(float(A["s2inc"].mean()), 4) if A["s2inc"].size else None,
                  s2_orth_ci95=list(s2inc_ci) if s2inc_ci else None,
                  s2_pred_corr_pooled=round(float(A["s2pc"].mean()), 3) if A["s2pc"].size else None,
                  s2_coverage_frac=round(float(A["s2inc"].size / max(len(A["raw"]), 1)), 3),
                  per_year=per_year, sign_consistent_king=sign_king, sign_consistent_s2=sign_s2,
                  gate_a_king=bool(A["kinc"].mean() >= 0.003 and kinc_ci[0] > 0 and sign_king),
                  gate_a_s2=bool(A["s2inc"].size and A["s2inc"].mean() >= 0.003 and s2inc_ci and s2inc_ci[0] > 0 and sign_s2),
                  gate_b_king=bool(A["kpc"].mean() < 0.7),
                  gate_b_s2=bool((A["s2pc"].mean() < 0.7) if A["s2pc"].size else True))
    json.dump(result, open(EDA + "arm_s3_core.json", "w"), indent=2, default=str)
    print(f"\nPOOLED raw {A['raw'].mean():+.4f} CI{raw_ci} | resid {A['resid'].mean():+.4f} CI{resid_ci}", flush=True)
    print(f"K-orth {A['kinc'].mean():+.4f} CI{kinc_ci} Kpc {A['kpc'].mean():.3f} | S2-orth {A['s2inc'].mean() if A['s2inc'].size else 'NA':.4f} CI{s2inc_ci} S2pc {A['s2pc'].mean() if A['s2pc'].size else 'NA':.3f} (cov {A['s2inc'].size}/{len(A['raw'])})", flush=True)
    print(f"sign-consistent king {sign_king} s2 {sign_s2}", flush=True)
    print("SAVED " + EDA + "arm_s3_core.json", flush=True)

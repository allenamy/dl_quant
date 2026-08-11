"""0C — ARM-S2 (24h suppl factor) score, gates (a) king-orthogonal incremental IC, (b) pred-corr vs
king, (d) dyn-share. king-pred base = king_pred_panel.npz (185d3b65, ts row-aligned to ARM-S2 panel
9f1bdb87, verified). Orthogonalize ARM-S2 pred on king-pred per-ts (values), rank-IC of residual vs
YR24. YR24 is already ⊥[funding+zoo] so this IS the increment over [funding+zoo+king]. CPU-only.
Writes exports/eda/arm_s2_core.json.
"""
import numpy as np, pandas as pd, json, glob
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
S2 = TR + "wideA_s2_y24_c1"
RNG = np.random.default_rng(0)


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
    pr = np.load(S2 + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR, Yraw = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    day = pr["day"]; yr = pd.to_datetime(pr["ts"].astype(np.int64), unit="ms", utc=True).year.to_numpy()
    kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
    king = kp["king_pred"].astype(np.float64)
    assert np.array_equal(pr["ts"], kp["ts"]), "ts mismatch"

    # ARM-S2 composite (stitched OOS) + per-fold te map
    T, N = Yraw.shape
    S = np.full((T, N), np.nan); fold_te = []
    for f in sorted(glob.glob(S2 + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        z = np.load(f); C = comp_panel(z["scores"], member, CL, YR)
        m = np.isfinite(C); S[m] = C[m]; fold_te.append(z["te_rows"])

    def orth_ic(rows):
        """per-ts: residualize S on king (values), rank-IC(resid, YR); also raw rank-IC(S,YR); pred-corr."""
        raw, inc, pc, days = [], [], [], []
        for t in rows:
            b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(S[t]) & np.isfinite(king[t]))[0]
            if b.size < 8:
                continue
            s = S[t, b]; k = king[t, b]; y = YR[t, b]
            raw.append(np.corrcoef(rankdata(s), rankdata(y))[0, 1])
            # OLS residualize s on k (demeaned)
            sd = s - s.mean(); kd = k - k.mean()
            beta = (sd @ kd) / (kd @ kd) if (kd @ kd) > 1e-12 else 0.0
            resid = sd - beta * kd
            inc.append(np.corrcoef(rankdata(resid), rankdata(y))[0, 1])
            pc.append(np.corrcoef(rankdata(s), rankdata(k))[0, 1])
            days.append(int(day[t]))
        return np.array(raw), np.array(inc), np.array(pc), np.array(days)

    def dyn_share(rows):
        # shuffle-future on the ORTHOGONAL signal (residualize per-ts first, store), vs YR
        Sorth = np.full((T, N), np.nan)
        for t in rows:
            b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(S[t]) & np.isfinite(king[t]))[0]
            if b.size < 8:
                continue
            s = S[t, b] - S[t, b].mean(); k = king[t, b] - king[t, b].mean()
            beta = (s @ k) / (k @ k) if (k @ k) > 1e-12 else 0.0
            Sorth[t, b] = s - beta * k
        rws = np.sort(rows)
        idx = [np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(Sorth[t]))[0] for t in rws]
        idx = [b if b.size >= 5 else None for b in idx]
        val = [i for i in range(len(rws)) if idx[i] is not None]
        tot = np.nanmean([np.corrcoef(rankdata(Sorth[rws[i], idx[i]]), rankdata(YR[rws[i], idx[i]]))[0, 1] for i in val])
        Psub = Sorth[rws]; sh = []
        for _ in range(20):
            Cs = Psub.copy()
            for a in range(N):
                fin = np.where(np.isfinite(Cs[:, a]))[0]
                if fin.size > 1:
                    Cs[fin, a] = Cs[fin[RNG.permutation(fin.size)], a]
            sh.append(np.nanmean([np.corrcoef(rankdata(Cs[i, idx[i]][np.isfinite(Cs[i, idx[i]])]),
                      rankdata(YR[rws[i], idx[i]][np.isfinite(Cs[i, idx[i]])]))[0, 1]
                      for i in val if np.isfinite(Cs[i, idx[i]]).sum() >= 5]))
        return round((float(tot) - np.nanmean(sh)) / tot, 3) if tot else None

    per_fold = []
    for fi, te in enumerate(fold_te):
        raw, inc, pc, days = orth_ic(te)
        Y = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min())
        per_fold.append(dict(fold=fi, year=Y, raw_ic=round(float(raw.mean()), 4),
                             incremental_ic=round(float(inc.mean()), 4), pred_corr_king=round(float(pc.mean()), 3),
                             n_ts=len(inc)))
        print(f"[fold{fi} te~{Y}] raw {raw.mean():+.4f} | king-orth INCREMENT {inc.mean():+.4f} | pred-corr king {pc.mean():.3f}", flush=True)

    allrows = np.array(sorted(set().union(*[set(t.tolist()) for t in fold_te])))
    raw, inc, pc, days = orth_ic(allrows)
    # day-block bootstrap of pooled incremental IC
    ud = np.unique(days); d2 = {u: np.where(days == u)[0] for u in ud}
    boot = np.array([inc[np.concatenate([d2[u] for u in RNG.choice(ud, len(ud), True)])].mean() for _ in range(3000)])
    ci = (round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4))
    ds = dyn_share(allrows)
    result = dict(title="ARM-S2 gates a/b/d", created="2026-07-13", auditor="0C",
                  panel_ts_aligned=True, n_test_rows=int(len(allrows)),
                  raw_resid_ic_pooled=round(float(raw.mean()), 4), json_raw_mean=0.0515,
                  incremental_ic_pooled=round(float(inc.mean()), 4), incremental_ci95=list(ci),
                  incremental_sig=bool(ci[0] > 0), pred_corr_king=round(float(pc.mean()), 3),
                  dyn_share_orth=ds, per_fold=per_fold,
                  gate_a_pass=bool(inc.mean() >= 0.003 and ci[0] > 0 and all(p["incremental_ic"] > 0 for p in per_fold)),
                  gate_b_pass=bool(pc.mean() < 0.7), gate_d_pass=bool(ds is not None and ds >= 0.5))
    json.dump(result, open(EDA + "arm_s2_core.json", "w"), indent=2, default=str)
    print(f"\nPOOLED raw {raw.mean():+.4f} | INCREMENT {inc.mean():+.4f} CI{ci} | pred-corr {pc.mean():.3f} | dyn {ds}", flush=True)
    print(f"GATES a={result['gate_a_pass']} b={result['gate_b_pass']} d={result['gate_d_pass']}", flush=True)
    print("SAVED " + EDA + "arm_s2_core.json", flush=True)

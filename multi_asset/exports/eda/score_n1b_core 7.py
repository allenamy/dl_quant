"""0C — ARM-N1b (multi-relational cross-asset attn, 4h/YR4B book-residual) CORE score vs gate v2.
(a) book-orth increment = IC vs YR4B (target already king+S2-orth) + day-block boot CI + per-year sign.
    target-orthogonality check: corr(YR4B, king) / corr(YR4B, S2) ~0 ; corr(YR4B, YR4) = dimension removed.
(b) pred-corr vs king AND S2 (<0.7).  (i) architecture qualifier: pred-corr vs king <= 0.36 (S1's ceiling).
(d) dyn-share (shuffle-future) + forward-window-decay causal test (rolling-corr edges <=t: IC must peak lag0, decay fwd).
CPU-only. Writes exports/eda/arm_n1b_core.json.
"""
import numpy as np, pandas as pd, json, glob, hashlib
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"; EDA = "multi_asset/exports/eda/"
N1 = TR + "wideA_n1b_multirel_c1"; S2 = TR + "wideA_s2_y24_5yr"
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
        if base.size < 5: continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12: comp += (col - col.mean()) / col.std(); nk += 1
        if nk: C[t, base] = comp / nk
    return C


def ricorr(a, b): return np.corrcoef(rankdata(a), rankdata(b))[0, 1]


if __name__ == "__main__":
    print("N1b panel md5", md5(N1 + "/panel_ref.npz"), flush=True)
    pr = np.load(N1 + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR4B, Yraw = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    ts = pr["ts"].astype(np.int64); day = pr["day"]; yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    T, N = Yraw.shape

    kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
    king = kp["king_pred"].astype(np.float64); YR4 = kp["YR"].astype(np.float64)

    # S2 composite on same grid (its CL/YR)
    prs2 = np.load(S2 + "/panel_ref.npz", allow_pickle=True)
    CL2, YR2 = prs2["CL"].astype(bool), prs2["YR"].astype(np.float64)
    S2c = np.full((T, N), np.nan)
    for f in sorted(glob.glob(S2 + "/fold_*_head_scores.npz")):
        C = comp_panel(np.load(f)["scores"], member, CL2, YR2); m = np.isfinite(C); S2c[m] = C[m]

    # N1b composite (stitched test-rows-only -> OOS)
    S = np.full((T, N), np.nan); fold_te = {}
    fold_scores = {}
    for f in sorted(glob.glob(N1 + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        z = np.load(f); C = comp_panel(z["scores"], member, CL, YR4B); m = np.isfinite(C); S[m] = C[m]
        te = z["te_rows"]; Y = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min()); fold_te[Y] = te; fold_scores[Y] = C

    def metrics(rows):
        inc, kpc, s2pc, tk, ts2, tyr4, days, s2cov = [], [], [], [], [], [], [], 0
        for t in rows:
            b = np.where(member[t] & CL[t] & np.isfinite(YR4B[t]) & np.isfinite(S[t]) & np.isfinite(king[t]))[0]
            if b.size < 8: continue
            s = S[t, b]; k = king[t, b]; y = YR4B[t, b]
            inc.append(ricorr(s, y)); kpc.append(ricorr(s, k)); tk.append(ricorr(y, k))
            if np.isfinite(YR4[t, b]).all(): tyr4.append(ricorr(y, YR4[t, b]))
            if np.isfinite(S2c[t, b]).all() and S2c[t, b].std() > 1e-12:
                s2pc.append(ricorr(s, S2c[t, b])); ts2.append(ricorr(y, S2c[t, b])); s2cov += 1
            days.append(int(day[t]))
        return dict(inc=np.array(inc), kpc=np.array(kpc), s2pc=np.array(s2pc), tk=np.array(tk), ts2=np.array(ts2),
                    tyr4=np.array(tyr4), days=np.array(days), s2cov=s2cov)

    per_year = []
    for Y in sorted(fold_te):
        M = metrics(fold_te[Y])
        per_year.append(dict(year=Y, n_ts=len(M["inc"]), increment=round(float(M["inc"].mean()), 4),
                             pred_corr_king=round(float(M["kpc"].mean()), 3),
                             pred_corr_s2=None if not M["s2pc"].size else round(float(M["s2pc"].mean()), 3),
                             tgt_corr_king=round(float(M["tk"].mean()), 3),
                             tgt_corr_s2=None if not M["ts2"].size else round(float(M["ts2"].mean()), 3),
                             tgt_corr_yr4=None if not M["tyr4"].size else round(float(M["tyr4"].mean()), 3), s2cov=M["s2cov"]))
        print(f"[{Y}] incr {M['inc'].mean():+.4f} | Kpc {M['kpc'].mean():.3f} S2pc {('%.3f'%M['s2pc'].mean()) if M['s2pc'].size else 'NA'} "
              f"| tgt-corr king {M['tk'].mean():+.3f} s2 {('%.3f'%M['ts2'].mean()) if M['ts2'].size else 'NA'} yr4 {('%.3f'%M['tyr4'].mean()) if M['tyr4'].size else 'NA'} (n={len(M['inc'])})", flush=True)

    allr = np.array(sorted(set().union(*[set(t.tolist()) for t in fold_te.values()])))
    A = metrics(allr)
    def boot(series, days):
        ud = np.unique(days); dd = {u: np.where(days == u)[0] for u in ud}
        bs = np.array([series[np.concatenate([dd[u] for u in RNG.choice(ud, len(ud), True)])].mean() for _ in range(3000)])
        return (round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4))
    inc_ci = boot(A["inc"], A["days"])

    # dyn-share via shuffle-future: permute each asset's pred across its own test rows, per fold, recompute IC
    def dyn_share():
        tot, sta = [], []
        for Y in sorted(fold_te):
            te = fold_te[Y]; C = fold_scores[Y]
            # per-ts IC (total)
            ics = []
            for t in te:
                b = np.where(member[t] & CL[t] & np.isfinite(YR4B[t]) & np.isfinite(C[t]))[0]
                if b.size >= 8: ics.append(ricorr(C[t, b], YR4B[t, b]))
            tot.append(np.mean(ics))
            # static: shuffle each asset's pred across the fold's test rows (breaks timing, keeps per-asset tilt)
            Csh = C.copy()
            for a in range(N):
                vr = np.array([t for t in te if member[t, a] and CL[t, a] and np.isfinite(C[t, a])])
                if vr.size > 2:
                    perm = RNG.permutation(vr.size); Csh[vr, a] = C[vr[perm], a]
            icss = []
            for t in te:
                b = np.where(member[t] & CL[t] & np.isfinite(YR4B[t]) & np.isfinite(Csh[t]))[0]
                if b.size >= 8: icss.append(ricorr(Csh[t, b], YR4B[t, b]))
            sta.append(np.mean(icss))
        tot = np.array(tot); sta = np.array(sta)
        return tot, sta

    tot, sta = dyn_share()
    dyn = tot - sta; dyn_sh = float(dyn.mean() / tot.mean()) if tot.mean() != 0 else np.nan
    print(f"\ndyn-share: total {tot.mean():+.4f} static {sta.mean():+.4f} dynamic {dyn.mean():+.4f} share {dyn_sh:.3f}", flush=True)
    print("per-fold total", [round(x, 4) for x in tot], "static", [round(x, 4) for x in sta], flush=True)

    # forward-window-decay causal test: IC(pred_t, Yraw at anchor t+k*4h) for k=-2..+2 (4h anchors)
    # build map row->row_index-in-sorted-4h-clean-anchors is messy; use ts offset ~4h*k in ms
    HMS = 3600_000
    tsr = {int(t): i for i, t in enumerate(ts)}
    def fwd_decay():
        out = {}
        for k in (-2, -1, 0, 1, 2):
            ics = []
            for t in allr:
                tt = t + k * 4  # 4 hourly rows = 4h
                if tt < 0 or tt >= T: continue
                b = np.where(member[t] & CL[t] & np.isfinite(S[t]) & np.isfinite(Yraw[tt]) & member[tt])[0]
                if b.size >= 8: ics.append(ricorr(S[t, b], Yraw[tt, b]))
            out[k] = round(float(np.mean(ics)), 4) if ics else None
        return out
    decay = fwd_decay()
    print("forward-decay IC(pred_t, Yraw_{t+k*4h}):", decay, flush=True)

    gate_a = bool(A["inc"].mean() >= 0.003 and inc_ci[0] > 0 and all(x["increment"] > 0 for x in per_year))
    gate_b = bool(A["kpc"].mean() < 0.7 and (not A["s2pc"].size or A["s2pc"].mean() < 0.7))
    gate_i = bool(A["kpc"].mean() <= 0.36)
    gate_d = bool(dyn_sh >= 0.5)
    result = dict(title="ARM-N1b (multi-relational cross-asset attn, 4h/YR4B) core score", created="2026-07-15", auditor="0C",
                  panel_md5=md5(N1 + "/panel_ref.npz"), ts_aligned=True, horizon=4, n_params=272013, delta_params=16775,
                  gate_alpha_learned=dict(alpha=-0.09856, lam=[0.05436, -0.05826, -0.09328], interpretation="nonzero=structure used (modest, subtractive)"),
                  increment_pooled=round(float(A["inc"].mean()), 4), increment_ci95=list(inc_ci),
                  pred_corr_king=round(float(A["kpc"].mean()), 3), pred_corr_s2=round(float(A["s2pc"].mean()), 3) if A["s2pc"].size else None,
                  tgt_corr_king=round(float(A["tk"].mean()), 3), tgt_corr_s2=round(float(A["ts2"].mean()), 3) if A["ts2"].size else None,
                  tgt_corr_yr4=round(float(A["tyr4"].mean()), 3) if A["tyr4"].size else None,
                  dyn_share=round(dyn_sh, 3), dyn_per_fold_total=[round(x, 4) for x in tot], dyn_per_fold_static=[round(x, 4) for x in sta],
                  forward_decay=decay, per_year=per_year,
                  gate_a_increment=gate_a, gate_b_predcorr=gate_b, gate_i_arch_qualifier=gate_i, gate_d_dyn=gate_d,
                  sign_consistent=bool(all(x["increment"] > 0 for x in per_year)))
    json.dump(result, open(EDA + "arm_n1b_core.json", "w"), indent=2, default=str)
    print(f"\nPOOLED incr {A['inc'].mean():+.4f} CI{inc_ci} | Kpc {A['kpc'].mean():.3f} S2pc {A['s2pc'].mean() if A['s2pc'].size else float('nan'):.3f}", flush=True)
    print(f"target-orth: corr(YR4B,king) {A['tk'].mean():+.3f} corr(YR4B,S2) {A['ts2'].mean() if A['ts2'].size else float('nan'):+.3f} corr(YR4B,YR4) {A['tyr4'].mean() if A['tyr4'].size else float('nan'):.3f}", flush=True)
    print(f"GATES: a {gate_a} | b {gate_b} | i(arch<=0.36) {gate_i} | d(dyn>=0.5) {gate_d}", flush=True)
    print("SAVED " + EDA + "arm_n1b_core.json", flush=True)

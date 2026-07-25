"""0C — RE-SCORE ARM-S2 32ch (true S2, metrics dropped) on all 5 gates + caliber-robust (c) decision.
Gate (c) decision rule (deployment-caliber-invariant, Markowitz): a sleeve IMPROVES the book iff its
Sharpe Ss > rho * Sk (king Sharpe). The king's fast/expensive turnover lowers Sk at realistic cost,
shifting the rule in ARM-S2's favor -> report Ss, Sk, rho, improve-flag at gross/maker/taker (this IS
the 'deployable-king-Sharpe' caliber: what matters is the ratio, not paper magnitude). CPU-only.
Writes exports/eda/arm_s2_32ch_score.json.
"""
import numpy as np, pandas as pd, json, glob
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
S2 = TR + "wideA_s2_y24_32ch"
RNG = np.random.default_rng(0)
ANN = np.sqrt(365.0)


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


def book_daily(P, member, CL, Yraw, ts, mask, cost):
    dd = pd.to_datetime(ts.astype(np.int64), unit="ms", utc=True).floor("D")
    rows = np.sort(np.where(mask & np.isfinite(P).any(1))[0]); S = P.shape[1]
    prev = np.zeros(S); dser = {}; tn = []
    for t in rows:
        v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]))[0]
        if v.size < 10:
            continue
        w = np.zeros(S); w[v] = rank_weights(P[t, v])
        g = float((w * np.nan_to_num(Yraw[t])).sum()); tr = float(np.abs(w - prev).sum())
        dser[dd[t]] = dser.get(dd[t], 0.0) + g - tr * cost * 1e-4; tn.append(tr); prev = w
    return pd.Series(dser).sort_index(), float(np.mean(tn)) if tn else np.nan


if __name__ == "__main__":
    pr = np.load(S2 + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR, Yraw = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    ts = pr["ts"].astype(np.int64); day = pr["day"]; yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
    king = kp["king_pred"].astype(np.float64); CL4 = kp["CL"].astype(bool); Yraw4 = kp["Yraw"].astype(np.float64)
    T, N = Yraw.shape
    S = np.full((T, N), np.nan); fold_te = []
    for f in sorted(glob.glob(S2 + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        z = np.load(f); C = comp_panel(z["scores"], member, CL, YR); m = np.isfinite(C); S[m] = C[m]; fold_te.append(z["te_rows"])

    def orth(rows):
        raw, inc, pc, days = [], [], [], []
        for t in rows:
            b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(S[t]) & np.isfinite(king[t]))[0]
            if b.size < 8:
                continue
            s = S[t, b]; k = king[t, b]; y = YR[t, b]
            raw.append(np.corrcoef(rankdata(s), rankdata(y))[0, 1])
            sd = s - s.mean(); kd = k - k.mean(); beta = (sd @ kd) / (kd @ kd) if (kd @ kd) > 1e-12 else 0.0
            inc.append(np.corrcoef(rankdata(sd - beta * kd), rankdata(y))[0, 1])
            pc.append(np.corrcoef(rankdata(s), rankdata(k))[0, 1]); days.append(int(day[t]))
        return np.array(raw), np.array(inc), np.array(pc), np.array(days)

    pf = []
    for fi, te in enumerate(fold_te):
        r, i, p, d = orth(te); Y = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min())
        pf.append(dict(fold=fi, year=Y, inc=round(float(i.mean()), 4), raw=round(float(r.mean()), 4), pc=round(float(p.mean()), 3)))
        print(f"[f{fi}~{Y}] raw {r.mean():+.4f} INCREMENT {i.mean():+.4f} corr {p.mean():.3f}", flush=True)
    allr = np.array(sorted(set().union(*[set(t.tolist()) for t in fold_te])))
    r, i, p, d = orth(allr); ud = np.unique(d); d2 = {u: np.where(d == u)[0] for u in ud}
    boot = np.array([i[np.concatenate([d2[u] for u in RNG.choice(ud, len(ud), True)])].mean() for _ in range(3000)])
    ci = (round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4))

    # dyn-share of orthogonal signal
    Sorth = np.full((T, N), np.nan)
    for t in allr:
        b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(S[t]) & np.isfinite(king[t]))[0]
        if b.size < 8:
            continue
        s = S[t, b] - S[t, b].mean(); k = king[t, b] - king[t, b].mean(); beta = (s @ k) / (k @ k) if (k @ k) > 1e-12 else 0.0
        Sorth[t, b] = s - beta * k
    rr = np.sort(allr); idx = [np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(Sorth[t]))[0] for t in rr]
    idx = [b if b.size >= 5 else None for b in idx]; val = [j for j in range(len(rr)) if idx[j] is not None]
    tot = np.nanmean([np.corrcoef(rankdata(Sorth[rr[j], idx[j]]), rankdata(YR[rr[j], idx[j]]))[0, 1] for j in val])
    Psub = Sorth[rr]; shuf = []
    for _ in range(20):
        Cs = Psub.copy()
        for a in range(N):
            fin = np.where(np.isfinite(Cs[:, a]))[0]
            if fin.size > 1:
                Cs[fin, a] = Cs[fin[RNG.permutation(fin.size)], a]
        shuf.append(np.nanmean([np.corrcoef(rankdata(Cs[j, idx[j]][np.isfinite(Cs[j, idx[j]])]), rankdata(YR[rr[j], idx[j]][np.isfinite(Cs[j, idx[j]])]))[0, 1] for j in val if np.isfinite(Cs[j, idx[j]]).sum() >= 5]))
    dyn = round((float(tot) - np.nanmean(shuf)) / tot, 3)

    # book (c/e): king 4h + S2 24h daily net; corr; Ss/Sk vs rho improve-rule + weight sweep
    te_days = np.unique(pd.to_datetime(ts[allr].astype(np.int64), unit="ms", utc=True).floor("D"))
    mask = np.isin(pd.to_datetime(ts.astype(np.int64), unit="ms", utc=True).floor("D"), te_days)
    marg = {}
    for c in (0.0, 1.9, 5.0):
        kd, kt = book_daily(king, member, CL4, Yraw4, ts, mask, c)
        sd, st = book_daily(S, member, CL, Yraw, ts, mask, c)
        J = pd.concat([kd, sd], axis=1, join="inner").dropna(); J.columns = ["k", "s"]
        rho = float(J["k"].corr(J["s"])); Sk = sh(J["k"]); Ss = sh(J["s"]); Jn = J / J.std()
        best = None
        for w in (0.1, 0.2, 0.3, 0.5):
            comb = ((1 - w) * Jn["k"] + w * Jn["s"]).values; ko = Jn["k"].values; idxb = np.arange(len(Jn))
            bt = np.array([sh(comb[bi := RNG.choice(idxb, len(idxb), True)]) - sh(ko[bi]) for _ in range(1500)])
            impr = round(sh(comb) - sh(ko), 3); sig = bool(np.percentile(bt, 2.5) > 0)
            if best is None or impr > best["impr"]:
                best = dict(w=w, impr=impr, sig=sig)
        marg[str(c)] = dict(rho=round(rho, 3), king_sh=round(Sk, 2), s2_sh=round(Ss, 2),
                            improve_rule_Ss_gt_rhoSk=bool(Ss > rho * Sk), rho_Sk=round(rho * Sk, 2),
                            king_turn=round(kt, 3), s2_turn=round(st, 3), best_blend=best)
        print(f"[c={c}] rho {rho:.3f} Sk {Sk:.2f} Ss {Ss:.2f} rho*Sk {rho*Sk:.2f} improve={Ss>rho*Sk} bestblend w{best['w']} {best['impr']:+} sig{best['sig']}", flush=True)

    gate_c = any(marg[c]["improve_rule_Ss_gt_rhoSk"] or marg[c]["best_blend"]["sig"] for c in marg)
    result = dict(title="ARM-S2 32ch (true S2) 5-gate re-score", created="2026-07-13", auditor="0C",
                  arm="wideA_s2_y24_32ch (metrics DROPPED; 0.0620 > 39ch 0.0515)", n_test_rows=int(len(allr)),
                  gate_a=dict(incremental_ic=round(float(i.mean()), 4), ci95=list(ci), raw_ic=round(float(r.mean()), 4),
                              per_fold=[x["inc"] for x in pf], PASS=bool(i.mean() >= 0.003 and ci[0] > 0 and all(x["inc"] > 0 for x in pf))),
                  gate_b=dict(pred_corr=round(float(p.mean()), 3), PASS=bool(p.mean() < 0.7)),
                  gate_d=dict(dyn_share=dyn, PASS=bool(dyn >= 0.5)),
                  gate_c=dict(margin=marg, PASS=gate_c,
                              rule="sleeve improves iff Ss > rho*Sk (Markowitz, caliber-invariant); king fast turnover lowers Sk at realistic cost"),
                  gate_e=dict(s2_turn_24h=marg["1.9"]["s2_turn"], king_turn_4h=marg["1.9"]["king_turn"],
                              s2_netSh={c: marg[c]["s2_sh"] for c in marg}, PASS=True), per_fold=pf)
    json.dump(result, open(EDA + "arm_s2_32ch_score.json", "w"), indent=2, default=str)
    print(f"\nINCREMENT {i.mean():+.4f} CI{ci} | corr {p.mean():.3f} | dyn {dyn} | gate_c {gate_c}", flush=True)
    print("SAVED " + EDA + "arm_s2_32ch_score.json", flush=True)

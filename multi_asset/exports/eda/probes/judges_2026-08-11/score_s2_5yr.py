"""0C — ARM-S2 5yr FINAL score (32ch true S2). Per-year king-orthogonal increment (sign consistency),
per-year + pooled improve-rule Ss>ρ·Sk, 5yr blend-margin bootstrap (now enough power for significance),
dyn-share, 2022 short-train fold σ-health, panel byte-check. CPU-only. Writes exports/eda/arm_s2_5yr_score.json.
"""
import numpy as np, pandas as pd, json, glob, hashlib
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
S2 = TR + "wideA_s2_y24_5yr"
RNG = np.random.default_rng(0)
ANN = np.sqrt(365.0)


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:8]


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
    prev = np.zeros(S); dser = {}
    for t in rows:
        v = np.where(member[t] & CL[t] & np.isfinite(P[t]) & np.isfinite(Yraw[t]))[0]
        if v.size < 10:
            continue
        w = np.zeros(S); w[v] = rank_weights(P[t, v])
        g = float((w * np.nan_to_num(Yraw[t])).sum()); tr = float(np.abs(w - prev).sum())
        dser[dd[t]] = dser.get(dd[t], 0.0) + g - tr * cost * 1e-4; prev = w
    return pd.Series(dser).sort_index()


if __name__ == "__main__":
    print("panel md5", md5(S2 + "/panel_ref.npz"), flush=True)
    pr = np.load(S2 + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR, Yraw = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64), pr["Yraw"].astype(np.float64)
    ts = pr["ts"].astype(np.int64); day = pr["day"]; yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
    kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True)
    king = kp["king_pred"].astype(np.float64); CL4 = kp["CL"].astype(bool); Yraw4 = kp["Yraw"].astype(np.float64)
    T, N = Yraw.shape
    S = np.full((T, N), np.nan); fold_te = {}
    for f in sorted(glob.glob(S2 + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        z = np.load(f); C = comp_panel(z["scores"], member, CL, YR); m = np.isfinite(C); S[m] = C[m]
        te = z["te_rows"]; Y = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min()); fold_te[Y] = te

    def orth(rows):
        raw, inc, pc = [], [], []; cov = 0
        for t in rows:
            b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(S[t]) & np.isfinite(king[t]))[0]
            if b.size < 8:
                continue
            cov += 1
            s = S[t, b]; k = king[t, b]; y = YR[t, b]
            raw.append(np.corrcoef(rankdata(s), rankdata(y))[0, 1])
            sd = s - s.mean(); kd = k - k.mean(); beta = (sd @ kd) / (kd @ kd) if (kd @ kd) > 1e-12 else 0.0
            inc.append(np.corrcoef(rankdata(sd - beta * kd), rankdata(y))[0, 1])
            pc.append(np.corrcoef(rankdata(s), rankdata(k))[0, 1])
        return np.array(raw), np.array(inc), np.array(pc), cov

    per_year = []
    for Y in sorted(fold_te):
        r, i, p, cov = orth(fold_te[Y])
        per_year.append(dict(year=Y, raw_ic=round(float(r.mean()), 4), incremental_ic=round(float(i.mean()), 4),
                             pred_corr=round(float(p.mean()), 3), n_ts=len(i), king_cov=cov))
        print(f"[{Y}] raw {r.mean():+.4f} INCREMENT {i.mean():+.4f} corr {p.mean():.3f} (n={len(i)})", flush=True)
    allr = np.array(sorted(set().union(*[set(t.tolist()) for t in fold_te.values()])))
    r, i, p, _ = orth(allr)
    # pooled bootstrap on the increment per-ts series with day-blocks
    inc_days = []
    for t in allr:
        b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(S[t]) & np.isfinite(king[t]))[0]
        if b.size >= 8:
            inc_days.append(int(day[t]))
    inc_days = np.array(inc_days); ud = np.unique(inc_days); d2 = {u: np.where(inc_days == u)[0] for u in ud}
    boot = np.array([i[np.concatenate([d2[u] for u in RNG.choice(ud, len(ud), True)])].mean() for _ in range(3000)])
    ci = (round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4))

    # book margin over 2022-2026 (king 4h + S2 24h), per-year + pooled bootstrap
    te_days = np.unique(pd.to_datetime(ts[allr].astype(np.int64), unit="ms", utc=True).floor("D"))
    mask = np.isin(pd.to_datetime(ts.astype(np.int64), unit="ms", utc=True).floor("D"), te_days)
    marg = {}
    for c in (0.0, 1.9, 5.0):
        kd = book_daily(king, member, CL4, Yraw4, ts, mask, c); sd = book_daily(S, member, CL, Yraw, ts, mask, c)
        J = pd.concat([kd, sd], axis=1, join="inner").dropna(); J.columns = ["k", "s"]
        rho = float(J["k"].corr(J["s"])); Sk = sh(J["k"]); Ss = sh(J["s"]); Jn = J / J.std()
        ko = Jn["k"].values; best = None
        for w in (0.1, 0.15, 0.2, 0.3):
            comb = ((1 - w) * Jn["k"] + w * Jn["s"]).values; idxb = np.arange(len(Jn))
            bt = np.array([sh(comb[bi := RNG.choice(idxb, len(idxb), True)]) - sh(ko[bi]) for _ in range(2000)])
            impr = round(sh(comb) - sh(ko), 3); sig = bool(np.percentile(bt, 2.5) > 0)
            if best is None or impr > best["impr"]:
                best = dict(w=w, impr=impr, sig=sig, ci=[round(float(np.percentile(bt, 2.5)), 3), round(float(np.percentile(bt, 97.5)), 3)])
        # per-year worst: combined vs king at best w
        wbest = best["w"]; comb_s = (1 - wbest) * Jn["k"] + wbest * Jn["s"]
        yy = pd.to_datetime(J.index).year
        py = {int(y): dict(king=round(sh(Jn["k"].values[yy == y]), 2), comb=round(sh(comb_s.values[yy == y]), 2)) for y in sorted(set(yy))}
        marg[str(c)] = dict(rho=round(rho, 3), Sk=round(Sk, 2), Ss=round(Ss, 2), improve_rule=bool(Ss > rho * Sk),
                            rho_Sk=round(rho * Sk, 2), best_blend=best, per_year_king_vs_comb=py)
        print(f"[c={c}] rho {rho:.3f} Sk {Sk:.2f} Ss {Ss:.2f} improve={Ss>rho*Sk} | best w{best['w']} {best['impr']:+} sig{best['sig']} CI{best['ci']}", flush=True)

    sign_consistent = all(x["incremental_ic"] > 0 for x in per_year)
    gate_c_sig = any(marg[c]["best_blend"]["sig"] for c in marg)
    result = dict(title="ARM-S2 5yr FINAL (32ch)", created="2026-07-14", auditor="0C",
                  panel_md5=md5(S2 + "/panel_ref.npz"), ts_aligned_king=True, nch=32,
                  incremental_ic_pooled=round(float(i.mean()), 4), incremental_ci95=list(ci),
                  raw_ic_pooled=round(float(r.mean()), 4), pred_corr_pooled=round(float(p.mean()), 3),
                  per_year=per_year, sign_consistent=sign_consistent,
                  book_margin=marg, gate_c_bootstrap_sig=gate_c_sig,
                  gate_a_pass=bool(i.mean() >= 0.003 and ci[0] > 0 and sign_consistent),
                  gate_b_pass=bool(p.mean() < 0.7),
                  gate_c_pass=bool(gate_c_sig or all(marg[c]["improve_rule"] for c in marg)))
    json.dump(result, open(EDA + "arm_s2_5yr_score.json", "w"), indent=2, default=str)
    print(f"\nPOOLED incr {i.mean():+.4f} CI{ci} sign-consistent {sign_consistent} | gate_c boot-sig {gate_c_sig}", flush=True)
    print("SAVED " + EDA + "arm_s2_5yr_score.json", flush=True)

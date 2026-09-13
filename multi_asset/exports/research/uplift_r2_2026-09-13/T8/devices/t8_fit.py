#!/usr/bin/env python3
"""t8_fit.py — PREREG_T8 §5/§6: the 80 observed fits (2 models x 4 targets x 2 arm seeds x 5 folds) and every §6 statistic:
pooled / per-fold / within-fold / 2023-26 Pearson + Spearman, UTC-day block bootstrap CI (k=0 streams [20260905,b], k=9 streams [20260905,18000+b]),
size readouts, quintile table, model internals, shift spectrum, dominance decomposition, C4 price-part correlation.
Requires the build receipt (ALL_PASS) and a complete null (r = 0..499 exactly once) BEFORE any observed fit. No verdict logic here (t8_judge.py).
Writes out/T8_oos.npz and receipts/RECEIPT_T8_fit.json. Launch: devices/run_t8.sh t8_fit.py"""
import os, sys, time, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t8_common as C
ENV = C.check_env(sys.argv)
import numpy as np
import lightgbm
t0 = time.time()
SELF = C.sha256(os.path.abspath(__file__)); COMMON = C.sha256(C.__file__); PRE = C.check_prereg()
ST0 = C.sysstate(); assert C.gpu_idle(ST0), ("GPU not idle before start", ST0["gpu"])
BPATH = C.T8 + "/receipts/RECEIPT_T8_build.json"; B = json.load(open(BPATH))
assert B["ALL_PASS"] is True and B["common_sha256"] == COMMON and B["self_sha256"] == C.sha256(C.T8 + "/devices/t8_build.py")
DATA = C.T8 + "/out/T8_data.npz"; assert C.sha256(DATA) == B["out"]["sha256"]
NULL_SELF = C.sha256(C.T8 + "/devices/t8_null.py"); seen = []
for p in sorted(glob.glob(C.T8 + "/receipts/RECEIPT_T8_null_*.json")):
    N = json.load(open(p))
    assert N["self_sha256"] == NULL_SELF and N["common_sha256"] == COMMON and N["data_sha256"] == B["out"]["sha256"], ("null receipt version mismatch", p)
    seen += [row["r"] for row in N["rows"]]
assert sorted(seen) == list(range(C.NNULL)), ("null incomplete or duplicated", len(seen))
print(f"T8 fit start {ST0['utc']} self {SELF[:12]}; null complete ({len(seen)} permutations)", flush=True)

Z = np.load(DATA, allow_pickle=False)
ts = Z["ts"].astype(np.int64); FL = C.folds(ts); A = np.arange(C.ALPHA0, C.N_FULL)
S = np.asarray(Z["S"], np.float64)
day = ((ts[A] - ts[C.ALPHA0]) // 86400).astype(np.int64); nd = int(day.max()) + 1; assert nd == C.NDAYS_ALPHA and np.bincount(day).min() == 6
C0 = C.draw_counts(nd, 0); C9 = C.draw_counts(nd, 9 * C.NB)
fold_of = np.full(C.N_FULL, -1)
for q, (_, _, te) in enumerate(FL):
    fold_of[te] = q
KS = (-2, -1, 0, 1, 2, 3)


def rstats(x, y):
    mom = C.day_moments(x, y, day, nd); b0 = C.boot_r(C0, mom); b9 = C.boot_r(C9, mom)
    return dict(r=C.pearson(x, y), ci95_k0=C.ci95(b0), ci95_k9=C.ci95(b9), se_boot_k0=float(b0.std(ddof=1)))


cells = {}; preds = {}
for s in C.SEEDS:
    F = np.asarray(Z["F_" + s], np.float64)
    preps = [C.FoldPrep(F, tr, te) for _, tr, te in FL]
    Y = {t: np.asarray(Z[t + "_" + s], np.float64) for t in ("NET", "LONG", "SHORT", "CARRY", "PRICE", "COST")}
    for t in C.TARGETS:
        y = Y[t]
        for m in C.MODELS:
            p, trp, info = C.oos(preps, y, m)
            preds[f"{m}_{t}_s{s}"] = p
            pa, ya = p[A], y[A]
            o = dict(model=m, target=t, seed=s)
            o["pool"] = rstats(pa, ya); o["rho_pool"] = C.spearman(pa, ya)
            o["folds"] = []
            for q, ((nm, tr, te), P) in enumerate(zip(FL, preps)):
                pf, yf = p[te], y[te]
                o["folds"].append(dict(fold=nm, n_test=int(te.sum()), n_train=int(len(P.tr_idx)), n_train_dropped=P.n_drop, n_test_imputed=P.n_imp,
                                       zero_std_features=[C.FEATS[z] for z in P.zero], r=C.pearson(pf, yf), rho=C.spearman(pf, yf),
                                       mean_target=float(yf.mean()), mean_pred=float(pf.mean()), sd_pred=float(pf.std()), train_mean_target=float(y[P.tr_idx].mean())))
            fq = fold_of[A]
            pw = pa - np.array([pa[fq == q].mean() for q in range(5)])[fq]; yw = ya - np.array([ya[fq == q].mean() for q in range(5)])[fq]
            o["r_within"] = C.pearson(pw, yw)
            m2326 = fq >= 1; o["r_2326"] = C.pearson(pa[m2326], ya[m2326])
            mf = np.array([y[P.tr_idx].mean() for P in preps])[fq]
            o["oos_r2_vs_train_mean"] = float(1.0 - ((ya - pa) ** 2).sum() / ((ya - mf) ** 2).sum())
            vp = pa.var(); o["calibration_slope"] = float(((pa - pa.mean()) * (ya - ya.mean())).mean() / vp) if vp > 0 else float("nan")
            o["hit_rate"] = float((np.sign(pa) == np.sign(ya)).mean()); o["base_rate"] = float(max((ya > 0).mean(), (ya < 0).mean()))
            qb = np.full(len(A), -1)
            for q, P in enumerate(preps):
                edges = np.quantile(trp[q], [0.2, 0.4, 0.6, 0.8]); sel = fq == q
                qb[sel] = np.searchsorted(edges, pa[sel], side="right")
            o["quintiles"] = [dict(q=int(b), n=int((qb == b).sum()), mean_target=(float(ya[qb == b].mean()) if (qb == b).any() else None),
                                   mean_pred=(float(pa[qb == b].mean()) if (qb == b).any() else None)) for b in range(5)]
            if m == "R":
                o["ridge"] = [dict(fold=FL[q][0], intercept=inf["intercept"], alpha=inf["alpha"], beta={C.FEATS[z]: float(inf["beta"][z]) for z in range(C.NF)}) for q, inf in enumerate(info)]
            else:
                o["lgbm"] = [dict(fold=FL[q][0], num_trees=int(inf["num_trees"]), gain={C.FEATS[z]: float(inf["gain"][z]) for z in range(C.NF)}) for q, inf in enumerate(info)]
            spec = {}
            for k in KS:
                ii = A[(A + k >= 0) & (A + k < C.N_FULL)]
                spec[str(k)] = dict(r=C.pearson(p[ii], y[ii + k]), n=int(len(ii)))
            o["spectrum"] = spec
            if t in C.SUBST:
                bS = np.full(C.N_FULL, np.nan); betas = []
                for q, P in enumerate(preps):
                    tri = P.tr_idx[np.isfinite(S[P.tr_idx])]
                    xs, ys = S[tri], y[tri]
                    beta = float(((xs - xs.mean()) * (ys - ys.mean())).sum() / ((xs - xs.mean()) ** 2).sum())
                    betas.append(beta); bS[P.te_idx] = beta * S[P.te_idx]
                okS = np.isfinite(bS[A])
                pS, yS, bSa = pa[okS], ya[okS], bS[A][okS]
                e = yS - bSa
                num = ((pS - pS.mean()) * (bSa - bSa.mean())).sum(); den = ((pS - pS.mean()) * (yS - yS.mean())).sum()
                mom_e = C.day_moments(pS, e, day[okS], nd)
                o["decomp"] = dict(beta_by_fold=betas, n_rows=int(okS.sum()), share_S=(float(num / den) if den != 0 else float("nan")),
                                   r_S=C.pearson(pS, S[A][okS]), r_e=C.pearson(pS, e), r_e_ci95_k0=C.ci95(C.boot_r(C0, mom_e)), r_e_ci95_k9=C.ci95(C.boot_r(C9, mom_e)))
            if t == "NET":
                o["C4_price"] = rstats(pa, Y["PRICE"][A])
            cells[f"{m}_{t}_s{s}"] = o
            print(f"  cell {m}_{t}_s{s} done {time.time()-t0:.0f}s", flush=True)

OUT = C.T8 + "/out/T8_oos.npz"
np.savez_compressed(OUT, ts=ts, **preds); assert os.path.getsize(OUT) < 500 * 2 ** 20
R = dict(device="t8_fit.py", self_sha256=SELF, common_sha256=COMMON, prereg_sha256=PRE, env=ENV, lightgbm=lightgbm.__version__, sys_before=ST0,
         build_receipt_sha256=C.sha256(BPATH), data_sha256=B["out"]["sha256"], null_device_sha256=NULL_SELF, lgb_params=C.LGB_PARAMS, lgb_rounds=C.LGB_ROUNDS,
         bootstrap=dict(nb=C.NB, n_days=nd, k0_streams="[20260905, b], b=0..1999", k9_streams="[20260905, 18000+b], b=0..1999"),
         out=dict(path=OUT, sha256=C.sha256(OUT), size=os.path.getsize(OUT)), cells=cells)
R["sys_after"] = C.sysstate(); R["wall_s"] = round(time.time() - t0, 1)
C.jdump(R, C.T8 + "/receipts/RECEIPT_T8_fit.json")
print(f"T8_FIT_DONE cells={len(cells)} oos_sha={R['out']['sha256'][:16]} wall_s={R['wall_s']}", flush=True)

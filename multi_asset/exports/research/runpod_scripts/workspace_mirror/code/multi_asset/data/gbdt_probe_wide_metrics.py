#!/usr/bin/env python3
"""GBDT NON-LINEAR probe for wide-metrics channels (Ridge/linear gate FAILED).

Hypothesis (per track-2 design): OI/positioning has no LINEAR increment but may
carry value in NON-LINEAR interactions (e.g. residual reversal conditioned on OI
crowding / L-S positioning). Tests baseline-32ch GBDT vs baseline+7metrics GBDT,
same YR4 residual target, same CL4 clean walk-forward folds as the Ridge gate.

Gate (== pre-registered factory rule): dIC >= +0.003 & per-fold sign-consistent
& metrics-block time-shuffle null (real dIC beats null, z>2). Plus shuffled-target
leak guard (train on within-ts-shuffled target -> OOS IC ~0).

Reuses 0C's gbdt_probe.py design: heavy-reg LightGBM, target standardization
(bps-scale target else L1/L2 dwarfs split gains -> constant model), no early stop.
"""
import json, argparse, numpy as np
from scipy.stats import rankdata
import lightgbm as lgb

PANEL = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl_full.npz"
LGB = dict(objective="regression", n_estimators=500, learning_rate=0.02, num_leaves=15,
           max_depth=4, min_child_samples=300, feature_fraction=0.6, bagging_fraction=0.7,
           bagging_freq=1, lambda_l1=1.0, lambda_l2=5.0, verbosity=-1, n_jobs=16)
MIN_ASSETS = 10


def xsec_standardize(X, member):
    m = member[:, :, None]
    Xm = np.where(m & np.isfinite(X), X, np.nan)
    mu = np.nanmean(Xm, axis=1, keepdims=True); sd = np.nanstd(Xm, axis=1, keepdims=True)
    sd = np.where(sd < 1e-9, 1.0, sd)
    Z = (Xm - mu) / sd
    return np.clip(np.where(np.isfinite(Z), Z, 0.0), -6, 6)


def _ric(a, b):
    ra, rb = rankdata(a), rankdata(b); ra = ra - ra.mean(); rb = rb - rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d > 1e-12 else np.nan


def xs_ic(pred, targ, ts_row):
    ics = []
    for t in np.unique(ts_row):
        m = ts_row == t
        if m.sum() < MIN_ASSETS:
            continue
        p, y = pred[m], targ[m]
        if np.std(p) > 1e-12 and np.std(y) > 1e-12:
            ic = _ric(p, y)
            if np.isfinite(ic):
                ics.append(ic)
    return np.array(ics)


def fit_predict_folds(Xfull, y_std, y_eval, ts_row, ts_index, fold_bounds, seed=0):
    """Train LightGBM per expanding fold, return per-fold mean xsec rank-IC (vs y_eval)."""
    ics = []
    for (tr_lo, tr_hi, te_lo, te_hi) in fold_bounds:
        tr = (ts_index >= tr_lo) & (ts_index < tr_hi)
        te = (ts_index >= te_lo) & (ts_index < te_hi)
        if tr.sum() < 1000 or te.sum() < 200:
            ics.append(np.nan); continue
        m = lgb.LGBMRegressor(**LGB, random_state=seed)
        m.fit(Xfull[tr], y_std[tr])
        pred = m.predict(Xfull[te])
        ic = xs_ic(pred, y_eval[te], ts_row[te])
        ics.append(float(np.mean(ic)) if len(ic) else np.nan)
    return np.array(ics)


def run(metrics_npz, out_json, out_md, n_null=8, seed=0):
    P = np.load(PANEL, allow_pickle=True)
    ts = P["ts"].astype(np.int64); ch_names = list(P["ch_names"])
    CHb = P["CH"].astype(np.float64); member = P["MEMBER110"]
    yr4 = P["YR4"].astype(np.float64); cl4 = P["CL4"]
    T, N, Fb = CHb.shape
    M = np.load(metrics_npz, allow_pickle=True)
    new_names = list(M["ch_names"]); CHn = np.where(M["MASK"], M["CH"].astype(np.float64), np.nan)

    emask = member & cl4 & np.isfinite(yr4)
    mu = np.nanmean(np.where(emask, yr4, np.nan), axis=1, keepdims=True)
    ytarg = np.where(emask, yr4 - mu, 0.0)                # per-ts demeaned residual target

    Zb = xsec_standardize(CHb, member)                   # [T,N,32]
    Zn = xsec_standardize(CHn, member)                   # [T,N,7]

    # flatten eval cells -> rows, keep ts + ts_index for folds
    ev = np.where(emask)
    ts_row = ts[ev[0]]; ts_index = ev[0]
    y_eval = ytarg[ev]
    y_std = (y_eval - y_eval.mean()) / (y_eval.std() + 1e-12)
    Xb = Zb[ev]                                           # [Nrows,32]
    Xn = Zn[ev]                                           # [Nrows,7]
    Xfam = np.concatenate([Xb, Xn], axis=1)              # [Nrows,39]

    # folds identical caliber to ridge gate: expanding, 35% seed train, 6 test blocks
    ev_ts_sorted = np.unique(ts_index)
    fr = [0.35, 0.4583, 0.5667, 0.675, 0.7833, 0.8917, 1.0]
    cuts = [int(np.quantile(np.arange(len(ev_ts_sorted)), f)) for f in fr]
    blk = []
    prev = cuts[0]
    for c in cuts[1:]:
        blk.append((ev_ts_sorted[prev], ev_ts_sorted[min(c, len(ev_ts_sorted) - 1)])); prev = c
    fold_bounds = [(0, b0, b0, b1) for (b0, b1) in blk]

    res = {"n_rows": int(len(y_eval)), "n_folds": len(fold_bounds), "LGB": {k: LGB[k] for k in ["n_estimators","num_leaves","max_depth","min_child_samples","lambda_l2"]}}

    base_ic = fit_predict_folds(Xb, y_std, y_eval, ts_row, ts_index, fold_bounds)
    fam_ic = fit_predict_folds(Xfam, y_std, y_eval, ts_row, ts_index, fold_bounds)
    dIC = fam_ic - base_ic
    res["base_ic_folds"] = [round(float(x), 4) for x in base_ic]
    res["fam_ic_folds"] = [round(float(x), 4) for x in fam_ic]
    res["dIC_folds"] = [round(float(x), 4) for x in dIC]
    res["base_ic_mean"] = round(float(np.nanmean(base_ic)), 4)
    res["fam_ic_mean"] = round(float(np.nanmean(fam_ic)), 4)
    res["dIC_mean"] = round(float(np.nanmean(dIC)), 4)
    res["sign_consistent"] = bool(np.all(dIC[np.isfinite(dIC)] > 0) or np.all(dIC[np.isfinite(dIC)] < 0))

    # metrics-block time-shuffle null: permute Zn over time, re-flatten family, retrain
    rng = np.random.default_rng(seed); null_d = []
    for k in range(n_null):
        Znull = Zn[rng.permutation(T)]
        Xfam_n = np.concatenate([Xb, Znull[ev]], axis=1)
        fam_n = fit_predict_folds(Xfam_n, y_std, y_eval, ts_row, ts_index, fold_bounds, seed=k)
        null_d.append(float(np.nanmean(fam_n - base_ic)))
    null_d = np.array(null_d)
    z = (res["dIC_mean"] - np.nanmean(null_d)) / (np.nanstd(null_d) + 1e-12)
    res["null"] = {"mean": round(float(np.nanmean(null_d)), 4), "std": round(float(np.nanstd(null_d)), 4),
                   "z": round(float(z), 2), "n": n_null}

    # leak guard: within-ts shuffle of target, train family -> OOS IC must be ~0
    yl = y_eval.copy()
    for t in np.unique(ts_row):
        idx = np.where(ts_row == t)[0]
        if len(idx) >= MIN_ASSETS:
            yl[idx] = y_eval[idx[rng.permutation(len(idx))]]
    yl_std = (yl - yl.mean()) / (yl.std() + 1e-12)
    leak_ic = fit_predict_folds(Xfam, yl_std, y_eval, ts_row, ts_index, fold_bounds)
    res["leak_guard_ic_mean"] = round(float(np.nanmean(leak_ic)), 4)
    res["leak_ok"] = bool(abs(np.nanmean(leak_ic)) < max(0.005, 0.3 * abs(res["dIC_mean"])))

    passed = (res["dIC_mean"] >= 0.003) and res["sign_consistent"] and (z > 2.0) and res["leak_ok"]
    res["GATE_PASS"] = bool(passed)

    with open(out_json, "w") as f:
        json.dump(res, f, indent=1)
    L = []
    L.append("# Wide-metrics GBDT non-linear probe (YR4 residual, xsec rank-IC, walk-forward)\n\n")
    L.append("- rows=%d  folds=%d  LightGBM(leaves=%d,depth=%d,l2=%s,n_est=%d)\n" % (
        res["n_rows"], res["n_folds"], LGB["num_leaves"], LGB["max_depth"], LGB["lambda_l2"], LGB["n_estimators"]))
    L.append("- baseline(32ch) GBDT IC = %.4f  folds=%s\n" % (res["base_ic_mean"], res["base_ic_folds"]))
    L.append("- +7 metrics family GBDT IC = %.4f  folds=%s\n" % (res["fam_ic_mean"], res["fam_ic_folds"]))
    L.append("- **dIC = %+.4f**  per-fold=%s  sign_consistent=%s\n" % (
        res["dIC_mean"], res["dIC_folds"], res["sign_consistent"]))
    L.append("- metrics-block shuffle null dIC = %+.4f +/- %.4f  z=%.2f\n" % (
        res["null"]["mean"], res["null"]["std"], res["null"]["z"]))
    L.append("- leak-guard (shuffled target) IC = %+.4f  (%s)\n" % (
        res["leak_guard_ic_mean"], "CLEAN" if res["leak_ok"] else "LEAK!"))
    L.append("- **GATE: %s**  (need dIC>=+0.003 & sign-consistent & z>2 & leak-clean)\n" % (
        "PASS" if passed else "FAIL"))
    with open(out_md, "w") as f:
        f.write("".join(L))
    print("".join(L))
    print("GBDT GATE PASS =", passed)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--out_json", required=True)
    ap.add_argument("--out_md", required=True)
    ap.add_argument("--n_null", type=int, default=8)
    a = ap.parse_args()
    run(a.metrics, a.out_json, a.out_md, a.n_null)

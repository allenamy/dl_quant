#!/usr/bin/env python3
"""Ridge pre-gate for wide-metrics channels vs the existing 32-channel factor book.
Metric: cross-sectional rank-IC on CL4 non-overlapping clean samples, walk-forward.
Gate: dIC >= +0.003 AND per-fold sign-consistent AND real dIC beats shuffle-future null.
"""
import os, json, argparse, numpy as np
from scipy.stats import rankdata

PANEL = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl_full.npz"


def xsec_standardize(X, member):
    # X: [T,N,F]; standardize per-t across member assets; NaN->0 (neutral)
    m = member[:, :, None]
    Xm = np.where(m & np.isfinite(X), X, np.nan)
    mu = np.nanmean(Xm, axis=1, keepdims=True)
    sd = np.nanstd(Xm, axis=1, keepdims=True)
    sd = np.where(sd < 1e-9, 1.0, sd)
    Z = (Xm - mu) / sd
    Z = np.where(np.isfinite(Z), Z, 0.0)
    return np.clip(Z, -6, 6)


def per_ts_spearman(pred, targ, eval_mask, ts_idx):
    ics = []
    for t in ts_idx:
        msk = eval_mask[t]
        if msk.sum() < 10:
            continue
        p = pred[t, msk]; y = targ[t, msk]
        if np.std(p) < 1e-12 or np.std(y) < 1e-12:
            continue
        ic = np.corrcoef(rankdata(p), rankdata(y))[0, 1]
        if np.isfinite(ic):
            ics.append(ic)
    return (float(np.mean(ics)) if ics else np.nan), len(ics)


def run(metrics_npz, out_json, out_md, alpha=100.0, n_null=20, seed=0):
    P = np.load(PANEL, allow_pickle=True)
    ts = P["ts"].astype(np.int64); ch_names = list(P["ch_names"])
    CHb = P["CH"].astype(np.float64)
    member = P["MEMBER110"]; yr4 = P["YR4"].astype(np.float64); cl4 = P["CL4"]
    T, N, Fb = CHb.shape
    M = np.load(metrics_npz, allow_pickle=True)
    new_names = list(M["ch_names"]); CHn = M["CH"].astype(np.float64); MASKn = M["MASK"]
    CHn = np.where(MASKn, CHn, np.nan)

    emask = member & cl4 & np.isfinite(yr4)
    mu = np.nanmean(np.where(emask, yr4, np.nan), axis=1, keepdims=True)
    ytarg = np.where(emask, yr4 - mu, 0.0)

    Zb = xsec_standardize(CHb, member)
    Zn = xsec_standardize(CHn, member)

    ev_ts = np.where(emask.any(1))[0]
    fracs = [0.35, 0.4583, 0.5667, 0.675, 0.7833, 0.8917, 1.0]
    cuts = [int(np.quantile(np.arange(len(ev_ts)), f)) for f in fracs]
    blocks = []
    prev = cuts[0]
    for c in cuts[1:]:
        blocks.append((ev_ts[prev], ev_ts[min(c, len(ev_ts) - 1)])); prev = c

    def flat_fit_eval(Zlist, tr_lo, tr_hi, te_lo, te_hi):
        Z = np.concatenate(Zlist, axis=2)
        tr = emask.copy(); tr[:tr_lo] = False; tr[tr_hi:] = False
        te = emask.copy(); te[:te_lo] = False; te[te_hi:] = False
        Xtr = Z[tr]; ytr = ytarg[tr]
        pred = np.zeros((T, N))
        if Xtr.shape[0] > 500:
            A = Xtr.T @ Xtr + alpha * np.eye(Xtr.shape[1])
            w = np.linalg.solve(A, Xtr.T @ ytr)
            pred = (Z.reshape(-1, Z.shape[2]) @ w).reshape(T, N)
        tsidx = np.where(te.any(1))[0]
        return per_ts_spearman(pred, ytarg, te, tsidx)

    fold_bounds = [(0, b0, b0, b1) for (b0, b1) in blocks]

    results = {"alpha": alpha, "folds": [], "per_channel": {}, "family": {}}
    base_ics = []; fam_ics = []
    for (tr_lo, tr_hi, te_lo, te_hi) in fold_bounds:
        ib, _ = flat_fit_eval([Zb], tr_lo, tr_hi, te_lo, te_hi)
        iff, _ = flat_fit_eval([Zb, Zn], tr_lo, tr_hi, te_lo, te_hi)
        base_ics.append(ib); fam_ics.append(iff)
        results["folds"].append({"te_lo": int(te_lo), "te_hi": int(te_hi),
                                 "base_ic": ib, "family_ic": iff, "d": iff - ib})
    base_ics = np.array(base_ics); fam_ics = np.array(fam_ics)
    dfam = fam_ics - base_ics
    results["family"] = {"base_ic_mean": float(np.nanmean(base_ics)),
                         "family_ic_mean": float(np.nanmean(fam_ics)),
                         "dIC_mean": float(np.nanmean(dfam)),
                         "dIC_per_fold": [float(x) for x in dfam],
                         "sign_consistent": bool(np.all(dfam > 0) or np.all(dfam < 0))}

    for ci, name in enumerate(new_names):
        Zc = Zn[:, :, ci:ci + 1]
        ics = []
        for (tr_lo, tr_hi, te_lo, te_hi) in fold_bounds:
            ic1, _ = flat_fit_eval([Zb, Zc], tr_lo, tr_hi, te_lo, te_hi)
            ics.append(ic1)
        d = np.array(ics) - base_ics
        results["per_channel"][name] = {"dIC_mean": float(np.nanmean(d)),
                                        "dIC_per_fold": [float(x) for x in d],
                                        "sign_consistent": bool(np.all(d > 0) or np.all(d < 0))}

    rng = np.random.default_rng(seed)
    null_d = []
    for k in range(n_null):
        Znull = Zn[rng.permutation(T)]
        d_folds = []
        for j, (tr_lo, tr_hi, te_lo, te_hi) in enumerate(fold_bounds):
            ifn, _ = flat_fit_eval([Zb, Znull], tr_lo, tr_hi, te_lo, te_hi)
            d_folds.append(ifn - base_ics[j])
        null_d.append(np.nanmean(d_folds))
    null_d = np.array(null_d)
    z = (results["family"]["dIC_mean"] - np.nanmean(null_d)) / (np.nanstd(null_d) + 1e-12)
    results["null"] = {"null_dIC_mean": float(np.nanmean(null_d)),
                       "null_dIC_std": float(np.nanstd(null_d)),
                       "real_dIC": results["family"]["dIC_mean"], "z": float(z), "n_null": n_null}

    fam = results["family"]
    passed = (fam["dIC_mean"] >= 0.003) and fam["sign_consistent"] and (z > 2.0)
    results["GATE_family_PASS"] = bool(passed)
    with open(out_json, "w") as f:
        json.dump(results, f, indent=1)

    per_fold = [round(x, 4) for x in fam["dIC_per_fold"]]
    L = []
    L.append("# Wide-metrics Ridge pre-gate (YR4 residual, xsec rank-IC, walk-forward)\n\n")
    L.append("- alpha=%s  folds=%d  null_perms=%d\n" % (alpha, len(fold_bounds), n_null))
    L.append("- baseline(32ch) IC mean = %.4f\n" % fam["base_ic_mean"])
    L.append("- +7 metrics family IC mean = %.4f  dIC = %+.4f\n" % (fam["family_ic_mean"], fam["dIC_mean"]))
    L.append("- family per-fold dIC = %s  sign_consistent=%s\n" % (per_fold, fam["sign_consistent"]))
    L.append("- shuffle-future null dIC = %+.4f +/- %.4f  z=%.2f\n" % (
        results["null"]["null_dIC_mean"], results["null"]["null_dIC_std"], z))
    L.append("- **GATE (family): %s**  (need dIC>=+0.003 & sign-consistent & z>2)\n\n" % ("PASS" if passed else "FAIL"))
    L.append("## Per-channel incremental dIC (baseline + single channel)\n\n")
    L.append("| channel | dIC_mean | sign_consistent | per_fold |\n|---|---|---|---|\n")
    for name, r in results["per_channel"].items():
        L.append("| %s | %+.4f | %s | %s |\n" % (
            name, r["dIC_mean"], r["sign_consistent"], [round(x, 4) for x in r["dIC_per_fold"]]))
    with open(out_md, "w") as f:
        f.write("".join(L))
    print("".join(L))
    print("GATE family PASS =", passed)
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--out_json", required=True)
    ap.add_argument("--out_md", required=True)
    ap.add_argument("--alpha", type=float, default=100.0)
    ap.add_argument("--n_null", type=int, default=20)
    a = ap.parse_args()
    run(a.metrics, a.out_json, a.out_md, a.alpha, a.n_null)

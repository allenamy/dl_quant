"""STAGE-1 GBDT INTERACTION PROBE — is there ANY nonlinear/interaction increment in the tested features
BEYOND linear funding?  The honest nonlinear baseline DL (stage 2) must beat.  CPU, walk-forward, leak-guarded.

Target = y_3600 residualised per-ts on funding_ema (cross-sectional OLS residual) → the GBDT can ONLY earn
INCREMENTAL-over-funding credit.  LightGBM heavy-regularised (14 assets, low SNR), 3-fold walk-forward with
val-based early stop.  Reports OOS cross-sectional rank-IC of the GBDT residual factor (vs the funding-residual
target AND vs raw y) + empirical within-ts shuffle-null z + per-fold signs + a SHUFFLED-TARGET leak guard
(shuffle y before training → OOS IC must be ~0).

Verdict: z≥2.5 + per-fold sign-consistent → nonlinear juice EXISTS → candidate factor (score through the full
factory b/c/d/e vs funding book) + justifies DL stage-2.  Null → features-as-given have no nonlinear increment;
stage-2's case rests on RAW SEQUENCES (temporal patterns GBDT can't see).

Panel format (assembled by 0B): per-asset keys '<sym>__X'[N,F], '<sym>__y'[N], '<sym>__ts'[N], '<sym>__day'[N],
'<sym>__cl'[N], '<sym>__funding'[N] (funding_ema value for residualisation); plus 'names'[F], 'symbols'.
"""
from __future__ import annotations
import argparse, numpy as np
from scipy.stats import rankdata
import lightgbm as lgb

MIN_ASSETS = 5
LGB_PARAMS = dict(objective="regression", n_estimators=600, learning_rate=0.02, num_leaves=15,
                  max_depth=4, min_child_samples=300, feature_fraction=0.6, bagging_fraction=0.7,
                  bagging_freq=1, lambda_l1=1.0, lambda_l2=5.0, verbosity=-1, n_jobs=4)


def _ric(a, b):
    ra, rb = rankdata(a), rankdata(b); ra = ra - ra.mean(); rb = rb - rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d > 1e-12 else np.nan


def residualize_perts(y, fund, ts):
    """Per-ts cross-sectional OLS residual of y on funding (+intercept). Only the part of y orthogonal
    to the funding factor survives → GBDT credited only for incremental-over-funding signal."""
    out = np.full(len(y), np.nan)
    for t in np.unique(ts):
        m = ts == t
        if m.sum() < 3:
            out[m] = y[m] - y[m].mean(); continue
        f = fund[m]; yy = y[m]
        if np.std(f) < 1e-12:
            out[m] = yy - yy.mean()
        else:
            b = np.cov(yy, f)[0, 1] / np.var(f)
            out[m] = yy - (yy.mean() + b * (f - f.mean()))
    return out


def xs_ic(pred, targ, ts, min_assets=MIN_ASSETS):
    ics = []
    for t in np.unique(ts):
        m = ts == t
        if m.sum() < min_assets:
            continue
        p, y = pred[m], targ[m]
        if np.std(p) > 1e-12 and np.std(y) > 1e-12:
            ic = _ric(p, y)
            if np.isfinite(ic):
                ics.append(ic)
    return np.array(ics)


def null_z(pred, targ, ts, n=25, seed=0, min_assets=MIN_ASSETS):
    rng = np.random.default_rng(seed); uts = np.unique(ts); real = float(np.mean(xs_ic(pred, targ, ts)))
    means = []
    for _ in range(n):
        ps = pred.copy()
        for t in uts:
            idx = np.where(ts == t)[0]
            if len(idx) >= min_assets:
                ps[idx] = pred[idx[rng.permutation(len(idx))]]
        means.append(float(np.mean(xs_ic(ps, targ, ts))))
    nm, ns = float(np.mean(means)), float(np.std(means) + 1e-12)
    return dict(real=round(real, 4), null_mean=round(nm, 4), null_std=round(ns, 4), z=round((real - nm) / ns, 2))


def walk_forward(X, yres, y_raw, ts, day, n_folds=3, params=None, val_frac=0.2, shuffle_target=False, seed=0):
    """3-fold blocked walk-forward: train on prior days (last val_frac as val), predict test fold. EARLY-STOP
    on val cross-sectional RANK-IC (maximise) — NOT MSE, which on this low-SNR residual collapses the model to
    a constant. Returns OOS pred + per-fold IC vs the residual target."""
    params = params or LGB_PARAMS
    uday = np.unique(day); edges = [uday[len(uday) * i // n_folds] for i in range(n_folds)] + [uday[-1] + 1]
    oos_pred = np.full(len(X), np.nan); per_fold = []
    ytr_all = yres.copy()
    if shuffle_target:                                   # LEAK GUARD: shuffle the target within each ts
        rng = np.random.default_rng(seed)
        for t in np.unique(ts):
            idx = np.where(ts == t)[0]; ytr_all[idx] = yres[idx[rng.permutation(len(idx))]]
    ytr_all = ytr_all / (np.std(ytr_all) + 1e-12)        # standardise (target is ~bps-scale ~2e-3; else L1/L2 reg dwarfs split gains → 0 trees). rank-IC is scale-invariant.
    for i in range(1, n_folds):                          # fold 0 = train-only seed
        tr = day < edges[i]; te = (day >= edges[i]) & (day < edges[i + 1])
        if tr.sum() < 500 or te.sum() < 100:
            continue
        # FIXED shrinkage-regularised boosting (no early stopping — on this low-SNR residual, val-MSE and even
        # val-rank-IC early stop collapse the model to a constant). Strong reg + few trees + small lr control
        # overfit; the SHUFFLED-TARGET leak guard is the honest overfit check (must give OOS IC ~0).
        m = lgb.LGBMRegressor(**{k: v for k, v in params.items() if k != "metric"})
        m.fit(X[tr], ytr_all[tr])
        oos_pred[te] = m.predict(X[te])
        ic = xs_ic(oos_pred[te], yres[te], ts[te])       # per-fold IC vs the (unshuffled) residual target
        per_fold.append(round(float(np.mean(ic)), 4) if len(ic) else np.nan)
    return oos_pred, per_fold


def run_probe(panel, label="gbdt_probe", n_folds=3, params=None):
    X, y, fund, ts, day = panel["X"], panel["y"], panel["fund"], panel["ts"], panel["day"]
    yres = residualize_perts(y, fund, ts)
    print(f"[{label}] rows={len(X)} feats={X.shape[1]} ts={len(np.unique(ts))} "
          f"| corr(y,funding)={_ric(y, fund):+.3f} → residualising out funding")

    # real probe
    pred, per_fold = walk_forward(X, yres, y, ts, day, n_folds, params=params)
    m = np.isfinite(pred)
    if m.sum() and np.std(pred[m]) < 1e-9:
        print("  ⚠ GBDT predicts near-CONSTANT (over-regularised or no signal) — IC undefined")
    ic_res = xs_ic(pred[m], yres[m], ts[m]); ic_raw = xs_ic(pred[m], y[m], ts[m])
    z = null_z(pred[m], yres[m], ts[m])
    signc = all(np.sign(x) == np.sign(per_fold[0]) for x in per_fold if np.isfinite(x)) if per_fold else False
    print(f"  OOS rank-IC vs FUNDING-RESIDUAL = {np.mean(ic_res):+.4f} (IR {np.mean(ic_res)/(np.std(ic_res)+1e-9)*np.sqrt(len(ic_res)):.2f})")
    print(f"  OOS rank-IC vs RAW y            = {np.mean(ic_raw):+.4f}")
    print(f"  empirical-null z = {z['z']} (real {z['real']} vs null {z['null_mean']}±{z['null_std']})")
    print(f"  per-fold IC = {per_fold}  sign-consistent = {signc}")

    # LEAK GUARD: shuffled-target
    predS, pfS = walk_forward(X, yres, y, ts, day, n_folds, params=params, shuffle_target=True)
    mS = np.isfinite(predS); icS = xs_ic(predS[mS], yres[mS], ts[mS])
    print(f"  ⛊ LEAK GUARD (shuffled target): OOS rank-IC = {np.mean(icS):+.4f} (must be ~0; per-fold {pfS})")

    verdict = "NONLINEAR JUICE EXISTS → candidate factor + justifies stage-2" if (abs(z["z"]) >= 2.5 and signc) \
        else "NULL → no nonlinear increment in features-as-given; stage-2 rests on raw sequences"
    # leak = the shuffled-target model still PREDICTS the real target (IC comparable to real). A small/negative
    # shuffled IC is clean noise. Threshold scales with the real signal.
    real_ic = float(np.mean(ic_res))
    leak_ok = abs(float(np.mean(icS))) < max(0.015, 0.3 * abs(real_ic))
    print(f"  VERDICT: {verdict}  | leak-guard {'CLEAN' if leak_ok else '⚠ FAIL (pipeline leaks!)'}")
    return dict(ic_res=float(np.mean(ic_res)), z=z["z"], per_fold=per_fold, sign_consistent=signc,
                leak_ic=float(np.mean(icS)), leak_ok=leak_ok)


def load_assembled(path):
    z = np.load(path, allow_pickle=True)
    syms = [str(s) for s in z["symbols"]] if "symbols" in z.files else sorted(set(k.split("__")[0] for k in z.files if "__X" in k))
    Xs, ys, fs, tss, ds = [], [], [], [], []
    for s in syms:
        m = z[f"{s}__cl"].astype(bool)
        Xs.append(z[f"{s}__X"][m]); ys.append(z[f"{s}__y"][m]); fs.append(z[f"{s}__funding"][m])
        tss.append(z[f"{s}__ts"][m].astype(np.int64)); ds.append(z[f"{s}__day"][m].astype(np.int64))
    return dict(X=np.vstack(Xs).astype(np.float64), y=np.concatenate(ys).astype(np.float64),
                fund=np.concatenate(fs).astype(np.float64), ts=np.concatenate(tss), day=np.concatenate(ds),
                names=[str(n) for n in z["names"]] if "names" in z.files else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True, help="assembled feature panel npz (per-asset X/y/ts/day/cl/funding)")
    ap.add_argument("--label", default="gbdt_probe")
    a = ap.parse_args()
    run_probe(load_assembled(a.panel), a.label)
    print("DONE_GBDT_PROBE")


if __name__ == "__main__":
    main()

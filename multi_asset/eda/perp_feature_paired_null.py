"""Paired block-bootstrap null for the perp feature-families gate.

The family table's `block dP` is compared against a y-PERMUTATION band, which tests
"is the family's TOTAL P above chance?". The sharper question the gate needs is
"is the family's P distinguishable from the SPOT-64 BASELINE's P?" -- i.e. is the
INCREMENT real, not just whether either model beats noise. This script answers that
with a PAIRED, day-block bootstrap on the pooled CLEAN test set:

  * Fit the baseline (SPOT-64) and a family once per STRONG fold (same walk-forward,
    full-history train, leak-free clean val/test as the main gate).
  * On the pooled clean test rows, resample TEST DAYS with replacement (block =
    one calendar day, to respect within-day autocorrelation), recompute
    Pearson(yhat_family, y) - Pearson(yhat_base, y) on the resampled rows, and
    report the bootstrap mean dP and a 95% CI. dP is "real" iff the CI excludes 0.

It caches the assembled feature/target arrays to /tmp on first run so it is cheap
to re-run (the lastts/clean/mid load is the only slow part). Reuses the main gate's
loader + walk machinery verbatim.
"""
from __future__ import annotations

import argparse
import os.path as p

import numpy as np
from scipy.stats import pearsonr

import multi_asset.eda.perp_feature_families_gate as G
from multi_asset.eda.perpY_ridge_gate import (
    EMBARGO_DAYS, MIN_TRAIN_DAYS, TEST_DAYS, VAL_DAYS, _fit_select, _predict,
)

CACHE = "/tmp/perp_feat_gate_data.npz"


def load_or_cache(verbose=True):
    if p.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True)
        if verbose:
            print(f"[cache] loaded {CACHE}  M={z['Xs'].shape[0]}")
        return {k: z[k] for k in z.files} | {"days": list(z["days"])}
    data = G.load_all(verbose=verbose)
    np.savez(CACHE, Xs=data["Xs"], Xp=data["Xp"], y=data["y"],
             basis=data["basis"], is_clean=data["is_clean"],
             day_idx=data["day_idx"], days=np.array(data["days"]))
    if verbose:
        print(f"[cache] wrote {CACHE}")
    return data


def _fold_preds(X, y, day_idx, days, is_clean, fold):
    """Return (yhat_test, y_test, test_day_of_each_row) for one fold, or None."""
    def first_ge(date):
        for i, d in enumerate(days):
            if d >= date:
                return i
        return len(days)
    ts0 = first_ge(fold["test_start"])
    te0, te1 = ts0, ts0 + TEST_DAYS
    va0, va1 = te0 - VAL_DAYS, te0
    tr0, tr1 = 0, va0 - EMBARGO_DAYS
    if te1 > len(days) or va0 < 0 or (tr1 - tr0) < MIN_TRAIN_DAYS:
        return None
    tr_m = np.isin(day_idx, list(range(tr0, tr1)))
    va_m = np.isin(day_idx, list(range(va0, va1))) & is_clean
    te_m = np.isin(day_idx, list(range(te0, te1))) & is_clean
    sel = _fit_select(X[tr_m], y[tr_m], X[va_m], y[va_m], "madz")
    if sel is None:
        return None
    w, b, c, s, sig, lam, vp = sel
    yhat = _predict(X[te_m], w, b, c, s, sig)
    return yhat, y[te_m], day_idx[te_m]


def paired_bootstrap(data, folds, fam, n_boot=2000, seed=0):
    """Pooled paired day-block bootstrap of P(fam) - P(base) over `folds`."""
    Xs, _ = G.build_family(data, "spot64")
    Xf, _ = G.build_family(data, fam)
    yh_b, yh_f, yy, dd = [], [], [], []
    for fold in folds:
        rb = _fold_preds(Xs, data["y"], data["day_idx"], data["days"],
                         data["is_clean"], fold)
        rf = _fold_preds(Xf, data["y"], data["day_idx"], data["days"],
                         data["is_clean"], fold)
        if rb is None or rf is None:
            continue
        # rb and rf use the SAME test rows (same fold/mask) -> aligned
        yh_b.append(rb[0]); yh_f.append(rf[0]); yy.append(rb[1]); dd.append(rb[2])
    if not yy:
        return None
    yh_b = np.concatenate(yh_b); yh_f = np.concatenate(yh_f)
    yy = np.concatenate(yy); dd = np.concatenate(dd)

    P_b = float(pearsonr(yh_b, yy)[0])
    P_f = float(pearsonr(yh_f, yy)[0])
    dP_point = P_f - P_b

    uniq_days = np.unique(dd)
    day_rows = {int(d): np.where(dd == d)[0] for d in uniq_days}
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.choice(uniq_days, size=uniq_days.size, replace=True)
        idx = np.concatenate([day_rows[int(d)] for d in pick])
        a, f, t = yh_b[idx], yh_f[idx], yy[idx]
        if t.std() <= 0 or a.std() <= 0 or f.std() <= 0:
            boots[i] = np.nan
            continue
        boots[i] = pearsonr(f, t)[0] - pearsonr(a, t)[0]
    boots = boots[np.isfinite(boots)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    frac_pos = float((boots > 0).mean())
    return dict(P_base=round(P_b, 4), P_fam=round(P_f, 4),
                dP_point=round(dP_point, 4),
                ci95=[round(float(lo), 4), round(float(hi), 4)],
                boot_mean=round(float(boots.mean()), 4),
                frac_boot_gt0=round(frac_pos, 3),
                excludes_zero=bool(lo > 0 or hi < 0),
                n_test=int(yy.size), n_days=int(uniq_days.size))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_boot", type=int, default=2000)
    ap.add_argument("--families", default="relative,divergence,perp64,basis,all")
    args = ap.parse_args()
    data = load_or_cache(verbose=True)

    print("\n=== PAIRED day-block bootstrap: P(family) - P(SPOT-64), STRONG folds ===")
    print(f"n_boot={args.n_boot}  block=1 calendar day  (dP real iff 95% CI excludes 0)")
    print(f"{'family':12s} {'P_base':>8s} {'P_fam':>8s} {'dP':>8s} "
          f"{'95% CI':>20s} {'boot_mean':>10s} {'P(dP>0)':>8s} {'real?':>6s}")
    for fam in args.families.split(","):
        r = paired_bootstrap(data, G.STRONG_FOLDS, fam, n_boot=args.n_boot)
        if r is None:
            print(f"{fam:12s}  unavailable")
            continue
        ci = f"[{r['ci95'][0]:+.4f},{r['ci95'][1]:+.4f}]"
        print(f"{fam:12s} {r['P_base']:+8.4f} {r['P_fam']:+8.4f} "
              f"{r['dP_point']:+8.4f} {ci:>20s} {r['boot_mean']:+10.4f} "
              f"{r['frac_boot_gt0']:8.3f} {'YES' if r['excludes_zero'] else 'no':>6s}")


if __name__ == "__main__":
    main()

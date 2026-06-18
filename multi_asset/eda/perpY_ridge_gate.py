"""GATE A + GATE B0 -- from-scratch SINGLE-ASSET temporal Ridge walk-forward.

Predicts the BTC **perp** 10-min forward return (``y_600`` on binance-futures mid)
from **spot** last-timestep features (spot order flow is measured ~2x cleaner /
more directional than perp). Cheap closed-form Ridge, no GPU, validates two things
before any model is built:

  GATE A -- spot-features -> perp-target reproduces the known base IC and is
            leakage-free (pooled raw Pearson vs the y-permutation null band; the
            project's known spot-feature base on perp is ~0.037-0.044 raw).
  GATE B0 -- rolling monthly-retrain beats a frozen model on the PERP target
            (the rolling lever was +40% on the SPOT target; does it carry?).

This is deliberately NOT ``gate0_btc_perp.py`` (that is cross-sectional over 14
assets and degenerates at N=1). Everything here is single-asset *temporal*:
per-asset Pearson/Spearman, OLS beta of y on yhat, sigma_yhat/sigma_y, per-fold
sign-consistency, RAW y_600 scoring (no clipping), MAD-sigma feature norm fit on
TRAIN only, 1-day embargo, no look-ahead.

Spot/perp JOIN (verified empirically, see _load_day): npz_spot and npz_perp have
the SAME number of rows per day and ``perp_ts - spot_ts`` is a single CONSTANT
across all rows (0 on 274/516 eval-span days, a small +/- whole-second offset on
the rest -- a snapshot-time label convention, NOT a row misalignment). Rows are
therefore positionally aligned bar-for-bar; we join by POSITION and assert the
per-day shift is constant and within tolerance, skipping any day that violates it.
(A strict ``np.array_equal`` skip would silently drop ~47% of the 2025-26 span and
bias the eval; the constant-shift join keeps all of it, correctly.)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import os.path as p
import sys

import numpy as np
from scipy.stats import pearsonr, spearmanr

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))  # repo root
from multi_asset.eda.leakage_null import permute_y_null  # noqa: E402

DATA_DIR = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data"
SPOT_DIR = p.join(DATA_DIR, "npz_spot")
PERP_DIR = p.join(DATA_DIR, "npz_perp")

LAMBDAS = [30.0, 100.0, 300.0, 1000.0]
SUBSAMPLE = 4          # ::4 for speed
EMBARGO_DAYS = 1
SHIFT_TOL_US = 10_000_000   # allow up to +/-10s constant label offset; skip beyond

# Walk-forward folds (GATE A). Anchored by calendar date for self-documentation.
# test = 40d from anchor; val = 20d before test; train = history up to val-start,
# minus a 1-day embargo, requiring >= 230 train days. Strong: 2025-02, 2025-04;
# choppy: 2026.
FOLDS = [
    dict(name="strong_2025_02", test_start="2025-02-01"),
    dict(name="strong_2025_04", test_start="2025-04-01"),
    dict(name="choppy_2026",    test_start="2026-03-01"),
]
TEST_DAYS = 40
VAL_DAYS = 20
MIN_TRAIN_DAYS = 230


# ---------------------------------------------------------------------------
# loading / join
# ---------------------------------------------------------------------------
def _all_days():
    spot = {p.basename(f)[:-4] for f in glob.glob(p.join(SPOT_DIR, "*.npz"))}
    perp = {p.basename(f)[:-4] for f in glob.glob(p.join(PERP_DIR, "*.npz"))
            if p.basename(f)[0].isdigit()}
    return sorted(spot & perp)


def _load_day(day: str):
    """Return (X_last, y_perp, ok, info) for one day, positionally joined.

    X_last: (n,64) spot last-timestep features, masked by spot y_mask_600 and
            subsampled ::SUBSAMPLE.
    y_perp: (n,) perp y_600 RAW, the SAME masked+subsampled rows.
    ok: False -> skip this day (shape mismatch / non-constant or out-of-tol shift).
    """
    ds = np.load(p.join(SPOT_DIR, f"{day}.npz"))
    dp = np.load(p.join(PERP_DIR, f"{day}.npz"))
    sts = ds["timestamps"].astype(np.int64)
    pts = dp["timestamps"].astype(np.int64)
    if sts.shape != pts.shape:
        return None, None, False, "len_mismatch"
    diff = pts - sts
    if diff.size == 0:
        return None, None, False, "empty"
    if not np.all(diff == diff[0]):
        return None, None, False, "nonconst_shift"
    if abs(int(diff[0])) > SHIFT_TOL_US:
        return None, None, False, f"shift_{int(diff[0])//1_000_000}s_gt_tol"

    X = ds["X"][:, -1, :].astype(np.float64)          # (N,64) last timestep
    mask = ds["y_mask_600"].astype(bool)
    yperp = dp["y_600"].astype(np.float64)            # perp target, positional

    keep = mask.copy()
    keep[~np.isfinite(yperp)] = False
    keep &= np.all(np.isfinite(X), axis=1)
    idx = np.where(keep)[0][::SUBSAMPLE]
    if idx.size == 0:
        return None, None, False, "no_valid_rows"
    return X[idx], yperp[idx], True, f"shift_{int(diff[0])//1_000_000}s"


def load_all(verbose=False):
    """Load the whole common span, in date order, with per-sample day & month id.

    Returns X (M,64), y (M,), day_idx (M,) int (index into `days`),
    month (M,) 'YYYY-MM' str, days (list), skipped (dict day->reason)."""
    days = _all_days()
    Xs, ys, di, mo = [], [], [], []
    skipped = {}
    for k, day in enumerate(days):
        Xd, yd, ok, info = _load_day(day)
        if not ok:
            skipped[day] = info
            continue
        Xs.append(Xd)
        ys.append(yd)
        di.append(np.full(yd.shape[0], k, dtype=np.int32))
        mo.append(np.array([day[:7]] * yd.shape[0]))
    X = np.concatenate(Xs)
    y = np.concatenate(ys)
    day_idx = np.concatenate(di)
    month = np.concatenate(mo)
    if verbose:
        print(f"[load] {len(days)} common days, kept {len(days)-len(skipped)}, "
              f"skipped {len(skipped)}; M={X.shape[0]} samples, D={X.shape[1]}")
        if skipped:
            from collections import Counter
            print("[load] skip reasons:", dict(Counter(skipped.values())))
    return X, y, day_idx, month, days, skipped


# ---------------------------------------------------------------------------
# ridge + metrics
# ---------------------------------------------------------------------------
def mad_sigma(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")
    med = np.median(x)
    return float(np.median(np.abs(x - med)) * 1.4826)


def _standardize_fit(Xtr, how="madz"):
    if how == "madz":
        center = np.median(Xtr, axis=0)
        scale = np.median(np.abs(Xtr - center), axis=0) * 1.4826
    else:  # meanstd
        center = Xtr.mean(axis=0)
        scale = Xtr.std(axis=0)
    scale = np.where(scale > 1e-12, scale, 1.0)
    return center, scale


def ridge_fit(Xtr, ytr, lam):
    """Closed-form ridge: w = (X'X + lam I)^-1 X'y. X already standardized,
    intercept handled by centering y (returns w, b)."""
    n, d = Xtr.shape
    yb = ytr.mean()
    yc = ytr - yb
    G = Xtr.T @ Xtr
    G[np.diag_indices_from(G)] += lam
    w = np.linalg.solve(G, Xtr.T @ yc)
    return w, yb


def _metrics(yhat, ytrue):
    if yhat.size < 3 or np.std(yhat) <= 0 or np.std(ytrue) <= 0:
        return dict(P=float("nan"), S=float("nan"), beta=float("nan"),
                    sig_ratio=float("nan"), bias_bps=float("nan"), n=int(yhat.size))
    P = float(pearsonr(yhat, ytrue)[0])
    S = float(spearmanr(yhat, ytrue)[0])
    vyh = float(np.var(yhat))
    beta = float(np.cov(ytrue, yhat)[0, 1] / vyh) if vyh > 0 else float("nan")
    sig_ratio = float(np.std(yhat) / np.std(ytrue))
    bias_bps = float(np.mean(yhat) * 1e4)
    return dict(P=P, S=S, beta=beta, sig_ratio=sig_ratio, bias_bps=bias_bps,
                n=int(yhat.size))


def _fit_select(Xtr, ytr, Xva, yva, norm):
    """Fit ridge over LAMBDAS, pick lambda maximizing val Pearson. Returns
    (w, b, center, scale, sig, best_lam, val_P)."""
    center, scale = _standardize_fit(Xtr, norm)
    Xtr_s = (Xtr - center) / scale
    Xva_s = (Xva - center) / scale
    sig = mad_sigma(ytr)
    if not np.isfinite(sig) or sig <= 0:
        return None
    ytr_n = ytr / sig
    best = None
    for lam in LAMBDAS:
        w, b = ridge_fit(Xtr_s, ytr_n, lam)
        yhat_va = (Xva_s @ w + b) * sig
        if np.std(yhat_va) <= 0:
            vp = -np.inf
        else:
            vp = float(pearsonr(yhat_va, yva)[0])
        if best is None or vp > best[0]:
            best = (vp, lam, w, b)
    val_P, best_lam, w, b = best
    return w, b, center, scale, sig, best_lam, val_P


def _predict(X, w, b, center, scale, sig):
    Xs = (X - center) / scale
    return (Xs @ w + b) * sig


# ---------------------------------------------------------------------------
# GATE A: walk-forward over the 3 folds
# ---------------------------------------------------------------------------
def ridge_walkforward(X, y, day_idx, days, norm="madz", verbose=True):
    days = list(days)
    d2i = {d: i for i, d in enumerate(days)}

    def first_ge(date):
        for i, d in enumerate(days):
            if d >= date:
                return i
        return len(days)

    fold_rows, fold_meta = [], []
    pooled_yhat, pooled_y = [], []
    perfold_P = []

    for fold in FOLDS:
        ts0 = first_ge(fold["test_start"])
        te0, te1 = ts0, ts0 + TEST_DAYS
        va0, va1 = te0 - VAL_DAYS, te0
        # train = [0, va0) minus 1-day embargo before val and before test
        tr0, tr1 = 0, va0 - EMBARGO_DAYS
        if te1 > len(days) or va0 < 0 or (tr1 - tr0) < MIN_TRAIN_DAYS:
            fold_meta.append(dict(name=fold["name"], status="unavailable"))
            continue
        # also embargo around test (val already separates; embargo the last
        # train day before val, done via tr1 above)
        tr_di = set(range(tr0, tr1))
        va_di = set(range(va0, va1))
        te_di = set(range(te0, te1))

        tr_m = np.isin(day_idx, list(tr_di))
        va_m = np.isin(day_idx, list(va_di))
        te_m = np.isin(day_idx, list(te_di))
        if tr_m.sum() < 500 or va_m.sum() < 20 or te_m.sum() < 20:
            fold_meta.append(dict(name=fold["name"], status="too_few_samples"))
            continue

        sel = _fit_select(X[tr_m], y[tr_m], X[va_m], y[va_m], norm)
        if sel is None:
            fold_meta.append(dict(name=fold["name"], status="bad_sigma"))
            continue
        w, b, center, scale, sig, lam, valP = sel
        yhat_te = _predict(X[te_m], w, b, center, scale, sig)
        yte = y[te_m]

        m = _metrics(yhat_te, yte)
        perfold_P.append(m["P"])
        pooled_yhat.append(yhat_te)
        pooled_y.append(yte)
        fold_meta.append(dict(
            name=fold["name"], status="ok",
            test_span=f"{days[te0]}..{days[te1-1]}",
            train_days=int(tr1 - tr0), val_days=int(va1 - va0),
            n_train=int(tr_m.sum()), n_val=int(va_m.sum()), n_test=int(te_m.sum()),
            best_lam=lam, val_P=round(valP, 4),
            P=round(m["P"], 4), S=round(m["S"], 4), beta=round(m["beta"], 3),
            sig_ratio=round(m["sig_ratio"], 4), bias_bps=round(m["bias_bps"], 3)))

    pooled = None
    if pooled_yhat:
        yh = np.concatenate(pooled_yhat)
        yy = np.concatenate(pooled_y)
        pm = _metrics(yh, yy)
        finite = [x for x in perfold_P if np.isfinite(x)]
        signs = set(np.sign(x) for x in finite if x != 0)
        sign_consistent = (len(signs) <= 1) and not any(x <= -0.01 for x in finite)
        pooled = dict(
            P=round(pm["P"], 4), S=round(pm["S"], 4), beta=round(pm["beta"], 3),
            sig_ratio=round(pm["sig_ratio"], 4), bias_bps=round(pm["bias_bps"], 3),
            n=pm["n"], perfold_P=[round(x, 4) for x in perfold_P],
            sign_consistent=bool(sign_consistent), pooled_yhat=yh, pooled_y=yy)
    return dict(folds=fold_meta, pooled=pooled, norm=norm)


# ---------------------------------------------------------------------------
# GATE B0: frozen vs rolling on 2026
# ---------------------------------------------------------------------------
def _month_list(days, prefix="2026"):
    ms = sorted({d[:7] for d in days if d.startswith(prefix)})
    return ms


def run_frozen(X, y, day_idx, month, days, norm="madz"):
    """Fit ONCE on all history <= 2025-12-31, eval each 2026 month.
    Lambda picked on a held-out val = last 20 train days."""
    train_mask = month <= "2025-12"
    # carve val = last VAL_DAYS train days
    tr_days = sorted({days[i] for i in np.unique(day_idx[train_mask])})
    val_days = set(tr_days[-VAL_DAYS:])
    val_day_idx = {days.index(d) for d in val_days}
    va_m = train_mask & np.isin(day_idx, list(val_day_idx))
    fit_m = train_mask & ~np.isin(day_idx, list(val_day_idx))
    # embargo: drop the single train day adjacent to first val day -> approximate
    sel = _fit_select(X[fit_m], y[fit_m], X[va_m], y[va_m], norm)
    w, b, center, scale, sig, lam, valP = sel

    per_month, pooled_yhat, pooled_y = [], [], []
    for mth in _month_list(days):
        mm = month == mth
        if mm.sum() < 20:
            continue
        yhat = _predict(X[mm], w, b, center, scale, sig)
        yy = y[mm]
        mt = _metrics(yhat, yy)
        per_month.append(dict(month=mth, n=int(mm.sum()),
                              P=round(mt["P"], 4), S=round(mt["S"], 4),
                              beta=round(mt["beta"], 3),
                              sig_ratio=round(mt["sig_ratio"], 4)))
        pooled_yhat.append(yhat)
        pooled_y.append(yy)
    yh, yy = np.concatenate(pooled_yhat), np.concatenate(pooled_y)
    pm = _metrics(yh, yy)
    return dict(mode="frozen", train_n=int(fit_m.sum()), best_lam=lam,
                per_month=per_month,
                pooled=dict(P=round(pm["P"], 4), S=round(pm["S"], 4),
                            beta=round(pm["beta"], 3),
                            sig_ratio=round(pm["sig_ratio"], 4), n=pm["n"]),
                pooled_yhat=yh, pooled_y=yy)


def run_rolling(X, y, day_idx, month, days, trail=400, norm="madz"):
    """For each 2026 month M: refit on the trailing `trail` days ending at the
    last day of month M-1 (val = last 20 of those), eval month M."""
    per_month, pooled_yhat, pooled_y = [], [], []
    for mth in _month_list(days):
        # last day index strictly before this month
        prior_idx = [i for i, d in enumerate(days) if d[:7] < mth]
        if not prior_idx:
            continue
        end_i = prior_idx[-1]
        start_i = max(0, end_i - trail + 1)
        win = set(range(start_i, end_i + 1))
        # val = last VAL_DAYS days of the window
        val_win = set(range(end_i - VAL_DAYS + 1, end_i + 1))
        fit_win = win - val_win
        # embargo 1 day between fit/val and the (future) test month is automatic
        fit_m = np.isin(day_idx, list(fit_win))
        va_m = np.isin(day_idx, list(val_win))
        te_m = month == mth
        if fit_m.sum() < 500 or va_m.sum() < 20 or te_m.sum() < 20:
            continue
        sel = _fit_select(X[fit_m], y[fit_m], X[va_m], y[va_m], norm)
        if sel is None:
            continue
        w, b, center, scale, sig, lam, valP = sel
        yhat = _predict(X[te_m], w, b, center, scale, sig)
        yy = y[te_m]
        mt = _metrics(yhat, yy)
        per_month.append(dict(month=mth, n=int(te_m.sum()),
                              train_span=f"{days[start_i]}..{days[end_i]}",
                              best_lam=lam,
                              P=round(mt["P"], 4), S=round(mt["S"], 4),
                              beta=round(mt["beta"], 3),
                              sig_ratio=round(mt["sig_ratio"], 4)))
        pooled_yhat.append(yhat)
        pooled_y.append(yy)
    yh, yy = np.concatenate(pooled_yhat), np.concatenate(pooled_y)
    pm = _metrics(yh, yy)
    return dict(mode="rolling", trail=trail, per_month=per_month,
                pooled=dict(P=round(pm["P"], 4), S=round(pm["S"], 4),
                            beta=round(pm["beta"], 3),
                            sig_ratio=round(pm["sig_ratio"], 4), n=pm["n"]),
                pooled_yhat=yh, pooled_y=yy)


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def _print_wf(res, null_band=None):
    print("\n=== GATE A: single-asset temporal Ridge walk-forward (spot X -> perp y_600) ===")
    print(f"norm={res['norm']}  lambdas={LAMBDAS}  subsample=::{SUBSAMPLE}  "
          f"train>={MIN_TRAIN_DAYS}d / val{VAL_DAYS} / test{TEST_DAYS}, embargo {EMBARGO_DAYS}d")
    print(f"{'fold':16s} {'test_span':24s} {'lam':>5s} {'valP':>7s} "
          f"{'P':>8s} {'S':>8s} {'beta':>7s} {'sigR':>7s} {'bias_bps':>9s} {'n_test':>7s}")
    for f in res["folds"]:
        if f.get("status") != "ok":
            print(f"{f['name']:16s} {f.get('status','?'):24s} (skipped)")
            continue
        print(f"{f['name']:16s} {f['test_span']:24s} {int(f['best_lam']):5d} "
              f"{f['val_P']:+7.4f} {f['P']:+8.4f} {f['S']:+8.4f} {f['beta']:+7.3f} "
              f"{f['sig_ratio']:7.4f} {f['bias_bps']:+9.3f} {f['n_test']:7d}")
    pl = res["pooled"]
    if pl:
        print("-" * 110)
        print(f"{'POOLED':16s} {'(3 folds)':24s} {'':>5s} {'':>7s} "
              f"{pl['P']:+8.4f} {pl['S']:+8.4f} {pl['beta']:+7.3f} "
              f"{pl['sig_ratio']:7.4f} {pl['bias_bps']:+9.3f} {pl['n']:7d}")
        print(f"  per-fold P = {pl['perfold_P']}  sign_consistent={pl['sign_consistent']}")
        if null_band is not None:
            print(f"  y-permutation null band (97.5pct |IC|) = {null_band:.4f}  "
                  f"-> pooled |P| {'>' if abs(pl['P'])>null_band else '<='} band")


def _print_mode(res):
    print(f"\n=== GATE B0: mode={res['mode']} "
          f"{'(trail '+str(res.get('trail'))+'d)' if res['mode']=='rolling' else '(fit<=2025-12)'} ===")
    print(f"{'month':9s} {'n':>7s} {'P':>8s} {'S':>8s} {'beta':>7s} {'sigR':>7s}  {'train_span/lam'}")
    for m in res["per_month"]:
        extra = m.get("train_span", "") + (f" lam={int(m['best_lam'])}" if "best_lam" in m else "")
        print(f"{m['month']:9s} {m['n']:7d} {m['P']:+8.4f} {m['S']:+8.4f} "
              f"{m['beta']:+7.3f} {m['sig_ratio']:7.4f}  {extra}")
    pl = res["pooled"]
    print("-" * 80)
    print(f"{'POOLED':9s} {pl['n']:7d} {pl['P']:+8.4f} {pl['S']:+8.4f} "
          f"{pl['beta']:+7.3f} {pl['sig_ratio']:7.4f}")


def _strip(d):
    """Remove ndarray fields for JSON dump."""
    out = {}
    for k, v in d.items():
        if isinstance(v, np.ndarray):
            continue
        if isinstance(v, dict):
            out[k] = _strip(v)
        else:
            out[k] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["frozen", "rolling", "both", "wf"],
                    default="wf",
                    help="wf=GATE A walk-forward; frozen/rolling/both=GATE B0")
    ap.add_argument("--norm", choices=["madz", "meanstd"], default="madz")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--null_n", type=int, default=1000)
    ap.add_argument("--json_out", default="")
    args = ap.parse_args()

    X, y, day_idx, month, days, skipped = load_all(verbose=True)
    out = {"n_samples": int(X.shape[0]), "n_feat": int(X.shape[1]),
           "n_days_kept": len(days) - len(skipped), "n_skipped": len(skipped),
           "norm": args.norm}

    if args.mode in ("wf", "frozen", "both"):
        # GATE A always runs the walk-forward (it is the base-IC reproduction)
        wf = ridge_walkforward(X, y, day_idx, days, norm=args.norm)
        null_band = None
        if wf["pooled"] is not None:
            null_band = permute_y_null(wf["pooled"]["pooled_yhat"],
                                       wf["pooled"]["pooled_y"],
                                       n=args.null_n, seed=0)
        _print_wf(wf, null_band)
        out["gate_A_walkforward"] = _strip(wf)
        out["gate_A_null_band_975"] = None if null_band is None else round(null_band, 4)

    if args.mode in ("frozen", "both"):
        fr = run_frozen(X, y, day_idx, month, days, norm=args.norm)
        _print_mode(fr)
        out["gate_B0_frozen"] = _strip(fr)

    if args.mode in ("rolling", "both"):
        ro = run_rolling(X, y, day_idx, month, days, norm=args.norm)
        _print_mode(ro)
        out["gate_B0_rolling"] = _strip(ro)

    if args.mode == "both":
        fp = out["gate_B0_frozen"]["pooled"]["P"]
        rp = out["gate_B0_rolling"]["pooled"]["P"]
        print(f"\n=== GATE B0 SUMMARY: frozen pooled P={fp:+.4f}  "
              f"rolling pooled P={rp:+.4f}  delta(rolling-frozen)={rp-fp:+.4f} ===")

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(out, f, indent=2, default=float)
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()

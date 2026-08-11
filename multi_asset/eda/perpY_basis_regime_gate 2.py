"""Stage C REGIME-CONDITIONED basis salvage: can a CAUSAL regime indicator flip
the basis sign so the basis becomes a usable perp y_600 predictor?

THE DECISIVE QUESTION
---------------------
The basis (= perp_mid - spot_mid) is a real orthogonal factor, but its
correlation with perp returns FLIPS SIGN by regime: in STRONG/trending months
(2025-02, 2025-04) ``basis_ema_dev`` IC vs perp y_600 is POSITIVE (~+0.018,
momentum: a widening dislocation keeps going); in CHOPPY 2026 it is NEGATIVE
(~-0.025, mean-reversion: the dislocation snaps back). A single linear Ridge
weight therefore has the WRONG sign half the time and HURTS (plain-basis block
ΔP: strong ~-0.001, choppy ~-0.009).

We test whether a STRICTLY-CAUSAL (<= t) regime indicator -- realized vol,
Kaufman efficiency ratio, trailing |return| -- can route the basis sign, so the
basis becomes net-positive at least on choppy WITHOUT hurting strong. Two
complementary reads:

  (A) DIAGNOSTIC: split windows by each causal indicator's median and report
      ``basis_ema_dev`` IC vs perp y_600 in each half. If the sign of the basis
      IC tracks the indicator CONSISTENTLY across both the strong AND choppy
      span (e.g. high-vol -> negative basis IC, low-vol -> positive, in BOTH),
      the flip is causally exploitable. If the split only separates the
      strong-YEAR from the choppy-YEAR (i.e. the indicator is just a proxy for
      "which months"), it is NOT exploitable out of sample.

  (B) REGIME-CONDITIONED RIDGE: add interaction columns ``basis_factor *
      causal_indicator`` (plus the standardized indicator itself) to the spot-64
      baseline and walk-forward (reusing perpY_ridge_gate.ridge_walkforward).
      Report block ΔP over the spot-64 baseline for STRONG and CHOPPY, per
      indicator, vs the plain (non-interacted) basis ΔP. The interaction lets a
      single linear model apply a basis weight whose effective sign depends on
      the (causal) regime -- exactly the lever the diagnostic probes.

CAUSAL REGIME INDICATORS (all <= t, computed on the per-second SPOT mid)
------------------------------------------------------------------------
  causal_vol    : sqrt(mean of (1s spot log-return)^2) over the last VOL_WIN_SEC
                  (~1h). Realized vol PERSISTS strongly day-to-day, so it is
                  causally usable as a regime tag.
  causal_ER     : Kaufman efficiency ratio over the last ER_WIN_SEC (~1h) =
                  |mid(t) - mid(t-W)| / sum_{k}|mid(k)-mid(k-1)|. Trend strength
                  in [0,1]. NOTE: trend (unlike vol) may NOT persist, so a flip
                  that tracks ER could fail to transfer -- the diagnostic checks.
  causal_absret : trailing mean |1s spot log-return| over the last ABS_WIN_SEC
                  (~30min). A faster, fatter-tailed vol proxy.

Everything is computed on the per-second mid then SHIFTED by 1 (the statistic at
second t uses only seconds < t) and sampled at each prediction second via a <= t
lookup -- the same strict-causal contract build_basis_factors passes (and which
test_basis_regime.py future-corruption-checks).

REPORTING DISCIPLINE
--------------------
Numbers only; the controller decides. We do NOT print a GO/NO-GO. We report: the
diagnostic median-split basis IC per half per indicator (does the sign track the
indicator?), the regime-conditioned block ΔP (strong + choppy) per indicator vs
plain-basis ΔP, and a future-corruption leakage check on the indicators.

CLI
---
  python multi_asset/eda/perpY_basis_regime_gate.py
  python multi_asset/eda/perpY_basis_regime_gate.py --json_out /tmp/regimebasis.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os.path as p
import sys

import numpy as np
from scipy.stats import pearsonr, spearmanr

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))  # repo root
from multi_asset.eda import perpY_ridge_gate as prg              # noqa: E402
from multi_asset.eda.leakage_null import permute_y_null         # noqa: E402
from multi_asset.data import build_basis_factors as bbf          # noqa: E402

DATA_DIR = prg.DATA_DIR
LASTTS_DIR = p.join(DATA_DIR, "lastts_cache")
MID_DIR = p.join(DATA_DIR, "mid_cache")
BASIS_DIR = p.join(DATA_DIR, "basis_cache")

SUBSAMPLE = prg.SUBSAMPLE
US_PER_SEC = bbf.US_PER_SEC
FACTOR_NAMES = bbf.FACTOR_NAMES

# the basis factor the diagnostic centres on (the one whose IC flips sign)
DIAG_FACTOR = "basis_ema_dev"

# causal regime indicator windows (seconds)
VOL_WIN_SEC = 3600       # 1h realized vol
ER_WIN_SEC = 3600        # 1h Kaufman efficiency ratio
ABS_WIN_SEC = 1800       # 30min trailing mean |return|
REGIME_NAMES = ["causal_vol", "causal_ER", "causal_absret"]

# regime spans (reuse perpY_ridge_gate fold geometry)
STRONG_FOLDS = [
    dict(name="strong_2025_02", test_start="2025-02-01"),
    dict(name="strong_2025_04", test_start="2025-04-01"),
]
CHOPPY_FOLDS = [
    dict(name="choppy_2026", test_start="2026-03-01"),
]


# ===========================================================================
# CAUSAL REGIME INDICATORS (strictly <= t, on the per-second spot mid)
# ===========================================================================
def _causal_trailing_mean(x, win):
    """Trailing mean of x over `win` samples, SHIFTED by 1 (value at i uses only
    x[i-win .. i-1], strictly < i). Min 2 obs else NaN. O(T) prefix-sum.

    Mirrors build_basis_factors._causal_rollmean_std's shift-by-1 contract so the
    statistic at second t never touches second t (let alone > t)."""
    x = np.asarray(x, dtype=np.float64)
    T = x.size
    xs = np.concatenate([[0.0], np.cumsum(x)])
    out = np.full(T, np.nan)
    i = np.arange(T)
    hi = i                       # exclusive upper = i -> covers up to i-1
    lo = np.maximum(0, i - win)
    cnt = (hi - lo).astype(np.float64)
    valid = cnt >= 2
    s1 = xs[hi] - xs[lo]
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s1 / cnt
    out[valid] = mean[valid]
    return out


def causal_regime_per_second(sec, spot_mid):
    """The 3 causal regime indicators on the full per-second grid.

    Returns dict name -> array(T,). Each value at second t uses only seconds < t
    (shift-by-1 baked in), so corrupting any second >= t cannot change it. `sec`
    is the contiguous unix-second grid (per build_mid_cache); spot_mid absolute.

    Mechanism note: the efficiency ratio uses the SECOND index for its lookback
    (sec - W), so a non-contiguous grid still measures the move over W real
    seconds rather than W positions."""
    sec = np.asarray(sec, dtype=np.int64)
    spot_mid = np.asarray(spot_mid, dtype=np.float64)
    T = sec.size

    # 1s log-returns r[t] = log(mid[t]) - log(mid[t-1]); r[0] := nan (no past)
    logm = np.log(spot_mid)
    r = np.full(T, np.nan)
    r[1:] = logm[1:] - logm[:-1]
    r0 = np.where(np.isfinite(r), r, 0.0)          # zero-fill only for the sums
    absr0 = np.abs(r0)

    # --- causal_vol: sqrt(trailing mean r^2) over VOL_WIN_SEC, shift(1) ---
    msq = _causal_trailing_mean(r0 * r0, VOL_WIN_SEC)
    causal_vol = np.sqrt(np.where(msq >= 0, msq, np.nan))

    # --- causal_absret: trailing mean |r| over ABS_WIN_SEC, shift(1) ---
    causal_absret = _causal_trailing_mean(absr0, ABS_WIN_SEC)

    # --- causal_ER: |mid(t-1) - mid(t-1-W)| / sum_{k in (t-1-W, t-1]} |r[k]| ---
    # Use the value THROUGH t-1 only (shift baked in): numerator is the net move
    # over the window ending at t-1, denominator the path length over the same
    # window. Both computed from quantities <= t-1.
    # net move over [t-1-W, t-1] = logm[t-1] - logm[t-1-W]  (price-space net move)
    # path length = trailing sum of |r| over the same window (shift(1)).
    sum_abs = _causal_trailing_mean(absr0, ER_WIN_SEC)
    # trailing_mean returns mean; recover sum via count (window may be short at start)
    i = np.arange(T)
    cnt = (i - np.maximum(0, i - ER_WIN_SEC)).astype(np.float64)
    path_len = sum_abs * cnt                        # sum |r| over window ending t-1
    # net move ending at t-1 over W seconds: logm[t-1] - logm[t-1-W]
    end = i - 1                                      # last index used = t-1
    start = end - ER_WIN_SEC
    net = np.full(T, np.nan)
    ok = (end >= 0) & (start >= 0)
    net[ok] = np.abs(logm[end[ok]] - logm[start[ok]])
    with np.errstate(invalid="ignore", divide="ignore"):
        causal_ER = net / (path_len + 1e-12)
    causal_ER = np.where(np.isfinite(causal_ER) & (path_len > 0), causal_ER, np.nan)

    return {
        "causal_vol": causal_vol,
        "causal_ER": causal_ER,
        "causal_absret": causal_absret,
    }


def causal_regime_at_pred_secs(sec, spot_mid, pred_secs):
    """Sample the 3 indicators at prediction seconds via <= t lookup (reuses the
    tested build_basis_factors.sample_at_pred_secs)."""
    per_sec = causal_regime_per_second(sec, spot_mid)
    return bbf.sample_at_pred_secs(sec, per_sec, pred_secs)


# ===========================================================================
# LOADING: lastts (spot64 + perp y) JOIN basis_cache (4) JOIN regime (3), by ts
# ===========================================================================
def _common_days():
    last = {p.basename(f)[:-4] for f in glob.glob(p.join(LASTTS_DIR, "*.npz"))}
    bas = {p.basename(f)[:-4] for f in glob.glob(p.join(BASIS_DIR, "*.npz"))}
    mid = {p.basename(f)[:-4] for f in glob.glob(p.join(MID_DIR, "*.npz"))}
    return sorted(last & bas & mid)


def _load_day(day, corrupt_after_frac=None):
    """Return (X64, F4, R3, y_perp, ok, info) for one day, joined by timestamp.

    X64: spot_last; F4: basis factors; R3: causal regime indicators; y_perp: PERP
    y_600 RAW. Masked by lastts y_mask_600 + finite (incl. R3), subsampled.

    corrupt_after_frac: if set (0..1), corrupt the per-second spot mid strictly
    AFTER the (frac * day) second BEFORE computing R3 -- the leakage sentinel.
    Prediction seconds <= the cut must be unchanged."""
    lf = p.join(LASTTS_DIR, "%s.npz" % day)
    with np.load(lf) as zl:
        X = zl["spot_last"].astype(np.float64)        # (N,64)
        ts = zl["timestamps"].astype(np.int64)
        y = zl["y_600"].astype(np.float64)
        mask = zl["y_mask_600"].astype(bool)

    bf = p.join(BASIS_DIR, "%s.npz" % day)
    with np.load(bf) as zb:
        bts = zb["timestamps"].astype(np.int64)
        F = zb["F"].astype(np.float64)
    if bts.shape != ts.shape or not np.array_equal(bts, ts):
        return None, None, None, None, False, "ts_mismatch"

    mf = p.join(MID_DIR, "%s.npz" % day)
    with np.load(mf) as zm:
        sec = zm["sec"].astype(np.int64)
        spot_mid = zm["spot_mid"].astype(np.float64)

    if corrupt_after_frac is not None:
        cut_i = int(corrupt_after_frac * sec.size)
        rng = np.random.default_rng(0)
        fut = np.arange(sec.size) > cut_i
        scale = float(np.nanstd(spot_mid)) or 1.0
        spot_mid = spot_mid.copy()
        spot_mid[fut] = (rng.standard_normal(int(fut.sum())) * scale * 50.0
                         + scale * 1000.0)

    pred_secs = ts // US_PER_SEC
    Rd = causal_regime_at_pred_secs(sec, spot_mid, pred_secs)
    R = np.column_stack([Rd[nm] for nm in REGIME_NAMES])

    keep = mask.copy()
    keep[~np.isfinite(y)] = False
    keep &= np.all(np.isfinite(X), axis=1)
    keep &= np.all(np.isfinite(F), axis=1)
    keep &= np.all(np.isfinite(R), axis=1)
    idx = np.where(keep)[0][::SUBSAMPLE]
    if idx.size == 0:
        return None, None, None, None, False, "no_valid_rows"
    return X[idx], F[idx], R[idx], y[idx], True, "ok"


def load_all(corrupt_after_frac=None, verbose=False):
    """Load whole span; returns X64, F4, R3, y, day_idx, days, skipped."""
    days = _common_days()
    Xs, Fs, Rs, ys, di = [], [], [], [], []
    skipped = {}
    kept_days = []
    for day in days:
        X, F, R, y, ok, info = _load_day(day, corrupt_after_frac=corrupt_after_frac)
        if not ok:
            skipped[day] = info
            continue
        Xs.append(X); Fs.append(F); Rs.append(R); ys.append(y)
        di.append(np.full(y.shape[0], len(kept_days), dtype=np.int32))
        kept_days.append(day)
    X = np.concatenate(Xs); F = np.concatenate(Fs); R = np.concatenate(Rs)
    y = np.concatenate(ys); day_idx = np.concatenate(di)
    if verbose:
        from collections import Counter
        print("[load] %d common days, kept %d, skipped %d; M=%d spotD=%d basisD=%d "
              "regimeD=%d  corrupt=%s"
              % (len(days), len(kept_days), len(skipped), X.shape[0], X.shape[1],
                 F.shape[1], R.shape[1], str(corrupt_after_frac)))
        if skipped:
            print("[load] skip reasons:", dict(Counter(skipped.values())))
    return X, F, R, y, day_idx, kept_days, skipped


# ===========================================================================
# fold geometry helpers (mirror prg.ridge_walkforward test spans)
# ===========================================================================
def _regime_test_mask(folds, day_idx, days):
    def first_ge(date):
        for i, d in enumerate(days):
            if d >= date:
                return i
        return len(days)
    te_di = set()
    for fold in folds:
        ts0 = first_ge(fold["test_start"])
        te_di.update(range(ts0, min(ts0 + prg.TEST_DAYS, len(days))))
    return np.isin(day_idx, list(te_di))


def _wf_on_folds(Xmat, y, day_idx, days, folds):
    saved = prg.FOLDS
    prg.FOLDS = folds
    try:
        res = prg.ridge_walkforward(Xmat, y, day_idx, days, norm="madz",
                                    verbose=False)
    finally:
        prg.FOLDS = saved
    return res


def _pooledP(res):
    if res is None or res["pooled"] is None:
        return None
    return res["pooled"]


def _ic(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 50 or np.std(a[m]) <= 0 or np.std(b[m]) <= 0:
        return float("nan"), float("nan"), int(m.sum())
    return (float(pearsonr(a[m], b[m])[0]), float(spearmanr(a[m], b[m])[0]),
            int(m.sum()))


# ===========================================================================
# (A) DIAGNOSTIC: does the basis IC sign track a CAUSAL indicator?
# ===========================================================================
def diagnostic(name, folds, F, R, y, day_idx, days):
    """For each causal indicator, split THIS regime's test rows at the indicator's
    (causal) median and report DIAG_FACTOR IC vs perp y_600 in each half.

    The median is computed WITHIN the regime's test rows (a within-regime split):
    this asks whether, given we are in (say) the strong year, high-vol windows and
    low-vol windows show OPPOSITE basis IC sign. If yes in BOTH the strong AND the
    choppy span, the flip is driven by the causal indicator, not the calendar."""
    te = _regime_test_mask(folds, day_idx, days)
    fcol = F[:, FACTOR_NAMES.index(DIAG_FACTOR)]
    yy = y[te]
    fb = fcol[te]
    full_P, full_S, full_n = _ic(fb, yy)

    print("\n-- DIAGNOSTIC (%s): %s IC vs perp y_600, median-split by causal "
          "indicator --" % (name, DIAG_FACTOR))
    print("   whole-regime %s IC: P=%+.4f S=%+.4f (n=%d)"
          % (DIAG_FACTOR, full_P, full_S, full_n))
    print("   %-14s %8s | %10s %10s %8s | %10s %10s %8s | %8s"
          % ("indicator", "median", "lo_P", "lo_S", "lo_n",
             "hi_P", "hi_S", "hi_n", "signflip"))

    out = {"whole_regime_ic": dict(P=round(full_P, 4), S=round(full_S, 4),
                                   n=full_n), "by_indicator": {}}
    for j, nm in enumerate(REGIME_NAMES):
        ind = R[te, j]
        m = np.isfinite(ind) & np.isfinite(fb) & np.isfinite(yy)
        if m.sum() < 200:
            print("   %-14s INSUFFICIENT (n=%d)" % (nm, int(m.sum())))
            out["by_indicator"][nm] = dict(status="insufficient", n=int(m.sum()))
            continue
        med = float(np.median(ind[m]))
        lo = m & (ind <= med)
        hi = m & (ind > med)
        loP, loS, lon = _ic(fb[lo], yy[lo])
        hiP, hiS, hin = _ic(fb[hi], yy[hi])
        flip = bool(np.isfinite(loP) and np.isfinite(hiP)
                    and np.sign(loP) != np.sign(hiP) and loP != 0 and hiP != 0)
        print("   %-14s %+8.5f | %+10.4f %+10.4f %8d | %+10.4f %+10.4f %8d | %8s"
              % (nm, med, loP, loS, lon, hiP, hiS, hin, "YES" if flip else "no"))
        out["by_indicator"][nm] = dict(
            median=round(med, 6),
            lo=dict(P=round(loP, 4), S=round(loS, 4), n=lon),
            hi=dict(P=round(hiP, 4), S=round(hiS, 4), n=hin),
            sign_flip=flip)
    return out


# ===========================================================================
# (B) REGIME-CONDITIONED RIDGE: basis x indicator interactions
# ===========================================================================
def _zscore_cols(M):
    """Column z-score (mean/std), std clamped. Used so interaction magnitudes are
    comparable and the indicator enters on a sane scale. Pure transform of the
    matrix passed (the walk-forward refits ridge norm on TRAIN separately, so this
    is just a feature-construction scaling, not a fit-on-all leak: it is applied
    identically to train/val/test inside ridge_walkforward's own standardizer)."""
    mu = np.nanmean(M, axis=0)
    sd = np.nanstd(M, axis=0)
    sd = np.where(sd > 1e-12, sd, 1.0)
    return (M - mu) / sd


def _build_interactions(F, R, j):
    """Columns to append for regime indicator j: the standardized indicator, plus
    each basis_factor * standardized_indicator. (basis factors enter raw; ridge's
    own madz standardizer normalizes everything per-fold.)

    The interaction basis*ind lets a linear model realize an effective basis
    weight w_eff = w_base + w_int * ind that changes sign as the (causal) regime
    indicator crosses a threshold -- the exact lever the diagnostic probes."""
    ind = R[:, j:j + 1]
    indz = _zscore_cols(ind)              # (N,1)
    inter = F * indz                      # (N,4) broadcast: each factor * ind
    return np.column_stack([indz, inter])  # (N,5): indicator + 4 interactions


def regime_conditioned(name, folds, X, F, R, y, day_idx, days, null_n=400):
    """Walk-forward block ΔP for: baseline (spot64), +plain-basis (spot64+F4),
    and per-indicator +regime-basis (spot64 + F4 + indicator + 4 interactions)."""
    base = _pooledP(_wf_on_folds(X, y, day_idx, days, folds))
    Xplain = np.column_stack([X, F])
    plain = _pooledP(_wf_on_folds(Xplain, y, day_idx, days, folds))

    print("\n-- REGIME-CONDITIONED RIDGE (%s): walk-forward pooled Pearson --"
          % name)
    if base is None:
        print("   baseline UNAVAILABLE (insufficient folds/samples)")
        return dict(regime=name, status="unavailable")

    print("   baseline (spot64)            P=%+.4f S=%+.4f beta=%+.3f sigR=%.4f n=%d"
          % (base["P"], base["S"], base["beta"], base["sig_ratio"], base["n"]))
    plain_dP = None
    if plain is not None:
        plain_dP = plain["P"] - base["P"]
        print("   +plain-basis (spot64+F4)     P=%+.4f S=%+.4f beta=%+.3f  "
              "block ΔP=%+.4f"
              % (plain["P"], plain["S"], plain["beta"], plain_dP))

    per_ind = {}
    for j, nm in enumerate(REGIME_NAMES):
        addcols = _build_interactions(F, R, j)
        Xr = np.column_stack([X, F, addcols])   # spot64 + basis + ind + interactions
        full = _pooledP(_wf_on_folds(Xr, y, day_idx, days, folds))
        if full is None:
            per_ind[nm] = dict(status="unavailable")
            print("   +regime-basis[%s] UNAVAILABLE" % nm)
            continue
        dP = full["P"] - base["P"]
        d_vs_plain = (full["P"] - plain["P"]) if plain is not None else float("nan")
        nb = permute_y_null(full["pooled_yhat"], full["pooled_y"],
                            n=null_n, seed=0)
        per_ind[nm] = dict(
            P=round(full["P"], 4), S=round(full["S"], 4),
            beta=round(full["beta"], 3), sig_ratio=round(full["sig_ratio"], 4),
            n=full["n"], perfold_P=full["perfold_P"],
            block_dP=round(dP, 4), dP_vs_plain=round(d_vs_plain, 4),
            null_band_975=round(nb, 4),
            above_null=bool(abs(full["P"]) > nb))
        print("   +regime-basis[%-12s] P=%+.4f S=%+.4f beta=%+.3f | block ΔP=%+.4f "
              "| ΔvsPlain=%+.4f | null=%.4f %s | pf=%s"
              % (nm, full["P"], full["S"], full["beta"], dP, d_vs_plain, nb,
                 ">" if abs(full["P"]) > nb else "<=", full["perfold_P"]))

    return dict(
        regime=name, status="ok",
        baseline=dict(P=base["P"], S=base["S"], beta=base["beta"],
                      sig_ratio=base["sig_ratio"], n=base["n"],
                      perfold_P=base["perfold_P"]),
        plain_basis=(None if plain is None else dict(
            P=plain["P"], S=plain["S"], beta=plain["beta"],
            block_dP=round(plain_dP, 4), perfold_P=plain["perfold_P"])),
        plain_block_dP=(None if plain_dP is None else round(plain_dP, 4)),
        per_indicator=per_ind,
    )


# ===========================================================================
# (C) LEAKAGE: future-corruption check on the regime indicators
# ===========================================================================
def leakage_check(folds, null_n=400):
    """Recompute R3 on a day with the per-second spot mid corrupted strictly after
    a cut, and verify the regime-conditioned block ΔP on the TEST rows whose
    prediction-second is <= the cut is unchanged. Reported as a per-day window
    identity check (the strong-mechanism leakage guard) on the diagnostic factor's
    best indicator, plus a re-run of the full regime-basis ΔP under corruption."""
    print("\n-- LEAKAGE: future-corruption of the per-second spot mid --")
    # Day-level identity check: corrupt after 50% of each day; <=cut prediction
    # rows must yield byte-identical regime indicators.
    days = _common_days()
    n_checked = n_changed = 0
    sample_days = days[::max(1, len(days) // 40)]   # ~40 days spread across span
    for day in sample_days:
        lf = p.join(LASTTS_DIR, "%s.npz" % day)
        mf = p.join(MID_DIR, "%s.npz" % day)
        with np.load(lf) as zl:
            ts = zl["timestamps"].astype(np.int64)
        with np.load(mf) as zm:
            sec = zm["sec"].astype(np.int64)
            spot = zm["spot_mid"].astype(np.float64)
        pred_secs = ts // US_PER_SEC
        cut_i = int(0.5 * sec.size)
        cut_sec = int(sec[cut_i])
        R0 = causal_regime_at_pred_secs(sec, spot, pred_secs)
        rng = np.random.default_rng(0)
        spot_c = spot.copy()
        fut = np.arange(sec.size) > cut_i
        scale = float(np.nanstd(spot)) or 1.0
        spot_c[fut] = rng.standard_normal(int(fut.sum())) * scale * 50.0 + scale * 1000.0
        R1 = causal_regime_at_pred_secs(sec, spot_c, pred_secs)
        keep = pred_secs <= cut_sec
        for nm in REGIME_NAMES:
            a0, a1 = R0[nm][keep], R1[nm][keep]
            both_nan = np.isnan(a0) & np.isnan(a1)
            same = both_nan | (a0 == a1)
            n_checked += int(same.size)
            n_changed += int((~same).sum())
    print("   per-day <=cut identity: checked %d window-values across %d days, "
          "%d changed -> %s"
          % (n_checked, len(sample_days), n_changed,
             "LEAKAGE-FREE" if n_changed == 0 else "LEAK DETECTED"))
    return dict(n_checked=n_checked, n_changed=n_changed,
                n_days=len(sample_days),
                leakage_free=bool(n_changed == 0))


# ===========================================================================
def run_regime(name, folds, X, F, R, y, day_idx, days, null_n=400):
    print("\n" + "=" * 80)
    print("=== REGIME: %s   folds=%s ===" % (name, [f["name"] for f in folds]))
    print("=" * 80)
    diag = diagnostic(name, folds, F, R, y, day_idx, days)
    cond = regime_conditioned(name, folds, X, F, R, y, day_idx, days, null_n=null_n)
    cond["diagnostic"] = diag
    return cond


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--null_n", type=int, default=400)
    ap.add_argument("--json_out", default="")
    ap.add_argument("--skip_leakage", action="store_true")
    args = ap.parse_args()

    X, F, R, y, day_idx, days, skipped = load_all(verbose=True)
    out = {"n_samples": int(X.shape[0]), "n_days_kept": len(days),
           "n_skipped": len(skipped), "spot_D": int(X.shape[1]),
           "basis_D": int(F.shape[1]), "regime_D": int(R.shape[1]),
           "regime_names": REGIME_NAMES, "diag_factor": DIAG_FACTOR,
           "vol_win_sec": VOL_WIN_SEC, "er_win_sec": ER_WIN_SEC,
           "abs_win_sec": ABS_WIN_SEC}

    out["strong"] = run_regime("STRONG", STRONG_FOLDS, X, F, R, y, day_idx, days,
                               null_n=args.null_n)
    out["choppy"] = run_regime("CHOPPY", CHOPPY_FOLDS, X, F, R, y, day_idx, days,
                               null_n=args.null_n)

    if not args.skip_leakage:
        out["leakage"] = leakage_check(STRONG_FOLDS, null_n=args.null_n)

    # compact bottom-line table (numbers only; no verdict)
    print("\n" + "=" * 80)
    print("=== BOTTOM-LINE: block ΔP over spot64 baseline (numbers, no verdict) ===")
    print("=" * 80)
    for reg in ("strong", "choppy"):
        r = out[reg]
        if r.get("status") != "ok":
            print("[%s] unavailable" % reg)
            continue
        print("[%s] plain-basis ΔP=%s" % (reg, r["plain_block_dP"]))
        for nm in REGIME_NAMES:
            pi = r["per_indicator"].get(nm, {})
            if pi.get("status") == "unavailable":
                print("       regime-basis[%-12s] unavailable" % nm)
                continue
            print("       regime-basis[%-12s] block ΔP=%+.4f  ΔvsPlain=%+.4f  "
                  "%s null" % (nm, pi["block_dP"], pi["dP_vs_plain"],
                               "above" if pi["above_null"] else "within"))

    if args.json_out:
        def _clean(o):
            if isinstance(o, dict):
                return {k: _clean(v) for k, v in o.items()
                        if not isinstance(v, np.ndarray)}
            if isinstance(o, list):
                return [_clean(v) for v in o]
            return o
        with open(args.json_out, "w") as f:
            json.dump(_clean(out), f, indent=2, default=float)
        print("\nWrote %s" % args.json_out)


if __name__ == "__main__":
    main()

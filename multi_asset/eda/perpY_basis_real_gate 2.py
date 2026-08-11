"""Stage C REAL-BASIS Ridge gate: does perp_mid - spot_mid predict perp y_600?

THE DECISIVE QUESTION
---------------------
A spot-feature model only reaches ~0.013 Pearson on the choppy-2026 PERP y_600
(~half of spot->spot) because the perp target carries a basis/funding component
orthogonal to the mid-RELATIVE spot features (the basis cancels in them). The
hypothesis: the REAL basis = perp_mid - spot_mid (absolute mids), its z-score and
mean-reversion, is a genuine orthogonal predictor of perp returns (high basis ->
perp rich -> reverts down -> negative perp return).

A prior attempt FAILED because the cached features were mid-relative (no absolute
price) so the basis cancelled. Here we compute the basis from the ABSOLUTE Tardis
book mids (data/mid_cache via build_mid_cache) -> basis factors (build_basis_
factors) -> Ridge-gate them on the perp target.

WHAT THIS REPORTS (numbers only; the controller decides GO/NO-GO)
----------------------------------------------------------------
Separately for STRONG (2025-02, 2025-04) and CHOPPY (2026), walk-forward
(train>=230d / val / test, embargo 1, reusing perpY_ridge_gate.ridge_walkforward):
  * baseline pooled Pearson  (spot-64 -> perp y_600)
  * +basis pooled Pearson    (spot-64 + 4 basis factors), block ΔP
  * add-one-in ΔP for EACH basis factor (64 + that one factor)
  * each basis factor's OWN univariate IC vs perp y_600 (value + SIGN)
  * leakage: permute_y_null band on +basis pooled, AND a SHIFT SENTINEL
    (rebuild the basis with perp_mid shifted +600s -> a true leak would make ΔP
    JUMP; the correctly-aligned basis must NOT).

JOIN
----
Per day we load data/lastts_cache (spot_last 64 features + the PERP y_600 +
y_mask_600 + prediction timestamps, already constant-offset aligned by the
lastts builder) and data/basis_cache (the 4 factors at the SAME prediction
timestamps). We assert the timestamps match exactly, then concatenate. The
spot->perp join is therefore the same constant-offset method perpY_ridge_gate
uses; basis factors are joined by exact prediction timestamp.

CLI
---
  python multi_asset/eda/perpY_basis_real_gate.py
  python multi_asset/eda/perpY_basis_real_gate.py --json_out /tmp/basis_gate.json
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
FACTOR_NAMES = bbf.FACTOR_NAMES

STRONG_FOLDS = [
    dict(name="strong_2025_02", test_start="2025-02-01"),
    dict(name="strong_2025_04", test_start="2025-04-01"),
]
CHOPPY_FOLDS = [
    dict(name="choppy_2026", test_start="2026-03-01"),
]


# ---------------------------------------------------------------------------
# loading: lastts (spot64 + perp y) JOIN basis_cache (4 factors), by timestamp
# ---------------------------------------------------------------------------
def _common_days():
    last = {p.basename(f)[:-4] for f in glob.glob(p.join(LASTTS_DIR, "*.npz"))}
    bas = {p.basename(f)[:-4] for f in glob.glob(p.join(BASIS_DIR, "*.npz"))}
    return sorted(last & bas)


def _load_day(day, shift_basis_sec=0):
    """Return (X64, F4, y_perp, ok, info) for one day, joined by timestamp.

    X64: spot_last features; F4: the 4 basis factors (optionally rebuilt with a
    perp_mid time-shift sentinel); y_perp: PERP y_600 RAW. All masked by lastts
    y_mask_600 + finite, subsampled ::SUBSAMPLE."""
    lf = p.join(LASTTS_DIR, "%s.npz" % day)
    with np.load(lf) as zl:
        X = zl["spot_last"].astype(np.float64)        # (N,64)
        ts = zl["timestamps"].astype(np.int64)
        y = zl["y_600"].astype(np.float64)
        mask = zl["y_mask_600"].astype(bool)

    if shift_basis_sec == 0:
        bf = p.join(BASIS_DIR, "%s.npz" % day)
        with np.load(bf) as zb:
            bts = zb["timestamps"].astype(np.int64)
            F = zb["F"].astype(np.float64)
    else:
        # SHIFT SENTINEL: rebuild basis with perp_mid shifted +shift_basis_sec.
        # If the basis were leaking the future, shifting the perp leg forward
        # (so basis at t reflects perp at t+shift) would INCREASE ΔP; correct
        # alignment must not benefit.
        bts, F = _rebuild_basis_shifted(day, ts, shift_basis_sec)

    if bts.shape != ts.shape or not np.array_equal(bts, ts):
        return None, None, None, False, "ts_mismatch"

    keep = mask.copy()
    keep[~np.isfinite(y)] = False
    keep &= np.all(np.isfinite(X), axis=1)
    keep &= np.all(np.isfinite(F), axis=1)
    idx = np.where(keep)[0][::SUBSAMPLE]
    if idx.size == 0:
        return None, None, None, False, "no_valid_rows"
    return X[idx], F[idx], y[idx], True, "ok"


def _rebuild_basis_shifted(day, ts_us, shift_sec):
    """Rebuild the 4 basis factors with perp_mid shifted forward by `shift_sec`
    seconds (leakage sentinel). spot_mid untouched."""
    mf = p.join(MID_DIR, "%s.npz" % day)
    with np.load(mf) as zm:
        sec = zm["sec"].astype(np.int64)
        spot_mid = zm["spot_mid"].astype(np.float64)
        perp_mid = zm["perp_mid"].astype(np.float64)
    # shift perp_mid so that index i carries perp_mid from i+shift (future leg).
    n = sec.size
    perp_shift = np.full(n, np.nan)
    if shift_sec < n:
        perp_shift[:n - shift_sec] = perp_mid[shift_sec:]
        perp_shift[n - shift_sec:] = perp_mid[-1]    # pad tail
    parts = bbf.per_second_factors(sec, spot_mid, perp_shift)
    pred_secs = ts_us // bbf.US_PER_SEC
    sampled = bbf.sample_at_pred_secs(sec, parts, pred_secs)
    F = np.column_stack([sampled[nm] for nm in FACTOR_NAMES])
    return ts_us, F


def load_all(shift_basis_sec=0, verbose=False):
    """Load whole span; returns X64, F4, y, day_idx, days, skipped."""
    days = _common_days()
    Xs, Fs, ys, di = [], [], [], []
    skipped = {}
    kept_days = []
    for k, day in enumerate(days):
        X, F, y, ok, info = _load_day(day, shift_basis_sec=shift_basis_sec)
        if not ok:
            skipped[day] = info
            continue
        Xs.append(X); Fs.append(F); ys.append(y)
        di.append(np.full(y.shape[0], len(kept_days), dtype=np.int32))
        kept_days.append(day)
    X = np.concatenate(Xs); F = np.concatenate(Fs)
    y = np.concatenate(ys); day_idx = np.concatenate(di)
    if verbose:
        from collections import Counter
        print("[load] %d common days, kept %d, skipped %d; M=%d, spot D=%d, "
              "basis D=%d  shift=%ds"
              % (len(days), len(kept_days), len(skipped), X.shape[0],
                 X.shape[1], F.shape[1], shift_basis_sec))
        if skipped:
            print("[load] skip reasons:", dict(Counter(skipped.values())))
    return X, F, y, day_idx, kept_days, skipped


# ---------------------------------------------------------------------------
# walk-forward over a chosen fold set (reuses prg.ridge_walkforward verbatim)
# ---------------------------------------------------------------------------
def _wf_on_folds(Xmat, y, day_idx, days, folds):
    """Run prg.ridge_walkforward with prg.FOLDS temporarily set to `folds`.
    Returns the pooled dict (or None)."""
    saved = prg.FOLDS
    prg.FOLDS = folds
    try:
        res = prg.ridge_walkforward(Xmat, y, day_idx, days,
                                    norm="madz", verbose=False)
    finally:
        prg.FOLDS = saved
    return res


def _pooledP(res):
    if res is None or res["pooled"] is None:
        return None
    return res["pooled"]


def _regime_test_mask(folds, day_idx, days):
    """Boolean row mask for rows whose day falls in ANY of this regime's TEST
    spans (mirrors prg.ridge_walkforward fold geometry: [first_ge(test_start),
    +TEST_DAYS)). Used so the univariate IC is reported per-regime, not pooled
    across the whole 2024-26 span."""
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


# ---------------------------------------------------------------------------
# univariate IC of each basis factor vs perp y (value + sign)
# ---------------------------------------------------------------------------
def _univariate_ic(F, y):
    out = {}
    for i, nm in enumerate(FACTOR_NAMES):
        col = F[:, i]
        m = np.isfinite(col) & np.isfinite(y)
        if m.sum() < 100 or np.std(col[m]) <= 0:
            out[nm] = dict(P=float("nan"), S=float("nan"), n=int(m.sum()))
            continue
        out[nm] = dict(P=round(float(pearsonr(col[m], y[m])[0]), 5),
                       S=round(float(spearmanr(col[m], y[m])[0]), 5),
                       n=int(m.sum()))
    return out


# ---------------------------------------------------------------------------
# run one regime (strong / choppy)
# ---------------------------------------------------------------------------
def run_regime(name, folds, X, F, y, day_idx, days, null_n=1000):
    print("\n" + "=" * 78)
    print("=== REGIME: %s   folds=%s ===" % (name, [f["name"] for f in folds]))
    print("=" * 78)

    # univariate IC: restrict to THIS regime's test-span rows so STRONG and
    # CHOPPY get distinct numbers (does the basis alone correlate with the perp
    # return, and with what sign, in this regime?). full-pool IC also reported.
    te_mask = _regime_test_mask(folds, day_idx, days)
    uic = _univariate_ic(F[te_mask], y[te_mask])
    uic_pool = _univariate_ic(F, y)
    print("\n-- basis factor UNIVARIATE IC vs perp y_600 (%s test rows; n=%d) --"
          % (name, int(te_mask.sum())))
    print("%-16s %9s %9s %10s" % ("factor", "Pearson", "Spearman", "n"))
    for nm in FACTOR_NAMES:
        d = uic[nm]
        print("%-16s %+9.5f %+9.5f %10d" % (nm, d["P"], d["S"], d["n"]))
    print("  (full-pool IC for reference: "
          + ", ".join("%s P=%+.4f" % (nm, uic_pool[nm]["P"])
                      for nm in FACTOR_NAMES) + ")")

    # baseline (spot 64)
    base = _pooledP(_wf_on_folds(X, y, day_idx, days, folds))
    # +basis block (spot 64 + 4 factors)
    Xb = np.column_stack([X, F])
    full = _pooledP(_wf_on_folds(Xb, y, day_idx, days, folds))

    print("\n-- walk-forward pooled Pearson (block) --")
    if base is None or full is None:
        print("  UNAVAILABLE (insufficient folds/samples for %s)" % name)
        return dict(regime=name, status="unavailable", univariate_ic=uic)
    dP = full["P"] - base["P"]
    print("  baseline (spot64)      P=%+.4f  S=%+.4f  beta=%+.3f  sigR=%.4f  n=%d"
          % (base["P"], base["S"], base["beta"], base["sig_ratio"], base["n"]))
    print("  +basis  (spot64+4)     P=%+.4f  S=%+.4f  beta=%+.3f  sigR=%.4f  n=%d"
          % (full["P"], full["S"], full["beta"], full["sig_ratio"], full["n"]))
    print("  block ΔP (+basis - baseline) = %+.4f   (ΔS=%+.4f)"
          % (dP, full["S"] - base["S"]))
    print("  per-fold P baseline:", base["perfold_P"])
    print("  per-fold P +basis:  ", full["perfold_P"])

    # add-one-in per factor
    print("\n-- add-one-in ΔP per basis factor (spot64 + ONE factor) --")
    add_one = {}
    for i, nm in enumerate(FACTOR_NAMES):
        Xi = np.column_stack([X, F[:, i]])
        r = _pooledP(_wf_on_folds(Xi, y, day_idx, days, folds))
        if r is None:
            add_one[nm] = None
            print("  %-16s UNAVAILABLE" % nm)
            continue
        d1 = r["P"] - base["P"]
        add_one[nm] = dict(P=round(r["P"], 4), dP=round(d1, 4),
                           S=round(r["S"], 4), beta=round(r["beta"], 3))
        print("  %-16s P=%+.4f  ΔP=%+.4f  (S=%+.4f beta=%+.3f)"
              % (nm, r["P"], d1, r["S"], r["beta"]))

    # leakage: null band on +basis pooled predictions
    null_band = permute_y_null(full["pooled_yhat"], full["pooled_y"],
                               n=null_n, seed=0)
    print("\n-- leakage: y-permutation null band (97.5pct |IC|) --")
    print("  null band = %.4f  -> +basis pooled |P|=%.4f %s band"
          % (null_band, abs(full["P"]),
             ">" if abs(full["P"]) > null_band else "<="))

    return dict(
        regime=name, status="ok",
        univariate_ic=uic, univariate_ic_fullpool=uic_pool,
        n_test_rows=int(te_mask.sum()),
        baseline=dict(P=base["P"], S=base["S"], beta=base["beta"],
                      sig_ratio=base["sig_ratio"], n=base["n"],
                      perfold_P=base["perfold_P"]),
        plus_basis=dict(P=full["P"], S=full["S"], beta=full["beta"],
                        sig_ratio=full["sig_ratio"], n=full["n"],
                        perfold_P=full["perfold_P"]),
        block_dP=round(dP, 4), block_dS=round(full["S"] - base["S"], 4),
        add_one_in=add_one,
        null_band_975=round(null_band, 4),
        plus_basis_above_null=bool(abs(full["P"]) > null_band),
    )


# ---------------------------------------------------------------------------
# shift sentinel: rebuild basis with perp_mid +600s, re-measure block ΔP
# ---------------------------------------------------------------------------
def shift_sentinel(name, folds, shift_sec=600, null_n=400):
    print("\n" + "-" * 78)
    print("-- SHIFT SENTINEL (%s): rebuild basis with perp_mid +%ds --"
          % (name, shift_sec))
    Xs, Fs, ys, di, days, _ = load_all(shift_basis_sec=shift_sec, verbose=False)
    base = _pooledP(_wf_on_folds(Xs, ys, di, days, folds))
    Xb = np.column_stack([Xs, Fs])
    full = _pooledP(_wf_on_folds(Xb, ys, di, days, folds))
    if base is None or full is None:
        print("   UNAVAILABLE")
        return dict(regime=name, status="unavailable")
    dP = full["P"] - base["P"]
    print("   baseline P=%+.4f   +shifted-basis P=%+.4f   block ΔP=%+.4f"
          % (base["P"], full["P"], dP))
    return dict(regime=name, shift_sec=shift_sec,
                baseline_P=round(base["P"], 4),
                plus_shifted_basis_P=round(full["P"], 4),
                shifted_block_dP=round(dP, 4))


# ---------------------------------------------------------------------------
def _sample_raw_rows(n=8):
    """Print a few raw (spot_mid, perp_mid, basis_bps) rows so the basis can be
    eyeballed as real (perp ~ spot +- a few bps)."""
    day = "2025-02-10"
    mf = p.join(MID_DIR, "%s.npz" % day)
    if not p.exists(mf):
        print("[raw] mid_cache for %s not built yet" % day)
        return []
    with np.load(mf) as zm:
        sec = zm["sec"].astype(np.int64)
        spot = zm["spot_mid"].astype(np.float64)
        perp = zm["perp_mid"].astype(np.float64)
    idx = np.linspace(1000, sec.size - 1000, n).astype(int)
    rows = []
    print("\n-- SAMPLE RAW MID ROWS (%s) — proof the basis is real --" % day)
    print("%-12s %14s %14s %12s" % ("unix_sec", "spot_mid", "perp_mid", "basis_bps"))
    for i in idx:
        b = (perp[i] - spot[i]) / spot[i] * 1e4
        print("%-12d %14.2f %14.2f %+12.3f" % (sec[i], spot[i], perp[i], b))
        rows.append(dict(sec=int(sec[i]), spot_mid=float(spot[i]),
                         perp_mid=float(perp[i]), basis_bps=round(float(b), 3)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--null_n", type=int, default=1000)
    ap.add_argument("--json_out", default="")
    ap.add_argument("--skip_sentinel", action="store_true")
    args = ap.parse_args()

    raw_rows = _sample_raw_rows()

    X, F, y, day_idx, days, skipped = load_all(verbose=True)

    out = {"raw_rows": raw_rows, "n_samples": int(X.shape[0]),
           "n_days_kept": len(days), "n_skipped": len(skipped),
           "spot_D": int(X.shape[1]), "basis_D": int(F.shape[1])}

    out["strong"] = run_regime("STRONG", STRONG_FOLDS, X, F, y, day_idx, days,
                               null_n=args.null_n)
    out["choppy"] = run_regime("CHOPPY", CHOPPY_FOLDS, X, F, y, day_idx, days,
                               null_n=args.null_n)

    if not args.skip_sentinel:
        out["shift_sentinel_strong"] = shift_sentinel("STRONG", STRONG_FOLDS)
        out["shift_sentinel_choppy"] = shift_sentinel("CHOPPY", CHOPPY_FOLDS)
        # INTERPRETATION of the shift sentinel.
        # The sentinel injects the future on purpose: basis(t) := perp(t+600) -
        # spot(t) ~ perp(t+600) - perp(t) = the numerator of the y_600 target.
        # So a LARGE shifted ΔP (-> ~0.9 P) is the EXPECTED, REQUIRED behaviour:
        # it proves the harness is SENSITIVE to a future leak. The real, correctly
        # aligned basis is leak-FREE iff its OWN block ΔP is ~0 AND its +basis
        # pooled |P| sits within the y-permutation null band — which is the actual
        # leakage verdict, independent of the sentinel jump.
        print("\n-- SHIFT-SENTINEL VERDICT --")
        for reg, key in (("strong", "shift_sentinel_strong"),
                         ("choppy", "shift_sentinel_choppy")):
            if out[reg].get("status") == "ok" and out[key].get("status") != "unavailable":
                corr_dP = out[reg]["block_dP"]
                shift_dP = out[key]["shifted_block_dP"]
                out[key]["correct_block_dP"] = corr_dP
                # sentinel fired (sensitive) iff the injected-future basis jumps
                sentinel_fired = bool(shift_dP > 0.30)
                out[key]["sentinel_fired_as_designed"] = sentinel_fired
                # real basis clean iff correct ΔP small AND within null band
                within_null = out[reg]["plus_basis_above_null"] is False
                real_clean = bool(abs(corr_dP) < 0.01 and within_null)
                out[key]["real_basis_leakage_free"] = real_clean
                print("   [%s] correct(real) ΔP=%+.4f (|P|%s null band) ; "
                      "future-injected ΔP=%+.4f -> sentinel %s ; real basis %s"
                      % (reg, corr_dP, "within" if within_null else "ABOVE",
                         shift_dP,
                         "FIRED (sensitive, as designed)" if sentinel_fired
                         else "DID NOT FIRE (test insensitive!)",
                         "LEAKAGE-FREE" if real_clean else "SUSPECT"))

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(out, f, indent=2, default=float)
        print("\nWrote %s" % args.json_out)


if __name__ == "__main__":
    main()

"""STAGE C1 GATE — does adding 6 cross-venue/basis factors to the spot-64 Ridge
recover IC lost on the PERP ``y_600`` target?

Reuses the GATE A machinery (``perpY_ridge_gate``): same MAD-σ feature norm fit
on TRAIN only, same closed-form Ridge with val-Pearson λ selection, same RAW
``y_600`` scoring, same 1-day-embargo walk-forward folds, same ``permute_y_null``.
The ONLY additions here:

  * a factor-aware loader that ALSO reads ``npz_perp.X[:, -1, :]`` and appends the
    6 ``build_interaction_factors`` columns to the spot-64 design matrix (joined
    BY POSITION per day, same constant-shift guard as GATE A);
  * separate STRONG (2025-02, 2025-04) vs CHOPPY (2026) pooled reporting;
  * block ΔP (baseline spot-64  vs  spot-64 + 6 factors);
  * add-one-in ΔP per individual factor (each added ALONE to the 64);
  * a VENUE-CROSS-SHIFT sentinel: shift the PERP arrays by +N rows (≈+600s)
    relative to spot before recomputing the factors. If the factors would exploit
    a mis-alignment leak, the shifted-Ridge ΔP JUMPS while the aligned ΔP does
    not. (If the ALIGNED version itself shows leak-like inflation, we REPORT it.)

This file does NOT modify GATE A; it imports from it. Runs CPU-only.

  python multi_asset/eda/perpY_basis_gate.py                # full gate
  python multi_asset/eda/perpY_basis_gate.py --addone       # + per-factor add-one
  python multi_asset/eda/perpY_basis_gate.py --sentinel     # + cross-shift leak test
  python multi_asset/eda/perpY_basis_gate.py --all --json_out /tmp/c1.json
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
from multi_asset.data.build_interaction_factors import (  # noqa: E402
    FACTOR_NAMES, compute_interaction_factors, finite_factors)
from multi_asset.eda.leakage_null import permute_y_null  # noqa: E402
from multi_asset.eda.perpY_ridge_gate import (  # noqa: E402
    EMBARGO_DAYS, MIN_TRAIN_DAYS, PERP_DIR, SHIFT_TOL_US, SPOT_DIR, SUBSAMPLE,
    TEST_DAYS, VAL_DAYS, _all_days, _fit_select, _metrics, _predict)

# Tiny last-timestep cache (build_lastts_cache.py) — 120 KB/day vs 73 MB/day full
# X member. The gate only needs X[:,-1,:]+ts+y; reading the full panels on every
# pass is ~365 GB of storage reads. If the cache exists we read it (bit-identical
# slice, verified); else we fall back to the full npz panels.
LASTTS_DIR = p.join(p.dirname(SPOT_DIR), "lastts_cache")

# Fold groups for the C1 report (strong vs choppy reported SEPARATELY).
STRONG_FOLDS = [dict(name="strong_2025_02", test_start="2025-02-01"),
                dict(name="strong_2025_04", test_start="2025-04-01")]
CHOPPY_FOLDS = [dict(name="choppy_2026", test_start="2026-03-01")]


# ---------------------------------------------------------------------------
# factor-aware loader (mirrors GATE A _load_day; adds perp-X factor columns)
# ---------------------------------------------------------------------------
def _load_day_with_factors(day: str, perp_shift_rows: int = 0,
                           causal_z: bool = False):
    """Return (X_spot64, F_factors6, y_perp, ok, info) for one day.

    Positional spot↔perp join (constant whole-second offset = label convention,
    NOT row misalignment — asserted constant & in-tol). Same mask (spot
    y_mask_600 ∧ finite) and ::SUBSAMPLE as GATE A so the baseline here is
    byte-identical to GATE A's spot-64 design rows.

    perp_shift_rows : roll the PERP feature rows by +k BEFORE computing factors
                      (k>0 = perp sees the future relative to spot). Used by the
                      venue-cross-shift sentinel. 0 = correctly aligned.
    """
    cpath = p.join(LASTTS_DIR, f"{day}.npz")
    if p.exists(cpath):                                # tiny cache (preferred)
        c = np.load(cpath)
        sts = c["timestamps"].astype(np.int64)
        pts = c["perp_ts"].astype(np.int64)
        Xs_src = c["spot_last"]
        Xp_src = c["perp_last"]
        yperp_src = c["y_600"]
        mask_src = c["y_mask_600"]
    else:                                              # fall back to full panels
        ds = np.load(p.join(SPOT_DIR, f"{day}.npz"), allow_pickle=True)
        dp = np.load(p.join(PERP_DIR, f"{day}.npz"), allow_pickle=True)
        sts = ds["timestamps"].astype(np.int64)
        pts = dp["timestamps"].astype(np.int64)
        Xs_src = ds["X"][:, -1, :]
        Xp_src = dp["X"][:, -1, :]
        yperp_src = dp["y_600"]
        mask_src = ds["y_mask_600"]
    if sts.shape != pts.shape:
        return None, None, None, False, "len_mismatch"
    diff = pts - sts
    if diff.size == 0:
        return None, None, None, False, "empty"
    if not np.all(diff == diff[0]):
        return None, None, None, False, "nonconst_shift"
    if abs(int(diff[0])) > SHIFT_TOL_US:
        return None, None, None, False, f"shift_{int(diff[0])//1_000_000}s_gt_tol"

    Xs = Xs_src.astype(np.float64)                    # (N,64) spot last timestep
    Xp = Xp_src.astype(np.float64)                    # (N,64) perp last timestep
    yperp = yperp_src.astype(np.float64)
    mask = mask_src.astype(bool)

    Xp_used = Xp
    if perp_shift_rows:
        # roll perp rows forward by k; the wrapped tail is invalid -> mask it out
        Xp_used = np.roll(Xp, perp_shift_rows, axis=0)

    F = compute_interaction_factors(Xs, Xp_used, causal_z=causal_z)  # (N,6)
    F = finite_factors(F)

    keep = mask.copy()
    keep[~np.isfinite(yperp)] = False
    keep &= np.all(np.isfinite(Xs), axis=1)
    keep &= np.all(np.isfinite(F), axis=1)
    if perp_shift_rows:                                # drop wrapped-around rows
        wrap = np.zeros(Xs.shape[0], dtype=bool)
        if perp_shift_rows > 0:
            wrap[:perp_shift_rows] = True
        else:
            wrap[perp_shift_rows:] = True
        keep &= ~wrap
    idx = np.where(keep)[0][::SUBSAMPLE]
    if idx.size == 0:
        return None, None, None, False, "no_valid_rows"
    return Xs[idx], F[idx], yperp[idx], True, f"shift_{int(diff[0])//1_000_000}s"


def load_all_with_factors(perp_shift_rows: int = 0, causal_z: bool = False,
                          verbose: bool = False):
    """Whole common span. Returns Xspot (M,64), Ffac (M,6), y (M,),
    day_idx (M,), month (M,) 'YYYY-MM', days(list), skipped(dict)."""
    days = _all_days()
    Xs, Ff, ys, di, mo, skipped = [], [], [], [], [], {}
    for k, day in enumerate(days):
        a, f, yd, ok, info = _load_day_with_factors(day, perp_shift_rows, causal_z)
        if not ok:
            skipped[day] = info
            continue
        Xs.append(a)
        Ff.append(f)
        ys.append(yd)
        di.append(np.full(yd.shape[0], k, dtype=np.int32))
        mo.append(np.array([day[:7]] * yd.shape[0]))
    X = np.concatenate(Xs)
    F = np.concatenate(Ff)
    y = np.concatenate(ys)
    day_idx = np.concatenate(di)
    month = np.concatenate(mo)
    if verbose:
        print(f"[load] {len(days)} common days, kept {len(days)-len(skipped)}, "
              f"skipped {len(skipped)}; M={X.shape[0]} spot64 + {F.shape[1]} factors"
              + (f"  [perp_shift={perp_shift_rows} rows]" if perp_shift_rows else ""))
        if skipped:
            from collections import Counter
            print("[load] skip reasons:", dict(Counter(skipped.values())))
    return X, F, y, day_idx, month, days, skipped


# ---------------------------------------------------------------------------
# pooled walk-forward over a chosen fold list, with an arbitrary design matrix
# ---------------------------------------------------------------------------
def _pooled_wf(Xdesign, y, day_idx, days, folds, norm="madz"):
    """Walk-forward over `folds`; return pooled metrics + per-fold P over the
    *given* design matrix (spot64 or spot64+extra). Mirrors GATE A fold geometry
    (test 40d / val 20d / train ≥ MIN_TRAIN_DAYS, 1d embargo)."""
    days = list(days)

    def first_ge(date):
        for i, d in enumerate(days):
            if d >= date:
                return i
        return len(days)

    pooled_yhat, pooled_y, perfold = [], [], []
    fold_rows = []
    for fold in folds:
        ts0 = first_ge(fold["test_start"])
        te0, te1 = ts0, ts0 + TEST_DAYS
        va0, va1 = te0 - VAL_DAYS, te0
        tr0, tr1 = 0, va0 - EMBARGO_DAYS
        if te1 > len(days) or va0 < 0 or (tr1 - tr0) < MIN_TRAIN_DAYS:
            fold_rows.append(dict(name=fold["name"], status="unavailable"))
            continue
        tr_m = np.isin(day_idx, list(range(tr0, tr1)))
        va_m = np.isin(day_idx, list(range(va0, va1)))
        te_m = np.isin(day_idx, list(range(te0, te1)))
        if tr_m.sum() < 500 or va_m.sum() < 20 or te_m.sum() < 20:
            fold_rows.append(dict(name=fold["name"], status="too_few_samples"))
            continue
        sel = _fit_select(Xdesign[tr_m], y[tr_m], Xdesign[va_m], y[va_m], norm)
        if sel is None:
            fold_rows.append(dict(name=fold["name"], status="bad_sigma"))
            continue
        w, b, center, scale, sig, lam, valP = sel
        yhat = _predict(Xdesign[te_m], w, b, center, scale, sig)
        yte = y[te_m]
        m = _metrics(yhat, yte)
        perfold.append(m["P"])
        pooled_yhat.append(yhat)
        pooled_y.append(yte)
        fold_rows.append(dict(name=fold["name"], status="ok",
                              test_span=f"{days[te0]}..{days[te1-1]}",
                              best_lam=lam, val_P=round(valP, 4),
                              P=round(m["P"], 4), S=round(m["S"], 4),
                              beta=round(m["beta"], 3),
                              sig_ratio=round(m["sig_ratio"], 4),
                              n_test=int(te_m.sum())))
    if not pooled_yhat:
        return dict(folds=fold_rows, pooled=None)
    yh = np.concatenate(pooled_yhat)
    yy = np.concatenate(pooled_y)
    pm = _metrics(yh, yy)
    return dict(folds=fold_rows,
                pooled=dict(P=round(pm["P"], 4), S=round(pm["S"], 4),
                            beta=round(pm["beta"], 3),
                            sig_ratio=round(pm["sig_ratio"], 4),
                            bias_bps=round(pm["bias_bps"], 3), n=pm["n"],
                            perfold_P=[round(x, 4) for x in perfold],
                            pooled_yhat=yh, pooled_y=yy))


def _block(Xspot, Ffac, y, day_idx, days, folds, cols=None, norm="madz"):
    """baseline (spot64) vs +factors (cols subset of the 6) over `folds`."""
    base = _pooled_wf(Xspot, y, day_idx, days, folds, norm)
    if cols is None:
        cols = list(range(Ffac.shape[1]))
    Xplus = np.concatenate([Xspot, Ffac[:, cols]], axis=1)
    plus = _pooled_wf(Xplus, y, day_idx, days, folds, norm)
    return base, plus


# ---------------------------------------------------------------------------
# reporting helpers
# ---------------------------------------------------------------------------
def _pp(tag, base, plus):
    bp = base["pooled"]
    pp = plus["pooled"]
    if bp is None or pp is None:
        print(f"  [{tag}] UNAVAILABLE (a fold had too little data)")
        return None
    dP = pp["P"] - bp["P"]
    dS = pp["S"] - bp["S"]
    print(f"  [{tag}] baseline P={bp['P']:+.4f} S={bp['S']:+.4f} "
          f"(perfold {bp['perfold_P']})")
    print(f"  [{tag}] +6factor P={pp['P']:+.4f} S={pp['S']:+.4f} "
          f"(perfold {pp['perfold_P']})  β={pp['beta']:+.3f} σR={pp['sig_ratio']:.4f}")
    print(f"  [{tag}] block ΔP = {dP:+.4f}   ΔS = {dS:+.4f}   n={pp['n']}")
    return dict(baseline_P=bp["P"], baseline_S=bp["S"], plus_P=pp["P"],
                plus_S=pp["S"], dP=round(dP, 4), dS=round(dS, 4),
                plus_beta=pp["beta"], plus_sigR=pp["sig_ratio"], n=pp["n"],
                baseline_perfold=bp["perfold_P"], plus_perfold=pp["perfold_P"])


def _strip(d):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, np.ndarray):
            continue
        out[k] = _strip(v) if isinstance(v, dict) else v
    return out


# ---------------------------------------------------------------------------
# main analyses
# ---------------------------------------------------------------------------
def run_block(Xspot, Ffac, y, day_idx, days, norm="madz"):
    """Block ΔP for STRONG and CHOPPY separately + permute-y null on +factors."""
    print("\n=== STAGE C1: block ΔP (spot-64  vs  spot-64 + 6 cross-venue factors) ===")
    out = {}
    for tag, folds in (("STRONG", STRONG_FOLDS), ("CHOPPY", CHOPPY_FOLDS)):
        base, plus = _block(Xspot, Ffac, y, day_idx, days, folds, norm=norm)
        res = _pp(tag, base, plus)
        out[tag] = res
        # permute-y null band on the +factor predictions (statistical floor)
        if plus["pooled"] is not None:
            nb = permute_y_null(plus["pooled"]["pooled_yhat"],
                                plus["pooled"]["pooled_y"], n=1000, seed=0)
            print(f"  [{tag}] +factor permute-y null band(97.5%|IC|)={nb:.4f}  "
                  f"-> |P|={abs(plus['pooled']['P']):.4f} "
                  f"{'>' if abs(plus['pooled']['P'])>nb else '<='} band")
            if res is not None:
                res["plus_null_band"] = round(nb, 4)
    return out


def run_addone(Xspot, Ffac, y, day_idx, days, norm="madz"):
    """Add-one-in ΔP: each of the 6 factors added ALONE to the spot-64."""
    print("\n=== STAGE C1: add-one-in ΔP per factor (each added alone to spot-64) ===")
    out = {}
    for tag, folds in (("STRONG", STRONG_FOLDS), ("CHOPPY", CHOPPY_FOLDS)):
        base = _pooled_wf(Xspot, y, day_idx, days, folds, norm)
        if base["pooled"] is None:
            print(f"  [{tag}] baseline UNAVAILABLE")
            continue
        bP = base["pooled"]["P"]
        print(f"  [{tag}] baseline P={bP:+.4f}")
        rows = {}
        for j, nm in enumerate(FACTOR_NAMES):
            _, plus = _block(Xspot, Ffac, y, day_idx, days, folds, cols=[j], norm=norm)
            if plus["pooled"] is None:
                print(f"    {nm:24s} UNAVAILABLE")
                continue
            pP = plus["pooled"]["P"]
            print(f"    {nm:24s} P={pP:+.4f}  ΔP={pP-bP:+.4f}")
            rows[nm] = dict(P=round(pP, 4), dP=round(pP - bP, 4))
        out[tag] = dict(baseline_P=round(bP, 4), per_factor=rows)
    return out


def run_sentinel(norm="madz", shift_rows=1):
    """Venue-cross-shift leak sentinel. shift_rows=1 row ≈ +600s (PRED_STRIDE
    grid). Aligned ΔP vs perp-shifted ΔP, STRONG + CHOPPY. A clean factor set:
    aligned ΔP stable, shifted ΔP collapses toward/below the null (no spurious
    inflation). A LEAKY set: shifted ΔP JUMPS (factors were exploiting alignment
    to peek)."""
    print(f"\n=== STAGE C1: venue-cross-shift sentinel (perp rolled +{shift_rows} "
          f"row ≈ +600s vs spot) ===")
    print("[sentinel] loading ALIGNED ...")
    Xs0, F0, y0, di0, _, days0, _ = load_all_with_factors(0, verbose=True)
    print(f"[sentinel] loading SHIFTED (+{shift_rows}) ...")
    Xs1, F1, y1, di1, _, days1, _ = load_all_with_factors(shift_rows, verbose=True)
    out = {}
    for tag, folds in (("STRONG", STRONG_FOLDS), ("CHOPPY", CHOPPY_FOLDS)):
        ba, pa = _block(Xs0, F0, y0, di0, days0, folds, norm=norm)
        bs, ps = _block(Xs1, F1, y1, di1, days1, folds, norm=norm)
        if None in (ba["pooled"], pa["pooled"], bs["pooled"], ps["pooled"]):
            print(f"  [{tag}] UNAVAILABLE")
            continue
        dPa = pa["pooled"]["P"] - ba["pooled"]["P"]
        dPs = ps["pooled"]["P"] - bs["pooled"]["P"]
        nb = permute_y_null(pa["pooled"]["pooled_yhat"],
                            pa["pooled"]["pooled_y"], n=1000, seed=0)
        print(f"  [{tag}] aligned ΔP={dPa:+.4f}   shifted(+{shift_rows}) ΔP={dPs:+.4f}"
              f"   (null band {nb:.4f})")
        verdict = ("LEAK-SUSPECT: shifted ΔP grew" if dPs > dPa + nb else
                   "clean: shifted ΔP did not exceed aligned+null")
        print(f"  [{tag}] -> {verdict}")
        out[tag] = dict(aligned_dP=round(dPa, 4), shifted_dP=round(dPs, 4),
                        null_band=round(nb, 4), verdict=verdict)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--addone", action="store_true", help="per-factor add-one-in ΔP")
    ap.add_argument("--sentinel", action="store_true", help="venue-cross-shift leak test")
    ap.add_argument("--all", action="store_true", help="block + addone + sentinel")
    ap.add_argument("--causal-z", action="store_true",
                    help="use strictly-causal expanding z for factor 3")
    ap.add_argument("--norm", choices=["madz", "meanstd"], default="madz")
    ap.add_argument("--shift-rows", type=int, default=1)
    ap.add_argument("--json_out", default="")
    args = ap.parse_args()

    do_block = True
    do_addone = args.addone or args.all
    do_sentinel = args.sentinel or args.all

    out = {"norm": args.norm, "causal_z": args.causal_z}
    Xs, F, y, di, mo, days, skipped = load_all_with_factors(
        0, causal_z=args.causal_z, verbose=True)
    out["n_samples"] = int(Xs.shape[0])
    out["n_days_kept"] = len(days) - len(skipped)
    out["factor_names"] = FACTOR_NAMES

    if do_block:
        out["block"] = run_block(Xs, F, y, di, days, args.norm)
    if do_addone:
        out["addone"] = run_addone(Xs, F, y, di, days, args.norm)
    if do_sentinel:
        out["sentinel"] = run_sentinel(args.norm, args.shift_rows)

    if args.json_out:
        with open(args.json_out, "w") as fjs:
            json.dump(_strip(out), fjs, indent=2, default=float)
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()

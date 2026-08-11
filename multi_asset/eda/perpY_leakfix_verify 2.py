"""LEAK-FREE re-verification of the perp y_600 retarget (lookahead-leak fix).

Re-runs the three decisive checks on the RE-ANCHORED clean perp target
(``data/npz_spot2perp_clean``, built by build_perp_y_clean.py) and reports the
numbers SIDE-BY-SIDE with the LEAKED target (``data/lastts_cache`` y_600 = the
old position-join). Reuses ``perpY_ridge_gate`` machinery (closed-form Ridge
walk-forward, MAD-sigma norm, ::4 non-overlap subsample, 1-day embargo, raw y).

JOIN (all by position per day -- verified identical pred-timestamps across caches)
---------------------------------------------------------------------------------
Per day, these caches share byte-identical ``timestamps`` and ``spot_last`` ==
``npz_spot.X[:,-1,:]``:
  * spot-64 last-ts features : data/lastts_cache  (spot_last)
  * LEAKED perp target       : data/lastts_cache  (y_600)            <- old join
  * CLEAN perp target        : data/npz_spot2perp_clean (y_600,y_mask_600)
  * spot's OWN y_600         : data/npz_spot (y_600)                 <- leak-free
  * basis factors (4)        : data/basis_cache (F)
So we load all of them positionally per day, mask by the relevant y_mask, and
subsample ::4 for clean non-overlapping IID rows.

CHECKS
------
1. Honest perp IC: spot-64 -> {leaked, clean} perp y_600, walk-forward Ridge,
   STRONG (2025-02, 2025-04) + CHOPPY (2026), pooled clean Pearson. Does strong
   DROP and choppy RISE under the clean target (vs leaked strong ~0.045 / choppy
   ~0.009)?
2. spot-vs-perp gap: window-level corr(spot_y_600, clean perp y) (should ~0.99);
   and Ridge IC spot->spot_y vs spot->perp_clean (does the leaked 0.0247-vs-0.0147
   gap close?).
3. Basis->residual, LEAK-FREE: residual r = perp_y - spot_y for {leaked, clean}.
   Recompute IC(basis factors, r) for strong+choppy, and IC(basis, perp_y)
   directly. Is the basis->residual IC still ~0.2-0.33, or leak-driven (collapses)?

REPORTS NUMBERS ONLY -- no GO/NO-GO verdict.

CLI
---
  python multi_asset/eda/perpY_leakfix_verify.py --json_out /tmp/leakfix.json
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
from multi_asset.data import build_basis_factors as bbf          # noqa: E402

DATA_DIR = prg.DATA_DIR
SPOT_DIR = p.join(DATA_DIR, "npz_spot")
LASTTS_DIR = p.join(DATA_DIR, "lastts_cache")
CLEAN_DIR = p.join(DATA_DIR, "npz_spot2perp_clean")
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
# loading: everything positionally per day, masked + ::4
# ---------------------------------------------------------------------------
def _common_days():
    def s(d):
        return {p.basename(f)[:-4] for f in glob.glob(p.join(d, "*.npz"))
                if p.basename(f)[0].isdigit()}
    return sorted(s(LASTTS_DIR) & s(CLEAN_DIR) & s(BASIS_DIR) & s(SPOT_DIR))


def _load_day(day):
    """Return dict of aligned arrays for one day, masked (clean y_mask) + ::4.

    Keys: X64, F4, y_clean, y_leaked, y_spot. None if no valid rows.
    Rows kept: clean y_mask AND all-finite X64/F4 AND finite leaked&spot y (so the
    SAME rows are compared across targets -> fair side-by-side)."""
    last = np.load(p.join(LASTTS_DIR, "%s.npz" % day))
    clean = np.load(p.join(CLEAN_DIR, "%s.npz" % day))
    bas = np.load(p.join(BASIS_DIR, "%s.npz" % day))
    spot = np.load(p.join(SPOT_DIR, "%s.npz" % day), allow_pickle=True)

    lts = last["timestamps"].astype(np.int64)
    cts = clean["timestamps"].astype(np.int64)
    bts = bas["timestamps"].astype(np.int64)
    sts = spot["timestamps"].astype(np.int64)
    if not (np.array_equal(lts, cts) and np.array_equal(lts, bts)
            and np.array_equal(lts, sts)):
        return None  # alignment guard (should never trip given identical builds)

    X = last["spot_last"].astype(np.float64)            # (N,64)
    F = bas["F"].astype(np.float64)                      # (N,4)
    y_clean = clean["y_600"].astype(np.float64)
    m_clean = clean["y_mask_600"].astype(bool)
    y_leaked = last["y_600"].astype(np.float64)
    y_spot = spot["y_600"].astype(np.float64)

    keep = m_clean.copy()
    keep &= np.all(np.isfinite(X), axis=1)
    keep &= np.all(np.isfinite(F), axis=1)
    keep &= np.isfinite(y_clean) & np.isfinite(y_leaked) & np.isfinite(y_spot)
    idx = np.where(keep)[0][::SUBSAMPLE]
    if idx.size == 0:
        return None
    return dict(X=X[idx], F=F[idx], y_clean=y_clean[idx],
                y_leaked=y_leaked[idx], y_spot=y_spot[idx])


def load_all(verbose=True):
    days = _common_days()
    acc = {k: [] for k in ("X", "F", "y_clean", "y_leaked", "y_spot")}
    di = []
    kept = []
    for day in days:
        d = _load_day(day)
        if d is None:
            continue
        for k in acc:
            acc[k].append(d[k])
        di.append(np.full(d["X"].shape[0], len(kept), dtype=np.int32))
        kept.append(day)
    out = {k: np.concatenate(v) for k, v in acc.items()}
    out["day_idx"] = np.concatenate(di)
    out["days"] = kept
    if verbose:
        print("[load] %d common days, kept %d; M=%d rows, X D=%d, F D=%d"
              % (len(days), len(kept), out["X"].shape[0], out["X"].shape[1],
                 out["F"].shape[1]))
    return out


# ---------------------------------------------------------------------------
# walk-forward pooled Pearson on a chosen target column + fold set
# ---------------------------------------------------------------------------
def _wf_pooled(Xmat, y, day_idx, days, folds):
    saved = prg.FOLDS
    prg.FOLDS = folds
    try:
        res = prg.ridge_walkforward(Xmat, y, day_idx, days,
                                    norm="madz", verbose=False)
    finally:
        prg.FOLDS = saved
    return res["pooled"]


def _fmt(pl):
    if pl is None:
        return "UNAVAILABLE"
    return ("P=%+.4f S=%+.4f beta=%+.3f sigR=%.4f n=%d perfold=%s"
            % (pl["P"], pl["S"], pl["beta"], pl["sig_ratio"], pl["n"],
               pl["perfold_P"]))


# ---------------------------------------------------------------------------
# univariate IC of a factor block vs a target (value + sign), restricted to rows
# ---------------------------------------------------------------------------
def _univ_ic(F, y, mask=None):
    out = {}
    for i, nm in enumerate(FACTOR_NAMES):
        col = F[:, i]
        m = np.isfinite(col) & np.isfinite(y)
        if mask is not None:
            m = m & mask
        if m.sum() < 100 or np.std(col[m]) <= 0 or np.std(y[m]) <= 0:
            out[nm] = dict(P=float("nan"), S=float("nan"), n=int(m.sum()))
            continue
        out[nm] = dict(P=round(float(pearsonr(col[m], y[m])[0]), 5),
                       S=round(float(spearmanr(col[m], y[m])[0]), 5),
                       n=int(m.sum()))
    return out


def _regime_test_mask(folds, day_idx, days):
    def first_ge(date):
        for i, d in enumerate(days):
            if d >= date:
                return i
        return len(days)
    te = set()
    for fold in folds:
        ts0 = first_ge(fold["test_start"])
        te.update(range(ts0, min(ts0 + prg.TEST_DAYS, len(days))))
    return np.isin(day_idx, list(te))


# ---------------------------------------------------------------------------
# CHECK 1: honest perp IC (leaked vs clean), strong + choppy
# ---------------------------------------------------------------------------
def check1(D):
    print("\n" + "=" * 78)
    print("CHECK 1 — honest perp Ridge IC: spot-64 -> perp y_600 (LEAKED vs CLEAN)")
    print("=" * 78)
    res = {}
    for rname, folds in (("STRONG", STRONG_FOLDS), ("CHOPPY", CHOPPY_FOLDS)):
        leaked = _wf_pooled(D["X"], D["y_leaked"], D["day_idx"], D["days"], folds)
        clean = _wf_pooled(D["X"], D["y_clean"], D["day_idx"], D["days"], folds)
        print("\n-- %s --" % rname)
        print("  LEAKED perp y : %s" % _fmt(leaked))
        print("  CLEAN  perp y : %s" % _fmt(clean))
        if leaked and clean:
            print("  ΔP(clean-leaked) = %+.4f" % (clean["P"] - leaked["P"]))
        res[rname] = dict(
            leaked=_pl(leaked), clean=_pl(clean),
            dP=None if not (leaked and clean) else round(clean["P"] - leaked["P"], 4))
    return res


# ---------------------------------------------------------------------------
# CHECK 2: spot-vs-perp gap
# ---------------------------------------------------------------------------
def check2(D):
    print("\n" + "=" * 78)
    print("CHECK 2 — spot-vs-perp gap (corr + Ridge IC spot_y vs perp_clean)")
    print("=" * 78)
    res = {}
    # window-level corr(spot_y, clean perp y) per regime + pooled
    for rname, folds in (("STRONG", STRONG_FOLDS), ("CHOPPY", CHOPPY_FOLDS),
                         ("ALLROWS", None)):
        if folds is None:
            m = np.ones(D["X"].shape[0], dtype=bool)
        else:
            m = _regime_test_mask(folds, D["day_idx"], D["days"])
        a, b = D["y_spot"][m], D["y_clean"][m]
        c_clean = float(np.corrcoef(a, b)[0, 1]) if m.sum() > 2 else float("nan")
        c_leak = (float(np.corrcoef(D["y_spot"][m], D["y_leaked"][m])[0, 1])
                  if m.sum() > 2 else float("nan"))
        print("  [%-7s] corr(spot_y, clean)=%.4f   corr(spot_y, leaked)=%.4f  (n=%d)"
              % (rname, c_clean, c_leak, int(m.sum())))
        res["corr_%s" % rname] = dict(clean=round(c_clean, 4),
                                      leaked=round(c_leak, 4), n=int(m.sum()))

    # Ridge IC: spot->spot_y  vs  spot->perp_clean  (and ->perp_leaked) per regime
    print("\n  Ridge IC (spot-64 ->):")
    for rname, folds in (("STRONG", STRONG_FOLDS), ("CHOPPY", CHOPPY_FOLDS)):
        spt = _wf_pooled(D["X"], D["y_spot"], D["day_idx"], D["days"], folds)
        clr = _wf_pooled(D["X"], D["y_clean"], D["day_idx"], D["days"], folds)
        lkr = _wf_pooled(D["X"], D["y_leaked"], D["day_idx"], D["days"], folds)
        sp = spt["P"] if spt else float("nan")
        cp = clr["P"] if clr else float("nan")
        lp = lkr["P"] if lkr else float("nan")
        print("    [%-7s] spot_y P=%+.4f | perp_clean P=%+.4f (gap %+.4f) | "
              "perp_leaked P=%+.4f (gap %+.4f)"
              % (rname, sp, cp, cp - sp, lp, lp - sp))
        res["ridge_%s" % rname] = dict(
            spot_y_P=round(sp, 4), perp_clean_P=round(cp, 4),
            gap_clean=round(cp - sp, 4), perp_leaked_P=round(lp, 4),
            gap_leaked=round(lp - sp, 4))
    return res


# ---------------------------------------------------------------------------
# CHECK 3: basis -> residual, leak-free
# ---------------------------------------------------------------------------
def check3(D):
    print("\n" + "=" * 78)
    print("CHECK 3 — basis -> residual, LEAK-FREE (does the basis lever survive?)")
    print("=" * 78)
    r_clean = D["y_clean"] - D["y_spot"]          # leak-free residual
    r_leaked = D["y_leaked"] - D["y_spot"]        # old (leaked) residual
    res = {}
    for rname, folds in (("STRONG", STRONG_FOLDS), ("CHOPPY", CHOPPY_FOLDS)):
        te = _regime_test_mask(folds, D["day_idx"], D["days"])
        print("\n-- %s (test rows n=%d) --" % (rname, int(te.sum())))
        uic_rc = _univ_ic(D["F"], r_clean, te)
        uic_rl = _univ_ic(D["F"], r_leaked, te)
        uic_yc = _univ_ic(D["F"], D["y_clean"], te)
        uic_yl = _univ_ic(D["F"], D["y_leaked"], te)
        print("  IC(basis, residual)  [factor: clean_r  /  leaked_r]")
        for nm in FACTOR_NAMES:
            print("    %-16s P=%+.4f  /  %+.4f      (S=%+.4f / %+.4f)"
                  % (nm, uic_rc[nm]["P"], uic_rl[nm]["P"],
                     uic_rc[nm]["S"], uic_rl[nm]["S"]))
        print("  IC(basis, perp_y)    [factor: clean_y  /  leaked_y]")
        for nm in FACTOR_NAMES:
            print("    %-16s P=%+.4f  /  %+.4f"
                  % (nm, uic_yc[nm]["P"], uic_yl[nm]["P"]))
        res[rname] = dict(
            n_test=int(te.sum()),
            ic_basis_resid_clean={nm: uic_rc[nm] for nm in FACTOR_NAMES},
            ic_basis_resid_leaked={nm: uic_rl[nm] for nm in FACTOR_NAMES},
            ic_basis_y_clean={nm: uic_yc[nm] for nm in FACTOR_NAMES},
            ic_basis_y_leaked={nm: uic_yl[nm] for nm in FACTOR_NAMES},
        )
    # also: residual magnitude sanity
    print("\n  residual std (bps): clean=%.3f  leaked=%.3f   "
          "(leaked residual inflated by the overlap?)"
          % (float(np.std(r_clean) * 1e4), float(np.std(r_leaked) * 1e4)))
    res["resid_std_bps"] = dict(clean=round(float(np.std(r_clean) * 1e4), 3),
                                leaked=round(float(np.std(r_leaked) * 1e4), 3))
    return res


def _pl(pl):
    if pl is None:
        return None
    return dict(P=pl["P"], S=pl["S"], beta=pl["beta"],
                sig_ratio=pl["sig_ratio"], n=pl["n"], perfold_P=pl["perfold_P"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json_out", default="")
    args = ap.parse_args()

    D = load_all(verbose=True)
    out = {"n_samples": int(D["X"].shape[0]), "n_days": len(D["days"]),
           "subsample": SUBSAMPLE}
    out["check1_honest_perp_ic"] = check1(D)
    out["check2_spot_vs_perp_gap"] = check2(D)
    out["check3_basis_residual"] = check3(D)

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(out, f, indent=2, default=float)
        print("\nWrote %s" % args.json_out)


if __name__ == "__main__":
    main()

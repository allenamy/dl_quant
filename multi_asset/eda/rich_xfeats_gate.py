"""DECISIVE Ridge gate for the RICH spot-perp feature set (build_rich_xfeats.py).

> **created:** 2026-06-19  | **status:** in-progress

THE QUESTION (numbers only, no GO/NO-GO)
----------------------------------------
The perp-specific alpha is r = perp_y_600 - spot_y_600 (the basis change;
corr(spot,perp)=0.9985, r_var/perp_var~0.003). The SHALLOW set (4 basis + 6
cross-venue) lifted the perp Ridge by ~+0.01 and basis-alone is the strongest
single r-predictor (~0.5+ univariate). Does a RICH, mechanism-grounded set --
funding-cycle/carry, multi-scale basis, deep multi-scale cross-venue, and a
liquidation-cascade proxy -- capture MORE of r, and crucially does any family add
ORTHOGONALLY on top of basis?

For each family {funding, basis, xvenue, liq} and the union, per regime
(STRONG = 2025-02/04, CHOPPY = 2026), CLEAN ::4, walk-forward, MAD-sigma:
  1. IC vs r        : best univariate |P| in the family, and multivariate Ridge
                      OOS P/S vs r.
  2. IC vs perp_y   : multivariate Ridge OOS P vs perp_y (the tradable target).
  3. block deltaP   : pooled CLEAN Pearson of (SPOT64 + family) minus SPOT64, on
                      perp_y (does the family add over the production spot set?).
  4. ORTHOGONALITY  : pooled r-IC of (BASIS + family) minus (BASIS alone), on r
                      (the decisive test: beyond basis, is there more?).
  5. add-one-in     : top-12 features by |univariate r-IC|, each added to basis,
                      delta r-IC.
  6. null band      : y-permutation 97.5pct |r-IC| for the union (sampling floor).
  7. shift sentinel : basis +600s forward shift must NOT inflate r-IC (leak guard).

CALIBER (reuses perpY_ridge_gate machinery -- _fit_select / _predict / _metrics):
RAW y, per-fold MAD-sigma norm (train-only), lambda picked on VAL, walk-forward,
CLEAN ::SUBSAMPLE, 1-day embargo. Targets exact-joined on the spot pred grid
(lastts.ts == npz_spot.ts == clean.ts, verified).

Run (server):
  /root/miniconda3/envs/hsy_v5push/bin/python -m multi_asset.eda.rich_xfeats_gate \
      --regime both --report --json_out /tmp/rich_feats_gate.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os.path as p
import sys

import numpy as np
from scipy.stats import pearsonr, spearmanr

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from multi_asset.data.build_rich_xfeats import (  # noqa: E402
    FAMILIES, build_day, per_second_source, family_basis, _sample_grid,
)
from multi_asset.eda.perpY_ridge_gate import (  # noqa: E402
    LAMBDAS, _fit_select, _predict, mad_sigma,
)

DATA_DIR = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data"
LASTTS_DIR = p.join(DATA_DIR, "lastts_cache")
SPOT_DIR = p.join(DATA_DIR, "npz_spot")
CLEAN_DIR = p.join(DATA_DIR, "npz_spot2perp_clean")
MID_DIR = p.join(DATA_DIR, "mid_cache")

SUBSAMPLE = 4
EMBARGO_DAYS = 1
US = 1_000_000
HORIZON_S = 600

# Walk-forward folds per regime (test windows present on disk). train = all days
# strictly before val, minus 1-day embargo; val = VAL_DAYS before test.
TEST_DAYS = 40
VAL_DAYS = 20
MIN_TRAIN_DAYS = 200
STRONG_FOLDS = [dict(name="strong_2025_02", test_start="2025-02-01"),
                dict(name="strong_2025_04", test_start="2025-04-01")]
CHOPPY_FOLDS = [dict(name="choppy_2026_03", test_start="2026-03-01"),
                dict(name="choppy_2026_05", test_start="2026-05-01")]


# --------------------------------------------------------------------------- #
# loading: rich features (cached) + spot64 + targets, exact-joined
# --------------------------------------------------------------------------- #
def _have(day):
    return all(p.exists(p.join(d, f"{day}.npz"))
               for d in (LASTTS_DIR, SPOT_DIR, CLEAN_DIR, MID_DIR))


def _load_day(day, shift_basis_sec=0):
    """Return per-day arrays (NOT yet clean-subsampled): spot64, rich families,
    spot_y, perp_y, r, mask, ts. shift_basis_sec>0 -> rebuild the basis family
    with a FORWARD-shifted mid grid (leak sentinel)."""
    lc = np.load(p.join(LASTTS_DIR, f"{day}.npz"))
    ts = lc["timestamps"].astype(np.int64)
    pts = lc["perp_ts"].astype(np.int64)
    diff = pts - ts
    if diff.size == 0 or not np.all(diff == diff[0]) or abs(int(diff[0])) > 10 * US:
        return None
    spot64 = lc["spot_last"].astype(np.float64)               # (N,64) = npz_spot X[:,-1]

    d = build_day(day, mid_dir=MID_DIR, lastts_dir=LASTTS_DIR)
    if not np.array_equal(d["ts"], ts):
        return None
    fam = {f: d["fam"][f][1] for f in FAMILIES}               # name lists fixed below
    fam_names = {f: d["fam"][f][0] for f in FAMILIES}

    if shift_basis_sec:
        # rebuild ONLY the basis family from a forward-shifted mid grid: a forward
        # shift means the basis "seen" at t is actually the basis at t+shift -> a
        # future value; the r-IC must NOT improve (else the unshifted align peeks).
        zm = np.load(p.join(MID_DIR, f"{day}.npz"))
        sec = zm["sec"].astype(np.int64)
        src = per_second_source(sec, zm["spot_mid"], zm["perp_mid"])
        bcols = family_basis(src)
        pred_sec = ts // US
        bsamp = {k: _sample_grid(sec, v, pred_sec + shift_basis_sec) for k, v in bcols.items()}
        from multi_asset.data.build_rich_xfeats import _pctrank_at
        bsamp["basis_pctrank_30m"] = _pctrank_at(sec, src["basis_bps"], 1800, pred_sec + shift_basis_sec)
        bsamp["basis_pctrank_2h"] = _pctrank_at(sec, src["basis_bps"], 7200, pred_sec + shift_basis_sec)
        names = list(bsamp.keys())
        X = np.nan_to_num(np.column_stack([bsamp[n] for n in names]), nan=0.0,
                          posinf=0.0, neginf=0.0)
        fam["basis"] = X; fam_names["basis"] = names

    # targets, exact-joined (ts are byte-identical across the three files)
    zs = np.load(p.join(SPOT_DIR, f"{day}.npz"), allow_pickle=True)
    zc = np.load(p.join(CLEAN_DIR, f"{day}.npz"))
    if not (np.array_equal(zs["timestamps"].astype(np.int64), ts) and
            np.array_equal(zc["timestamps"].astype(np.int64), ts)):
        return None
    sy = zs["y_600"].astype(np.float64); sm = zs["y_mask_600"].astype(bool)
    cy = zc["y_600"].astype(np.float64); cm = zc["y_mask_600"].astype(bool)
    r = cy - sy
    mask = sm & cm & np.isfinite(sy) & np.isfinite(cy) & np.all(np.isfinite(spot64), axis=1)
    for f in FAMILIES:
        mask &= np.all(np.isfinite(fam[f]), axis=1)

    return dict(ts=ts, spot64=spot64, fam=fam, fam_names=fam_names,
                spot_y=sy, perp_y=cy, r=r, mask=mask)


def _clean_idx(ts):
    """Keep labels >= HORIZON_S apart on time-sorted order (anti-pattern #2)."""
    order = np.argsort(ts, kind="stable")
    dd = np.diff(np.sort(ts)); dd = dd[dd > 0]
    gap = float(np.median(dd)) / US if dd.size else 180.0
    factor = max(1, int(np.ceil(HORIZON_S / max(gap, 1e-9))))
    keep = np.zeros(ts.size, bool); keep[order[::factor]] = True
    return keep


def load_days(days, shift_basis_sec=0, verbose=False):
    """Load + clean-subsample a list of days; concatenate. Returns dict of arrays
    + day_idx + the family name lists (from the first day)."""
    acc_spot, acc_fam = [], {f: [] for f in FAMILIES}
    acc_sy, acc_cy, acc_r, acc_ts, acc_di = [], [], [], [], []
    fam_names = None
    kept_days = []
    for day in days:
        if not _have(day):
            continue
        d = _load_day(day, shift_basis_sec=shift_basis_sec)
        if d is None:
            continue
        keep = d["mask"] & _clean_idx(d["ts"])
        if keep.sum() == 0:
            continue
        if fam_names is None:
            fam_names = d["fam_names"]
        ki = len(kept_days)
        acc_spot.append(d["spot64"][keep])
        for f in FAMILIES:
            acc_fam[f].append(d["fam"][f][keep])
        acc_sy.append(d["spot_y"][keep]); acc_cy.append(d["perp_y"][keep])
        acc_r.append(d["r"][keep]); acc_ts.append(d["ts"][keep])
        acc_di.append(np.full(int(keep.sum()), ki, dtype=np.int32))
        kept_days.append(day)
    if not kept_days:
        raise RuntimeError("no usable days")
    out = dict(
        spot64=np.concatenate(acc_spot),
        fam={f: np.concatenate(acc_fam[f]) for f in FAMILIES},
        fam_names=fam_names,
        spot_y=np.concatenate(acc_sy), perp_y=np.concatenate(acc_cy),
        r=np.concatenate(acc_r), ts=np.concatenate(acc_ts),
        day_idx=np.concatenate(acc_di), n_days=len(kept_days),
        kept_days=kept_days,
    )
    if verbose:
        print(f"[load] {len(days)} candidate days, kept {len(kept_days)}; "
              f"N(clean,masked)={out['spot64'].shape[0]}  "
              f"std(r)={out['r'].std():.3e} std(perp)={out['perp_y'].std():.3e} "
              f"r_var/perp_var={out['r'].var()/max(out['perp_y'].var(),1e-30):.4f}")
    return out


# --------------------------------------------------------------------------- #
# walk-forward Ridge (pooled OOS) over a fold set, given X and target
# --------------------------------------------------------------------------- #
def _first_ge(days, date):
    for i, dd in enumerate(days):
        if dd >= date:
            return i
    return len(days)


def walkforward(X, target, day_idx, day_list, folds, norm="madz"):
    """Pooled OOS metrics over the given folds. X (N,k), target (N,). Returns
    dict(P,S,beta,sig_ratio,n,perfold_P, pooled_yhat, pooled_y)."""
    d2i = {d: i for i, d in enumerate(day_list)}
    yh_all, yy_all, perfold = [], [], []
    for fold in folds:
        ts0 = _first_ge(day_list, fold["test_start"])
        te0, te1 = ts0, ts0 + TEST_DAYS
        va0, va1 = te0 - VAL_DAYS, te0
        tr0, tr1 = 0, va0 - EMBARGO_DAYS
        if te1 > len(day_list) or va0 < 0 or (tr1 - tr0) < MIN_TRAIN_DAYS:
            continue
        tr_m = np.isin(day_idx, np.arange(tr0, tr1))
        va_m = np.isin(day_idx, np.arange(va0, va1))
        te_m = np.isin(day_idx, np.arange(te0, te1))
        if tr_m.sum() < 500 or va_m.sum() < 20 or te_m.sum() < 20:
            continue
        sel = _fit_select(X[tr_m], target[tr_m], X[va_m], target[va_m], norm)
        if sel is None:
            continue
        w, b, center, scale, sig, lam, valP = sel
        yhat = _predict(X[te_m], w, b, center, scale, sig)
        yte = target[te_m]
        if np.std(yhat) > 0 and np.std(yte) > 0:
            perfold.append(float(pearsonr(yhat, yte)[0]))
        yh_all.append(yhat); yy_all.append(yte)
    if not yh_all:
        return dict(P=float("nan"), S=float("nan"), n=0, perfold_P=[])
    yh = np.concatenate(yh_all); yy = np.concatenate(yy_all)
    if np.std(yh) <= 0 or np.std(yy) <= 0:
        return dict(P=0.0, S=0.0, n=len(yy), perfold_P=perfold,
                    pooled_yhat=yh, pooled_y=yy)
    vyh = float(np.var(yh))
    return dict(
        P=float(pearsonr(yh, yy)[0]), S=float(spearmanr(yh, yy).correlation),
        beta=float(np.cov(yy, yh)[0, 1] / vyh) if vyh > 0 else float("nan"),
        sig_ratio=float(np.std(yh) / np.std(yy)),
        n=len(yy), perfold_P=[round(x, 4) for x in perfold],
        pooled_yhat=yh, pooled_y=yy)


def _uni_ic(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 50 or x[m].std() == 0 or y[m].std() == 0:
        return float("nan"), float("nan")
    return float(pearsonr(x[m], y[m])[0]), float(spearmanr(x[m], y[m]).correlation)


# --------------------------------------------------------------------------- #
# per-regime run
# --------------------------------------------------------------------------- #
def _months_days(months):
    import datetime as dt
    out = []
    for m in months:
        y, mo = map(int, m.split("-"))
        n = (dt.date(y + (mo == 12), (mo % 12) + 1, 1) - dt.date(y, mo, 1)).days
        out += [f"{y:04d}-{mo:02d}-{dd:02d}" for dd in range(1, n + 1)]
    return out


def _all_train_days_through(end_date):
    """All feature days with full data, from the start, up to end_date inclusive
    (the walk-forward train history). lastts spans 2023-01..2026-05 but mid/clean
    start 2024-06; _have() restricts to the intersection (2024-06+)."""
    days = sorted({p.basename(f)[:-4] for f in glob.glob(p.join(LASTTS_DIR, "*.npz"))
                   if p.basename(f)[0].isdigit()})
    return [d for d in days if d <= end_date and _have(d)]


def run_regime(name, folds, json_out=None, do_sentinel=True):
    last_test = max(f["test_start"] for f in folds)
    end = _months_days([last_test[:7]])[-1]
    days = _all_train_days_through(end)
    print(f"\n{'='*78}\nREGIME={name}  folds={[f['name'] for f in folds]}  "
          f"candidate_days={len(days)} (..{end})")
    data = load_days(days, verbose=True)
    day_list = data["kept_days"]      # exact kept-day order; day_idx indexes into this

    spot64 = data["spot64"]; r = data["r"]; perp_y = data["perp_y"]
    di = data["day_idx"]; fam = data["fam"]; fam_names = data["fam_names"]
    basis = fam["basis"]

    # ---- per-family multivariate r-IC, perp-IC, block deltaP, orthogonality ----
    print("\n-- per-family Ridge (walk-forward pooled OOS) --")
    print(f"  {'family':9s} k  {'rIC_P':>7s} {'rIC_S':>7s} | {'perpIC_P':>8s} | "
          f"{'blkdP_perp':>10s} | {'orthdP_r(+basis)':>16s}  perfoldP(r)")
    base_perp = walkforward(spot64, perp_y, di, day_list, folds)        # SPOT64 on perp_y
    base_r_basis = walkforward(basis, r, di, day_list, folds)           # BASIS-only on r
    fam_res = {}
    for f in FAMILIES:
        Xf = fam[f]
        ric = walkforward(Xf, r, di, day_list, folds)
        pic = walkforward(Xf, perp_y, di, day_list, folds)
        blk = walkforward(np.concatenate([spot64, Xf], axis=1), perp_y, di, day_list, folds)
        dP_perp = blk["P"] - base_perp["P"]
        if f == "basis":
            orth = 0.0                                              # basis vs basis = 0
        else:
            comb = walkforward(np.concatenate([basis, Xf], axis=1), r, di, day_list, folds)
            orth = comb["P"] - base_r_basis["P"]
        fam_res[f] = dict(k=Xf.shape[1], rIC=ric, perpIC=pic,
                          blk_dP_perp=dP_perp, orth_dP_r=orth)
        print(f"  {f:9s} {Xf.shape[1]:2d} {ric['P']:+7.4f} {ric.get('S',float('nan')):+7.4f} | "
              f"{pic['P']:+8.4f} | {dP_perp:+10.4f} | {orth:+16.4f}  {ric['perfold_P']}")
    print(f"  {'[base]':9s}  SPOT64->perp_y P={base_perp['P']:+.4f}  "
          f"BASIS-only->r P={base_r_basis['P']:+.4f}")

    # ---- union (all rich) ----
    allX = np.concatenate([fam[f] for f in FAMILIES], axis=1)
    uni_r = walkforward(allX, r, di, day_list, folds)
    uni_perp = walkforward(allX, perp_y, di, day_list, folds)
    blk_union = walkforward(np.concatenate([spot64, allX], axis=1), perp_y, di, day_list, folds)
    orth_union = walkforward(np.concatenate([basis, allX], axis=1), r, di, day_list, folds)
    print(f"\n-- UNION (all rich, k={allX.shape[1]}) --")
    print(f"  r-IC  P={uni_r['P']:+.4f} S={uni_r.get('S',float('nan')):+.4f}  n={uni_r['n']}  perfold={uni_r['perfold_P']}")
    print(f"  perp-IC P={uni_perp['P']:+.4f}  | block dP over spot64 (perp_y) = {blk_union['P']-base_perp['P']:+.4f}")
    print(f"  orth dP over basis-alone (r) = {orth_union['P']-base_r_basis['P']:+.4f}  "
          f"(basis-only r-IC={base_r_basis['P']:+.4f} -> union+basis r-IC={orth_union['P']:+.4f})")

    # ---- univariate r-IC ranking + add-one-in top-12 over basis ----
    all_names = sum([fam_names[f] for f in FAMILIES], [])
    uni = []
    for j, nm in enumerate(all_names):
        pP, pS = _uni_ic(allX[:, j], r)
        pPy, _ = _uni_ic(allX[:, j], perp_y)
        uni.append((nm, pP, pS, pPy, j))
    uni_sorted = sorted(uni, key=lambda t: -abs(t[1]) if np.isfinite(t[1]) else 0)
    print("\n-- top-15 features by |univariate r-IC| (P_r / S_r / P_perp) --")
    for nm, pP, pS, pPy, j in uni_sorted[:15]:
        print(f"  {nm:28s} r:{pP:+.4f}/{pS:+.4f}  perp:{pPy:+.4f}")

    print("\n-- add-one-in: top-12 features each added to BASIS, delta r-IC --")
    addone = []
    for nm, pP, pS, pPy, j in uni_sorted[:12]:
        if nm in fam_names["basis"]:
            continue  # already in basis
        Xc = np.concatenate([basis, allX[:, [j]]], axis=1)
        rr = walkforward(Xc, r, di, day_list, folds)
        d = rr["P"] - base_r_basis["P"]
        addone.append((nm, round(d, 4), round(rr["P"], 4)))
        print(f"  +{nm:28s} basis+1 r-IC={rr['P']:+.4f}  dP={d:+.4f}")

    # ---- null band on union r-IC (permute target) ----
    null = _perm_null(allX, r, di, day_list, folds, n=200)
    print(f"\n-- y-permutation null band (97.5pct |r-IC|, union) = {null:.4f} -> "
          f"union r-IC |{uni_r['P']:.4f}| {'>' if abs(uni_r['P'])>null else '<='} band")

    out = dict(regime=name, n=int(uni_r["n"]),
               r_std=float(r.std()), r_var_frac=float(r.var()/max(perp_y.var(),1e-30)),
               base_perp_P=round(base_perp["P"], 4),
               base_r_basis_P=round(base_r_basis["P"], 4),
               families={f: dict(k=v["k"],
                                 rIC_P=round(v["rIC"]["P"], 4),
                                 rIC_S=round(v["rIC"].get("S", float("nan")), 4),
                                 perpIC_P=round(v["perpIC"]["P"], 4),
                                 blk_dP_perp=round(v["blk_dP_perp"], 4),
                                 orth_dP_r=round(v["orth_dP_r"], 4),
                                 perfold_P=v["rIC"]["perfold_P"])
                         for f, v in fam_res.items()},
               union=dict(k=int(allX.shape[1]),
                          rIC_P=round(uni_r["P"], 4), rIC_S=round(uni_r.get("S", float("nan")), 4),
                          perpIC_P=round(uni_perp["P"], 4),
                          blk_dP_perp=round(blk_union["P"] - base_perp["P"], 4),
                          orth_dP_r=round(orth_union["P"] - base_r_basis["P"], 4),
                          perfold_P=uni_r["perfold_P"]),
               top_uni=[dict(name=nm, rP=round(pP, 4), rS=round(pS, 4), perpP=round(pPy, 4))
                        for nm, pP, pS, pPy, j in uni_sorted[:15]],
               add_one_in=[dict(name=nm, dP=d, basis_plus1_rIC=rr) for nm, d, rr in addone],
               null_band_975=round(null, 4))

    if do_sentinel:
        ds = load_days(days, shift_basis_sec=600)
        base_unshift = walkforward(data["fam"]["basis"], data["r"], data["day_idx"], day_list, folds)
        shift = walkforward(ds["fam"]["basis"], ds["r"], ds["day_idx"], ds["kept_days"], folds)
        print(f"\n-- shift sentinel: basis->r unshifted P={base_unshift['P']:+.4f}  "
              f"+600s-shifted P={shift['P']:+.4f}  (shift must NOT exceed unshifted)")
        out["shift_sentinel"] = dict(unshifted=round(base_unshift["P"], 4),
                                     shifted_600s=round(shift["P"], 4))

    if json_out:
        json.dump({k: v for k, v in out.items()}, open(json_out, "w"), indent=2, default=float)
        print(f"\nsaved -> {json_out}")
    return out


def _perm_null(X, target, day_idx, day_list, folds, n=200, seed=0):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        tp = rng.permutation(target)
        r = walkforward(X, tp, day_idx, day_list, folds)
        if np.isfinite(r["P"]):
            vals.append(abs(r["P"]))
    return float(np.percentile(vals, 97.5)) if vals else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regime", choices=["strong", "choppy", "both"], default="both")
    ap.add_argument("--json_out", default=None)
    ap.add_argument("--no_sentinel", action="store_true")
    args = ap.parse_args()
    if args.regime in ("strong", "both"):
        run_regime("STRONG", STRONG_FOLDS,
                   json_out=(args.json_out and args.json_out.replace(".json", "_strong.json")),
                   do_sentinel=not args.no_sentinel)
    if args.regime in ("choppy", "both"):
        run_regime("CHOPPY", CHOPPY_FOLDS,
                   json_out=(args.json_out and args.json_out.replace(".json", "_choppy.json")),
                   do_sentinel=not args.no_sentinel)


if __name__ == "__main__":
    main()

"""DECISIVE Ridge gate: do basis / cross-venue factors carry the spot->perp
RESIDUAL ``r = perp_y_600 - spot_y_600``?  (leak-free, clean caliber)

WHY (the mechanism under test)
------------------------------
A spot-feature model transfers to the PERP target at only ~0.008 dense Pearson
(choppy) vs ~0.022 on the spot target, because the perp-minus-spot residual
``r = perp_y - spot_y`` (tiny, ~0.2-4% of perp variance) is NEGATIVELY correlated
with the spot model's q50 — the spot signal MIS-SIGNS the part of the perp move
that differs from spot. If basis/cross-venue factors predict ``r`` (Ridge IC
~0.2-0.3 claimed), feeding them lets a model recover that lost residual.

The prior gate (``/tmp/basis_gate.json``) only scored factors vs **perp_y**, where
the tiny basis signal is swamped by the 0.999-spot-correlated bulk (block ΔP came
out NEGATIVE). THIS gate scores vs **r** directly (and vs perp_y for contrast),
which is the correct target for the residual-recovery mechanism.

DATA (all leak-free, <= t)
--------------------------
  spot_last / perp_last (N,64)  : last-step (pred-index) features per venue
                                  (``data/lastts_cache``). perp pred-idx is at-or-
                                  before the spot second s (constant per-day shift
                                  <= 0), so perp - spot diffs are causal-safe.
  basis factors (4)             : ``data/basis_cache`` (basis_bps/z/mom/ema_dev),
                                  causal per-second, sampled at s.
  cross-venue diffs (computed here, at pred-index):
      ps_obi_diff_L5   = obi_L5^perp - obi_L5^spot           (ch 6)
      ps_microdev_diff = microprice_dev_bps^perp - ^spot     (ch 52)
      ps_cumflow_diff  = z(cumflow_30s^perp) - z(cumflow_30s^spot)   (ch 47)*
      spot_flow_lead   = z(net_trade_flow^spot) - z(^perp)          (ch 45)*
      perp_spot_vol_r  = log1p(RV60^perp/(RV60^spot+eps))    (ch 19)
      perp_spot_spr_r  = log1p(spread^perp/(spread^spot+eps))(ch 3)
   *z over the cross-sectional pool within each test fold (the per-window
    last-step has no intra-window axis at lastts caliber; the z removes the
    perp>>spot scale gap so the diff is a pressure-imbalance sign, not a scale).
  spot_y  = ``data/npz_spot`` y_600        (spot forward 10-min return)
  perp_y  = ``data/npz_spot2perp_clean`` y_600  (LEAK-FREE perp target)
  r       = perp_y - spot_y

CALIBER
-------
RAW y, MAD-σ standardize per fold, CLEAN subsample (stride >= 600s within each
day on time-sorted order) so labels are non-overlapping (anti-pattern #2). Per
regime: CHOPPY (2026 months on disk) and STRONG (2025-02; 2025-04 if covered).
Reports, per factor: univariate Pearson & Spearman vs r AND vs perp_y; plus the
multivariate Ridge ``r``-IC of {4 basis}, {6 cross-venue}, {all 10}, walk-forward.

Leak check: a y-permutation null band on the all-factor r-IC, and a basis +600s
SHIFT sentinel (shifting the basis series forward must NOT inflate r-IC; if it
does, the unshifted alignment was already peeking — it must not).

CLI
---
  python multi_asset/eda/perpY_basis_residual_gate.py --regime choppy --json_out /tmp/resid_gate.json
  python multi_asset/eda/perpY_basis_residual_gate.py --regime strong
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os.path as p
import sys

import numpy as np
from scipy.stats import pearsonr, spearmanr

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

LASTTS_DIR = p.join(_REPO, "data", "lastts_cache")
BASIS_DIR = p.join(_REPO, "data", "basis_cache")
SPOT_NPZ_DIR = p.join(_REPO, "data", "npz_spot")
PERP_CLEAN_DIR = p.join(_REPO, "data", "npz_spot2perp_clean")

HORIZON_S = 600
US = 1_000_000

# feature channel indices (identical 64-feature list for spot & perp)
CH = dict(spread_bps=3, obi_L5=6, rv60=19, cumflow_30s=47, microdev=52, netflow=45)
BASIS_NAMES = ["basis_bps", "basis_z", "basis_mom", "basis_ema_dev"]
XV_NAMES = ["ps_obi_diff_L5", "ps_microdev_diff", "ps_cumflow_diff",
            "spot_flow_lead", "perp_spot_vol_r", "perp_spot_spr_r"]

# regime day spans (test windows present on disk)
CHOPPY_MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]
STRONG_MONTHS = ["2025-02", "2025-04"]


# --------------------------------------------------------------------------- #
def _months_days(months):
    out = []
    for m in months:
        y, mo = map(int, m.split("-"))
        n = (dt.date(y + (mo == 12), (mo % 12) + 1, 1) - dt.date(y, mo, 1)).days
        out += ["%04d-%02d-%02d" % (y, mo, d) for d in range(1, n + 1)]
    return out


def _have(day):
    return all(p.exists(p.join(d, "%s.npz" % day))
               for d in (LASTTS_DIR, BASIS_DIR, SPOT_NPZ_DIR, PERP_CLEAN_DIR))


def _safe_log_ratio(num, den, eps=1e-9):
    r = np.asarray(num, np.float64) / (np.abs(np.asarray(den, np.float64)) + eps)
    return np.log1p(np.clip(r, 0.0, 1e4))


def _load_day(day, shift_basis_sec=0):
    """Return dict of pred-index arrays for one day: cross-venue diffs (raw, the
    flow z-scoring is done per-fold), basis 4, spot_y, perp_y, r, mask, ts.

    ``shift_basis_sec`` > 0 shifts the basis factors FORWARD by that many seconds
    (the leak sentinel: a forward shift must not help)."""
    zl = np.load(p.join(LASTTS_DIR, "%s.npz" % day), allow_pickle=True)
    spot = zl["spot_last"].astype(np.float64)        # (N,64)
    perp = zl["perp_last"].astype(np.float64)        # (N,64)
    ts = zl["timestamps"].astype(np.int64)           # spot pred ts (us)
    mask = zl["y_mask_600"].astype(bool)

    # cross-venue diffs (raw; cumflow/netflow left raw -> z per fold)
    ps_obi = perp[:, CH["obi_L5"]] - spot[:, CH["obi_L5"]]
    ps_micro = perp[:, CH["microdev"]] - spot[:, CH["microdev"]]
    ps_cumflow_raw_p = perp[:, CH["cumflow_30s"]]
    ps_cumflow_raw_s = spot[:, CH["cumflow_30s"]]
    netflow_p = perp[:, CH["netflow"]]
    netflow_s = spot[:, CH["netflow"]]
    vol_r = _safe_log_ratio(perp[:, CH["rv60"]], spot[:, CH["rv60"]])
    spr_r = _safe_log_ratio(perp[:, CH["spread_bps"]], spot[:, CH["spread_bps"]])

    # basis 4 (optionally forward-shifted for the sentinel)
    zb = np.load(p.join(BASIS_DIR, "%s.npz" % day), allow_pickle=True)
    bts = zb["timestamps"].astype(np.int64)
    F = zb["F"].astype(np.float64)                    # (Nb,4) cols=BASIS_NAMES
    # join basis -> lastts by timestamp (exact)
    if shift_basis_sec:
        key = ts + shift_basis_sec * US              # look basis up at t+shift
    else:
        key = ts
    j = np.searchsorted(bts, key, side="right") - 1
    okb = j >= 0
    jj = np.clip(j, 0, len(bts) - 1)
    basis = F[jj]                                     # (N,4)
    basis[~okb] = np.nan

    # spot_y, perp_y by exact-timestamp join
    zs = np.load(p.join(SPOT_NPZ_DIR, "%s.npz" % day), allow_pickle=True)
    sts = zs["timestamps"].astype(np.int64); sy = zs["y_600"].astype(np.float64)
    smask = zs["y_mask_600"].astype(bool)
    zc = np.load(p.join(PERP_CLEAN_DIR, "%s.npz" % day), allow_pickle=True)
    cts = zc["timestamps"].astype(np.int64); cy = zc["y_600"].astype(np.float64)
    cmask = zc["y_mask_600"].astype(bool)

    def _join(target_ts, target_y, target_m):
        idx = np.searchsorted(target_ts, ts)
        ok = (idx < len(target_ts)) & (target_ts[np.clip(idx, 0, len(target_ts) - 1)] == ts)
        y = np.full(len(ts), np.nan); m = np.zeros(len(ts), bool)
        y[ok] = target_y[idx[ok]]; m[ok] = target_m[idx[ok]]
        return y, m

    spot_y, sm = _join(sts, sy, smask)
    perp_y, cm = _join(cts, cy, cmask)
    r = perp_y - spot_y
    full_mask = mask & sm & cm & okb & np.isfinite(r)

    return dict(ts=ts, mask=full_mask,
                ps_obi=ps_obi, ps_micro=ps_micro,
                cumflow_p=ps_cumflow_raw_p, cumflow_s=ps_cumflow_raw_s,
                netflow_p=netflow_p, netflow_s=netflow_s,
                vol_r=vol_r, spr_r=spr_r,
                basis=basis, spot_y=spot_y, perp_y=perp_y, r=r)


def _clean_idx(ts):
    """Indices keeping labels >= HORIZON_S apart on time-sorted order."""
    order = np.argsort(ts, kind="stable")
    d = np.diff(np.sort(ts)); d = d[d > 0]
    gap = float(np.median(d)) / US if d.size else 1.0
    factor = max(1, int(np.ceil(HORIZON_S / max(gap, 1e-9))))
    return order[::factor]


def load_regime(days, shift_basis_sec=0):
    rows = []
    for day in days:
        if not _have(day):
            continue
        d = _load_day(day, shift_basis_sec=shift_basis_sec)
        keep = d["mask"].copy()
        # clean subsample within the day on its own grid
        ci = _clean_idx(d["ts"])
        cmask = np.zeros(len(d["ts"]), bool); cmask[ci] = True
        keep &= cmask
        if keep.sum() == 0:
            continue
        rows.append({k: (v[keep] if isinstance(v, np.ndarray) and v.shape[:1] == d["ts"].shape
                         else v) for k, v in d.items()})
    if not rows:
        raise RuntimeError("no usable days for regime")
    out = {}
    for k in rows[0]:
        if k == "basis":
            out[k] = np.concatenate([r[k] for r in rows], axis=0)
        else:
            out[k] = np.concatenate([np.atleast_1d(r[k]) for r in rows], axis=0)
    return out


def _z(a):
    a = np.asarray(a, np.float64)
    s = a.std()
    return (a - a.mean()) / (s + 1e-12) if s > 1e-12 else a * 0.0


def _factor_matrix(R):
    """Build the candidate factor matrix (N, 10): 4 basis + 6 cross-venue. Flow
    diffs are z-scored over the pool here (scale removal). Returns (names, X)."""
    cumflow_diff = _z(R["cumflow_p"]) - _z(R["cumflow_s"])
    spot_lead = _z(R["netflow_s"]) - _z(R["netflow_p"])
    cols = {
        "basis_bps": R["basis"][:, 0], "basis_z": R["basis"][:, 1],
        "basis_mom": R["basis"][:, 2], "basis_ema_dev": R["basis"][:, 3],
        "ps_obi_diff_L5": R["ps_obi"], "ps_microdev_diff": R["ps_micro"],
        "ps_cumflow_diff": cumflow_diff, "spot_flow_lead": spot_lead,
        "perp_spot_vol_r": R["vol_r"], "perp_spot_spr_r": R["spr_r"],
    }
    names = BASIS_NAMES + XV_NAMES
    X = np.column_stack([cols[n] for n in names])
    return names, X


def _ic(x, y):
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 50 or x[m].std() == 0 or y[m].std() == 0:
        return dict(P=float("nan"), S=float("nan"), n=int(m.sum()))
    return dict(P=round(float(pearsonr(x[m], y[m])[0]), 4),
                S=round(float(spearmanr(x[m], y[m]).correlation), 4),
                n=int(m.sum()))


def _ridge_ic_cv(X, y, n_folds=4, lam=10.0):
    """Time-split walk-forward Ridge; pooled OOS Pearson of yhat vs y (the
    multivariate r-IC). MAD-σ standardize y per fold; standardize X on train."""
    N = len(y)
    m = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    X, y = X[m], y[m]
    N = len(y)
    if N < 200:
        return dict(P=float("nan"), n=N)
    bnds = np.linspace(0, N, n_folds + 1).astype(int)
    yh_all, y_all = [], []
    for f in range(1, n_folds):
        tr = slice(0, bnds[f]); te = slice(bnds[f], bnds[f + 1])
        Xtr, ytr = X[tr], y[tr]; Xte, yte = X[te], y[te]
        if len(yte) < 30 or len(ytr) < 100:
            continue
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
        Xtr = (Xtr - mu) / sd; Xte = (Xte - mu) / sd
        ymu = np.median(ytr); ysd = np.median(np.abs(ytr - ymu)) * 1.4826 + 1e-12
        ytr_n = (ytr - ymu) / ysd
        A = Xtr.T @ Xtr + lam * np.eye(Xtr.shape[1])
        w = np.linalg.solve(A, Xtr.T @ ytr_n)
        yh = Xte @ w
        yh_all.append(yh); y_all.append((yte - ymu) / ysd)
    if not yh_all:
        return dict(P=float("nan"), n=N)
    yh = np.concatenate(yh_all); yy = np.concatenate(y_all)
    if yh.std() == 0:
        return dict(P=0.0, n=len(yy))
    return dict(P=round(float(pearsonr(yh, yy)[0]), 4),
                S=round(float(spearmanr(yh, yy).correlation), 4), n=len(yy))


def _perm_null(X, y, n=400, seed=0, **kw):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        yp = rng.permutation(y)
        r = _ridge_ic_cv(X, yp, **kw)
        if np.isfinite(r["P"]):
            vals.append(abs(r["P"]))
    return float(np.percentile(vals, 97.5)) if vals else float("nan")


def run_regime(name, months, json_out=None):
    days = [d for d in _months_days(months) if _have(d)]
    print("\n%s  regime=%s  usable_days=%d" % ("=" * 70, name, len(days)))
    R = load_regime(days)
    names, X = _factor_matrix(R)
    r = R["r"]; perp_y = R["perp_y"]; spot_y = R["spot_y"]
    print("N(clean,masked)=%d  std(r)=%.3e  std(perp_y)=%.3e  r_var/perp_var=%.4f  "
          "corr(spot_y,perp_y)=%.4f"
          % (len(r), r.std(), perp_y.std(), r.var() / max(perp_y.var(), 1e-30),
             np.corrcoef(spot_y, perp_y)[0, 1]))

    print("\n-- univariate IC of each factor vs RESIDUAL r  AND vs perp_y --")
    print("  %-18s | %18s | %18s" % ("factor", "vs r (P/S)", "vs perp_y (P/S)"))
    uni = {}
    for i, nm in enumerate(names):
        ir = _ic(X[:, i], r); iy = _ic(X[:, i], perp_y)
        uni[nm] = dict(vs_r=ir, vs_perp_y=iy)
        print("  %-18s | %+7.4f / %+7.4f | %+7.4f / %+7.4f  (n=%d)"
              % (nm, ir["P"], ir["S"], iy["P"], iy["S"], ir["n"]))

    print("\n-- multivariate Ridge r-IC (walk-forward, pooled OOS) --")
    grp = {"basis4": list(range(4)), "xvenue6": list(range(4, 10)),
           "all10": list(range(10))}
    multi = {}
    for g, idx in grp.items():
        rr = _ridge_ic_cv(X[:, idx], r)
        ry = _ridge_ic_cv(X[:, idx], perp_y)
        multi[g] = dict(vs_r=rr, vs_perp_y=ry)
        print("  %-8s vs r: P=%+.4f S=%+.4f n=%d   | vs perp_y: P=%+.4f"
              % (g, rr["P"], rr.get("S", float("nan")), rr["n"], ry["P"]))

    # leak guards on all10 vs r
    null = _perm_null(X, r, n=300)
    all_r = multi["all10"]["vs_r"]["P"]
    print("\n-- leakage: y-permutation null band (97.5pct |r-IC|) = %.4f -> all10 |r-IC|=%.4f %s"
          % (null, abs(all_r), ">" if abs(all_r) > null else "<="))

    # +600s basis shift sentinel
    Rs = load_regime(days, shift_basis_sec=600)
    _, Xs = _factor_matrix(Rs)
    shifted = _ridge_ic_cv(Xs[:, :4], Rs["r"])   # basis4 shifted
    base = _ridge_ic_cv(X[:, :4], r)
    print("-- shift sentinel: basis4 r-IC unshifted P=%+.4f  +600s-shifted P=%+.4f "
          "(shift must NOT exceed unshifted)" % (base["P"], shifted["P"]))

    out = dict(regime=name, n=len(r), r_std=float(r.std()),
               r_var_frac=float(r.var() / max(perp_y.var(), 1e-30)),
               univariate=uni, multivariate=multi,
               null_band_975=round(null, 4),
               all10_r_ic_above_null=bool(abs(all_r) > null),
               shift_sentinel=dict(unshifted=base["P"], shifted_600s=shifted["P"]))
    if json_out:
        json.dump(out, open(json_out, "w"), indent=2, default=float)
        print("\nsaved -> %s" % json_out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regime", choices=["choppy", "strong", "both"], default="choppy")
    ap.add_argument("--json_out", default=None)
    args = ap.parse_args()
    res = {}
    if args.regime in ("choppy", "both"):
        res["choppy"] = run_regime("CHOPPY", CHOPPY_MONTHS,
                                   json_out=(args.json_out and args.json_out.replace(".json", "_choppy.json")))
    if args.regime in ("strong", "both"):
        res["strong"] = run_regime("STRONG", STRONG_MONTHS,
                                   json_out=(args.json_out and args.json_out.replace(".json", "_strong.json")))


if __name__ == "__main__":
    main()

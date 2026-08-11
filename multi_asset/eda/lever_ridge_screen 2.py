"""RIDGE lever screen — perp y_600, leak-free walk-forward, ΔP vs baseline.

> created 2026-06-22 | status: screening | branch: multi-asset

Reuses perpY_ridge_gate machinery (MAD-z norm, λ-on-val, ::4 subsample, RAW y,
1-day embargo, per-fold sign-consistency) to screen every analyzed LEVER as a
last-timestep feature-matrix slice -> Ridge -> per-fold + pooled Pearson, in
SECONDS-to-MINUTES (not the 2h DL runs). DL validates only the Ridge winners.

LEVERS (all -> perp y_600; baseline = spot book + spot trades):
  base            npz_spot X (64)                       spot book + spot trades
  perp_trades     48 spot-book cols + 16 perp-trade cols (npz_perp trade cols)
  perp_book       48 perp-book cols + 16 spot-trade cols (npz_perp book cols)
  dual            npz_perp X (64)                        perp book + perp trades
  bs_bookshape    base 64 + BS book-shape change feats (append, last-t)
  cross_venue     base 64 + cross-venue relative ratios (append, last-t)
  long_context    base 64 + 60s-pooled 4h summary (append, flattened summary)

Each lever's X is built positionally-joined to perp y exactly like the gate's
_load_day (spot/perp constant-shift join). Folds: strong_2025_02, strong_2025_04,
choppy_2026 (the gate's FOLDS). Reports per-fold P + ΔP vs base + sign-consistency.

Usage:
  python multi_asset/eda/lever_ridge_screen.py --levers base perp_trades perp_book dual
  python multi_asset/eda/lever_ridge_screen.py --all
"""
from __future__ import annotations

import argparse
import glob
import os.path as p
import sys

import numpy as np

_REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, _REPO)

from multi_asset.eda.perpY_ridge_gate import (   # noqa: E402
    ridge_walkforward, SUBSAMPLE, SHIFT_TOL_US,
)

DATA = p.join(_REPO, "data")
SPOT = p.join(DATA, "npz_spot")
PERP = p.join(DATA, "npz_perp")
MID = p.join(DATA, "mid_cache")

# the 16 trade/volume features (perp-vs-spot divergent); rest (48) are book/price
TRADE_FEATS = ["buy_volume_1s", "sell_volume_1s", "net_trade_flow_1s",
               "trade_imbalance_1s", "cumulative_net_flow_30s",
               "cumulative_net_flow_300s", "trade_intensity_30s", "vwap_return_1s",
               "kyle_lambda_30s", "vpin_60s", "vpin_300s", "price_impact_30s",
               "net_flow_x_spread", "net_flow_x_vol", "net_flow_rank_1h",
               "large_trade_arrival_60s"]

US = 1_000_000


def _all_days():
    s = {p.basename(f)[:-4] for f in glob.glob(p.join(SPOT, "*.npz"))}
    q = {p.basename(f)[:-4] for f in glob.glob(p.join(PERP, "*.npz"))
         if p.basename(f)[0].isdigit()}
    return sorted(s & q)


# ---- per-day extra-feature builders (last-timestep, causal <= t) -------------
def _bs_lastt(zs, zp, names):
    """BS book-shape: last-t levels of perp book-shape primitives + cross-venue
    obi/mpdev diff (the BS family's LEVEL proxies; Ridge can't see Δ-over-time
    without a sequence, so use the perp last-t shape + cross diff as the screenable
    surrogate). Returns (N, k)."""
    fi = {n: i for i, n in enumerate(names)}
    cols = ["bid_concentration", "ask_concentration", "microprice_dev_bps",
            "bid_slope_L10", "ask_slope_L10", "book_pressure_imbalance"]
    Xp = zp["X"][:, -1, :].astype(np.float64)
    Xs = zs["X"][:, -1, :].astype(np.float64)
    out = [Xp[:, fi[c]] for c in cols]
    out.append(Xp[:, fi["obi_L5"]] - Xs[:, fi["obi_L5"]])           # cross obi diff
    out.append(Xp[:, fi["microprice_dev_bps"]] - Xs[:, fi["microprice_dev_bps"]])
    return np.column_stack(out)


def _cross_lastt(zs, zp, names):
    """Cross-venue relative: spread ratio, depth ratio, obi diff, mpdev diff,
    rvol(30s) ratio — last-t, from the two venues' 64-feat snapshots."""
    fi = {n: i for i, n in enumerate(names)}
    Xs = zs["X"][:, -1, :].astype(np.float64)
    Xp = zp["X"][:, -1, :].astype(np.float64)
    eps = 1e-9
    sd = Xs[:, fi["bid_depth_L25"]] + Xs[:, fi["ask_depth_L25"]]
    pdp = Xp[:, fi["bid_depth_L25"]] + Xp[:, fi["ask_depth_L25"]]
    out = [
        np.log((np.abs(Xp[:, fi["spread_bps"]]) + 1.0) / (np.abs(Xs[:, fi["spread_bps"]]) + 1.0)),
        np.log((np.abs(pdp) + eps) / (np.abs(sd) + eps)),
        Xp[:, fi["obi_L5"]] - Xs[:, fi["obi_L5"]],
        Xp[:, fi["microprice_dev_bps"]] - Xs[:, fi["microprice_dev_bps"]],
        np.log((np.abs(Xp[:, fi["realized_vol_30s"]]) + eps) / (np.abs(Xs[:, fi["realized_vol_30s"]]) + eps)),
    ]
    return np.column_stack(out)


def _long_lastt(day, zs, n_rows, idx_full):
    """Long-context 60s-pooled summary at each window's pred second, from
    mid_cache: trailing {600s,1800s,3600s} perp/spot return, rvol, basis. Causal.
    Returns (N, k) aligned to the spot windows' pred timestamps."""
    fmid = p.join(MID, f"{day}.npz")
    if not p.exists(fmid):
        return None
    zm = np.load(fmid)
    sec = zm["sec"].astype(np.int64)
    sm = zm["spot_mid"].astype(np.float64); pm = zm["perp_mid"].astype(np.float64)
    lsm = np.log(np.clip(sm, 1e-9, None)); lpm = np.log(np.clip(pm, 1e-9, None))
    sret = np.zeros_like(lsm); sret[1:] = np.diff(lsm)
    pret = np.zeros_like(lpm); pret[1:] = np.diff(lpm)
    basis = np.clip((pm - sm) / np.where(sm > 0, sm, 1.0) * 1e4, -50, 50)

    def cumsum_pref(a):
        return np.concatenate([[0.0], np.cumsum(a)])
    cs_s = cumsum_pref(sret); cs_p = cumsum_pref(pret)
    cs_s2 = cumsum_pref(sret * sret); cs_p2 = cumsum_pref(pret * pret)

    pred_sec = (zs["timestamps"].astype(np.int64) // US)
    # map each pred second to its position on the mid grid (<= t)
    pos = np.searchsorted(sec, pred_sec, side="right") - 1
    ok = pos >= 0
    feats = []
    for W in (600, 1800, 3600):
        lo = np.clip(pos - W, 0, None)
        n = (pos - lo).astype(np.float64); n[n < 1] = 1.0
        sret_w = (cs_s[pos + 1] - cs_s[lo]) if True else None
        # guard index
        pidx = np.clip(pos + 1, 0, sec.size)
        sret_w = cs_s[pidx] - cs_s[lo]
        pret_w = cs_p[pidx] - cs_p[lo]
        srv = np.sqrt(np.clip((cs_s2[pidx] - cs_s2[lo]) / n - (sret_w / n) ** 2, 0, None))
        prv = np.sqrt(np.clip((cs_p2[pidx] - cs_p2[lo]) / n - (pret_w / n) ** 2, 0, None))
        feats += [np.clip(sret_w, -0.05, 0.05), np.clip(pret_w, -0.05, 0.05), srv, prv]
    feats.append(basis[np.clip(pos, 0, sec.size - 1)])
    M = np.column_stack(feats)
    M[~ok] = 0.0
    # restrict to the masked+subsampled rows used by the gate (idx_full)
    return M[idx_full]


# ---- per-lever loader (positional spot/perp join, like the gate) ------------
def load_lever(lever, verbose=False):
    days = _all_days()
    Xs_l, ys_l, di, mo = [], [], [], []
    names_ref = None
    for k, day in enumerate(days):
        fs = p.join(SPOT, f"{day}.npz"); fp = p.join(PERP, f"{day}.npz")
        zs = np.load(fs, allow_pickle=True); zp = np.load(fp, allow_pickle=True)
        sts = zs["timestamps"].astype(np.int64); pts = zp["timestamps"].astype(np.int64)
        if sts.shape != pts.shape:
            continue
        diff = pts - sts
        if diff.size == 0 or not np.all(diff == diff[0]) or abs(int(diff[0])) > SHIFT_TOL_US:
            continue
        names = [str(x) for x in zs["features"]]
        if names_ref is None:
            names_ref = names
        fi = {n: i for i, n in enumerate(names)}
        Xs = zs["X"][:, -1, :].astype(np.float64)     # (N,64) spot last-t
        Xp = zp["X"][:, -1, :].astype(np.float64)     # (N,64) perp last-t
        yperp = zp["y_600"].astype(np.float64)
        mask = zs["y_mask_600"].astype(bool)

        # compose X per lever
        if lever == "base":
            X = Xs
        elif lever == "dual":
            X = Xp
        elif lever == "perp_trades":          # spot book (48) + perp trades (16)
            X = Xs.copy()
            for nm in TRADE_FEATS:
                X[:, fi[nm]] = Xp[:, fi[nm]]
        elif lever == "perp_book":            # perp book (48) + spot trades (16)
            X = Xp.copy()
            for nm in TRADE_FEATS:
                X[:, fi[nm]] = Xs[:, fi[nm]]
        elif lever == "bs_bookshape":
            X = np.column_stack([Xs, _bs_lastt(zs, zp, names)])
        elif lever == "cross_venue":
            X = np.column_stack([Xs, _cross_lastt(zs, zp, names)])
        elif lever == "long_context":
            X = Xs   # extra appended after mask (needs idx) -> handled below
        else:
            raise ValueError(lever)

        keep = mask.copy()
        keep[~np.isfinite(yperp)] = False
        keep &= np.all(np.isfinite(X), axis=1)
        idx = np.where(keep)[0][::SUBSAMPLE]
        if idx.size == 0:
            continue
        Xk = X[idx]
        if lever == "long_context":
            extra = _long_lastt(day, zs, len(mask), idx)
            if extra is None:
                continue
            Xk = np.column_stack([Xk, extra])
            fin = np.all(np.isfinite(Xk), axis=1)
            Xk = Xk[fin]; idx = idx[fin]
            if idx.size == 0:
                continue
        Xs_l.append(Xk)
        ys_l.append(yperp[idx])
        di.append(np.full(idx.size, k, dtype=np.int32))
        mo.append(np.array([day[:7]] * idx.size))
    X = np.concatenate(Xs_l); y = np.concatenate(ys_l)
    day_idx = np.concatenate(di); month = np.concatenate(mo)
    if verbose:
        print(f"[{lever}] M={X.shape[0]} D={X.shape[1]}", flush=True)
    return X, y, day_idx, month, days


_RAWCACHE = p.join("/tmp", "lever_raw_cache.npz")


def build_raw_cache():
    """Load ONCE: spot last-t 64, perp last-t 64, perp y, day_idx, + the extra
    last-t feature blocks (bs, cross, long), all positionally joined + masked +
    ::4. Cache to /tmp so every lever composes in-memory (no re-read). The
    expensive npz reads happen exactly once here."""
    days = _all_days()
    Xs_l, Xp_l, y_l, di, mo = [], [], [], [], []
    bs_l, cr_l, lg_l = [], [], []
    names_ref = None
    for k, day in enumerate(days):
        fs = p.join(SPOT, f"{day}.npz"); fp = p.join(PERP, f"{day}.npz")
        zs = np.load(fs, allow_pickle=True); zp = np.load(fp, allow_pickle=True)
        sts = zs["timestamps"].astype(np.int64); pts = zp["timestamps"].astype(np.int64)
        if sts.shape != pts.shape:
            continue
        diff = pts - sts
        if diff.size == 0 or not np.all(diff == diff[0]) or abs(int(diff[0])) > SHIFT_TOL_US:
            continue
        names = [str(x) for x in zs["features"]]
        names_ref = names
        Xs = zs["X"][:, -1, :].astype(np.float64)
        Xp = zp["X"][:, -1, :].astype(np.float64)
        yperp = zp["y_600"].astype(np.float64)
        mask = zs["y_mask_600"].astype(bool)
        keep = mask.copy()
        keep[~np.isfinite(yperp)] = False
        keep &= np.all(np.isfinite(Xs), axis=1) & np.all(np.isfinite(Xp), axis=1)
        idx = np.where(keep)[0][::SUBSAMPLE]
        if idx.size == 0:
            continue
        bs = _bs_lastt(zs, zp, names)[idx]
        cr = _cross_lastt(zs, zp, names)[idx]
        lg = _long_lastt(day, zs, len(mask), idx)
        if lg is None:
            lg = np.full((idx.size, 13), np.nan)        # long unavailable this day
        Xs_l.append(Xs[idx]); Xp_l.append(Xp[idx]); y_l.append(yperp[idx])
        bs_l.append(bs); cr_l.append(cr); lg_l.append(lg)
        di.append(np.full(idx.size, k, dtype=np.int32))
        mo.append(np.array([day[:7]] * idx.size))
    np.savez(_RAWCACHE,
             Xs=np.concatenate(Xs_l), Xp=np.concatenate(Xp_l),
             y=np.concatenate(y_l), bs=np.concatenate(bs_l),
             cr=np.concatenate(cr_l), lg=np.concatenate(lg_l),
             day_idx=np.concatenate(di), month=np.concatenate(mo),
             days=np.array(days, dtype=object), names=np.array(names_ref, dtype=object))
    print(f"[raw_cache] built -> {_RAWCACHE}  M={np.concatenate(y_l).shape[0]}", flush=True)


def _compose(lev, R):
    Xs = R["Xs"]; Xp = R["Xp"]; names = [str(x) for x in R["names"]]
    fi = {n: i for i, n in enumerate(names)}
    if lev == "base":
        return Xs
    if lev == "dual":
        return Xp
    if lev == "perp_trades":
        X = Xs.copy()
        for nm in TRADE_FEATS:
            X[:, fi[nm]] = Xp[:, fi[nm]]
        return X
    if lev == "perp_book":
        X = Xp.copy()
        for nm in TRADE_FEATS:
            X[:, fi[nm]] = Xs[:, fi[nm]]
        return X
    if lev == "bs_bookshape":
        return np.column_stack([Xs, R["bs"]])
    if lev == "cross_venue":
        return np.column_stack([Xs, R["cr"]])
    if lev == "long_context":
        return np.column_stack([Xs, R["lg"]])
    raise ValueError(lev)


def screen_fast(levers):
    if not p.exists(_RAWCACHE):
        build_raw_cache()
    R = np.load(_RAWCACHE, allow_pickle=True)
    days = list(R["days"]); day_idx = R["day_idx"]
    results = {}
    for lev in levers:
        X = _compose(lev, R); y = R["y"]
        # drop rows with non-finite in composed X (long_context has NaN days)
        fin = np.all(np.isfinite(X), axis=1)
        Xf, yf, dif = X[fin], y[fin], day_idx[fin]
        r = ridge_walkforward(Xf, yf, dif, days, verbose=False)
        results[lev] = r
        pooled = r["pooled"]
        pf = {f["name"]: f.get("P") for f in r["folds"] if f.get("status") == "ok"}
        print(f"\n=== LEVER {lev} (D={X.shape[1]}, M={int(fin.sum())}) ===", flush=True)
        if pooled:
            print(f"  pooled P={pooled['P']} S={pooled['S']} beta={pooled['beta']} "
                  f"sig={pooled['sig_ratio']} sign_consistent={pooled['sign_consistent']}",
                  flush=True)
            print(f"  per-fold: 2025-02={pf.get('strong_2025_02')} "
                  f"2025-04={pf.get('strong_2025_04')} 2026={pf.get('choppy_2026')}",
                  flush=True)
        for f in r["folds"]:
            if f.get("status") == "ok":
                print(f"    {f['name']}: P={f['P']} beta={f['beta']} sig={f['sig_ratio']} "
                      f"lam={f['best_lam']} n_te={f['n_test']}", flush=True)
            else:
                print(f"    {f['name']}: {f['status']}", flush=True)
    return results


def screen(levers):
    results = {}
    for lev in levers:
        X, y, day_idx, month, days = load_lever(lev, verbose=True)
        r = ridge_walkforward(X, y, day_idx, days, verbose=False)
        results[lev] = r
        pooled = r["pooled"]
        pf = {f["name"]: f.get("P") for f in r["folds"] if f.get("status") == "ok"}
        print(f"\n=== LEVER {lev} (D={X.shape[1]}) ===", flush=True)
        if pooled:
            print(f"  pooled P={pooled['P']} S={pooled['S']} beta={pooled['beta']} "
                  f"sig={pooled['sig_ratio']} sign_consistent={pooled['sign_consistent']}",
                  flush=True)
            print(f"  per-fold P: {pooled['perfold_P']}  "
                  f"(2025-02={pf.get('strong_2025_02')} 2025-04={pf.get('strong_2025_04')} "
                  f"2026={pf.get('choppy_2026')})", flush=True)
        for f in r["folds"]:
            if f.get("status") == "ok":
                print(f"    {f['name']}: P={f['P']} S={f['S']} beta={f['beta']} "
                      f"sig={f['sig_ratio']} lam={f['best_lam']} n_te={f['n_test']}",
                      flush=True)
            else:
                print(f"    {f['name']}: {f['status']}", flush=True)
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--levers", nargs="+", default=None)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    ALL = ["base", "perp_trades", "perp_book", "dual", "bs_bookshape",
           "cross_venue", "long_context"]
    levers = ALL if args.all else (args.levers or ["base"])
    screen_fast(levers)

"""Build the REAL basis factors (perp_mid - spot_mid), strictly causal (<= t).

Stage C real-basis, step 2. Consumes ``data/mid_cache/<day>.npz`` (absolute spot
& perp mids on a 1s grid) and produces, per UTC day, the 4 basis factors sampled
at each window's PREDICTION timestamp (taken from ``data/lastts_cache/<day>.npz``)::

    data/basis_cache/<YYYY-MM-DD>.npz
        timestamps   int64   (N,)   = lastts prediction timestamps (us), verbatim
        basis_bps    float64 (N,)   (perp_mid - spot_mid)/spot_mid * 1e4, clip +-50
        basis_z      float64 (N,)   (basis_bps - causal rollmean_30m)/(rollstd_30m+eps)
        basis_mom    float64 (N,)   basis_bps(t) - basis_bps(t-300s)
        basis_ema_dev float64(N,)   basis_bps(t) - causal EMA(basis_bps, span~60s)
        F            float64 (N,4)  [basis_bps, basis_z, basis_mom, basis_ema_dev]

FACTOR DEFINITIONS (mechanism)
------------------------------
The basis (perp rich/cheap vs spot) is an orthogonal driver of the *perp*
forward return: a high positive basis means perp is rich and tends to revert
DOWN (negative perp y_600), a deeply negative basis the reverse. We expose the
level, its standardized deviation, its short momentum, and its fast-EMA
deviation:

  basis_bps     : the level itself (clipped +-50 bps to kill print/cross glitches).
  basis_z       : level standardized by a causal 30-min rolling mean/std -> "how
                  unusual is the basis right now" (mean-reversion signal).
  basis_mom     : 5-min change of the basis -> is the dislocation widening?
  basis_ema_dev : level minus a fast (~60s) causal EMA -> micro mean-reversion.

STRICT CAUSALITY (<= t)
-----------------------
Everything is computed on the per-SECOND mid series, then sampled at each
prediction second t = floor(pred_ts_us / 1e6). All rolling/EMA statistics are
``shift(1)`` BEFORE being combined so the statistic used at second t excludes
second t's own value (uses only seconds < t); the level basis_bps(t) itself is a
<=t quantity. basis_mom uses basis_bps at t and at (t-300s) — both <= t. No
statistic ever touches a second > t. (Verified by the shuffle-future null in the
gate: corrupting mids strictly after t leaves every <=t window byte-identical.)

CLI
---
  python multi_asset/data/build_basis_factors.py --days 2025-02-10 2025-02-11
  python multi_asset/data/build_basis_factors.py --all          # skip existing
"""
from __future__ import annotations

import argparse
import os
import os.path as p
import sys
import time

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))

MID_DIR = p.join(_REPO, "data", "mid_cache")
LASTTS_DIR = p.join(_REPO, "data", "lastts_cache")
OUT_DIR = p.join(_REPO, "data", "basis_cache")

US_PER_SEC = 1_000_000
CLIP_BPS = 50.0
ROLL_WIN_SEC = 30 * 60      # 30-min causal rolling window for basis_z
EMA_SPAN_SEC = 60           # ~60s fast EMA for basis_ema_dev
MOM_LAG_SEC = 300           # 5-min momentum lag
EPS = 1e-6

FACTOR_NAMES = ["basis_bps", "basis_z", "basis_mom", "basis_ema_dev"]


# ---------------------------------------------------------------------------
# causal rolling helpers (operate on a per-second, contiguous-in-value array)
# ---------------------------------------------------------------------------
def _causal_rollmean_std(x, win):
    """Trailing rolling mean & std of x over `win` samples, SHIFTED by 1 so the
    value at index i uses only x[i-win .. i-1] (strictly < i). Min 2 obs, else
    NaN. Pure cumulative-sum O(T)."""
    x = np.asarray(x, dtype=np.float64)
    T = x.size
    xs = np.concatenate([[0.0], np.cumsum(x)])              # prefix sums, len T+1
    xs2 = np.concatenate([[0.0], np.cumsum(x * x)])
    out_m = np.full(T, np.nan)
    out_s = np.full(T, np.nan)
    # at index i, window is [lo, i-1] inclusive (strictly < i) -> shift(1) baked in
    i = np.arange(T)
    hi = i                       # exclusive upper = i  -> covers up to i-1
    lo = np.maximum(0, i - win)
    cnt = (hi - lo).astype(np.float64)
    valid = cnt >= 2
    s1 = xs[hi] - xs[lo]
    s2 = xs2[hi] - xs2[lo]
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s1 / cnt
        var = s2 / cnt - mean * mean
        var = np.where(var < 0, 0.0, var)
        std = np.sqrt(var)
    out_m[valid] = mean[valid]
    out_s[valid] = std[valid]
    return out_m, out_s


def _causal_ema_shift1(x, span):
    """EMA(x, span) then SHIFT by 1 (the EMA used at i is the EMA through i-1).
    alpha = 2/(span+1). First value (no past) -> NaN."""
    x = np.asarray(x, dtype=np.float64)
    T = x.size
    alpha = 2.0 / (span + 1.0)
    ema = np.empty(T, dtype=np.float64)
    ema[0] = x[0]
    for i in range(1, T):
        ema[i] = alpha * x[i] + (1.0 - alpha) * ema[i - 1]
    out = np.full(T, np.nan)
    out[1:] = ema[:-1]          # shift(1): value at i is EMA through i-1
    return out


# ---------------------------------------------------------------------------
# core: per-second basis series + sampling at prediction seconds (pure, tested)
# ---------------------------------------------------------------------------
def per_second_factors(sec, spot_mid, perp_mid):
    """Compute the 4 basis factors on the full per-second grid.

    Returns dict name -> array(T,). All causal (<= that second). `sec` is the
    contiguous (per build_mid_cache) unix-second grid; spot/perp are absolute
    mids. basis_mom looks back exactly MOM_LAG_SEC seconds via the second index
    (uses the grid, not positional, so gaps don't shorten the lag)."""
    sec = np.asarray(sec, dtype=np.int64)
    spot_mid = np.asarray(spot_mid, dtype=np.float64)
    perp_mid = np.asarray(perp_mid, dtype=np.float64)

    basis_bps = (perp_mid - spot_mid) / spot_mid * 1e4
    basis_bps = np.clip(basis_bps, -CLIP_BPS, CLIP_BPS)

    rmean, rstd = _causal_rollmean_std(basis_bps, ROLL_WIN_SEC)
    basis_z = (basis_bps - rmean) / (rstd + EPS)

    ema_s1 = _causal_ema_shift1(basis_bps, EMA_SPAN_SEC)
    basis_ema_dev = basis_bps - ema_s1

    # 5-min momentum: basis_bps(t) - basis_bps(t-300s), aligned on the SECOND
    # index so a non-contiguous grid still subtracts the value 300s earlier.
    lag_sec = sec - MOM_LAG_SEC
    pos = np.searchsorted(sec, lag_sec, side="left")
    exact = (pos < sec.size) & (sec[np.minimum(pos, sec.size - 1)] == lag_sec)
    basis_mom = np.full(sec.size, np.nan)
    basis_mom[exact] = basis_bps[exact] - basis_bps[pos[exact]]

    return {
        "basis_bps": basis_bps,
        "basis_z": basis_z,
        "basis_mom": basis_mom,
        "basis_ema_dev": basis_ema_dev,
    }


def sample_at_pred_secs(sec, factors, pred_secs):
    """Sample each per-second factor at prediction seconds via <= t lookup
    (searchsorted side='right' - 1). A pred_sec before the first grid second ->
    NaN row. Returns dict name -> array(N,)."""
    sec = np.asarray(sec, dtype=np.int64)
    pred_secs = np.asarray(pred_secs, dtype=np.int64)
    j = np.searchsorted(sec, pred_secs, side="right") - 1
    valid = j >= 0
    jj = np.clip(j, 0, sec.size - 1)
    out = {}
    for name, arr in factors.items():
        v = arr[jj].astype(np.float64)
        v[~valid] = np.nan
        out[name] = v
    return out


def build_factors_for_day(date_str):
    """Load mid_cache + lastts for one day, return (timestamps_us, F (N,4), parts).

    timestamps are the lastts prediction timestamps (us), verbatim. F columns are
    FACTOR_NAMES in order. parts is the dict of individual factor arrays."""
    midf = p.join(MID_DIR, "%s.npz" % date_str)
    lastf = p.join(LASTTS_DIR, "%s.npz" % date_str)
    if not p.exists(midf):
        raise FileNotFoundError("mid_cache missing: %s" % midf)
    if not p.exists(lastf):
        raise FileNotFoundError("lastts_cache missing: %s" % lastf)
    with np.load(midf) as zm:
        sec = zm["sec"].astype(np.int64)
        spot_mid = zm["spot_mid"].astype(np.float64)
        perp_mid = zm["perp_mid"].astype(np.float64)
    with np.load(lastf) as zl:
        ts_us = zl["timestamps"].astype(np.int64)          # prediction time (us)

    pred_secs = ts_us // US_PER_SEC
    per_sec = per_second_factors(sec, spot_mid, perp_mid)
    sampled = sample_at_pred_secs(sec, per_sec, pred_secs)
    F = np.column_stack([sampled[n] for n in FACTOR_NAMES])
    return ts_us, F, sampled


def build_one_day(date_str, out_path):
    t0 = time.time()
    ts_us, F, parts = build_factors_for_day(date_str)
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = "%s.tmp.%d.npz" % (out_path, os.getpid())
    np.savez_compressed(
        tmp, timestamps=ts_us, F=F,
        basis_bps=parts["basis_bps"], basis_z=parts["basis_z"],
        basis_mom=parts["basis_mom"], basis_ema_dev=parts["basis_ema_dev"])
    os.replace(tmp, out_path)
    fin = float(np.isfinite(F).all(axis=1).mean())
    return {"N": int(F.shape[0]), "secs": time.time() - t0,
            "finite_frac": fin,
            "med_basis_bps": float(np.nanmedian(parts["basis_bps"]))}


# --------------------------------------------------------------------- driver
def list_days():
    """Days with BOTH a mid_cache and a lastts_cache."""
    if not p.isdir(MID_DIR):
        return []
    out = []
    for name in sorted(os.listdir(MID_DIR)):
        if not (len(name) == 14 and name.endswith(".npz")):
            continue
        d = name[:-4]
        if p.exists(p.join(LASTTS_DIR, "%s.npz" % d)):
            out.append(d)
    return out


def build(days_subset=None, force=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset if days_subset else list_days()
    print("[basis] %d day(s) -> %s" % (len(days), OUT_DIR), flush=True)
    t0 = time.time()
    n_ok = n_skip = n_fail = 0
    failed = []
    for i, d in enumerate(days):
        out = p.join(OUT_DIR, "%s.npz" % d)
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            st = build_one_day(d, out)
        except Exception as e:
            n_fail += 1; failed.append(d)
            print("  [warn] day %s failed: %s: %s"
                  % (d, type(e).__name__, e), flush=True)
            continue
        n_ok += 1
        if (i % 50) == 0 or n_ok <= 5:
            print("  [%d/%d] %s N=%d %.2fs finite=%.4f med_basis=%.2fbps"
                  % (i + 1, len(days), d, st["N"], st["secs"],
                     st["finite_frac"], st["med_basis_bps"]), flush=True)
    print("[basis] DONE in %.1f min: built=%d skip=%d fail=%d%s -> %s"
          % ((time.time() - t0) / 60, n_ok, n_skip, n_fail,
             ("  FAILED: %s" % failed[:20]) if failed else "", OUT_DIR),
          flush=True)
    return n_fail


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every day with mid_cache + lastts (skip existing)")
    g.add_argument("--days", type=str, nargs="+",
                   help="build only these YYYY-MM-DD days")
    ap.add_argument("--force", action="store_true", help="rebuild existing files")
    args = ap.parse_args()
    nf = build(days_subset=args.days, force=args.force)
    sys.exit(1 if nf else 0)

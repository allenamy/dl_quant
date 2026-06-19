"""Build the LEAK-FREE perp y_600 retarget cache (re-anchored to spot pred time).

THE BUG THIS FIXES
------------------
``data/npz_spot2perp`` swapped the spot prediction target for the PERP ``y_600``
by POSITION-joining ``npz_spot`` windows to ``npz_perp`` windows, guarding only
``|perp_ts - spot_ts| <= tol`` but NOT the SIGN of the offset. Empirically
``perp_ts - spot_ts < 0`` on ~61% of windows, i.e. the perp label's measurement
second sits BEFORE the spot feature cutoff ``spot_ts``. Because the perp y_600
window is ``[perp_ts, perp_ts + 600]``, a perp_ts earlier than the cutoff means
the label window OVERLAPS the feature window -> a lookahead leak (the leaked
prefix correlates ~+0.06 with y_600, with a regime-dependent sign). So every
artifact built on ``npz_spot2perp`` carries a leaked target.

THE FIX (re-anchor the perp target to the spot prediction time)
---------------------------------------------------------------
``data/mid_cache/<day>.npz`` holds ``sec`` (contiguous unix-second grid) and
``perp_mid`` per second (binance-futures top-of-book mid, 2024-06-01..2026-05-31).
For a spot window whose prediction second is ``s = floor(spot_ts_us / 1e6)`` (the
feature cutoff -- ``timestamps`` in npz_spot are MICROSECONDS, verified on disk),
the leak-free perp target is::

    y_600_clean = log( perp_mid[s + 600] / perp_mid[s] )

This is strictly causal: the target's measurement window starts EXACTLY at ``s``
(the feature cutoff, offset 0 by construction) and looks 600s FORWARD, which is
correct -- targets are future returns; the bug was the OLD target's window
starting BEFORE the cutoff. It uses the perp price (the tradeable instrument) and
never touches a second < s for the label.

CROSS-DAY TAIL
--------------
The last windows of a day have ``s`` near 23:5x:xx so ``s + 600`` overflows into
the next calendar day (~0.6% of windows/day). ``mid_cache`` is per-day, so we
STITCH the next day's ``perp_mid`` onto today's grid when it exists; the few tail
windows whose forward second is missing (e.g. the last day of the span, or a gap)
are simply left INVALID in ``y_mask_600`` -- never silently dropped or filled.

OUTPUT (NEW DIR -- nothing existing is touched)
-----------------------------------------------
  data/npz_spot2perp_clean/<YYYY-MM-DD>.npz  with keys:
      X            (N,600,64)     SPOT features        (copied verbatim from npz_spot)
      X_raw        (N,600,20,4)   SPOT raw LOB         (copied verbatim from npz_spot)
      regime_prior (N,6)          SPOT regime prior    (copied verbatim from npz_spot)
      timestamps   (N,)   int64   SPOT pred-idx us     (copied verbatim from npz_spot)
      y_600        (N,)   float32 RE-ANCHORED perp fwd log-return (this file)
      y_mask_600   (N,)   bool    valid where spot mask AND perp_mid[s] AND
                                  perp_mid[s+600] both present & positive

CLI
---
  python multi_asset/data/build_perp_y_clean.py --days 2025-02-10 2025-02-11
  python multi_asset/data/build_perp_y_clean.py --all              # skip existing
  python multi_asset/data/build_perp_y_clean.py --all --procs 8 --force
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import os.path as p
import sys
import time

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))

# ----------------------------------------------------------------------- paths
SPOT_NPZ_DIR = p.join(_REPO, "data", "npz_spot")    # proven feature inputs + grid
MID_DIR = p.join(_REPO, "data", "mid_cache")        # absolute perp/spot mids (1s)
OUT_DIR = p.join(_REPO, "data", "npz_spot2perp_clean")

US_PER_SEC = 1_000_000
HORIZON_SEC = 600          # y_600


# ---------------------------------------------------------------------------
# core re-anchor (pure, unit-tested)
# ---------------------------------------------------------------------------
def reanchor_y600(spot_ts_us, sec, perp_mid, horizon=HORIZON_SEC):
    """Re-anchor the perp y_600 target to the spot prediction second.

    Parameters
    ----------
    spot_ts_us : (N,) int64  spot window prediction timestamps, MICROSECONDS.
    sec        : (T,) int64  contiguous unix-second grid (this day [+ next day
                 stitched on by the caller]).
    perp_mid   : (T,) float  perp top-of-book mid aligned to ``sec``.
    horizon    : int         forward horizon in seconds (600).

    Returns
    -------
    y_clean : (N,) float64  log(perp_mid[s+600] / perp_mid[s]); NaN where either
              second is missing from the grid or the price is non-positive.
    valid   : (N,) bool      True iff y_clean is finite (both legs present & >0).

    CAUSALITY: the target window starts at s (= the feature cutoff, offset 0) and
    ends at s+horizon -- strictly forward of the cutoff. No second < s is touched.
    """
    spot_ts_us = np.asarray(spot_ts_us, dtype=np.int64)
    sec = np.asarray(sec, dtype=np.int64)
    perp_mid = np.asarray(perp_mid, dtype=np.float64)

    s = spot_ts_us // US_PER_SEC               # prediction second (feature cutoff)
    s_fwd = s + horizon                         # target measurement second

    # exact second lookup on the (contiguous, ascending) grid: searchsorted then
    # confirm the matched grid second EQUALS the requested second (no nearest-
    # neighbour fudge -> a missing second yields NaN, never a wrong price).
    def _lookup(target_sec):
        pos = np.searchsorted(sec, target_sec, side="left")
        in_range = (pos >= 0) & (pos < sec.size)
        pos_c = np.clip(pos, 0, sec.size - 1)
        hit = in_range & (sec[pos_c] == target_sec)
        v = np.full(target_sec.shape, np.nan, dtype=np.float64)
        v[hit] = perp_mid[pos_c[hit]]
        return v

    mid_s = _lookup(s)
    mid_fwd = _lookup(s_fwd)

    with np.errstate(invalid="ignore", divide="ignore"):
        good = np.isfinite(mid_s) & np.isfinite(mid_fwd) & (mid_s > 0) & (mid_fwd > 0)
        y_clean = np.full(s.shape, np.nan, dtype=np.float64)
        y_clean[good] = np.log(mid_fwd[good] / mid_s[good])

    valid = np.isfinite(y_clean)
    return y_clean, valid


# ---------------------------------------------------------------------------
# per-day build
# ---------------------------------------------------------------------------
def _next_day(date_str):
    return (dt.date.fromisoformat(date_str) + dt.timedelta(days=1)).isoformat()


def _load_mid(date_str):
    """Return (sec, perp_mid) for one day, or (None, None) if absent."""
    f = p.join(MID_DIR, "%s.npz" % date_str)
    if not p.exists(f):
        return None, None
    with np.load(f) as zm:
        return zm["sec"].astype(np.int64), zm["perp_mid"].astype(np.float64)


def _stitched_grid(date_str):
    """Today's per-second grid with the next day's perp_mid stitched on (so the
    cross-day s+600 tail can resolve). Returns (sec, perp_mid). The next day is
    optional -- if absent, only today's grid is returned and the tail windows
    whose forward second overflows simply stay invalid."""
    sec0, mid0 = _load_mid(date_str)
    if sec0 is None:
        raise FileNotFoundError("mid_cache missing: %s" % date_str)
    sec1, mid1 = _load_mid(_next_day(date_str))
    if sec1 is None:
        return sec0, mid0
    # next-day seconds strictly after today's last second (the grids are per-UTC-
    # day and contiguous, so this is just an append; guard against overlap).
    keep = sec1 > sec0[-1]
    if not keep.any():
        return sec0, mid0
    sec = np.concatenate([sec0, sec1[keep]])
    mid = np.concatenate([mid0, mid1[keep]])
    return sec, mid


def build_one_day(date_str, out_path):
    """Build + atomically write data/npz_spot2perp_clean/<day>.npz for one day."""
    t0 = time.time()
    spot_npz = p.join(SPOT_NPZ_DIR, "%s.npz" % date_str)
    if not p.exists(spot_npz):
        raise FileNotFoundError("spot cache missing: %s" % spot_npz)

    with np.load(spot_npz, allow_pickle=True) as zs:
        X = zs["X"]
        X_raw = zs["X_raw"]
        regime_prior = zs["regime_prior"]
        spot_ts = zs["timestamps"].astype(np.int64)
        spot_mask = zs["y_mask_600"].astype(bool)

    sec, perp_mid = _stitched_grid(date_str)

    y_clean, leg_valid = reanchor_y600(spot_ts, sec, perp_mid)

    # final mask: spot's own window validity AND both perp legs present
    y_mask = spot_mask & leg_valid
    # store NaN where invalid (keeps the alignment; eval masks on y_mask anyway)
    y_600 = y_clean.astype(np.float32)

    N = X.shape[0]
    assert spot_ts.shape[0] == N == y_600.shape[0] == y_mask.shape[0], \
        "row count mismatch in %s" % date_str

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = "%s.tmp.%d.npz" % (out_path, os.getpid())
    np.savez_compressed(
        tmp,
        X=X, X_raw=X_raw, regime_prior=regime_prior,
        timestamps=spot_ts,            # SPOT pred grid (authoritative)
        y_600=y_600,                   # RE-ANCHORED perp fwd return (leak-free)
        y_mask_600=y_mask,             # valid where spot mask AND both perp legs
    )
    os.replace(tmp, out_path)

    n_valid = int(y_mask.sum())
    n_tail_lost = int((spot_mask & ~leg_valid).sum())
    yv = y_clean[y_mask]
    return {
        "N": int(N), "n_valid": n_valid,
        "valid_frac": n_valid / max(N, 1),
        "n_tail_lost": n_tail_lost,
        "y_bps_std": float(np.std(yv) * 1e4) if yv.size else float("nan"),
        "secs": time.time() - t0,
        "mb": os.path.getsize(out_path) / 1e6,
    }


# --------------------------------------------------------------------- driver
def list_days():
    """Calendar days present in BOTH npz_spot and mid_cache (the buildable set).

    NOTE: a day's cross-day tail (~0.6% of windows) needs the NEXT day's
    mid_cache; those tail windows are simply masked invalid when it is absent, so
    a day is still buildable as long as its own spot + mid exist."""
    if not p.isdir(SPOT_NPZ_DIR):
        raise FileNotFoundError("spot cache dir not found: %s" % SPOT_NPZ_DIR)
    if not p.isdir(MID_DIR):
        raise FileNotFoundError("mid_cache dir not found: %s" % MID_DIR)

    def _day_set(d):
        s = set()
        for name in os.listdir(d):
            if not (len(name) == 14 and name.endswith(".npz")):
                continue
            day = name[:-4]
            try:
                dt.date.fromisoformat(day)
            except ValueError:
                continue
            s.add(day)
        return s

    return sorted(_day_set(SPOT_NPZ_DIR) & _day_set(MID_DIR))


def _worker(args):
    d, force = args
    out = p.join(OUT_DIR, "%s.npz" % d)
    if (not force) and p.exists(out):
        return (d, "skip", None)
    try:
        st = build_one_day(d, out)
        return (d, "ok", st)
    except Exception as e:
        return (d, "fail", "%s: %s" % (type(e).__name__, e))


def _report(i, n, d, status, st):
    if status == "ok":
        print("  [%d/%d] %s N=%d valid=%d (%.1f%%) tail_lost=%d "
              "y_std=%.2fbps %.2fMB %.1fs"
              % (i + 1, n, d, st["N"], st["n_valid"], 100 * st["valid_frac"],
                 st["n_tail_lost"], st["y_bps_std"], st["mb"], st["secs"]),
              flush=True)
    elif status == "fail":
        print("  [warn] day %s failed: %s" % (d, st), flush=True)


def build(days_subset=None, force=False, procs=1):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset if days_subset else list_days()
    print("[perp_y_clean] %d day(s) -> %s  (procs=%d)" % (len(days), OUT_DIR, procs),
          flush=True)
    t0 = time.time()
    n_ok = n_skip = n_fail = 0
    failed = []
    tasks = [(d, force) for d in days]

    if procs <= 1:
        for i, t in enumerate(tasks):
            d, status, st = _worker(t)
            _report(i, len(days), d, status, st)
            n_ok += status == "ok"; n_skip += status == "skip"
            if status == "fail":
                n_fail += 1; failed.append((d, st))
    else:
        import multiprocessing as mp
        with mp.Pool(processes=procs) as pool:
            for i, (d, status, st) in enumerate(
                    pool.imap_unordered(_worker, tasks, chunksize=2)):
                _report(i, len(days), d, status, st)
                n_ok += status == "ok"; n_skip += status == "skip"
                if status == "fail":
                    n_fail += 1; failed.append((d, st))

    print("[perp_y_clean] DONE in %.1f min: built=%d skip=%d fail=%d -> %s"
          % ((time.time() - t0) / 60, n_ok, n_skip, n_fail, OUT_DIR), flush=True)
    if failed:
        print("  FAILED %d day(s):" % len(failed), flush=True)
        for d, why in failed[:40]:
            print("    %s  %s" % (d, why), flush=True)
    return n_fail


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every day present in both npz_spot and mid_cache "
                        "(skip existing)")
    g.add_argument("--days", type=str, nargs="+",
                   help="build only these YYYY-MM-DD days")
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    ap.add_argument("--procs", type=int, default=1, help="parallel processes")
    args = ap.parse_args()
    nf = build(days_subset=args.days, force=args.force, procs=args.procs)
    sys.exit(1 if nf else 0)

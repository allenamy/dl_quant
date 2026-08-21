"""Build the SPOT+PERP top-of-book MID cache (Stage C real-basis, step 1).

GOAL
----
Per UTC calendar day, read ONLY the top-of-book bid0/ask0 from the raw Tardis
``book_snapshot_25`` files for BOTH venues (``binance`` = SPOT, ``binance-futures``
= PERP), compute ``mid = (bid0 + ask0) / 2`` per venue, index both onto a shared
1-second grid, and save::

    data/mid_cache/<YYYY-MM-DD>.npz
        sec       int64   (T,)   unix SECONDS (the floored-second grid)
        spot_mid  float64 (T,)   spot top-of-book mid at that second
        perp_mid  float64 (T,)   perp top-of-book mid at that second

WHY ABSOLUTE MIDS (and why a separate cache)
--------------------------------------------
The single-asset perp y_600 has a basis/funding component orthogonal to the
spot-relative microstructure features (which are mid-RELATIVE, so the basis
cancels). To recover the basis = perp_mid - spot_mid we need the ABSOLUTE mids,
which the existing npz caches deliberately do not store. This cache holds exactly
those two absolute price series on a common 1s grid, nothing else — kept light
(top-of-book only) so the ~2yr span builds quickly.

NO LEAKAGE / CAUSALITY
----------------------
The 1s grid uses the SAME floor-then-ffill convention as the frozen perp
pipeline (``_resample_lob_to_1s``): timestamps are floored to the second (no
rounding -> no look-ahead), the last tick within each second is kept, the grid is
made contiguous, and gaps are forward-filled (causal — only past info). The basis
factors built downstream apply their own shift(1) for any rolling/EMA stat; this
file just produces the two raw mid series faithfully.

CLI
---
  python multi_asset/data/build_mid_cache.py --days 2025-02-10 2025-02-11
  python multi_asset/data/build_mid_cache.py --all          # span, skip existing
  python multi_asset/data/build_mid_cache.py --all --procs 8
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import os
import os.path as p
import sys
import time
from io import StringIO

import numpy as np
import pandas as pd

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))

# --------------------------------------------------------------------- paths
BOOK_ROOT = ("/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/"
             "book_snapshot_25")                              # READ-ONLY
SPOT_VENUE = "binance"
PERP_VENUE = "binance-futures"
OUT_DIR = p.join(_REPO, "data", "mid_cache")

# The basis gate needs ~2024-06-01 .. 2026-05-31 (covers the strong-2025 and
# choppy-2026 folds with >=230 train days of history). Build that span only.
SPAN_START = dt.date(2024, 6, 1)
SPAN_END = dt.date(2026, 5, 31)

US_PER_SEC = 1_000_000

# only top-of-book is needed for the mid
_BOOK_COLS = ["timestamp", "asks[0].price", "bids[0].price"]


# ----------------------------------------------------------- vendored reader
def _read_gz_csv_robust(path, usecols=None):
    """gzip CSV reader robust to truncated streams — VENDORED verbatim (logic)
    from multi_asset.data.build_dual_npz._read_gz_csv_robust."""
    try:
        try:
            return pd.read_csv(path, usecols=usecols, engine="pyarrow")
        except Exception:
            return pd.read_csv(path, usecols=usecols)
    except (EOFError, OSError):
        header, rows = None, []
        try:
            with gzip.open(path, "rt", errors="replace") as f:
                for line in f:
                    if header is None:
                        header = line
                        continue
                    rows.append(line)
        except (EOFError, OSError):
            pass
        if header is None or not rows:
            raise ValueError("%s: no readable content" % path)
        df = pd.read_csv(StringIO("".join([header] + rows)), on_bad_lines="skip")
        return df[usecols] if usecols else df


def _book_path(date_str, venue):
    return p.join(BOOK_ROOT, date_str, venue, "BTCUSDT.csv.gz")


def _mid_1s(date_str, venue):
    """Return (sec, mid) for one UTC day/venue on a contiguous 1s grid.

    floor->last-per-second->contiguous-grid->ffill, stripped to [00:00,24:00) UTC.
    sec is unix SECONDS (int64); mid is float64. Causal (floor + ffill only)."""
    path = _book_path(date_str, venue)
    if not p.exists(path):
        raise FileNotFoundError(path)
    df = _read_gz_csv_robust(path, usecols=_BOOK_COLS)
    ts = df["timestamp"].to_numpy(np.int64)
    bid0 = df["bids[0].price"].to_numpy(np.float64)
    ask0 = df["asks[0].price"].to_numpy(np.float64)
    mid = (bid0 + ask0) / 2.0

    sec = ts // US_PER_SEC
    # keep last tick within each second (data is time-ordered, but sort to be safe)
    order = np.argsort(ts, kind="stable")
    sec_s = sec[order]
    mid_s = mid[order]
    # last occurrence per second: since stable-sorted by ts, the last index for
    # each unique second is the last tick of that second.
    uniq_sec, last_pos = np.unique(sec_s[::-1], return_index=True)
    last_idx = (len(sec_s) - 1) - last_pos
    last_idx.sort()
    g_sec = sec_s[last_idx]
    g_mid = mid_s[last_idx]

    # contiguous 1s grid + forward-fill (causal)
    full = np.arange(g_sec[0], g_sec[-1] + 1, dtype=np.int64)
    filled = np.full(full.shape, np.nan, dtype=np.float64)
    pos = g_sec - g_sec[0]
    filled[pos] = g_mid
    # forward-fill
    isn = np.isnan(filled)
    if isn.any():
        idx = np.where(~isn, np.arange(filled.size), 0)
        np.maximum.accumulate(idx, out=idx)
        filled = filled[idx]

    # strip to [00:00, 24:00) UTC
    day_start = int(pd.Timestamp(date_str, tz="UTC").timestamp())
    day_end = day_start + 86_400
    keep = (full >= day_start) & (full < day_end)
    return full[keep], filled[keep]


def build_one_day(date_str, out_path):
    """Build + atomically write data/mid_cache/<day>.npz for one UTC day."""
    t0 = time.time()
    spot_sec, spot_mid = _mid_1s(date_str, SPOT_VENUE)
    perp_sec, perp_mid = _mid_1s(date_str, PERP_VENUE)

    # intersect the two grids to a common second index (inner join on second)
    common = np.intersect1d(spot_sec, perp_sec)
    if common.size == 0:
        raise ValueError("%s: empty spot/perp second intersection" % date_str)
    s_pos = np.searchsorted(spot_sec, common)
    p_pos = np.searchsorted(perp_sec, common)
    spot_m = spot_mid[s_pos]
    perp_m = perp_mid[p_pos]

    if not (np.all(np.isfinite(spot_m)) and np.all(np.isfinite(perp_m))):
        # ffill should have removed NaN past the first tick; guard anyway
        bad = (~np.isfinite(spot_m)) | (~np.isfinite(perp_m))
        common = common[~bad]
        spot_m = spot_m[~bad]
        perp_m = perp_m[~bad]
        if common.size == 0:
            raise ValueError("%s: all-NaN after intersection" % date_str)

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = "%s.tmp.%d.npz" % (out_path, os.getpid())
    np.savez_compressed(tmp, sec=common.astype(np.int64),
                        spot_mid=spot_m.astype(np.float64),
                        perp_mid=perp_m.astype(np.float64))
    os.replace(tmp, out_path)

    med_basis = float(np.median((perp_m - spot_m) / spot_m * 1e4))
    return {"T": int(common.size), "secs": time.time() - t0,
            "mb": os.path.getsize(out_path) / 1e6,
            "spot_mid0": float(spot_m[0]), "perp_mid0": float(perp_m[0]),
            "med_basis_bps": med_basis}


# --------------------------------------------------------------------- driver
def _span_days():
    out, d = [], SPAN_START
    while d <= SPAN_END:
        out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def list_days():
    """Span days that have BOTH a spot and a perp Tardis book."""
    out = []
    for d in _span_days():
        if p.exists(_book_path(d, SPOT_VENUE)) and p.exists(_book_path(d, PERP_VENUE)):
            out.append(d)
    return out


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


def build(days_subset=None, force=False, procs=8):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset if days_subset else list_days()
    print("[mid] %d day(s) -> %s  (procs=%d)" % (len(days), OUT_DIR, procs),
          flush=True)
    t0 = time.time()
    n_ok = n_skip = n_fail = 0
    failed = []
    tasks = [(d, force) for d in days]

    if procs <= 1:
        results = (_worker(t) for t in tasks)
        for i, (d, status, st) in enumerate(results):
            _report(i, len(days), d, status, st)
            n_ok += status == "ok"; n_skip += status == "skip"
            if status == "fail":
                n_fail += 1; failed.append(d)
    else:
        import multiprocessing as mp
        with mp.Pool(processes=procs) as pool:
            for i, (d, status, st) in enumerate(
                    pool.imap_unordered(_worker, tasks, chunksize=2)):
                _report(i, len(days), d, status, st)
                n_ok += status == "ok"; n_skip += status == "skip"
                if status == "fail":
                    n_fail += 1; failed.append(d)

    print("[mid] DONE in %.1f min: built=%d skip=%d fail=%d%s -> %s"
          % ((time.time() - t0) / 60, n_ok, n_skip, n_fail,
             ("  FAILED: %s" % failed[:20]) if failed else "", OUT_DIR),
          flush=True)
    return n_fail


def _report(i, n, d, status, st):
    if status == "ok":
        print("  [%d/%d] %s T=%d %.2fMB %.1fs spot0=%.2f perp0=%.2f "
              "med_basis=%.2fbps"
              % (i + 1, n, d, st["T"], st["mb"], st["secs"],
                 st["spot_mid0"], st["perp_mid0"], st["med_basis_bps"]),
              flush=True)
    elif status == "fail":
        print("  [warn] day %s failed: %s" % (d, st), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build the gate span (skip existing)")
    g.add_argument("--days", type=str, nargs="+",
                   help="build only these YYYY-MM-DD days")
    ap.add_argument("--force", action="store_true", help="rebuild existing files")
    ap.add_argument("--procs", type=int, default=8, help="parallel processes")
    args = ap.parse_args()
    nf = build(days_subset=args.days, force=args.force, procs=args.procs)
    sys.exit(1 if nf else 0)

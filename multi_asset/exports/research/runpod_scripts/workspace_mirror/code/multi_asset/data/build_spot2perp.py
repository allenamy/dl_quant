"""Build the SPOT2PERP retarget cache (Stage B-data) — LIGHT, no Tardis re-read.

GOAL
----
Per UTC calendar day, emit a training NPZ that keeps the PROVEN SPOT feature
inputs (X / X_raw / regime_prior / timestamps from ``data/npz_spot`` — spot order
flow reproduces the single-asset milestone signal, ~2x cleaner than perp) but
REPLACES the prediction target with the PERP ``y_600`` / ``y_mask_600`` (from
``data/npz_perp``). The result trains the proven SPOT-feature REG_arch to predict
the binance-FUTURES (perp) 10-min forward return.

WHY A POSITION JOIN IS SAFE
---------------------------
``npz_spot`` and ``npz_perp`` were built by the SAME windowing pipeline (input_len
600, stride 180) on the SAME UTC day grid, so per day they have identical row
count N and identical window ordering. Their pred-index timestamps are NOT always
byte-identical: ``perp_ts - spot_ts`` is a CONSTANT per day (a snapshot-label
offset, empirically 0 or +/-1..4 s). Because the target is a FUTURE return
(y at t = return over [t, t+600s]), a small constant snapshot offset is
causal-safe — it only shifts which second the label is anchored to by a few
seconds, far inside the 600s horizon, and identically for every row.

We therefore join by POSITION and GUARD it: a day is emitted only when
  (a) spot and perp have the SAME length, AND
  (b) ``np.ptp(perp_ts - spot_ts) <= 10e6`` us  (offset constant across all rows
      to within <= 10 s; i.e. a single per-day shift, not a row-dependent
      misalignment).
Days that fail either guard are SKIPPED and LOGGED (with their length mismatch /
offset spread) — never silently position-joined.

OUTPUT (NEW DIR — nothing existing is touched)
----------------------------------------------
  data/npz_spot2perp/<YYYY-MM-DD>.npz  with keys:
      X            (N,600,64)     SPOT features        (copied from npz_spot)
      X_raw        (N,600,20,4)   SPOT raw LOB         (copied from npz_spot)
      regime_prior (N,6)          SPOT regime prior    (copied from npz_spot)
      timestamps   (N,)           SPOT pred-idx us     (copied from npz_spot)
      y_600        (N,)           PERP fwd log-return  (copied from npz_perp)
      y_mask_600   (N,)           PERP target mask     (copied from npz_perp)

CLI
---
  python multi_asset/data/build_spot2perp.py --days 2025-02-10 2025-02-11
  python multi_asset/data/build_spot2perp.py --all            # skip existing
  python multi_asset/data/build_spot2perp.py --all --force     # rebuild all
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
SPOT_NPZ_DIR = p.join(_REPO, "data", "npz_spot")   # proven feature inputs
PERP_NPZ_DIR = p.join(_REPO, "data", "npz_perp")   # perp target source
OUT_DIR = p.join(_REPO, "data", "npz_spot2perp")

# offset-constancy tolerance: perp_ts - spot_ts must vary by <= this many us
# across all rows of a day (i.e. a single per-day snapshot shift of <= 10 s).
MAX_OFFSET_PTP_US = int(10e6)


class AlignmentError(ValueError):
    """Raised when spot/perp cannot be safely position-joined for a day."""


def _check_alignment(spot_ts, perp_ts):
    """Validate the (a) equal-length and (b) constant-offset guards.

    Returns (offset_us, ptp_us) on success; raises AlignmentError otherwise.
    ``offset_us`` is the per-day perp-minus-spot snapshot shift (median row).
    """
    spot_ts = spot_ts.astype(np.int64)
    perp_ts = perp_ts.astype(np.int64)
    if spot_ts.shape != perp_ts.shape:
        raise AlignmentError(
            "length mismatch: spot N=%d perp N=%d" % (spot_ts.shape[0],
                                                      perp_ts.shape[0]))
    diff = perp_ts - spot_ts
    ptp = int(np.ptp(diff))
    if ptp > MAX_OFFSET_PTP_US:
        raise AlignmentError(
            "offset not constant: ptp(perp_ts-spot_ts)=%d us > %d us "
            "(row-dependent misalignment)" % (ptp, MAX_OFFSET_PTP_US))
    return int(np.median(diff)), ptp


def build_one_day(date_str, out_path):
    """Build + atomically write data/npz_spot2perp/<day>.npz for one UTC day."""
    t0 = time.time()
    spot_npz = p.join(SPOT_NPZ_DIR, "%s.npz" % date_str)
    perp_npz = p.join(PERP_NPZ_DIR, "%s.npz" % date_str)
    if not p.exists(spot_npz):
        raise FileNotFoundError("spot cache missing: %s" % spot_npz)
    if not p.exists(perp_npz):
        raise FileNotFoundError("perp cache missing: %s" % perp_npz)

    with np.load(spot_npz, allow_pickle=True) as zs:
        X = zs["X"]
        X_raw = zs["X_raw"]
        regime_prior = zs["regime_prior"]
        spot_ts = zs["timestamps"].astype(np.int64)
    with np.load(perp_npz, allow_pickle=True) as zp:
        perp_ts = zp["timestamps"].astype(np.int64)
        y_600 = zp["y_600"]
        y_mask_600 = zp["y_mask_600"]

    # GUARD: equal length + constant per-day offset (else skip this day)
    offset_us, ptp_us = _check_alignment(spot_ts, perp_ts)

    N = X.shape[0]
    if not (y_600.shape[0] == N and y_mask_600.shape[0] == N):
        raise AlignmentError(
            "perp target length %d/%d != spot N=%d"
            % (y_600.shape[0], y_mask_600.shape[0], N))

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = "%s.tmp.%d.npz" % (out_path, os.getpid())
    np.savez_compressed(
        tmp,
        X=X, X_raw=X_raw, regime_prior=regime_prior,
        timestamps=spot_ts,        # from SPOT (authoritative window grid)
        y_600=y_600,               # from PERP (target swapped)
        y_mask_600=y_mask_600,     # from PERP
    )
    os.replace(tmp, out_path)
    return {"N": int(N), "offset_sec": offset_us / 1e6,
            "offset_ptp_sec": ptp_us / 1e6, "secs": time.time() - t0,
            "mb": os.path.getsize(out_path) / 1e6}


def list_days():
    """Calendar days present in BOTH npz_spot and npz_perp."""
    if not p.isdir(SPOT_NPZ_DIR):
        raise FileNotFoundError("spot cache dir not found: %s" % SPOT_NPZ_DIR)
    if not p.isdir(PERP_NPZ_DIR):
        raise FileNotFoundError("perp cache dir not found: %s" % PERP_NPZ_DIR)

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

    return sorted(_day_set(SPOT_NPZ_DIR) & _day_set(PERP_NPZ_DIR))


def build(days_subset=None, force=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset if days_subset else list_days()
    print("[spot2perp] %d day(s) -> %s" % (len(days), OUT_DIR), flush=True)
    t0 = time.time()
    n_done = n_skip_exist = n_skip_align = n_fail = 0
    skipped_align = []     # (day, reason)
    failed = []            # (day, reason)
    for i, d in enumerate(days):
        out = p.join(OUT_DIR, "%s.npz" % d)
        if (not force) and p.exists(out):
            n_skip_exist += 1
            continue
        try:
            st = build_one_day(d, out)
        except AlignmentError as e:
            n_skip_align += 1
            skipped_align.append((d, str(e)))
            print("  [SKIP-align] %s: %s" % (d, e), flush=True)
            continue
        except Exception as e:
            n_fail += 1
            failed.append((d, "%s: %s" % (type(e).__name__, e)))
            print("  [warn] day %s failed: %s: %s"
                  % (d, type(e).__name__, e), flush=True)
            continue
        n_done += 1
        if (i + 1) % 100 == 0 or len(days) <= 20:
            print("  [%d/%d] %s N=%d offset=%+.0fs ptp=%.0fs %.2fMB %.2fs"
                  % (i + 1, len(days), d, st["N"], st["offset_sec"],
                     st["offset_ptp_sec"], st["mb"], st["secs"]), flush=True)

    print("[spot2perp] DONE in %.1f min: built=%d skip_exist=%d "
          "skip_align=%d fail=%d -> %s"
          % ((time.time() - t0) / 60, n_done, n_skip_exist, n_skip_align,
             n_fail, OUT_DIR), flush=True)
    if skipped_align:
        print("  ALIGN-SKIPPED %d day(s):" % len(skipped_align), flush=True)
        for d, why in skipped_align:
            print("    %s  %s" % (d, why), flush=True)
    if failed:
        print("  FAILED %d day(s):" % len(failed), flush=True)
        for d, why in failed:
            print("    %s  %s" % (d, why), flush=True)
    return n_fail


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every day present in both npz_spot and npz_perp "
                        "(skip existing)")
    g.add_argument("--days", type=str, nargs="+",
                   help="build only these YYYY-MM-DD days")
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    args = ap.parse_args()
    nf = build(days_subset=args.days, force=args.force)
    sys.exit(1 if nf else 0)

"""Build the DUAL-LOB training cache by a CHEAP merge (Stage D2, no Tardis).

GOAL
----
Per UTC calendar day, write ``data/npz_duallob/<day>.npz`` = **ALL keys of the
baseline ``data/npz_spot2perp/<day>.npz``** PLUS one new key
``X_raw_perp_deep`` = the PERP raw order book from ``data/npz_perp/<day>.npz``
(``X_raw`` there). The two caches are position-joined bar-for-bar.

WHY THIS IS THE RIGHT (and cheap) MERGE
---------------------------------------
The dual-LOB experiment asks: does fusing the **perp** deep order book lift the
perp ``y_600`` prediction over the SPOT-only baseline? The baseline model
(``DualPathLOBModelV3`` = REG_arch) trains on ``data/npz_spot2perp``: spot
features ``X`` (N,600,64), the SPOT raw LOB ``X_raw`` (N,600,20,4) feeding its
Path-B tower, ``regime_prior``, and the PERP target ``y_600``/``y_mask_600``.

``DualLOBREGArch`` (the subclass under test) keeps the spot book on Path B
(``X_raw``) and injects the PERP deep book as a zero-init-identity *gated
residual* via the new ``x_raw_perp_deep`` input. So this cache only needs to add
the perp raw book alongside the existing spot2perp contract — everything else
(``X``, ``y_600``, ``regime_prior``, ``timestamps``) is copied VERBATIM so the
baseline is exactly reproduced and the ONLY new content is the perp book.

There is no Tardis re-derivation here: ``data/npz_perp`` already holds the perp
raw LOB built by the frozen perp pipeline, so the merge is a pure file join.

POSITION JOIN (verified, see multi_asset/eda/perpY_ridge_gate.py)
----------------------------------------------------------------
``npz_spot2perp`` and ``npz_perp`` have the SAME number of rows per day and
``perp_ts - spot_ts`` is a single CONSTANT across all rows for the day (0 on most
days, a small whole-second offset on the rest — a snapshot-time label
convention, NOT a row misalignment). Rows are therefore positionally aligned
bar-for-bar. We:
  1. assert equal length (N),
  2. assert the per-row (perp_ts - spot_ts) offset is CONSTANT and within
     ``SHIFT_TOL_US`` (skip the day otherwise — a non-constant shift would mean a
     genuine misalignment),
  3. assert ``X_raw_perp_deep`` (perp X_raw) has the SAME shape as the spot
     ``X_raw``,
  4. assert the PERP ``y_600`` is byte-identical between the two caches (both
     carry the perp target; a free integrity check that the join is sound).

OUTPUT (NEW DIR — nothing existing is touched)
----------------------------------------------
  data/npz_duallob/<YYYY-MM-DD>.npz with keys:
      <all keys of data/npz_spot2perp/<day>.npz, copied verbatim>:
        X            float32 (N,600,64)    spot features
        X_raw        float16 (N,600,20,4)  SPOT raw LOB  (Path B — unchanged)
        regime_prior float32 (N,6)
        y_600        float32 (N,)          PERP target
        y_mask_600   uint8   (N,)
        timestamps   int64   (N,)
      X_raw_perp_deep float16 (N,600,20,4) NEW — PERP raw LOB (gated residual)

CLI
---
  python multi_asset/data/build_duallob_npz.py --days 2025-02-10 2025-02-11
  python multi_asset/data/build_duallob_npz.py --all          # skip existing
  python multi_asset/data/build_duallob_npz.py --all --force  # rebuild
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

SPOT2PERP_DIR = p.join(_REPO, "data", "npz_spot2perp")   # baseline contract (READ)
PERP_DIR = p.join(_REPO, "data", "npz_perp")             # perp raw book   (READ)
OUT_DIR = p.join(_REPO, "data", "npz_duallob")           # NEW output dir

# Allow up to +/-10s of CONSTANT whole-second label offset between the two grids
# (snapshot-time convention). Anything non-constant, or beyond this, is treated
# as a real misalignment and the day is skipped. Matches perpY_ridge_gate.py.
SHIFT_TOL_US = 10_000_000

NEW_KEY = "X_raw_perp_deep"


def build_one_day(date_str: str, out_path: str) -> dict:
    """Build + atomically write ``data/npz_duallob/<day>.npz`` for one UTC day.

    Copies every key of the spot2perp cache verbatim and adds
    ``X_raw_perp_deep`` = the perp cache's ``X_raw``, position-joined with the
    asserts documented in the module docstring. Raises on any violation so a
    bad day is never silently emitted.
    """
    t0 = time.time()

    spot_npz = p.join(SPOT2PERP_DIR, "%s.npz" % date_str)
    perp_npz = p.join(PERP_DIR, "%s.npz" % date_str)
    if not p.exists(spot_npz):
        raise FileNotFoundError("spot2perp cache missing: %s" % spot_npz)
    if not p.exists(perp_npz):
        raise FileNotFoundError("perp cache missing: %s" % perp_npz)

    with np.load(spot_npz, allow_pickle=True) as zs:
        # Copy ALL spot2perp keys verbatim (materialize now; np.load is lazy).
        spot_data = {k: zs[k] for k in zs.files}
    with np.load(perp_npz, allow_pickle=True) as zp:
        perp_raw = np.asarray(zp["X_raw"])           # PERP raw LOB (N,600,20,4)
        perp_ts = np.asarray(zp["timestamps"], dtype=np.int64)

    if "X_raw" not in spot_data:
        raise KeyError("%s: spot2perp cache lacks X_raw (the spot Path-B book)"
                       % date_str)
    spot_raw = np.asarray(spot_data["X_raw"])        # SPOT raw LOB (N,600,20,4)
    spot_ts = np.asarray(spot_data["timestamps"], dtype=np.int64)

    Ns, Np = spot_raw.shape[0], perp_raw.shape[0]

    # (1) equal length — required for a positional join.
    if Ns != Np:
        raise RuntimeError(
            "%s: length mismatch spot N=%d vs perp N=%d — cannot position-join"
            % (date_str, Ns, Np))

    # (2) constant within-tolerance timestamp offset (snapshot-time convention).
    diff = perp_ts - spot_ts
    if diff.size == 0:
        raise RuntimeError("%s: zero rows" % date_str)
    if not np.all(diff == diff[0]):
        uniq = np.unique(diff)
        raise RuntimeError(
            "%s: non-constant perp-spot timestamp offset (%d distinct values, "
            "e.g. %s) — genuine row misalignment, refusing to emit"
            % (date_str, uniq.size, uniq[:5].tolist()))
    off_us = int(diff[0])
    if abs(off_us) > SHIFT_TOL_US:
        raise RuntimeError(
            "%s: constant offset %d us (> tol %d us) — refusing to emit"
            % (date_str, off_us, SHIFT_TOL_US))

    # (3) perp raw (the new key) must match the spot raw shape exactly.
    if perp_raw.shape != spot_raw.shape:
        raise RuntimeError(
            "%s: X_raw_perp_deep shape %s != spot X_raw shape %s"
            % (date_str, perp_raw.shape, spot_raw.shape))

    # (4) free integrity check: both caches carry the PERP y_600; it must be
    #     byte-identical (proves the positional join is on the same rows).
    if "y_600" in spot_data:
        with np.load(perp_npz, allow_pickle=True) as zp2:
            if "y_600" in zp2.files:
                ys = np.nan_to_num(np.asarray(spot_data["y_600"], dtype=np.float64))
                yp = np.nan_to_num(np.asarray(zp2["y_600"], dtype=np.float64))
                if not np.array_equal(ys, yp):
                    md = float(np.max(np.abs(ys - yp)))
                    raise RuntimeError(
                        "%s: perp y_600 differs between spot2perp and perp "
                        "caches (max|dev|=%.3e) — join is NOT row-aligned, "
                        "refusing to emit" % (date_str, md))

    # Assemble: all spot2perp keys + the new perp deep book.
    out = dict(spot_data)
    out[NEW_KEY] = perp_raw

    # Atomic write (tmp + os.replace), preserving compression like the source.
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = "%s.tmp.%d.npz" % (out_path, os.getpid())
    np.savez_compressed(tmp, **out)
    os.replace(tmp, out_path)

    return {
        "N": int(Ns),
        "secs": time.time() - t0,
        "mb": os.path.getsize(out_path) / 1e6,
        "offset_sec": off_us // 1_000_000,
        "perp_raw_finite_frac": float(np.isfinite(perp_raw).mean()),
    }


def list_days() -> list:
    """Calendar days present in BOTH the spot2perp and perp caches."""
    if not p.isdir(SPOT2PERP_DIR):
        raise FileNotFoundError("spot2perp dir not found: %s" % SPOT2PERP_DIR)
    if not p.isdir(PERP_DIR):
        raise FileNotFoundError("perp dir not found: %s" % PERP_DIR)

    def _days(d):
        out = set()
        for name in os.listdir(d):
            if not (len(name) == 14 and name.endswith(".npz")):
                continue
            stem = name[:-4]
            try:
                dt.date.fromisoformat(stem)
            except ValueError:
                continue
            out.add(stem)
        return out

    return sorted(_days(SPOT2PERP_DIR) & _days(PERP_DIR))


def build(days_subset=None, force=False) -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset if days_subset else list_days()
    print("[duallob] %d day(s) -> %s" % (len(days), OUT_DIR), flush=True)
    t0 = time.time()
    n_done = n_skip = n_fail = 0
    failed = []
    for i, d in enumerate(days):
        out = p.join(OUT_DIR, "%s.npz" % d)
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            st = build_one_day(d, out)
        except Exception as e:  # noqa: BLE001 — keep going; report at the end
            n_fail += 1
            failed.append(d)
            print("  [warn] day %s failed: %s: %s"
                  % (d, type(e).__name__, e), flush=True)
            continue
        n_done += 1
        print("  [%d/%d] %s N=%d %.1fMB %.1fs offset=%ds finite=%.4f"
              % (i + 1, len(days), d, st["N"], st["mb"], st["secs"],
                 st["offset_sec"], st["perp_raw_finite_frac"]),
              flush=True)
    print("[duallob] DONE in %.1f min: built=%d skip=%d fail=%d%s -> %s"
          % ((time.time() - t0) / 60, n_done, n_skip, n_fail,
             ("  FAILED: %s" % failed) if failed else "", OUT_DIR), flush=True)
    return n_fail


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every day present in BOTH caches (skip existing)")
    g.add_argument("--days", type=str, nargs="+",
                   help="build only these YYYY-MM-DD days")
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    args = ap.parse_args()
    nf = build(days_subset=args.days, force=args.force)
    sys.exit(1 if nf else 0)

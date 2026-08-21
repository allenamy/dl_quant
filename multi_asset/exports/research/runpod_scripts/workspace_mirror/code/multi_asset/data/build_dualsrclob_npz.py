"""Build the DUAL-SOURCE + perp-deep-book cache by a CHEAP merge (Stage G, no Tardis).

GOAL
----
Per UTC calendar day, write ``data/npz_dualsrclob/<day>.npz`` = **ALL keys of the
dual-SOURCE cache ``data/npz_dualsrc/<day>.npz`` (copied VERBATIM)** PLUS one new
key ``X_raw_perp_deep`` = the PERP raw order book from ``data/npz_perp/<day>.npz``
(its ``X_raw`` there). The two caches are position-joined bar-for-bar.

WHY THIS IS THE RIGHT (and cheap) MERGE — and how it differs from build_duallob_npz
-----------------------------------------------------------------------------------
This is the THIRD experiment arm (Stage G): take the proven dual-SOURCE model
(``data/npz_dualsrc``: X = spot-64 ++ 5 DIFFERENCED perp-spot divergence-seq = 69;
``regime_prior`` = 6 spot cols ++ 4 UN-normalized LEVEL signals = 10; SPOT
``X_raw`` on Path B; LEAK-FREE re-anchored perp ``y_600``) and ALSO feed the PERP
deep order book as a zero-init-identity *gated residual* via the new
``x_raw_perp_deep`` model input (``DualLOBREGArch(use_perp_residual=True)``). So
this cache copies the entire dual-SOURCE contract VERBATIM (so the dual-SOURCE
baseline is exactly reproduced and the ONLY new content is the perp book) and
adds the perp raw LOB alongside it.

It is the dual-SOURCE analogue of ``build_duallob_npz.py`` (which merges
``npz_spot2perp`` + ``npz_perp``). Two deliberate differences from that builder:

  * BASE is ``npz_dualsrc`` (X width 69, regime_prior width 10, ``y_mask_600``
    dtype bool) — NOT ``npz_spot2perp`` (X width 64, regime_prior width 6). Set
    ``model.d_prior=10`` in the config (the dual-SOURCE FiLM level-routing).

  * NO ``y_600`` byte-identity check against ``npz_perp``. ``build_duallob_npz``
    asserts ``spot2perp.y_600 == perp.y_600`` byte-for-byte as a free join check,
    because the spot2perp cache carries the SAME (un-re-anchored) perp target the
    perp cache does. The dual-SOURCE cache instead carries the **LEAK-FREE
    RE-ANCHORED** perp ``y_600`` (target window starts EXACTLY at the spot
    feature cutoff; see ``build_dualsrc_npz`` / ``build_perp_y_clean``), which is
    a DIFFERENT array from the perp cache's older ``y_600`` (verified
    ``max|dev|~2e-3`` on 2025-02-10). We must keep the dual-SOURCE (re-anchored)
    target verbatim — it is the leak-free label this arm trains on — so the
    byte-identity check is intentionally DROPPED. The positional join is instead
    validated by the structural asserts that DO hold (equal N, constant within-
    tolerance timestamp offset, equal X_raw shape), which are exactly what
    ``build_dualsrc_npz`` itself relies on to align perp-vs-spot rows.

There is no Tardis re-derivation here: ``data/npz_perp`` already holds the perp
raw LOB built by the frozen perp pipeline, so the merge is a pure file join.

POSITION JOIN (verified, see build_dualsrc_npz / multi_asset/eda/perpY_ridge_gate)
----------------------------------------------------------------------------------
``npz_dualsrc`` (whose grid IS the leak-free clean cache's spot grid) and
``npz_perp`` have the SAME number of rows per day and ``perp_ts - spot_ts`` is a
single CONSTANT across all rows for the day (0 on most days, a small whole-second
offset on the rest — a snapshot-time label convention, NOT a row misalignment;
``build_dualsrc_npz`` asserts ``ptp(perp_ts - spot_ts) == 0`` and aligns by it).
Rows are therefore positionally aligned bar-for-bar. We:
  1. assert equal length (N),
  2. assert the per-row (perp_ts - spot_ts) offset is CONSTANT and within
     ``SHIFT_TOL_US`` (skip the day otherwise — a non-constant shift would mean a
     genuine misalignment),
  3. assert ``X_raw_perp_deep`` (perp X_raw) has the SAME shape as the dual-SOURCE
     spot ``X_raw``.

OUTPUT (NEW DIR — nothing existing is touched)
----------------------------------------------
  data/npz_dualsrclob/<YYYY-MM-DD>.npz with keys:
      <all keys of data/npz_dualsrc/<day>.npz, copied verbatim>:
        X            float32 (N,600,69)    spot-64 ++ 5 divergence-seq
        X_raw        float16 (N,600,20,4)  SPOT raw LOB  (Path B — unchanged)
        regime_prior float32 (N,10)        6 spot ++ 4 LEVEL (FiLM-routed)
        y_600        float32 (N,)          LEAK-FREE re-anchored PERP target
        y_mask_600   bool    (N,)
        timestamps   int64   (N,)
      X_raw_perp_deep float16 (N,600,20,4) NEW — PERP raw LOB (gated residual)

CLI
---
  python multi_asset/data/build_dualsrclob_npz.py --days 2025-02-10 2026-01-05
  python multi_asset/data/build_dualsrclob_npz.py --all          # skip existing
  python multi_asset/data/build_dualsrclob_npz.py --all --force  # rebuild
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

DUALSRC_DIR = p.join(_REPO, "data", "npz_dualsrc")   # dual-SOURCE contract (READ)
PERP_DIR = p.join(_REPO, "data", "npz_perp")         # perp raw book        (READ)
OUT_DIR = p.join(_REPO, "data", "npz_dualsrclob")    # NEW output dir

# Allow up to +/-10s of CONSTANT whole-second label offset between the two grids
# (snapshot-time convention). Anything non-constant, or beyond this, is treated
# as a real misalignment and the day is skipped. Matches build_duallob_npz.py.
SHIFT_TOL_US = 10_000_000

NEW_KEY = "X_raw_perp_deep"


def build_one_day(date_str: str, out_path: str) -> dict:
    """Build + atomically write ``data/npz_dualsrclob/<day>.npz`` for one UTC day.

    Copies every key of the dual-SOURCE cache verbatim and adds
    ``X_raw_perp_deep`` = the perp cache's ``X_raw``, position-joined with the
    structural asserts documented in the module docstring. Raises on any
    violation so a bad day is never silently emitted.
    """
    t0 = time.time()

    dualsrc_npz = p.join(DUALSRC_DIR, "%s.npz" % date_str)
    perp_npz = p.join(PERP_DIR, "%s.npz" % date_str)
    if not p.exists(dualsrc_npz):
        raise FileNotFoundError("dualsrc cache missing: %s" % dualsrc_npz)
    if not p.exists(perp_npz):
        raise FileNotFoundError("perp cache missing: %s" % perp_npz)

    with np.load(dualsrc_npz, allow_pickle=True) as zs:
        # Copy ALL dualsrc keys verbatim (materialize now; np.load is lazy).
        dualsrc_data = {k: zs[k] for k in zs.files}
    with np.load(perp_npz, allow_pickle=True) as zp:
        perp_raw = np.asarray(zp["X_raw"])           # PERP raw LOB (N,600,20,4)
        perp_ts = np.asarray(zp["timestamps"], dtype=np.int64)

    if "X_raw" not in dualsrc_data:
        raise KeyError("%s: dualsrc cache lacks X_raw (the spot Path-B book)"
                       % date_str)
    spot_raw = np.asarray(dualsrc_data["X_raw"])     # SPOT raw LOB (N,600,20,4)
    spot_ts = np.asarray(dualsrc_data["timestamps"], dtype=np.int64)

    Ns, Np = spot_raw.shape[0], perp_raw.shape[0]

    # (1) equal length — required for a positional join.
    if Ns != Np:
        raise RuntimeError(
            "%s: length mismatch dualsrc N=%d vs perp N=%d — cannot position-join"
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
            "%s: X_raw_perp_deep shape %s != dualsrc X_raw shape %s"
            % (date_str, perp_raw.shape, spot_raw.shape))

    # NOTE: NO y_600 byte-identity check here (unlike build_duallob_npz). The
    # dual-SOURCE cache carries the LEAK-FREE RE-ANCHORED perp y_600, which is a
    # DIFFERENT array from npz_perp's older y_600 (verified max|dev|~2e-3). We
    # keep the dual-SOURCE re-anchored target verbatim; the structural asserts
    # (1)-(3) above are what validate the positional join (same asserts
    # build_dualsrc_npz itself uses to align perp-vs-spot rows).

    # Assemble: all dualsrc keys + the new perp deep book.
    out = dict(dualsrc_data)
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
    """Calendar days present in BOTH the dualsrc and perp caches."""
    if not p.isdir(DUALSRC_DIR):
        raise FileNotFoundError("dualsrc dir not found: %s" % DUALSRC_DIR)
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

    return sorted(_days(DUALSRC_DIR) & _days(PERP_DIR))


def build(days_subset=None, force=False) -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset if days_subset else list_days()
    print("[dualsrclob] %d day(s) -> %s" % (len(days), OUT_DIR), flush=True)
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
    print("[dualsrclob] DONE in %.1f min: built=%d skip=%d fail=%d%s -> %s"
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

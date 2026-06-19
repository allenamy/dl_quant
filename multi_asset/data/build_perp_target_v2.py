"""Build the CORRECT leak-free, builder-caliber PERP y_600 target — v2.

WHY THIS FILE EXISTS (and what the two prior versions got wrong)
---------------------------------------------------------------
We train a model on SPOT order-flow features (``data/npz_spot``) to predict the
BTC **PERP** 10-min forward return. The target must be the *perp* return measured
at the *spot prediction second* ``s`` (the feature cutoff), so it is both
LEAK-FREE and matches the exact mid/resampling caliber the feature builder uses.
Two earlier targets each violated one requirement:

  * ``data/npz_spot2perp``         (LEAKED)        — position-joined perp windows
    onto spot windows guarding only |perp_ts - spot_ts| <= 10s, NOT the sign. On
    ~61% of windows perp_ts < s, so the perp return window [perp_ts, perp_ts+600]
    starts BEFORE the feature cutoff -> a lookahead leak. (Spot-model q50 scores
    an inflated 0.0166 against it precisely because the leaked prefix is partly
    predictable.)
  * ``data/npz_spot2perp_clean``   (RE-ANCHORED)   — re-anchored the perp return
    to start exactly at ``s`` using ``data/mid_cache/<day>.npz`` ``perp_mid``.

THE BUILDER CALIBER WE REPLICATE (proven, exact)
------------------------------------------------
The frozen feature/label pipeline (``src.features.pipeline.build_npz_for_day`` +
``src.features.microstructure.compute_microstructure_features`` +
``src.features.resample.resample_lob_to_1s``) defines, per UTC calendar day with
a cold start at 00:00 UTC:

  * MID            ``mid = (bids[0].price + asks[0].price) / 2``  (top-of-book
                   midpoint), guarded ``max(mid, 1e-10)``. NOT microprice.
  * RESAMPLE TO 1s last-tick-per-second: floor each tick ts to the second
                   (truncate, never round), keep the LAST tick in each 1s bucket,
                   build a complete 1s grid from first->last second, FORWARD-FILL
                   gaps (causal). Rows are then stripped to [00:00, 24:00) UTC.
  * y_600          ``log( mid[s + 600] / mid[s] )`` where ``s`` is the prediction
                   second and ``s + 600`` is +600 ROWS on the contiguous 1s grid
                   (== +600 s). In-day only (mask=0 when ``s+600`` overflows the
                   grid / next-day stitch is unavailable).

This builder applies that EXACT recipe to the caliber-correct PERP high-precision
book (``binance-futures``, the same root the perp feature builders read) and then
anchors the forward return at the SPOT prediction second ``s`` taken from
``data/npz_spot/<day>.npz`` ``timestamps`` (microseconds; ``s = ts // 1e6``).
The perp 1s mid is read THROUGH the frozen pipeline path
(``build_regarch_perp_npz._resample_strip_day`` -> ``compute_microstructure_features``)
so the mid + resampling are byte-identical to the perp feature builder, not an
approximation.

VERIFIED EQUIVALENCE (this session)
-----------------------------------
On every spot day tested, this builder's perp mid is byte-identical to
``mid_cache.perp_mid`` (corr 1.000000, median |Δ|=0.0 bps, frac-equal 1.0) and the
resulting y_600 is byte-identical to ``npz_spot2perp_clean`` (per-day corr
1.00000). So ``npz_spot2perp_clean`` was ALREADY correct caliber + leak-free; v2
reproduces it directly from the perp Tardis book (no ``mid_cache`` dependency,
hence extensible to the full 2023-01..2026-05 period, whereas ``mid_cache`` only
covers 2024-06+).  The proven spot-model q50 transfer to this target is the HONEST
choppy-2026 number (~0.008 dense), NOT ~0.024 — the gap vs spot_y (~0.022) is a
real property of the spot->perp problem (the tiny perp-minus-spot basis residual,
~4% of variance, is negatively correlated with the weak q50), confirmed
model-independently by Ridge. See /tmp/perp_target_v2.md for the full diagnosis.

LEAK SAFETY
-----------
The target window starts EXACTLY at ``s`` (offset 0 by construction) and looks
600s FORWARD; no second < ``s`` is ever touched for the label. ``--validate``
re-runs a future-perturbation check (corrupt all perp book/trade rows strictly
after a cut second; the label legs at-or-before the cut are byte-identical).

CROSS-DAY TAIL
--------------
The last ~0.6% of windows per day have ``s`` near 23:5x so ``s + 600`` overflows
into the next UTC calendar day. We STITCH the next calendar day's perp 1s mid onto
today's grid when present; tail windows whose forward second is still missing
(span end / source gap) are left INVALID in ``y_mask_600`` — never filled.

OUTPUT (NEW DIR — nothing existing is touched). LEAN: only the target.
----------------------------------------------------------------------
  data/npz_perp_target_v2/<YYYY-MM-DD>.npz  with keys:
      y_600        (N,)  float32  PERP fwd log-return anchored at spot second s
                                  (NaN where invalid; eval masks on y_mask_600)
      y_mask_600   (N,)  bool     spot's own y_mask_600 AND both perp legs present
      timestamps   (N,)  int64    SPOT pred-idx us (== npz_spot timestamps; the
                                  authoritative join key — row-for-row with the
                                  spot feature cache)
  plus build_meta.json at the cache root.

CPU-only. READ-ONLY over the perp Tardis source and over data/npz_spot.

Usage
-----
  # smoke / leak gate on a few days (force rebuild):
  python multi_asset/data/build_perp_target_v2.py --validate 2026-01-15 2025-02-10
  # build a subset:
  python multi_asset/data/build_perp_target_v2.py --days 2026-01-15 2026-01-16
  # build all spot days (skip existing); detached:
  setsid nohup nice -n 10 python multi_asset/data/build_perp_target_v2.py --all \
      > /tmp/perp_target_v2_build.log 2>&1 < /dev/null &
  # restrict to a window:
  python multi_asset/data/build_perp_target_v2.py --all --start 2024-06-01 --end 2026-05-31
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import os.path as p
import sys
import time
import warnings

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
sys.path.insert(0, _REPO)

# Frozen production mid/resample path — IMPORTED UNCHANGED. ``_resample_strip_day``
# reads the caliber-correct PERP book (binance-futures) and resamples it to the 1s
# last-tick grid stripped to [00:00,24:00) UTC, EXACTLY as the perp feature builder
# does; ``compute_microstructure_features`` then defines ``mid_price`` ==
# (bids[0]+asks[0])/2 — the identical mid the label uses in build_npz_for_day.
from multi_asset.data.build_regarch_perp_npz import _resample_strip_day  # noqa: E402
from src.features.microstructure import compute_microstructure_features  # noqa: E402

US_PER_SEC = 1_000_000
HORIZON_SEC = 600

# Spot feature cache supplies the authoritative window grid + prediction seconds.
SPOT_NPZ_DIR = p.join(_REPO, "data", "npz_spot")
OUT_DIR = p.join(_REPO, "data", "npz_perp_target_v2")


# --------------------------------------------------------------------------- #
# builder-caliber perp 1s mid for one UTC calendar day (cached across calls)
# --------------------------------------------------------------------------- #
def perp_mid_1s(date_str: str) -> tuple[np.ndarray, np.ndarray]:
    """Return (sec, mid) for one UTC calendar day, builder-caliber.

    ``sec`` is the contiguous unix-second grid (int64); ``mid`` is the top-of-book
    midpoint on the frozen 1s last-tick+ffill grid. Identical to what the perp
    feature builder computes for its labels. Raises on missing/short days.
    """
    df_1s, _ = _resample_strip_day(date_str)               # frozen perp resample
    feat = compute_microstructure_features(df_1s, n_levels=25)  # defines mid_price
    sec = (feat["timestamp"].to_numpy(np.int64) // US_PER_SEC)
    mid = feat["mid_price"].to_numpy(np.float64)
    if sec.size and not np.all(np.diff(sec) == 1):
        # The frozen resampler builds a complete 1s grid, so this should not trip;
        # if a day is pathological we refuse it rather than mis-anchor +600 rows.
        raise RuntimeError(f"{date_str}: perp 1s grid not contiguous after resample")
    return sec, mid


class MidCache:
    """LRU of the most recent K calendar-day perp mids. Consecutive spot days
    share their cross-day tail's next-day mid, so a tiny cache avoids re-reading
    the same perp book twice in a sequential build."""

    def __init__(self, k: int = 3):
        self.k = k
        self._d: "dict[str, tuple[np.ndarray, np.ndarray]]" = {}
        self._order: list[str] = []

    def get(self, date_str: str) -> tuple[np.ndarray, np.ndarray]:
        if date_str in self._d:
            self._order.remove(date_str)
            self._order.append(date_str)
            return self._d[date_str]
        if len(self._order) >= self.k:
            old = self._order.pop(0)
            self._d.pop(old, None)
        v = perp_mid_1s(date_str)
        self._d[date_str] = v
        self._order.append(date_str)
        return v


def _next_day(date_str: str) -> str:
    return (dt.date.fromisoformat(date_str) + dt.timedelta(days=1)).isoformat()


def _stitched_perp_mid(date_str: str, cache: "MidCache | None" = None
                       ) -> tuple[np.ndarray, np.ndarray]:
    """Today's perp 1s mid with the next calendar day's mid appended, so the
    cross-day ``s + 600`` tail can resolve. If the next day is absent, only
    today's grid is returned (tail windows stay invalid)."""
    get = (cache.get if cache is not None else perp_mid_1s)
    sec0, mid0 = get(date_str)
    try:
        sec1, mid1 = get(_next_day(date_str))
    except (FileNotFoundError, ValueError, RuntimeError):
        return sec0, mid0
    keep = sec1 > sec0[-1]
    if not keep.any():
        return sec0, mid0
    return np.concatenate([sec0, sec1[keep]]), np.concatenate([mid0, mid1[keep]])


# --------------------------------------------------------------------------- #
# core anchor (pure)
# --------------------------------------------------------------------------- #
def anchor_y600(spot_ts_us, sec, perp_mid, horizon: int = HORIZON_SEC):
    """Perp forward log-return anchored at the spot prediction second.

    Parameters
    ----------
    spot_ts_us : (N,) int64  spot window prediction timestamps, MICROSECONDS.
    sec        : (T,) int64  contiguous unix-second grid (today [+ next day]).
    perp_mid   : (T,) float  builder-caliber perp top-of-book mid aligned to sec.
    horizon    : int         forward horizon in seconds (600).

    Returns
    -------
    y    : (N,) float64  log(perp_mid[s+H] / perp_mid[s]); NaN where either second
           is missing from the grid or the price is non-positive.
    leg_valid : (N,) bool  True iff both legs present & > 0 (y finite).

    The target window starts at ``s`` (the feature cutoff, offset 0) and ends at
    ``s + horizon`` — strictly forward. No second < ``s`` is read. Lookups use an
    EXACT-second match (searchsorted + equality), so a missing second yields NaN,
    never a nearest-neighbour wrong price.
    """
    s = np.asarray(spot_ts_us, dtype=np.int64) // US_PER_SEC
    sec = np.asarray(sec, dtype=np.int64)
    perp_mid = np.asarray(perp_mid, dtype=np.float64)
    s_fwd = s + horizon

    def _lookup(target_sec):
        pos = np.searchsorted(sec, target_sec, side="left")
        n = sec.size
        pos_c = np.clip(pos, 0, max(n - 1, 0))
        hit = (pos < n) & (n > 0) & (sec[pos_c] == target_sec)
        v = np.full(target_sec.shape, np.nan, dtype=np.float64)
        v[hit] = perp_mid[pos_c[hit]]
        return v

    mid_s = _lookup(s)
    mid_fwd = _lookup(s_fwd)
    with np.errstate(invalid="ignore", divide="ignore"):
        good = (np.isfinite(mid_s) & np.isfinite(mid_fwd)
                & (mid_s > 0) & (mid_fwd > 0))
        y = np.full(s.shape, np.nan, dtype=np.float64)
        y[good] = np.log(mid_fwd[good] / mid_s[good])
    return y, np.isfinite(y)


# --------------------------------------------------------------------------- #
# per-day build
# --------------------------------------------------------------------------- #
def build_one_day(date_str: str, out_path: str,
                  cache: "MidCache | None" = None) -> dict:
    """Build + atomically write data/npz_perp_target_v2/<day>.npz for one day."""
    t0 = time.time()
    spot_npz = p.join(SPOT_NPZ_DIR, f"{date_str}.npz")
    if not p.exists(spot_npz):
        raise FileNotFoundError(f"spot cache missing: {spot_npz}")
    with np.load(spot_npz, allow_pickle=True) as zs:
        spot_ts = zs["timestamps"].astype(np.int64)
        spot_mask = zs["y_mask_600"].astype(bool)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sec, perp_mid = _stitched_perp_mid(date_str, cache)

    y, leg_valid = anchor_y600(spot_ts, sec, perp_mid)
    y_mask = spot_mask & leg_valid                  # both spot-valid AND perp legs
    y_600 = y.astype(np.float32)

    N = spot_ts.shape[0]
    if not (y_600.shape[0] == N and y_mask.shape[0] == N):
        raise RuntimeError(f"{date_str}: row count mismatch (N={N})")

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = f"{out_path}.tmp.{os.getpid()}.npz"
    np.savez_compressed(
        tmp,
        y_600=y_600,                # re-anchored perp fwd return (leak-free)
        y_mask_600=y_mask,          # valid where spot mask AND both perp legs
        timestamps=spot_ts,         # SPOT pred grid (authoritative join key)
    )
    os.replace(tmp, out_path)

    n_valid = int(y_mask.sum())
    n_tail_lost = int((spot_mask & ~leg_valid).sum())
    yv = y[y_mask]
    return {
        "N": int(N), "n_valid": n_valid,
        "valid_frac": n_valid / max(N, 1),
        "n_tail_lost": n_tail_lost,
        "y_bps_std": float(np.std(yv) * 1e4) if yv.size else float("nan"),
        "secs": time.time() - t0,
        "mb": os.path.getsize(out_path) / 1e6,
    }


# --------------------------------------------------------------------------- #
# day listing + driver
# --------------------------------------------------------------------------- #
def list_spot_days(start: "str | None" = None, end: "str | None" = None
                   ) -> list[str]:
    """All YYYY-MM-DD days present in data/npz_spot (optionally within [start,end])."""
    if not p.isdir(SPOT_NPZ_DIR):
        raise FileNotFoundError(f"spot cache dir not found: {SPOT_NPZ_DIR}")
    out = []
    for name in os.listdir(SPOT_NPZ_DIR):
        if not (len(name) == 14 and name.endswith(".npz")):
            continue
        day = name[:-4]
        try:
            dt.date.fromisoformat(day)
        except ValueError:
            continue
        if start is not None and day < start:
            continue
        if end is not None and day > end:
            continue
        out.append(day)
    return sorted(out)


def _write_meta(days, n_done, n_skip, n_fail, failed_days, leak_max_dev=None):
    meta = {
        "purpose": ("CORRECT leak-free, builder-caliber PERP y_600 target: perp "
                    "forward 600s log-return anchored at the SPOT prediction "
                    "second s, using the frozen feature builder's mid "
                    "((bids0+asks0)/2) + 1s last-tick+ffill resample on the "
                    "caliber-correct PERP (binance-futures) high-precision book."),
        "join_key": ("timestamps == data/npz_spot timestamps (microseconds); "
                     "row-for-row with the spot feature cache"),
        "mid_definition": "(bids[0].price + asks[0].price) / 2  (top-of-book midpoint)",
        "resample": ("1s last-tick-per-second, floor ts to second, complete 1s "
                     "grid first->last, forward-fill gaps, strip to [00:00,24:00) "
                     "UTC — src.features.resample.resample_lob_to_1s (UNCHANGED)"),
        "label": ("y_600 = log(perp_mid[s+600] / perp_mid[s]); future-only, "
                  "window starts at s (offset 0); cross-day tail stitched from "
                  "next calendar day, else left invalid"),
        "mid_source_path": ("multi_asset.data.build_regarch_perp_npz._resample_strip_day "
                            "(reads PERP book binance-futures) -> "
                            "src.features.microstructure.compute_microstructure_features"),
        "verified_equivalence": ("perp mid byte-identical to data/mid_cache.perp_mid "
                                 "(corr 1.000000); y_600 byte-identical to "
                                 "data/npz_spot2perp_clean (per-day corr 1.00000). "
                                 "v2 reads the perp Tardis book directly (no "
                                 "mid_cache dependency) so it extends to the full "
                                 "2023-01..2026-05 period."),
        "horizon_sec": HORIZON_SEC,
        "n_days_listed": len(days), "n_days_built": n_done,
        "n_days_skipped": n_skip, "n_days_failed": n_fail,
        "failed_days": failed_days,
        "npz_keys": {
            "y_600": "(N,) float32 perp fwd log-return anchored at spot second s (NaN if invalid)",
            "y_mask_600": "(N,) bool  spot y_mask_600 AND both perp legs present",
            "timestamps": "(N,) int64 SPOT pred-idx us (== npz_spot timestamps)",
        },
        "leak_check_max_dev_future_perturb": leak_max_dev,
    }
    with open(p.join(OUT_DIR, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


def build(days_subset=None, force=False, start=None, end=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset if days_subset else list_spot_days(start, end)
    print(f"[perp_target_v2] {len(days)} day(s) -> {OUT_DIR}", flush=True)
    t0 = time.time()
    n_done = n_skip = n_fail = 0
    failed = []
    cache = MidCache(k=3)
    for i, d in enumerate(days):
        out = p.join(OUT_DIR, f"{d}.npz")
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            st = build_one_day(d, out, cache)
        except Exception as e:
            n_fail += 1
            failed.append((d, f"{type(e).__name__}: {e}"))
            print(f"  [warn] day {d} failed: {type(e).__name__}: {e}", flush=True)
            continue
        n_done += 1
        if n_done % 25 == 0 or i == len(days) - 1:
            el = time.time() - t0
            rate = n_done / el if el > 0 else 0
            eta = (len(days) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1:4d}/{len(days)}] {d} N={st['N']} valid={st['n_valid']} "
                  f"({100*st['valid_frac']:.1f}%) tail_lost={st['n_tail_lost']} "
                  f"y_std={st['y_bps_std']:.2f}bps  built={n_done} skip={n_skip} "
                  f"fail={n_fail}  {el/60:.1f}min ~{rate*60:.1f}day/min "
                  f"ETA {eta/60:.1f}min", flush=True)
    _write_meta(days, n_done, n_skip, n_fail, [d for d, _ in failed])
    print(f"[perp_target_v2] DONE in {(time.time()-t0)/60:.1f} min: built={n_done} "
          f"skip={n_skip} fail={n_fail} -> {OUT_DIR}", flush=True)
    if failed:
        print(f"  FAILED {len(failed)} day(s):", flush=True)
        for d, why in failed[:40]:
            print(f"    {d}  {why}", flush=True)
    return n_fail


# --------------------------------------------------------------------------- #
# gates
# --------------------------------------------------------------------------- #
def _gate_smoke(date_str: str, st: dict) -> bool:
    ok_valid = st["n_valid"] > 0 and st["valid_frac"] > 0.95
    ok_y = (np.isfinite(st["y_bps_std"]) and 1.0 < st["y_bps_std"] < 500.0)
    ok = ok_valid and ok_y
    print(f"  [SMOKE {date_str}] N={st['N']} valid={st['n_valid']} "
          f"({100*st['valid_frac']:.2f}%) tail_lost={st['n_tail_lost']} "
          f"y_std={st['y_bps_std']:.2f}bps -> {'PASS' if ok else 'FAIL'}",
          flush=True)
    return bool(ok)


def _gate_equiv(date_str: str, out_path: str) -> bool:
    """Equivalence to the prior re-anchored target (data/npz_spot2perp_clean):
    on shared timestamps + masks, y_600 must be byte-identical (corr 1.0). This
    proves v2 reproduces the correct caliber. SKIP (not FAIL) if absent."""
    clean_path = p.join(_REPO, "data", "npz_spot2perp_clean", f"{date_str}.npz")
    if not p.exists(clean_path):
        print(f"  [GATE equiv {date_str}] SKIP: no npz_spot2perp_clean day",
              flush=True)
        return True
    with np.load(out_path, allow_pickle=True) as zn, \
            np.load(clean_path, allow_pickle=True) as zc:
        tn = zn["timestamps"].astype(np.int64); tc = zc["timestamps"].astype(np.int64)
        yn = zn["y_600"].astype(np.float64); yc = zc["y_600"].astype(np.float64)
        mn = zn["y_mask_600"].astype(bool); mc = zc["y_mask_600"].astype(bool)
    if not np.array_equal(tn, tc):
        print(f"  [GATE equiv {date_str}] FAIL: timestamps differ", flush=True)
        return False
    both = mn & mc & np.isfinite(yn) & np.isfinite(yc)
    if both.sum() < 20:
        print(f"  [GATE equiv {date_str}] SKIP: <20 shared valid rows", flush=True)
        return True
    corr = float(np.corrcoef(yn[both], yc[both])[0, 1])
    max_abs = float(np.max(np.abs(yn[both] - yc[both])))
    ok = corr > 0.99999 and max_abs < 1e-7
    print(f"  [GATE equiv {date_str}] vs npz_spot2perp_clean: corr={corr:.6f} "
          f"max|Δ|={max_abs:.2e} n={int(both.sum())} -> "
          f"{'PASS (byte-identical caliber)' if ok else 'FAIL'}", flush=True)
    return bool(ok)


def _gate_leak(date_str: str) -> tuple[bool, float]:
    """Leak check by future perturbation. Build the perp mid normally; then
    corrupt every perp book row STRICTLY AFTER a cut second, rebuild the mid, and
    assert every label leg whose own/forward second <= cut is byte-identical.

    The forward leg at s+600 is allowed to move if s+600 > cut (that is the
    legitimate future); we restrict the comparison to legs fully at-or-before the
    cut, which a causal target must leave untouched."""
    df_1s, _ = _resample_strip_day(date_str)

    def _mid(dfb):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            feat = compute_microstructure_features(dfb, n_levels=25)
        return ((feat["timestamp"].to_numpy(np.int64) // US_PER_SEC),
                feat["mid_price"].to_numpy(np.float64))

    sec0, mid0 = _mid(df_1s)
    cut_i = int(0.7 * len(df_1s))
    cut_sec = int(df_1s["timestamp"].iloc[cut_i] // US_PER_SEC)
    dfb = df_1s.copy()
    fut = dfb.index > cut_i
    rng = np.random.default_rng(20260618)
    nfut = int(fut.sum())
    for c in [c for c in dfb.columns if c.endswith(".price")]:
        dfb.loc[fut, c] = dfb.loc[fut, c].to_numpy() * (1.0 + rng.uniform(-0.5, 0.5, nfut))
    for c in [c for c in dfb.columns if c.endswith(".amount")]:
        dfb.loc[fut, c] = rng.uniform(1e3, 1e5, nfut)
    sec1, mid1 = _mid(dfb)
    if not np.array_equal(sec0, sec1):
        print(f"  [GATE leak {date_str}] FAIL: grid changed under perturbation",
              flush=True)
        return False, float("nan")
    # mids at seconds <= cut must be byte-identical (those are the only seconds a
    # causal label leg can read for any window with s <= cut and s+600 <= cut).
    le = sec0 <= cut_sec
    d = np.abs(mid0[le] - mid1[le])
    mx = float(np.max(d)) if d.size else 0.0
    ok = mx < 1e-6
    print(f"  [GATE leak {date_str}] future-perturb (cut sec={cut_sec}, "
          f"{int(le.sum())} causal seconds <= cut): max|Δmid|={mx:.3e} -> "
          f"{'PASS (causal, ~0)' if ok else 'FAIL'}", flush=True)
    return ok, mx


def validate(days: list[str]):
    os.makedirs(OUT_DIR, exist_ok=True)
    gates = {"smoke": True, "equiv": True, "leak": True}
    leak_max = 0.0
    cache = MidCache(k=3)
    for d in days:
        out = p.join(OUT_DIR, f"{d}.npz")
        st = build_one_day(d, out, cache)            # force rebuild
        print(f"\n========= day {d}: {st['mb']:.3f} MB in {st['secs']:.1f}s "
              f"=========", flush=True)
        gates["smoke"] &= _gate_smoke(d, st)
        gates["equiv"] &= _gate_equiv(d, out)
        ok_leak, mx = _gate_leak(d)
        gates["leak"] &= ok_leak
        leak_max = max(leak_max, mx if np.isfinite(mx) else 0.0)
    _write_meta(days, len(days), 0, 0, [], leak_max_dev=leak_max)
    print("\n[validate] " + "  ".join(
        f"GATE_{g}={'PASS' if ok else 'FAIL'}" for g, ok in gates.items())
        + f"  leak_max_dev={leak_max:.2e}", flush=True)
    if not all(gates.values()):
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every spot day (skip existing)")
    g.add_argument("--days", type=str, nargs="+",
                   help="build only these YYYY-MM-DD days")
    g.add_argument("--validate", type=str, nargs="+",
                   help="force-build + smoke/equiv/leak gates on these days")
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    ap.add_argument("--start", type=str, default=None,
                    help="restrict --all to days >= START (YYYY-MM-DD)")
    ap.add_argument("--end", type=str, default=None,
                    help="restrict --all to days <= END (YYYY-MM-DD)")
    args = ap.parse_args()
    if args.validate:
        validate(args.validate)
    else:
        build(days_subset=args.days, force=args.force, start=args.start, end=args.end)

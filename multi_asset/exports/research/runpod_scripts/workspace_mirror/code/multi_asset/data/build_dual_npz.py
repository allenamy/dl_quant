"""Build the DUAL-SOURCE single-asset NPZ cache (Task A1).

GOAL
----
Produce, per UTC calendar day, a training NPZ that carries the EXISTING perp
feature/target contract (identical to ``data/npz_perp``: X (N,600,64),
X_raw=perp 20-level raw LOB (N,600,20,4), regime_prior (N,6), y_600 on the PERP
mid, y_mask_600, timestamps in us) PLUS a NEW key ``X_raw_spot`` (N,600,20,4):
the SPOT 20-level raw order book aligned to the SAME window timestamps as the
perp grid. A later model fuses perp + spot microstructure; the target stays the
PERP y_600 and the perp windowing/timestamps are authoritative.

WHY THIS DESIGN (and why self-contained)
----------------------------------------
The frozen perp pipeline (src.features.pipeline.build_npz_for_day +
src.features.resample.resample_lob_to_1s + src.features.raw_lob) already
produced ``data/npz_perp/<day>.npz`` for the corrected-PERP period. This builder
treats that cache as the AUTHORITATIVE perp contract: X / regime_prior / y_* /
timestamps are copied from it verbatim. The ONLY new content is X_raw_spot,
which is the spot book run through the SAME raw-LOB extraction routine as perp
X_raw, then aligned second-for-second onto the perp window grid.

To stay faithful AND avoid touching the read-only src/ tree, the two pure
functions the raw path needs — the 1s resampler and the raw-LOB tensor
extractor — are VENDORED here verbatim from src/features/resample.py and
src/features/raw_lob.py (byte-for-byte logic). The vendored perp path is
cross-checked against the cached perp X_raw (assert byte-identical) so we PROVE
the spot raw is produced by exactly the same routine that built perp X_raw —
the two are directly comparable, as required.

NO LEAKAGE
----------
The perp window grid is re-derived by resampling the PERP book to 1s and
stripping to [00:00, 24:00) UTC (identical to the perp builder). Each window
occupies contiguous 1s seconds [pred_sec-599 .. pred_sec]. The SPOT book is
resampled the same way; spot raw at each perp second is the spot snapshot whose
floored-second is exactly that perp second, found via
``np.searchsorted(spot_seconds, perp_seconds, side="right") - 1`` and then
HARD-ASSERTED to equal the perp second (no forward-fill of a perp t+delta onto
spot t; exact match only). Per day we also assert the reconstructed perp window
grid equals the cached perp grid (same N, same pred-idx timestamps) and that the
reconstructed perp X_raw is byte-identical to the cache.

OUTPUT (NEW DIR — nothing existing is touched)
----------------------------------------------
  data/npz_dual/<YYYY-MM-DD>.npz  with keys:
      X            float32 (N,600,64)     copied from data/npz_perp
      X_raw        float16 (N,600,20,4)   perp raw LOB, copied from data/npz_perp
      X_raw_spot   float16 (N,600,20,4)   NEW — spot raw LOB at perp window seconds
      regime_prior float32 (N,6)          copied from data/npz_perp
      y_600        float32 (N,)           PERP mid forward log-return (copied)
      y_mask_600   uint8   (N,)           copied
      timestamps   int64   (N,)           pred-idx timestamp (us), copied

CLI
---
  python multi_asset/data/build_dual_npz.py --days 2025-02-10 2025-02-11
  python multi_asset/data/build_dual_npz.py --all          # skip existing
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
PERP_VENUE = "binance-futures"
SPOT_VENUE = "binance"
PERP_NPZ_DIR = p.join(_REPO, "data", "npz_perp")              # authoritative perp
OUT_DIR = p.join(_REPO, "data", "npz_dual")

N_LVL = 25            # book levels read from source
N_RAW = 20            # raw-LOB tensor levels (min(25,20)); matches perp X_raw
INPUT_LEN = 600
STRIDE = 180          # matches data/npz_perp build_meta (input_len=600/stride=180)

PERIOD_START = dt.date(2023, 1, 1)
PERIOD_END = dt.date(2026, 5, 31)

# book columns the resampler consumes (timestamp + 25 levels both sides)
_BOOK_COLS = ["timestamp"]
for _i in range(N_LVL):
    _BOOK_COLS += [f"asks[{_i}].price", f"asks[{_i}].amount",
                   f"bids[{_i}].price", f"bids[{_i}].amount"]


# ----------------------------------------------------------- vendored readers
def _read_gz_csv_robust(path, usecols=None):
    """gzip CSV reader robust to truncated streams — VENDORED verbatim from
    multi_asset.data.build_btc_feat64_perp._read_gz_csv_robust."""
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


def _read_book_day(date_str, venue):
    path = p.join(BOOK_ROOT, date_str, venue, "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    return _read_gz_csv_robust(path, usecols=_BOOK_COLS)


# ------------------------------------------- vendored resampler (src.features)
def _resample_lob_to_1s(df, n_levels=25, ts_col="timestamp"):
    """1s last-tick-per-second resampler — VENDORED verbatim (logic) from
    src.features.resample.resample_lob_to_1s. Floors timestamps to the second
    (no rounding -> no look-ahead), keeps last tick per second, builds a
    complete 1s grid, forward-fills (causal), drops leading no-top-of-book rows,
    pads deeper NaN levels."""
    lob_cols = []
    for i in range(n_levels):
        for side in ("asks", "bids"):
            for field in ("price", "amount"):
                col = "%s[%d].%s" % (side, i, field)
                if col in df.columns:
                    lob_cols.append(col)
    if not lob_cols:
        raise ValueError("No LOB columns found in DataFrame")

    work = df[[ts_col] + lob_cols].copy()
    us_per_sec = 1_000_000
    work["_ts_sec"] = (work[ts_col] // us_per_sec) * us_per_sec
    work.sort_values(ts_col, inplace=True)
    last_per_sec = work.groupby("_ts_sec", sort=True).last().reset_index()

    ts_min = last_per_sec["_ts_sec"].iloc[0]
    ts_max = last_per_sec["_ts_sec"].iloc[-1]
    full_grid = pd.DataFrame(
        {"_ts_sec": np.arange(ts_min, ts_max + us_per_sec, us_per_sec)})
    merged = full_grid.merge(last_per_sec.drop(columns=[ts_col]),
                             on="_ts_sec", how="left")
    merged.sort_values("_ts_sec", inplace=True)
    merged[lob_cols] = merged[lob_cols].ffill()

    top_cols = [c for c in ("asks[0].price", "asks[0].amount",
                            "bids[0].price", "bids[0].amount")
                if c in lob_cols]
    merged.dropna(subset=top_cols, how="any", inplace=True)

    if len(merged) > 0:
        best_ask = merged["asks[0].price"] if "asks[0].price" in merged else None
        best_bid = merged["bids[0].price"] if "bids[0].price" in merged else None
        for col in lob_cols:
            if col in top_cols:
                continue
            if col.endswith(".amount"):
                merged[col] = merged[col].fillna(0.0)
            elif (col.endswith(".price") and best_ask is not None
                  and best_bid is not None):
                side_default = best_ask if col.startswith("asks[") else best_bid
                merged[col] = merged[col].fillna(side_default)
            else:
                merged[col] = merged[col].fillna(0.0)

    merged.reset_index(drop=True, inplace=True)
    merged.rename(columns={"_ts_sec": ts_col}, inplace=True)
    return merged


# ------------------------------------- vendored raw-LOB tensor (src.features)
def _extract_raw_lob_tensor(df_1s, n_levels=20):
    """Raw LOB tensor (N, n_levels, 4) — VENDORED verbatim (logic) from
    src.features.raw_lob.extract_raw_lob_tensor. Channels:
    [bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt]; strictly per-row
    causal. Identical normalization to how perp X_raw was produced."""
    bid_prices = np.column_stack(
        [df_1s["bids[%d].price" % i].values for i in range(n_levels)]
    ).astype(np.float64)
    ask_prices = np.column_stack(
        [df_1s["asks[%d].price" % i].values for i in range(n_levels)]
    ).astype(np.float64)
    bid_amounts = np.column_stack(
        [df_1s["bids[%d].amount" % i].values for i in range(n_levels)]
    ).astype(np.float64)
    ask_amounts = np.column_stack(
        [df_1s["asks[%d].amount" % i].values for i in range(n_levels)]
    ).astype(np.float64)

    mid = (bid_prices[:, 0] + ask_prices[:, 0]) / 2.0
    mid = np.where(mid == 0.0, 1.0, mid)
    mid_col = mid[:, np.newaxis]
    bid_delta_bps = (bid_prices - mid_col) / mid_col * 10_000.0
    ask_delta_bps = (ask_prices - mid_col) / mid_col * 10_000.0

    bid_amounts = np.maximum(bid_amounts, 0.0)
    ask_amounts = np.maximum(ask_amounts, 0.0)
    bid_log_amt = np.log1p(bid_amounts)
    ask_log_amt = np.log1p(ask_amounts)

    tensor = np.stack(
        [bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt], axis=-1)
    tensor = np.nan_to_num(tensor, nan=0.0, posinf=0.0, neginf=0.0)
    return tensor.astype(np.float32)


# ----------------------------------------------- per-day grid reconstruction
def _resample_strip_day(date_str, venue):
    """Read book for one UTC day, resample to 1s, strip to [00:00,24:00) UTC —
    identical preprocessing to build_regarch_perp_npz._resample_strip_day."""
    raw_book = _read_book_day(date_str, venue)
    df_1s = _resample_lob_to_1s(raw_book, n_levels=N_LVL)
    del raw_book
    day_start_us = int(pd.Timestamp(date_str, tz="UTC").timestamp() * 1_000_000)
    day_end_us = day_start_us + 86_400 * 1_000_000
    df_1s = df_1s[(df_1s["timestamp"] >= day_start_us)
                  & (df_1s["timestamp"] < day_end_us)].reset_index(drop=True)
    if len(df_1s) < INPUT_LEN:
        raise ValueError("%s: only %d 1s rows (< input_len) for %s"
                         % (date_str, len(df_1s), venue))
    return df_1s


def _window_starts(n_total):
    return list(range(0, n_total - INPUT_LEN + 1, STRIDE))


# --------------------------------------------------------------------- build
def build_one_day(date_str, out_path):
    """Build + atomically write data/npz_dual/<day>.npz for one UTC day."""
    t0 = time.time()

    # 1) authoritative perp arrays from the frozen-pipeline cache
    perp_npz = p.join(PERP_NPZ_DIR, "%s.npz" % date_str)
    if not p.exists(perp_npz):
        raise FileNotFoundError(
            "perp cache missing: %s (build data/npz_perp for this day first)"
            % perp_npz)
    with np.load(perp_npz, allow_pickle=True) as zp:
        X = zp["X"]
        X_raw = zp["X_raw"]                      # perp raw LOB (N,600,20,4) f16
        regime_prior = zp["regime_prior"]
        y_600 = zp["y_600"]
        y_mask_600 = zp["y_mask_600"]
        ts = zp["timestamps"].astype(np.int64)   # pred-idx us
    N = X.shape[0]

    # 2) re-derive the PERP window grid (to align spot) and CROSS-CHECK it
    #    reproduces the cached perp arrays exactly.
    df_perp = _resample_strip_day(date_str, PERP_VENUE)
    perp_sec_all = (df_perp["timestamp"].to_numpy(np.int64) // 1_000_000)
    starts = _window_starts(len(df_perp))
    pred_idx = np.array([s + INPUT_LEN - 1 for s in starts], dtype=np.int64)
    recon_ts = df_perp["timestamp"].to_numpy(np.int64)[pred_idx]
    if len(recon_ts) != N or not np.array_equal(recon_ts, ts):
        raise RuntimeError(
            "%s: reconstructed perp window grid (N=%d) does not match cached "
            "perp grid (N=%d) -- resample drift; refusing to emit"
            % (date_str, len(recon_ts), N))
    # verify vendored raw path reproduces cached perp X_raw byte-identically
    perp_raw_full = _extract_raw_lob_tensor(df_perp, n_levels=N_RAW)
    perp_raw_win = np.stack(
        [perp_raw_full[s:s + INPUT_LEN] for s in starts]).astype(np.float16)
    if not np.array_equal(perp_raw_win, X_raw):
        d = float(np.max(np.abs(perp_raw_win.astype(np.float32)
                                - X_raw.astype(np.float32))))
        raise RuntimeError(
            "%s: vendored perp raw-LOB != cached perp X_raw (max|dev|=%.3e); "
            "vendored routine is not faithful, refusing to emit" % (date_str, d))

    # 3) SPOT raw LOB aligned to the perp window seconds (exact-second join)
    df_spot = _resample_strip_day(date_str, SPOT_VENUE)
    spot_sec = (df_spot["timestamp"].to_numpy(np.int64) // 1_000_000)
    spot_raw_full = _extract_raw_lob_tensor(df_spot, n_levels=N_RAW)  # (Ns,20,4)
    # exact-timestamp cross-venue join: <= t, then assert equality (no drift)
    j = np.searchsorted(spot_sec, perp_sec_all, side="right") - 1
    if j.min() < 0:
        raise RuntimeError(
            "%s: some perp seconds precede the first spot second (no <=t match)"
            % date_str)
    matched_spot_sec = spot_sec[j]
    max_dev = int(np.max(np.abs(matched_spot_sec - perp_sec_all)))
    if max_dev != 0:
        raise RuntimeError(
            "%s: spot-perp second alignment drift max=%d (must be 0; exact "
            "same-second match required, no forward-fill of perp t+delta)"
            % (date_str, max_dev))
    spot_raw_aligned = spot_raw_full[j]            # (n_perp_sec, 20, 4) at perp secs
    # slice the SAME window starts as perp -> (N,600,20,4), quantize like perp
    X_raw_spot = np.stack(
        [spot_raw_aligned[s:s + INPUT_LEN] for s in starts]).astype(np.float16)
    if X_raw_spot.shape != X_raw.shape:
        raise RuntimeError("%s: X_raw_spot shape %s != X_raw shape %s"
                           % (date_str, X_raw_spot.shape, X_raw.shape))

    # 4) atomic write
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = "%s.tmp.%d.npz" % (out_path, os.getpid())
    np.savez_compressed(
        tmp, X=X, X_raw=X_raw, X_raw_spot=X_raw_spot,
        regime_prior=regime_prior, y_600=y_600, y_mask_600=y_mask_600,
        timestamps=ts)
    os.replace(tmp, out_path)

    fin = np.isfinite(X_raw_spot).mean()
    return {"N": int(N), "secs": time.time() - t0,
            "mb": os.path.getsize(out_path) / 1e6,
            "spot_align_max_dev_sec": max_dev, "spot_raw_finite_frac": float(fin)}


def list_days():
    """Calendar days that have BOTH a perp cache and spot+perp Tardis book."""
    if not p.isdir(PERP_NPZ_DIR):
        raise FileNotFoundError("perp cache dir not found: %s" % PERP_NPZ_DIR)
    out = []
    for name in sorted(os.listdir(PERP_NPZ_DIR)):
        if not (len(name) == 14 and name.endswith(".npz")):
            continue
        d = name[:-4]
        try:
            dt.date.fromisoformat(d)
        except ValueError:
            continue
        spot = p.join(BOOK_ROOT, d, SPOT_VENUE, "BTCUSDT.csv.gz")
        perp = p.join(BOOK_ROOT, d, PERP_VENUE, "BTCUSDT.csv.gz")
        if p.exists(spot) and p.exists(perp):
            out.append(d)
    return out


def build(days_subset=None, force=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset if days_subset else list_days()
    print("[dual] %d day(s) -> %s" % (len(days), OUT_DIR), flush=True)
    t0 = time.time(); n_done = n_skip = n_fail = 0; failed = []
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
        n_done += 1
        print("  [%d/%d] %s N=%d %.1fMB %.1fs align_dev=%d finite=%.4f"
              % (i + 1, len(days), d, st["N"], st["mb"], st["secs"],
                 st["spot_align_max_dev_sec"], st["spot_raw_finite_frac"]),
              flush=True)
    print("[dual] DONE in %.1f min: built=%d skip=%d fail=%d%s -> %s"
          % ((time.time() - t0) / 60, n_done, n_skip, n_fail,
             ("  FAILED: %s" % failed) if failed else "", OUT_DIR), flush=True)
    return n_fail


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every day with a perp cache + spot/perp book (skip existing)")
    g.add_argument("--days", type=str, nargs="+",
                   help="build only these YYYY-MM-DD days")
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    args = ap.parse_args()
    nf = build(days_subset=args.days, force=args.force)
    sys.exit(1 if nf else 0)

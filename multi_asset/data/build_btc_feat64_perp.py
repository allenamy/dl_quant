"""Build the per-day BTC "REG_arch 64-feature" cache on the CALIBER-CORRECT
PERP high-precision book + trades — the corrected twin of the F64/raw/regime
inputs that ``build_factor_leg.py`` constructs.

WHY THIS FILE EXISTS
--------------------
``build_factor_leg.py`` builds REG_arch's EXACT single-asset inputs (64 hand
features + 20-level raw-LOB tensor + 6-dim regime prior) by calling the frozen
``src.features.pipeline.build_npz_for_day`` per UTC calendar day with
``input_len=1/stride=1`` (a per-bar emitter), then running the model on the
stride-180 prediction grid. BUT its data source is the DEPRECATED, BUGGY root
``/mnt/storage/share/23-25-BTCUSDT`` whose *book* is binance SPOT while its
*trades* are PERP — a known caliber bug (spot-perp basis +5..-7.5 bps, the
documented root cause of the B25-FAIL). The corrected PERP high-precision data
(book + trades both ``binance-futures``) verified perp-book mid == bar perp
target at corr 1.000.

This builder repoints ONLY the data-source stage to the corrected PERP root and
emits, per PANEL DAY, the EXACT same 64-feature / 20-level-raw / 6-dim-regime
contract on the FULL 1s seq_cache grid (T==85800), ts-aligned ROW-FOR-ROW to
``exports/btc25_raw_perp/<day>.npz`` (and seq_cache). The feature pipeline,
the resampler, and the 64-feature axis order are IMPORTED UNCHANGED from the
frozen ``src/`` tree and from ``build_factor_leg`` — faithfulness to REG_arch's
exact input contract is the whole point; nothing is approximated or substituted.

The ONLY difference vs ``build_factor_leg.build_calendar_day``:
  * book  read from PERP ``book_snapshot_25/<date>/binance-futures/BTCUSDT.csv.gz``
  * trades read from PERP ``trades/<date>/binance-futures/BTCUSDT.csv.gz``
Everything downstream of the read (``resample_lob_to_1s`` -> ``build_npz_for_day``
with the identical kwargs, incl. ``quantize_features=True`` fp16 round-trip of
X_raw, ``nan_to_num`` + clip, the EXPECTED_FEATURES schema assert) is byte-for-
byte the production code path.

SOURCE (NEW, READ-ONLY — schema proven identical to the deprecated spot book)
-----------------------------------------------------------------------------
  book   : /mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/
           book_snapshot_25/<YYYY-MM-DD>/binance-futures/BTCUSDT.csv.gz
  trades : /mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/
           trades/<YYYY-MM-DD>/binance-futures/BTCUSDT.csv.gz
Tardis schema: book has asks[0..24].price/.amount + bids[0..24].price/.amount +
timestamp (MICROSECONDS); trades have timestamp(us), side('buy'/'sell'), price,
amount. ``resample_lob_to_1s`` consumes the book columns directly; trades are
normalised exactly like the production multi-day pipeline (amount->size,
id->exec_id, side Title-cased).

ALIGNMENT (must match build_btc25_raw_perp EXACTLY so this cache lines up
row-for-row with exports/btc25_raw_perp/<day>.npz)
------------------------------------------------------------------------
The panel trading day d (seq_cache/<d>.npz) spans UTC ~14:05 of d-1 ..
~13:54:59 of d (85800 1s bars). We build features PER UTC CALENDAR DAY with a
cold start at 00:00 UTC (identical to training / build_factor_leg), concatenate
the two calendar days [d-1, d] that the panel day overlaps, then slice onto the
seq_cache ts grid by EXACT second. Because the panel day starts 14h into the
UTC calendar day, every rolling window the 64 features use (max 3600s = 1h) is
fully warm at the first kept row — no in-day warmup loss, and the values are
bit-identical to training-era per-calendar-day features. ``ts`` is hard-asserted
byte-identical to seq_cache/<day>.npz (== btc25_raw_perp/<day>.npz).

OUTPUT (NEW DIR — nothing else is touched)
------------------------------------------
  <OUT_DIR=exports/btc_feat64_perp>/<day>.npz
      ts   (T,)        int64    ns, IDENTICAL to seq_cache & btc25_raw_perp ts
      F64  (T, 64)     float16  the 64 hand features, EXACT EXPECTED_FEATURES order
      R20  (T, 20, 4)  float16  20-level raw LOB tensor (bid_off, bid_logamt,
                                ask_off, ask_logamt) — build_npz_for_day's X_raw
      RP   (T, 6)      float16  6-dim regime prior (build_npz_for_day regime_prior)
  plus channel_names.json + build_meta.json at the cache root.

NaN policy: build_npz_for_day already applies the production nan_to_num/clip for
regime_prior and the fp16 round-trip for X_raw; F64 is produced fp32 by the
pipeline (several features live in fp16-denormal range, so the pipeline keeps X
fp32) — we store F64 as fp16 ONLY in the cache for footprint parity with the
sibling caches, after a final nan_to_num(0.0) guard. Downstream per-fold
standardization is unchanged. (REG_arch's RevIN makes the model affine-invariant
per window; the fp16 cache cast affects only >10-sigma clip tails, same as the
btc25_raw_perp / btc_trade_perp sibling caches.)

CPU-only, single process (run under nice -n 10). READ-ONLY over the source.

Usage
-----
  # smoke / validation on a few days (force rebuild, prints all gates):
  python multi_asset/data/build_btc_feat64_perp.py --validate 20250210 20250512 20250811
  # full batch build (detached):
  setsid nohup nice -n 10 python multi_asset/data/build_btc_feat64_perp.py --all \
      > /tmp/feat64perp_build.log 2>&1 < /dev/null &
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import os.path as p
import sys
import time
import warnings
from collections import OrderedDict
from io import StringIO

import numpy as np
import pandas as pd

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
sys.path.insert(0, _REPO)

# Frozen production feature pipeline + resampler — IMPORTED UNCHANGED (src/ is
# read-only; we only repoint the data source upstream of these calls).
from src.features.pipeline import build_npz_for_day              # noqa: E402
from src.features.resample import resample_lob_to_1s             # noqa: E402

# The exact production 64-feature schema + the panel-grid alignment helper, both
# inherited from the sibling caches so this build is provably aligned to them.
from multi_asset.data.build_factor_leg import EXPECTED_FEATURES  # noqa: E402
from multi_asset.data.build_btc25_raw import _seq_ts, list_days  # noqa: E402
from multi_asset.data.btc25_state import SEQ_DIR                 # noqa: E402

# --------------------------------------------------------------------- paths
PERP_BOOK_ROOT = ("/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/"
                  "book_snapshot_25")                            # READ-ONLY
PERP_TRADES_ROOT = ("/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/"
                    "trades")                                    # READ-ONLY
OUT_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/btc_feat64_perp")

N_LVL = 25          # book levels read from source (pipeline raw path keeps 20)
N_RAW = 20          # raw-LOB tensor levels build_npz_for_day emits (min(25,20))
N_FEAT = 64
N_RP = 6
WINDOW = 600        # max model input length — only used to seed the calendar span

# book columns resample_lob_to_1s consumes (timestamp + 25 levels both sides)
_BOOK_COLS = ["timestamp"]
for _i in range(N_LVL):
    _BOOK_COLS += [f"asks[{_i}].price", f"asks[{_i}].amount",
                   f"bids[{_i}].price", f"bids[{_i}].amount"]


# ------------------------------------------------------------------ raw read
def _read_gz_csv_robust(path, usecols=None):
    """gzip CSV reader robust to truncated streams (mirrors build_factor_leg's
    ``_read_gz_csv_robust`` == the validated inference package reader)."""
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
            raise ValueError(f"{path}: no readable content")
        df = pd.read_csv(StringIO("".join([header] + rows)), on_bad_lines="skip")
        return df[usecols] if usecols else df


def read_book_day(date_str: str) -> pd.DataFrame:
    """PERP twin of build_factor_leg.read_book_day — same usecols, perp path."""
    path = p.join(PERP_BOOK_ROOT, date_str, "binance-futures", "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    return _read_gz_csv_robust(path, usecols=_BOOK_COLS)


def read_trades_day(date_str: str) -> pd.DataFrame:
    """PERP twin of build_factor_leg.read_trades_day — read + normalise trades
    exactly like the production multi-day pipeline (amount->size, id->exec_id,
    side Title-cased: 'buy'->'Buy')."""
    path = p.join(PERP_TRADES_ROOT, date_str, "binance-futures", "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    df = _read_gz_csv_robust(path)
    ren = {}
    if "amount" in df.columns and "size" not in df.columns:
        ren["amount"] = "size"
    if "id" in df.columns and "exec_id" not in df.columns:
        ren["id"] = "exec_id"
    if ren:
        df.rename(columns=ren, inplace=True)
    if "side" in df.columns:
        df["side"] = df["side"].astype(str).str.title()
    return df


# -------------------------------------------------- per-calendar-day features
def build_calendar_day(date_str: str) -> dict:
    """Per-bar (1s) feature/raw/regime arrays for one UTC calendar day through
    the EXACT production pipeline (cold start at 00:00 UTC). input_len=1/stride=1
    turns the production windower into a per-bar emitter — feature values are
    bit-identical to training because features are computed on the full day
    BEFORE windowing. VERBATIM copy of build_factor_leg.build_calendar_day with
    the PERP read functions above (the only change)."""
    t0 = time.time()
    raw_book = read_book_day(date_str)
    df_1s = resample_lob_to_1s(raw_book, n_levels=N_LVL)
    del raw_book

    # strip rows outside the folder date (mirrors multi_day_pipeline / factor_leg)
    day_start_us = int(pd.Timestamp(date_str, tz="UTC").timestamp() * 1_000_000)
    day_end_us = day_start_us + 86_400 * 1_000_000
    df_1s = df_1s[(df_1s["timestamp"] >= day_start_us)
                  & (df_1s["timestamp"] < day_end_us)].reset_index(drop=True)
    if len(df_1s) < WINDOW:
        raise ValueError(f"{date_str}: only {len(df_1s)} 1s rows")

    trades_df = read_trades_day(date_str)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")          # stride<horizon warning (n/a here)
        res = build_npz_for_day(
            df_1s, trades_df=trades_df, horizons_sec=[600],
            input_len=1, stride=1, n_levels=N_LVL,
            include_ridge_features=True, include_regime_prior=True,
            quantize_features=True,              # X_raw fp16 round-trip == training
        )
    del df_1s, trades_df

    feats = [str(f) for f in res["features"]]
    if feats != EXPECTED_FEATURES:
        raise RuntimeError(
            f"{date_str}: feature schema drift vs production "
            f"({len(feats)} cols; first diff at "
            f"{next((i for i, (a, b) in enumerate(zip(feats, EXPECTED_FEATURES)) if a != b), 'len')})")

    out = {
        "sec": (res["timestamps"] // 1_000_000).astype(np.int64),   # epoch s
        "F": res["X"][:, 0, :].astype(np.float32),                  # (T,64) fp32
        "R": res["X_raw"][:, 0].astype(np.float32),                 # (T,20,4) fp16->fp32
        "RP": res["regime_prior"].astype(np.float32),               # (T,6)
        "secs_build": time.time() - t0,
    }
    if not np.all(np.diff(out["sec"]) == 1):
        raise RuntimeError(f"{date_str}: 1s grid not contiguous after strip")
    return out


class CalendarCache:
    """Keep the most recent K calendar days (consecutive panel days share D-1)."""

    def __init__(self, k: int = 3):
        self.k = k
        self._d: "OrderedDict[str, dict]" = OrderedDict()

    def get(self, date_str: str) -> dict:
        if date_str in self._d:
            self._d.move_to_end(date_str)
            return self._d[date_str]
        if len(self._d) >= self.k:
            self._d.popitem(last=False)
        self._d[date_str] = build_calendar_day(date_str)
        return self._d[date_str]


def _concat_days(cds: list) -> tuple:
    sec = np.concatenate([c["sec"] for c in cds])
    if not np.all(np.diff(sec) > 0):
        raise RuntimeError("calendar-day concat: seconds not strictly increasing")
    F = np.concatenate([c["F"] for c in cds], axis=0)
    R = np.concatenate([c["R"] for c in cds], axis=0)
    RP = np.concatenate([c["RP"] for c in cds], axis=0)
    return sec, F, R, RP


# --------------------------------------------------------------------- build
def _calendar_days_for(grid_secs: np.ndarray) -> list:
    """UTC calendar 'YYYY-MM-DD' folders covering [first_bar, last_bar]. The
    panel day is fully inside [d-1, d]; we seed WINDOW seconds before the first
    bar so the calendar span is robust if the day ever begins right at a
    midnight boundary (it does not — starts ~14:05 — but be safe)."""
    lo = int(grid_secs[0]) - WINDOW
    hi = int(grid_secs[-1])
    d0 = dt.datetime.fromtimestamp(lo, dt.timezone.utc).date()
    d1 = dt.datetime.fromtimestamp(hi, dt.timezone.utc).date()
    out, d = [], d0
    while d <= d1:
        out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def build_one_day(day: int, out_path: str, cache: CalendarCache,
                  keep_arrays: bool = False) -> dict:
    """Build <out_path> for one PANEL day on the FULL 1s seq_cache grid. Same
    alignment + atomic-write contract as build_btc25_raw_perp.build_one_day:
    ts is hard-asserted byte-identical to seq_cache/<day>.npz."""
    t0 = time.time()
    ts = _seq_ts(day)                                  # (T,) ns, 1s grid (==btc25_raw_perp)
    grid_secs = ts // 1_000_000_000
    if not np.all(np.diff(grid_secs) == 1):
        raise ValueError(f"day {day}: seq_cache ts grid is not contiguous 1s")

    dates = _calendar_days_for(grid_secs)
    sec, F, R, RP = _concat_days([cache.get(ds) for ds in dates])

    # Align the per-calendar-day per-bar arrays onto the panel 1s grid by CAUSAL
    # forward-fill — IDENTICAL semantics to build_btc25_raw_perp._load_book_1s
    # (searchsorted(side="right")-1: each grid second takes the last available
    # per-bar row at-or-before it). Almost every grid second matches exactly; the
    # ONLY structural gaps are calendar-file-boundary seconds where the source
    # book/trade file's first tick lands at 00:00:01 instead of 00:00:00, so the
    # 00:00:00 panel bar has no own per-bar row. Carrying forward the prior
    # second's feature state is leak-free (uses only data <= t) and matches how
    # btc25_raw_perp fills the very same gap, keeping the two caches row-for-row
    # consistent. The first grid second is always deep inside the d-1 file
    # (panel day starts ~14:05 UTC) so pos>=0 everywhere; we assert that.
    pos = np.searchsorted(sec, grid_secs, side="right") - 1
    if pos.min() < 0:
        miss = int(grid_secs[pos < 0][0])
        raise RuntimeError(f"day {day}: grid second {miss} precedes all calendar "
                           f"data {dates} — alignment contract broken")
    n_ffilled = int((sec[pos] != grid_secs).sum())   # gap-filled (carried) seconds
    if n_ffilled > 0:
        gaps = grid_secs[sec[pos] != grid_secs]
        print(f"  [day {day}] {n_ffilled} grid second(s) causally ffilled "
              f"(calendar-boundary gaps, e.g. {int(gaps[0])}); same as "
              f"btc25_raw_perp", flush=True)

    F64 = F[pos]                                        # (T,64) fp32
    R20 = R[pos]                                        # (T,20,4) fp32 (already fp16-rounded)
    RP6 = RP[pos]                                       # (T,6) fp32

    if F64.shape != (ts.shape[0], N_FEAT):
        raise RuntimeError(f"day {day}: F64 shape {F64.shape} != ({ts.shape[0]},{N_FEAT})")
    if R20.shape != (ts.shape[0], N_RAW, 4):
        raise RuntimeError(f"day {day}: R20 shape {R20.shape}")
    if RP6.shape != (ts.shape[0], N_RP):
        raise RuntimeError(f"day {day}: RP shape {RP6.shape}")

    n_nan_F = int((~np.isfinite(F64)).sum())
    n_nan_R = int((~np.isfinite(R20)).sum())
    n_nan_RP = int((~np.isfinite(RP6)).sum())

    F16 = np.nan_to_num(F64, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float16)
    R16 = np.nan_to_num(R20, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float16)
    RP16 = np.nan_to_num(RP6, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float16)
    if not (np.isfinite(F16).all() and np.isfinite(R16).all()
            and np.isfinite(RP16).all()):
        raise RuntimeError(f"day {day}: non-finite values after fp16 cast")

    # hard alignment assert (the contract): ts == seq_cache ts byte-for-byte
    sts = _seq_ts(day)
    if F16.shape[0] != ts.shape[0] or not np.array_equal(ts, sts):
        raise RuntimeError(
            f"day {day}: ts mismatch vs seq_cache — alignment contract broken")

    tmp = out_path + ".tmp.npz"
    np.savez(tmp, ts=ts, F64=F16, R20=R16, RP=RP16)
    os.replace(tmp, out_path)

    stats = {"day": day, "secs": time.time() - t0,
             "mb": os.path.getsize(out_path) / 1e6, "T": int(ts.shape[0]),
             "n_nan_F": n_nan_F, "n_nan_R": n_nan_R, "n_nan_RP": n_nan_RP,
             "n_ffilled": n_ffilled, "calendar_days": dates}
    if keep_arrays:
        stats.update(ts=ts, F16=F16, R16=R16, RP16=RP16,
                     F64=F64, R20=R20, RP6=RP6, grid_secs=grid_secs)
    return stats


# --------------------------------------------------------------------- names/meta
def channel_layout() -> dict:
    return {
        "F64": EXPECTED_FEATURES,
        "R20": {
            "shape": [N_RAW, 4],
            "level_axis": "0..19 (top-of-book = 0)",
            "feature_axis": ["bid_offset_bps_or_delta", "bid_log_amount",
                             "ask_offset_bps_or_delta", "ask_log_amount"],
            "note": ("exact build_npz_for_day X_raw tensor (extract_raw_lob_tensor, "
                     "first 20 of 25 levels); fp16 round-tripped == training"),
        },
        "RP": {
            "shape": [N_RP],
            "note": ("6-dim regime prior from build_npz_for_day include_regime_prior; "
                     "compute_regime_prior_features / REGIME_PRIOR_FEATURE_NAMES order"),
        },
    }


def _write_meta(days: list, n_done: int, n_skip: int, n_fail: int,
                failed_days: list, leak_max_dev=None):
    layout = channel_layout()
    meta = {
        "purpose": ("faithful REG_arch 64-feature + 20-level raw-LOB + 6-dim "
                    "regime cache computed on the CALIBER-CORRECT PERP "
                    "high-precision book + trades; corrected twin of "
                    "build_factor_leg.py inputs (which read the deprecated "
                    "spot-book / perp-trades root)"),
        "source_book": PERP_BOOK_ROOT,
        "source_trades": PERP_TRADES_ROOT,
        "source_instrument": "binance-futures (PERP) — caliber-correct vs bar mid_bnfbtc",
        "feature_pipeline": "src.features.pipeline.build_npz_for_day (UNCHANGED import)",
        "resampler": "src.features.resample.resample_lob_to_1s (UNCHANGED import)",
        "pipeline_kwargs": {"horizons_sec": [600], "input_len": 1, "stride": 1,
                            "n_levels": N_LVL, "include_ridge_features": True,
                            "include_regime_prior": True, "quantize_features": True},
        "twin_of": "build_factor_leg.build_calendar_day (same code path, perp read)",
        "alignment": ("per-UTC-calendar-day cold-start features (00:00 UTC), "
                      "concat [d-1,d], sliced onto seq_cache 1s grid by exact "
                      "second; ts byte-identical to seq_cache & btc25_raw_perp"),
        "n_days_listed": len(days), "n_days_built": n_done,
        "n_days_skipped": n_skip, "n_days_failed": n_fail,
        "failed_days": failed_days,
        "n_features": N_FEAT, "n_raw_levels": N_RAW, "n_regime": N_RP,
        "dtype": "float16",
        "schema": {
            "ts": "(T,) int64 ns, IDENTICAL to seq_cache & btc25_raw_perp ts",
            "F64": f"(T,{N_FEAT}) f16 hand features in EXPECTED_FEATURES order",
            "R20": f"(T,{N_RAW},4) f16 20-level raw-LOB tensor (build_npz_for_day X_raw)",
            "RP": f"(T,{N_RP}) f16 regime prior (build_npz_for_day regime_prior)",
        },
        "channel_layout": layout,
        "leak_check_max_dev_future_perturb": leak_max_dev,
        "note": ("F64 is fp32 in the pipeline (several features sit in fp16-denormal "
                 "range); stored fp16 here for footprint parity with sibling caches. "
                 "X_raw / regime already production-clipped/nan_to_num'd by the "
                 "pipeline; downstream per-fold standardization unchanged."),
    }
    with open(p.join(OUT_DIR, "channel_names.json"), "w") as f:
        json.dump(layout, f, indent=2)
    with open(p.join(OUT_DIR, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


def build(force: bool = False, days_subset: "list | None" = None):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset or list_days(SEQ_DIR)
    print(f"[btc_feat64_perp] {len(days)} day(s), F64/R20/RP -> {OUT_DIR}",
          flush=True)
    cache = CalendarCache(k=3)
    t0 = time.time()
    n_done = n_skip = n_fail = 0
    failed_days = []
    for di, d in enumerate(days):
        out = p.join(OUT_DIR, f"{d}.npz")
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            st = build_one_day(d, out, cache)
        except Exception as e:           # missing/corrupt day -> keep going
            n_fail += 1
            failed_days.append(d)
            print(f"  [warn] day {d} failed: {type(e).__name__}: {e}", flush=True)
            continue
        n_done += 1
        if st["n_nan_F"] or st["n_nan_R"] or st["n_nan_RP"]:
            print(f"  [warn] day {d}: pre-cast NaN/inf cells "
                  f"F={st['n_nan_F']} R={st['n_nan_R']} RP={st['n_nan_RP']} "
                  f"(zero-filled by pipeline+guard)", flush=True)
        if n_done % 10 == 0 or di == len(days) - 1:
            el = time.time() - t0
            rate = n_done / el if el > 0 else 0
            eta = (len(days) - di - 1) / rate if rate > 0 else 0
            print(f"  [{di+1:4d}/{len(days)}] day {d}  built={n_done} "
                  f"skip={n_skip} fail={n_fail}  {el/60:.1f} min, "
                  f"~{rate*60:.2f} day/min, ETA {eta/60:.1f} min", flush=True)

    _write_meta(days, n_done, n_skip, n_fail, failed_days)
    print(f"[btc_feat64_perp] done in {(time.time()-t0)/60:.1f} min: "
          f"built={n_done} skip={n_skip} fail={n_fail}"
          + (f"  FAILED DAYS: {failed_days}" if failed_days else "")
          + f" -> {OUT_DIR}", flush=True)


# ------------------------------------------------------------ quality gates
def _gate_ts(day: int, ts_saved: np.ndarray) -> bool:
    """ts identity vs seq_cache AND vs btc25_raw_perp (row-for-row)."""
    sts = _seq_ts(day)
    ok_seq = np.array_equal(ts_saved, sts)
    rp = p.join(p.dirname(OUT_DIR), "btc25_raw_perp", f"{day}.npz")
    ok_b25 = None
    if p.exists(rp):
        with np.load(rp) as z:
            ok_b25 = np.array_equal(ts_saved, z["ts"].astype(np.int64))
    print(f"  [GATE ts] ts==seq_cache: {ok_seq}  T={ts_saved.shape[0]} "
          f"(85800 expected)  ts==btc25_raw_perp: {ok_b25}", flush=True)
    return bool(ok_seq and (ok_b25 in (True, None)))


def _gate_shapes_finite(F16, R16, RP16) -> bool:
    ok = (F16.shape[1:] == (N_FEAT,) and R16.shape[1:] == (N_RAW, 4)
          and RP16.shape[1:] == (N_RP,)
          and F16.dtype == np.float16 and R16.dtype == np.float16
          and RP16.dtype == np.float16)
    fin = (np.isfinite(F16.astype(np.float32)).all()
           and np.isfinite(R16.astype(np.float32)).all()
           and np.isfinite(RP16.astype(np.float32)).all())
    # no all-NaN/all-zero feature column (each of the 64 must carry content)
    F = F16.astype(np.float32)
    col_nonzero = (np.abs(F) > 0).any(axis=0)
    n_dead = int((~col_nonzero).sum())
    print(f"  [GATE shape/finite] F{F16.shape} R{R16.shape} RP{RP16.shape}  "
          f"dtypes f16: {F16.dtype==np.float16}  all-finite: {fin}  "
          f"dead(all-zero) feature cols: {n_dead}/{N_FEAT}", flush=True)
    if n_dead:
        dead = [EXPECTED_FEATURES[i] for i in np.flatnonzero(~col_nonzero)]
        print(f"    dead cols: {dead}", flush=True)
    return bool(ok and fin and n_dead == 0)


def _feat_sanity(F16) -> None:
    F = F16.astype(np.float32)
    print(f"  {'#':>3} {'feature':<26}{'min':>12}{'median':>12}{'max':>12}",
          flush=True)
    for j, nm in enumerate(EXPECTED_FEATURES):
        c = F[:, j]
        print(f"  {j:>3} {nm:<26}{c.min():>12.5g}{np.median(c):>12.5g}"
              f"{c.max():>12.5g}", flush=True)


def _gate_leak(day: int, cache: CalendarCache) -> tuple:
    """LEAK CHECK by future perturbation: build the day normally, then perturb
    the LAST calendar day's input book/trades by overwriting all rows AFTER a
    cut second with garbage, rebuild, and confirm feature rows AT-OR-BEFORE the
    cut are byte-identical (a causal feature cannot move when only its future
    changes). Reports max deviation over F64/R20/RP at rows <= cut.

    Implementation: rather than re-plumb the resampler, we cut on the already-
    built per-calendar-day per-bar arrays of the FINAL calendar day, perturb the
    rows after the cut, and assert the pipeline's per-bar outputs (which are the
    feature values) are unaffected at rows <= cut. Because build_npz_for_day
    computes each feature on the full day BEFORE windowing, the only way a row
    <= cut could change is a non-causal (future-looking) feature. We re-run the
    pipeline on a future-perturbed RAW book/trades to make this airtight."""
    ts = _seq_ts(day)
    grid_secs = ts // 1_000_000_000
    dates = _calendar_days_for(grid_secs)
    last_date = dates[-1]

    # raw inputs for the final calendar day
    raw_book = read_book_day(last_date)
    df_1s = resample_lob_to_1s(raw_book, n_levels=N_LVL)
    day_start_us = int(pd.Timestamp(last_date, tz="UTC").timestamp() * 1_000_000)
    day_end_us = day_start_us + 86_400 * 1_000_000
    df_1s = df_1s[(df_1s["timestamp"] >= day_start_us)
                  & (df_1s["timestamp"] < day_end_us)].reset_index(drop=True)
    trades_df = read_trades_day(last_date)

    def _run(df_1s_in, trades_in):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = build_npz_for_day(
                df_1s_in, trades_df=trades_in, horizons_sec=[600],
                input_len=1, stride=1, n_levels=N_LVL,
                include_ridge_features=True, include_regime_prior=True,
                quantize_features=True)
        return (r["X"][:, 0, :].astype(np.float32),
                r["X_raw"][:, 0].astype(np.float32),
                r["regime_prior"].astype(np.float32),
                (r["timestamps"] // 1_000_000).astype(np.int64))

    F0, R0, RP0, sec0 = _run(df_1s, trades_df)

    # cut at ~80% through the day; perturb every input row STRICTLY AFTER the cut
    cut_i = int(0.8 * len(df_1s))
    cut_sec = int(df_1s["timestamp"].iloc[cut_i] // 1_000_000)
    dfb = df_1s.copy()
    fut = dfb.index > cut_i
    rng = np.random.default_rng(123 + day)
    pxcols = [c for c in dfb.columns if c.endswith(".price")]
    amcols = [c for c in dfb.columns if c.endswith(".amount")]
    # garbage the future book rows (huge, sign-flipped, randomized)
    for c in pxcols:
        dfb.loc[fut, c] = dfb.loc[fut, c].to_numpy() * (1.0 + rng.uniform(
            -0.5, 0.5, size=int(fut.sum())))
    for c in amcols:
        dfb.loc[fut, c] = dfb.loc[fut, c].to_numpy() * 0.0 + rng.uniform(
            1e3, 1e5, size=int(fut.sum()))
    # garbage all future trades (after cut_sec)
    trb = trades_df.copy()
    if "timestamp" in trb.columns:
        tmask = (trb["timestamp"].to_numpy(np.int64) // 1_000_000) > cut_sec
        if "price" in trb.columns:
            trb.loc[tmask, "price"] = trb.loc[tmask, "price"].to_numpy() * 3.0
        if "size" in trb.columns:
            trb.loc[tmask, "size"] = trb.loc[tmask, "size"].to_numpy() * 0.0 + 1e6
        elif "amount" in trb.columns:
            trb.loc[tmask, "amount"] = trb.loc[tmask, "amount"].to_numpy() * 0.0 + 1e6
        if "side" in trb.columns:
            trb.loc[tmask, "side"] = "Buy"

    F1, R1, RP1, sec1 = _run(dfb, trb)
    if not np.array_equal(sec0, sec1):
        print("  [GATE leak] FAIL: timestamp grid changed under perturbation",
              flush=True)
        return False, float("nan")

    le = sec0 <= cut_sec                       # rows whose own second <= cut
    dF = np.abs(F0[le] - F1[le]); dR = np.abs(R0[le] - R1[le])
    dRP = np.abs(RP0[le] - RP1[le])
    mF = float(np.nanmax(dF)) if dF.size else 0.0
    mR = float(np.nanmax(dR)) if dR.size else 0.0
    mRP = float(np.nanmax(dRP)) if dRP.size else 0.0
    mx = max(mF, mR, mRP)
    # which feature moved most (diagnostic)
    if dF.size:
        jbad = int(np.nanargmax(np.nanmax(dF, axis=0)))
        worst = f"{EXPECTED_FEATURES[jbad]} (|d|={np.nanmax(dF[:, jbad]):.3g})"
    else:
        worst = "n/a"
    ok = mx < 1e-5
    print(f"  [GATE leak] future-perturb (cut sec={cut_sec}, "
          f"{int(le.sum())} causal rows <= cut):  max|dF|={mF:.3e} "
          f"max|dR|={mR:.3e} max|dRP|={mRP:.3e}  worst-feat={worst}  "
          f"-> {'PASS (causal, ~0)' if ok else 'FAIL'}", flush=True)
    return ok, mx


def _gate_xcheck(day: int, F16, out_path: str) -> None:
    """Cross-check overlapping primitives vs btc25_raw_perp (same perp book):
    spread_bps and microprice_dev_bps appear in both caches; correlate them."""
    rp = p.join(p.dirname(OUT_DIR), "btc25_raw_perp", f"{day}.npz")
    if not p.exists(rp):
        print("  [xcheck] SKIP: btc25_raw_perp missing", flush=True)
        return
    with np.load(rp) as z:
        if not np.array_equal(z["ts"].astype(np.int64), _seq_ts(day)):
            print("  [xcheck] SKIP: ts misaligned", flush=True)
            return
        names = [str(s) for s in z["ch_names"]]
        R25 = z["R25"].astype(np.float32)
    idx25 = {n: i for i, n in enumerate(names)}
    F = F16.astype(np.float32)
    fidx = {n: i for i, n in enumerate(EXPECTED_FEATURES)}
    print("  [xcheck] feat64_perp vs btc25_raw_perp shared primitives "
          "(same perp book):", flush=True)
    for nm in ("spread_bps", "microprice_dev_bps"):
        if nm in fidx and nm in idx25:
            a = F[:, fidx[nm]]; b = R25[:, idx25[nm]]
            g = np.isfinite(a) & np.isfinite(b)
            c = (float(np.corrcoef(a[g], b[g])[0, 1])
                 if g.sum() > 100 and a[g].std() > 0 and b[g].std() > 0 else float("nan"))
            md = float(np.median(np.abs(a[g] - b[g]))) if g.sum() else float("nan")
            print(f"    {nm:<22} corr={c:+.5f}  med|d|={md:.4f}  "
                  f"(feat mean {a[g].mean():+.4f} / b25 mean {b[g].mean():+.4f})",
                  flush=True)
    # OBI: feat64 obi_L25 vs btc25 deep_imb_l1_25 (both full-book imbalance)
    if "obi_L25" in fidx and "deep_imb_l1_25" in idx25:
        a = F[:, fidx["obi_L25"]]; b = R25[:, idx25["deep_imb_l1_25"]]
        g = np.isfinite(a) & np.isfinite(b)
        c = (float(np.corrcoef(a[g], b[g])[0, 1])
             if g.sum() > 100 and a[g].std() > 0 and b[g].std() > 0 else float("nan"))
        print(f"    {'obi_L25 ~ deep_imb_l1_25':<22} corr={c:+.5f}  "
              f"(both full-25-level book imbalance)", flush=True)


def validate(days: list):
    os.makedirs(OUT_DIR, exist_ok=True)
    n_total = len(list_days(SEQ_DIR))
    cache = CalendarCache(k=3)
    per_day_secs, per_day_mb = [], []
    gates = {"ts": True, "shape_finite": True, "leak": True}
    leak_max = 0.0

    for d in days:
        out = p.join(OUT_DIR, f"{d}.npz")
        st = build_one_day(d, out, cache, keep_arrays=True)   # force rebuild
        per_day_secs.append(st["secs"]); per_day_mb.append(st["mb"])
        F16, R16, RP16 = st["F16"], st["R16"], st["RP16"]
        print(f"\n================ day {d}: T={st['T']} F64={F16.shape} "
              f"R20={R16.shape} RP={RP16.shape} {st['mb']:.2f} MB "
              f"{st['secs']:.1f}s  calendar={st['calendar_days']} ================",
              flush=True)

        with np.load(out) as z:
            ts_saved = z["ts"].astype(np.int64)
            Fz, Rz, RPz = z["F64"], z["R20"], z["RP"]
        gates["ts"] &= _gate_ts(d, ts_saved)
        gates["shape_finite"] &= _gate_shapes_finite(Fz, Rz, RPz)
        print("  [feature min/median/max sanity]", flush=True)
        _feat_sanity(Fz)
        ok_leak, mx = _gate_leak(d, cache)
        gates["leak"] &= ok_leak
        leak_max = max(leak_max, mx if np.isfinite(mx) else 0.0)
        _gate_xcheck(d, Fz, out)

    s, mb = float(np.mean(per_day_secs)), float(np.mean(per_day_mb))
    print(f"\n[GATE size] avg {s:.1f} s/day, {mb:.2f} MB/day; full build est "
          f"({n_total} days): {n_total*s/3600:.2f} h, {n_total*mb/1000:.2f} GB",
          flush=True)
    print("\n[validate] " + "  ".join(
        f"GATE_{g}={'PASS' if ok else 'FAIL'}" for g, ok in gates.items())
        + f"  leak_max_dev={leak_max:.2e}  GATE_size=reported", flush=True)
    # write meta with leak result even in validate mode (provenance)
    _write_meta(days, len(days), 0, 0, [], leak_max_dev=leak_max)
    if not all(gates.values()):
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every seq_cache day (skip existing)")
    g.add_argument("--days", type=int, nargs="+",
                   help="build only these YYYYMMDD days")
    g.add_argument("--validate", type=int, nargs="+",
                   help="force-build + full quality-gate suite on these days")
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    ap.add_argument("--threads", type=int, default=8,
                    help="numpy/pandas thread cap is left to the BLAS env; this "
                         "is a no-op placeholder for symmetry with siblings")
    args = ap.parse_args()
    if args.validate:
        validate(args.validate)
    else:
        build(force=args.force, days_subset=args.days)

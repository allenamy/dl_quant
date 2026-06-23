"""Build the single-asset REG_arch TRAINING NPZ cache on the CALIBER-CORRECT
PERP high-precision book + trades — the corrected twin of ``data/npz_v4`` that
the frozen single-asset trainer (``LOBDatasetV2`` / ``trainer_v2.py``) consumes.

WHY THIS FILE EXISTS
--------------------
The single-asset REG_arch winner (``configs/v5push/singh_alpha0_huber_track_reg_arch.json``)
trains from ``data/npz_v4/<YYYY-MM-DD>.npz`` — windowed 64-feature + 20-level
raw-LOB + 6-dim regime-prior + multi-horizon (y_60/180/300/600) labels. Those
NPZs were built by ``src.features.pipeline.process_csv_to_npz`` /
``build_npz_for_day`` from the DEPRECATED, BUGGY root
``/mnt/storage/share/23-25-BTCUSDT`` whose *book* is binance SPOT while its
*trades* are PERP — the documented spot-perp caliber bug (basis +5..-7.5 bps,
root cause of B25-FAIL). The corrected PERP high-precision data (book + trades
BOTH ``binance-futures``) was verified perp-book mid == bar perp target at
corr 1.000.

This builder repoints ONLY the data-source stage to the corrected PERP root and
emits, PER UTC CALENDAR DAY, the EXACT same windowed training contract that
``data/npz_v4`` carries (``input_len=600``, ``stride=180``, horizons
[60,180,300,600], ``include_ridge_features=True``, ``include_regime_prior=True``,
``quantize_features=True``). The feature pipeline, the resampler, the windower,
the label computation, and the NPZ writer are all IMPORTED UNCHANGED from the
frozen ``src/`` tree and the existing perp adapter — faithfulness to REG_arch's
exact input contract is the whole point; nothing is approximated or substituted.

DIFFERENCE vs the existing perp adapter ``build_btc_feat64_perp.py``
-------------------------------------------------------------------
``build_btc_feat64_perp.py`` reuses the SAME perp CSV readers + resampler but
calls ``build_npz_for_day`` with ``input_len=1/stride=1`` (a per-bar emitter)
and aligns the per-bar arrays onto the panel seq_cache grid — i.e. it produces
INFERENCE slices for the multi-asset panel, NOT the windowed training cache.
This builder REUSES that file's perp readers + resampler VERBATIM (imported)
but calls ``build_npz_for_day`` with the TRAINING windowing config so the output
is the full ``X (N,600,64)`` / ``X_raw (N,600,20,4)`` / ``y_600`` / ``y_mask`` /
``regime_prior`` contract that ``LOBDatasetV2`` reads, for ALL 1247 days of the
corrected PERP period (2023-01-01 .. 2026-05-31), not just the 487 panel days.

OUTPUT (NEW DIR — nothing existing is touched)
----------------------------------------------
  <OUT_DIR=data/npz_perp>/<YYYY-MM-DD>.npz   one file per UTC calendar day, with
  the EXACT keys ``LOBDatasetV2`` reads (identical to ``data/npz_v4`` schema):
      X            float32  (N, 600, 64)      64 hand features, EXPECTED_FEATURES order
      X_raw        float16  (N, 600, 20, 4)   20-level raw-LOB tensor (build_npz_for_day)
      timestamps   int64    (N,)              pred-idx timestamp (us since epoch)
      features     object   (64,)             feature column names
      horizons_sec int64    (4,)              [60, 180, 300, 600]
      y_{H}        float32  (N,)              log-return label at horizon H (PERP mid)
      y_mask_{H}   uint8    (N,)              1 if label valid (target_idx in-day)
      y, y_mask    aliases of the smallest horizon (y_60) — back-compat
      regime_prior float32  (N, 6)            6-dim regime prior
  plus build_meta.json at the cache root.

tv_overlay DECISION
-------------------
The config carries ``tv_overlay_dir: "data/npz_v4_tv_overlay"`` but the frozen
REG_arch training path (``run_pipeline_v3.py`` ~L689) EXPLICITLY does NOT wire
``tv_overlay_dir`` into ``LOBDatasetV2`` — the comment there documents that the
REG_arch baseline was trained with ``n_features=64`` (ckpt
``input_proj.weight=(32,64)``), and adding tv_overlay would change baseline
behavior. The tv_overlay key in the config is inert for this track. Therefore
this builder does NOT produce a tv_overlay cache; the corrected perp NPZ alone
is the complete REG_arch training input. (Recorded in build_meta.json.)

ALIGNMENT / WARMUP
------------------
Features are computed PER UTC CALENDAR DAY with a cold start at 00:00 UTC —
byte-identical methodology to the original npz_v4 build (``process_csv_to_npz``
splits by UTC day, then windows within each day). The first kept window's
pred_idx is at second input_len-1 (= 599s ≈ 00:09:59), so each day carries an
in-day feature warmup exactly as the original cache did. No cross-day concat.

LEAK SAFETY
-----------
Labels are forward log-returns of the PERP mid (``build_npz_for_day``:
``y = log(mid[pred_idx + H] / mid[pred_idx])``) — strictly future-only, gated by
``y_mask`` (0 when ``pred_idx + H`` falls outside the day). Features at a window
use only rows ``[start, pred_idx]`` (<= t). A future-perturbation gate
(``--validate``) corrupts all input rows AFTER a cut second, rebuilds, and
asserts every window whose pred_idx <= cut is byte-identical (max|dev| ~ 0).

CPU-only, single process (run under nice -n 10). READ-ONLY over the source.

Usage
-----
  # smoke / validation on a few days (force rebuild, prints all gates + leak):
  python multi_asset/data/build_regarch_perp_npz.py --validate 2025-02-10 2024-08-15 2023-06-01
  # build a subset:
  python multi_asset/data/build_regarch_perp_npz.py --days 2025-02-10 2025-02-11
  # full batch build (detached) — all 1247 perp days, skip existing:
  setsid nohup nice -n 10 python multi_asset/data/build_regarch_perp_npz.py --all \
      > /tmp/regarch_perp_build.log 2>&1 < /dev/null &
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
import pandas as pd

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
sys.path.insert(0, _REPO)

# Frozen production feature pipeline + writer — IMPORTED UNCHANGED (src/ is
# read-only; we only repoint the data source upstream of these calls).
from src.features.pipeline import build_npz_for_day, _save_result_npz  # noqa: E402
from src.features.resample import resample_lob_to_1s                   # noqa: E402

# The exact 64-feature production schema + the VERBATIM perp CSV readers built
# this session — reused so this build is provably the corrected twin of npz_v4.
from multi_asset.data.build_factor_leg import EXPECTED_FEATURES        # noqa: E402
from multi_asset.data.build_btc_feat64_perp import (                   # noqa: E402
    PERP_BOOK_ROOT,
    PERP_TRADES_ROOT,
    read_book_day,
    read_trades_day,
)

# --------------------------------------------------------------------- config
# EXACT data block of configs/v5push/singh_alpha0_huber_track_reg_arch.json,
# except horizons_sec — the config requests [600] (the only key the dataset
# reads for this track) but npz_v4 stored all of [60,180,300,600]; we replicate
# the FULL multi-horizon label set so this cache is a byte-schema match to
# npz_v4 and remains reusable for any multi-horizon config. Adding the extra
# horizons is free (same windows; y_60/180/300 just fill more arrays).
N_LEVELS = 25            # book levels read; pipeline raw path keeps min(25,20)=20
HORIZON_SEC = 600
INPUT_LEN = 600
STRIDE = 180
HORIZONS_SEC = [60, 180, 300, 600]
INCLUDE_RIDGE = True
INCLUDE_REGIME = True
QUANTIZE = True

N_FEAT = 64
N_RAW = 20

# Full corrected-PERP period (inclusive), matching the source roots.
PERIOD_START = dt.date(2023, 1, 1)
PERIOD_END = dt.date(2026, 5, 31)

# Output cache — repo data/ (writable on jpline). One file per UTC calendar day.
OUT_DIR = p.join(_REPO, "data", "npz_perp")

# Local-dev fallback if data/ is not writable (mirrors the sibling caches'
# convention of living under multi_asset/exports when data/ is unavailable).
_FALLBACK_OUT = p.join(_REPO, "multi_asset", "exports", "npz_perp")


def _resolve_out_dir() -> str:
    """Prefer repo data/npz_perp; fall back to multi_asset/exports/npz_perp if
    data/ cannot be created/written."""
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        testf = p.join(OUT_DIR, ".write_test")
        with open(testf, "w") as f:
            f.write("ok")
        os.remove(testf)
        return OUT_DIR
    except OSError:
        os.makedirs(_FALLBACK_OUT, exist_ok=True)
        return _FALLBACK_OUT


# --------------------------------------------------------------- day listing
def list_perp_days() -> list[str]:
    """All YYYY-MM-DD calendar days present in the PERP book source, within the
    declared period, sorted. (Trades existence is checked at build time; a day
    missing trades fails gracefully and is recorded.)"""
    if not p.isdir(PERP_BOOK_ROOT):
        raise FileNotFoundError(f"PERP book root not found: {PERP_BOOK_ROOT}")
    out = []
    for name in os.listdir(PERP_BOOK_ROOT):
        try:
            d = dt.date.fromisoformat(name)
        except ValueError:
            continue
        if PERIOD_START <= d <= PERIOD_END:
            out.append(name)
    return sorted(out)


# ------------------------------------------------ per-calendar-day windowing
def _resample_strip_day(date_str: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read PERP book+trades for one UTC calendar day, resample book to 1s, and
    strip to rows strictly inside [00:00, 24:00) UTC — identical preprocessing to
    build_btc_feat64_perp.build_calendar_day (and to the original per-UTC-day
    npz_v4 build). Returns (df_1s, trades_df). Raises on short/missing days."""
    raw_book = read_book_day(date_str)              # PERP book (binance-futures)
    df_1s = resample_lob_to_1s(raw_book, n_levels=N_LEVELS)
    del raw_book
    day_start_us = int(pd.Timestamp(date_str, tz="UTC").timestamp() * 1_000_000)
    day_end_us = day_start_us + 86_400 * 1_000_000
    df_1s = df_1s[(df_1s["timestamp"] >= day_start_us)
                  & (df_1s["timestamp"] < day_end_us)].reset_index(drop=True)
    if len(df_1s) < INPUT_LEN:
        raise ValueError(f"{date_str}: only {len(df_1s)} 1s rows (< input_len)")
    trades_df = read_trades_day(date_str)           # PERP trades (binance-futures)
    return df_1s, trades_df


def build_day_result(date_str: str) -> dict:
    """Build the windowed REG_arch training dict for one UTC calendar day via
    the FROZEN production pipeline with the TRAINING windowing config. The
    returned dict is exactly what _save_result_npz writes and LOBDatasetV2
    reads. Feature schema is hard-asserted against EXPECTED_FEATURES so any
    drift fails the day instead of silently producing a bad cache."""
    df_1s, trades_df = _resample_strip_day(date_str)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # stride<max_horizon: 180<600 is intended
        res = build_npz_for_day(
            df_1s, trades_df=trades_df,
            horizons_sec=HORIZONS_SEC,
            input_len=INPUT_LEN, stride=STRIDE, n_levels=N_LEVELS,
            include_ridge_features=INCLUDE_RIDGE,
            include_regime_prior=INCLUDE_REGIME,
            quantize_features=QUANTIZE,
        )
    del df_1s, trades_df

    feats = [str(f) for f in res["features"]]
    if feats != EXPECTED_FEATURES:
        diff = next((i for i, (a, b) in enumerate(zip(feats, EXPECTED_FEATURES))
                     if a != b), "len")
        raise RuntimeError(
            f"{date_str}: feature schema drift vs production "
            f"({len(feats)} cols; first diff at {diff})")
    return res


def _result_stats(res: dict) -> dict:
    X = res["X"]; Xr = res["X_raw"]; rp = res.get("regime_prior")
    y6 = res["y_600"]; m6 = res["y_mask_600"]
    valid = m6.astype(bool)
    yv = y6[valid] if valid.any() else y6[:0]
    return {
        "N": int(X.shape[0]),
        "X_shape": tuple(int(s) for s in X.shape),
        "X_dtype": str(X.dtype),
        "X_raw_shape": tuple(int(s) for s in Xr.shape),
        "X_raw_dtype": str(Xr.dtype),
        "rp_shape": (tuple(int(s) for s in rp.shape) if rp is not None else None),
        "y600_valid": int(valid.sum()),
        "y600_mean_bps": (float(yv.mean() * 1e4) if yv.size else float("nan")),
        "y600_std_bps": (float(yv.std() * 1e4) if yv.size else float("nan")),
        "y600_min_bps": (float(yv.min() * 1e4) if yv.size else float("nan")),
        "y600_max_bps": (float(yv.max() * 1e4) if yv.size else float("nan")),
        "n_nan_X": int((~np.isfinite(X)).sum()),
        "n_dead_cols": int((~(np.abs(X.astype(np.float32)) > 0)
                            .any(axis=(0, 1))).sum()),
    }


def build_one_day(date_str: str, out_path: str) -> dict:
    """Build + atomically write <out_path> for one UTC calendar day."""
    t0 = time.time()
    res = build_day_result(date_str)
    st = _result_stats(res)
    # PID-unique tmp so a second accidental instance cannot consume our tmp
    # before os.replace runs (defensive against double-launch races). Still
    # ends in .npz so np.savez_compressed does not append a second extension.
    tmp = f"{out_path}.tmp.{os.getpid()}.npz"
    _save_result_npz(tmp, res)          # frozen production NPZ writer (compressed)
    os.replace(tmp, out_path)
    st["secs"] = time.time() - t0
    st["mb"] = os.path.getsize(out_path) / 1e6
    return st


# --------------------------------------------------------------------- meta
def _write_meta(out_dir: str, days: list[str], n_done: int, n_skip: int,
                n_fail: int, failed_days: list[str], leak_max_dev=None):
    meta = {
        "purpose": ("single-asset REG_arch TRAINING NPZ cache (windowed "
                    "input_len=600/stride=180, multi-horizon labels + raw-LOB "
                    "+ regime prior) computed on the CALIBER-CORRECT PERP "
                    "high-precision book + trades; corrected twin of "
                    "data/npz_v4 (which read the deprecated spot-book root)."),
        "consumed_by": "src.training.dataset.LOBDatasetV2 (trainer_v2.py)",
        "config_reproduced": "configs/v5push/singh_alpha0_huber_track_reg_arch.json",
        "source_book": PERP_BOOK_ROOT,
        "source_trades": PERP_TRADES_ROOT,
        "source_instrument": ("binance-futures (PERP) — perp book mid corr 1.000 "
                              "with bar perp target; fixes spot-perp basis bug"),
        "feature_pipeline": "src.features.pipeline.build_npz_for_day (UNCHANGED import)",
        "npz_writer": "src.features.pipeline._save_result_npz (UNCHANGED import)",
        "resampler": "src.features.resample.resample_lob_to_1s (UNCHANGED import)",
        "perp_readers": ("multi_asset.data.build_btc_feat64_perp.read_book_day / "
                         "read_trades_day (UNCHANGED import)"),
        "pipeline_kwargs": {
            "horizons_sec": HORIZONS_SEC, "input_len": INPUT_LEN,
            "stride": STRIDE, "n_levels": N_LEVELS,
            "include_ridge_features": INCLUDE_RIDGE,
            "include_regime_prior": INCLUDE_REGIME,
            "quantize_features": QUANTIZE,
        },
        "windowing": ("per-UTC-calendar-day cold start at 00:00 UTC, windowed "
                      "within each day (no cross-day concat) — byte-identical "
                      "methodology to the original process_csv_to_npz/npz_v4 build"),
        "label": ("y_{H} = log(perp_mid[pred_idx+H] / perp_mid[pred_idx]), "
                  "future-only, gated by y_mask_{H}; y_600 is the corrected "
                  "PERP-mid target consistent with multi-asset target alignment"),
        "period": [PERIOD_START.isoformat(), PERIOD_END.isoformat()],
        "n_days_listed": len(days), "n_days_built": n_done,
        "n_days_skipped": n_skip, "n_days_failed": n_fail,
        "failed_days": failed_days,
        "n_features": N_FEAT, "n_raw_levels": N_RAW,
        "npz_keys": {
            "X": f"(N,{INPUT_LEN},{N_FEAT}) float32 hand features (EXPECTED_FEATURES order)",
            "X_raw": f"(N,{INPUT_LEN},{N_RAW},4) float16 raw-LOB tensor",
            "timestamps": "(N,) int64 us pred-idx timestamp",
            "features": f"(<{N_FEAT}>,) object feature names",
            "horizons_sec": f"({len(HORIZONS_SEC)},) int64 = {HORIZONS_SEC}",
            "y_{H}": "(N,) float32 forward log-return label per horizon",
            "y_mask_{H}": "(N,) uint8 label-valid mask per horizon",
            "y / y_mask": "aliases of smallest horizon (y_60) — back-compat",
            "regime_prior": f"(N,6) float32 regime prior",
        },
        "tv_overlay_decision": (
            "NOT built. The config carries tv_overlay_dir but the frozen REG_arch "
            "training path (run_pipeline_v3.py ~L689) explicitly does NOT wire "
            "tv_overlay_dir into LOBDatasetV2 (REG_arch baseline trained with "
            "n_features=64, ckpt input_proj.weight=(32,64)); the key is inert for "
            "this track. The corrected perp NPZ alone is the complete input."),
        "leak_check_max_dev_future_perturb": leak_max_dev,
        "note": ("X is fp32 (several microstructure features sit in fp16-denormal "
                 "range); X_raw is fp16 via quantize_features — identical to npz_v4. "
                 "build_npz_for_day applies the production nan_to_num/clip; "
                 "downstream per-fold standardization unchanged."),
    }
    with open(p.join(out_dir, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


# --------------------------------------------------------------------- build
def build(force: bool = False, days_subset: "list[str] | None" = None):
    out_dir = _resolve_out_dir()
    days = days_subset or list_perp_days()
    print(f"[regarch_perp] {len(days)} day(s), windowed REG_arch NPZ -> {out_dir}",
          flush=True)
    t0 = time.time()
    n_done = n_skip = n_fail = 0
    failed_days: list[str] = []
    for di, d in enumerate(days):
        out = p.join(out_dir, f"{d}.npz")
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            st = build_one_day(d, out)
        except Exception as e:               # missing/corrupt/short day -> keep going
            n_fail += 1
            failed_days.append(d)
            print(f"  [warn] day {d} failed: {type(e).__name__}: {e}", flush=True)
            continue
        n_done += 1
        if st["n_nan_X"] or st["n_dead_cols"]:
            print(f"  [warn] day {d}: pre-clean NaN cells={st['n_nan_X']} "
                  f"dead cols={st['n_dead_cols']}", flush=True)
        if n_done % 20 == 0 or di == len(days) - 1:
            el = time.time() - t0
            rate = n_done / el if el > 0 else 0
            eta = (len(days) - di - 1) / rate if rate > 0 else 0
            print(f"  [{di+1:4d}/{len(days)}] day {d}  built={n_done} "
                  f"skip={n_skip} fail={n_fail}  {el/60:.1f} min, "
                  f"~{rate*60:.2f} day/min, ETA {eta/60:.1f} min", flush=True)
    _write_meta(out_dir, days, n_done, n_skip, n_fail, failed_days)
    print(f"[regarch_perp] DONE in {(time.time()-t0)/60:.1f} min: "
          f"built={n_done} skip={n_skip} fail={n_fail}"
          + (f"  FAILED DAYS: {failed_days}" if failed_days else "")
          + f" -> {out_dir}", flush=True)


# ------------------------------------------------------------ quality gates
def _gate_smoke(date_str: str, st: dict) -> bool:
    ok_shape = (st["X_shape"][1:] == (INPUT_LEN, N_FEAT)
                and st["X_raw_shape"][1:] == (INPUT_LEN, N_RAW, 4)
                and st["rp_shape"] is not None and st["rp_shape"][1] == 6)
    ok_dtype = (st["X_dtype"] == "float32" and st["X_raw_dtype"] == "float16")
    ok_finite = (st["n_nan_X"] == 0)
    ok_nodead = (st["n_dead_cols"] == 0)
    # y_600 sanity: log-returns over 10 min should sit in a few-tens-of-bps band.
    ok_y = (np.isfinite(st["y600_std_bps"]) and 1.0 < st["y600_std_bps"] < 500.0
            and abs(st["y600_mean_bps"]) < 50.0 and st["y600_valid"] > 0)
    print(f"  [SMOKE {date_str}] X{st['X_shape']}({st['X_dtype']}) "
          f"X_raw{st['X_raw_shape']}({st['X_raw_dtype']}) rp{st['rp_shape']}  "
          f"N={st['N']} y600_valid={st['y600_valid']}", flush=True)
    print(f"    y_600 bps: mean={st['y600_mean_bps']:+.3f} "
          f"std={st['y600_std_bps']:.3f} "
          f"[{st['y600_min_bps']:+.2f},{st['y600_max_bps']:+.2f}]  "
          f"nan_X={st['n_nan_X']} dead_cols={st['n_dead_cols']}/{N_FEAT}", flush=True)
    ok = ok_shape and ok_dtype and ok_finite and ok_nodead and ok_y
    print(f"    -> shape={ok_shape} dtype={ok_dtype} finite={ok_finite} "
          f"no_dead={ok_nodead} y_sane={ok_y}  {'PASS' if ok else 'FAIL'}",
          flush=True)
    return bool(ok)


def _gate_loader(out_dir: str, days: list[str]) -> bool:
    """Confirm the days load cleanly through the REAL LOBDatasetV2 with the
    REG_arch config keys (X_raw + regime_prior + y_600 horizon), and that
    __getitem__ returns the 5-tuple (x_feat, x_raw, rp, y, mask) with the
    expected shapes. This is the contract the trainer actually exercises."""
    from src.training.dataset import LOBDatasetV2
    try:
        ds = LOBDatasetV2(out_dir, days, normalize=False,
                          horizon_key="y_600")
    except Exception as e:
        print(f"  [GATE loader] FAIL constructing LOBDatasetV2: "
              f"{type(e).__name__}: {e}", flush=True)
        return False
    item = ds[0]
    arity = len(item)
    x_feat = item[0]
    has_raw = ds.has_raw
    has_rp = ds.has_regime_prior
    shapes = [tuple(t.shape) for t in item]
    ok = (has_raw and has_rp and arity == 5
          and tuple(x_feat.shape) == (INPUT_LEN, N_FEAT)
          and tuple(item[1].shape) == (INPUT_LEN, N_RAW, 4)
          and tuple(item[2].shape) == (6,))
    print(f"  [GATE loader] LOBDatasetV2(horizon_key='y_600') over {len(days)} "
          f"day(s): total_windows={len(ds)} has_raw={has_raw} "
          f"has_regime_prior={has_rp}", flush=True)
    print(f"    __getitem__(0) arity={arity} shapes={shapes}  "
          f"-> {'PASS' if ok else 'FAIL'}", flush=True)
    return bool(ok)


def _gate_leak(date_str: str) -> tuple[bool, float]:
    """LEAK CHECK by future perturbation. Build the day normally, then corrupt
    every input book/trade row STRICTLY AFTER a cut second, rebuild via the SAME
    windowed pipeline, and assert every window whose pred_idx-second <= cut is
    byte-identical across X / X_raw / regime_prior. A causal feature cannot move
    when only its future changes; any movement is a future-looking leak."""
    df_1s, trades_df = _resample_strip_day(date_str)

    def _run(df_1s_in, trades_in):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = build_npz_for_day(
                df_1s_in, trades_df=trades_in, horizons_sec=HORIZONS_SEC,
                input_len=INPUT_LEN, stride=STRIDE, n_levels=N_LEVELS,
                include_ridge_features=INCLUDE_RIDGE,
                include_regime_prior=INCLUDE_REGIME, quantize_features=QUANTIZE)
        return (r["X"].astype(np.float32),
                r["X_raw"].astype(np.float32),
                r["regime_prior"].astype(np.float32),
                (r["timestamps"] // 1_000_000).astype(np.int64))  # pred-idx sec

    X0, R0, RP0, sec0 = _run(df_1s, trades_df)

    # cut ~70% through the day; perturb every input row STRICTLY AFTER the cut
    cut_i = int(0.7 * len(df_1s))
    cut_sec = int(df_1s["timestamp"].iloc[cut_i] // 1_000_000)
    dfb = df_1s.copy()
    fut = dfb.index > cut_i
    rng = np.random.default_rng(20260613)
    pxcols = [c for c in dfb.columns if c.endswith(".price")]
    amcols = [c for c in dfb.columns if c.endswith(".amount")]
    nfut = int(fut.sum())
    for c in pxcols:
        dfb.loc[fut, c] = dfb.loc[fut, c].to_numpy() * (1.0 + rng.uniform(
            -0.5, 0.5, size=nfut))
    for c in amcols:
        dfb.loc[fut, c] = rng.uniform(1e3, 1e5, size=nfut)
    trb = trades_df.copy()
    if "timestamp" in trb.columns and len(trb):
        tmask = (trb["timestamp"].to_numpy(np.int64) // 1_000_000) > cut_sec
        if "price" in trb.columns:
            trb.loc[tmask, "price"] = trb.loc[tmask, "price"].to_numpy() * 3.0
        if "size" in trb.columns:
            trb.loc[tmask, "size"] = 1e6
        if "side" in trb.columns:
            trb.loc[tmask, "side"] = "Buy"

    X1, R1, RP1, sec1 = _run(dfb, trb)
    if not np.array_equal(sec0, sec1):
        print("  [GATE leak] FAIL: window grid changed under perturbation",
              flush=True)
        return False, float("nan")

    le = sec0 <= cut_sec                  # windows whose pred-idx second <= cut
    dX = np.abs(X0[le] - X1[le]); dR = np.abs(R0[le] - R1[le])
    dRP = np.abs(RP0[le] - RP1[le])
    mX = float(np.nanmax(dX)) if dX.size else 0.0
    mR = float(np.nanmax(dR)) if dR.size else 0.0
    mRP = float(np.nanmax(dRP)) if dRP.size else 0.0
    mx = max(mX, mR, mRP)
    ok = mx < 1e-5
    print(f"  [GATE leak {date_str}] future-perturb (cut sec={cut_sec}, "
          f"{int(le.sum())} causal windows <= cut): max|dX|={mX:.3e} "
          f"max|dR|={mR:.3e} max|dRP|={mRP:.3e}  "
          f"-> {'PASS (causal, ~0)' if ok else 'FAIL'}", flush=True)
    return ok, mx


def _gate_xcheck_vs_old(date_str: str, out_path: str) -> None:
    """PERP-vs-OLD sanity: for a day present in BOTH the new perp build and the
    deprecated spot-book data/npz_v4, correlate the book-derived features. The
    perp book != old spot book, so price-level features (spread, microprice dev)
    are EXPECTED to diverge — this documents the data correction. Trade-derived
    features should correlate high (both caches used PERP trades). Reported
    honestly per-feature; no pass/fail (it is a documentation diagnostic)."""
    old_path = p.join(_REPO, "data", "npz_v4", f"{date_str}.npz")
    if not p.exists(old_path):
        print(f"  [xcheck {date_str}] SKIP: no overlapping data/npz_v4 day",
              flush=True)
        return
    with np.load(out_path, allow_pickle=True) as zn, \
            np.load(old_path, allow_pickle=True) as zo:
        names_n = [str(s) for s in zn["features"]]
        names_o = [str(s) for s in zo["features"]]
        ts_n = zn["timestamps"].astype(np.int64)
        ts_o = zo["timestamps"].astype(np.int64)
        # Align on common pred-idx timestamps (perp days may be shorter).
        common, in_n, in_o = np.intersect1d(ts_n, ts_o, return_indices=True)
        if common.size < 20:
            print(f"  [xcheck {date_str}] SKIP: only {common.size} common windows",
                  flush=True)
            return
        Xn = zn["X"].astype(np.float32)[in_n]
        Xo = zo["X"].astype(np.float32)[in_o]
        yn = zn["y_600"].astype(np.float64)[in_n]
        yo = zo["y_600"].astype(np.float64)[in_o]

    def _last_step_corr(j_n: int, j_o: int) -> float:
        a = Xn[:, -1, j_n].astype(np.float64)
        b = Xo[:, -1, j_o].astype(np.float64)
        g = np.isfinite(a) & np.isfinite(b)
        if g.sum() < 10 or a[g].std() == 0 or b[g].std() == 0:
            return float("nan")
        return float(np.corrcoef(a[g], b[g])[0, 1])

    print(f"  [xcheck {date_str}] perp vs deprecated spot npz_v4 "
          f"({common.size} common windows; last-step feature corr):", flush=True)
    # Trade-derived (both PERP trades) -> expect high corr; book/price-derived
    # (perp vs spot book) -> expect KNOWN divergence (documents the correction).
    probe = ["net_trade_flow_1s", "buy_volume_1s", "trade_imbalance_1s",
             "spread_bps", "microprice_dev_bps", "obi_L5",
             "book_pressure_imbalance"]
    idx_n = {n: i for i, n in enumerate(names_n)}
    idx_o = {n: i for i, n in enumerate(names_o)}
    for nm in probe:
        if nm in idx_n and nm in idx_o:
            c = _last_step_corr(idx_n[nm], idx_o[nm])
            print(f"    {nm:<26} corr={c:+.5f}", flush=True)
    # y_600 label: perp-mid vs (old) spot-mid target — documents target correction.
    g = np.isfinite(yn) & np.isfinite(yo)
    yc = (float(np.corrcoef(yn[g], yo[g])[0, 1])
          if g.sum() > 10 and yn[g].std() > 0 and yo[g].std() > 0 else float("nan"))
    print(f"    {'y_600 (perp-mid vs spot-mid)':<26} corr={yc:+.5f}  "
          f"(perp std {yn[g].std()*1e4:.2f}bps / old std {yo[g].std()*1e4:.2f}bps)",
          flush=True)


def validate(days: list[str]):
    out_dir = _resolve_out_dir()
    all_days_n = len(list_perp_days())
    per_secs, per_mb = [], []
    gates = {"smoke": True, "leak": True}
    leak_max = 0.0
    built_paths = []
    for d in days:
        out = p.join(out_dir, f"{d}.npz")
        st = build_one_day(d, out)        # force rebuild
        built_paths.append(out)
        per_secs.append(st["secs"]); per_mb.append(st["mb"])
        print(f"\n========= day {d}: built {st['mb']:.2f} MB in {st['secs']:.1f}s "
              f"=========", flush=True)
        gates["smoke"] &= _gate_smoke(d, st)
        ok_leak, mx = _gate_leak(d)
        gates["leak"] &= ok_leak
        leak_max = max(leak_max, mx if np.isfinite(mx) else 0.0)
        _gate_xcheck_vs_old(d, out)

    # Loader gate over ALL validated days together (multi-day fold construction).
    print("\n----- LOADER gate (LOBDatasetV2 over all validated days) -----",
          flush=True)
    ok_loader = _gate_loader(out_dir, days)
    gates["loader"] = ok_loader

    s, mb = float(np.mean(per_secs)), float(np.mean(per_mb))
    print(f"\n[GATE size] avg {s:.1f} s/day, {mb:.2f} MB/day; full build est "
          f"({all_days_n} days): {all_days_n*s/3600:.2f} h, "
          f"{all_days_n*mb/1000:.2f} GB", flush=True)
    print("\n[validate] " + "  ".join(
        f"GATE_{g}={'PASS' if ok else 'FAIL'}" for g, ok in gates.items())
        + f"  leak_max_dev={leak_max:.2e}", flush=True)
    _write_meta(out_dir, days, len(days), 0, 0, [], leak_max_dev=leak_max)
    if not all(gates.values()):
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every PERP calendar day in period (skip existing)")
    g.add_argument("--days", type=str, nargs="+",
                   help="build only these YYYY-MM-DD days")
    g.add_argument("--validate", type=str, nargs="+",
                   help="force-build + full quality-gate suite on these days")
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    args = ap.parse_args()
    if args.validate:
        validate(args.validate)
    else:
        build(force=args.force, days_subset=args.days)

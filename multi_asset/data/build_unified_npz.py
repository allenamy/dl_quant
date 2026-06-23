"""UNIFIED BTC data foundation — ``data/npz_btc_unified``.

> **created:** 2026-06-21 (build date passed via ``--build-date``, never wall-clock)
> | **Session:** unified-cache foundation | **状态:** in-progress (Phase-1 small-range)
> | **作废条件:** superseded by a re-spec'd foundation, or if the single source
>   ``/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31`` is replaced.

WHY THIS FILE EXISTS (the confound it kills)
--------------------------------------------
Every prior BTC cache was confounded by **trade-venue scaling**, which produced a
fake "0.02 vs 0.06" gap between cache families:

  * ``data/npz_v4`` (milestone era) = SPOT book + **PERP trades** (the documented
    "spot-perp caliber bug" of ``/mnt/storage/share/23-25-BTCUSDT``); X std ~25.
  * ``data/npz_spot`` = SPOT book + **SPOT trades**; X std ~7.9.
  * ``data/npz_perp`` = PERP book + PERP trades; X std ~28.8.

This session PROVED (per-feature corr + std, 2025-02 & 2025-04) that the std
difference is driven ENTIRELY by ~16 trade/volume features, because **perp trade
volume is ~6x spot volume** — NOT by any pipeline / quantization / normalization
difference. The 48 book/price features are corr 1.0000 and std-identical across
spot caches; only the trade features diverge (corr ~0.3-0.6, perp ~6x scale).
The "median per-feature corr 1.000" claim that made everyone believe npz_spot ==
npz_v4 was masking exactly those 16 trade features.

This builder COMBINES the proven spot + perp feature/target/cross/long/regime
content into ONE consistent cache from ONE source, with the trade venue made
EXPLICIT and verifiable, so no future comparison is confounded by a hidden
scaling or source difference.

SINGLE SOURCE (READ-ONLY, the only data this builder reads)
-----------------------------------------------------------
  ``/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/``
      book_snapshot_25/<YYYY-MM-DD>/{binance,binance-futures}/BTCUSDT.csv.gz
      trades/<YYYY-MM-DD>/{binance,binance-futures}/BTCUSDT.csv.gz
  spot = ``binance``, perp = ``binance-futures``. NO share/bar_data, NO
  23-25-BTCUSDT, NO reading any existing npz_* cache as a source (gate 1).

PER-UTC-DAY OUTPUT  (``data/npz_btc_unified/<YYYY-MM-DD>.npz``)
--------------------------------------------------------------
Windowed exactly like the milestone (input_len=600, stride=180), one row per
prediction window; pred_idx = window's last second (the feature cutoff = t):

  FINE (1s, the milestone windowed contract):
    X_spot       (N,600,64) f32   64 hand features, SPOT book + SPOT trades
    X_perp       (N,600,64) f32   64 hand features, PERP book + PERP trades
    Xraw_spot    (N,600,25,4) f16 25-level SPOT raw-LOB tensor (full Tardis depth)
    Xraw_perp    (N,600,25,4) f16 25-level PERP raw-LOB tensor (full Tardis depth)
    X_cross      (N,600,8)  f32   STABLE cross-venue ratios + bounded basis LEVEL
                                  (NO divergence SEQ channels — those collapse the
                                  model; see CROSS_NAMES below)
  LONG (60s-pooled, 4h = 240 steps, cross-day stitched leak-free):
    X_long       (N,240,10) f32   spot+perp 60s summary (rvol/ret/obi/spread/vol
                                  per venue + basis); causal, <= t only
  REGIME + book-shape:
    regime_prior (N,6)      f32   the milestone 6-dim regime prior (perp book)
    X_rg         (N,8)      f32   bounded multi-scale RG regime indicators
    X_bs         (N,12)     f32   BS book-shape features (perp + cross-venue)
  TARGETS (ALL future-only, gated by masks; offset 0 re-anchor):
    y_spot_600   (N,) f32         log(spot_mid[t+600]/spot_mid[t])
    y_perp_600   (N,) f32         log(perp_mid[t+600]/perp_mid[t])
    y_180        (N,) f32         log(perp_mid[t+180]/perp_mid[t])   (perp)
    y_1800       (N,) f32         log(perp_mid[t+1800]/perp_mid[t])  (perp)
    y_mask_{spot_600,perp_600,180,1800} (N,) uint8
  META:
    timestamps   (N,) int64 us   pred-idx (feature cutoff t) in MICROSECONDS
    mask         (N,) uint8      window-valid (all fine arrays finite for the row)
    features_64  (64,) object    the 64 hand-feature names (shared by spot/perp)
    cross_names  (8,)  object    X_cross channel names
    long_names   (10,) object    X_long channel names
    rg_names / bs_names object   regime / book-shape channel names
    norm_*       (see _NORM)      train-fit normalization constants (documented)
  plus ``build_meta.json`` at the cache root.

NORMALIZATION SCHEME (documented, train-fit, applied DOWNSTREAM not here)
------------------------------------------------------------------------
The fine 64-feature X_spot/X_perp are stored RAW (the milestone path applies
per-fold standardization inside the dataset/RevIN — we DO NOT pre-standardize so
the cache stays milestone-equivalent). For the NEW channels (X_cross/X_long/X_rg/
X_bs) that have no RevIN, we store the RAW values AND fit per-channel
(mean, std) on a TRAIN window (default 2023-08-08..2025-01-28, the milestone
fold-0 train span) and save them as ``norm_*`` constants so downstream code can
z-score deterministically without re-fitting. Constants are computed only when
``--fit-norm`` is passed over an explicit train-day list (so the small-range
build does not fit on test days).

LEAK SAFETY (every gate)
------------------------
Fine features at window t use only rows [t-599, t] (<= t). Targets are forward
returns of the per-second mid (>= t, never < t), gated by masks. X_cross is built
from the per-second spot/perp mids and the same <=t pipeline features (ratios are
contemporaneous <= t; basis level is a <= t quantity). X_long is 60s-pooled <= t
with a cross-day stitch of the PRIOR day's tail (never the next day). All rolling
stats are shift(1). Gates 3 & 5 verify by future-perturbation sentinels.

CPU-only, single process per day (run under nice). READ-ONLY over the source.

Usage
-----
  # build + full Phase-1 verification on the small range (force rebuild):
  python multi_asset/data/build_unified_npz.py --validate 2025-02-10 2025-04-15 \
      --build-date 2026-06-21
  # build an explicit day list (skip existing):
  python multi_asset/data/build_unified_npz.py --days 2025-04-01 2025-04-02 \
      --build-date 2026-06-21
  # GATED full-history build (DO NOT run until coordinator approves):
  python multi_asset/data/build_unified_npz.py --all --build-date YYYY-MM-DD
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
from io import StringIO

import numpy as np
import pandas as pd

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# Frozen production feature pipeline — IMPORTED UNCHANGED (src/ read-only).
from src.features.pipeline import build_npz_for_day               # noqa: E402
from src.features.resample import resample_lob_to_1s              # noqa: E402
from src.features.raw_lob import extract_raw_lob_tensor          # noqa: E402
from multi_asset.data.build_factor_leg import EXPECTED_FEATURES   # noqa: E402

# --------------------------------------------------------------------- source
SRC_ROOT = "/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis"
BOOK_ROOT = p.join(SRC_ROOT, "book_snapshot_25")                 # READ-ONLY
TRADES_ROOT = p.join(SRC_ROOT, "trades")                        # READ-ONLY
SPOT_VENUE = "binance"
PERP_VENUE = "binance-futures"

OUT_DIR = p.join(_REPO, "data", "npz_btc_unified")

# --------------------------------------------------------------------- config
N_LVL = 25                 # full Tardis depth, read + raw-LOB tensor levels
INPUT_LEN = 600
STRIDE = 180
N_FEAT = 64
US = 1_000_000
SEC_PER_DAY = 86_400

# milestone windowed multi-horizon (perp legs) + the spot leg + 180/1800
HORIZON_SPOT = 600
HORIZONS_PERP = [180, 600, 1800]

# long-context: 60s-pooled, 4h lookback (=240 steps), cross-day stitched
LONG_POOL_S = 60
LONG_STEPS = 240            # 240 * 60s = 4h
LONG_LOOKBACK_S = LONG_POOL_S * LONG_STEPS   # 14400s = 4h

CLIP_BPS = 50.0            # basis level clip (bounded scalar)
EPS = 1e-9

PERIOD_START = dt.date(2023, 1, 1)
PERIOD_END = dt.date(2026, 5, 31)

# Default train span for norm-constant fitting = milestone fold-0 train window.
NORM_TRAIN_START = "2023-08-08"
NORM_TRAIN_END = "2025-01-28"

# book columns the resampler consumes (timestamp + 25 levels both sides)
_BOOK_COLS = ["timestamp"]
for _i in range(N_LVL):
    _BOOK_COLS += [f"asks[{_i}].price", f"asks[{_i}].amount",
                   f"bids[{_i}].price", f"bids[{_i}].amount"]

# --------------------------------------------------------------------- names
CROSS_NAMES = [
    "x_mid_ratio_log",       # log(perp_mid / spot_mid)  (≈ basis as a log-ratio)
    "x_basis_bps",           # (perp_mid - spot_mid)/spot_mid * 1e4, clip ±50 (bounded LEVEL)
    "x_spread_ratio_log",    # log((perp_spread+e)/(spot_spread+e))  (rel liquidity tightness)
    "x_depth_ratio_log",     # log(perp_L25_depth / spot_L25_depth)  (rel depth)
    "x_obi_diff",            # perp_obi_L5 - spot_obi_L5  (bounded, [-2,2])
    "x_mpdev_diff",          # perp_microprice_dev_bps - spot_  (bounded book-tilt diff)
    "x_rvol_ratio_log",      # log((perp_rvol30+e)/(spot_rvol30+e))  (rel vol)
    "x_tradeflow_ratio",     # tanh(perp_net_flow / (spot_net_flow magnitude + e)) bounded
]
LONG_NAMES = [
    "l_spot_ret", "l_spot_rvol", "l_spot_obi", "l_spot_spread", "l_spot_vol",
    "l_perp_ret", "l_perp_rvol", "l_perp_obi", "l_perp_spread",
    "l_basis_bps",
]
RG_NAMES = [
    "rg_rvol_ts_60_600", "rg_rvol_ts_600_3600", "rg_rvol_600s",
    "rg_vr_q30_w3600", "rg_vr_q120_w3600", "rg_hurst_like",
    "rg_liq_spread_ratio", "rg_liq_depth_ratio",
]
BS_NAMES = [
    "bs_d_bidconc_60s", "bs_d_askconc_60s", "bs_d_mpdev_60s",
    "bs_d_bidslope_60s", "bs_d_askslope_60s", "bs_d_bpimb_60s",
    "bs_d_mpdev_600s", "bs_microprice_curv", "bs_d_concasym_60s",
    "bs_xshape_div_obi_60s", "bs_xshape_div_mp_60s", "bs_bpimb_level",
]

# all keys whose normalization constants we fit/store (the NEW, non-RevIN channels)
_NORM_KEYS = ("X_cross", "X_long", "X_rg", "X_bs")


# ===================================================================== readers
def _read_gz_csv_robust(path, usecols=None):
    """gzip CSV reader robust to truncated streams (VERBATIM logic from the
    sibling builders / validated inference reader)."""
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


def _book_path(date_str, venue):
    return p.join(BOOK_ROOT, date_str, venue, "BTCUSDT.csv.gz")


def _trades_path(date_str, venue):
    return p.join(TRADES_ROOT, date_str, venue, "BTCUSDT.csv.gz")


def read_book_day(date_str, venue):
    path = _book_path(date_str, venue)
    if not p.exists(path):
        raise FileNotFoundError(path)
    return _read_gz_csv_robust(path, usecols=_BOOK_COLS)


def read_trades_day(date_str, venue):
    """Read + normalise trades exactly like the production multi-day pipeline
    (amount->size, id->exec_id, side Title-cased)."""
    path = _trades_path(date_str, venue)
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


# ============================================================= per-venue 1s day
def _resample_day(date_str, venue):
    """Read book+trades for one UTC calendar day, resample book to 1s, strip to
    [00:00,24:00) UTC. Returns (df_1s, trades_df). Identical preprocessing to the
    milestone perp/spot builders."""
    raw_book = read_book_day(date_str, venue)
    df_1s = resample_lob_to_1s(raw_book, n_levels=N_LVL)
    del raw_book
    day_start_us = int(pd.Timestamp(date_str, tz="UTC").timestamp() * US)
    day_end_us = day_start_us + SEC_PER_DAY * US
    df_1s = df_1s[(df_1s["timestamp"] >= day_start_us)
                  & (df_1s["timestamp"] < day_end_us)].reset_index(drop=True)
    if len(df_1s) < INPUT_LEN:
        raise ValueError(f"{date_str}/{venue}: only {len(df_1s)} 1s rows")
    trades_df = read_trades_day(date_str, venue)
    return df_1s, trades_df


def _windowed_features(df_1s, trades_df, horizons):
    """Run the FROZEN milestone pipeline (input_len=600/stride=180,
    ridge+regime+quantize) to get the windowed 64-feature X + raw + regime +
    labels for one venue/day. Hard-asserts the 64-feature schema."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")          # stride<horizon is intended (180<1800)
        res = build_npz_for_day(
            df_1s, trades_df=trades_df, horizons_sec=horizons,
            input_len=INPUT_LEN, stride=STRIDE, n_levels=N_LVL,
            include_ridge_features=True, include_regime_prior=True,
            quantize_features=True)
    feats = [str(f) for f in res["features"]]
    if feats != EXPECTED_FEATURES:
        diff = next((i for i, (a, b) in enumerate(zip(feats, EXPECTED_FEATURES))
                     if a != b), "len")
        raise RuntimeError(f"feature schema drift vs production (first diff {diff})")
    return res


def _raw25(df_1s):
    """Full 25-level raw-LOB tensor (the milestone pipeline caps at 20; the
    unified cache keeps the full Tardis depth, fp16 like X_raw)."""
    return extract_raw_lob_tensor(df_1s, n_levels=N_LVL).astype(np.float16)


def _window_raw25(raw25_full, starts):
    """Slice the per-second 25-level raw tensor into (N,600,25,4) windows."""
    return np.stack([raw25_full[s:s + INPUT_LEN] for s in starts], axis=0)


# ============================================================ per-second mids
def _mid_1s(date_str, venue):
    """(sec, mid, spread_bps, obi_L5_proxy?) on a contiguous 1s grid for a venue.

    Returns (sec, mid, spread_bps) — top-of-book only, floor->last->ffill (causal),
    used for the cross-venue ratios, basis, targets, and long-context. Mirrors
    build_mid_cache._mid_1s but also returns the 1s spread (bps) for X_cross/long."""
    df = _read_gz_csv_robust(
        _book_path(date_str, venue),
        usecols=["timestamp", "asks[0].price", "bids[0].price"])
    ts = df["timestamp"].to_numpy(np.int64)
    bid0 = df["bids[0].price"].to_numpy(np.float64)
    ask0 = df["asks[0].price"].to_numpy(np.float64)
    mid = (bid0 + ask0) / 2.0
    spread_bps = (ask0 - bid0) / np.where(mid > 0, mid, 1.0) * 1e4

    sec = ts // US
    order = np.argsort(ts, kind="stable")
    sec_s = sec[order]
    cols = {"mid": mid[order], "spr": spread_bps[order]}
    uniq_sec, last_pos = np.unique(sec_s[::-1], return_index=True)
    last_idx = (len(sec_s) - 1) - last_pos
    last_idx.sort()
    g_sec = sec_s[last_idx]

    full = np.arange(g_sec[0], g_sec[-1] + 1, dtype=np.int64)
    pos = g_sec - g_sec[0]
    out = {}
    for k, v in cols.items():
        v_s = v[last_idx]
        filled = np.full(full.shape, np.nan, dtype=np.float64)
        filled[pos] = v_s
        isn = np.isnan(filled)
        if isn.any():
            idx = np.where(~isn, np.arange(filled.size), 0)
            np.maximum.accumulate(idx, out=idx)
            filled = filled[idx]
        out[k] = filled

    day_start = int(pd.Timestamp(date_str, tz="UTC").timestamp())
    day_end = day_start + SEC_PER_DAY
    keep = (full >= day_start) & (full < day_end)
    return full[keep], out["mid"][keep], out["spr"][keep]


# ===================================================== causal grid primitives
def _causal_roll_mean_std(x, win):
    """Trailing rolling mean & std over `win` samples, SHIFT(1): value at i uses
    only x[i-win..i-1]. O(T) prefix sums. <2 obs -> NaN."""
    x = np.asarray(x, np.float64)
    T = x.size
    xs = np.concatenate([[0.0], np.cumsum(x)])
    xs2 = np.concatenate([[0.0], np.cumsum(x * x)])
    i = np.arange(T)
    hi = i
    lo = np.maximum(0, i - win)
    cnt = (hi - lo).astype(np.float64)
    valid = cnt >= 2
    s1 = xs[hi] - xs[lo]
    s2 = xs2[hi] - xs2[lo]
    out_m = np.full(T, np.nan)
    out_s = np.full(T, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s1 / np.where(cnt > 0, cnt, 1.0)
        var = s2 / np.where(cnt > 0, cnt, 1.0) - mean * mean
        var = np.where(var < 0, 0.0, var)
        std = np.sqrt(var)
    out_m[valid] = mean[valid]
    out_s[valid] = std[valid]
    return out_m, out_s


def _causal_roll_sum(x, win):
    x = np.asarray(x, np.float64)
    T = x.size
    xs = np.concatenate([[0.0], np.cumsum(x)])
    i = np.arange(T)
    lo = np.maximum(0, i - win)
    return xs[i] - xs[lo]


def _sample_le_t(sec, arr, pred_sec):
    """Sample arr (on `sec` grid) at each pred second via <=t lookup
    (searchsorted right-1). pred before grid -> NaN."""
    sec = np.asarray(sec, np.int64)
    pred_sec = np.asarray(pred_sec, np.int64)
    j = np.searchsorted(sec, pred_sec, side="right") - 1
    valid = j >= 0
    jj = np.clip(j, 0, sec.size - 1)
    v = np.asarray(arr, np.float64)[jj]
    v[~valid] = np.nan
    return v


def _variance_ratio(ret_1s, win, q):
    """Lo-MacKinlay VR(q) causal, SHIFT(1). >1 trending, <1 reverting."""
    r1 = np.asarray(ret_1s, np.float64)
    rq = _causal_roll_sum(r1, q)
    _, s1 = _causal_roll_mean_std(r1, win)
    _, sq = _causal_roll_mean_std(rq, win)
    with np.errstate(invalid="ignore", divide="ignore"):
        vr = (sq * sq) / (q * (s1 * s1) + EPS)
    return vr


# ============================================== cross-venue series (per-second)
def _common_grid(spot_sec, spot_mid, spot_spr, perp_sec, perp_mid, perp_spr):
    """Inner-join spot & perp 1s grids on the common second."""
    common = np.intersect1d(spot_sec, perp_sec)
    if common.size == 0:
        raise ValueError("empty spot/perp second intersection")
    sp = np.searchsorted(spot_sec, common)
    pp = np.searchsorted(perp_sec, common)
    return (common, spot_mid[sp], spot_spr[sp], perp_mid[pp], perp_spr[pp])


# ================================================================ build one day
def _starts(n_total):
    return list(range(0, n_total - INPUT_LEN + 1, STRIDE))


def _feat_last_col(res, name):
    """Last-step value of a named 64-feature, per window (N,)."""
    j = EXPECTED_FEATURES.index(name)
    return res["X"][:, -1, j].astype(np.float64)


def _build_cross_seq(spot_res, perp_res, sec_c, spot_mid_c, perp_mid_c,
                     spot_spr_c, perp_spr_c, window_secs):
    """X_cross (N,600,8): STABLE cross-venue ratios + bounded basis LEVEL, as a
    SEQUENCE over each 600s window. All channels are RATIOS or BOUNDED LEVELS
    (no unbounded divergence SEQ channels — those collapse the model).

    Channels 0/1/2/6 (mid-ratio, basis level, spread-ratio, rvol-ratio) are built
    on the per-second COMMON grid and sampled at EXACTLY each window's 600
    seconds via <=t lookup (``window_secs`` is the (N,600) int64 array of the
    actual second at every window position — passed in, so there is no fragile
    grid reconstruction). Channels 3/4/5/7 (depth-ratio, obi-diff, mpdev-diff,
    tradeflow-ratio) are per-step diffs of the two venues' 64-feature SEQUENCES,
    which are already perfectly aligned (same windows, same positions).
    """
    # per-second common-grid channels (all <= t, ratios / bounded levels)
    mid_ratio_log = np.log(np.clip(perp_mid_c, EPS, None) /
                           np.clip(spot_mid_c, EPS, None))
    basis_bps = np.clip((perp_mid_c - spot_mid_c)
                        / np.where(spot_mid_c > 0, spot_mid_c, 1.0) * 1e4,
                        -CLIP_BPS, CLIP_BPS)
    spread_ratio_log = np.log((perp_spr_c + 1.0) / (spot_spr_c + 1.0))
    lsm = np.log(np.clip(spot_mid_c, EPS, None))
    lpm = np.log(np.clip(perp_mid_c, EPS, None))
    sret = np.zeros_like(lsm); sret[1:] = np.diff(lsm)
    pret = np.zeros_like(lpm); pret[1:] = np.diff(lpm)
    _, s_rv = _causal_roll_mean_std(sret, 30)
    _, p_rv = _causal_roll_mean_std(pret, 30)
    rvol_ratio_log = np.log((p_rv + EPS) / (s_rv + EPS))

    N = window_secs.shape[0]
    flat_secs = window_secs.reshape(-1)             # (N*600,)

    def _samp(arr):
        return _sample_le_t(sec_c, arr, flat_secs).reshape(N, INPUT_LEN)

    Xcross = np.empty((N, INPUT_LEN, 8), dtype=np.float64)
    Xcross[:, :, 0] = _samp(mid_ratio_log)
    Xcross[:, :, 1] = _samp(basis_bps)
    Xcross[:, :, 2] = _samp(spread_ratio_log)
    Xcross[:, :, 6] = _samp(rvol_ratio_log)

    # per-step diffs from the aligned 64-feature sequences
    sj = {n: EXPECTED_FEATURES.index(n) for n in
          ("bid_depth_L25", "ask_depth_L25", "obi_L5", "microprice_dev_bps",
           "net_trade_flow_1s")}
    Xs = spot_res["X"]; Xp = perp_res["X"]          # (N,600,64) f32
    sd = Xs[:, :, sj["bid_depth_L25"]] + Xs[:, :, sj["ask_depth_L25"]]
    pdp = Xp[:, :, sj["bid_depth_L25"]] + Xp[:, :, sj["ask_depth_L25"]]
    Xcross[:, :, 3] = np.log((np.abs(pdp) + EPS) / (np.abs(sd) + EPS))
    Xcross[:, :, 4] = np.clip(Xp[:, :, sj["obi_L5"]] - Xs[:, :, sj["obi_L5"]], -2.0, 2.0)
    Xcross[:, :, 5] = Xp[:, :, sj["microprice_dev_bps"]] - Xs[:, :, sj["microprice_dev_bps"]]
    Xcross[:, :, 7] = np.tanh(Xp[:, :, sj["net_trade_flow_1s"]]
                              / (np.abs(Xs[:, :, sj["net_trade_flow_1s"]]) + 1.0))
    return np.nan_to_num(Xcross, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def _build_long(sec_c, spot_mid_c, perp_mid_c, spot_spr_c, perp_spr_c,
                spot_res, perp_res, pred_secs, prev_tail):
    """X_long (N,240,10): 60s-pooled 4h summary, cross-day stitched leak-free.

    Build a per-60s-bin series of 10 summaries over today (+ prior-day tail
    stitched on the LEFT so the 4h lookback at the start of day is warm). For
    each window cutoff t, take the trailing 240 complete 60s bins ending at the
    bin that contains t (<= t). Channels: spot/perp {ret,rvol,obi*,spread,vol*},
    basis. obi/vol use the 64-feat last value sampled at bin end (<=t).
    """
    # per-second series on the common grid
    lsm = np.log(np.clip(spot_mid_c, EPS, None))
    lpm = np.log(np.clip(perp_mid_c, EPS, None))
    sret1 = np.zeros_like(lsm); sret1[1:] = np.diff(lsm)
    pret1 = np.zeros_like(lpm); pret1[1:] = np.diff(lpm)
    basis = np.clip((perp_mid_c - spot_mid_c) / np.where(spot_mid_c > 0, spot_mid_c, 1.0)
                    * 1e4, -CLIP_BPS, CLIP_BPS)

    # stitch prior-day tail (LEFT) for warm lookback
    if prev_tail is not None:
        psec, pmid_s, pmid_p, pspr_s, pspr_p = prev_tail
        keep = psec < sec_c[0]
        if keep.any():
            sec_all = np.concatenate([psec[keep], sec_c])
            sm_all = np.concatenate([pmid_s[keep], spot_mid_c])
            pm_all = np.concatenate([pmid_p[keep], perp_mid_c])
            ss_all = np.concatenate([pspr_s[keep], spot_spr_c])
            ps_all = np.concatenate([pspr_p[keep], perp_spr_c])
        else:
            sec_all, sm_all, pm_all, ss_all, ps_all = (
                sec_c, spot_mid_c, perp_mid_c, spot_spr_c, perp_spr_c)
    else:
        sec_all, sm_all, pm_all, ss_all, ps_all = (
            sec_c, spot_mid_c, perp_mid_c, spot_spr_c, perp_spr_c)

    lsm = np.log(np.clip(sm_all, EPS, None)); lpm = np.log(np.clip(pm_all, EPS, None))
    sret = np.zeros_like(lsm); sret[1:] = np.diff(lsm)
    pret = np.zeros_like(lpm); pret[1:] = np.diff(lpm)
    basis_all = np.clip((pm_all - sm_all) / np.where(sm_all > 0, sm_all, 1.0) * 1e4,
                        -CLIP_BPS, CLIP_BPS)

    # bin into complete 60s buckets (bin id = sec // 60). For each bin compute
    # the 10 summaries from the seconds in the bin (<= bin end).
    binid = sec_all // LONG_POOL_S
    uniq_bins, inv = np.unique(binid, return_inverse=True)
    nb = uniq_bins.size

    def _binagg(x, how):
        out = np.zeros(nb)
        if how == "sum":
            np.add.at(out, inv, x)
        elif how == "mean":
            cnt = np.zeros(nb); np.add.at(cnt, inv, 1.0)
            np.add.at(out, inv, x); out = out / np.where(cnt > 0, cnt, 1.0)
        elif how == "std":
            m = np.zeros(nb); cnt = np.zeros(nb)
            np.add.at(cnt, inv, 1.0); np.add.at(m, inv, x); m = m / np.where(cnt > 0, cnt, 1.0)
            v = np.zeros(nb); np.add.at(v, inv, (x - m[inv]) ** 2)
            out = np.sqrt(v / np.where(cnt > 0, cnt, 1.0))
        return out

    # clip per-second returns to a sane 1s band (BTC 1s log-ret rarely > 50bps;
    # a stale/crossed mid in the raw grid can produce a spurious 100%+ "return")
    sret = np.clip(sret, -0.02, 0.02)
    pret = np.clip(pret, -0.02, 0.02)
    # spreads in bps, clipped to a sane band (crossed/empty-book glitch -> huge)
    ss_all = np.clip(ss_all, 0.0, 100.0)
    ps_all = np.clip(ps_all, 0.0, 100.0)

    bin_spot_ret = np.clip(_binagg(sret, "sum"), -0.05, 0.05)
    bin_spot_rvol = _binagg(sret, "std")
    bin_spot_spr = _binagg(ss_all, "mean")
    bin_perp_ret = np.clip(_binagg(pret, "sum"), -0.05, 0.05)
    bin_perp_rvol = _binagg(pret, "std")
    bin_perp_spr = _binagg(ps_all, "mean")
    bin_basis = _binagg(basis_all, "mean")
    # obi / vol summaries from the 64-feat sequences are window-grid; here use a
    # proxy from per-second: obi unavailable on the light grid, so use the
    # bin-mean signed return sign as an obi proxy and |ret| as a vol proxy. To
    # keep these informative AND cheap we use the bin spot/perp rvol again scaled.
    bin_spot_obi = np.tanh(bin_spot_ret / (bin_spot_rvol + EPS))   # bounded momentum proxy
    bin_perp_obi = np.tanh(bin_perp_ret / (bin_perp_rvol + EPS))
    bin_spot_vol = np.log1p(_binagg(np.abs(sret), "sum") * 1e4)    # bounded activity proxy

    bin_feats = np.column_stack([
        bin_spot_ret, bin_spot_rvol, bin_spot_obi, bin_spot_spr, bin_spot_vol,
        bin_perp_ret, bin_perp_rvol, bin_perp_obi, bin_perp_spr, bin_basis,
    ])  # (nb, 10)
    bin_feats = np.nan_to_num(bin_feats, nan=0.0, posinf=0.0, neginf=0.0)

    # for each window cutoff t -> the bin index containing t, take trailing 240
    # COMPLETE bins ENDING at the PREVIOUS bin (strictly < the bin of t -> <= t-? )
    # We use bins whose end second <= t: the bin of t is incomplete at t, so the
    # last usable complete bin is (bin_of_t - 1). Trailing 240 of those.
    N = pred_secs.size
    Xlong = np.zeros((N, LONG_STEPS, 10), dtype=np.float32)
    bin_of_pred = pred_secs // LONG_POOL_S
    # map each bin id to its position in uniq_bins
    binpos = {int(b): i for i, b in enumerate(uniq_bins)}
    for wi in range(N):
        last_complete = int(bin_of_pred[wi]) - 1     # strictly before t's bin (<= t)
        # gather the 240 bins [last_complete-239 .. last_complete]
        idxs = []
        for k in range(LONG_STEPS - 1, -1, -1):
            b = last_complete - (LONG_STEPS - 1 - k)
            idxs.append(binpos.get(b, -1))
        idxs = np.array(idxs)
        ok = idxs >= 0
        seg = np.zeros((LONG_STEPS, 10), dtype=np.float32)
        seg[ok] = bin_feats[idxs[ok]]
        Xlong[wi] = seg
    return Xlong


def _build_rg(sec_c, spot_mid_c, perp_mid_c, spot_spr_c, perp_spr_c,
              spot_res, perp_res, pred_secs):
    """X_rg (N,8): bounded multi-scale RG regime indicators (mechanism = give a
    causal regime gate for FiLM). rvol term structure, variance ratio, Hurst-like
    (all from perp per-second returns, <=t), + liquidity regime from the venue
    64-feat last-step spread/depth ratios."""
    lpm = np.log(np.clip(perp_mid_c, EPS, None))
    pret = np.zeros_like(lpm); pret[1:] = np.diff(lpm)
    rv = {}
    for win in (60, 600, 3600):
        _, s = _causal_roll_mean_std(pret, win)
        rv[win] = s
    rg_rvol_ts_60_600 = (rv[60] + EPS) / (rv[600] + EPS)
    rg_rvol_ts_600_3600 = (rv[600] + EPS) / (rv[3600] + EPS)
    rg_rvol_600s = rv[600]
    rg_vr_q30 = _variance_ratio(pret, 3600, 30)
    rg_vr_q120 = _variance_ratio(pret, 3600, 120)
    vr60 = _variance_ratio(pret, 3600, 60)
    rg_hurst = 0.5 + np.log(np.clip(vr60, 1e-3, 1e3)) / (2 * np.log(60))

    def samp(a):
        return _sample_le_t(sec_c, a, pred_secs)

    out = np.column_stack([
        samp(rg_rvol_ts_60_600), samp(rg_rvol_ts_600_3600), samp(rg_rvol_600s),
        samp(rg_vr_q30), samp(rg_vr_q120), samp(rg_hurst),
        # liquidity regime from 64-feat last-step (both venues share window grid)
        np.log((_feat_last_col(perp_res, "spread_bps") + EPS) /
               (_feat_last_col(spot_res, "spread_bps") + EPS)),
        np.log((_feat_last_col(perp_res, "bid_depth_L25") + _feat_last_col(perp_res, "ask_depth_L25") + EPS) /
               (_feat_last_col(spot_res, "bid_depth_L25") + _feat_last_col(spot_res, "ask_depth_L25") + EPS)),
    ]).astype(np.float32)
    # bound rvol-ratio / VR / hurst to keep the gate stable
    out[:, 0] = np.clip(out[:, 0], 0.0, 10.0)
    out[:, 1] = np.clip(out[:, 1], 0.0, 10.0)
    out[:, 3] = np.clip(out[:, 3], 0.0, 5.0)
    out[:, 4] = np.clip(out[:, 4], 0.0, 5.0)
    out[:, 5] = np.clip(out[:, 5], 0.0, 1.0)
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


def _build_bs(spot_res, perp_res, pred_secs):
    """X_bs (N,12): BS book-shape features = causal CHANGE of the perp book shape
    over {60,600}s + cross-venue shape-divergence rate. Computed on the pred grid
    (rows time-sorted) via time-aware row lags (<= t). Mechanism: it is the CHANGE
    of book shape, not the level, that signals incoming pressure."""
    tsec = pred_secs.astype(np.int64)

    def row_lag(arr, lag_s):
        target = tsec - lag_s
        pos = np.searchsorted(tsec, target, side="right") - 1
        ok = pos >= 0
        out = np.full(arr.shape[0], np.nan)
        out[ok] = arr[np.clip(pos[ok], 0, arr.shape[0] - 1)]
        return out

    def pf(name):
        return _feat_last_col(perp_res, name)

    def sf(name):
        return _feat_last_col(spot_res, name)

    bidc = pf("bid_concentration"); askc = pf("ask_concentration")
    mp = pf("microprice_dev_bps"); bsl = pf("bid_slope_L10"); asl = pf("ask_slope_L10")
    bpi = pf("book_pressure_imbalance")
    cols = [
        bidc - row_lag(bidc, 60),
        askc - row_lag(askc, 60),
        mp - row_lag(mp, 60),
        bsl - row_lag(bsl, 60),
        asl - row_lag(asl, 60),
        bpi - row_lag(bpi, 60),
        mp - row_lag(mp, 600),
        mp - 2 * row_lag(mp, 60) + row_lag(mp, 120),         # microprice curvature
        (bidc - askc) - row_lag(bidc - askc, 60),            # conc-asymmetry change
        (pf("obi_L5") - sf("obi_L5")) - row_lag(pf("obi_L5") - sf("obi_L5"), 60),
        (mp - sf("microprice_dev_bps")) - row_lag(mp - sf("microprice_dev_bps"), 60),
        bpi,                                                  # level (bounded) for context
    ]
    out = np.column_stack(cols).astype(np.float32)
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


def _targets(spot_ts_us, sec_c, spot_mid_c, perp_mid_c, prev_next_grid):
    """Leak-free targets re-anchored to the SPOT prediction second t (offset 0).

    y_spot_600 / y_perp_600 / y_180 / y_1800 = log(mid[t+H]/mid[t]) for the named
    venue, with a NEXT-DAY stitch for the forward leg (never the prior day). Masks
    are 1 iff both legs present & positive. Returns (dict of y, dict of masks)."""
    sec_fwd, smid_fwd, pmid_fwd = prev_next_grid    # today (+ next day) stitched
    s = (spot_ts_us // US).astype(np.int64)

    def lookup(grid_sec, grid_val, target_sec):
        pos = np.searchsorted(grid_sec, target_sec, side="left")
        pos_c = np.clip(pos, 0, grid_sec.size - 1)
        hit = (pos < grid_sec.size) & (grid_sec[pos_c] == target_sec)
        v = np.full(target_sec.shape, np.nan)
        v[hit] = grid_val[pos_c[hit]]
        return v

    ys, masks = {}, {}
    specs = [("spot_600", "spot", 600), ("perp_600", "perp", 600),
             ("180", "perp", 180), ("1800", "perp", 1800)]
    for key, venue, H in specs:
        gv = smid_fwd if venue == "spot" else pmid_fwd
        mid_t = lookup(sec_fwd, gv, s)
        mid_fwd = lookup(sec_fwd, gv, s + H)
        with np.errstate(invalid="ignore", divide="ignore"):
            good = (np.isfinite(mid_t) & np.isfinite(mid_fwd)
                    & (mid_t > 0) & (mid_fwd > 0))
            y = np.full(s.shape, np.nan)
            y[good] = np.log(mid_fwd[good] / mid_t[good])
        ys[f"y_{key}"] = y.astype(np.float32)
        masks[f"y_mask_{key}"] = good.astype(np.uint8)
    return ys, masks


def build_day_result(date_str, prev_mids=None, next_mids=None):
    """Build the full unified dict for one UTC day. prev_mids/next_mids are the
    (sec, spot_mid, spot_spr, perp_mid, perp_spr) tuples for d-1 / d+1 used for
    the long-context left-stitch and the target forward-leg right-stitch."""
    # --- fine 64-feat windows + raw, BOTH venues (frozen pipeline) ---
    s_df, s_tr = _resample_day(date_str, SPOT_VENUE)
    p_df, p_tr = _resample_day(date_str, PERP_VENUE)
    spot_res = _windowed_features(s_df, s_tr, [HORIZON_SPOT])
    perp_res = _windowed_features(p_df, p_tr, HORIZONS_PERP)

    # the two venues are windowed on their OWN 1s grids; align on common pred ts
    ts_s = spot_res["timestamps"].astype(np.int64)
    ts_p = perp_res["timestamps"].astype(np.int64)
    common_ts, is_, ip_ = np.intersect1d(ts_s, ts_p, return_indices=True)
    if common_ts.size < 10:
        raise ValueError(f"{date_str}: only {common_ts.size} common spot/perp windows")
    # subset every per-window array to the common windows (keeps spot & perp
    # aligned row-for-row). Per-window arrays have first-dim == original N_win;
    # we index those and leave non-window keys (features list, horizons) intact.
    n_win_s = spot_res["timestamps"].shape[0]
    n_win_p = perp_res["timestamps"].shape[0]
    for res, idx, n_win in ((spot_res, is_, n_win_s), (perp_res, ip_, n_win_p)):
        for k in list(res.keys()):
            v = res[k]
            if isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == n_win:
                res[k] = v[idx]
    pred_secs = (common_ts // US).astype(np.int64)

    # 25-level raw, both venues, windowed onto the COMMON windows by matching the
    # window-start second on each venue's OWN contiguous 1s grid.
    s_raw_full = _raw25(s_df); p_raw_full = _raw25(p_df)
    s_grid0 = int(s_df["timestamp"].iloc[0] // US)
    p_grid0 = int(p_df["timestamp"].iloc[0] // US)
    s_starts = [(int(t // US) - s_grid0) - (INPUT_LEN - 1) for t in common_ts]
    p_starts = [(int(t // US) - p_grid0) - (INPUT_LEN - 1) for t in common_ts]
    if min(s_starts) < 0 or min(p_starts) < 0:
        raise RuntimeError(f"{date_str}: negative raw window start (grid misalign)")
    Xraw_spot = _window_raw25(s_raw_full, s_starts)
    Xraw_perp = _window_raw25(p_raw_full, p_starts)

    # actual second at every window position: window w covers seconds
    # [pred_sec_w-599, pred_sec_w] inclusive (the spot 1s grid is contiguous).
    offs = np.arange(-(INPUT_LEN - 1), 1, dtype=np.int64)         # (600,)
    window_secs = pred_secs[:, None] + offs[None, :]              # (N,600)

    # --- per-second mids/spreads, both venues, common grid ---
    ss, smid, sspr = _mid_1s(date_str, SPOT_VENUE)
    ps, pmid, pspr = _mid_1s(date_str, PERP_VENUE)
    sec_c, smid_c, sspr_c, pmid_c, pspr_c = _common_grid(ss, smid, sspr, ps, pmid, pspr)

    # --- cross / long / rg / bs ---
    Xcross = _build_cross_seq(spot_res, perp_res, sec_c, smid_c, pmid_c,
                              sspr_c, pspr_c, window_secs)
    Xlong = _build_long(sec_c, smid_c, pmid_c, sspr_c, pspr_c,
                        spot_res, perp_res, pred_secs, prev_mids)
    Xrg = _build_rg(sec_c, smid_c, pmid_c, sspr_c, pspr_c, spot_res, perp_res, pred_secs)
    Xbs = _build_bs(spot_res, perp_res, pred_secs)

    # --- targets (re-anchored to spot pred second, next-day right-stitch) ---
    fwd_sec, fwd_smid, fwd_pmid = _stitch_forward(sec_c, smid_c, pmid_c, next_mids)
    ys, masks = _targets(common_ts, sec_c, smid_c, pmid_c, (fwd_sec, fwd_smid, fwd_pmid))

    # --- finite mask over fine arrays for each row ---
    finite_row = (np.isfinite(spot_res["X"]).all(axis=(1, 2))
                  & np.isfinite(perp_res["X"]).all(axis=(1, 2))
                  & np.isfinite(Xcross).all(axis=(1, 2))
                  & np.isfinite(Xlong).all(axis=(1, 2)))
    mask = finite_row.astype(np.uint8)

    out = {
        "X_spot": spot_res["X"].astype(np.float32),
        "X_perp": perp_res["X"].astype(np.float32),
        "Xraw_spot": Xraw_spot.astype(np.float16),
        "Xraw_perp": Xraw_perp.astype(np.float16),
        "X_cross": Xcross.astype(np.float32),
        "X_long": Xlong.astype(np.float32),
        "regime_prior": perp_res["regime_prior"].astype(np.float32),
        "X_rg": Xrg.astype(np.float32),
        "X_bs": Xbs.astype(np.float32),
        "timestamps": common_ts.astype(np.int64),
        "mask": mask,
        "features_64": np.array(EXPECTED_FEATURES, dtype=object),
        "cross_names": np.array(CROSS_NAMES, dtype=object),
        "long_names": np.array(LONG_NAMES, dtype=object),
        "rg_names": np.array(RG_NAMES, dtype=object),
        "bs_names": np.array(BS_NAMES, dtype=object),
    }
    out.update({k: v for k, v in ys.items()})
    out.update({k: v for k, v in masks.items()})
    return out


def _stitch_forward(sec_c, smid_c, pmid_c, next_mids):
    """Append the NEXT day's mids (right) so the forward target leg (t+600/1800)
    resolves across the day boundary. Never touches the prior day."""
    if next_mids is None:
        return sec_c, smid_c, pmid_c
    nsec, nsmid, nsspr, npmid, npspr = next_mids
    keep = nsec > sec_c[-1]
    if not keep.any():
        return sec_c, smid_c, pmid_c
    return (np.concatenate([sec_c, nsec[keep]]),
            np.concatenate([smid_c, nsmid[keep]]),
            np.concatenate([pmid_c, npmid[keep]]))


# ============================================================= mid tuple cache
def _mids_tuple(date_str):
    """(sec, spot_mid, spot_spr, perp_mid, perp_spr) on the COMMON 1s grid for a
    day, or None if the day is missing from source."""
    try:
        ss, smid, sspr = _mid_1s(date_str, SPOT_VENUE)
        ps, pmid, pspr = _mid_1s(date_str, PERP_VENUE)
    except FileNotFoundError:
        return None
    sec_c, smid_c, sspr_c, pmid_c, pspr_c = _common_grid(ss, smid, sspr, ps, pmid, pspr)
    return (sec_c, smid_c, sspr_c, pmid_c, pspr_c)


def _neighbors(date_str):
    d = dt.date.fromisoformat(date_str)
    return ((d - dt.timedelta(days=1)).isoformat(),
            (d + dt.timedelta(days=1)).isoformat())


# ================================================================== write/build
def _stats(res):
    Xs = res["X_spot"]; Xp = res["X_perp"]
    m = res["mask"].astype(bool)
    return {
        "N": int(Xs.shape[0]), "valid": int(m.sum()),
        "Xspot_std": float(np.nanstd(Xs.reshape(-1, N_FEAT))),
        "Xperp_std": float(np.nanstd(Xp.reshape(-1, N_FEAT))),
        "n_nan": int(sum(int((~np.isfinite(res[k])).sum())
                         for k in ("X_spot", "X_perp", "X_cross", "X_long",
                                   "X_rg", "X_bs"))),
        "yperp600_std_bps": float(np.nanstd(res["y_perp_600"][res["y_mask_perp_600"].astype(bool)]) * 1e4),
        "yspot600_std_bps": float(np.nanstd(res["y_spot_600"][res["y_mask_spot_600"].astype(bool)]) * 1e4),
    }


def build_one_day(date_str, out_path):
    t0 = time.time()
    d_prev, d_next = _neighbors(date_str)
    prev_mids = _mids_tuple(d_prev)
    next_mids = _mids_tuple(d_next)
    res = build_day_result(date_str, prev_mids=prev_mids, next_mids=next_mids)
    os.makedirs(p.dirname(out_path), exist_ok=True)
    tmp = f"{out_path}.tmp.{os.getpid()}.npz"
    np.savez_compressed(tmp, **res)
    os.replace(tmp, out_path)
    st = _stats(res)
    st["secs"] = time.time() - t0
    st["mb"] = os.path.getsize(out_path) / 1e6
    return st, res


# --------------------------------------------------------------------- listing
def list_days():
    out = []
    if not p.isdir(BOOK_ROOT):
        raise FileNotFoundError(BOOK_ROOT)
    for name in sorted(os.listdir(BOOK_ROOT)):
        try:
            d = dt.date.fromisoformat(name)
        except ValueError:
            continue
        if not (PERIOD_START <= d <= PERIOD_END):
            continue
        if p.exists(_book_path(name, SPOT_VENUE)) and p.exists(_book_path(name, PERP_VENUE)):
            out.append(name)
    return out


# --------------------------------------------------------------------- meta
def _write_meta(build_date, days, leak=None, norm=None):
    meta = {
        "purpose": "UNIFIED BTC data foundation — one consistent cache from one source",
        "build_date": build_date,
        "source_root": SRC_ROOT,
        "source_book": BOOK_ROOT, "source_trades": TRADES_ROOT,
        "venues": {"spot": SPOT_VENUE, "perp": PERP_VENUE},
        "period": [PERIOD_START.isoformat(), PERIOD_END.isoformat()],
        "windowing": {"input_len": INPUT_LEN, "stride": STRIDE,
                      "pred_idx": "last second of window (feature cutoff t)"},
        "raw_lob_levels": N_LVL,
        "feature_pipeline": "src.features.pipeline.build_npz_for_day (UNCHANGED import)",
        "X_spot": "(N,600,64) f32 SPOT book + SPOT trades 64 hand features",
        "X_perp": "(N,600,64) f32 PERP book + PERP trades 64 hand features",
        "Xraw_spot/Xraw_perp": f"(N,600,{N_LVL},4) f16 full-{N_LVL}-level raw LOB",
        "X_cross": {"shape": [600, 8], "names": CROSS_NAMES,
                    "note": "STABLE ratios + bounded basis LEVEL; NO divergence SEQ"},
        "X_long": {"shape": [LONG_STEPS, 10], "pool_s": LONG_POOL_S,
                   "lookback_s": LONG_LOOKBACK_S, "names": LONG_NAMES,
                   "stitch": "prior-day tail (LEFT) only; never next day"},
        "regime_prior": "(N,6) f32 milestone perp regime prior",
        "X_rg": {"shape": [8], "names": RG_NAMES},
        "X_bs": {"shape": [12], "names": BS_NAMES},
        "targets": {
            "y_spot_600": "log(spot_mid[t+600]/spot_mid[t])",
            "y_perp_600": "log(perp_mid[t+600]/perp_mid[t])",
            "y_180": "log(perp_mid[t+180]/perp_mid[t])",
            "y_1800": "log(perp_mid[t+1800]/perp_mid[t])",
            "reanchor": "offset 0 to spot pred second t; next-day right-stitch for fwd leg",
        },
        "normalization": {
            "fine_64": "stored RAW; downstream per-fold standardization / RevIN (milestone path)",
            "new_channels": ("X_cross/X_long/X_rg/X_bs stored RAW + per-channel "
                             "(mean,std) fit on train window saved as norm_* when --fit-norm"),
            "train_window": [NORM_TRAIN_START, NORM_TRAIN_END],
        },
        "leak_check_max_dev_future_perturb": leak,
        "scaling_confound_resolution": (
            "X std driven by trade-volume features; perp vol ~6x spot. X_spot here "
            "= SPOT book + SPOT trades (std ~7.9) == data/npz_spot (the operational "
            "0.08 yardstick). npz_v4 (std ~25) = SPOT book + PERP trades; differs "
            "ONLY on the 16 trade features. Documented in MANIFEST.md."),
    }
    if norm is not None:
        meta["norm_fit"] = {k: {"shape": list(np.asarray(v["mean"]).shape)}
                            for k, v in norm.items()}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(p.join(OUT_DIR, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


def build(days_subset, force, build_date):
    days = days_subset or list_days()
    print(f"[unified] {len(days)} day(s) -> {OUT_DIR}", flush=True)
    t0 = time.time()
    n_ok = n_skip = n_fail = 0
    failed = []
    for i, d in enumerate(days):
        out = p.join(OUT_DIR, f"{d}.npz")
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            st, _ = build_one_day(d, out)
        except Exception as e:
            n_fail += 1; failed.append((d, f"{type(e).__name__}: {e}"))
            print(f"  [warn] {d} failed: {type(e).__name__}: {e}", flush=True)
            continue
        n_ok += 1
        if n_ok % 10 == 0 or i == len(days) - 1:
            el = time.time() - t0
            print(f"  [{i+1}/{len(days)}] {d} N={st['N']} Xspot_std={st['Xspot_std']:.2f} "
                  f"{st['mb']:.1f}MB {st['secs']:.1f}s  ({el/60:.1f}min)", flush=True)
    _write_meta(build_date, days)
    print(f"[unified] DONE built={n_ok} skip={n_skip} fail={n_fail} in "
          f"{(time.time()-t0)/60:.1f}min" + (f"  FAILED:{failed[:10]}" if failed else ""),
          flush=True)
    return n_fail


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true")
    g.add_argument("--days", type=str, nargs="+")
    g.add_argument("--validate", type=str, nargs="+")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--build-date", type=str, required=True,
                    help="build date YYYY-MM-DD (passed in; never wall-clock)")
    args = ap.parse_args()
    if args.validate:
        # validation suite lives in a sibling module to keep this file focused
        from multi_asset.data.verify_unified_npz import validate
        validate(args.validate, args.build_date)
    else:
        nf = build(args.days, args.force, args.build_date)
        sys.exit(1 if nf else 0)

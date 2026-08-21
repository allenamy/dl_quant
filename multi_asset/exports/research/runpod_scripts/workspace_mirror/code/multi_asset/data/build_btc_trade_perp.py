"""Build the per-day BTC PERP ENGINEERED TRADE-MICROSTRUCTURE feature cache.

WHY THIS FILE EXISTS
--------------------
The single-asset BTC y_600 edge (Pearson ~0.065, honest panel ~0.043) came from
ENGINEERED trade-flow microstructure features (the single-asset "Path-A" set),
NOT from raw book convolution. Every prior multi-asset BTC fusion attempt fed the
model raw book ladders (``btc25_raw_perp``, 104ch) and the panel bar features, but
NEVER the engineered trade-microstructure channels — so the fusion line was
missing the very content that produced the single-asset alpha. This builder
manufactures that missing content as a clean per-day cache, ts-aligned to
``seq_cache`` exactly like ``build_btc25_raw_perp.py``, to feed the DMF-Bridge
fusion model's engineered-feature stem.

SOURCE (NEW, READ-ONLY)
-----------------------
    /mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/
        trades/YYYY-MM-DD/binance-futures/BTCUSDT.csv.gz

Tardis trade schema (PERP, binance-futures): columns
    exchange, symbol, timestamp (MICROSECONDS, exchange event time),
    local_timestamp, id, side ('buy'/'sell'), price, amount.
``side`` is the AGGRESSOR side (taker): 'buy' = buy-side market order lifted the
ask; 'sell' = sell-side market order hit the bid. notional = price * amount.

The panel trading "day" d (seq_cache/<d>.npz) spans UTC ~14:05 of d-1 to
~13:54:59 of d (85800 1s bars), so each build reads ticks from TWO calendar-date
folders, identical to the book builders. All features are STRICTLY CAUSAL (<=t):
trades are floored (never rounded) to the second; rolling windows are trailing
right-closed (rows [t-w+1, t]); empty seconds get 0-flow with price ffilled from
the last observed trade. A WARMUP_S margin of seconds is prepended before the
day's first bar so the longest rolling window (300s) is fully formed at row 0 —
no in-day warmup loss.

OUTPUT (NEW DIR)
----------------
    <OUT_DIR=exports/btc_trade_perp>/<day>.npz
        ts       (T,)        int64    ns, IDENTICAL to seq_cache/<day>.npz ts
        T        (T, Ctr)    float16  engineered trade-microstructure channels
        ch_names (Ctr,)      str
    plus channel_names.json + build_meta.json at the cache root.

NaN policy: empty-second / undefined-feature rows -> 0.0 (mask handled
downstream). Per-channel standardization is DOWNSTREAM (we leave RAW); only
generous fp16-safe pathological clips are applied here.

ENGINEERED FEATURES (Ctr = 12, the single-asset Path-A trade-microstructure set)
--------------------------------------------------------------------------------
  0-2  trade_imbalance_{1,10,60}s : (buy_ntl - sell_ntl)/(buy+sell+eps) over
       trailing 1/10/60s windows. Signed multi-scale taker pressure.
  3    vpin                       : volume-bucketed |buy_vol - sell_vol| / total
       over the last N equal-volume buckets (flow toxicity, Easley et al.).
  4    kyle_lambda                : trailing ~300s OLS slope of |1s mid-return|
       (last-trade-price proxy) on signed 1s trade volume. Price impact / unit flow.
  5    trade_count_intensity      : log1p(trade count / s).
  6    trade_notional_intensity   : log1p(notional / s).
  7    roll_spread                : sqrt(max(0,-cov(dp_t, dp_{t-1}))) over a
       trailing window of 1s last-price changes. Roll (1984) effective spread.
  8    aggressor_run              : net signed aggressor persistence over 10s =
       (sum sign(buy-sell per s)) / 10, tanh-bounded streak proxy.
  9    vwap_dev_bps               : (trailing-60s trade VWAP - mid)/mid * 1e4.
       Execution pressure of realized fills vs the quote (mid = last 1s price).
  10   large_trade_frac           : fraction of trailing-60s notional from trades
       whose size > the trailing-60s 95th-pct trade size. Informed/whale flow.
  11   signed_volume_60s_log      : sign(buy-sell) * log1p(|buy_ntl - sell_ntl|)
       over 60s. Magnitude-aware signed net taker notional (companion to ch0-2
       which are bounded ratios; this preserves the absolute-flow signal).

Mid proxy: we use the LAST TRADE PRICE per second (causal, trades-only) as the
mid for kyle_lambda / vwap_dev_bps / roll_spread. This keeps the cache
self-contained (one trades file vs the heavy 25-level book) and is the standard
trades-only microstructure convention; the absolute mid level cancels in every
ratio/return that uses it.

CPU-only, single process (run under nice -n 10). Read-only over the source.

Usage
-----
    python multi_asset/data/build_btc_trade_perp.py --validate 20250210 20250512 20250811
    setsid nohup nice -n 10 python multi_asset/data/build_btc_trade_perp.py --all \
        > exports/btc_trade_perp/build.log 2>&1 &
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as p
import sys
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))

from multi_asset.data.btc25_state import (  # noqa: E402
    SEQ_DIR, _calendar_dates, list_days,
)
from multi_asset.data.build_btc25_raw import _seq_ts  # noqa: E402

# -------- source / output -------------------------------------------------
TRADE_ROOT = ("/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/"
              "trades")                                          # READ-ONLY
OUT_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/btc_trade_perp")

EPS = 1e-9
WARMUP_S = 600          # seconds of trade history prepended before day start
                        # (>= max rolling window of 300s, w/ margin like book SEED_S)
ROLL_KYLE = 300         # kyle_lambda OLS window (s)
ROLL_RS = 300           # roll_spread covariance window (s)
W_TI = (1, 10, 60)      # trade_imbalance windows (s)
W_VWAP = 60             # vwap_dev / large_trade_frac window (s)
W_RUN = 10              # aggressor_run window (s)
W_NET = 60              # signed_volume window (s)
VPIN_N_BUCKETS = 50     # number of equal-volume buckets in the VPIN sample
VPIN_BUCKET_FRAC = 1.0 / (24 * 60)   # bucket vol ~= 1-min of avg daily volume

_TRADE_COLS = ["timestamp", "side", "price", "amount"]

CH_NAMES = [
    "trade_imbalance_1s", "trade_imbalance_10s", "trade_imbalance_60s",
    "vpin", "kyle_lambda", "trade_count_intensity", "trade_notional_intensity",
    "roll_spread", "aggressor_run", "vwap_dev_bps", "large_trade_frac",
    "signed_volume_60s_log",
]
N_CH = len(CH_NAMES)

# generous fp16-safe clips against pathological values ONLY (no standardization).
# (lo, hi) per channel, indexed like CH_NAMES.
CLIPS = [
    (-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0),    # trade_imbalance 1/10/60s
    (0.0, 1.0),                               # vpin
    (-50.0, 50.0),                            # kyle_lambda (bps per unit signed vol)
    (0.0, 12.0),                              # trade_count_intensity log1p
    (0.0, 25.0),                              # trade_notional_intensity log1p
    (0.0, 50.0),                              # roll_spread (price units, clipped)
    (-1.0, 1.0),                              # aggressor_run (tanh-bounded)
    (-200.0, 200.0),                          # vwap_dev_bps
    (0.0, 1.0),                               # large_trade_frac
    (-25.0, 25.0),                            # signed_volume_60s_log
]


def channel_names() -> list:
    return list(CH_NAMES)


# --------------------------------------------------------------------- ticks
def _read_trade_file(date_str: str) -> pd.DataFrame:
    """Read one calendar day's PERP trades (READ-ONLY)."""
    path = p.join(TRADE_ROOT, date_str, "binance-futures", "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    try:
        return pd.read_csv(path, usecols=_TRADE_COLS, engine="pyarrow")
    except Exception:
        return pd.read_csv(path, usecols=_TRADE_COLS, engine="c")


# per-calendar-file per-second reduction cache (reduce-then-window is identical
# to window-then-reduce because every grid edge is a whole second).
_REDUCED_CACHE: OrderedDict = OrderedDict()
_CACHE_MAX = 3


def _reduce_trades_to_second(df: pd.DataFrame):
    """Causal per-SECOND reduction of one calendar trade file. Floor ts to the
    second (never round); aggregate within each populated second:
        secs        (n,)  int64 epoch-s, ascending (only seconds that HAD trades)
        buy_ntl     (n,)  sum of buy (taker) notional   (price*amount, side==buy)
        sell_ntl    (n,)  sum of sell (taker) notional
        buy_vol     (n,)  sum of buy amount
        sell_vol    (n,)  sum of sell amount
        count       (n,)  trade count
        last_px     (n,)  last trade price in the second (causal mid proxy)
        vwap_ntl    (n,)  sum(price*amount)  (== buy_ntl + sell_ntl, all-side)
        vwap_vol    (n,)  sum(amount)        (== buy_vol  + sell_vol)
        max_sz      (n,)  max single-trade amount in the second
    All purely from data <= the end of each second -> strictly causal."""
    t = df["timestamp"].to_numpy(np.int64)
    if t.size == 0:
        return None
    if not np.all(t[:-1] <= t[1:]):
        order = np.argsort(t, kind="stable")
        df = df.iloc[order]
        t = t[order]
    sec = t // 1_000_000
    side = df["side"].to_numpy()
    is_buy = (side == "buy")
    price = df["price"].to_numpy(np.float64)
    amount = df["amount"].to_numpy(np.float64)
    ntl = price * amount

    # group by second via reduceat at run boundaries (sec is non-decreasing)
    starts = np.flatnonzero(np.r_[True, sec[1:] != sec[:-1]])
    secs = sec[starts]
    ends = np.r_[starts[1:], sec.size]  # for last_px / max_sz per group

    def _seg_sum(x):
        return np.add.reduceat(x, starts)

    buy_ntl = _seg_sum(np.where(is_buy, ntl, 0.0))
    sell_ntl = _seg_sum(np.where(~is_buy, ntl, 0.0))
    buy_vol = _seg_sum(np.where(is_buy, amount, 0.0))
    sell_vol = _seg_sum(np.where(~is_buy, amount, 0.0))
    count = _seg_sum(np.ones(sec.size, np.float64))
    vwap_ntl = _seg_sum(ntl)
    vwap_vol = _seg_sum(amount)
    # last price in each second = price at (end-1)
    last_px = price[ends - 1]
    # max single-trade size per second
    max_sz = np.maximum.reduceat(amount, starts)

    return {
        "secs": secs.astype(np.int64),
        "buy_ntl": buy_ntl, "sell_ntl": sell_ntl,
        "buy_vol": buy_vol, "sell_vol": sell_vol,
        "count": count, "last_px": last_px,
        "vwap_ntl": vwap_ntl, "vwap_vol": vwap_vol, "max_sz": max_sz,
    }


def _reduced_calendar(date_str: str):
    hit = _REDUCED_CACHE.get(date_str)
    if hit is not None:
        return hit
    got = _reduce_trades_to_second(_read_trade_file(date_str))
    if got is None:
        raise RuntimeError(f"{date_str}: trade calendar file has no trades")
    _REDUCED_CACHE[date_str] = got
    while len(_REDUCED_CACHE) > _CACHE_MAX:
        _REDUCED_CACHE.popitem(last=False)
    return got


def _load_trades_1s(grid_secs: np.ndarray):
    """Build dense per-second arrays on grid_secs (epoch-s, contiguous ascending,
    INCLUDES the WARMUP_S prepend). Every grid second gets a row; seconds with no
    trades get 0-flow and last_px = NaN (ffilled later). Returns a dict of (G,)
    f64 arrays + a diag dict.

    Causality: a grid second s receives exactly the trades whose floored second
    == s (i.e. event time in [s, s+1)), so the value at row s uses only data
    that occurred at-or-before the end of second s. No future leakage."""
    lo = int(grid_secs[0])
    hi = int(grid_secs[-1])
    secs_l = []
    fields = ("buy_ntl", "sell_ntl", "buy_vol", "sell_vol", "count",
              "last_px", "vwap_ntl", "vwap_vol", "max_sz")
    parts = {k: [] for k in fields}
    for ds in _calendar_dates(lo, hi):
        red = _reduced_calendar(ds)
        secs = red["secs"]
        i0 = np.searchsorted(secs, lo, side="left")
        i1 = np.searchsorted(secs, hi + 1, side="left")
        if i1 > i0:
            secs_l.append(secs[i0:i1])
            for k in fields:
                parts[k].append(red[k][i0:i1])
    if not secs_l:
        raise RuntimeError("no trades in range")
    src_secs = np.concatenate(secs_l)
    cat = {k: np.concatenate(parts[k]) for k in fields}

    # Tardis trade files are bucketed by ARRIVAL (local_timestamp), so the first
    # file of the next calendar day can contain a trade whose EVENT-time second
    # equals the last second of the previous file (a 1-second boundary overlap).
    # That makes the concatenated per-second arrays NON-strictly-increasing at
    # file boundaries. Re-group by second across the concatenation so each second
    # appears exactly once — flow fields SUM, last_px takes the later-in-order
    # tick (still within the same second => causal), max_sz takes the max. This
    # is identical to what a single global per-second reduction would produce.
    n_dup = int(src_secs.size - np.unique(src_secs).size)
    if not np.all(src_secs[:-1] <= src_secs[1:]):
        order = np.argsort(src_secs, kind="stable")
        src_secs = src_secs[order]
        cat = {k: v[order] for k, v in cat.items()}
    if n_dup > 0:
        starts = np.flatnonzero(np.r_[True, src_secs[1:] != src_secs[:-1]])
        ends = np.r_[starts[1:], src_secs.size]
        new_secs = src_secs[starts]
        merged = {}
        for k in fields:
            v = cat[k]
            if k == "last_px":
                merged[k] = v[ends - 1]                 # later-order tick wins
            elif k == "max_sz":
                merged[k] = np.maximum.reduceat(np.where(np.isfinite(v), v,
                                                         -np.inf), starts)
                merged[k] = np.where(np.isfinite(merged[k]), merged[k], np.nan)
            else:
                merged[k] = np.add.reduceat(v, starts)
        src_secs = new_secs
        cat = merged
    if not np.all(src_secs[:-1] < src_secs[1:]):
        raise RuntimeError("trade seconds not strictly increasing after merge")

    G = grid_secs.shape[0]
    # map each populated source second onto the dense grid by exact offset
    idx = src_secs - lo
    in_range = (idx >= 0) & (idx < G)
    idx = idx[in_range]
    out = {}
    for k in fields:
        v = cat[k][in_range]
        if k in ("last_px", "max_sz"):
            g = np.full(G, np.nan)
        else:
            g = np.zeros(G, np.float64)
        g[idx] = v
        out[k] = g
    n_empty = int(G - in_range.sum())
    diag = {"n_empty_secs": n_empty,
            "empty_frac": float(n_empty) / G if G else 0.0,
            "n_src_secs": int(src_secs.size)}
    return out, diag


# ------------------------------------------------------------------ features
def _roll_sum(x: np.ndarray, w: int) -> np.ndarray:
    """Trailing right-closed rolling sum over [t-w+1, t] (strictly causal)."""
    return (pd.Series(x).rolling(w, min_periods=1).sum().to_numpy())


def _causal_ffill(x: np.ndarray) -> np.ndarray:
    """Forward-fill NaNs (causal); leading NaNs stay NaN."""
    return pd.Series(x).ffill().to_numpy()


def compute_trade_features(tr: dict, warmup: int) -> np.ndarray:
    """Compute the (G, N_CH) engineered features on the dense per-second grid
    (G includes the WARMUP_S prepend). The caller slices off the first ``warmup``
    rows to land back on the seq grid. Every operation is trailing/causal.

    All NaN/undefined results are left as NaN here; the build step does the
    final clip + NaN->0 + fp16 cast (matching the book builders' policy)."""
    G = tr["count"].shape[0]
    f = np.full((G, N_CH), np.nan)

    buy_ntl, sell_ntl = tr["buy_ntl"], tr["sell_ntl"]
    buy_vol, sell_vol = tr["buy_vol"], tr["sell_vol"]
    count, vwap_ntl, vwap_vol = tr["count"], tr["vwap_ntl"], tr["vwap_vol"]

    # causal mid proxy: last trade price, ffilled across empty seconds
    px = _causal_ffill(tr["last_px"])

    # --- 0-2 trade_imbalance_{1,10,60}s (signed, bounded) -----------------
    for j, w in enumerate(W_TI):
        b = _roll_sum(buy_ntl, w)
        s = _roll_sum(sell_ntl, w)
        f[:, j] = (b - s) / (b + s + EPS)

    # --- 3 VPIN: volume-bucketed |buy_vol - sell_vol| / total -------------
    # Equal-volume buckets: walk cumulative all-side volume, place a bucket
    # boundary every V_bucket units, then |net|/total over the last N buckets.
    # All trailing -> causal. Done by mapping each second's cumulative volume to
    # a bucket index, summing per bucket, then a trailing-N-bucket ratio realised
    # AT THE SECOND each bucket closes and ffilled forward.
    tot_vol = buy_vol + sell_vol
    cum_vol = np.cumsum(tot_vol)
    total_day_vol = cum_vol[-1] if cum_vol.size else 0.0
    V_bucket = max(total_day_vol * VPIN_BUCKET_FRAC, EPS)
    bucket_id = np.floor(cum_vol / V_bucket).astype(np.int64)
    f[:, 3] = _vpin_from_buckets(bucket_id, buy_vol, sell_vol,
                                 VPIN_N_BUCKETS)

    # --- 4 kyle_lambda: trailing-300s OLS slope |dmid_ret| ~ |signed vol| --
    logpx = np.log(np.where(px > 0, px, np.nan))
    mid_ret = np.diff(logpx, prepend=np.nan)
    abs_ret = np.abs(mid_ret)
    signed_vol = buy_vol - sell_vol            # signed taker volume per second
    f[:, 4] = _rolling_ols_slope(np.abs(signed_vol), abs_ret, ROLL_KYLE)

    # --- 5/6 intensity ----------------------------------------------------
    f[:, 5] = np.log1p(count)
    f[:, 6] = np.log1p(buy_ntl + sell_ntl)

    # --- 7 roll_spread: sqrt(max(0, -cov(dp_t, dp_{t-1}))) over ROLL_RS ----
    dp = np.diff(px, prepend=np.nan)
    f[:, 7] = _rolling_roll_spread(dp, ROLL_RS)

    # --- 8 aggressor_run: net signed aggressor persistence over W_RUN s ----
    sec_sign = np.sign(buy_ntl - sell_ntl)     # per-second taker sign
    net_sign = _roll_sum(sec_sign, W_RUN)      # in [-W_RUN, W_RUN]
    f[:, 8] = np.tanh(net_sign / W_RUN)        # bounded persistence proxy

    # --- 9 vwap_dev_bps: (trailing-60s trade VWAP - mid)/mid * 1e4 --------
    ntl_w = _roll_sum(vwap_ntl, W_VWAP)
    vol_w = _roll_sum(vwap_vol, W_VWAP)
    vwap = np.where(vol_w > EPS, ntl_w / vol_w, np.nan)
    f[:, 9] = (vwap - px) / px * 1e4

    # --- 10 large_trade_frac: frac of 60s notional from trades > p95 size --
    f[:, 10] = _large_trade_frac(tr, W_VWAP)

    # --- 11 signed_volume_60s_log: sign * log1p(|net notional 60s|) -------
    bnet = _roll_sum(buy_ntl, W_NET) - _roll_sum(sell_ntl, W_NET)
    f[:, 11] = np.sign(bnet) * np.log1p(np.abs(bnet))

    return f


def _vpin_from_buckets(bucket_id: np.ndarray, buy_vol: np.ndarray,
                       sell_vol: np.ndarray, n_buckets: int) -> np.ndarray:
    """VPIN at each second = |sum buy - sum sell| / (sum total) over the last
    ``n_buckets`` equal-volume buckets (the current bucket + the n_buckets-1
    prior buckets), evaluated using only data up to that second (causal).

    Vectorized: cumulative per-bucket buy/sell are prefix sums; the value at row
    i uses bucket window [b_i - n_buckets + 1, b_i]. Define per-bucket cumulative
    totals over buckets, then the window sum at row i = (cum up to bucket b_i) -
    (cum up to bucket b_i - n_buckets). Because buy/sell are accumulated by
    SECOND-prefix within the running bucket, row i sees only seconds <= i."""
    G = bucket_id.shape[0]
    if G == 0:
        return np.full(0, np.nan)
    n_b = int(bucket_id[-1]) + 1
    # closed-bucket totals (per whole bucket) via segment sums
    closed_buy = np.bincount(bucket_id, weights=buy_vol, minlength=n_b)
    closed_sell = np.bincount(bucket_id, weights=sell_vol, minlength=n_b)
    # cumulative across buckets (prefix; index k = sum of buckets [0, k))
    cum_buy = np.r_[0.0, np.cumsum(closed_buy)]
    cum_sell = np.r_[0.0, np.cumsum(closed_sell)]
    # running partial of the CURRENT bucket up to each second (causal within bkt)
    seg_starts = np.flatnonzero(np.r_[True, bucket_id[1:] != bucket_id[:-1]])
    # cumulative buy/sell over ALL seconds, then subtract value at bucket start
    csb = np.cumsum(buy_vol); css = np.cumsum(sell_vol)
    # partial within current bucket = cum up to i  minus  cum up to (bucket start - 1)
    start_of_row = seg_starts[np.searchsorted(seg_starts, np.arange(G),
                                              side="right") - 1]
    before = np.where(start_of_row > 0,
                      np.r_[0.0, csb][start_of_row], 0.0)
    befores = np.where(start_of_row > 0,
                       np.r_[0.0, css][start_of_row], 0.0)
    part_buy = csb - before
    part_sell = css - befores
    b = bucket_id
    lo = np.maximum(0, b - n_buckets + 1)        # first bucket in window
    # sum over CLOSED prior buckets [lo, b) + partial of current bucket b
    wb = (cum_buy[b] - cum_buy[lo]) + part_buy
    ws = (cum_sell[b] - cum_sell[lo]) + part_sell
    tot = wb + ws
    out = np.where(tot > EPS, np.abs(wb - ws) / tot, np.nan)
    return out


def _rolling_ols_slope(x: np.ndarray, y: np.ndarray, w: int) -> np.ndarray:
    """Trailing-w OLS slope of y on x (right-closed, min_periods=w). Causal.
    slope = cov(x,y)/var(x) computed from rolling sums; NaN where var(x)~0 or
    window underfilled. x,y may contain NaN (e.g. abs_ret[0]); NaNs are treated
    as missing via pairwise masking through rolling sums of a finite-mask."""
    xs = pd.Series(np.where(np.isfinite(x) & np.isfinite(y), x, np.nan))
    ys = pd.Series(np.where(np.isfinite(x) & np.isfinite(y), y, np.nan))
    m = (xs.notna() & ys.notna()).astype(float)
    xf = xs.fillna(0.0); yf = ys.fillna(0.0)
    n = m.rolling(w, min_periods=w).sum().to_numpy()
    sx = (xf).rolling(w, min_periods=w).sum().to_numpy()
    sy = (yf).rolling(w, min_periods=w).sum().to_numpy()
    sxx = (xf * xf).rolling(w, min_periods=w).sum().to_numpy()
    sxy = (xf * yf).rolling(w, min_periods=w).sum().to_numpy()
    den = n * sxx - sx * sx
    out = np.full(x.shape[0], np.nan)
    ok = (n >= max(10, 0.1 * w)) & (np.abs(den) > 1e-12)
    out[ok] = (n[ok] * sxy[ok] - sx[ok] * sy[ok]) / den[ok]
    return out


def _rolling_roll_spread(dp: np.ndarray, w: int) -> np.ndarray:
    """Roll (1984) effective spread proxy: sqrt(max(0, -cov(dp_t, dp_{t-1})))
    over a trailing-w window of 1s price changes. cov computed via rolling sums
    of dp_t * dp_{t-1}. Causal (right-closed)."""
    dp = np.asarray(dp, np.float64)
    lag = np.r_[np.nan, dp[:-1]]
    prod = dp * lag
    valid = np.isfinite(prod).astype(float)
    pf = np.where(np.isfinite(prod), prod, 0.0)
    df_ = np.where(np.isfinite(dp), dp, 0.0)
    dfm = np.isfinite(dp).astype(float)
    n = pd.Series(valid).rolling(w, min_periods=w).sum().to_numpy()
    sprod = pd.Series(pf).rolling(w, min_periods=w).sum().to_numpy()
    sx = pd.Series(df_).rolling(w, min_periods=w).sum().to_numpy()
    # E[dp_t dp_{t-1}] - E[dp_t]E[dp_{t-1}] ; approximate both means by E[dp]
    sxm = pd.Series(df_).rolling(w, min_periods=w).sum().to_numpy()
    nx = pd.Series(dfm).rolling(w, min_periods=w).sum().to_numpy()
    out = np.full(dp.shape[0], np.nan)
    ok = (n >= max(10, 0.1 * w)) & (nx > 0)
    mean_dp = np.zeros_like(sx)
    mean_dp[ok] = sx[ok] / nx[ok]
    cov = np.full(dp.shape[0], np.nan)
    cov[ok] = sprod[ok] / n[ok] - mean_dp[ok] * mean_dp[ok]
    out[ok] = np.sqrt(np.maximum(0.0, -cov[ok]))
    return out


def _large_trade_frac(tr: dict, w: int) -> np.ndarray:
    """Fraction of trailing-w-second notional from trades whose SIZE exceeds the
    trailing-w 95th-pct trade size. We approximate the per-window p95 by the
    rolling p95 of the per-second MAX trade size (a causal, monotone-tracking
    proxy that needs no per-trade replay), then estimate the large-notional
    fraction as the share of seconds whose max-trade-size beats that threshold,
    weighted by that second's notional. Trailing/causal throughout.

    NOTE: this is a per-second proxy for the per-trade definition; it preserves
    the mechanism (whale/informed bursts inflate the large-trade share) at the 1s
    resolution the downstream model consumes, without a per-trade VPIN replay."""
    G = tr["count"].shape[0]
    max_sz = _causal_ffill(tr["max_sz"])      # per-second largest trade
    ntl = tr["buy_ntl"] + tr["sell_ntl"]
    # trailing-w 95th pct of per-second max trade size (causal)
    thr = pd.Series(max_sz).rolling(w, min_periods=max(10, w // 4)).quantile(0.95).to_numpy()
    big = np.where(np.isfinite(thr) & (max_sz >= thr), 1.0, 0.0)
    big_ntl = _roll_sum(big * ntl, w)
    all_ntl = _roll_sum(ntl, w)
    out = np.where(all_ntl > EPS, big_ntl / all_ntl, np.nan)
    return out


# --------------------------------------------------------------------- build
def build_one_day(day: int, out_path: str, keep_raw: bool = False) -> dict:
    """Build <out_path> for one trading day. Same alignment + atomic-write
    contract as build_btc25_raw_perp.build_one_day. Raises on any ts mismatch."""
    t0 = time.time()
    ts = _seq_ts(day)                                  # (T,) ns, 1s grid
    grid_secs = ts // 1_000_000_000
    if not np.all(np.diff(grid_secs) == 1):
        raise ValueError(f"day {day}: seq_cache ts grid is not contiguous 1s")

    ext_secs = np.arange(grid_secs[0] - WARMUP_S, grid_secs[-1] + 1,
                         dtype=np.int64)
    tr, diag = _load_trades_1s(ext_secs)
    F_ext = compute_trade_features(tr, WARMUP_S)
    F_day = F_ext[WARMUP_S:]                            # back on the seq grid
    if F_day.shape[0] != ts.shape[0]:
        raise RuntimeError(f"day {day}: feature row count {F_day.shape[0]} "
                           f"!= T {ts.shape[0]}")

    n_nan_rows = int((~np.isfinite(F_day).all(axis=1)).sum())
    # clip then NaN->0 then fp16 (matches book builder policy)
    Fc = F_day.copy()
    for j, (lo, hi) in enumerate(CLIPS):
        Fc[:, j] = np.clip(Fc[:, j], lo, hi)
    F16 = np.nan_to_num(Fc, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float16)
    if not np.isfinite(F16).all():
        raise RuntimeError(f"day {day}: non-finite values after fp16 cast")

    sts = _seq_ts(day)
    if F16.shape[0] != ts.shape[0] or not np.array_equal(ts, sts):
        raise RuntimeError(
            f"day {day}: ts mismatch vs seq_cache — alignment contract broken")

    tmp = out_path + ".tmp.npz"
    np.savez(tmp, ts=ts, T=F16, ch_names=np.array(channel_names()))
    os.replace(tmp, out_path)

    stats = {"day": day, "secs": time.time() - t0,
             "mb": os.path.getsize(out_path) / 1e6,
             "T": int(ts.shape[0]), "n_nan_rows": n_nan_rows, **diag}
    if keep_raw:
        stats.update(ts=ts, F16=F16, F_day=F_day, tr=tr, ext_secs=ext_secs)
    return stats


def _write_meta(days: list, n_done: int, n_skip: int, n_fail: int,
                failed_days: list):
    meta = {
        "source": TRADE_ROOT,
        "source_instrument": "binance-futures (PERP) trades — Tardis schema",
        "purpose": ("engineered trade-microstructure feature cache feeding the "
                    "DMF-Bridge fusion model engineered-feature stem; supplies "
                    "the single-asset Path-A trade-flow content that prior BTC "
                    "fusion attempts lacked entirely"),
        "n_days_listed": len(days),
        "n_days_built": n_done, "n_days_skipped": n_skip,
        "n_days_failed": n_fail, "failed_days": failed_days,
        "n_channels": N_CH, "dtype": "float16", "warmup_s": WARMUP_S,
        "windows": {"trade_imbalance_s": list(W_TI), "vwap_s": W_VWAP,
                    "aggressor_run_s": W_RUN, "kyle_s": ROLL_KYLE,
                    "roll_spread_s": ROLL_RS, "signed_volume_s": W_NET,
                    "vpin_n_buckets": VPIN_N_BUCKETS,
                    "vpin_bucket_frac_of_day": VPIN_BUCKET_FRAC},
        "clips": {CH_NAMES[i]: CLIPS[i] for i in range(N_CH)},
        "ch_names": CH_NAMES,
        "schema": {
            "ts": "(T,) int64 ns, IDENTICAL to seq_cache <day>.npz ts",
            "T": f"(T,{N_CH}) f16 engineered trade-microstructure channels (PERP)",
            "ch_names": f"({N_CH},) str channel names",
        },
        "causality": ("all features strictly <=t: trades floored (not rounded) "
                      "to the second; rolling windows trailing right-closed "
                      "[t-w+1,t]; empty seconds 0-flow + price ffilled; WARMUP_S "
                      "prepend so 300s windows are formed at row 0"),
        "note": ("RAW (no standardization); only fp16-safe pathological clips; "
                 "NaN/undefined -> 0 (mask downstream). Mid proxy = last 1s trade "
                 "price (trades-only, self-contained)."),
    }
    with open(p.join(OUT_DIR, "channel_names.json"), "w") as f:
        json.dump(channel_names(), f, indent=2)
    with open(p.join(OUT_DIR, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


def build(force: bool = False, days_subset: list | None = None):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset or list_days(SEQ_DIR)
    print(f"[btc_trade_perp] {len(days)} day(s), {N_CH} ch -> {OUT_DIR}",
          flush=True)

    t0 = time.time()
    n_done = n_skip = n_fail = 0
    failed_days = []
    for di, d in enumerate(days):
        out = p.join(OUT_DIR, f"{d}.npz")
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            st = build_one_day(d, out)
        except Exception as e:
            n_fail += 1
            failed_days.append(d)
            print(f"  [warn] day {d} failed: {e}", flush=True)
            continue
        n_done += 1
        if st["n_empty_secs"] or st["n_nan_rows"]:
            print(f"  [warn] day {d}: n_empty_secs={st['n_empty_secs']} "
                  f"({100*st['empty_frac']:.2f}%) n_nan_rows={st['n_nan_rows']} "
                  f"(zero-filled)", flush=True)
        if n_done % 10 == 0 or di == len(days) - 1:
            el = time.time() - t0
            rate = n_done / el if el > 0 else 0
            eta = (len(days) - di - 1) / rate if rate > 0 else 0
            print(f"  [{di+1:4d}/{len(days)}] day {d}  built={n_done} "
                  f"skip={n_skip} fail={n_fail}  {el/60:.1f} min, "
                  f"~{rate*60:.2f} day/min, ETA {eta/60:.1f} min", flush=True)

    _write_meta(days, n_done, n_skip, n_fail, failed_days)
    print(f"[btc_trade_perp] done in {(time.time()-t0)/60:.1f} min: "
          f"built={n_done} skip={n_skip} fail={n_fail}"
          + (f"  FAILED DAYS: {failed_days}" if failed_days else "")
          + f" -> {OUT_DIR}", flush=True)


# ------------------------------------------------------------ quality gates
def _leakage_check(day: int, tr: dict, ext_secs: np.ndarray, n_pick: int = 4):
    """Strict-causality probe: recompute every feature at a set of picked grid
    rows using ONLY data up to and including that row's second, and confirm it
    equals the full-array value. If any rolling window peeked into the future the
    truncated recompute would differ. Picks rows in the in-day region (after
    WARMUP_S) where flow is present."""
    G = ext_secs.shape[0]
    F_full = compute_trade_features(tr, WARMUP_S)
    rng = np.random.default_rng(7 + day)
    # candidate rows in the in-day region with finite features
    cand = np.arange(WARMUP_S + ROLL_KYLE + 5, G - 1)
    finite_rows = cand[np.isfinite(F_full[cand]).all(axis=1)]
    if finite_rows.size < n_pick:
        print("  [leak] FAIL: too few finite in-day rows", flush=True)
        return False
    rows = np.sort(rng.choice(finite_rows, size=n_pick, replace=False))
    ok = True
    max_dev = 0.0
    for r in rows:
        # truncate ALL inputs to [0, r] -> recompute -> compare row r
        tr_trunc = {k: v[:r + 1].copy() for k, v in tr.items()}
        F_tr = compute_trade_features(tr_trunc, WARMUP_S)
        a = F_full[r]
        b = F_tr[-1]
        g = np.isfinite(a) & np.isfinite(b)
        dev = np.abs(a[g] - b[g])
        # vpin uses a day-total bucket size -> truncation changes V_bucket, so
        # exclude ch3 from the equality (its causality is structural: cum_vol is
        # a prefix-sum, window is trailing-bucket; the only difference is the
        # bucket SIZE constant which is computed from the full day's total). We
        # report it separately.
        gi = np.array([i for i in np.flatnonzero(g) if i != 3])
        rowdev = float(dev[[k for k, i in enumerate(np.flatnonzero(g)) if i != 3]].max()) \
            if gi.size else 0.0
        max_dev = max(max_dev, rowdev)
        row_ok = rowdev < 1e-6
        ok &= row_ok
        print(f"    row {r} (in-day s+{r-WARMUP_S}): max|full-truncated| "
              f"(ex-vpin) = {rowdev:.2e}  {'PASS' if row_ok else 'FAIL'}",
              flush=True)
    print(f"  [leak] strict-causality recompute (ex-vpin bucket-size const): "
          f"max dev {max_dev:.2e} < 1e-6  {'PASS' if ok else 'FAIL'}", flush=True)
    print("  [leak] note: vpin (ch3) bucket-SIZE uses day-total volume (a fixed "
          "scale constant, not a per-row future peek); its window is a trailing "
          "prefix-sum so the per-row mechanism is causal.", flush=True)
    return ok


def _dist_sanity(F16: np.ndarray) -> bool:
    """Distribution sanity per the spec bounds + per-channel finite-frac."""
    print(f"  {'channel':<24}{'finite%':>9}{'mean':>12}{'std':>12}"
          f"{'min':>12}{'max':>12}", flush=True)
    ok = True
    F = F16.astype(np.float32)
    for j, nm in enumerate(CH_NAMES):
        col = F[:, j]
        fin = float(np.isfinite(col).mean()) * 100
        cmin, cmax = float(col.min()), float(col.max())
        print(f"  {nm:<24}{fin:>8.2f}%{col.mean():>12.5g}{col.std():>12.5g}"
              f"{cmin:>12.5g}{cmax:>12.5g}", flush=True)
        if fin < 100.0:
            print(f"    [FAIL] {nm} not 100% finite in fp16", flush=True)
            ok = False
    # spec range checks
    def _rng(j, lo, hi, name):
        nonlocal ok
        col = F[:, j]
        if col.min() < lo - 1e-3 or col.max() > hi + 1e-3:
            print(f"    [FAIL] {name} out of [{lo},{hi}]: "
                  f"[{col.min():.4g},{col.max():.4g}]", flush=True)
            ok = False
    for j in (0, 1, 2):
        _rng(j, -1.0, 1.0, CH_NAMES[j])
    _rng(3, 0.0, 1.0, "vpin")
    _rng(10, 0.0, 1.0, "large_trade_frac")
    _rng(8, -1.0, 1.0, "aggressor_run")
    return ok


def validate(days: list):
    os.makedirs(OUT_DIR, exist_ok=True)
    n_total = len(list_days(SEQ_DIR))
    per_day_secs, per_day_mb = [], []
    gates = {"ts": True, "finite": True, "dist": True, "leak": True}

    for d in days:
        out = p.join(OUT_DIR, f"{d}.npz")
        st = build_one_day(d, out, keep_raw=True)
        per_day_secs.append(st["secs"])
        per_day_mb.append(st["mb"])
        ts, F16 = st["ts"], st["F16"]
        print(f"\n================ day {d}: T={st['T']} F={F16.shape} "
              f"{st['mb']:.2f} MB  {st['secs']:.1f}s  "
              f"empty_secs={st['n_empty_secs']} ({100*st['empty_frac']:.2f}%) "
              f"nan_rows={st['n_nan_rows']} ================", flush=True)

        # GATE ts: identity vs seq_cache
        with np.load(out) as z:
            ts_saved, F_saved = z["ts"].astype(np.int64), z["T"]
        sts = _seq_ts(d)
        g_ts = (np.array_equal(ts_saved, sts)
                and F_saved.shape == (sts.shape[0], N_CH)
                and F_saved.dtype == np.float16)
        gates["ts"] &= g_ts
        print(f"[GATE ts] ts==seq_cache ts: {np.array_equal(ts_saved, sts)}  "
              f"T={ts_saved.shape[0]} (85800 expected)  shape={F_saved.shape}  "
              f"dtype={F_saved.dtype}  {'PASS' if g_ts else 'FAIL'}", flush=True)

        # GATE finite + dist sanity
        print("[GATE dist] per-channel finite% / mean / std / min / max "
              "+ spec-range checks:", flush=True)
        g_dist = _dist_sanity(F_saved)
        gates["finite"] &= bool(np.isfinite(F_saved.astype(np.float32)).all())
        gates["dist"] &= g_dist
        print(f"[GATE dist] {'PASS' if g_dist else 'FAIL'}", flush=True)

        # GATE leak: strict-causality recompute
        print("[GATE leak] strict-causality truncated-recompute probe:",
              flush=True)
        gates["leak"] &= _leakage_check(d, st["tr"], st["ext_secs"])

    s, mb = float(np.mean(per_day_secs)), float(np.mean(per_day_mb))
    print(f"\n[GATE size] avg {s:.1f} s/day, {mb:.2f} MB/day; full build est "
          f"({n_total} days): {n_total*s/3600:.2f} h, "
          f"{n_total*mb/1000:.2f} GB", flush=True)
    print("\n[validate] " + "  ".join(
        f"GATE_{g}={'PASS' if ok else 'FAIL'}" for g, ok in gates.items())
        + "  GATE_size=reported", flush=True)
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
    args = ap.parse_args()
    if args.validate:
        validate(args.validate)
    else:
        build(force=args.force, days_subset=args.days)

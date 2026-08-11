#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced 1s resampler with engineered + microstructure features.

Supports multi-horizon targets:
  - 1m (60s), 5m (300s), 10m (600s) forward returns.

Adds horizon-relevant feature windows:
  - Flow/cum-flow for 60s/300s/600s
  - Realized variance/asymmetry for 60s/300s/600s
  - APB for 60s/300s/600s

Inputs (per task, via --tasks-file CSV):
    depth_file,trade_file,out_file

All resampling is aligned to 1s grid with:
  label="right", closed="right"
so timestamp t represents interval (t-1s, t].
"""

import argparse
import math
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple, Optional, Dict

import numpy as np
import pandas as pd


# ======================================================================
# General helpers
# ======================================================================

TS_CANDS = ("time_utc", "timestamp", "local_timestamp", "sts", "ts", "lts")

# Keep one consistent resample convention everywhere
RESAMPLE_KW: Dict[str, str] = {"label": "right", "closed": "right"}


def read_any(path: str) -> pd.DataFrame:
    """
    Read Parquet/Feather/CSV depending on extension.
    """
    path = str(path)
    lower = path.lower()

    if lower.endswith((".parquet", ".pq", ".parquet.gzip")):
        return pd.read_parquet(path)

    if lower.endswith(".feather"):
        return pd.read_feather(path)

    # treat everything else as CSV(-ish)
    return pd.read_csv(path)


def _infer_ts_unit_numeric(values: pd.Series) -> str:
    v = pd.to_numeric(values.dropna(), errors="coerce")
    v = v[np.isfinite(v)]
    if v.empty:
        return "ms"
    vmax = float(np.max(np.abs(v)))
    if vmax > 1e18:
        return "ns"
    if vmax > 1e15:
        return "us"
    if vmax > 1e12:
        return "ms"
    return "s"


def ensure_datetime_index(df: pd.DataFrame,
                          ts_candidates: Tuple[str, ...] = TS_CANDS) -> pd.DataFrame:
    """
    Ensure df has a tz-aware DatetimeIndex (UTC). Prefer given ts_candidates.

    Handles both numeric timestamps and ISO8601 strings.
    """
    if isinstance(df.index, pd.DatetimeIndex):
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")
        return df.sort_index()

    cols = df.columns
    ts_col = None
    for c in ts_candidates:
        if c in cols:
            ts_col = c
            break
    if ts_col is None:
        raise RuntimeError(f"No timestamp column found among {ts_candidates}")

    s = df[ts_col]

    if pd.api.types.is_numeric_dtype(s):
        unit = _infer_ts_unit_numeric(s)
        ts = pd.to_datetime(s, unit=unit, utc=True, errors="coerce")
    else:
        ts = pd.to_datetime(s, utc=True, errors="coerce")

    df = df.assign(_ts=ts).dropna(subset=["_ts"]).set_index("_ts")
    df.index.name = None
    df = df.sort_index()
    return df


def _parse_book_level_index(col: str) -> int:
    """
    Extract numeric level from column like 'asks[3].price' or 'bids[10].size'.
    """
    try:
        inside = col.split("[", 1)[1].split("]", 1)[0]
        return int(inside)
    except Exception:
        return 9999


def find_best_price_size_cols(depth: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Discover L1 bid/ask price & size columns from depth DataFrame.
    Returns (ask_price_col, ask_size_col, bid_price_col, bid_size_col) or None where missing.
    """
    ask_price_cols = [c for c in depth.columns if c.startswith("asks[") and ".price" in c]
    bid_price_cols = [c for c in depth.columns if c.startswith("bids[") and ".price" in c]
    ask_size_cols = [c for c in depth.columns if c.startswith("asks[") and any(s in c for s in (".size", ".qty", ".amount"))]
    bid_size_cols = [c for c in depth.columns if c.startswith("bids[") and any(s in c for s in (".size", ".qty", ".amount"))]

    ask_price_cols = sorted(ask_price_cols, key=_parse_book_level_index)
    bid_price_cols = sorted(bid_price_cols, key=_parse_book_level_index)
    ask_size_cols = sorted(ask_size_cols, key=_parse_book_level_index)
    bid_size_cols = sorted(bid_size_cols, key=_parse_book_level_index)

    ask_price_col = ask_price_cols[0] if ask_price_cols else None
    bid_price_col = bid_price_cols[0] if bid_price_cols else None
    ask_size_col = ask_size_cols[0] if ask_size_cols else None
    bid_size_col = bid_size_cols[0] if bid_size_cols else None
    return ask_price_col, ask_size_col, bid_price_col, bid_size_col


def infer_tick_size(depth: pd.DataFrame,
                    bid_col: str,
                    ask_col: str,
                    default: float = 0.1) -> float:
    """
    Infer tick size from best bid prices. Fallback to default if unclear.
    """
    px = pd.to_numeric(depth[bid_col], errors="coerce").dropna().values
    if px.size < 2:
        return default
    px = np.unique(np.sort(px))
    dp = np.diff(px)
    dp = dp[dp > 0]
    if dp.size == 0:
        return default
    tick = float(np.median(dp))
    if not np.isfinite(tick) or tick <= 0:
        return default
    return tick


def cont_ewma_half_life(x: np.ndarray,
                        dt_sec: np.ndarray,
                        half_life: float) -> np.ndarray:
    """
    Continuous-time EWMA with half-life H (seconds):
        alpha_i = 1 - exp(-ln2 * dt_i / H)
    dt_sec is per-step time delta in seconds; len(dt_sec) == len(x).
    """
    n = len(x)
    if n == 0:
        return x
    if half_life <= 0:
        return x.copy()

    ln2 = math.log(2.0)
    out = np.zeros(n, dtype=float)
    out[0] = float(x[0])
    for i in range(1, n):
        dt = max(float(dt_sec[i]), 0.0)
        alpha = 1.0 - math.exp(-ln2 * dt / half_life)
        alpha = max(0.0, min(1.0, alpha))
        out[i] = alpha * float(x[i]) + (1.0 - alpha) * out[i - 1]
    return out


# =========================
# Numerically-stable sigmoid (fix APB overflow)
# =========================

def stable_sigmoid(z: np.ndarray) -> np.ndarray:
    """
    Stable sigmoid for large |z| without exp overflow.
    """
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z, dtype=np.float64)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


# ======================================================================
# Deep Trade Alpha (raw depth+trades → 1s)
# ======================================================================

def extract_trade_dir_qty(trades: pd.DataFrame) -> Tuple[Optional[pd.Series], Optional[pd.Series]]:
    """
    Try to infer trade direction (+1 buy, -1 sell) and quantity from trades df.
    """
    if trades.empty:
        return None, None

    qty_col = None
    for c in ("quantity", "qty", "size", "vol", "volume", "base_qty", "amount"):
        if c in trades.columns:
            qty_col = c
            break
    if qty_col is None:
        return None, None

    qty = pd.to_numeric(trades[qty_col], errors="coerce")

    dir_ser = None
    if "is_buy" in trades.columns:
        raw = trades["is_buy"]

        def _map_is_buy(v):
            try:
                if isinstance(v, str):
                    vv = v.strip().upper()
                    if vv in ("BUY", "B", "TRUE", "T", "1"):
                        return 1
                    if vv in ("SELL", "S", "FALSE", "F", "0"):
                        return -1
                if v in (1, True):
                    return 1
                if v in (0, False, -1):
                    return -1
            except Exception:
                pass
            return 0

        dir_ser = raw.map(_map_is_buy).astype("int8")

    elif "side" in trades.columns:
        raw = trades["side"]

        def _map_side(v):
            vv = str(v).strip().upper()
            if vv in ("BUY", "B", "BID"):
                return 1
            if vv in ("SELL", "S", "ASK"):
                return -1
            return 0

        dir_ser = raw.map(_map_side).astype("int8")

    elif "is_buyer_maker" in trades.columns:
        raw = trades["is_buyer_maker"]
        dir_ser = raw.apply(lambda x: -1 if bool(x) else 1).astype("int8")

    else:
        return None, None

    dir_ser = dir_ser.where(np.isfinite(qty), 0)
    qty = qty.where(np.isfinite(qty) & (qty > 0), 0.0)

    return dir_ser, qty


def compute_deep_trade_alpha_1s(
    depth_raw: pd.DataFrame,
    trades_raw: pd.DataFrame,
    resample_freq: str = "1s",
    hl_short: float = 60.0,
    hl_long: float = 300.0,
    max_bps: float = 50.0,
) -> pd.DataFrame:
    if depth_raw.empty or trades_raw.empty:
        return pd.DataFrame()

    depth = ensure_datetime_index(depth_raw)
    trades = ensure_datetime_index(trades_raw)

    ask_px_col, ask_sz_col, bid_px_col, bid_sz_col = find_best_price_size_cols(depth)
    if not all([ask_px_col, ask_sz_col, bid_px_col, bid_sz_col]):
        return pd.DataFrame()

    tick_size = infer_tick_size(depth, bid_px_col, ask_px_col)

    ts_depth = depth.index.astype("int64").to_numpy()
    ask_sz = pd.to_numeric(depth[ask_sz_col], errors="coerce").to_numpy()
    bid_sz = pd.to_numeric(depth[bid_sz_col], errors="coerce").to_numpy()
    ask_px = pd.to_numeric(depth[ask_px_col], errors="coerce").to_numpy()
    bid_px = pd.to_numeric(depth[bid_px_col], errors="coerce").to_numpy()
    mid_prev = 0.5 * (ask_px + bid_px)

    trade_dir, trade_qty = extract_trade_dir_qty(trades)
    if trade_dir is None or trade_qty is None:
        return pd.DataFrame()

    trade_ts_ns = trades.index.astype("int64").to_numpy()
    tdir = trade_dir.to_numpy()
    tqty = trade_qty.to_numpy()

    pos_prev = np.searchsorted(ts_depth, trade_ts_ns, side="right") - 1
    ok_prev = pos_prev >= 0
    if not ok_prev.any():
        return pd.DataFrame()

    pos_prev = pos_prev[ok_prev]
    tdir = tdir[ok_prev]
    tqty = tqty[ok_prev]
    tts_ns = trade_ts_ns[ok_prev]

    prev_ask_sz = ask_sz[pos_prev]
    prev_bid_sz = bid_sz[pos_prev]
    prev_mid = mid_prev[pos_prev]

    cond_buy = (tdir == 1) & np.isfinite(prev_ask_sz) & (tqty >= prev_ask_sz)
    cond_sell = (tdir == -1) & np.isfinite(prev_bid_sz) & (tqty >= prev_bid_sz)
    signal = cond_buy | cond_sell
    if not signal.any():
        return pd.DataFrame()

    side_depth = np.where(tdir == 1, prev_ask_sz, prev_bid_sz)
    eps = 1e-12
    size_ratio = np.clip(tqty / (side_depth + eps), 0.0, 50.0)

    mid_safe = np.where(np.isfinite(prev_mid) & (prev_mid > 0.0), prev_mid, np.nan)
    strength_raw = np.log1p(size_ratio)
    impulse_frac = strength_raw * (tick_size / mid_safe)
    impulse_frac = np.where(np.isfinite(impulse_frac), impulse_frac, 0.0)
    impulse_bps = np.clip(impulse_frac * 1e4, -max_bps, max_bps)

    alpha_impulse_all = np.zeros_like(impulse_bps)
    alpha_impulse_all[cond_buy] = np.abs(impulse_bps[cond_buy])
    alpha_impulse_all[cond_sell] = -np.abs(impulse_bps[cond_sell])

    pos_entry = np.searchsorted(ts_depth, tts_ns[signal], side="right")
    has_entry = pos_entry < len(ts_depth)
    pos_entry = pos_entry[has_entry]
    impulses = alpha_impulse_all[signal][has_entry]

    imp_series = pd.Series(0.0, index=depth.index)
    idx_stamp = depth.index[pos_entry]
    stamp_df = pd.DataFrame({"idx": idx_stamp, "imp": impulses}).groupby("idx")["imp"].sum()
    imp_series.loc[stamp_df.index] = stamp_df.values

    ts_ns = depth.index.astype("int64").to_numpy()
    dt_ns = np.diff(ts_ns)
    dt_sec = np.concatenate([[0.0], np.maximum(dt_ns * 1e-9, 0.0)])
    imp_arr = imp_series.to_numpy(dtype=float)

    ewm_short = cont_ewma_half_life(imp_arr, dt_sec, hl_short)
    ewm_long = cont_ewma_half_life(imp_arr, dt_sec, hl_long)

    df_depth = pd.DataFrame(
        {
            "deep_impulse_bps": imp_arr,
            f"deep_ewm_{int(hl_short)}s_bps": ewm_short,
            f"deep_ewm_{int(hl_long)}s_bps": ewm_long,
        },
        index=depth.index,
    )
    df_depth["deep_alpha_bps"] = df_depth[f"deep_ewm_{int(hl_long)}s_bps"]

    df_1s = df_depth.resample(resample_freq, **RESAMPLE_KW).last().ffill()
    return df_1s


# ======================================================================
# Queue Depletion Alpha (raw depth → 1s)
# ======================================================================

def compute_queue_depletion_alpha_1s(
    depth_raw: pd.DataFrame,
    resample_freq: str = "1s",
    win_sec: float = 60.0,
    tau_ask: float = 0.35,
    tau_bid: float = 0.35,
    cooldown_sec: float = 2.0,
    hl_short: float = 60.0,
    hl_long: float = 300.0,
    tick_size: Optional[float] = None,
    max_bps: float = 50.0,
) -> pd.DataFrame:
    if depth_raw.empty:
        return pd.DataFrame()

    depth = ensure_datetime_index(depth_raw)
    ask_px_col, ask_sz_col, bid_px_col, bid_sz_col = find_best_price_size_cols(depth)
    if not all([ask_px_col, ask_sz_col, bid_px_col, bid_sz_col]):
        return pd.DataFrame()

    if tick_size is None:
        tick_size = infer_tick_size(depth, bid_px_col, ask_px_col)

    d = depth[[ask_px_col, ask_sz_col, bid_px_col, bid_sz_col]].copy()
    d[ask_px_col] = pd.to_numeric(d[ask_px_col], errors="coerce")
    d[bid_px_col] = pd.to_numeric(d[bid_px_col], errors="coerce")
    d[ask_sz_col] = pd.to_numeric(d[ask_sz_col], errors="coerce")
    d[bid_sz_col] = pd.to_numeric(d[bid_sz_col], errors="coerce")

    d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=[ask_px_col, bid_px_col])
    d = d[(d[ask_px_col] > 0) & (d[bid_px_col] > 0)]
    d = d[d[ask_px_col] >= d[bid_px_col]]

    d["mid"] = 0.5 * (d[bid_px_col] + d[ask_px_col])
    d["spread"] = d[ask_px_col] - d[bid_px_col]

    smooth_alpha = 0.20
    d["bid_sz_s"] = d[bid_sz_col].ewm(alpha=smooth_alpha, adjust=False).mean()
    d["ask_sz_s"] = d[ask_sz_col].ewm(alpha=smooth_alpha, adjust=False).mean()

    win_str = f"{int(max(1, round(win_sec)))}s"
    med_bid = d["bid_sz_s"].shift(1).rolling(win_str, min_periods=5).median()
    med_ask = d["ask_sz_s"].shift(1).rolling(win_str, min_periods=5).median()

    d["ratio_bid"] = d["bid_sz_s"] / med_bid
    d["ratio_ask"] = d["ask_sz_s"] / med_ask

    d["ok_bid"] = (d["bid_sz_s"] > 0) & np.isfinite(d["ratio_bid"])
    d["ok_ask"] = (d["ask_sz_s"] > 0) & np.isfinite(d["ratio_ask"])

    d["trig_buy_raw"] = d["ok_ask"] & (d["ratio_ask"] < tau_ask) & (d["spread"] >= tick_size)
    d["trig_sell_raw"] = d["ok_bid"] & (d["ratio_bid"] < tau_bid) & (d["spread"] >= tick_size)

    cooldown = pd.Timedelta(seconds=max(0.0, cooldown_sec))
    last_sig_time = None
    sig_rows = []
    for ts, row in d.iterrows():
        buy = bool(row["trig_buy_raw"])
        sell = bool(row["trig_sell_raw"])
        if not (buy or sell):
            continue
        if last_sig_time is not None and ts < last_sig_time + cooldown:
            continue

        if buy and not sell:
            side = "BUY"
            thin_ratio = float(row["ratio_ask"])
        elif sell and not buy:
            side = "SELL"
            thin_ratio = float(row["ratio_bid"])
        else:
            if row["ratio_ask"] <= row["ratio_bid"]:
                side = "BUY"
                thin_ratio = float(row["ratio_ask"])
            else:
                side = "SELL"
                thin_ratio = float(row["ratio_bid"])

        sig_rows.append(
            {"ts": ts, "side": side, "thin_ratio": thin_ratio, "mid": float(row["mid"]), "spread": float(row["spread"])}
        )
        last_sig_time = ts

    if not sig_rows:
        return pd.DataFrame()

    sig_df = pd.DataFrame(sig_rows).sort_values("ts")
    sig_df["ts"] = pd.to_datetime(sig_df["ts"], utc=True)

    side_sign = np.where(sig_df["side"] == "BUY", 1.0, -1.0)
    thin_ratio = sig_df["thin_ratio"].to_numpy(dtype=float)
    spread = sig_df["spread"].to_numpy(dtype=float)
    mid = sig_df["mid"].to_numpy(dtype=float)

    thin_severity = np.clip(1.0 - thin_ratio, 0.0, 1.0)
    spread_ticks = np.clip(spread / float(tick_size), 1.0, 5.0)
    edge_price = thin_severity * spread_ticks * float(tick_size)

    mid_safe = np.where(np.isfinite(mid) & (mid > 0.0), mid, np.nan)
    edge_frac = np.where(np.isfinite(edge_price / mid_safe), edge_price / mid_safe, 0.0)
    impulse_bps = np.clip(side_sign * edge_frac * 1e4, -max_bps, max_bps)

    impulses = pd.Series(0.0, index=d.index)
    stamp = pd.Series(impulse_bps, index=sig_df["ts"])
    stamp = stamp[stamp.index.isin(impulses.index)]
    impulses.loc[stamp.index] = stamp.values

    ts_ns = d.index.astype("int64").to_numpy()
    dt_ns = np.diff(ts_ns)
    dt_sec = np.concatenate([[0.0], np.maximum(dt_ns * 1e-9, 0.0)])
    imp_arr = impulses.to_numpy(dtype=float)

    ewm_s = cont_ewma_half_life(imp_arr, dt_sec, hl_short)
    ewm_l = cont_ewma_half_life(imp_arr, dt_sec, hl_long)

    df_depth = pd.DataFrame(
        {
            "qd_impulse_bps": imp_arr,
            f"qd_ewm_{int(hl_short)}s_bps": ewm_s,
            f"qd_ewm_{int(hl_long)}s_bps": ewm_l,
        },
        index=d.index,
    )
    df_depth["qd_alpha_bps"] = df_depth[f"qd_ewm_{int(hl_long)}s_bps"]

    df_1s = df_depth.resample(resample_freq, **RESAMPLE_KW).last().ffill()
    return df_1s


# ======================================================================
# OFI / elasticity (raw depth → 1s)
# ======================================================================

def compute_ofi_elasticity_1s(
    depth_raw: pd.DataFrame,
    resample_freq: str = "1s",
    halflife_secs=(10.0, 60.0, 180.0, 300.0, 600.0),
    max_frac_move: float = 0.01,
) -> pd.DataFrame:
    """
    OFI-based fractional move proxy (smoothed). Ask-side sign is correct.
    """
    if depth_raw.empty:
        return pd.DataFrame()

    depth = ensure_datetime_index(depth_raw)
    ask_px_col, ask_sz_col, bid_px_col, bid_sz_col = find_best_price_size_cols(depth)
    if not all([ask_px_col, ask_sz_col, bid_px_col, bid_sz_col]):
        return pd.DataFrame()

    df = depth[[ask_px_col, ask_sz_col, bid_px_col, bid_sz_col]].copy()
    df = df.sort_index().dropna()


    ask_q = pd.to_numeric(df[ask_sz_col], errors="coerce").to_numpy(dtype=np.float64)
    bid_q = pd.to_numeric(df[bid_sz_col], errors="coerce").to_numpy(dtype=np.float64)
    ask_px = pd.to_numeric(df[ask_px_col], errors="coerce").to_numpy(dtype=np.float64)
    bid_px = pd.to_numeric(df[bid_px_col], errors="coerce").to_numpy(dtype=np.float64)

    n = len(df)
    if n < 2:
        return pd.DataFrame(index=df.index)

    ts_ns = df.index.astype("int64").to_numpy()
    dt_ns = np.diff(ts_ns)
    dt_sec = np.concatenate([[0.0], np.maximum(dt_ns * 1e-9, 0.0)])

    ask_px_prev = np.roll(ask_px, 1); ask_px_prev[0] = np.nan
    bid_px_prev = np.roll(bid_px, 1); bid_px_prev[0] = np.nan
    ask_q_prev  = np.roll(ask_q, 1);  ask_q_prev[0]  = np.nan
    bid_q_prev  = np.roll(bid_q, 1);  bid_q_prev[0]  = np.nan

    valid = np.isfinite(ask_px) & np.isfinite(bid_px) & np.isfinite(ask_q) & np.isfinite(bid_q) & \
            np.isfinite(ask_px_prev) & np.isfinite(bid_px_prev) & np.isfinite(ask_q_prev) & np.isfinite(bid_q_prev)

    ofi = np.zeros(n, dtype=float)

    bid_up = valid & (bid_px > bid_px_prev)
    bid_dn = valid & (bid_px < bid_px_prev)
    bid_eq = valid & ~(bid_up | bid_dn)

    ofi[bid_up] += bid_q[bid_up]
    ofi[bid_dn] += -bid_q_prev[bid_dn]
    ofi[bid_eq] += (bid_q - bid_q_prev)[bid_eq]

    ask_up = valid & (ask_px > ask_px_prev)
    ask_dn = valid & (ask_px < ask_px_prev)
    ask_eq = valid & ~(ask_up | ask_dn)

    # correct ask contribution
    ofi[ask_dn] += ask_q[ask_dn]
    ofi[ask_up] += -ask_q_prev[ask_up]
    ofi[ask_eq] += -(ask_q - ask_q_prev)[ask_eq]

    total_q = bid_q + ask_q + bid_q_prev + ask_q_prev
    eps = 1e-12
    denom_ok = np.isfinite(total_q) & (total_q > eps)
    ofi_ratio = np.zeros_like(ofi)
    ofi_ratio[denom_ok] = ofi[denom_ok] / total_q[denom_ok]

    mid = 0.5 * (bid_px + ask_px)
    spr = ask_px - bid_px
    valid_mid = np.isfinite(mid) & (mid > eps) & np.isfinite(spr) & (spr > 0)

    frac_move = np.zeros_like(ofi_ratio)
    frac_move[valid_mid] = ofi_ratio[valid_mid] * (spr[valid_mid] / mid[valid_mid])
    frac_move = np.clip(frac_move, -max_frac_move, max_frac_move)
    frac_move_bps = frac_move * 1e4

    out = pd.DataFrame(index=df.index)
    for H in halflife_secs:
        H = float(H)
        key = f"ofi{int(H)}_bps"
        out[key] = cont_ewma_half_life(frac_move_bps, dt_sec, H)

    out_1s = out.resample(resample_freq, **RESAMPLE_KW).last().ffill()
    return out_1s


# ======================================================================
# Entropy Skew (raw depth → 1s)
# ======================================================================

def compute_entropy_skew_alpha_1s(
    depth_raw: pd.DataFrame,
    resample_freq: str = "1s",
    max_levels: int = 10,
    halflife_secs=(60.0, 300.0),
    eps: float = 1e-12,
) -> pd.DataFrame:
    if depth_raw.empty:
        return pd.DataFrame()

    depth = ensure_datetime_index(depth_raw).sort_index()

    ask_sz_cols = []
    bid_sz_cols = []
    for c in depth.columns:
        if c.startswith("asks[") and any(s in c for s in (".size", ".qty", ".amount")):
            ask_sz_cols.append(c)
        if c.startswith("bids[") and any(s in c for s in (".size", ".qty", ".amount")):
            bid_sz_cols.append(c)

    ask_sz_cols = sorted(ask_sz_cols, key=_parse_book_level_index)
    bid_sz_cols = sorted(bid_sz_cols, key=_parse_book_level_index)
    if not ask_sz_cols or not bid_sz_cols:
        return pd.DataFrame()

    L = min(max_levels, len(ask_sz_cols), len(bid_sz_cols))
    ask_sz_cols = ask_sz_cols[:L]
    bid_sz_cols = bid_sz_cols[:L]

    ask_Q = depth[ask_sz_cols].apply(pd.to_numeric, errors="coerce").to_numpy()
    bid_Q = depth[bid_sz_cols].apply(pd.to_numeric, errors="coerce").to_numpy()
    ask_Q = np.nan_to_num(ask_Q, nan=0.0, posinf=0.0, neginf=0.0)
    bid_Q = np.nan_to_num(bid_Q, nan=0.0, posinf=0.0, neginf=0.0)

    N = ask_Q.shape[0]
    if N < 1:
        return pd.DataFrame()

    def _normalized_entropy(Q_row: np.ndarray) -> float:
        total = float(np.sum(Q_row))
        if total <= 0:
            return 0.0
        p = Q_row / total
        p = np.clip(p, eps, 1.0)
        H = -float(np.sum(p * np.log(p)))
        lnL = math.log(len(Q_row))
        if lnL <= 0:
            return 0.0
        Hn = H / lnL
        return float(max(0.0, min(1.0, Hn)))

    ent_bid = np.zeros(N, dtype=float)
    ent_ask = np.zeros(N, dtype=float)
    for i in range(N):
        ent_bid[i] = _normalized_entropy(bid_Q[i, :])
        ent_ask[i] = _normalized_entropy(ask_Q[i, :])

    ent_both = 0.5 * (ent_bid + ent_ask)
    ent_gap = ent_ask - ent_bid

    ts_ns = depth.index.astype("int64").to_numpy()
    dt_ns = np.diff(ts_ns)
    dt_sec = np.concatenate([[0.0], np.maximum(dt_ns * 1e-9, 0.0)])

    out_depth = pd.DataFrame(
        {"ent_bid": ent_bid, "ent_ask": ent_ask, "ent_both": ent_both, "ent_gap": ent_gap},
        index=depth.index,
    )

    for H in halflife_secs:
        H = float(H)
        suf = f"_ewm_{int(H)}s"
        out_depth["ent_bid" + suf] = cont_ewma_half_life(ent_bid, dt_sec, H)
        out_depth["ent_ask" + suf] = cont_ewma_half_life(ent_ask, dt_sec, H)
        out_depth["ent_both" + suf] = cont_ewma_half_life(ent_both, dt_sec, H)
        out_depth["ent_gap" + suf] = cont_ewma_half_life(ent_gap, dt_sec, H)

    out_1s = out_depth.resample(resample_freq, **RESAMPLE_KW).last().ffill()
    return out_1s


# ======================================================================
# Energy skew & Temperature (on 1s book)
# ======================================================================

def compute_energy_skew_temp_1s(
    book_1s: pd.DataFrame,
    tick_size: float,
    max_levels: int = 10,
    k_ticks: int = 5,
    energy_decay_ticks: float = 5.0,
    rv_window: int = 600,
) -> pd.DataFrame:
    if book_1s.empty or "mid" not in book_1s.columns:
        return pd.DataFrame(index=book_1s.index)

    mid = pd.to_numeric(book_1s["mid"], errors="coerce")
    mid = mid.where(mid > 0).ffill()

    ask_px_cols = [c for c in book_1s.columns if c.startswith("asks[") and ".price" in c]
    bid_px_cols = [c for c in book_1s.columns if c.startswith("bids[") and ".price" in c]
    ask_sz_cols = [c for c in book_1s.columns if c.startswith("asks[") and any(s in c for s in (".size", ".qty", ".amount"))]
    bid_sz_cols = [c for c in book_1s.columns if c.startswith("bids[") and any(s in c for s in (".size", ".qty", ".amount"))]

    ask_px_cols = sorted(ask_px_cols, key=_parse_book_level_index)[:max_levels]
    bid_px_cols = sorted(bid_px_cols, key=_parse_book_level_index)[:max_levels]
    ask_sz_cols = sorted(ask_sz_cols, key=_parse_book_level_index)[:max_levels]
    bid_sz_cols = sorted(bid_sz_cols, key=_parse_book_level_index)[:max_levels]

    if not ask_px_cols or not bid_px_cols or not ask_sz_cols or not bid_sz_cols:
        return pd.DataFrame(index=book_1s.index)

    ask_px = book_1s[ask_px_cols].apply(pd.to_numeric, errors="coerce").to_numpy()
    bid_px = book_1s[bid_px_cols].apply(pd.to_numeric, errors="coerce").to_numpy()
    ask_q = book_1s[ask_sz_cols].apply(pd.to_numeric, errors="coerce").to_numpy()
    bid_q = book_1s[bid_sz_cols].apply(pd.to_numeric, errors="coerce").to_numpy()
    mid_arr = mid.to_numpy(dtype=float)

    N, _L = ask_q.shape
    if N < 2:
        return pd.DataFrame(index=book_1s.index)

    ask_q = np.nan_to_num(ask_q, nan=0.0, posinf=0.0, neginf=0.0)
    bid_q = np.nan_to_num(bid_q, nan=0.0, posinf=0.0, neginf=0.0)

    dist_ask = np.abs(ask_px - mid_arr[:, None])
    dist_bid = np.abs(bid_px - mid_arr[:, None])
    dist_ask_ticks = dist_ask / tick_size
    dist_bid_ticks = dist_bid / tick_size

    w_ask = np.exp(-np.nan_to_num(dist_ask_ticks, nan=1e6) / energy_decay_ticks)
    w_bid = np.exp(-np.nan_to_num(dist_bid_ticks, nan=1e6) / energy_decay_ticks)

    E_ask = np.sum(ask_q * w_ask, axis=1)
    E_bid = np.sum(bid_q * w_bid, axis=1)
    V_ask = np.sum(ask_q, axis=1)
    V_bid = np.sum(bid_q, axis=1)

    eps = 1e-12
    E_ask_bar = np.divide(E_ask, V_ask + eps, out=np.zeros_like(E_ask), where=(V_ask + eps) > 0)
    E_bid_bar = np.divide(E_bid, V_bid + eps, out=np.zeros_like(E_bid), where=(V_bid + eps) > 0)

    energy_skew = E_ask_bar - E_bid_bar
    dE_ask_bar = np.diff(E_ask_bar, prepend=E_ask_bar[0])
    dE_bid_bar = np.diff(E_bid_bar, prepend=E_bid_bar[0])
    delta_energy_skew = dE_ask_bar - dE_bid_bar

    log_mid = np.log(np.clip(mid_arr, 1e-12, None))
    d_log_mid = np.diff(log_mid, prepend=log_mid[0])
    d2 = d_log_mid ** 2

    rv_all = pd.Series(d2, index=book_1s.index).rolling(rv_window, min_periods=10).sum().to_numpy()
    rv_up = pd.Series(np.where(d_log_mid > 0, d2, 0.0), index=book_1s.index).rolling(rv_window, min_periods=10).sum().to_numpy()
    rv_dn = pd.Series(np.where(d_log_mid < 0, d2, 0.0), index=book_1s.index).rolling(rv_window, min_periods=10).sum().to_numpy()

    band = k_ticks * tick_size
    mask_bid = np.abs(bid_px - mid_arr[:, None]) <= band
    mask_ask = np.abs(ask_px - mid_arr[:, None]) <= band

    D_bid = np.sum(np.where(mask_bid, bid_q, 0.0), axis=1)
    D_ask = np.sum(np.where(mask_ask, ask_q, 0.0), axis=1)

    T_bid = np.divide(rv_dn, D_bid + eps, out=np.zeros_like(rv_dn), where=(D_bid + eps) > 0)
    T_ask = np.divide(rv_up, D_ask + eps, out=np.zeros_like(rv_up), where=(D_ask + eps) > 0)

    T_imb = np.divide((T_ask - T_bid), (T_ask + T_bid + eps), out=np.zeros_like(T_bid), where=(T_ask + T_bid + eps) != 0)

    out = pd.DataFrame(
        {"energy_skew": energy_skew, "delta_energy_skew": delta_energy_skew, "temp_bid": T_bid, "temp_ask": T_ask, "temp_imb": T_imb},
        index=book_1s.index,
    )
    return out


# ======================================================================
# Trades aggregated to 1s, signed volume EWMA, APB, CPV, DVA
# ======================================================================

def aggregate_trades_1s(trades_raw: pd.DataFrame,
                        resample_freq: str = "1s") -> pd.DataFrame:
    """
    Resampling alignment matches book_1s (right/right).
    Robust if price column missing.
    """
    if trades_raw.empty:
        return pd.DataFrame()

    trades = ensure_datetime_index(trades_raw)
    trade_dir, qty_ser = extract_trade_dir_qty(trades)

    if qty_ser is not None:
        q_mag = pd.to_numeric(qty_ser, errors="coerce").fillna(0.0).abs()
    else:
        q_mag = pd.Series(0.0, index=trades.index)

    if "price" in trades.columns:
        px = pd.to_numeric(trades["price"], errors="coerce").fillna(np.nan)
    else:
        px = pd.Series(np.nan, index=trades.index)

    df = pd.DataFrame({"qty": q_mag, "px": px}, index=trades.index).sort_index()

    grp = df.resample(resample_freq, **RESAMPLE_KW)

    vol_sec = grp["qty"].sum()
    pxvol_sec = (df["qty"] * df["px"]).resample(resample_freq, **RESAMPLE_KW).sum()
    vwap_sec = pxvol_sec / (vol_sec + 1e-12)

    out = pd.DataFrame(index=vol_sec.index)
    out["trade_qty"] = vol_sec.fillna(0.0)
    out["trade_notional"] = pxvol_sec.fillna(0.0)
    out["trade_vwap"] = vwap_sec

    if trade_dir is not None and qty_ser is not None:
        signed_qty = (trade_dir * qty_ser).resample(resample_freq, **RESAMPLE_KW).sum()
        out["trade_signed_qty"] = signed_qty.fillna(0.0)
    else:
        out["trade_signed_qty"] = 0.0

    out["trade_px_last"] = df["px"].resample(resample_freq, **RESAMPLE_KW).last()
    return out


def compute_signed_volume_ewma_1s(
    trade_1s: pd.DataFrame,
    halflife_secs=(60.0, 300.0, 600.0),
) -> pd.DataFrame:
    if trade_1s.empty or "trade_signed_qty" not in trade_1s.columns:
        return pd.DataFrame(index=trade_1s.index)

    ts = trade_1s.index
    ts_ns = ts.astype("int64").to_numpy()
    dt_ns = np.diff(ts_ns)
    dt_sec = np.concatenate([[0.0], np.maximum(dt_ns * 1e-9, 0.0)])
    x = trade_1s["trade_signed_qty"].to_numpy(dtype=float)

    out = pd.DataFrame(index=trade_1s.index)
    for H in halflife_secs:
        H = float(H)
        key = f"signed_vol_hl{int(H)}s"
        out[key] = cont_ewma_half_life(x, dt_sec, H)
    return out


# =========================
# FIXED: APB (overflow-safe)
# =========================

def compute_apb_window(
    book_1s: pd.DataFrame,
    trade_1s: pd.DataFrame,
    window_sec: int,
    log_scale: float = 1e4,   # was 1e5 -> too aggressive, caused exp overflow
    clip_z: float = 50.0,     # clip z before sigmoid (sigmoid saturates well before 50)
) -> pd.Series:
    """
    APB: compares rolling VWAP to TWAP; mapped to [-1, 1] via stable sigmoid.

    Fixes overflow:
      - uses stable_sigmoid
      - clips z
      - uses more reasonable scaling
    """
    if book_1s.empty or "mid" not in book_1s.columns:
        return pd.Series(0.0, index=book_1s.index)

    idx = book_1s.index
    trade_1s = trade_1s.reindex(idx).fillna(0.0)

    mid = pd.to_numeric(book_1s["mid"], errors="coerce").ffill()
    mid = mid.where(mid > 0).ffill()

    v = trade_1s.get("trade_qty", pd.Series(0.0, index=idx)).fillna(0.0)

    p = trade_1s.get("trade_px_last", pd.Series(np.nan, index=idx))
    p = pd.to_numeric(p, errors="coerce").fillna(mid)

    win = int(window_sec)
    if win < 2:
        win = 2

    minp = max(10, win // 10)
    notional = (v * p).fillna(0.0)
    roll_notional = notional.rolling(win, min_periods=minp).sum()
    roll_volume = v.rolling(win, min_periods=minp).sum()
    vwap = roll_notional / (roll_volume + 1e-12)

    twap = mid.rolling(win, min_periods=minp).mean()

    ratio = (twap / vwap).where((vwap > 0) & (twap > 0), np.nan)
    log_ratio = np.log(np.clip(ratio, 1e-12, None)).fillna(0.0)

    z = (log_ratio * float(log_scale)).to_numpy(dtype=np.float64)
    z = np.nan_to_num(z, nan=0.0, posinf=clip_z, neginf=-clip_z)
    z = np.clip(z, -clip_z, clip_z)

    sig = stable_sigmoid(z)
    apb = (sig - 0.5) * 2.0  # [-1, 1]
    return pd.Series(apb.astype(np.float32), index=idx)


def compute_apb_features_1s(book_1s: pd.DataFrame, trade_1s: pd.DataFrame, windows=(60, 300, 600)) -> pd.DataFrame:
    out = pd.DataFrame(index=book_1s.index)
    for w in windows:
        out[f"apb_{int(w)}s"] = compute_apb_window(book_1s, trade_1s, int(w))
    return out


def compute_cpv_1s(
    book_1s: pd.DataFrame,
    trade_1s: pd.DataFrame,
    windows=(20, 60, 120),
    smoothing_alphas=(0.3,),
) -> pd.DataFrame:
    idx = book_1s.index
    if "mid" not in book_1s.columns:
        return pd.DataFrame(index=idx)

    trade_1s = trade_1s.reindex(idx).fillna(0.0)
    vol = trade_1s.get("trade_qty", pd.Series(0.0, index=idx))
    mid = pd.to_numeric(book_1s["mid"], errors="coerce").ffill()

    d_mid = mid.diff().fillna(0.0)

    out = pd.DataFrame(index=idx)

    def fast_spearman(x: np.ndarray, y: np.ndarray) -> float:
        n = len(x)
        if n < 3:
            return 0.0
        ix = np.argsort(x)
        rx = np.empty(n, float); rx[ix] = np.arange(1, n + 1)
        iy = np.argsort(y)
        ry = np.empty(n, float); ry[iy] = np.arange(1, n + 1)
        vx = rx - rx.mean()
        vy = ry - ry.mean()
        num = np.mean(vx * vy)
        den = math.sqrt(np.mean(vx ** 2) * np.mean(vy ** 2)) + 1e-12
        return float(num / den)

    arr_dmid = d_mid.to_numpy(dtype=float)
    arr_vol = vol.to_numpy(dtype=float)
    arr_vol_prev = np.roll(arr_vol, 1); arr_vol_prev[0] = 0.0

    n = len(idx)
    for W in windows:
        W = int(W)
        if W < 5:
            continue
        corr_norm = np.zeros(n, dtype=float)
        corr_vfirst = np.zeros(n, dtype=float)
        for i in range(n):
            if i < W:
                continue
            x = arr_dmid[i - W + 1: i + 1]
            y_norm = arr_vol[i - W + 1: i + 1]
            y_vfirst = arr_vol_prev[i - W + 1: i + 1]
            corr_norm[i] = fast_spearman(x, y_norm)
            corr_vfirst[i] = fast_spearman(x, y_vfirst)

        for alpha in smoothing_alphas:
            name_norm = f"cpv_{W}s_alpha{alpha:.1f}"
            name_vfirst = f"cpv_vfirst_{W}s_alpha{alpha:.1f}"
            ema_norm = pd.Series(corr_norm, index=idx).ewm(alpha=alpha, adjust=False).mean().to_numpy()
            ema_vfirst = pd.Series(corr_vfirst, index=idx).ewm(alpha=alpha, adjust=False).mean().to_numpy()
            out[name_norm] = corr_norm - ema_norm
            out[name_vfirst] = corr_vfirst - ema_vfirst

    return out


def compute_dva_1s(
    book_1s: pd.DataFrame,
    depth_levels=(5, 10),
) -> pd.DataFrame:
    idx = book_1s.index
    ask_sz_cols = [c for c in book_1s.columns if c.startswith("asks[") and any(s in c for s in (".size", ".qty", ".amount"))]
    bid_sz_cols = [c for c in book_1s.columns if c.startswith("bids[") and any(s in c for s in (".size", ".qty", ".amount"))]

    ask_sz_cols = sorted(ask_sz_cols, key=_parse_book_level_index)
    bid_sz_cols = sorted(bid_sz_cols, key=_parse_book_level_index)
    if not ask_sz_cols or not bid_sz_cols:
        return pd.DataFrame(index=idx)

    out = pd.DataFrame(index=idx)
    window = 60
    eps = 1e-12

    for L in depth_levels:
        ask_cols_L = ask_sz_cols[:L]
        bid_cols_L = bid_sz_cols[:L]
        ask_q = book_1s[ask_cols_L].apply(pd.to_numeric, errors="coerce")
        bid_q = book_1s[bid_cols_L].apply(pd.to_numeric, errors="coerce")
        ask_var = ask_q.rolling(window, min_periods=10).var().sum(axis=1)
        bid_var = bid_q.rolling(window, min_periods=10).var().sum(axis=1)

        dva = (bid_var - ask_var) / (bid_var + ask_var + eps)
        out[f"dva_L{L}"] = dva.astype(float)

    return out


# ======================================================================
# Meta-order run features (raw trades → 1s)
# ======================================================================

def compute_meta_order_features_1s(
    trades_raw: pd.DataFrame,
    resample_freq: str = "1s"
) -> pd.DataFrame:
    if trades_raw.empty:
        return pd.DataFrame()

    trades = ensure_datetime_index(trades_raw)
    dir_ser, qty_ser = extract_trade_dir_qty(trades)
    if dir_ser is None or qty_ser is None:
        return pd.DataFrame()

    df = pd.DataFrame(
        {"dir": dir_ser.astype(int), "qty": pd.to_numeric(qty_ser, errors="coerce").fillna(0.0)},
        index=trades.index,
    ).sort_index()

    run_dir = 0
    run_signed = 0.0
    run_count = 0
    run_start_ts = None
    rows = []

    for ts, row in df.iterrows():
        d = int(row["dir"])
        v = float(row["qty"])

        run_sec = float((ts - run_start_ts).total_seconds()) if run_start_ts is not None else 0.0

        if v <= 0 or d == 0:
            rows.append({"ts": ts, "run_signed_qty": run_signed, "run_len_trades": run_count, "run_len_seconds": run_sec})
            continue

        if run_dir == 0 or d == run_dir:
            if run_dir == 0:
                run_start_ts = ts
            run_dir = d
            run_signed += d * v
            run_count += 1
        else:
            run_dir = d
            run_signed = d * v
            run_count = 1
            run_start_ts = ts

        run_sec = float((ts - run_start_ts).total_seconds()) if run_start_ts is not None else 0.0
        rows.append({"ts": ts, "run_signed_qty": run_signed, "run_len_trades": run_count, "run_len_seconds": run_sec})

    if not rows:
        return pd.DataFrame()

    df_runs = pd.DataFrame(rows).set_index("ts").sort_index()
    df_1s = df_runs.resample(resample_freq, **RESAMPLE_KW).last().ffill()
    return df_1s[["run_signed_qty", "run_len_trades", "run_len_seconds"]]


# ======================================================================
# Flow features (1s trades → 1s)
# ======================================================================

def compute_flow_features_1s(
    trade_1s: pd.DataFrame,
    windows=(30, 60, 120, 300, 600),
) -> pd.DataFrame:
    """
    For each W:
      cum_signed_qty_{W}s
      cum_abs_qty_{W}s
      flow_imb_{W}s = cum_signed / (cum_abs + eps)
    """
    if trade_1s.empty:
        return pd.DataFrame(index=trade_1s.index)

    if "trade_signed_qty" not in trade_1s.columns or "trade_qty" not in trade_1s.columns:
        return pd.DataFrame(index=trade_1s.index)

    idx = trade_1s.index
    signed = trade_1s["trade_signed_qty"].fillna(0.0)
    absvol = trade_1s["trade_qty"].fillna(0.0)
    eps = 1e-9

    out = pd.DataFrame(index=idx)
    for W in windows:
        W = int(W)
        if W <= 1:
            continue
        sum_signed = signed.rolling(W, min_periods=max(10, W // 3)).sum()
        sum_abs = absvol.rolling(W, min_periods=max(10, W // 3)).sum()

        out[f"cum_signed_qty_{W}s"] = sum_signed
        out[f"cum_abs_qty_{W}s"] = sum_abs
        out[f"flow_imb_{W}s"] = sum_signed / (sum_abs + eps)

    return out


# ======================================================================
# Realized variance/asymmetry features (1s mid → 1s)
# ======================================================================

def compute_rv_features_1s(
    df_1s: pd.DataFrame,
    mid_col: str = "mid",
    windows=(60, 300, 600),
) -> pd.DataFrame:
    if df_1s.empty or mid_col not in df_1s.columns:
        return pd.DataFrame(index=df_1s.index)

    mid = pd.to_numeric(df_1s[mid_col], errors="coerce").ffill()
    if mid.isnull().all():
        return pd.DataFrame(index=df_1s.index)

    log_mid = np.log(mid.clip(lower=1e-12))
    dlog = log_mid.diff().fillna(0.0)
    d2 = dlog ** 2

    out = pd.DataFrame(index=df_1s.index)
    eps = 1e-12

    for W in windows:
        W = int(W)
        rv_all = d2.rolling(W, min_periods=max(10, W // 6)).sum()
        rv_up = d2.where(dlog > 0.0, 0.0).rolling(W, min_periods=max(10, W // 6)).sum()
        rv_dn = d2.where(dlog < 0.0, 0.0).rolling(W, min_periods=max(10, W // 6)).sum()
        rv_asym = (rv_up - rv_dn) / (rv_up + rv_dn + eps)

        out[f"rv_{W}s"] = rv_all
        out[f"rv_up_{W}s"] = rv_up
        out[f"rv_dn_{W}s"] = rv_dn
        out[f"rv_asym_{W}s"] = rv_asym

    return out


# ======================================================================
# OLD engineered features on 1s grid
# ======================================================================

def add_old_features(book_1s: pd.DataFrame) -> pd.DataFrame:
    df = book_1s.copy()
    idx = df.index

    spread = pd.to_numeric(df["spread"], errors="coerce")
    spread_bps = pd.to_numeric(df["spread_bps"], errors="coerce")

    win30 = 30
    df["spread_acceleration"] = spread_bps.diff().rolling(win30, min_periods=5).mean()

    win60 = 60
    df["spread_volatility"] = spread.rolling(win60, min_periods=10).std()

    mid = pd.to_numeric(df["mid"], errors="coerce").ffill()
    log_mid = np.log(mid.clip(lower=1e-12))

    def mom_log(window: int) -> pd.Series:
        return log_mid - log_mid.shift(window)

    df["mom_log_60s"] = mom_log(60)
    df["mom_log_300s"] = mom_log(300)
    df["mom_log_600s"] = mom_log(600)

    df["mom_accel_60_300s"] = df["mom_log_60s"] - df["mom_log_300s"]

    win3600 = 3600
    m60 = df["mom_log_60s"]
    m_mean = m60.rolling(win3600, min_periods=300).mean()
    m_std = m60.rolling(win3600, min_periods=300).std()
    df["mom_overextended_60s"] = ((m60 - m_mean).abs() > 2 * m_std).astype("float32")

    spread_med_1h = spread_bps.rolling(win3600, min_periods=300).median()
    df["low_liq_state"] = (spread_bps > 2.0 * spread_med_1h).astype("float32")

    if isinstance(idx, pd.DatetimeIndex):
        df["hour_of_day"] = idx.hour.astype(float)
        df["minute_of_hour"] = idx.minute.astype(float)
        df["day_of_week"] = idx.dayofweek.astype(float)
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(float)

        df["asia_session"] = ((idx.hour >= 0) & (idx.hour < 8)).astype(float)
        df["europe_session"] = ((idx.hour >= 8) & (idx.hour < 16)).astype(float)
        df["us_session"] = (idx.hour >= 16).astype(float)

        seconds_since_midnight = idx.hour * 3600 + idx.minute * 60 + idx.second
        day_seconds = 24 * 3600
        df["day_sin"] = np.sin(2 * np.pi * seconds_since_midnight / day_seconds)
        df["day_cos"] = np.cos(2 * np.pi * seconds_since_midnight / day_seconds)

        week_seconds = 7 * day_seconds
        seconds_in_week = df["day_of_week"] * day_seconds + seconds_since_midnight
        df["week_sin"] = np.sin(2 * np.pi * seconds_in_week / week_seconds)
        df["week_cos"] = np.cos(2 * np.pi * seconds_in_week / week_seconds)
    else:
        for c in [
            "hour_of_day", "minute_of_hour", "day_of_week", "is_weekend",
            "asia_session", "europe_session", "us_session",
            "day_sin", "day_cos", "week_sin", "week_cos",
        ]:
            df[c] = 0.0

    return df


# ======================================================================
# Targets (1m/5m/10m)
# ======================================================================

def compute_targets_multi(
    df_1s: pd.DataFrame,
    mid_col: str = "mid",
    horizons_sec=(60, 300, 600),
) -> pd.DataFrame:
    """
    Adds targets for each horizon:
      target_{Xm}_logret, target_{Xm}_ret, target_{Xm}_bps, target_{Xm}_valid
    """
    out = pd.DataFrame(index=df_1s.index)

    mid = pd.to_numeric(df_1s.get(mid_col, np.nan), errors="coerce")
    mid = mid.where(mid > 0).ffill()

    if mid.isnull().all():
        for H in horizons_sec:
            m = int(H // 60)
            out[f"target_{m}m_logret"] = np.nan
            out[f"target_{m}m_ret"] = np.nan
            out[f"target_{m}m_bps"] = np.nan
            out[f"target_{m}m_valid"] = False
        return out

    for H in horizons_sec:
        H = int(H)
        m = int(H // 60)
        fwd = mid.shift(-H)
        logret = np.log(fwd) - np.log(mid)
        ret = fwd / mid - 1.0
        bps = ret * 1e4

        valid = np.isfinite(logret) & np.isfinite(ret) & np.isfinite(bps)
        out[f"target_{m}m_logret"] = logret
        out[f"target_{m}m_ret"] = ret
        out[f"target_{m}m_bps"] = bps
        out[f"target_{m}m_valid"] = valid.astype(bool)

    return out


# ======================================================================
# Core resample_one
# ======================================================================

def resample_one(
    depth_file: str,
    trade_file: str,
    out_file: str,
    resample_freq: str = "1s",
    clip_q_low: float = 0.005,
    clip_q_high: float = 0.995,
    fmt: str = "parquet",
) -> None:
    print(f"[resample_one] depth={depth_file} trades={trade_file} → {out_file}", flush=True)

    if not os.path.exists(depth_file):
        print(f"[WARN] Missing depth file: {depth_file}", flush=True)
        return
    if not os.path.exists(trade_file):
        print(f"[WARN] Missing trade file: {trade_file}", flush=True)
        return

    depth_raw = read_any(depth_file)
    trades_raw = read_any(trade_file)

    depth = ensure_datetime_index(depth_raw)
    trades = ensure_datetime_index(trades_raw)

    ask_px_col, ask_sz_col, bid_px_col, bid_sz_col = find_best_price_size_cols(depth)
    if not all([ask_px_col, ask_sz_col, bid_px_col, bid_sz_col]):
        print("[WARN] Could not find best bid/ask columns; aborting task.", flush=True)
        return

    tick_size = infer_tick_size(depth, bid_px_col, ask_px_col)

    # --- 1s book with base price features ---
    book_1s = depth.resample(resample_freq, **RESAMPLE_KW).last().ffill()

    book_1s[ask_px_col] = pd.to_numeric(book_1s[ask_px_col], errors="coerce")
    book_1s[bid_px_col] = pd.to_numeric(book_1s[bid_px_col], errors="coerce")

    book_1s["mid"] = (book_1s[ask_px_col] + book_1s[bid_px_col]) / 2.0
    book_1s["mid"] = pd.to_numeric(book_1s["mid"], errors="coerce").where(lambda s: s > 0).ffill()

    book_1s["spread"] = book_1s[ask_px_col] - book_1s[bid_px_col]
    book_1s["spread_bps"] = (book_1s["spread"] / (book_1s["mid"] + 1e-12)) * 1e4

    # --- OLD engineered features ---
    book_1s = add_old_features(book_1s)

    # --- 1s trade aggregations (aligned right/right) ---
    trade_1s = aggregate_trades_1s(trades_raw, resample_freq=resample_freq)

    df_1s = book_1s.join(trade_1s, how="left")

    # Fill trade fields reasonably
    df_1s["trade_qty"] = df_1s.get("trade_qty", 0.0).fillna(0.0)
    df_1s["trade_signed_qty"] = df_1s.get("trade_signed_qty", 0.0).fillna(0.0)
    df_1s["trade_notional"] = df_1s.get("trade_notional", 0.0).fillna(0.0)

    # trade_px_last fallback to mid for downstream features that need a price
    if "trade_px_last" in df_1s.columns:
        df_1s["trade_px_last"] = pd.to_numeric(df_1s["trade_px_last"], errors="coerce")
        df_1s["trade_px_last"] = df_1s["trade_px_last"].fillna(df_1s["mid"])
    else:
        df_1s["trade_px_last"] = df_1s["mid"]

    # =========================================================
    # NEW microstructure factors
    # =========================================================

    deep_1s = compute_deep_trade_alpha_1s(depth_raw=depth_raw, trades_raw=trades_raw, resample_freq=resample_freq)
    if not deep_1s.empty:
        df_1s = df_1s.join(deep_1s, how="left")

    qd_1s = compute_queue_depletion_alpha_1s(depth_raw=depth_raw, tick_size=tick_size, resample_freq=resample_freq)
    if not qd_1s.empty:
        df_1s = df_1s.join(qd_1s, how="left")

    ofi_1s = compute_ofi_elasticity_1s(depth_raw=depth_raw, resample_freq=resample_freq)
    if not ofi_1s.empty:
        df_1s = df_1s.join(ofi_1s, how="left")

    ent_1s = compute_entropy_skew_alpha_1s(depth_raw=depth_raw, resample_freq=resample_freq)
    if not ent_1s.empty:
        df_1s = df_1s.join(ent_1s, how="left")

    et_1s = compute_energy_skew_temp_1s(book_1s=df_1s, tick_size=tick_size, rv_window=600)
    if not et_1s.empty:
        df_1s = df_1s.join(et_1s, how="left")

    sv_ewm = compute_signed_volume_ewma_1s(df_1s, halflife_secs=(60.0, 300.0, 600.0))
    if not sv_ewm.empty:
        df_1s = df_1s.join(sv_ewm, how="left")

    # APB multi-window (fixed overflow)
    apb_df = compute_apb_features_1s(book_1s=df_1s, trade_1s=df_1s, windows=(60, 300, 600))
    df_1s = df_1s.join(apb_df, how="left")

    cpv_1s = compute_cpv_1s(book_1s=df_1s, trade_1s=df_1s)
    if not cpv_1s.empty:
        df_1s = df_1s.join(cpv_1s, how="left")

    dva_1s = compute_dva_1s(book_1s=df_1s)
    if not dva_1s.empty:
        df_1s = df_1s.join(dva_1s, how="left")

    meta_1s = compute_meta_order_features_1s(trades_raw=trades_raw, resample_freq=resample_freq)
    if not meta_1s.empty:
        df_1s = df_1s.join(meta_1s, how="left")

    flow_feat = compute_flow_features_1s(df_1s, windows=(30, 60, 120, 300, 600))
    if not flow_feat.empty:
        df_1s = df_1s.join(flow_feat, how="left")

    rv_feat = compute_rv_features_1s(df_1s, mid_col="mid", windows=(60, 300, 600))
    if not rv_feat.empty:
        df_1s = df_1s.join(rv_feat, how="left")

    targets = compute_targets_multi(df_1s, mid_col="mid", horizons_sec=(60, 300, 600))
    df_1s = df_1s.join(targets, how="left")

    # --- Clip extremes for some continuous factors (robust) ---
    cont_prefixes = (
        "deep_", "qd_", "ofi", "energy_", "temp_",
        "signed_vol", "cpv_", "dva_", "ent_",
        "flow_imb_", "cum_signed_qty_", "cum_abs_qty_",
        "rv_", "apb_",
    )

    cont_cols = [
        c for c in df_1s.columns
        if df_1s[c].dtype.kind in "fc" and c.startswith(cont_prefixes)
    ]

    for c in cont_cols:
        s = df_1s[c]
        if s.notna().sum() < 100:
            continue
        ql = float(s.quantile(clip_q_low))
        qh = float(s.quantile(clip_q_high))
        if not (np.isfinite(ql) and np.isfinite(qh) and qh > ql):
            continue
        df_1s[c] = s.clip(ql, qh)

    # --- Drop all raw bid/ask price & amount/size columns ---
    raw_book_cols = [ask_px_col, bid_px_col, ask_sz_col, bid_sz_col, "ask", "bid", "ask_size", "bid_size"]
    drop_cols = [
        c for c in df_1s.columns
        if c.startswith("asks[") or c.startswith("bids[") or c in raw_book_cols
    ]
    if drop_cols:
        print(f"[resample_one] Dropping {len(drop_cols)} raw book columns", flush=True)
        df_1s.drop(columns=drop_cols, inplace=True)

    # Write output
    out_dir = os.path.dirname(out_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    if fmt.lower() == "parquet":
        df_1s.to_parquet(out_file, index=True)
    elif fmt.lower() == "csv":
        df_1s.to_csv(out_file, index=True)
    else:
        raise ValueError(f"Unknown output fmt: {fmt}")

    print(f"[resample_one] wrote {out_file} rows={len(df_1s)}", flush=True)


# ======================================================================
# CLI / main
# ======================================================================

def parse_args():
    ap = argparse.ArgumentParser(description="Enhanced 1s resampler with engineered + microstructure features.")
    ap.add_argument("--tasks-file", required=True, help="CSV with columns: depth_file,trade_file,out_file")
    ap.add_argument("--jobs", type=int, default=4, help="Parallel processes for tasks")
    ap.add_argument("--resample-freq", type=str, default="1s")
    ap.add_argument("--clip-low-q", type=float, default=0.005)
    ap.add_argument("--clip-high-q", type=float, default=0.995)
    ap.add_argument("--fmt", type=str, default="parquet", choices=["parquet", "csv"])
    return ap.parse_args()


def load_tasks(tasks_file: str) -> List[Tuple[str, str, str]]:
    df = pd.read_csv(tasks_file)
    required = ["depth_file", "trade_file", "out_file"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"{tasks_file} missing columns: {missing}")
    return list(df[required].itertuples(index=False, name=None))


def main():
    args = parse_args()
    tasks = load_tasks(args.tasks_file)
    if not tasks:
        print("No tasks in tasks-file; nothing to do.")
        return

    print(f"Loaded {len(tasks)} tasks from {args.tasks_file}", flush=True)

    if args.jobs <= 1:
        for depth_file, trade_file, out_file in tasks:
            resample_one(
                depth_file=depth_file,
                trade_file=trade_file,
                out_file=out_file,
                resample_freq=args.resample_freq,
                clip_q_low=args.clip_low_q,
                clip_q_high=args.clip_high_q,
                fmt=args.fmt,
            )
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            futures = [
                ex.submit(
                    resample_one,
                    depth_file,
                    trade_file,
                    out_file,
                    args.resample_freq,
                    args.clip_low_q,
                    args.clip_high_q,
                    args.fmt,
                )
                for depth_file, trade_file, out_file in tasks
            ]
            for fut in as_completed(futures):
                _ = fut.result()

    print("All tasks done.", flush=True)


if __name__ == "__main__":
    main()

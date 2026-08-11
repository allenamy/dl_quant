"""Build TV v4: TV v2 (14 ch) + 5 new theory-motivated regime channels.

Adds 5 NEW channels:
  Trade-derived (2):
    [14] hawkes_intensity_60s — Σ exp(-(t-t_i)/τ) over past trades, τ=60s.
         Self-exciting cluster intensity (Bacry/Muzy 2015). Informed flow
         signature — bursts of trades cluster temporally.
    [15] kyle_lambda_60s — EWMA of |Δmid_bps| / (|signed_vol| + 1), HL=60s.
         Price impact per unit volume (Kyle 1985). Liquidity inverse —
         high λ = thin market = quiet regime indicator.
  Book-derived (1):
    [16] obi_bid_kurtosis — kurtosis of bid_amt across 25 levels per t.
         Depth distribution shape. High kurt = stacked at touch (informed
         queuing); low kurt = spread out (passive flow).
  Time-derived (2, constant within sample):
    [17] hour_sin — sin(2π × hour_of_day / 24)
    [18] day_sin — sin(2π × day_of_week / 7)
         24/7 crypto cycle: US/Asia/Europe trading hours, weekend low vol.

Total K=19 channels (8 v1 + 6 v2 + 5 v4).

Note: NO long-horizon RV (Track R rv_1h/4h/24h NULL/NEG). Time-of-day
captures part of long-horizon regime cheaper.
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
import math
import pathlib
import time
import datetime as dt
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_tv_feature_overlay_v2 import (
    FEAT_NAMES as FEAT_NAMES_V2,
    compute_book_tv_v1,
    compute_book_tv_v2,
    compute_trade_tv_v1,
    compute_trade_tv_v2,
    read_trades_csv,
    ewma_recursive,
)

EPS = 1e-12

FEAT_NAMES = np.concatenate([
    FEAT_NAMES_V2,
    np.array([
        "hawkes_intensity_60s",
        "kyle_lambda_60s",
        "obi_bid_kurtosis",
        "hour_sin",
        "day_sin",
    ], dtype="<U24"),
])


def compute_hawkes_intensity(trades: pd.DataFrame, sample_ts_us: np.ndarray, T: int = 600,
                              tau_s: float = 60.0) -> np.ndarray:
    """Returns (N, T) per-timestep Hawkes-style intensity.

    λ(t) = Σ_{t_i < t} exp(-(t - t_i) / τ)  over past trades.

    Implementation: per-second grid, compute exponential-decayed trade count.
    This is the standard self-exciting intensity (Bacry 2015 — Hawkes
    processes in finance), simplified to scalar (no time-varying base rate).
    """
    N = len(sample_ts_us)
    if N == 0:
        return np.zeros((N, T), dtype=np.float32)
    sample_ts_s = (sample_ts_us // 1_000_000).astype(np.int64)
    min_ts_s = int(sample_ts_s.min()) - T - 10
    max_ts_s = int(sample_ts_s.max())
    span = max_ts_s - min_ts_s + 1
    trade_count = np.zeros(span, dtype=np.float64)
    if not trades.empty:
        in_range = (trades["ts_s"].values >= min_ts_s) & (trades["ts_s"].values <= max_ts_s)
        idx = (trades["ts_s"].values[in_range] - min_ts_s).astype(np.int64)
        np.add.at(trade_count, idx, 1.0)
    # Hawkes intensity = exp-decay sum of past counts. Use EWMA with hl=τ.
    intensity = ewma_recursive(trade_count, tau_s)
    # log1p to compress scale (intensity can spike on bursts)
    intensity_log = np.log1p(intensity)
    out = np.zeros((N, T), dtype=np.float32)
    for s_i, t_s in enumerate(sample_ts_s):
        t_end = t_s - min_ts_s
        if t_end < T - 1: continue
        t_start = t_end - T + 1
        out[s_i] = intensity_log[t_start:t_end + 1]
    return out


def compute_kyle_lambda(trades: pd.DataFrame, sample_ts_us: np.ndarray, T: int = 600,
                        tau_s: float = 60.0) -> np.ndarray:
    """Returns (N, T) Kyle's λ EWMA on per-second grid.

    λ_t = EWMA( |Δmid_t| / (|signed_vol_t| + 1), hl=τ )

    Since we don't have absolute mid per second from trades alone, use
    trade VWAP as mid proxy: ΔVWAP_t = VWAP_t - VWAP_{t-1}. Approximation.
    """
    N = len(sample_ts_us)
    if N == 0:
        return np.zeros((N, T), dtype=np.float32)
    sample_ts_s = (sample_ts_us // 1_000_000).astype(np.int64)
    min_ts_s = int(sample_ts_s.min()) - T - 10
    max_ts_s = int(sample_ts_s.max())
    span = max_ts_s - min_ts_s + 1
    vol = np.zeros(span, dtype=np.float64)
    signed_vol = np.zeros(span, dtype=np.float64)
    px_vol = np.zeros(span, dtype=np.float64)  # price × vol for VWAP
    if not trades.empty:
        in_range = (trades["ts_s"].values >= min_ts_s) & (trades["ts_s"].values <= max_ts_s)
        idx = (trades["ts_s"].values[in_range] - min_ts_s).astype(np.int64)
        amt = trades["amount"].values[in_range].astype(np.float64)
        ss = trades["side_sign"].values[in_range].astype(np.float64)
        prc = trades["price"].values[in_range].astype(np.float64)
        np.add.at(vol, idx, amt)
        np.add.at(signed_vol, idx, ss * amt)
        np.add.at(px_vol, idx, prc * amt)
    # VWAP per second (NaN where vol=0)
    vwap = np.where(vol > 1e-9, px_vol / np.maximum(vol, 1e-9), 0.0)
    # Forward-fill VWAP when no trades
    last_vwap = 0.0
    for i in range(span):
        if vwap[i] == 0.0 and i > 0:
            vwap[i] = last_vwap
        else:
            last_vwap = vwap[i]
    # Δvwap in bps (1e4 × log-return)
    log_vwap = np.log(np.maximum(vwap, 1e-9))
    dlog = np.diff(log_vwap, prepend=log_vwap[:1])
    dvwap_bps = dlog * 1e4
    # Kyle's λ per second
    lam_per_s = np.abs(dvwap_bps) / (np.abs(signed_vol) + 1.0)
    lam_ewm = ewma_recursive(lam_per_s, tau_s)
    out = np.zeros((N, T), dtype=np.float32)
    for s_i, t_s in enumerate(sample_ts_s):
        t_end = t_s - min_ts_s
        if t_end < T - 1: continue
        t_start = t_end - T + 1
        out[s_i] = lam_ewm[t_start:t_end + 1]
    return out


def compute_obi_kurt(X_raw_day: np.ndarray) -> np.ndarray:
    """Returns (N, T, 1) bid-side depth kurtosis across L=25 levels per timestep.

    High kurt = stacked at touch; low kurt = spread out.
    Useful regime indicator: quiet markets often have concentrated depth at touch.
    """
    N, T, L, _ = X_raw_day.shape
    bid_amt = X_raw_day[:, :, :L, 1].astype(np.float64)  # log_amt
    # Convert to linear quantities
    bid_q = np.exp(bid_amt) - 1.0  # (N, T, L)
    # Normalize to probability distribution across L
    bid_sum = bid_q.sum(axis=2, keepdims=True) + EPS  # (N, T, 1)
    p = bid_q / bid_sum  # (N, T, L)
    # Compute kurtosis via standardized 4th moment
    # μ = Σ p_i × i (mean position)
    levels = np.arange(L, dtype=np.float64)  # (L,)
    mu = (p * levels[None, None, :]).sum(axis=2)  # (N, T)
    centered = levels[None, None, :] - mu[:, :, None]  # (N, T, L)
    var = (p * centered ** 2).sum(axis=2)  # (N, T)
    kurt_raw = (p * centered ** 4).sum(axis=2) / (var ** 2 + EPS)  # (N, T)
    # Excess kurtosis: kurt_raw - 3
    kurt = kurt_raw - 3.0
    return kurt[:, :, None].astype(np.float32)


def compute_time_features(sample_ts_us: np.ndarray, T: int = 600) -> np.ndarray:
    """Returns (N, T, 2): [hour_sin, day_sin], broadcast constant across T."""
    N = len(sample_ts_us)
    out = np.zeros((N, T, 2), dtype=np.float32)
    if N == 0: return out
    for s_i, ts_us in enumerate(sample_ts_us):
        t = dt.datetime.fromtimestamp(int(ts_us) / 1e6, tz=dt.timezone.utc)
        hour_frac = t.hour + t.minute / 60.0 + t.second / 3600.0
        hour_sin = math.sin(2 * math.pi * hour_frac / 24.0)
        dow = t.weekday()  # 0=Mon, 6=Sun
        day_sin = math.sin(2 * math.pi * dow / 7.0)
        out[s_i, :, 0] = hour_sin
        out[s_i, :, 1] = day_sin
    return out


def process_day(date: str, v4_dir, trades_dir, out_dir, force=False):
    out_path = pathlib.Path(out_dir) / f"{date}.npz"
    if out_path.exists() and not force:
        return date, "skip"
    try:
        v4 = np.load(pathlib.Path(v4_dir) / f"{date}.npz", allow_pickle=True)
        X_raw = v4["X_raw"]
        ts = v4["timestamps"]
        N, T, L, _ = X_raw.shape
        if N == 0:
            tv = np.zeros((0, T, 19), dtype=np.float32)
            np.savez_compressed(out_path, timestamps=ts, tv_feats=tv, feat_names=FEAT_NAMES)
            return date, "empty"

        book_v1 = compute_book_tv_v1(X_raw)  # (N, T, 4)
        book_v2 = compute_book_tv_v2(X_raw)  # (N, T, 3)
        trade_csv = pathlib.Path(trades_dir) / f"BTCUSDT-trades-{date}.csv.gz"
        if not trade_csv.exists():
            trade_csv = pathlib.Path(trades_dir) / date / "BTCUSDT.csv.gz"
        if trade_csv.exists():
            trades = read_trades_csv(trade_csv)
        else:
            trades = pd.DataFrame(columns=["timestamp", "side", "price", "amount", "side_sign", "ts_s"])
        trade_v1 = compute_trade_tv_v1(trades, ts, T=T)  # (N, T, 4)
        trade_v2 = compute_trade_tv_v2(trades, ts, T=T)  # (N, T, 3)
        # V4 NEW
        hawkes = compute_hawkes_intensity(trades, ts, T=T)[:, :, None]  # (N, T, 1)
        kyle = compute_kyle_lambda(trades, ts, T=T)[:, :, None]  # (N, T, 1)
        obi_kurt = compute_obi_kurt(X_raw)  # (N, T, 1)
        time_feats = compute_time_features(ts, T=T)  # (N, T, 2)

        tv = np.concatenate([
            trade_v1[:, :, 0:2],  # sv_60, sv_300
            trade_v1[:, :, 2:4],  # apb_60, apb_300
            book_v1,              # energy, ent, dva, qd
            trade_v2,             # ofi, rate, meta_buy
            book_v2,              # l1_imb, total_depth, l5_diff
            hawkes,               # NEW: Hawkes
            kyle,                 # NEW: Kyle's λ
            obi_kurt,             # NEW: OBI kurtosis
            time_feats,           # NEW: hour_sin, day_sin
        ], axis=-1).astype(np.float32)
        np.savez_compressed(out_path, timestamps=ts, tv_feats=tv, feat_names=FEAT_NAMES)
        return date, f"ok N={N}"
    except Exception as e:
        import traceback
        return date, f"err: {e} {traceback.format_exc()[-200:]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4-dir", default="data/npz_v4")
    ap.add_argument("--trades-dir", default="/mnt/storage/share/23-25-BTCUSDT/trades")
    ap.add_argument("--out-dir", default="data/npz_v4_tv_overlay_v4")
    ap.add_argument("--dates", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    v4_dir = pathlib.Path(args.v4_dir)
    if args.dates:
        dates = args.dates
    else:
        dates = sorted([p.stem for p in v4_dir.glob("*.npz")])
    print(f"Processing {len(dates)} days → {out_dir}")
    t0 = time.time()
    if args.workers <= 1:
        for d in dates:
            r = process_day(d, args.v4_dir, args.trades_dir, args.out_dir, args.force)
            print(f"  {r[0]}: {r[1]}")
    else:
        with cf.ProcessPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(process_day, d, args.v4_dir, args.trades_dir, args.out_dir, args.force) for d in dates]
            for i, f in enumerate(cf.as_completed(futs)):
                r = f.result()
                if i % 50 == 0 or "err" in r[1]:
                    print(f"  [{i+1}/{len(dates)}] {r[0]}: {r[1]} ({time.time()-t0:.0f}s)")
    print(f"Done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()

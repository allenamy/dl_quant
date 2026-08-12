"""Build TV v3: TV v2 (14 ch) + 3 long-horizon RV channels (17 ch total).

Adds 3 NEW channels (broadcast constant across T within sample — regime indicator):
  [14] rv_1h_bps2   — realized variance of 1s mid log returns over past 1h
  [15] rv_4h_bps2   — past 4h
  [16] rv_24h_bps2  — past 24h

Source: data/midprice_per_day/*.npz with `timestamps_s`, `mid_price` per-second
across days. Cross-day load for 24h window.

Per sample at anchor t_us:
  rv_Wh = sum_{i in [t-W*3600, t]} log(mid_i / mid_{i-1})^2 × 1e8 (bps²)

Note: broadcast constant across 600 timesteps within sample. The DL model
sees this as a "regime context" feature persistent through the sample window.

Output: data/npz_v4_tv_overlay_v3/<date>.npz with tv_feats (N, 600, 17).
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

# Reuse v2 builder for first 14 channels
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_tv_feature_overlay_v2 import (
    FEAT_NAMES as FEAT_NAMES_V2,
    compute_book_tv_v1,
    compute_book_tv_v2,
    compute_trade_tv_v1,
    compute_trade_tv_v2,
    read_trades_csv,
)

EPS = 1e-12

FEAT_NAMES = np.concatenate([
    FEAT_NAMES_V2,
    np.array(["rv_1h_bps2", "rv_4h_bps2", "rv_24h_bps2"], dtype="<U24"),
])


def load_mid_window(midprice_dir: pathlib.Path, date: str, lookback_days: int = 2):
    """Load per-second mid prices for `date` + previous `lookback_days`.

    Returns (timestamps_s, mid_log) sorted, with `mid_log = log(mid)`.
    Missing days return empty arrays for that day.
    """
    d_target = dt.datetime.strptime(date, "%Y-%m-%d").date()
    all_ts = []; all_mid = []
    for back in range(lookback_days, -1, -1):
        d = d_target - dt.timedelta(days=back)
        p = midprice_dir / f"{d.isoformat()}.npz"
        if not p.exists():
            continue
        z = np.load(p, allow_pickle=True)
        ts = z["timestamps_s"].astype(np.int64)
        mid = z["mid_price"].astype(np.float64)
        m = (mid > 0) & np.isfinite(mid)
        all_ts.append(ts[m]); all_mid.append(np.log(mid[m]))
    if not all_ts:
        return np.array([], dtype=np.int64), np.array([], dtype=np.float64)
    ts_all = np.concatenate(all_ts); mid_log_all = np.concatenate(all_mid)
    order = np.argsort(ts_all)
    return ts_all[order], mid_log_all[order]


def compute_rv_channels(sample_ts_us: np.ndarray, mid_ts_s: np.ndarray, mid_log: np.ndarray,
                        T: int = 600) -> np.ndarray:
    """Compute (N, T, 3) RV channels broadcast constant per sample.

    Channels: [rv_1h, rv_4h, rv_24h] in bps².
    """
    N = len(sample_ts_us)
    out = np.zeros((N, T, 3), dtype=np.float32)
    if N == 0 or len(mid_ts_s) < 2:
        return out
    sample_ts_s = (sample_ts_us // 1_000_000).astype(np.int64)
    # 1s log returns
    log_ret_bps = np.diff(mid_log) * 1e4  # (M-1,), in bps
    ret_sq = log_ret_bps * log_ret_bps  # bps²
    # Cumulative sum for fast windowed sum
    ret_sq_cs = np.concatenate([[0.0], np.cumsum(ret_sq)])  # (M,)
    # `mid_ts_s[i]` corresponds to log_ret_bps[i-1] for i>=1
    # For window ending at t (inclusive), need ret_sq indices from t_lo+1 to t (where ts == t_lo, t_lo+1, ... t)
    windows = [3600, 14400, 86400]  # 1h, 4h, 24h in seconds
    for s_i, t_s in enumerate(sample_ts_s):
        # find idx where mid_ts_s == t_s (closest)
        idx_end = np.searchsorted(mid_ts_s, t_s, side='right') - 1
        if idx_end < 1:
            continue
        for w_i, W in enumerate(windows):
            t_lo = t_s - W
            idx_lo = np.searchsorted(mid_ts_s, t_lo, side='left')
            # Sum of ret_sq from idx_lo to idx_end
            # ret_sq[idx_lo .. idx_end-1] gives returns for mid_ts_s[idx_lo+1 .. idx_end]
            # which covers prices at idx_lo+1 (after t_lo) to idx_end (at or before t_s)
            if idx_end <= idx_lo:
                continue
            rv = ret_sq_cs[idx_end] - ret_sq_cs[idx_lo]
            # broadcast constant across T
            out[s_i, :, w_i] = rv
    return out


def process_day(date: str, v4_dir, trades_dir, midprice_dir, out_dir, force=False):
    out_path = pathlib.Path(out_dir) / f"{date}.npz"
    if out_path.exists() and not force:
        return date, "skip"
    try:
        v4 = np.load(pathlib.Path(v4_dir) / f"{date}.npz", allow_pickle=True)
        X_raw = v4["X_raw"]
        ts = v4["timestamps"]
        N, T, L, _ = X_raw.shape
        if N == 0:
            tv = np.zeros((0, T, 17), dtype=np.float32)
            np.savez_compressed(out_path, timestamps=ts, tv_feats=tv, feat_names=FEAT_NAMES)
            return date, "empty"

        # v1 + v2 channels (14 total)
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

        # v3 NEW: long-horizon RV channels (need cross-day midprice)
        mid_ts_s, mid_log = load_mid_window(pathlib.Path(midprice_dir), date, lookback_days=2)
        rv = compute_rv_channels(ts, mid_ts_s, mid_log, T=T)  # (N, T, 3)

        tv = np.concatenate([
            trade_v1[:, :, 0:2],  # sv_60, sv_300
            trade_v1[:, :, 2:4],  # apb_60, apb_300
            book_v1,              # energy, ent, dva, qd
            trade_v2,             # ofi, rate, meta_buy
            book_v2,              # l1_imb, total_depth, l5_diff
            rv,                   # rv_1h, rv_4h, rv_24h
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
    ap.add_argument("--midprice-dir", default="data/midprice_per_day")
    ap.add_argument("--out-dir", default="data/npz_v4_tv_overlay_v3")
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
            r = process_day(d, args.v4_dir, args.trades_dir, args.midprice_dir, args.out_dir, args.force)
            print(f"  {r[0]}: {r[1]}")
    else:
        with cf.ProcessPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(process_day, d, args.v4_dir, args.trades_dir, args.midprice_dir, args.out_dir, args.force) for d in dates]
            for i, f in enumerate(cf.as_completed(futs)):
                r = f.result()
                if i % 50 == 0 or "err" in r[1]:
                    print(f"  [{i+1}/{len(dates)}] {r[0]}: {r[1]} ({time.time()-t0:.0f}s)")
    print(f"Done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()

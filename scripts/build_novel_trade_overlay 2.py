"""Build trade-derived novel-feature overlay NPZs from raw trades CSV.

Per sample at timestamp t, computes features over rolling windows:
  sv_ewm_60s, sv_ewm_300s, sv_ewm_600s     - signed_vol EWMA at HL 60/300/600
  apb_60s, apb_300s, apb_600s              - rolling VWAP(window)/TWAP(window) sigmoid → [-1, 1]
  run_signed_qty                            - sum signed qty in current same-side run ending at t
  run_len_sec                                - duration of current same-side run ending at t
  cum_abs_qty_60s, cum_abs_qty_600s         - cumulative abs trade qty over window

Output: data/npz_v4_novel_trade/<date>.npz with:
  timestamps     (N,) int64
  novel_trade_feats   (N, 10) float32
  feat_names     (10,) <U32

Reuses raw trades reader pattern from build_tradeflow_overlay.py.
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
import io
import math
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

FEAT_NAMES = np.array([
    "sv_ewm_60s", "sv_ewm_300s", "sv_ewm_600s",
    "apb_60s", "apb_300s", "apb_600s",
    "run_signed_qty", "run_len_sec",
    "cum_abs_qty_60s", "cum_abs_qty_600s",
], dtype="<U32")


def read_trades_csv(path: Path) -> pd.DataFrame:
    proc = subprocess.run(["gunzip", "-c", str(path)], capture_output=True, check=False)
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"gunzip failed for {path}: {proc.stderr[:200]}")
    df = pd.read_csv(io.BytesIO(proc.stdout), usecols=["timestamp", "side", "price", "amount"])
    df["side_sign"] = np.where(df["side"].values == "buy", 1.0, -1.0).astype(np.float32)
    df = df.rename(columns={"timestamp": "ts_us"})
    df["ts_s"] = (df["ts_us"].values // 1_000_000).astype(np.int64)
    df["amount"] = df["amount"].astype(np.float32)
    df["price"] = df["price"].astype(np.float64)
    return df[["ts_us", "ts_s", "side_sign", "price", "amount"]].sort_values("ts_us").reset_index(drop=True)


def stable_sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z, dtype=np.float64)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def compute_novel_trade_features(
    v4_npz: dict,
    trades: pd.DataFrame,
    mid_ts: np.ndarray,
    mid_grid: np.ndarray,
) -> np.ndarray:
    """Per-second-bucket vectorized features + per-trade meta-order run state."""
    timestamps_us = v4_npz["timestamps"].astype(np.int64)
    N = len(timestamps_us)
    if N == 0:
        return np.zeros((0, 10), dtype=np.float32)

    grid_start = int(mid_ts[0]) if len(mid_ts) else 0
    grid_end = int(mid_ts[-1]) + 1 if len(mid_ts) else 1
    span = grid_end - grid_start
    if span <= 0 or span > 3 * 86400:
        return np.zeros((N, 10), dtype=np.float32)

    # Per-second aggregates: signed_vol, abs_vol, vwap_num, vwap_den
    sv = np.zeros(span, dtype=np.float64)
    av = np.zeros(span, dtype=np.float64)
    vnum = np.zeros(span, dtype=np.float64)
    vden = np.zeros(span, dtype=np.float64)

    if len(trades) > 0:
        idx = trades["ts_s"].values - grid_start
        in_range = (idx >= 0) & (idx < span)
        if in_range.any():
            idx_r = idx[in_range]
            ss = trades["side_sign"].values[in_range]
            amt = trades["amount"].values[in_range].astype(np.float64)
            prc = trades["price"].values[in_range]
            np.add.at(sv, idx_r, ss * amt)
            np.add.at(av, idx_r, amt)
            np.add.at(vnum, idx_r, prc * amt)
            np.add.at(vden, idx_r, amt)

    # EWMA signed_vol at multiple HL (continuous 1s grid, simple alpha)
    def ewma_hl(arr, hl_s):
        alpha = 1.0 - math.exp(-math.log(2.0) / hl_s)
        out = np.zeros_like(arr)
        cur = 0.0
        for i in range(len(arr)):
            cur = alpha * arr[i] + (1.0 - alpha) * cur
            out[i] = cur
        return out

    sv_ewm_60 = ewma_hl(sv, 60.0)
    sv_ewm_300 = ewma_hl(sv, 300.0)
    sv_ewm_600 = ewma_hl(sv, 600.0)

    # Cumulative sums for O(1) rolling window
    sv_cs = np.cumsum(sv)
    av_cs = np.cumsum(av)
    vnum_cs = np.cumsum(vnum)
    vden_cs = np.cumsum(vden)

    def _rs(cs, s, e):
        sc = cs[s - 1] if s > 0 else 0.0
        return float(cs[e - 1] - sc) if e > s else 0.0

    # APB scale: log(twap/vwap) * 1e4 → sigmoid; clip z
    apb_z_scale = 1e4
    apb_clip = 50.0

    # Sample timestamps (1s grid)
    sample_ts_s = timestamps_us // 1_000_000
    offsets = sample_ts_s - grid_start

    # Meta-order run state computed by sequential pass on trades
    # For each trade timestamp_us, we maintain run_signed_qty + run_start_ts.
    # Then we map run state to sample timestamps via searchsorted on trade ts_us.
    if len(trades) > 0:
        trade_ts_us = trades["ts_us"].values.astype(np.int64)
        trade_side = trades["side_sign"].values
        trade_amt = trades["amount"].values.astype(np.float64)
        run_sq = np.zeros(len(trades), dtype=np.float64)
        run_len_s = np.zeros(len(trades), dtype=np.float64)
        cur_dir = 0.0
        cur_signed = 0.0
        cur_start = 0
        for i in range(len(trades)):
            d = trade_side[i]; v = trade_amt[i]; ts = trade_ts_us[i]
            if cur_dir == 0.0 or d == cur_dir:
                if cur_dir == 0.0:
                    cur_start = ts
                cur_dir = d
                cur_signed += d * v
            else:
                cur_dir = d
                cur_signed = d * v
                cur_start = ts
            run_sq[i] = cur_signed
            run_len_s[i] = (ts - cur_start) / 1e6
    else:
        trade_ts_us = np.array([], dtype=np.int64)
        run_sq = np.array([], dtype=np.float64)
        run_len_s = np.array([], dtype=np.float64)

    # For each sample, find most-recent trade ≤ sample_ts_us, get run state
    feats = np.zeros((N, 10), dtype=np.float64)
    for i in range(N):
        off = int(offsets[i])
        if off < 0 or off >= span:
            continue
        # Per-second EWMA values
        feats[i, 0] = sv_ewm_60[off]
        feats[i, 1] = sv_ewm_300[off]
        feats[i, 2] = sv_ewm_600[off]
        # APB at multiple windows
        for j, W in enumerate((60, 300, 600)):
            s_lo = max(0, off - W + 1)
            s_hi = off + 1
            num = _rs(vnum_cs, s_lo, s_hi)
            den = _rs(vden_cs, s_lo, s_hi)
            vwap = num / den if den > 1e-9 else np.nan
            # TWAP from mid grid
            mid_slice = mid_grid[s_lo:s_hi]
            mid_valid = mid_slice[np.isfinite(mid_slice)]
            twap = mid_valid.mean() if len(mid_valid) >= 2 else np.nan
            if np.isfinite(vwap) and np.isfinite(twap) and vwap > 0 and twap > 0:
                z = math.log(twap / vwap) * apb_z_scale
                z = max(-apb_clip, min(apb_clip, z))
                apb = (stable_sigmoid(np.array([z]))[0] - 0.5) * 2.0
            else:
                apb = 0.0
            feats[i, 3 + j] = apb
        # Meta-order run state
        if len(trade_ts_us) > 0:
            sample_us = int(sample_ts_s[i] * 1_000_000)
            # Last trade idx ≤ sample_us
            k = np.searchsorted(trade_ts_us, sample_us, side="right") - 1
            if k >= 0:
                feats[i, 6] = run_sq[k]
                feats[i, 7] = run_len_s[k]
        # cum_abs_qty
        for j, W in enumerate((60, 600)):
            s_lo = max(0, off - W + 1)
            s_hi = off + 1
            feats[i, 8 + j] = _rs(av_cs, s_lo, s_hi)

    return np.nan_to_num(feats.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)


def process_day(date_name: str, v4_dir: Path, trades_dir: Path, midprice_dir: Path, out_dir: Path):
    t0 = time.time()
    try:
        v4_path = v4_dir / f"{date_name}.npz"
        trades_path = trades_dir / date_name / "BTCUSDT.csv.gz"
        mid_path = midprice_dir / f"{date_name}.npz"
        out_path = out_dir / f"{date_name}.npz"

        if not v4_path.exists() or not trades_path.exists() or not mid_path.exists():
            return (date_name, time.time() - t0, "MISSING")
        if out_path.exists():
            return (date_name, time.time() - t0, "SKIP")

        v4 = np.load(str(v4_path), allow_pickle=True)
        mid = np.load(str(mid_path), allow_pickle=True)

        # Build midprice grid (deduplicate)
        mid_ts_all = mid["timestamps_s"].astype(np.int64)
        mid_prc = mid["mid_price"].astype(np.float64)
        order_valid = np.zeros(len(mid_ts_all), dtype=bool)
        cur_max = -1
        for i, t in enumerate(mid_ts_all):
            if t >= cur_max:
                order_valid[i] = True
                cur_max = t
        mid_ts_all = mid_ts_all[order_valid]
        mid_prc = mid_prc[order_valid]
        if len(mid_ts_all) < 2:
            return (date_name, time.time() - t0, "NO_MID")
        t_start = int(mid_ts_all[0])
        t_end = int(mid_ts_all[-1]) + 1
        span = t_end - t_start
        if span <= 0 or span > 3 * 86400:
            return (date_name, time.time() - t0, "BAD_SPAN")
        mid_grid = np.full(span, np.nan, dtype=np.float64)
        offs = mid_ts_all - t_start
        in_range = (offs >= 0) & (offs < span)
        mid_grid[offs[in_range]] = mid_prc[in_range]
        mid_grid = pd.Series(mid_grid).ffill(limit=60).to_numpy()
        mid_ts = np.arange(t_start, t_end, dtype=np.int64)

        trades = read_trades_csv(trades_path)
        feats = compute_novel_trade_features(v4, trades, mid_ts, mid_grid)

        out_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            str(out_path),
            timestamps=v4["timestamps"],
            novel_trade_feats=feats,
            feat_names=FEAT_NAMES,
        )
        n_valid = int((np.abs(feats).sum(axis=1) > 0).sum())
        return (date_name, time.time() - t0, f"OK valid={n_valid}/{len(feats)}")
    except Exception as e:
        return (date_name, time.time() - t0, f"ERR: {type(e).__name__}: {str(e)[:120]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4-dir", default="data/npz_v4")
    ap.add_argument("--trades-dir", default="crypto_data/trades/trades")
    ap.add_argument("--midprice-dir", default="data/midprice_per_day")
    ap.add_argument("--out-dir", default="data/npz_v4_novel_trade")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dates", nargs="*", default=None)
    args = ap.parse_args()

    v4_dir = Path(args.v4_dir)
    trades_dir = Path(args.trades_dir)
    mid_dir = Path(args.midprice_dir)
    out_dir = Path(args.out_dir)

    dates = args.dates or sorted(p.stem for p in mid_dir.glob("*.npz"))
    print(f"Processing {len(dates)} days → {out_dir}, workers={args.workers}", flush=True)
    t0 = time.time()

    ok = skip = err = 0
    with cf.ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_day, d, v4_dir, trades_dir, mid_dir, out_dir): d for d in dates}
        for i, fut in enumerate(cf.as_completed(futures)):
            name, dt, status = fut.result()
            if status.startswith("OK"):
                ok += 1
            elif status == "SKIP":
                skip += 1
            else:
                err += 1
                print(f"  {name}: {status} ({dt:.1f}s)", flush=True)
            if (i + 1) % 50 == 0:
                print(f"  progress {i+1}/{len(dates)} ok={ok} skip={skip} err={err} ({time.time()-t0:.0f}s)", flush=True)

    print(f"\nDone: ok={ok} skip={skip} err={err} in {time.time()-t0:.0f}s → {out_dir}")


if __name__ == "__main__":
    main()

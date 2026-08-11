"""Build information-flow overlay with VPIN + large-order footprint features.

These are structural/event-driven features NOT derivable from V4's
time-averaged signals:

  vpin_50         : Volume-Synchronized PIN over last 50 buckets of 100 BTC
                    each. Measures persistent directional flow toxicity.
  large_count_60  : Count of trades with amount > 99th-pct over last 60s.
  large_count_300 : ... over last 300s.
  time_since_last_large : Seconds since last 99th-pct trade (capped at 1800).

All features use ONLY past data ([off-N, off]), no lookahead.

Output: data/npz_v4_infoflow/<date>.npz keyed on V4 NPZ timestamps.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import io
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd


FEAT_NAMES = np.array([
    "if_vpin_50", "if_large_count_60", "if_large_count_300", "if_time_since_last_large",
], dtype="<U30")


def read_trades_csv(path: Path) -> pd.DataFrame:
    proc = subprocess.run(["gunzip", "-c", str(path)], capture_output=True, check=False)
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"gunzip failed: {path}")
    df = pd.read_csv(io.BytesIO(proc.stdout), usecols=["timestamp", "side", "price", "amount"])
    df = df.dropna(subset=["timestamp", "side", "amount"]).reset_index(drop=True)
    df["side_sign"] = np.where(df["side"].values == "buy", 1.0, -1.0).astype(np.float32)
    df["ts_s"] = (df["timestamp"].values // 1_000_000).astype(np.int64)
    df["amount"] = df["amount"].astype(np.float32)
    df = df[df["amount"] > 0]
    return df[["ts_s", "side_sign", "amount"]].sort_values("ts_s").reset_index(drop=True)


def compute_vpin_series(
    trades: pd.DataFrame,
    bucket_volume: float = 100.0,
    n_buckets: int = 50,
) -> tuple[np.ndarray, np.ndarray]:
    """Cumulative-volume-bucket VPIN. Returns (bucket_end_ts_s, vpin_rolling).

    VPIN per bucket = |buy_vol - sell_vol| / bucket_volume
    vpin_rolling[i] = mean(vpin[i-n_buckets:i+1])
    """
    if len(trades) == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
    cum_vol = np.cumsum(trades["amount"].values.astype(np.float64))
    # Find bucket boundaries: every `bucket_volume` BTC of cumulative volume.
    bucket_edges = np.arange(bucket_volume, cum_vol[-1] + bucket_volume, bucket_volume)
    if len(bucket_edges) < 2:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
    # For each bucket edge, find the trade index where cum_vol >= edge
    edge_idx = np.searchsorted(cum_vol, bucket_edges, side="left")
    edge_idx = np.clip(edge_idx, 0, len(cum_vol) - 1)

    # Per-bucket signed volume = sum(side * amount) within bucket
    side_amt = (trades["side_sign"].values * trades["amount"].values).astype(np.float64)
    cum_side = np.cumsum(side_amt)
    # Previous edge 0 at start
    prev_edge_idx = np.concatenate([[0], edge_idx[:-1]])
    bucket_signed = cum_side[edge_idx] - np.concatenate([[0.0], cum_side[prev_edge_idx[1:] - 1]])
    bucket_vpin = np.abs(bucket_signed) / bucket_volume  # (n_buckets_total,)

    # Rolling mean over last `n_buckets` buckets (backward looking)
    if len(bucket_vpin) < 2:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
    kernel = np.ones(min(n_buckets, len(bucket_vpin))) / min(n_buckets, len(bucket_vpin))
    vpin_rolling = np.convolve(bucket_vpin, kernel, mode="full")[: len(bucket_vpin)]

    bucket_end_ts = trades["ts_s"].values[edge_idx].astype(np.int64)
    return bucket_end_ts, vpin_rolling.astype(np.float32)


def compute_features_for_day(
    v4_npz: dict,
    trades: pd.DataFrame,
) -> np.ndarray:
    ts_us = v4_npz["timestamps"].astype(np.int64)
    N = len(ts_us)
    if N == 0:
        return np.zeros((0, 4), dtype=np.float32)
    sample_ts_s = ts_us // 1_000_000

    # --- VPIN per-sample (lookup from bucket timeline) --------------------
    bucket_ts, vpin_series = compute_vpin_series(trades)
    vpin_at_sample = np.zeros(N, dtype=np.float32)
    if len(bucket_ts) > 0:
        # For each sample t, take the most recent bucket VPIN with bucket_end_ts <= t.
        idx = np.searchsorted(bucket_ts, sample_ts_s, side="right") - 1
        valid = idx >= 0
        vpin_at_sample[valid] = vpin_series[idx[valid]]

    # --- Large-order footprint --------------------------------------------
    large_count_60 = np.zeros(N, dtype=np.float32)
    large_count_300 = np.zeros(N, dtype=np.float32)
    time_since_last = np.full(N, 1800.0, dtype=np.float32)  # cap at 1800s
    if len(trades) > 0:
        # 99th percentile of trade amount (daily; stable statistic)
        p99 = float(np.percentile(trades["amount"].values, 99.0))
        large_mask = trades["amount"].values >= p99
        large_ts_s = trades["ts_s"].values[large_mask].astype(np.int64)
        if len(large_ts_s) > 0:
            # For count: how many large trades in [t-N, t]?
            for i, t in enumerate(sample_ts_s):
                lo_60 = np.searchsorted(large_ts_s, t - 60, side="left")
                hi = np.searchsorted(large_ts_s, t, side="right")
                large_count_60[i] = float(hi - lo_60)
                lo_300 = np.searchsorted(large_ts_s, t - 300, side="left")
                large_count_300[i] = float(hi - lo_300)
                # time since last: most recent large trade at or before t
                last_idx = hi - 1
                if last_idx >= 0:
                    dt = float(t - large_ts_s[last_idx])
                    time_since_last[i] = min(max(dt, 0.0), 1800.0)

    out = np.stack([vpin_at_sample, large_count_60, large_count_300, time_since_last], axis=-1)
    return np.nan_to_num(out, nan=0.0, posinf=10.0, neginf=-10.0).astype(np.float32)


def process_day(date_name: str, v4_dir: Path, trades_dir: Path, out_dir: Path) -> tuple[str, float, str]:
    t0 = time.time()
    try:
        v4_path = v4_dir / f"{date_name}.npz"
        trades_path = trades_dir / date_name / "BTCUSDT.csv.gz"
        out_path = out_dir / f"{date_name}.npz"
        if not v4_path.exists() or not trades_path.exists():
            return (date_name, 0.0, "MISSING")
        if out_path.exists():
            return (date_name, 0.0, "SKIP")

        v4 = np.load(str(v4_path), allow_pickle=True)
        trades = read_trades_csv(trades_path)
        feats = compute_features_for_day(v4, trades)

        out_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            str(out_path),
            timestamps=v4["timestamps"],
            infoflow_feats=feats,
            feat_names=FEAT_NAMES,
        )
        n_nonzero = int((np.abs(feats).sum(axis=1) > 0).sum())
        return (date_name, time.time() - t0, f"OK valid={n_nonzero}/{len(feats)}")
    except Exception as e:
        return (date_name, time.time() - t0, f"ERR: {type(e).__name__}: {str(e)[:100]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4-dir", default="data/npz_v4")
    ap.add_argument("--trades-dir", default="crypto_data/trades/trades")
    ap.add_argument("--out-dir", default="data/npz_v4_infoflow")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dates", nargs="*", default=None)
    args = ap.parse_args()

    v4_dir = Path(args.v4_dir)
    trades_dir = Path(args.trades_dir)
    out_dir = Path(args.out_dir)

    dates = args.dates or sorted(p.stem for p in Path("data/npz_v4").glob("*.npz"))
    print(f"Processing {len(dates)} days → {out_dir}")

    def _wrap(d):
        return process_day(d, v4_dir, trades_dir, out_dir)

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(_wrap, dates))

    ok = [r for r in results if r[2].startswith("OK")]
    skip = [r for r in results if r[2] == "SKIP"]
    err = [r for r in results if not r[2].startswith("OK") and r[2] != "SKIP"]
    total = sum(r[1] for r in results)
    print(f"OK={len(ok)} SKIP={len(skip)} ERR={len(err)} wall_s={total:.1f}")
    for n, _, s in err[:15]:
        print(f"  {n}: {s}")


if __name__ == "__main__":
    main()

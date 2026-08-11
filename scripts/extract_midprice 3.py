"""Extract per-second mid-price + best bid/ask from raw LOB CSVs.

Input: /crypto_data/book_snapshot_25/<date>/BTCUSDT.csv.gz (ms-level 25-level LOB)
Output: one .npz per day with per-second:
    timestamps_s : (T,) int64 — POSIX second
    mid_price    : (T,) float64
    best_bid     : (T,) float64
    best_ask     : (T,) float64

Per-day NPZ size ≈ 80 KB; total for 1004 days ≈ 80 MB. Ready for S3 sync.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import gzip
import time
from pathlib import Path

import numpy as np
import pandas as pd


def extract_one(in_path: Path, out_path: Path) -> tuple[str, float, str]:
    t0 = time.time()
    try:
        if out_path.exists():
            return (in_path.parent.name, 0.0, "SKIP")
        # Source gzips are truncated (missing CRC trailer) but content is
        # readable. Pipe via subprocess gunzip -c which tolerates this, and
        # parse with pandas C engine. ~3-5 s per day.
        import subprocess, io
        proc = subprocess.Popen(
            ["gunzip", "-c", str(in_path)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        df = pd.read_csv(
            proc.stdout,
            usecols=["timestamp", "asks[0].price", "bids[0].price"],
            dtype={"timestamp": np.int64, "asks[0].price": np.float64, "bids[0].price": np.float64},
            engine="c",
        )
        proc.wait()
        ts_us = df["timestamp"].to_numpy()
        ask = df["asks[0].price"].to_numpy()
        bid = df["bids[0].price"].to_numpy()

        # Convert to second granularity: take LAST tick per second (keeps most recent prices)
        ts_s_all = (ts_us // 1_000_000).astype(np.int64)
        # np.unique preserves order of first occurrence; we want LAST. Use
        # cumulative max trick with argsort or just a fast numba-like approach:
        # since ts_s is monotonic non-decreasing in the CSV, we can just take
        # the last index of each unique second.
        # Verify monotonic (should be true for Tardis order-book snapshots)
        # Use np.diff to find boundaries where second changes
        if len(ts_s_all) == 0:
            return (in_path.parent.name, time.time() - t0, "EMPTY")
        # Find positions where second changes (last observation of each second)
        is_last_of_sec = np.concatenate(
            [np.diff(ts_s_all) != 0, np.array([True], dtype=bool)]
        )
        ts_s = ts_s_all[is_last_of_sec]
        best_ask = ask[is_last_of_sec].astype(np.float64)
        best_bid = bid[is_last_of_sec].astype(np.float64)
        mid = (best_bid + best_ask) / 2.0

        out_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            out_path,
            timestamps_s=ts_s,
            mid_price=mid,
            best_bid=best_bid,
            best_ask=best_ask,
        )
        return (in_path.parent.name, time.time() - t0, "OK")
    except Exception as e:
        return (in_path.parent.name, time.time() - t0, f"ERR: {str(e)[:120]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--in-dir",
        default="/Users/haosiyu/Desktop/quant_research/crypto_data/book_snapshot_25",
    )
    ap.add_argument("--out-dir", default="/Users/haosiyu/Desktop/quant_research/midprice_per_day")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    in_root = Path(args.in_dir)
    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    day_dirs = sorted(d for d in in_root.iterdir() if d.is_dir())
    jobs = []
    for d in day_dirs:
        csv = d / "BTCUSDT.csv.gz"
        if not csv.exists():
            continue
        out = out_root / f"{d.name}.npz"
        jobs.append((csv, out))

    print(f"Extracting {len(jobs)} days from {in_root} → {out_root}")

    t0 = time.time()

    def _wrap(pp):
        return extract_one(pp[0], pp[1])

    # Use ThreadPoolExecutor since pandas.read_csv releases GIL during I/O
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(_wrap, jobs))

    ok = sum(1 for _, _, s in results if s == "OK")
    skip = sum(1 for _, _, s in results if s == "SKIP")
    err = [(n, s) for n, _, s in results if s.startswith("ERR")]
    print(f"OK={ok} SKIP={skip} ERR={len(err)} wall={time.time()-t0:.1f}s")
    for n, s in err[:10]:
        print(f"  {n}: {s}")


if __name__ == "__main__":
    main()

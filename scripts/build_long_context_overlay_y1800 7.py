"""Build long-context feature overlay for y_1800 stride=600 NPZ.

Why a separate script (vs reusing build_smoothed_target_overlay.py)
-------------------------------------------------------------------
The existing y_600 overlay was generated for stride=180 timestamps and uses
1800/3600s lookback windows. For y_1800 with horizon=1800 and stride=600:

1. Sample timestamps are different (stride=600 vs 180): the overlay must
   re-run with the y_1800 NPZ's `timestamps` array.
2. Lookback windows of "1800s" are now degenerate (= horizon), so we widen
   to 3600s / 7200s to provide genuinely new signal beyond what the model's
   input_len=1200 already sees.

Output features (6, per sample anchor, broadcast unchanged across L)
--------------------------------------------------------------------
- lr_3600 :  log(mid[t] / mid[t-3600])         past-1h log return
- lr_7200 :  log(mid[t] / mid[t-7200])         past-2h log return (NEW vs input)
- rv_3600 :  realised vol over [t-3600, t]
- rv_7200 :  realised vol over [t-7200, t]     (NEW — extends past input_len)
- hurst   :  log(rv_300 / rv_3600)             vol-regime indicator
- mz_7200 :  (mid[t] - mean[t-7200,t]) / std   long-term mean-reversion signal

All 6 features look BACKWARD only — no lookahead leak.

Output: data/npz_v4_smooth_y1800/<date>.npz with:
  long_context_feats (N, 6)  — float32, broadcast-ready
  timestamps         (N,)    — int64 us, mirrors source NPZ for alignment check
  mask               (N,)    — uint8, 1 if all 6 features computable, else 0

Usage (pod, after y_1800 NPZ is built)
--------------------------------------
    python scripts/build_long_context_overlay_y1800.py \\
        --src-npz-dir data/npz_v4_y1800 \\
        --mid-dir data/midprice_per_day \\
        --out-dir data/npz_v4_smooth_y1800 \\
        --workers 8

Then enable in any y_1800 config via:
    "data": { "smooth_target_dir": "data/npz_v4_smooth_y1800", ... }
The dataset code already injects long_context_feats from this overlay path
(src/training/dataset.py:537).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import time
from pathlib import Path

import numpy as np

EPS = 1e-9
N_FEATS = 6


def build_second_grid(mid_data) -> tuple[np.ndarray, np.ndarray]:
    """Same logic as build_smoothed_target_overlay.build_second_grid:
    monotonic timestamp filter + 1s-resolution grid + ffill≤60s gaps.
    """
    ts = mid_data["timestamps_s"].astype(np.int64)
    mid = mid_data["mid_price"].astype(np.float64)
    if len(ts) == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    order_valid = np.zeros(len(ts), dtype=bool)
    current_max = -1
    for i, t in enumerate(ts):
        if t >= current_max:
            order_valid[i] = True
            current_max = t
    ts = ts[order_valid]
    mid = mid[order_valid]
    if len(ts) < 2:
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    t_start = int(ts[0])
    t_end = int(ts[-1]) + 1
    span = t_end - t_start
    if span <= 0 or span > 3 * 86400:
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    grid = np.full(span, np.nan, dtype=np.float64)
    offsets = ts - t_start
    in_range = (offsets >= 0) & (offsets < span)
    grid[offsets[in_range]] = mid[in_range]
    import pandas as pd
    s = pd.Series(grid).ffill(limit=60)
    return np.arange(t_start, t_end, dtype=np.int64), s.to_numpy()


def compute_long_context(
    src_npz,
    mid_ts: np.ndarray,
    mid_grid: np.ndarray,
) -> dict:
    """Compute 6 long-context features per sample timestamp.

    Returns dict with long_context_feats (N, 6), timestamps (N,), mask (N,).
    """
    timestamps_us = src_npz["timestamps"].astype(np.int64)
    N = len(timestamps_us)
    if N == 0:
        return {
            "long_context_feats": np.zeros((0, N_FEATS), dtype=np.float32),
            "timestamps": np.zeros(0, dtype=np.int64),
            "mask": np.zeros(0, dtype=np.uint8),
        }

    feats = np.zeros((N, N_FEATS), dtype=np.float64)
    mask = np.zeros(N, dtype=np.uint8)

    if len(mid_grid) == 0:
        return {
            "long_context_feats": feats.astype(np.float32),
            "timestamps": timestamps_us,
            "mask": mask,
        }

    grid_start = int(mid_ts[0])
    T = len(mid_grid)
    ts_s = timestamps_us // 1_000_000
    offsets = ts_s - grid_start  # (N,) in seconds

    # Cumulative sums for fast rolling stats
    mid_log = np.log(mid_grid + EPS)
    log_ret = np.diff(mid_log, prepend=mid_log[:1])
    log_ret_clean = np.where(np.isfinite(log_ret), log_ret, 0.0)
    cs_lr = np.cumsum(log_ret_clean)
    cs_lr2 = np.cumsum(log_ret_clean * log_ret_clean)
    isfin = np.isfinite(log_ret).astype(np.int64)
    cs_isfin = np.cumsum(isfin)
    cs_mid = np.cumsum(np.where(np.isfinite(mid_grid), mid_grid, 0.0))
    cs_mid2 = np.cumsum(np.where(np.isfinite(mid_grid), mid_grid * mid_grid, 0.0))
    cs_mid_isfin = np.cumsum(np.isfinite(mid_grid).astype(np.int64))

    def rs(c, s, e):
        if s >= e or s < 0 or e > len(c):
            return 0.0
        return float(c[e - 1]) - (float(c[s - 1]) if s > 0 else 0.0)

    def rs_int(c, s, e):
        if s >= e or s < 0 or e > len(c):
            return 0
        return int(c[e - 1]) - (int(c[s - 1]) if s > 0 else 0)

    LB_3600 = 3600
    LB_7200 = 7200
    LB_300 = 300

    for i in range(N):
        off = int(offsets[i])
        if off < 0 or off >= T:
            continue

        # Need at least 7200s of history for the longest feature
        if off - LB_7200 < 0:
            continue
        # Current mid must be defined
        mid_t = mid_grid[off]
        if not np.isfinite(mid_t):
            continue
        # Anchor mid 3600s back & 7200s back
        mid_3600 = mid_grid[off - LB_3600]
        mid_7200 = mid_grid[off - LB_7200]
        if not (np.isfinite(mid_3600) and np.isfinite(mid_7200)):
            continue

        # Past returns (look-back)
        lr_3600 = float(np.log((mid_t + EPS) / (mid_3600 + EPS)))
        lr_7200 = float(np.log((mid_t + EPS) / (mid_7200 + EPS)))

        # Realised vol over windows ([off - LB, off))
        n_3600 = max(rs_int(cs_isfin, off - LB_3600, off), 1)
        sq_3600 = rs(cs_lr2, off - LB_3600, off)
        rv_3600 = float(np.sqrt(max(sq_3600 / n_3600, 0.0) + EPS) * np.sqrt(n_3600))

        n_7200 = max(rs_int(cs_isfin, off - LB_7200, off), 1)
        sq_7200 = rs(cs_lr2, off - LB_7200, off)
        rv_7200 = float(np.sqrt(max(sq_7200 / n_7200, 0.0) + EPS) * np.sqrt(n_7200))

        # Hurst-proxy: short rv / long rv. Negative = mean-reverting (short<long),
        # positive = trending (short>long).
        n_300 = max(rs_int(cs_isfin, off - LB_300, off), 1)
        sq_300 = rs(cs_lr2, off - LB_300, off)
        rv_300 = float(np.sqrt(max(sq_300 / n_300, 0.0) + EPS))
        rv_3600_persec = float(np.sqrt(max(sq_3600 / n_3600, 0.0) + EPS))
        hurst = float(np.log((rv_300 + EPS) / (rv_3600_persec + EPS)))

        # mid z-score vs last 2h
        n_w = max(rs_int(cs_mid_isfin, off - LB_7200, off + 1), 1)
        sum_m = rs(cs_mid, off - LB_7200, off + 1)
        sum_m2 = rs(cs_mid2, off - LB_7200, off + 1)
        mean_m = sum_m / n_w
        var_m = max(sum_m2 / n_w - mean_m * mean_m, 0.0)
        std_m = float(np.sqrt(var_m) + EPS)
        mz = float((mid_t - mean_m) / std_m)

        feats[i, 0] = lr_3600
        feats[i, 1] = lr_7200
        feats[i, 2] = rv_3600
        feats[i, 3] = rv_7200
        feats[i, 4] = hurst
        feats[i, 5] = mz
        mask[i] = 1

    feats = np.nan_to_num(feats, nan=0.0, posinf=10.0, neginf=-10.0).astype(np.float32)
    return {
        "long_context_feats": feats,
        "timestamps": timestamps_us,
        "mask": mask,
    }


def process_day(date_name: str, src_dir: Path, mid_dir: Path, out_dir: Path) -> tuple[str, float, str]:
    t0 = time.time()
    try:
        src_path = src_dir / f"{date_name}.npz"
        mid_path = mid_dir / f"{date_name}.npz"
        out_path = out_dir / f"{date_name}.npz"
        if not src_path.exists() or not mid_path.exists():
            return (date_name, 0.0, "MISSING")
        if out_path.exists():
            return (date_name, 0.0, "SKIP")

        src = np.load(str(src_path), allow_pickle=True)
        mid = np.load(str(mid_path), allow_pickle=True)
        mid_ts, mid_grid = build_second_grid(mid)
        out = compute_long_context(src, mid_ts, mid_grid)

        out_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            str(out_path),
            long_context_feats=out["long_context_feats"],
            timestamps=out["timestamps"],
            mask=out["mask"],
        )
        return (date_name, time.time() - t0, "OK")
    except Exception as e:
        return (date_name, time.time() - t0, f"ERR:{type(e).__name__}:{e}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src-npz-dir", type=Path, default=Path("data/npz_v4_y1800"),
                    help="y_1800 NPZ directory (provides sample timestamps)")
    ap.add_argument("--mid-dir", type=Path, default=Path("data/midprice_per_day"),
                    help="midprice_per_day NPZ directory")
    ap.add_argument("--out-dir", type=Path, default=Path("data/npz_v4_smooth_y1800"),
                    help="output overlay directory")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None,
                    help="optional cap for smoke testing (N days)")
    args = ap.parse_args()

    if not args.src_npz_dir.exists():
        raise SystemExit(f"src-npz-dir does not exist: {args.src_npz_dir}")
    if not args.mid_dir.exists():
        raise SystemExit(f"mid-dir does not exist: {args.mid_dir}")

    src_files = sorted(args.src_npz_dir.glob("*.npz"))
    if args.limit:
        src_files = src_files[: args.limit]
    if not src_files:
        raise SystemExit(f"no NPZ files found in {args.src_npz_dir}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[lc-overlay-y1800] processing {len(src_files)} days "
          f"with {args.workers} workers → {args.out_dir}")

    t0 = time.time()
    n_ok = n_skip = n_err = n_missing = 0
    with cf.ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [
            ex.submit(process_day, p.stem, args.src_npz_dir, args.mid_dir, args.out_dir)
            for p in src_files
        ]
        for fut in cf.as_completed(futs):
            date, dt, status = fut.result()
            if status == "OK":
                n_ok += 1
                if n_ok % 50 == 0 or n_ok == 1:
                    print(f"  [{n_ok}/{len(src_files)}] {date} ok ({dt:.1f}s)")
            elif status == "SKIP":
                n_skip += 1
            elif status == "MISSING":
                n_missing += 1
            else:
                n_err += 1
                print(f"  ERROR {date}: {status}")

    print(f"[lc-overlay-y1800] done in {time.time()-t0:.1f}s | "
          f"ok={n_ok} skip={n_skip} missing={n_missing} err={n_err}")


if __name__ == "__main__":
    main()

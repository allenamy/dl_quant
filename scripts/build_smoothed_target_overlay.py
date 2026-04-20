"""Build y_600_smooth overlay NPZs + long-horizon context features.

For each day's existing V4 NPZ (data/npz_v4/<date>.npz), use the per-second
mid-price trajectory (midprice_per_day/<date>.npz) to compute:

1. y_600_smooth — smoothed target. Instead of y_600 = log(mid[t+600]/mid[t])
   (single-tick endpoint, ~10% noise), we use:
     y_600_smooth = log(mean(mid[t+570..t+630]) / mean(mid[t-30..t+30]))
   Averages endpoint over 60s window → reduces tick-noise by ~sqrt(60) ≈ 7.7x.

2. 6 long-horizon context features per sample (broadcast to all timesteps):
   - log_return_1800s: return over last 30 min (before window start)
   - log_return_3600s: return over last 60 min
   - rv_1800s_hist: realized vol over last 30 min
   - rv_3600s_hist: realized vol over last 60 min
   - hurst_1800s: log(RV_60_short / RV_1800_long) — regime indicator
   - mid_zscore_3600s: (current mid - last 60min mean) / last 60min std

These are TRULY NEW info beyond what's in the existing 600-step window.

Output: data/npz_v4_smooth/<date>.npz with:
  y_600_smooth       (N,) new smoothed target
  long_context_feats (N, 6) scalar-per-sample long-horizon features
  mask_smooth        (N,) 1 if both endpoints have enough mid-price data
  ... plus pass-through of everything else from source NPZ
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import time
from pathlib import Path

import numpy as np


EPS = 1e-9


def build_second_grid(mid_data: dict) -> tuple[np.ndarray, np.ndarray]:
    """Return (ts_grid_sec, mid_grid) at 1-second resolution with NaN for
    gaps. `mid_data` is an npz with timestamps_s and mid_price."""
    ts = mid_data["timestamps_s"].astype(np.int64)
    mid = mid_data["mid_price"].astype(np.float64)
    if len(ts) == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    t_start = int(ts[0])
    t_end = int(ts[-1]) + 1
    grid = np.full(t_end - t_start, np.nan, dtype=np.float64)
    offsets = ts - t_start
    # Take last observation per second if duplicates (np.maximum.at handles ordering)
    grid[offsets] = mid
    # Forward-fill small gaps (NaN propagation is acceptable beyond ~30s gaps)
    # Use pandas for robust ffill
    import pandas as pd
    s = pd.Series(grid)
    s = s.ffill(limit=60)  # fill up to 1-min gaps
    return np.arange(t_start, t_end, dtype=np.int64), s.to_numpy()


def compute_smoothed_and_context(
    v4_npz: dict,
    mid_ts: np.ndarray,
    mid_grid: np.ndarray,
    smooth_halfwidth_s: int = 30,
    long_context_s: tuple[int, int] = (1800, 3600),
) -> dict:
    """Compute y_600_smooth and long-context features for one day.

    Parameters
    ----------
    v4_npz : dict-like (np.load result) for the existing V4 NPZ
    mid_ts : (T,) int64 POSIX seconds where mid is defined on
    mid_grid : (T,) float64 1s-resolution mid price (NaN for gaps)

    Returns
    -------
    dict with y_600_smooth (N,), mask_smooth (N,), long_context_feats (N, 6)
    """
    timestamps_us = v4_npz["timestamps"].astype(np.int64)  # sample anchor in microseconds
    if len(timestamps_us) == 0:
        return {
            "y_600_smooth": np.zeros(0, dtype=np.float32),
            "mask_smooth": np.zeros(0, dtype=np.uint8),
            "long_context_feats": np.zeros((0, 6), dtype=np.float32),
        }

    # Convert to seconds and offset into grid
    ts_s = timestamps_us // 1_000_000
    grid_start = int(mid_ts[0])
    offsets = ts_s - grid_start  # (N,)

    N = len(timestamps_us)
    y_smooth = np.full(N, np.nan, dtype=np.float64)
    mask_smooth = np.zeros(N, dtype=np.uint8)
    long_feats = np.zeros((N, 6), dtype=np.float64)

    halfw = int(smooth_halfwidth_s)
    lc1, lc2 = long_context_s  # 1800s, 3600s
    T = len(mid_grid)

    # Precompute cumulative log returns for fast rolling stats
    # log_ret[i] = log(mid[i] / mid[i-1]), NaN propagates
    mid_log = np.log(mid_grid + EPS)
    # log_returns at 1s frequency
    log_ret = np.diff(mid_log, prepend=mid_log[:1])
    # Replace NaN log returns with 0 for cumsum; mask used separately
    log_ret_clean = np.where(np.isfinite(log_ret), log_ret, 0.0)
    log_ret_cumsum = np.cumsum(log_ret_clean)
    log_ret2_cumsum = np.cumsum(log_ret_clean * log_ret_clean)
    isfin = np.isfinite(log_ret).astype(np.int64)
    isfin_cumsum = np.cumsum(isfin)

    def rolling_sum(cumsum: np.ndarray, start: int, end: int) -> float:
        """Sum over [start, end) using cumsum trick."""
        start_c = cumsum[start - 1] if start > 0 else 0.0
        return float(cumsum[end - 1]) - start_c

    def rolling_sum_int(cumsum: np.ndarray, start: int, end: int) -> int:
        start_c = cumsum[start - 1] if start > 0 else 0
        return int(cumsum[end - 1]) - int(start_c)

    for i in range(N):
        off = int(offsets[i])  # t-anchor in seconds from grid_start
        # Smooth endpoints: anchor mean = mid[off-halfw : off+halfw]; target mean = mid[off+600-halfw : off+600+halfw]
        a0, a1 = off - halfw, off + halfw + 1
        t0, t1 = off + 600 - halfw, off + 600 + halfw + 1
        if a0 < 0 or t1 > T:
            # Not enough data for smoothing
            continue
        anchor_slice = mid_grid[a0:a1]
        target_slice = mid_grid[t0:t1]
        if np.any(~np.isfinite(anchor_slice)) or np.any(~np.isfinite(target_slice)):
            continue
        anchor_mean = anchor_slice.mean()
        target_mean = target_slice.mean()
        y_smooth[i] = np.log(target_mean / anchor_mean)
        mask_smooth[i] = 1

        # Long-horizon context: compute from mid_grid BEFORE the window start
        # Window: last 600 steps, i.e., [off-600, off]. Long-context is before that.
        # lc1 = 1800s back from off (not from window-start, so lc1 ends at off)
        # Use [off-lc1, off] and [off-lc2, off] for historical context.
        s1_start, s1_end = max(0, off - lc1), off
        s2_start, s2_end = max(0, off - lc2), off

        # log_return: sum of log_ret over window
        if s1_end > s1_start:
            lr_1800 = rolling_sum(log_ret_cumsum, s1_start, s1_end)
            sq_1800 = rolling_sum(log_ret2_cumsum, s1_start, s1_end)
            n_1800 = max(rolling_sum_int(isfin_cumsum, s1_start, s1_end), 1)
            rv_1800 = np.sqrt(max(sq_1800 / n_1800 - (lr_1800 / n_1800) ** 2, 0.0) + EPS) * np.sqrt(n_1800)
        else:
            lr_1800 = 0.0; rv_1800 = 0.0; n_1800 = 1

        if s2_end > s2_start:
            lr_3600 = rolling_sum(log_ret_cumsum, s2_start, s2_end)
            sq_3600 = rolling_sum(log_ret2_cumsum, s2_start, s2_end)
            n_3600 = max(rolling_sum_int(isfin_cumsum, s2_start, s2_end), 1)
            rv_3600 = np.sqrt(max(sq_3600 / n_3600 - (lr_3600 / n_3600) ** 2, 0.0) + EPS) * np.sqrt(n_3600)
        else:
            lr_3600 = 0.0; rv_3600 = 0.0; n_3600 = 1

        # Hurst-ish indicator: log(RV_60 / RV_1800). Negative = mean-reverting.
        s3_start, s3_end = max(0, off - 60), off
        if s3_end > s3_start:
            sq_60 = rolling_sum(log_ret2_cumsum, s3_start, s3_end)
            n_60 = max(rolling_sum_int(isfin_cumsum, s3_start, s3_end), 1)
            rv_60 = np.sqrt(sq_60 / n_60 + EPS)
        else:
            rv_60 = EPS
        hurst_proxy = np.log((rv_60 + EPS) / (rv_1800 / np.sqrt(max(n_1800, 1)) + EPS))

        # Mid-zscore over last 1h
        mid_window = mid_grid[max(0, off - lc2):off + 1]
        mid_window = mid_window[np.isfinite(mid_window)]
        if len(mid_window) > 10:
            mz = (mid_grid[off] - mid_window.mean()) / (mid_window.std() + EPS) if np.isfinite(mid_grid[off]) else 0.0
        else:
            mz = 0.0

        long_feats[i, 0] = lr_1800
        long_feats[i, 1] = lr_3600
        long_feats[i, 2] = rv_1800
        long_feats[i, 3] = rv_3600
        long_feats[i, 4] = hurst_proxy
        long_feats[i, 5] = mz

    # NaN/inf safety
    long_feats = np.nan_to_num(long_feats, nan=0.0, posinf=10.0, neginf=-10.0).astype(np.float32)
    y_smooth_out = np.where(np.isfinite(y_smooth), y_smooth, 0.0).astype(np.float32)

    return {
        "y_600_smooth": y_smooth_out,
        "mask_smooth": mask_smooth,
        "long_context_feats": long_feats,
    }


def process_day(date_name: str, in_v4: Path, in_mid: Path, out_dir: Path) -> tuple[str, float, str]:
    t0 = time.time()
    try:
        v4_path = in_v4 / f"{date_name}.npz"
        mid_path = in_mid / f"{date_name}.npz"
        out_path = out_dir / f"{date_name}.npz"
        if not v4_path.exists() or not mid_path.exists():
            return (date_name, 0.0, "MISSING")
        if out_path.exists():
            return (date_name, 0.0, "SKIP")

        v4 = np.load(str(v4_path), allow_pickle=True)
        mid = np.load(str(mid_path), allow_pickle=True)
        mid_ts, mid_grid = build_second_grid(mid)
        out = compute_smoothed_and_context(v4, mid_ts, mid_grid)

        # Include the mask_600 from source so overlay aligns with existing mask
        existing_mask = v4["y_mask_600"].astype(np.uint8) if "y_mask_600" in v4.files else v4["y_mask"].astype(np.uint8)
        combined_mask = (out["mask_smooth"] & existing_mask).astype(np.uint8)

        out_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            str(out_path),
            y_600_smooth=out["y_600_smooth"],
            mask_smooth=combined_mask,
            long_context_feats=out["long_context_feats"],
            timestamps=v4["timestamps"],  # for alignment verification
        )
        return (date_name, time.time() - t0, f"OK valid={int(combined_mask.sum())}/{len(combined_mask)}")
    except Exception as e:
        return (date_name, time.time() - t0, f"ERR: {str(e)[:120]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz-v4-dir", default="data/npz_v4")
    ap.add_argument("--midprice-dir", default="data/midprice_per_day")
    ap.add_argument("--out-dir", default="data/npz_v4_smooth")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    npz_dir = Path(args.npz_v4_dir)
    mid_dir = Path(args.midprice_dir)
    out_dir = Path(args.out_dir)

    dates = sorted(p.stem for p in mid_dir.glob("*.npz"))
    print(f"Processing {len(dates)} days from {npz_dir} + {mid_dir} → {out_dir}")

    def _wrap(d):
        return process_day(d, npz_dir, mid_dir, out_dir)

    # ThreadPoolExecutor + numpy releases GIL for vectorized ops
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(_wrap, dates))

    ok = [r for r in results if r[2].startswith("OK")]
    skip = [r for r in results if r[2] == "SKIP"]
    err = [r for r in results if r[2].startswith("ERR") or r[2] == "MISSING"]
    print(f"OK={len(ok)} SKIP={len(skip)} ERR/MISSING={len(err)}")
    for n, _, s in err[:10]:
        print(f"  {n}: {s}")


if __name__ == "__main__":
    main()

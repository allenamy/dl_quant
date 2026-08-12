"""Build intraday-regime per-day overlay NPZ from `data/midprice_per_day/*.npz`.

v5push Track v7 (2026-05-15): builds per-(N, T) overlay aligned to npz_v4
windows, with 4 channels of per-timestep regime context features. Mirrors the
TV overlay format (`tv_feats: (N, T, K)` + `feat_names`) so existing dataset
loader path (`tv_overlay_dir`-style) can reuse it via a new
`intraday_regime_dir` arg.

Usage:
    python scripts/build_intraday_regime_overlay.py \
        --midprice-dir data/midprice_per_day \
        --npz-dir data/npz_v4 \
        --out-dir data/npz_v4_intraday_regime

Process is sequential across days (cross-day state propagation for 24h / 30d
lookbacks). On jpline ~1-2 hours for 991 days.
"""
from __future__ import annotations
import argparse
import os
import pathlib
import sys
import time
import numpy as np
import pandas as pd

# Allow running from repo root with `python scripts/...`
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.features.intraday_regime_features import (  # noqa: E402
    compute_intraday_regime_features,
    IntradayRegimeState,
    FEAT_NAMES,
)


def _build_full_second_grid(ts_s: np.ndarray, mid_price: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Forward-fill `mid_price` onto contiguous 1-second grid [ts.min(), ts.max()].

    Defensive against unsorted / duplicate timestamps (some midprice NPZ days have
    these). Sorts first, then deduplicates by keeping first-occurrence value.
    """
    if len(ts_s) == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    # Filter NaN/invalid: positive ts + positive finite mid_price
    ts_s = np.asarray(ts_s, dtype=np.int64)
    mid_price = np.asarray(mid_price, dtype=np.float64)
    valid = (ts_s > 0) & np.isfinite(mid_price) & (mid_price > 0)
    if not valid.any():
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    ts_s = ts_s[valid]
    mid_price = mid_price[valid]
    order = np.argsort(ts_s, kind="stable")
    ts_sorted = ts_s[order]
    mid_sorted = mid_price[order]
    # Dedupe: keep first occurrence
    _, uniq_idx = np.unique(ts_sorted, return_index=True)
    ts_clean = ts_sorted[uniq_idx]
    mid_clean = mid_sorted[uniq_idx]
    if len(ts_clean) < 2:
        return ts_clean, mid_clean

    t0, t1 = int(ts_clean[0]), int(ts_clean[-1])
    if t1 < t0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    n = t1 - t0 + 1
    if n <= 0 or n > 5 * 86400:  # sanity: don't allocate >5 days for one "day" file
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    grid_ts = np.arange(t0, t1 + 1, dtype=np.int64)
    grid_mid = np.full(n, np.nan, dtype=np.float64)
    offsets = (ts_clean - t0).astype(np.int64)
    grid_mid[offsets] = mid_clean
    # Forward-fill NaN gaps (carry last known mid forward)
    s = pd.Series(grid_mid)
    s = s.ffill().bfill()  # bfill leading NaN before first known mid
    return grid_ts, s.to_numpy()


def _compute_log_return_1s(mid: np.ndarray) -> np.ndarray:
    """log(mid_t / mid_{t-1}) per 1s tick. First element = 0."""
    out = np.zeros_like(mid)
    valid = (mid[:-1] > 0) & (mid[1:] > 0)
    out[1:][valid] = np.log(mid[1:][valid] / mid[:-1][valid])
    return out


def _align_to_npz_windows(
    npz_path: pathlib.Path,
    ts_full: np.ndarray,
    feat_df: pd.DataFrame,
    feat_cols: list[str],
) -> np.ndarray | None:
    """Map per-1s feature values onto npz_v4 window timestamps.

    npz_v4 has `timestamps: (N,)` = window-end timestamps in MICROSECONDS,
    and X.shape = (N, T, n_features). For each window n with end-ts t_end,
    we need feature values at timesteps [t_end - (T-1)*1e6, ..., t_end] at 1s spacing.

    Returns: tv_feats (N, T, K) float32, or None on error.
    """
    if ts_full.size == 0 or feat_df.shape[0] == 0:
        return None
    try:
        with np.load(npz_path, allow_pickle=True) as z:
            window_ts_us = np.asarray(z["timestamps"], dtype=np.int64)  # (N,) microseconds
            n_windows = window_ts_us.shape[0]
            T = int(z["X"].shape[1])
    except Exception as e:
        print(f"  [align] failed loading {npz_path.name}: {e}")
        return None

    # Convert window end-ts from microseconds to seconds
    window_ts_s = window_ts_us // 1_000_000  # (N,)

    # Build lookup: ts_full[i] = timestamp in seconds, feat_df aligned to ts_full
    # ts_full IS the contiguous 1s grid we computed features on.
    # For each window n, compute T 1s offsets relative to window_end:
    #   sample_ts[t] = window_ts_s[n] - (T - 1 - t)  for t in 0..T-1
    K = len(feat_cols)
    out = np.zeros((n_windows, T, K), dtype=np.float32)
    feat_arr = feat_df[feat_cols].to_numpy().astype(np.float32)  # (len(ts_full), K)

    t0 = int(ts_full[0])
    n_full = len(ts_full)
    for n in range(n_windows):
        t_end = int(window_ts_s[n])
        # Index of t_end in ts_full
        i_end = t_end - t0
        if i_end < 0 or i_end >= n_full:
            # Window timestamp outside the day's mid_price grid; fill with feat at clamp
            i_clamp = max(0, min(i_end, n_full - 1))
            out[n] = feat_arr[i_clamp]
            continue
        # Build per-timestep indices for the T window timesteps
        i_lo = i_end - (T - 1)
        if i_lo >= 0:
            out[n] = feat_arr[i_lo:i_end + 1]
        else:
            # Partial window: pad pre-day samples with first-available value
            n_pad = -i_lo
            out[n, :n_pad] = feat_arr[0]
            out[n, n_pad:] = feat_arr[0:i_end + 1]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--midprice-dir", required=True, help="Directory of per-day {YYYY-MM-DD}.npz with 1s mid_price")
    ap.add_argument("--npz-dir", required=True, help="npz_v4 directory (for window timestamps)")
    ap.add_argument("--out-dir", required=True, help="Output dir for intraday-regime overlay NPZ")
    ap.add_argument("--start-day", default=None, help="YYYY-MM-DD, optional limit")
    ap.add_argument("--end-day", default=None, help="YYYY-MM-DD, optional limit")
    args = ap.parse_args()

    mid_dir = pathlib.Path(args.midprice_dir)
    npz_dir = pathlib.Path(args.npz_dir)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Collect days present in BOTH dirs, sorted chronologically
    mid_days = {p.stem for p in mid_dir.iterdir() if p.suffix == ".npz" and len(p.stem) == 10}
    npz_days = {p.stem for p in npz_dir.iterdir() if p.suffix == ".npz" and len(p.stem) == 10}
    days = sorted(mid_days & npz_days)
    if args.start_day:
        days = [d for d in days if d >= args.start_day]
    if args.end_day:
        days = [d for d in days if d <= args.end_day]
    print(f"[build_intraday] Processing {len(days)} days "
          f"({days[0] if days else 'N/A'} → {days[-1] if days else 'N/A'})")

    state = IntradayRegimeState()
    t_start = time.time()
    for i, day in enumerate(days):
        mid_path = mid_dir / f"{day}.npz"
        npz_path = npz_dir / f"{day}.npz"
        out_path = out_dir / f"{day}.npz"
        if out_path.exists():
            # Skip if already built (idempotent); but state must be re-derived,
            # so we need to recompute features on this day's mid_price anyway.
            # The simple choice: still recompute features to keep state correct,
            # but skip saving.
            skip_save = True
        else:
            skip_save = False

        try:
            with np.load(mid_path, allow_pickle=False) as z:
                ts_s = np.asarray(z["timestamps_s"], dtype=np.int64)
                mid_price_raw = np.asarray(z["mid_price"], dtype=np.float64)
        except Exception as e:
            print(f"  [{day}] mid load fail: {e}; skip")
            continue

        if len(ts_s) < 60:
            print(f"  [{day}] too few mid samples ({len(ts_s)}); skip")
            continue

        # 1s contiguous grid + forward-fill
        ts_full, mid_full = _build_full_second_grid(ts_s, mid_price_raw)
        if ts_full.size == 0:
            print(f"  [{day}] degenerate grid (empty); skip both features + save")
            continue
        log_ret = _compute_log_return_1s(mid_full)

        # Compute features streaming
        feat_df, state = compute_intraday_regime_features(ts_full, mid_full, log_ret, state)

        if skip_save:
            if (i + 1) % 50 == 0 or i == len(days) - 1:
                elapsed = time.time() - t_start
                print(f"  [{day}] state-update only ({i + 1}/{len(days)}, {elapsed:.0f}s)")
            continue

        # Align features to per-window grid
        tv_feats = _align_to_npz_windows(npz_path, ts_full, feat_df, FEAT_NAMES)
        if tv_feats is None:
            print(f"  [{day}] alignment failed; skip save")
            continue

        # Save in TV-overlay-compatible format
        np.savez_compressed(
            out_path,
            tv_feats=tv_feats,
            feat_names=np.array(FEAT_NAMES, dtype="<U24"),
            timestamps_s=ts_full,  # diagnostic only; not used by loader
        )

        if (i + 1) % 50 == 0 or i == len(days) - 1:
            elapsed = time.time() - t_start
            v0_min, v0_max = float(tv_feats[..., 0].min()), float(tv_feats[..., 0].max())
            v3_min, v3_max = float(tv_feats[..., 3].min()), float(tv_feats[..., 3].max())
            print(f"  [{day}] saved ({i + 1}/{len(days)}, {elapsed:.0f}s, "
                  f"shape={tv_feats.shape}, "
                  f"vol_pct ∈ [{v0_min:.3f}, {v0_max:.3f}], "
                  f"dd_24h ∈ [{v3_min:.3f}, {v3_max:.3f}])")

    elapsed = time.time() - t_start
    print(f"[build_intraday] Done in {elapsed:.0f}s. Output: {out_dir}")


if __name__ == "__main__":
    main()

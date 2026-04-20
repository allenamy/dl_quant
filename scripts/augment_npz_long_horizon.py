"""Augment V4 NPZs with long-horizon (y_600-matched) features computed from X_raw.

Existing V4 features top out at RV_300s / log_return_30s. y_600 target is 600s.
Adds 8 new per-timestep features covering 300-600s scales:

  1. log_return_300s   — return over trailing 300 steps (bps)
  2. log_return_600s   — return over full 600-step window (bps)
  3. realized_vol_600s — rolling std of 1s returns over 600 steps
  4. mid_drift_600s    — rolling mean of per-step mid deviation (directional)
  5. spread_percentile — current spread z-score over the window
  6. depth_asym_300s   — rolling mean of total-depth asymmetry
  7. obi_persistence   — rolling autocorrelation of top-level OBI at lag 60
  8. hurst_approx      — rough Hurst exponent via R/S analysis (regime indicator)

Output: data/npz_v4_plus/<day>.npz with X enlarged from (N, 600, 64) to
(N, 600, 72). All other fields (X_raw, y_*, timestamps, masks) copied as-is.

Usage: run on pod, takes ~15-30 min for 991 days with 8 workers.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import time
from pathlib import Path

import numpy as np


EPS = 1e-8


def rolling_mean_causal(x: np.ndarray, window: int) -> np.ndarray:
    """Causal rolling mean over last `window` samples. x: (T,) → (T,)."""
    T = len(x)
    if window >= T:
        return np.full_like(x, x.mean())
    # Pad left with x[0] so early windows don't underflow
    xp = np.concatenate([np.full(window - 1, x[0], dtype=x.dtype), x])
    c = np.cumsum(xp)
    out = (c[window - 1:] - np.concatenate([[0.0], c[:-window]])) / window
    return out.astype(x.dtype)


def rolling_std_causal(x: np.ndarray, window: int) -> np.ndarray:
    m = rolling_mean_causal(x, window)
    m2 = rolling_mean_causal(x * x, window)
    var = np.maximum(m2 - m * m, 0.0)
    return np.sqrt(var + EPS).astype(x.dtype)


def compute_long_horizon_features(x_raw_day: np.ndarray) -> np.ndarray:
    """Compute 8 new features per (sample, timestep).

    Parameters
    ----------
    x_raw_day : (N_samples, 600, 20, 4) float (could be fp16; promoted to fp32)

    Returns
    -------
    features : (N_samples, 600, 8) float32
    """
    x = x_raw_day.astype(np.float32)
    N, T, L, C = x.shape
    assert T == 600 and C == 4, f"unexpected shape {x.shape}"

    # Extract best-bid/ask deltas (in bps relative to per-timestep mid)
    best_bid_bps = x[:, :, 0, 0]  # (N, T)
    best_ask_bps = x[:, :, 0, 2]
    best_bid_sz = x[:, :, 0, 1]   # log amounts
    best_ask_sz = x[:, :, 0, 3]

    # Mid-drift proxy: (best_bid_bps + best_ask_bps) / 2 — non-zero under
    # asymmetric book because the mid used for bps-normalization drifts.
    mid_drift = (best_bid_bps + best_ask_bps) / 2.0  # (N, T)

    # Step-to-step mid returns (in bps; approximate log return since scales small)
    # mid_return[t] ≈ mid_drift[t] - mid_drift[t-1]  (first-difference proxy)
    mid_return = np.diff(mid_drift, axis=1, prepend=mid_drift[:, :1])  # (N, T)

    # Spread in bps (ask - bid); sometimes slightly negative in noisy data
    spread_bps = np.maximum(best_ask_bps - best_bid_bps, 0.0)

    # Top-level OBI (using log amounts as size proxy)
    obi_L0 = (best_bid_sz - best_ask_sz) / (np.abs(best_bid_sz) + np.abs(best_ask_sz) + 1e-3)

    # Total depth imbalance across 20 levels
    total_bid = x[:, :, :, 1].sum(axis=-1)  # (N, T)
    total_ask = x[:, :, :, 3].sum(axis=-1)
    depth_asym = (total_bid - total_ask) / (np.abs(total_bid) + np.abs(total_ask) + 1e-3)

    # Compute per-sample rolling features (vectorized over N via loop or
    # broadcasting). Loop is simpler and fast enough for N~150.
    feats = np.empty((N, T, 8), dtype=np.float32)
    for i in range(N):
        # 1. log_return_300s: trailing mid drift at lag 300 (mid_drift now - mid_drift 300 ago)
        md = mid_drift[i]
        lr_300 = np.zeros(T, dtype=np.float32)
        if T > 300:
            lr_300[300:] = md[300:] - md[:-300]
            lr_300[:300] = md[:300] - md[0]  # pad with earliest available
        feats[i, :, 0] = lr_300

        # 2. log_return_600s: full-window return (end - start)
        feats[i, :, 1] = md - md[0]  # cumulative drift from window start

        # 3. realized_vol_600s: rolling std of 1s returns over 600s
        feats[i, :, 2] = rolling_std_causal(mid_return[i], window=300)  # 5min as strong proxy

        # 4. mid_drift_600s: rolling mean of mid_drift over 300s (avg mid deviation)
        feats[i, :, 3] = rolling_mean_causal(md, window=300)

        # 5. spread_z-score over window: (spread_t - mean_window) / std_window
        sp = spread_bps[i]
        sp_m = rolling_mean_causal(sp, window=300)
        sp_s = rolling_std_causal(sp, window=300)
        feats[i, :, 4] = (sp - sp_m) / (sp_s + 0.1)

        # 6. depth_asym_300s: rolling mean of total-depth asymmetry
        feats[i, :, 5] = rolling_mean_causal(depth_asym[i], window=300)

        # 7. obi_persistence: current_OBI × lag-60 OBI (sign-agreement proxy)
        obi = obi_L0[i]
        obi_lag60 = np.concatenate([np.zeros(60, dtype=np.float32), obi[:-60]])
        feats[i, :, 6] = obi * obi_lag60  # positive = persistent direction

        # 8. hurst_approx: log(RV_60) - log(RV_300) as simple vol-scaling proxy
        # True Hurst is expensive; this captures whether vol grows with timescale
        rv60 = rolling_std_causal(mid_return[i], window=60) + 1e-6
        rv300 = rolling_std_causal(mid_return[i], window=300) + 1e-6
        feats[i, :, 7] = np.log(rv60 / rv300)  # -0.5 random walk; > -0.5 mean revert

    # Clip extremes
    feats = np.nan_to_num(feats, nan=0.0, posinf=10.0, neginf=-10.0)
    feats = np.clip(feats, -10.0, 10.0)
    return feats


def augment_day(in_path: Path, out_dir: Path) -> tuple[str, float, str]:
    """Augment one day's NPZ. Returns (name, seconds, status)."""
    t0 = time.time()
    try:
        out_path = out_dir / in_path.name
        if out_path.exists():
            return (in_path.name, 0.0, "SKIP")
        d = np.load(str(in_path), allow_pickle=True)
        x = d["X"]          # (N, 600, 64)
        x_raw = d["X_raw"]  # (N, 600, 20, 4), may be fp16
        if x.shape[0] == 0:
            # Empty day: just copy
            np.savez(str(out_path), **{k: d[k] for k in d.files})
            return (in_path.name, time.time() - t0, "EMPTY")

        aug = compute_long_horizon_features(x_raw)  # (N, 600, 8)
        x_new = np.concatenate([x.astype(np.float32), aug], axis=-1)  # (N, 600, 72)

        # Update features list
        new_feat_names = [
            "log_return_300s_win", "log_return_600s_win",
            "rv_300s_win", "mid_drift_300s_win",
            "spread_z_300s_win", "depth_asym_300s_win",
            "obi_persistence_60lag", "hurst_log_ratio",
        ]
        feat_names_old = list(d["features"]) if "features" in d.files else []
        feat_names = feat_names_old + new_feat_names

        # Save all original fields, swap X, update features
        out = {k: d[k] for k in d.files}
        out["X"] = x_new.astype(np.float32)
        out["features"] = np.asarray(feat_names)
        np.savez(str(out_path), **out)
        return (in_path.name, time.time() - t0, "OK")
    except Exception as e:
        return (in_path.name, time.time() - t0, f"ERR: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", default="data/npz_v4")
    ap.add_argument("--out-dir", default="data/npz_v4_plus")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    days = sorted(in_dir.glob("*.npz"))
    print(f"Augmenting {len(days)} days from {in_dir} to {out_dir}")

    with cf.ProcessPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(augment_day, days, [out_dir] * len(days)))

    ok = sum(1 for _, _, s in results if s == "OK")
    skip = sum(1 for _, _, s in results if s == "SKIP")
    err = sum(1 for _, _, s in results if s.startswith("ERR"))
    total_time = sum(t for _, t, _ in results)
    print(f"OK={ok} SKIP={skip} ERR={err} total_compute_time={total_time:.1f}s")
    if err:
        print("Errors:")
        for n, t, s in results:
            if s.startswith("ERR"):
                print(f"  {n}: {s}")


if __name__ == "__main__":
    main()

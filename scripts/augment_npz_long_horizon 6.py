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


def compute_long_horizon_features(x_raw_day: np.ndarray, x_day: np.ndarray, lr_idx: int) -> np.ndarray:
    """Compute 8 new features per (sample, timestep).

    NOTE: mid-prices drift across timesteps but x_raw's best-bid/ask are bps
    relative to each step's own mid (so bid_bps + ask_bps ≡ 0 structurally).
    Actual price drift isn't recoverable from x_raw alone. We use X's existing
    `log_return_1s` column for return-based features and x_raw for book-shape
    features.

    Parameters
    ----------
    x_raw_day : (N_samples, 600, 20, 4) float
    x_day     : (N_samples, 600, 64) float — existing V4 feature tensor
    lr_idx    : int — column index of `log_return_1s` in x_day

    Returns
    -------
    features : (N_samples, 600, 8) float32
    """
    x_raw = x_raw_day.astype(np.float32)
    x = x_day.astype(np.float32)
    N, T, L, C = x_raw.shape
    assert T == 600 and C == 4, f"unexpected shape {x_raw.shape}"

    # Get log_return_1s series from X (it's already z-normalized if normalize=True,
    # but NPZ stores unnormalized — we're running pre-normalize)
    lr1 = x[:, :, lr_idx]  # (N, T) log returns at 1s

    # Features from x_raw (book shape)
    best_bid_bps = x_raw[:, :, 0, 0]
    best_ask_bps = x_raw[:, :, 0, 2]
    best_bid_sz = x_raw[:, :, 0, 1]
    best_ask_sz = x_raw[:, :, 0, 3]
    spread_bps = np.maximum(best_ask_bps - best_bid_bps, 0.0)
    obi_L0 = (best_bid_sz - best_ask_sz) / (np.abs(best_bid_sz) + np.abs(best_ask_sz) + 1e-3)
    total_bid = x_raw[:, :, :, 1].sum(axis=-1)
    total_ask = x_raw[:, :, :, 3].sum(axis=-1)
    depth_asym = (total_bid - total_ask) / (np.abs(total_bid) + np.abs(total_ask) + 1e-3)

    feats = np.empty((N, T, 8), dtype=np.float32)
    for i in range(N):
        r = lr1[i]  # 1s log returns (T,)

        # 1. log_return_300s = sum of last 300 log_return_1s
        cum = np.cumsum(r)
        lr_300 = np.zeros(T, dtype=np.float32)
        lr_300[300:] = (cum[300:] - cum[:-300]).astype(np.float32)
        lr_300[:300] = cum[:300].astype(np.float32)
        feats[i, :, 0] = lr_300

        # 2. log_return_600s = full window cumsum (cum itself)
        feats[i, :, 1] = cum.astype(np.float32)

        # 3. realized_vol_600s: rolling std of 1s log returns (300s window used,
        #    since full-600 window would need padding all the way)
        feats[i, :, 2] = rolling_std_causal(r, window=300)

        # 4. mid_mean_reversion_300s: -cumsum/300 (if price moved up, this expects reversion)
        #    i.e., z-score of cumulative move relative to rolling vol
        rv = rolling_std_causal(r, window=60) + 1e-6
        # Sum over trailing 300 normalized by vol
        feats[i, :, 3] = lr_300 / (rv * np.sqrt(300.0))

        # 5. spread_z-score over window
        sp = spread_bps[i]
        sp_m = rolling_mean_causal(sp, window=300)
        sp_s = rolling_std_causal(sp, window=300)
        feats[i, :, 4] = (sp - sp_m) / (sp_s + 0.1)

        # 6. depth_asym_300s: rolling mean of depth asymmetry
        feats[i, :, 5] = rolling_mean_causal(depth_asym[i], window=300)

        # 7. obi_persistence: current OBI × lag-60 OBI
        obi = obi_L0[i]
        obi_lag60 = np.concatenate([np.zeros(60, dtype=np.float32), obi[:-60]])
        feats[i, :, 6] = obi * obi_lag60

        # 8. hurst_approx: log(RV_60 / RV_300) — vol scaling indicator
        rv60 = rolling_std_causal(r, window=60) + 1e-6
        rv300 = rolling_std_causal(r, window=300) + 1e-6
        feats[i, :, 7] = np.log(rv60 / rv300)

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

        feat_names_old = list(d["features"]) if "features" in d.files else []
        try:
            lr_idx = feat_names_old.index("log_return_1s")
        except ValueError:
            return (in_path.name, time.time() - t0, "ERR: no log_return_1s column")
        aug = compute_long_horizon_features(x_raw, x, lr_idx)  # (N, 600, 8)
        x_new = np.concatenate([x.astype(np.float32), aug], axis=-1)  # (N, 600, 72)

        # Update features list
        new_feat_names = [
            "log_return_300s_win", "log_return_600s_win",
            "rv_300s_win", "mean_rev_z_300s",
            "spread_z_300s_win", "depth_asym_300s_win",
            "obi_persistence_60lag", "hurst_log_ratio",
        ]
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

"""V5-LH NPZ pipeline — stitches V4 windows into 1800-step LH windows.

V4 NPZ structure (from data/npz_v4/*.npz):
  X: (N, 600, F) — 600 one-second timesteps per window
  X_raw: (N, 600, 20, 4) — raw LOB (fp16)
  Windows have stride=60 seconds; V4 window i covers absolute seconds
  [i*60, i*60 + 600).

V5-LH target: 1800-step input at 1-second resolution (30 minutes of history),
ending at the same anchor timestep as a V4 window.

Key observation: V4 windows at indices [anchor - 20, anchor - 10, anchor] are
exactly NON-OVERLAPPING in absolute time (600-sec stride in index-10 units)
and together cover absolute seconds [anchor*60 - 1200, anchor*60 + 600) =
1800 consecutive seconds ending at V4[anchor]'s end. Concatenating these three
V4 windows gives the full 1800 one-second samples with zero gaps, zero overlap,
and no uninitialized memory.

Lookahead safety:
  - LH input end = last timestep of V4[anchor] = second (anchor*60 + 599)
  - LH target y_h = V4's y_h[anchor] = return from (anchor*60 + 600) onward
  - Target is strictly FUTURE of input's last step — no leakage.

Numerical: X_raw is fp16 on disk; kept as fp16 in output to save memory.
"""
import pathlib
from typing import List, Optional

import numpy as np

# V4 window constants
V4_WINDOW_SEC = 600     # each V4 window = 600 one-second timesteps
V4_STRIDE_SEC = 60      # V4 windows stride by 60 seconds
STEP_BACK = V4_WINDOW_SEC // V4_STRIDE_SEC  # = 10 V4 indices for non-overlapping hop


def build_lh_npz_from_v4(
    src_path: pathlib.Path,
    dst_path: pathlib.Path,
    input_len: int = 1800,
    kept_feature_indices: Optional[List[int]] = None,
) -> None:
    """Produce V5-LH NPZ from a single V4 NPZ day.

    Parameters
    ----------
    src_path : path to V4 NPZ for one day.
    dst_path : path where LH NPZ will be written.
    input_len : LH input length in seconds. Must be a multiple of V4_WINDOW_SEC
                (600) so it divides evenly into N non-overlapping V4 windows.
    kept_feature_indices : which V4 feature columns to carry over (output from
                the redundancy filter). If None, keep all.
    """
    assert input_len % V4_WINDOW_SEC == 0, (
        f"input_len must be a multiple of V4 window size ({V4_WINDOW_SEC}); "
        f"got {input_len}"
    )
    n_v4_windows_per_lh = input_len // V4_WINDOW_SEC  # e.g. 1800/600 = 3

    src = np.load(str(src_path), allow_pickle=True)
    X_v4 = src["X"]                   # (N, 600, F)
    X_raw_v4 = src["X_raw"]           # (N, 600, levels, 4), fp16
    features_v4 = src["features"]
    regime_prior = src["regime_prior"]
    timestamps = src["timestamps"]

    N = X_v4.shape[0]
    # First viable anchor has (n_v4_windows_per_lh - 1) * STEP_BACK windows of
    # prior context behind it. For 1800-step LH with STEP_BACK=10: start = 20.
    start = (n_v4_windows_per_lh - 1) * STEP_BACK

    if kept_feature_indices is None:
        kept_feature_indices = list(range(X_v4.shape[2]))
    F_kept = len(kept_feature_indices)
    kept_idx_arr = np.asarray(kept_feature_indices, dtype=np.int64)
    levels = X_raw_v4.shape[2]

    # Copy target keys that exist in source (preserve dtype)
    target_keys = [k for k in ("y_60", "y_mask_60", "y_180", "y_mask_180",
                               "y_300", "y_mask_300", "y_600", "y_mask_600")
                   if k in src.files]

    if N <= start:
        # Not enough V4 windows to form even one LH window → write an empty NPZ.
        empty = {
            "X": np.zeros((0, input_len, F_kept), dtype=np.float32),
            "X_raw": np.zeros((0, input_len, levels, 4), dtype=X_raw_v4.dtype),
            "features": np.array([features_v4[i] for i in kept_feature_indices], dtype=object),
            "regime_prior": np.zeros((0, regime_prior.shape[1]), dtype=np.float32),
            "timestamps": np.zeros((0,), dtype=np.int64),
        }
        for k in target_keys:
            empty[k] = np.zeros((0,), dtype=src[k].dtype)
        if "horizons_sec" in src.files:
            empty["horizons_sec"] = src["horizons_sec"]
        np.savez(str(dst_path), **empty)
        return

    M = N - start  # number of LH windows produced
    X_lh = np.empty((M, input_len, F_kept), dtype=np.float32)
    X_raw_lh = np.empty((M, input_len, levels, 4), dtype=X_raw_v4.dtype)

    for lh_idx in range(M):
        anchor = lh_idx + start
        # Stitch n_v4_windows_per_lh non-overlapping V4 windows end-to-end:
        # indices [anchor - (n-1)*STEP_BACK, ..., anchor - STEP_BACK, anchor].
        for w in range(n_v4_windows_per_lh):
            v4_idx = anchor - (n_v4_windows_per_lh - 1 - w) * STEP_BACK
            seg = slice(w * V4_WINDOW_SEC, (w + 1) * V4_WINDOW_SEC)
            # Safe indexing: basic slice first, then advanced column select
            # X_v4[v4_idx] shape: (600, F); [:, kept_idx_arr] → (600, F_kept)
            X_lh[lh_idx, seg, :] = X_v4[v4_idx][:, kept_idx_arr]
            X_raw_lh[lh_idx, seg, :, :] = X_raw_v4[v4_idx, :, :, :]

    out_kwargs = {
        "X": X_lh,
        "X_raw": X_raw_lh,
        "features": np.array([features_v4[i] for i in kept_feature_indices], dtype=object),
        "regime_prior": regime_prior[start:].astype(np.float32),
        "timestamps": timestamps[start:].astype(np.int64),
    }
    for k in target_keys:
        out_kwargs[k] = src[k][start:].astype(src[k].dtype)
    if "horizons_sec" in src.files:
        out_kwargs["horizons_sec"] = src["horizons_sec"]

    np.savez(str(dst_path), **out_kwargs)

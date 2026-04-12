"""CSV-to-NPZ pipeline: build sliding-window datasets from raw LOB CSVs.

Functions
---------
build_npz_for_day
    Convert a single day of 1-second LOB bars into sliding-window arrays.
process_csv_to_npz
    End-to-end: CSV -> resample -> split by day -> per-day NPZ files.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.microstructure import compute_microstructure_features
from src.features.resample import resample_lob_to_1s


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_npz_for_day(
    df_1s: pd.DataFrame,
    *,
    horizon_sec: int = 180,
    input_len: int = 300,
    stride: int = 60,
    n_levels: int = 25,
    feature_clip: float = 10.0,
) -> dict:
    """Build sliding-window arrays for a single day of 1-second LOB bars.

    Parameters
    ----------
    df_1s : pd.DataFrame
        1-second LOB bars (output of ``resample_lob_to_1s``).
    horizon_sec : int
        Prediction horizon in seconds for the label (fractional return).
    input_len : int
        Number of 1-second rows per input window.
    stride : int
        Step size between consecutive windows.
    n_levels : int
        Number of LOB levels passed to ``compute_microstructure_features``.
    feature_clip : float
        Clip feature values to [-feature_clip, +feature_clip] after nan_to_num.

    Returns
    -------
    dict with keys:
        X          – float32, shape (N_win, input_len, n_features)
        y          – float32, shape (N_win,)
        y_mask     – uint8,   shape (N_win,)  (1 if label is valid, 0 otherwise)
        timestamps – int64,   shape (N_win,)  (timestamp at pred_idx)
        features   – list[str]                (feature column names)
    """

    # --- compute microstructure features ------------------------------------
    feat_df = compute_microstructure_features(df_1s, n_levels=n_levels)

    # Separate mid_price (used for labels) and feature columns
    feature_cols = [c for c in feat_df.columns if c not in ("timestamp", "mid_price")]
    mid_prices = feat_df["mid_price"].values.astype(np.float64)
    timestamps_all = feat_df["timestamp"].values.astype(np.int64)

    feat_matrix = feat_df[feature_cols].values.astype(np.float32)

    # Clean: nan_to_num then clip
    feat_matrix = np.nan_to_num(feat_matrix, nan=0.0, posinf=0.0, neginf=0.0)
    feat_matrix = np.clip(feat_matrix, -feature_clip, feature_clip)

    n_total = len(feat_matrix)

    # --- build sliding windows ----------------------------------------------
    starts = list(range(0, n_total - input_len + 1, stride))

    X_list = []
    y_list = []
    mask_list = []
    ts_list = []

    for start in starts:
        X_win = feat_matrix[start : start + input_len]  # (input_len, n_features)

        pred_idx = start + input_len - 1
        target_idx = pred_idx + horizon_sec

        if target_idx < n_total:
            y_val = mid_prices[target_idx] / mid_prices[pred_idx] - 1.0
            mask_val = 1
        else:
            y_val = 0.0
            mask_val = 0

        X_list.append(X_win)
        y_list.append(y_val)
        mask_list.append(mask_val)
        ts_list.append(timestamps_all[pred_idx])

    X = np.array(X_list, dtype=np.float32)       # (N_win, input_len, n_features)
    y = np.array(y_list, dtype=np.float32)        # (N_win,)
    y_mask = np.array(mask_list, dtype=np.uint8)  # (N_win,)
    timestamps = np.array(ts_list, dtype=np.int64)  # (N_win,)

    return {
        "X": X,
        "y": y,
        "y_mask": y_mask,
        "timestamps": timestamps,
        "features": feature_cols,
    }


# ---------------------------------------------------------------------------
# End-to-end CSV -> NPZ
# ---------------------------------------------------------------------------

def process_csv_to_npz(
    csv_path: str | Path,
    output_dir: str | Path,
    *,
    horizon_sec: int = 180,
    input_len: int = 300,
    stride: int = 60,
    n_levels: int = 25,
) -> list[Path]:
    """Load a raw LOB CSV, resample to 1s, split by UTC day, and save NPZ files.

    Parameters
    ----------
    csv_path : str | Path
        Path to the raw LOB CSV (may be gzip-compressed with .gz extension).
    output_dir : str | Path
        Directory where per-day NPZ files will be written.
    horizon_sec, input_len, stride, n_levels
        Forwarded to ``build_npz_for_day``.

    Returns
    -------
    list[Path]
        Paths of the NPZ files written.
    """

    csv_path = Path(csv_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- load CSV -----------------------------------------------------------
    if csv_path.suffix == ".gz" or csv_path.name.endswith(".csv.gz"):
        raw = pd.read_csv(csv_path, compression="gzip")
    else:
        raw = pd.read_csv(csv_path)

    # --- resample to 1s -----------------------------------------------------
    df_1s = resample_lob_to_1s(raw, n_levels=n_levels)

    # --- split by UTC day ---------------------------------------------------
    us_per_day = 86_400 * 1_000_000
    day_ids = df_1s["timestamp"].values // us_per_day

    saved_paths: list[Path] = []

    for day_id in np.unique(day_ids):
        day_mask = day_ids == day_id
        df_day = df_1s.loc[day_mask].reset_index(drop=True)

        if len(df_day) < input_len:
            continue  # skip short days

        result = build_npz_for_day(
            df_day,
            horizon_sec=horizon_sec,
            input_len=input_len,
            stride=stride,
            n_levels=n_levels,
        )

        # Derive YYYY-MM-DD from the day_id (days since epoch)
        date_str = pd.Timestamp(day_id * us_per_day, unit="us", tz="UTC").strftime("%Y-%m-%d")
        out_path = output_dir / f"{date_str}.npz"

        np.savez(
            out_path,
            X=result["X"],
            y=result["y"],
            y_mask=result["y_mask"],
            timestamps=result["timestamps"],
            features=np.array(result["features"], dtype=object),
        )
        saved_paths.append(out_path)

    return saved_paths


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert LOB CSV to per-day NPZ files")
    parser.add_argument("csv", help="Path to raw LOB CSV")
    parser.add_argument("--output-dir", default="data/npz", help="Output directory")
    parser.add_argument("--horizon", type=int, default=180)
    parser.add_argument("--input-len", type=int, default=300)
    parser.add_argument("--stride", type=int, default=60)
    parser.add_argument("--n-levels", type=int, default=25)
    args = parser.parse_args()

    paths = process_csv_to_npz(
        args.csv,
        args.output_dir,
        horizon_sec=args.horizon,
        input_len=args.input_len,
        stride=args.stride,
        n_levels=args.n_levels,
    )
    for p in paths:
        d = np.load(p, allow_pickle=True)
        print(f"  {p.name}: X={d['X'].shape}  y={d['y'].shape}  mask_sum={d['y_mask'].sum()}")
    print("Done.")

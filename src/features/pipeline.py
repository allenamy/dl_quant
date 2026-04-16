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

from src.features.derived_features import (
    DERIVED_FEATURE_NAMES,
    compute_derived_features,
)
from src.features.microstructure import compute_microstructure_features
from src.features.raw_lob import extract_raw_lob_tensor
from src.features.resample import resample_lob_to_1s
from src.features.trade_features import (
    TRADE_FEATURE_NAMES,
    aggregate_trades_to_1s,
    compute_trade_flow_features,
)


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_npz_for_day(
    df_1s: pd.DataFrame,
    *,
    trades_df: pd.DataFrame | None = None,
    horizons_sec: list[int] | None = None,
    horizon_sec: int = 180,
    input_len: int = 300,
    stride: int = 60,
    n_levels: int = 25,
    feature_clip: float = 1000.0,
    include_ridge_features: bool = False,
    include_regime_prior: bool = False,
) -> dict:
    """Build sliding-window arrays for a single day of 1-second LOB bars.

    Parameters
    ----------
    df_1s : pd.DataFrame
        1-second LOB bars (output of ``resample_lob_to_1s``).
    trades_df : pd.DataFrame, optional
        Raw trade ticks for the same day.  If provided, 9 trade-flow
        features and 6 derived features are computed and appended to the
        feature matrix (total 43 + 9 + 6 = 58 features).  If None, only
        the 43 microstructure features plus 6 LOB-only derived features
        are used (the trade-dependent derived columns become zero in that
        case — total 43 + 6 = 49 features).
    horizons_sec : list[int] | None
        List of prediction horizons in seconds; one label column per
        horizon is produced.  When ``None`` (default) falls back to
        ``[horizon_sec]`` (single-horizon behaviour, preserved for
        back-compat).
    horizon_sec : int
        Prediction horizon in seconds for the label (fractional return).
        Used only when ``horizons_sec`` is ``None``.
    input_len : int
        Number of 1-second rows per input window.
    stride : int
        Step size between consecutive windows.
    n_levels : int
        Number of LOB levels passed to ``compute_microstructure_features``.
    feature_clip : float
        Clip feature values to [-feature_clip, +feature_clip] after nan_to_num.
    include_ridge_features : bool
        When True, append 6 ridge-informed interaction features (Task 1) to the
        feature matrix (58 base → 64 cols). Default False keeps V3 behaviour.
    include_regime_prior : bool
        When True, compute hourly-scale regime-prior features and return them
        as a separate ``regime_prior`` array of shape (N_win, 6) sliced at
        each window's pred_idx. Default False; no overhead when disabled.

    Returns
    -------
    dict with keys:
        X            – float32, shape (N_win, input_len, n_features)
        X_raw        – float32, shape (N_win, input_len, raw_levels, 4)
        timestamps   – int64,   shape (N_win,)  (timestamp at pred_idx)
        features     – list[str]                (feature column names)
        horizons_sec – list[int]                (the horizons actually built)
        y_{H}        – float32, shape (N_win,) for each H in horizons_sec
        y_mask_{H}   – uint8,   shape (N_win,) (1 if label valid, else 0)
        y, y_mask    – aliases pointing to the smallest horizon (back-compat)
        regime_prior – float32, shape (N_win, 6) — only present when
                       ``include_regime_prior=True``
    """

    # --- resolve horizon list -----------------------------------------------
    # Multi-horizon is an additive feature: when ``horizons_sec`` is None we
    # fall back to ``[horizon_sec]`` so every legacy caller is unaffected.
    if horizons_sec is None:
        horizons_sec_list = [int(horizon_sec)]
    else:
        if len(horizons_sec) == 0:
            raise ValueError("horizons_sec must be a non-empty list")
        horizons_sec_list = [int(h) for h in horizons_sec]
        if any(h <= 0 for h in horizons_sec_list):
            raise ValueError(
                f"horizons_sec must contain positive integers, got {horizons_sec_list}"
            )
    # Deduplicate while preserving order; guard against caller passing
    # [60, 60, 180] which would otherwise produce duplicate keys.
    seen: set[int] = set()
    deduped: list[int] = []
    for h in horizons_sec_list:
        if h not in seen:
            seen.add(h)
            deduped.append(h)
    horizons_sec_list = deduped

    max_horizon = max(horizons_sec_list)
    min_horizon = min(horizons_sec_list)

    # --- validate windowing config -----------------------------------------
    # stride < max(horizons) causes label overlap for the longest horizon:
    # adjacent labels share (H - stride) seconds of forward return, inflating
    # sample count and biasing residual autocorrelation. Backtest P&L is also
    # incorrectly accumulated in this case.
    if stride < max_horizon:
        import warnings
        warnings.warn(
            f"stride ({stride}) < max(horizons_sec) ({max_horizon}): labels will "
            f"overlap by {max_horizon - stride}s at the longest horizon, "
            f"inflating metrics and breaking backtest.",
            stacklevel=2,
        )

    # --- compute microstructure features ------------------------------------
    feat_df = compute_microstructure_features(df_1s, n_levels=n_levels)

    # Separate mid_price (used for labels) and feature columns
    feature_cols = [c for c in feat_df.columns if c not in ("timestamp", "mid_price")]
    mid_prices = feat_df["mid_price"].values.astype(np.float64)
    timestamps_all = feat_df["timestamp"].values.astype(np.int64)

    feat_matrix = feat_df[feature_cols].values.astype(np.float32)

    # Per-level bid/ask arrays — reused by derived features below
    bid_prices_arr = np.column_stack(
        [df_1s[f"bids[{i}].price"].values for i in range(n_levels)]
    )
    ask_prices_arr = np.column_stack(
        [df_1s[f"asks[{i}].price"].values for i in range(n_levels)]
    )
    bid_amounts_arr = np.column_stack(
        [df_1s[f"bids[{i}].amount"].values for i in range(n_levels)]
    )
    ask_amounts_arr = np.column_stack(
        [df_1s[f"asks[{i}].amount"].values for i in range(n_levels)]
    )
    log_returns_1s_arr = feat_df["log_return_1s"].values.astype(np.float64)

    # --- optionally add trade features --------------------------------------
    buy_volume_1s: np.ndarray | None = None
    sell_volume_1s: np.ndarray | None = None
    if trades_df is not None and len(trades_df) > 0:
        # Aggregate trade ticks to 1s bars aligned to the depth grid.
        # Pass mid_prices_1s so no-trade seconds get a sensible vwap (mid)
        # instead of 0 -- important for downstream vwap_return_1s to not
        # report a -100% return for silent seconds.
        start_ts = int(timestamps_all[0])
        end_ts = int(timestamps_all[-1])
        trade_bars = aggregate_trades_to_1s(
            trades_df,
            start_ts_us=start_ts,
            end_ts_us=end_ts,
            mid_prices_1s=mid_prices,
        )
        trade_feat_df = compute_trade_flow_features(
            trade_bars, mid_prices=mid_prices
        )
        trade_cols = [c for c in trade_feat_df.columns if c != "timestamp"]
        trade_matrix = trade_feat_df[trade_cols].values.astype(np.float32)

        # Verify alignment: trade bars must match depth bar count.
        # A mismatch is always a bug in aggregate_trades_to_1s / the caller —
        # loop silently concatenating 49 vs 58 features per day will fail at
        # LOBDatasetV2 load time with a cryptic concat error.  Fail fast here.
        if trade_matrix.shape[0] != feat_matrix.shape[0]:
            raise ValueError(
                f"trade_matrix rows ({trade_matrix.shape[0]}) != feat_matrix "
                f"rows ({feat_matrix.shape[0]}); aggregate_trades_to_1s must "
                f"return a bar count matching the 1s depth grid."
            )
        feat_matrix = np.concatenate([feat_matrix, trade_matrix], axis=1)
        feature_cols = feature_cols + trade_cols
        # Extract buy/sell volumes for derived features.
        buy_volume_1s = trade_feat_df["buy_volume_1s"].values.astype(
            np.float64
        )
        sell_volume_1s = trade_feat_df["sell_volume_1s"].values.astype(
            np.float64
        )

    # --- derived features (always computed; trade-dependent cols default 0) --
    derived_df = compute_derived_features(
        bid_prices=bid_prices_arr,
        ask_prices=ask_prices_arr,
        bid_amounts=bid_amounts_arr,
        ask_amounts=ask_amounts_arr,
        mid=mid_prices,
        log_returns_1s=log_returns_1s_arr,
        buy_volume_1s=buy_volume_1s,
        sell_volume_1s=sell_volume_1s,
    )
    derived_cols = list(derived_df.columns)
    derived_matrix = derived_df.values.astype(np.float32)
    if derived_matrix.shape[0] != feat_matrix.shape[0]:
        raise ValueError(
            f"derived_matrix rows ({derived_matrix.shape[0]}) != feat_matrix "
            f"rows ({feat_matrix.shape[0]}); compute_derived_features must "
            f"return one row per 1s depth bar."
        )
    feat_matrix = np.concatenate([feat_matrix, derived_matrix], axis=1)
    feature_cols = feature_cols + derived_cols

    # --- optional ridge-informed features ---------------------------------
    if include_ridge_features:
        from src.features.ridge_informed_features import (
            compute_ridge_informed_features,
            RIDGE_INFORMED_FEATURE_NAMES,
        )
        from src.features.trade_features import TRADE_FEATURE_NAMES as _TRADE_FEATURE_NAMES

        # When trades_df was not provided, the 9 trade columns are absent.
        # Inject them as zero columns so the feature matrix always has the full
        # 58-column base (43 micro + 9 trade + 6 derived) before ridge features
        # are appended — this keeps the final column count at 64 regardless of
        # whether actual trade data is available.
        for _tc in _TRADE_FEATURE_NAMES:
            if _tc not in feature_cols:
                feat_matrix = np.concatenate(
                    [feat_matrix, np.zeros((len(feat_matrix), 1), dtype=np.float32)],
                    axis=1,
                )
                feature_cols = feature_cols + [_tc]

        def _col(name: str) -> np.ndarray:
            if name not in feature_cols:
                return np.zeros(len(feat_matrix), dtype=np.float64)
            idx = feature_cols.index(name)
            return feat_matrix[:, idx].astype(np.float64)

        rf_df = pd.DataFrame({
            "timestamp": timestamps_all,
            "net_trade_flow_1s": _col("net_trade_flow_1s"),
            "spread_bps": _col("spread_bps"),
            "realized_vol_30s": _col("realized_vol_30s"),
            "obi_L5": _col("obi_L5"),
            "book_pressure_imbalance": _col("book_pressure_imbalance"),
        })
        ridge_df = compute_ridge_informed_features(rf_df)
        ridge_cols = list(RIDGE_INFORMED_FEATURE_NAMES)
        ridge_matrix = ridge_df[ridge_cols].to_numpy().astype(np.float32)
        if ridge_matrix.shape[0] != feat_matrix.shape[0]:
            raise ValueError(
                f"ridge features rows ({ridge_matrix.shape[0]}) != "
                f"feat_matrix rows ({feat_matrix.shape[0]})"
            )
        feat_matrix = np.concatenate([feat_matrix, ridge_matrix], axis=1)
        feature_cols = feature_cols + ridge_cols

    # Clean: nan_to_num then clip (covers all columns including ridge if added)
    feat_matrix = np.nan_to_num(feat_matrix, nan=0.0, posinf=0.0, neginf=0.0)
    feat_matrix = np.clip(feat_matrix, -feature_clip, feature_clip)

    # --- optional regime-prior matrix -------------------------------------
    regime_prior_matrix: np.ndarray | None = None
    if include_regime_prior:
        from src.features.regime_prior_features import (
            compute_regime_prior_features,
            REGIME_PRIOR_FEATURE_NAMES,
        )

        def _col_rp(name: str) -> np.ndarray:
            if name not in feature_cols:
                return np.zeros(len(feat_matrix), dtype=np.float64)
            idx = feature_cols.index(name)
            return feat_matrix[:, idx].astype(np.float64)

        rp_df = pd.DataFrame({
            "timestamp": timestamps_all,
            "mid_price": mid_prices,
            "log_return_1s": log_returns_1s_arr,
            "obi_L5": _col_rp("obi_L5"),
            "spread_bps": _col_rp("spread_bps"),
        })
        rp_out = compute_regime_prior_features(rp_df)
        regime_prior_matrix = rp_out[list(REGIME_PRIOR_FEATURE_NAMES)].to_numpy().astype(np.float32)
        regime_prior_matrix = np.nan_to_num(regime_prior_matrix, nan=0.0, posinf=0.0, neginf=0.0)

    # --- extract raw LOB tensor (Path B) ------------------------------------
    raw_levels = min(n_levels, 20)  # cap at 20 for Binance compatibility
    raw_tensor = extract_raw_lob_tensor(df_1s, n_levels=raw_levels)
    # raw_tensor: (n_total, raw_levels, 4)

    n_total = len(feat_matrix)

    # --- build sliding windows ----------------------------------------------
    starts = list(range(0, n_total - input_len + 1, stride))

    X_list = []
    X_raw_list = []
    # Per-horizon label + mask buckets keyed by horizon (seconds).
    y_lists: dict[int, list[float]] = {h: [] for h in horizons_sec_list}
    mask_lists: dict[int, list[int]] = {h: [] for h in horizons_sec_list}
    ts_list = []
    regime_list: list[np.ndarray] = []

    for start in starts:
        X_win = feat_matrix[start : start + input_len]      # (input_len, n_features)
        X_raw_win = raw_tensor[start : start + input_len]    # (input_len, raw_levels, 4)

        pred_idx = start + input_len - 1
        mid_ref = mid_prices[pred_idx]

        X_list.append(X_win)
        X_raw_list.append(X_raw_win)
        ts_list.append(timestamps_all[pred_idx])
        if regime_prior_matrix is not None:
            regime_list.append(regime_prior_matrix[pred_idx])

        for h in horizons_sec_list:
            target_idx = pred_idx + h
            if target_idx < n_total and mid_ref > 0:
                y_val = float(np.log(mid_prices[target_idx] / mid_ref))
                mask_val = 1
            else:
                y_val = 0.0
                mask_val = 0
            y_lists[h].append(y_val)
            mask_lists[h].append(mask_val)

    X = np.array(X_list, dtype=np.float32)           # (N_win, input_len, n_features)
    X_raw = np.array(X_raw_list, dtype=np.float32)   # (N_win, input_len, raw_levels, 4)
    timestamps = np.array(ts_list, dtype=np.int64)    # (N_win,)

    # Per-horizon arrays keyed as y_{H} / y_mask_{H}.
    ys_by_h: dict[int, np.ndarray] = {
        h: np.array(y_lists[h], dtype=np.float32) for h in horizons_sec_list
    }
    masks_by_h: dict[int, np.ndarray] = {
        h: np.array(mask_lists[h], dtype=np.uint8) for h in horizons_sec_list
    }

    out: dict[str, object] = {
        "X": X,
        "X_raw": X_raw,
        "timestamps": timestamps,
        "features": feature_cols,
        "horizons_sec": list(horizons_sec_list),
    }
    for h in horizons_sec_list:
        out[f"y_{h}"] = ys_by_h[h]
        out[f"y_mask_{h}"] = masks_by_h[h]

    # Back-compat aliases: ``y`` / ``y_mask`` point to the smallest-horizon
    # label column so every legacy consumer (LOBDataset, LOBDatasetV2, old
    # tests, run_pipeline_v3) keeps working without code changes.  The smallest
    # horizon is the natural default because it is the closest to the original
    # single-horizon value and has the most valid labels near the end of day.
    out["y"] = ys_by_h[min_horizon]
    out["y_mask"] = masks_by_h[min_horizon]

    if regime_prior_matrix is not None:
        out["regime_prior"] = np.asarray(regime_list, dtype=np.float32)

    return out


# ---------------------------------------------------------------------------
# End-to-end CSV -> NPZ
# ---------------------------------------------------------------------------

def process_csv_to_npz(
    csv_path: str | Path,
    output_dir: str | Path,
    *,
    horizons_sec: list[int] | None = None,
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
    horizons_sec : list[int] | None
        Optional multi-horizon list; forwarded to ``build_npz_for_day``.
        When ``None`` we run in single-horizon mode using ``horizon_sec``
        (back-compat).
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
            horizons_sec=horizons_sec,
            horizon_sec=horizon_sec,
            input_len=input_len,
            stride=stride,
            n_levels=n_levels,
        )

        # Derive YYYY-MM-DD from the day_id (days since epoch)
        date_str = pd.Timestamp(day_id * us_per_day, unit="us", tz="UTC").strftime("%Y-%m-%d")
        out_path = output_dir / f"{date_str}.npz"

        _save_result_npz(out_path, result)
        saved_paths.append(out_path)

    return saved_paths


def _save_result_npz(out_path: Path, result: dict) -> None:
    """Save a ``build_npz_for_day`` result dict to a compressed NPZ.

    Centralised so the per-day writer here and in ``multi_day_pipeline`` agree
    on the field encoding (features as object array, horizons_sec as int
    array, everything else as-is).  Using ``**kwargs`` expansion means every
    ``y_{H}`` / ``y_mask_{H}`` key is forwarded automatically -- no caller
    needs to know about multi-horizon specifics.
    """
    save_kwargs: dict[str, np.ndarray] = {}
    for key, val in result.items():
        if key == "features":
            save_kwargs[key] = np.array(val, dtype=object)
        elif key == "horizons_sec":
            save_kwargs[key] = np.array(val, dtype=np.int64)
        elif isinstance(val, np.ndarray):
            save_kwargs[key] = val
        else:
            # Scalars / lists -- np.savez_compressed coerces them, but we're
            # defensive: every known producer key is already an ndarray or
            # list/str handled above.  For anything else, wrap in array.
            save_kwargs[key] = np.asarray(val)
    np.savez_compressed(out_path, **save_kwargs)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert LOB CSV to per-day NPZ files")
    parser.add_argument("csv", help="Path to raw LOB CSV")
    parser.add_argument("--output-dir", default="data/npz", help="Output directory")
    parser.add_argument("--horizon", type=int, default=180)
    parser.add_argument(
        "--horizons",
        type=str,
        default=None,
        help="Comma-separated list of horizons in seconds (e.g. '60,180,300,600'). "
             "Overrides --horizon when supplied.",
    )
    parser.add_argument("--input-len", type=int, default=300)
    parser.add_argument("--stride", type=int, default=60)
    parser.add_argument("--n-levels", type=int, default=25)
    args = parser.parse_args()

    horizons_sec: list[int] | None = None
    if args.horizons is not None:
        horizons_sec = [int(h) for h in args.horizons.split(",") if h.strip()]

    paths = process_csv_to_npz(
        args.csv,
        args.output_dir,
        horizons_sec=horizons_sec,
        horizon_sec=args.horizon,
        input_len=args.input_len,
        stride=args.stride,
        n_levels=args.n_levels,
    )
    for p in paths:
        d = np.load(p, allow_pickle=True)
        print(f"  {p.name}: X={d['X'].shape}  y={d['y'].shape}  mask_sum={d['y_mask'].sum()}")
    print("Done.")

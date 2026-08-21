"""Windowed-NPZ builder for the multi-asset FAIR dual-path DL experiment.

Goal — produce per-day NPZ files in the **exact format the proven single-asset
REG_arch trainer consumes** (`src/training/dataset.py::LOBDatasetV2`), but built
from OUR bar-data feature/raw-LOB builders. This lets us train the proven
REG_arch on bar data and get an apples-to-apples BTC number.

Output NPZ keys (per day), matching single-asset `build_npz_for_day`:

    X            float32  (N_win, 600, 47)        hand-crafted features (Path A)
    X_raw        float16  (N_win, 600, 5, 4)      raw-LOB tensor (Path B)
    timestamps   int64    (N_win,)                ns timestamp at each pred-idx
    features     <U..     (47,)                   feature names (object/str array)
    horizons_sec int64    (1,)                    == [600]
    y_600        float32  (N_win,)                forward 600s log-return at pred-idx
    y_mask_600   uint8    (N_win,)                1 if label valid, else 0
    y            float32  (N_win,)                back-compat alias of y_600
    y_mask       uint8    (N_win,)                back-compat alias of y_mask_600
    regime_prior float32  (N_win, 6)              hourly-scale regime context

Windowing convention (identical to single-asset pipeline):
    starts   = range(0, n_total - input_len + 1, stride)
    pred_idx = start + input_len - 1
    window   = bars [pred_idx-599, pred_idx]  (inclusive)  -> X/X_raw lookback
    y_600    = log(mid[pred_idx+600] / mid[pred_idx])       -> strictly forward
    timestamp at the window = ts[pred_idx]
    stride   = 180 (>= horizon? no — 180 < 600, but this matches the proven
               single-asset y_600 build which also used stride 180; eval
               subsamples to stride >= horizon for honest IID clean numbers).

DTYPE choices mirror single-asset `quantize_features=True`:
    - X kept float32 (some features ~1e-6 fall in fp16 denormals — see
      single-asset pipeline note). X_raw -> float16 (values in [0, ~6], safe).
    The trainer upcasts X_raw to float32 on read, so the model sees fp32.

DIVERGENCES from single-asset (documented, by bar-data spec):
    - n_features = 47 (our `features_ma`) vs single-asset 64. EXPECTED — this is
      the whole point: same FORMAT, our features. The trainer reads n_features
      from the array shape, so 47 is fine.
    - n_levels = 5 (bar schema has 5 LOB levels) vs single-asset up-to-20.
    - `timestamps` are int64 NANOSECONDS (bar `time64` grid) vs single-asset
      MICROSECONDS. The REG_arch winner config does NOT use time2vec (which is
      the only consumer that interprets ts units), so this is inert for the
      fair-comparison run. If a future config enables time2vec, divide by 1e9
      not 1e6. Documented here so it is not a silent trap.
    - regime_prior reuses the single-asset module
      (`src/features/regime_prior_features.py::compute_regime_prior_features`)
      verbatim — see `_build_regime_prior` for the bar-input adapter. Its 6 dims
      and strict causality are unchanged; we only feed it bar-derived columns.

I/O discipline:
    - Each share day is read ONCE via `bar_loader.load_day_panel` (slow MooseFS
      mount). All four builders consume that single in-memory panel.
    - Output is written to SERVER-LOCAL `multi_asset/exports/windowed_npz/<sym>/`
      (NOT the read-only share, NOT synced back to local — see sync_to_server.sh
      which excludes multi_asset/exports/).
"""
from __future__ import annotations

import argparse
import os
from typing import List, Optional, Tuple

import numpy as np

from multi_asset.data.bar_loader import load_day_panel
from multi_asset.data.features_ma import (
    HORIZON,
    build_features,
    compute_y600,
    valid_mask,
)
from multi_asset.data.raw_lob_ma import N_LEVELS, build_raw_lob_tensor

INPUT_LEN = 600
STRIDE = 180
DEFAULT_OUT_ROOT = "multi_asset/exports/windowed_npz"

# Single-asset regime-prior module — reused verbatim for an apples-to-apples
# 6-dim regime context. See module docstring + `_build_regime_prior`.
from src.features.regime_prior_features import (  # noqa: E402
    REGIME_PRIOR_FEATURE_NAMES,
    compute_regime_prior_features,
)

_NS_PER_US = 1_000


# ---------------------------------------------------------------------------
# regime_prior (reuse single-asset module on bar-derived columns)
# ---------------------------------------------------------------------------

def _build_regime_prior(panel, sym: str, feat_names: List[str],
                        feat_matrix: np.ndarray) -> np.ndarray:
    """(T, 6) regime-prior matrix via the single-asset module, fed bar columns.

    The single-asset `compute_regime_prior_features` needs a DataFrame with:
        timestamp (microseconds), mid_price, log_return_1s, obi_L5, spread_bps.

    We source these strictly causally from the bar panel + our feature matrix:
        - mid_price    : raw `mid` column (used only for the 6h backward log-ret)
        - log_return_1s: raw 1s log-return of mid (NOT bps; the module takes std)
        - obi_L5       : the `obi_L5` feature (already computed, causal)
        - spread_bps   : the `spread_bps` feature (already computed, causal)
        - timestamp    : panel ts (ns) -> us, so hour-of-day sin/cos land right.

    Every operation inside the module is a trailing rolling window or a backward
    shift, so the result is strictly causal (row t uses only bars <= t). Output
    columns are exactly REGIME_PRIOR_FEATURE_NAMES, order preserved.
    """
    import pandas as pd

    mid = panel.data[sym][:, panel.cols.index("mid")].astype(np.float64)
    ts_us = (panel.ts.astype(np.int64) // _NS_PER_US)

    # raw 1s log-return of mid (causal; row 0 = 0). NaN mids -> 0 contribution.
    with np.errstate(divide="ignore", invalid="ignore"):
        lm = np.log(mid)
    log_ret_1s = np.zeros_like(mid)
    log_ret_1s[1:] = lm[1:] - lm[:-1]
    log_ret_1s = np.nan_to_num(log_ret_1s, nan=0.0, posinf=0.0, neginf=0.0)

    obi_l5 = feat_matrix[:, feat_names.index("obi_L5")].astype(np.float64)
    spread = feat_matrix[:, feat_names.index("spread_bps")].astype(np.float64)
    # mid_price must be positive for the 6h log-return guard; sanitize NaNs to a
    # neutral 1.0 (the module already guards mid<=0 -> log-ret 0 there).
    mid_safe = np.where(np.isfinite(mid) & (mid > 0), mid, 1.0)

    df = pd.DataFrame({
        "timestamp": ts_us,
        "mid_price": mid_safe,
        "log_return_1s": log_ret_1s,
        "obi_L5": np.nan_to_num(obi_l5, nan=0.0, posinf=0.0, neginf=0.0),
        "spread_bps": np.nan_to_num(spread, nan=0.0, posinf=0.0, neginf=0.0),
    })
    rp = compute_regime_prior_features(df)
    M = rp[list(REGIME_PRIOR_FEATURE_NAMES)].to_numpy().astype(np.float32)
    return np.nan_to_num(M, nan=0.0, posinf=0.0, neginf=0.0)


# ---------------------------------------------------------------------------
# Per-day windowed NPZ
# ---------------------------------------------------------------------------

def build_day_npz(
    panel,
    sym: str,
    *,
    input_len: int = INPUT_LEN,
    stride: int = STRIDE,
    horizon: int = HORIZON,
    quantize: bool = True,
) -> dict:
    """Build the single-asset-format NPZ payload for one (loaded) day panel.

    Reads NOTHING from disk — operates on the already-loaded `panel` so the
    share day is read exactly once (by the caller). Returns a dict of arrays
    ready for `np.savez`. Windows with an invalid/out-of-range label, a
    non-tradeable pred-index bar, or insufficient forward history are kept with
    y_mask_600=0 (single-asset parity: masked, not dropped, so window indexing
    stays aligned with timestamps) EXCEPT windows whose pred-index bar itself is
    non-finite, which are masked the same way.
    """
    feat_matrix, feat_names = build_features(panel, sym)   # (T, 47) f32
    raw_tensor = build_raw_lob_tensor(panel, sym)          # (T, 5, 4) f32
    y_full = compute_y600(panel, sym)                      # (T,) f64, NaN tail
    vmask = valid_mask(panel, sym)                         # (T,) bool
    regime_prior = _build_regime_prior(panel, sym, feat_names, feat_matrix)

    n_total = feat_matrix.shape[0]
    starts = list(range(0, n_total - input_len + 1, stride))

    X_list: List[np.ndarray] = []
    Xraw_list: List[np.ndarray] = []
    ts_list: List[int] = []
    rp_list: List[np.ndarray] = []
    y_list: List[float] = []
    m_list: List[int] = []

    for start in starts:
        pred_idx = start + input_len - 1
        target_idx = pred_idx + horizon

        X_list.append(feat_matrix[start:start + input_len])          # (L, 47)
        Xraw_list.append(raw_tensor[start:start + input_len])        # (L, 5, 4)
        ts_list.append(int(panel.ts[pred_idx]))
        rp_list.append(regime_prior[pred_idx])

        # Label validity: forward window in-range AND label finite AND the
        # pred-index bar is a tradeable (valid) bar. Otherwise mask out.
        if (
            target_idx < n_total
            and bool(vmask[pred_idx])
            and np.isfinite(y_full[pred_idx])
        ):
            y_val = float(y_full[pred_idx])
            mask_val = 1
        else:
            y_val = 0.0
            mask_val = 0
        y_list.append(y_val)
        m_list.append(mask_val)

    X = np.asarray(X_list, dtype=np.float32)                  # (N, L, 47)
    X_raw = np.asarray(Xraw_list, dtype=np.float32)           # (N, L, 5, 4)
    timestamps = np.asarray(ts_list, dtype=np.int64)          # (N,)  ns
    regime_arr = np.asarray(rp_list, dtype=np.float32)        # (N, 6)
    y_600 = np.asarray(y_list, dtype=np.float32)              # (N,)
    y_mask_600 = np.asarray(m_list, dtype=np.uint8)           # (N,)

    # Sanitize X/X_raw NaNs the same way the trainer would (it nan_to_num's on
    # read). We keep X_raw NaNs-as-zero here for clean storage; warmup rows that
    # land inside a window are zeroed.
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    X_raw = np.nan_to_num(X_raw, nan=0.0, posinf=0.0, neginf=0.0)
    if quantize:
        X_raw = X_raw.astype(np.float16)   # single-asset parity (values in [0,~6])

    out: dict = {
        "X": X,
        "X_raw": X_raw,
        "timestamps": timestamps,
        "features": np.asarray(feat_names),
        "horizons_sec": np.asarray([horizon], dtype=np.int64),
        "y_600": y_600,
        "y_mask_600": y_mask_600,
        # back-compat aliases (single-asset alias points at the only horizon)
        "y": y_600,
        "y_mask": y_mask_600,
        "regime_prior": regime_arr,
    }
    return out


def build_and_save_day(
    date: int,
    sym: str,
    out_root: str = DEFAULT_OUT_ROOT,
    *,
    input_len: int = INPUT_LEN,
    stride: int = STRIDE,
    horizon: int = HORIZON,
    quantize: bool = True,
    overwrite: bool = False,
) -> Optional[str]:
    """Load one share day ONCE, build the windowed NPZ, write it server-local.

    Returns the output path (or None if skipped because it already exists and
    `overwrite=False`). Output: `<out_root>/<sym>/<YYYYMMDD>.npz`.
    """
    out_dir = os.path.join(out_root, sym)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{date}.npz")
    if os.path.exists(out_path) and not overwrite:
        return None

    panel = load_day_panel(date, [sym])  # single read of the share day
    payload = build_day_npz(
        panel, sym, input_len=input_len, stride=stride,
        horizon=horizon, quantize=quantize,
    )
    # Write to a temp path then atomic-rename so a crash never leaves a partial.
    tmp_path = out_path + ".tmp"
    np.savez(tmp_path, **payload)
    # np.savez appends .npz to the given name — account for that.
    written = tmp_path if os.path.exists(tmp_path) else tmp_path + ".npz"
    os.replace(written, out_path)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _date_range(start: int, end: int) -> List[int]:
    """Inclusive YYYYMMDD range via real calendar dates (no missing-file check;
    `build_and_save_day` raises if a day's HDF5 is absent — caller decides
    whether to skip)."""
    from datetime import datetime, timedelta
    d0 = datetime.strptime(str(start), "%Y%m%d")
    d1 = datetime.strptime(str(end), "%Y%m%d")
    out: List[int] = []
    d = d0
    while d <= d1:
        out.append(int(d.strftime("%Y%m%d")))
        d += timedelta(days=1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sym", default="bnfbtc", help="symbol (default bnfbtc)")
    ap.add_argument("--start", type=int, required=True, help="start YYYYMMDD")
    ap.add_argument("--end", type=int, required=True, help="end YYYYMMDD (incl)")
    ap.add_argument("--out-root", default=DEFAULT_OUT_ROOT)
    ap.add_argument("--input-len", type=int, default=INPUT_LEN)
    ap.add_argument("--stride", type=int, default=STRIDE)
    ap.add_argument("--horizon", type=int, default=HORIZON)
    ap.add_argument("--no-quantize", action="store_true",
                    help="store X_raw as float32 instead of float16")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--skip-missing", action="store_true",
                    help="skip days whose HDF5 file is absent instead of erroring")
    args = ap.parse_args()

    dates = _date_range(args.start, args.end)
    print(f"[build_windowed_npz] sym={args.sym} {len(dates)} day(s) "
          f"{args.start}..{args.end} -> {args.out_root}/{args.sym}/")
    n_ok = 0
    for date in dates:
        try:
            path = build_and_save_day(
                date, args.sym, args.out_root,
                input_len=args.input_len, stride=args.stride,
                horizon=args.horizon, quantize=not args.no_quantize,
                overwrite=args.overwrite,
            )
        except FileNotFoundError:
            if args.skip_missing:
                print(f"  {date}: MISSING (skipped)")
                continue
            raise
        if path is None:
            print(f"  {date}: exists (skipped)")
            continue
        with np.load(path, allow_pickle=True) as d:
            n_win = int(d["X"].shape[0])
            n_valid = int(d["y_mask_600"].sum())
        print(f"  {date}: N_win={n_win} valid={n_valid} -> {path}")
        n_ok += 1
    print(f"[build_windowed_npz] done: {n_ok}/{len(dates)} written")


if __name__ == "__main__":
    main()

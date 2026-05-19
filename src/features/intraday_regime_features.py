"""Intraday regime overlay features — per-timestep regime context.

v5push Track v7 (2026-05-15): adds 4 features at 1-second tick resolution that
encode "where is the current tick in long-horizon distributions". Orthogonal
to existing alpha-bearing flow features (TV overlay) and instantaneous
microstructure (X 64 base) — these encode REGIME ROUTING info, not alpha.

Features:
  - vol_1h_pct_30d_t:        rolling 1h vol's percentile in trailing 30d distribution ∈ [0, 1]
  - KER_1h_t:                Kaufman Efficiency Ratio over 1h ∈ [0, 1]
  - ret_autocorr_lag10_1h_t: rolling 1h autocorr of log_return_1s at lag 10 ∈ [-1, 1]
  - dd_24h_t:                drawdown from 24h-trailing max of mid_price ∈ [-1, 0]

All strictly causal — use only data at times ≤ t.

Cross-day state propagation: caller passes `hist_state` from previous-day call
to enable 24h / 30d lookbacks at day boundaries.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


FEAT_NAMES: list[str] = [
    "vol_1h_pct_30d",
    "KER_1h",
    "ret_autocorr_lag10_1h",
    "dd_24h",
]

_WINDOW_1H = 3600          # 1 hour in seconds
_WINDOW_24H = 86400        # 24 hours in seconds
_WINDOW_30D = 30 * 86400   # 30 days in seconds
_AUTOCORR_LAG = 10
_VOL_SUBSAMPLE = 60        # subsample 1h-vol at 60s grid for 30d-percentile (speed)


@dataclass
class IntradayRegimeState:
    """Cross-day state for streaming intraday regime computation.

    Keeps the tail of:
    - log_return_1s history (for rolling 1h vol / autocorr / KER / dd)
    - mid_price history (for dd_24h rolling max)
    - subsampled vol_1h history (for 30d-percentile rolling rank)

    Held back > max lookback (30d) to ensure full window availability when new
    day starts. After processing each day, caller updates state via append +
    truncate-to-window.
    """
    # 1s tick tails (length up to _WINDOW_24H, capped to avoid bloat)
    log_ret_tail: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float64))
    mid_price_tail: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float64))
    ts_tail: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    # Subsampled 1h-vol series for 30d percentile (60s grid → 43200 points per 30d)
    vol_1h_series: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float64))
    vol_1h_series_ts: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int64))


def _rolling_std(arr: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """Causal rolling std (population), pandas-backed for stability."""
    s = pd.Series(arr)
    return s.rolling(window=window, min_periods=min_periods).std(ddof=0).to_numpy()


def _rolling_max(arr: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """Causal rolling max."""
    s = pd.Series(arr)
    return s.rolling(window=window, min_periods=min_periods).max().to_numpy()


def _rolling_sum_abs(arr: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """Causal rolling sum of |arr|."""
    s = pd.Series(np.abs(arr))
    return s.rolling(window=window, min_periods=min_periods).sum().to_numpy()


def _net_change_1h(log_ret: np.ndarray, window: int) -> np.ndarray:
    """Causal rolling sum (= log(mid_t / mid_{t-window})) of log_return_1s."""
    s = pd.Series(log_ret)
    return s.rolling(window=window, min_periods=2).sum().to_numpy()


def _rolling_autocorr_lag(arr: np.ndarray, window: int, lag: int, min_periods: int) -> np.ndarray:
    """Causal rolling autocorr at fixed lag, using product trick.

    autocorr_lag = E[r_t · r_{t-lag}] / Var(r) — over trailing window of length `window`.
    Approximation: divides by per-window E[r²] - (E[r])² (population variance).
    """
    s = pd.Series(arr)
    s_lag = s.shift(lag)
    prod = s * s_lag
    # E[r·r_{lag}] = rolling mean of product (using min_periods to require coverage)
    e_prod = prod.rolling(window=window, min_periods=min_periods).mean().to_numpy()
    e_x = s.rolling(window=window, min_periods=min_periods).mean().to_numpy()
    e_xx = (s * s).rolling(window=window, min_periods=min_periods).mean().to_numpy()
    var = e_xx - e_x * e_x
    out = np.where(var > 1e-18, e_prod / var, 0.0)
    return np.clip(out, -1.0, 1.0)


def compute_intraday_regime_features(
    ts_s: np.ndarray,
    mid_price: np.ndarray,
    log_return_1s: np.ndarray,
    state: Optional[IntradayRegimeState] = None,
) -> tuple[pd.DataFrame, IntradayRegimeState]:
    """Compute 4 intraday regime features at 1s tick resolution.

    Parameters
    ----------
    ts_s : (N,) int64, unix seconds, monotone-increasing
    mid_price : (N,) float, 1s mid_price
    log_return_1s : (N,) float, derived from mid_price (log_ret_1s_i = log(mid_i / mid_{i-1}))
    state : optional cross-day state (last 24h log_ret + 30d vol_1h subsampled). If None,
        start cold (early values are neutral fillers).

    Returns
    -------
    df : DataFrame with columns [timestamp_s, vol_1h_pct_30d, KER_1h, ret_autocorr_lag10_1h, dd_24h]
    new_state : IntradayRegimeState for chaining into next day
    """
    if state is None:
        state = IntradayRegimeState()

    n = len(ts_s)
    if n == 0:
        return pd.DataFrame(columns=["timestamp_s"] + FEAT_NAMES), state

    # ---- 1. Concatenate prev-day tail with current-day data for rolling ----
    log_ret_full = np.concatenate([state.log_ret_tail, log_return_1s])
    mid_full = np.concatenate([state.mid_price_tail, mid_price])
    ts_full = np.concatenate([state.ts_tail, ts_s])
    n_prefix = len(state.log_ret_tail)

    # ---- 2. Rolling 1h vol on log_ret (over 1s ticks) ----
    vol_1h_full = _rolling_std(log_ret_full, window=_WINDOW_1H, min_periods=600)
    vol_1h_full = np.nan_to_num(vol_1h_full, nan=0.0)

    # ---- 3. 30d percentile of vol_1h — subsample at 60s grid for speed ----
    # Sub-grid index: pick every 60th element from ts_full
    sub_idx = np.arange(0, len(vol_1h_full), _VOL_SUBSAMPLE)
    sub_vol = vol_1h_full[sub_idx]
    sub_ts = ts_full[sub_idx]
    # Combine with any historical sub-series carried in state
    if len(state.vol_1h_series) > 0:
        full_sub_vol = np.concatenate([state.vol_1h_series, sub_vol])
        full_sub_ts = np.concatenate([state.vol_1h_series_ts, sub_ts])
    else:
        full_sub_vol = sub_vol
        full_sub_ts = sub_ts
    # Rolling 30d percentile rank on subsampled series.
    # Window in subsample-units: 30d × 86400s / 60s = 43200
    sub_window = (_WINDOW_30D // _VOL_SUBSAMPLE)
    sub_min_periods = max(60, sub_window // 10)  # need at least ~10% of 30d to compute pct
    sub_series = pd.Series(full_sub_vol)
    sub_pct = sub_series.rolling(window=sub_window, min_periods=sub_min_periods).rank(pct=True)
    sub_pct = sub_pct.fillna(0.5).to_numpy()  # neutral 0.5 when insufficient history

    # Map subsampled percentile back to per-1s by carry-forward (last valid).
    # For each 1s tick at index i in ts_full, find the largest sub_idx <= i.
    # Since sub_idx is just np.arange(0, ..., 60), we can compute i // 60 directly.
    # But we want to use ONLY the current-and-newly-extended sub_series, indexed
    # into full_sub_pct = [old_sub_pct (for state's sub series) + new_sub_pct].
    # Map back to 1s grid:
    full_sub_n = len(full_sub_vol)
    # Index of each 1s tick into the subsampled grid (carry-forward)
    # tick i (in ts_full coordinate) corresponds to sub_idx_in_combined =
    #   len(state.vol_1h_series) + (i // _VOL_SUBSAMPLE)
    state_sub_offset = len(state.vol_1h_series)
    tick_to_sub_idx = state_sub_offset + (np.arange(len(ts_full)) // _VOL_SUBSAMPLE)
    tick_to_sub_idx = np.clip(tick_to_sub_idx, 0, full_sub_n - 1)
    vol_pct_full = sub_pct[tick_to_sub_idx]

    # ---- 4. KER_1h — Kaufman Efficiency Ratio ----
    # |net change over 1h| / Σ |1s changes over 1h|
    net_change = _net_change_1h(log_ret_full, _WINDOW_1H)  # log(mid_t / mid_{t-1h})
    sum_abs = _rolling_sum_abs(log_ret_full, _WINDOW_1H, min_periods=600)
    abs_net = np.abs(np.nan_to_num(net_change, nan=0.0))
    sum_abs = np.nan_to_num(sum_abs, nan=0.0)
    # Compute safely using np.divide with where mask to silence runtime warnings
    ker_full = np.zeros_like(sum_abs)
    np.divide(abs_net, sum_abs, out=ker_full, where=sum_abs > 1e-12)
    ker_full = np.clip(ker_full, 0.0, 1.0)

    # ---- 5. Rolling 1h autocorr lag-10 on log_return_1s ----
    autocorr_full = _rolling_autocorr_lag(log_ret_full, _WINDOW_1H, _AUTOCORR_LAG, min_periods=600)
    autocorr_full = np.nan_to_num(autocorr_full, nan=0.0)

    # ---- 6. dd_24h — drawdown from 24h trailing max of mid_price ----
    max_24h = _rolling_max(mid_full, _WINDOW_24H, min_periods=600)
    max_24h = np.where(np.isnan(max_24h) | (max_24h <= 0), mid_full, max_24h)
    dd_full = (mid_full - max_24h) / max_24h
    dd_full = np.clip(dd_full, -1.0, 0.0)

    # ---- 7. Slice off the prefix (state tail), return only current-day values ----
    df = pd.DataFrame({
        "timestamp_s": ts_s,
        "vol_1h_pct_30d": vol_pct_full[n_prefix:].astype(np.float32),
        "KER_1h": ker_full[n_prefix:].astype(np.float32),
        "ret_autocorr_lag10_1h": autocorr_full[n_prefix:].astype(np.float32),
        "dd_24h": dd_full[n_prefix:].astype(np.float32),
    })

    # ---- 8. Build new state — keep last 24h of 1s ticks + last 30d of subsampled vol ----
    keep_1s = min(_WINDOW_24H, len(log_ret_full))
    new_state = IntradayRegimeState(
        log_ret_tail=log_ret_full[-keep_1s:].astype(np.float64),
        mid_price_tail=mid_full[-keep_1s:].astype(np.float64),
        ts_tail=ts_full[-keep_1s:].astype(np.int64),
        vol_1h_series=full_sub_vol[-sub_window:].astype(np.float64),
        vol_1h_series_ts=full_sub_ts[-sub_window:].astype(np.int64),
    )
    return df, new_state

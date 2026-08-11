"""Regime prior features for the PPNet gate.

These features operate on HOURLY timescale, not the 5-min input window.
They capture the macro market state that conditions model behavior
differently per regime, following PEPNet (KDD 2023).

All features are strictly causal (backward-looking only).

Features (6 total):
  realized_vol_1h    -- 1-hour realized volatility (std of 1s log returns)
  obi_trend_1h       -- linear regression slope of OBI_L5 over past hour
  hour_sin           -- sin(2*pi * hour_of_day / 24)
  hour_cos           -- cos(2*pi * hour_of_day / 24)
  spread_mean_1h     -- average spread_bps over past hour
  depth_ratio_1h     -- average depth_ratio_L5 over past hour
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


# Number of regime prior features
N_REGIME_PRIORS = 6

# Feature names in canonical order
REGIME_PRIOR_NAMES = [
    "realized_vol_1h",
    "obi_trend_1h",
    "hour_sin",
    "hour_cos",
    "spread_mean_1h",
    "depth_ratio_1h",
]


def compute_regime_priors(
    df_1s: pd.DataFrame,
    current_idx: int,
    lookback: int = 3600,
) -> np.ndarray:
    """Compute regime prior features for a given timestep.

    These features operate on HOURLY timescale, not the 5-min input window.
    They capture the macro market state that conditions model behavior.

    Parameters
    ----------
    df_1s : pd.DataFrame
        1-second LOB bars with columns including:
        ``timestamp``, ``bids[0].price``, ``asks[0].price``,
        and depth/amount columns for at least 5 levels.
    current_idx : int
        Row index in ``df_1s`` for which to compute priors.
        Uses rows ``[max(0, current_idx - lookback + 1) : current_idx + 1]``.
    lookback : int
        Number of past seconds to use (default 3600 = 1 hour).

    Returns
    -------
    np.ndarray
        Shape ``(6,)`` float32 vector of regime prior features.
        Order matches ``REGIME_PRIOR_NAMES``.

    Notes
    -----
    All features are strictly causal: only rows at or before ``current_idx``
    are used. If fewer than ``lookback`` rows are available, the computation
    uses whatever is available (graceful degradation).
    """
    start_idx = max(0, current_idx - lookback + 1)
    window = df_1s.iloc[start_idx:current_idx + 1]
    n = len(window)

    result = np.zeros(N_REGIME_PRIORS, dtype=np.float32)

    # --- 1. Realized volatility (1h) -----------------------------------------
    # std of 1-second log returns over the lookback window
    bid0 = window["bids[0].price"].values.astype(np.float64)
    ask0 = window["asks[0].price"].values.astype(np.float64)
    mid = (bid0 + ask0) / 2.0

    if n >= 2:
        log_mid = np.log(np.maximum(mid, 1e-10))
        log_returns = np.diff(log_mid)
        result[0] = np.std(log_returns).astype(np.float32) if len(log_returns) > 0 else 0.0
    # else: 0.0 (default)

    # --- 2. OBI trend (1h) ---------------------------------------------------
    # Linear regression slope of OBI_L5 over the window.
    # OBI_L5 = (sum_bid_5 - sum_ask_5) / (sum_bid_5 + sum_ask_5)
    bid_amounts = np.column_stack([
        window[f"bids[{i}].amount"].values.astype(np.float64)
        for i in range(min(5, _count_levels(window, "bids")))
    ])
    ask_amounts = np.column_stack([
        window[f"asks[{i}].amount"].values.astype(np.float64)
        for i in range(min(5, _count_levels(window, "asks")))
    ])

    sum_bid = bid_amounts.sum(axis=1)
    sum_ask = ask_amounts.sum(axis=1)
    denom = sum_bid + sum_ask
    with np.errstate(divide="ignore", invalid="ignore"):
        obi = np.where(denom != 0, (sum_bid - sum_ask) / denom, 0.0)

    if n >= 2:
        # Simple linear regression slope: cov(t, obi) / var(t)
        t = np.arange(n, dtype=np.float64)
        t_mean = t.mean()
        obi_mean = obi.mean()
        cov_t_obi = ((t - t_mean) * (obi - obi_mean)).sum()
        var_t = ((t - t_mean) ** 2).sum()
        if var_t > 0:
            result[1] = (cov_t_obi / var_t).astype(np.float32)
    # else: 0.0

    # --- 3 & 4. Hour-of-day encoding -----------------------------------------
    # timestamp is microseconds since epoch
    current_ts = window["timestamp"].iloc[-1]
    # Extract hour of day (UTC)
    seconds_of_day = (current_ts % (86_400 * 1_000_000)) / 1_000_000
    hour_frac = seconds_of_day / 3600.0
    result[2] = np.sin(2.0 * np.pi * hour_frac / 24.0).astype(np.float32)
    result[3] = np.cos(2.0 * np.pi * hour_frac / 24.0).astype(np.float32)

    # --- 5. Average spread (1h) ----------------------------------------------
    spread = ask0 - bid0
    with np.errstate(divide="ignore", invalid="ignore"):
        spread_bps = np.where(mid != 0, (spread / mid) * 10_000.0, 0.0)
    result[4] = np.mean(spread_bps).astype(np.float32)

    # --- 6. Average depth ratio (1h) -----------------------------------------
    depth_sum = sum_bid + sum_ask
    with np.errstate(divide="ignore", invalid="ignore"):
        depth_ratio = np.where(depth_sum != 0, sum_bid / depth_sum, 0.5)
    result[5] = np.mean(depth_ratio).astype(np.float32)

    # Replace any NaN/inf with 0
    result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)

    return result


def compute_regime_priors_batch(
    df_1s: pd.DataFrame,
    indices: np.ndarray,
    lookback: int = 3600,
) -> np.ndarray:
    """Compute regime priors for a batch of timestep indices.

    Parameters
    ----------
    df_1s : pd.DataFrame
        1-second LOB bars (same format as ``compute_regime_priors``).
    indices : np.ndarray
        Array of row indices for which to compute priors.
    lookback : int
        Number of past seconds to use per timestep (default 3600).

    Returns
    -------
    np.ndarray
        Shape ``(len(indices), 6)`` float32.
    """
    result = np.zeros((len(indices), N_REGIME_PRIORS), dtype=np.float32)
    for i, idx in enumerate(indices):
        result[i] = compute_regime_priors(df_1s, int(idx), lookback)
    return result


def compute_regime_priors_from_buffer(
    timestamps: np.ndarray,
    bid0_prices: np.ndarray,
    ask0_prices: np.ndarray,
    bid_amounts_l5: np.ndarray,
    ask_amounts_l5: np.ndarray,
    lookback: int = 3600,
) -> np.ndarray:
    """Compute regime priors from streaming buffer arrays.

    This is the streaming-friendly interface: instead of a DataFrame, it
    accepts pre-extracted numpy arrays from the StreamingFeatureComputer's
    internal buffer.

    Parameters
    ----------
    timestamps : np.ndarray
        Shape ``(N,)`` int64 microsecond timestamps (most recent last).
    bid0_prices : np.ndarray
        Shape ``(N,)`` best bid prices.
    ask0_prices : np.ndarray
        Shape ``(N,)`` best ask prices.
    bid_amounts_l5 : np.ndarray
        Shape ``(N, 5)`` bid amounts for levels 0-4.
    ask_amounts_l5 : np.ndarray
        Shape ``(N, 5)`` ask amounts for levels 0-4.
    lookback : int
        Number of rows to look back from the end (default 3600).

    Returns
    -------
    np.ndarray
        Shape ``(6,)`` float32 regime prior vector.
    """
    n_total = len(timestamps)
    start = max(0, n_total - lookback)

    ts_w = timestamps[start:]
    bid0_w = bid0_prices[start:].astype(np.float64)
    ask0_w = ask0_prices[start:].astype(np.float64)
    bid_amt_w = bid_amounts_l5[start:].astype(np.float64)
    ask_amt_w = ask_amounts_l5[start:].astype(np.float64)

    n = len(ts_w)
    result = np.zeros(N_REGIME_PRIORS, dtype=np.float32)

    mid = (bid0_w + ask0_w) / 2.0

    # 1. Realized vol
    if n >= 2:
        log_mid = np.log(np.maximum(mid, 1e-10))
        log_returns = np.diff(log_mid)
        result[0] = np.std(log_returns).astype(np.float32)

    # 2. OBI trend
    sum_bid = bid_amt_w.sum(axis=1)
    sum_ask = ask_amt_w.sum(axis=1)
    denom = sum_bid + sum_ask
    with np.errstate(divide="ignore", invalid="ignore"):
        obi = np.where(denom != 0, (sum_bid - sum_ask) / denom, 0.0)

    if n >= 2:
        t = np.arange(n, dtype=np.float64)
        t_mean = t.mean()
        obi_mean = obi.mean()
        cov_t_obi = ((t - t_mean) * (obi - obi_mean)).sum()
        var_t = ((t - t_mean) ** 2).sum()
        if var_t > 0:
            result[1] = (cov_t_obi / var_t).astype(np.float32)

    # 3 & 4. Hour-of-day
    current_ts = ts_w[-1]
    seconds_of_day = (current_ts % (86_400 * 1_000_000)) / 1_000_000
    hour_frac = seconds_of_day / 3600.0
    result[2] = np.sin(2.0 * np.pi * hour_frac / 24.0).astype(np.float32)
    result[3] = np.cos(2.0 * np.pi * hour_frac / 24.0).astype(np.float32)

    # 5. Average spread
    spread = ask0_w - bid0_w
    with np.errstate(divide="ignore", invalid="ignore"):
        spread_bps = np.where(mid != 0, (spread / mid) * 10_000.0, 0.0)
    result[4] = np.mean(spread_bps).astype(np.float32)

    # 6. Average depth ratio
    depth_sum = sum_bid + sum_ask
    with np.errstate(divide="ignore", invalid="ignore"):
        depth_ratio = np.where(depth_sum != 0, sum_bid / depth_sum, 0.5)
    result[5] = np.mean(depth_ratio).astype(np.float32)

    result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)
    return result


def _count_levels(df: pd.DataFrame, side: str) -> int:
    """Count how many orderbook levels are present for a given side."""
    count = 0
    while f"{side}[{count}].price" in df.columns:
        count += 1
    return count

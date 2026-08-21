"""Microprice trajectory features — per-timestep dynamics of size-weighted price.

v5push Track v8 (2026-05-15): adds 4 features at 1-second tick resolution
encoding the TRAJECTORY (not snapshot) of microprice deviation from mid.
Orthogonal to existing X 64 base / TV 14 alpha-flow / regime_prior 6 context.

Classical microprice (Stoll 2000 / Cartea 2015):
    microprice = (bid_size·ask_price + ask_size·bid_price) / (bid_size + ask_size)

Size-weight: more bid liquidity → microprice closer to ask (upward bias).
Microprice persistently above mid → institutional buy pressure → predicts ↑.

Derivation from existing X_raw[..., level=0, :] = [bid_Δbps, bid_log_amt, ask_Δbps, ask_log_amt]:
    bid_size = exp(bid_log_amt) - 1
    ask_size = exp(ask_log_amt) - 1
    micro_dev_bps = (bid_size·ask_Δbps − ask_size·bid_Δbps) / (bid_size + ask_size)
        ∈ ℝ, sign(micro_dev) > 0 ⇒ buy pressure, < 0 ⇒ sell pressure.

4 trajectory features (60s rolling within each 600s input window):
    micro_dev_ema_60s_t        — EWMA (HL=60s) of micro_dev_bps → smooth state
    micro_dev_slope_60s_t      — rolling 60s linear slope → trend direction
    micro_dev_persistence_60s_t — rolling 60s mean(sign(micro_dev)) ∈ [-1,1]
    micro_dev_amplitude_60s_t  — rolling 60s (max − min) → trend strength

Causality: 60s lookback is strictly within each 600s window (t≥60 has full
window, t<60 uses min_periods=10). NO cross-window state. NO future use.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd


FEAT_NAMES: list[str] = [
    "micro_dev_ema_60s",
    "micro_dev_slope_60s",
    "micro_dev_persistence_60s",
    "micro_dev_amplitude_60s",
]

_W_60S = 60
_MIN_PERIODS = 10
_EPS = 1e-9


def _micro_dev_bps_from_xraw(x_raw_lvl0: np.ndarray) -> np.ndarray:
    """Compute microprice deviation from mid in bps using level-0 X_raw.

    x_raw_lvl0: (N, T, 4) = [bid_Δbps, bid_log_amt, ask_Δbps, ask_log_amt]
    Where bid_Δbps < 0 (bid below mid), ask_Δbps > 0 (ask above mid).

    Microprice (Cartea 2015): size-weighted with OPPOSITE side's price:
        micro = (bid_size · ask_price + ask_size · bid_price) / (bid_size + ask_size)
        micro - mid = (bid_size · ask_Δbps + ask_size · bid_Δbps) / (bid_size + ask_size)

    Sign semantics:
      bid_size > ask_size (buy demand)  → dominate positive ask_Δbps  → micro > mid → +
      ask_size > bid_size (sell supply) → dominate negative bid_Δbps  → micro < mid → −
    """
    bid_dbps = x_raw_lvl0[..., 0].astype(np.float32)
    bid_log_amt = x_raw_lvl0[..., 1].astype(np.float32)
    ask_dbps = x_raw_lvl0[..., 2].astype(np.float32)
    ask_log_amt = x_raw_lvl0[..., 3].astype(np.float32)
    bid_amt = np.expm1(bid_log_amt).astype(np.float32)
    ask_amt = np.expm1(ask_log_amt).astype(np.float32)
    denom = bid_amt + ask_amt + _EPS
    # NOTE: + (not -) on ask_amt·bid_dbps; bid_dbps already carries negative sign.
    num = bid_amt * ask_dbps + ask_amt * bid_dbps
    return (num / denom).astype(np.float32)


def _rolling_linear_slope_per_row(arr_2d: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """Causal rolling OLS slope per row of arr_2d, vectorized via pandas.

    arr_2d: (N, T)
    Returns: (N, T) slope (in y-units per 1-tick).

    Slope identity (relative index i = 0..m-1 in window):
        slope_m = (m·Σi·y − Σi·Σy) / (m·Σi² − (Σi)²)
    Σi = m(m-1)/2, denom = m²(m²-1)/12.
    Need rolling Σy and Σ(k·y) (k = absolute index).
    """
    N, T = arr_2d.shape
    out = np.zeros((N, T), dtype=np.float32)
    if T == 0:
        return out
    idx = np.arange(T, dtype=np.float64)
    for n in range(N):
        s = pd.Series(arr_2d[n].astype(np.float64))
        m_count = s.rolling(window, min_periods=min_periods).count().to_numpy()
        sum_y = s.rolling(window, min_periods=min_periods).sum().to_numpy()
        sum_ky = pd.Series(idx * arr_2d[n]).rolling(window, min_periods=min_periods).sum().to_numpy()
        offset = idx - m_count + 1.0
        sum_iy = sum_ky - offset * sum_y
        sum_i = m_count * (m_count - 1) / 2.0
        denom = (m_count ** 2) * (m_count ** 2 - 1) / 12.0
        num = m_count * sum_iy - sum_i * sum_y
        slope_row = np.zeros(T, dtype=np.float64)
        valid = (m_count >= min_periods) & (denom > 0) & np.isfinite(denom)
        slope_row[valid] = num[valid] / denom[valid]
        out[n] = slope_row.astype(np.float32)
    return out


def _rolling_persistence_per_row(arr_2d: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """Rolling mean of sign(arr) per row. Output ∈ [-1, 1]."""
    sign_arr = np.sign(arr_2d).astype(np.float32)
    N, T = sign_arr.shape
    out = np.zeros((N, T), dtype=np.float32)
    for n in range(N):
        out[n] = (
            pd.Series(sign_arr[n])
            .rolling(window, min_periods=min_periods)
            .mean()
            .fillna(0.0)
            .to_numpy(dtype=np.float32)
        )
    return out


def _rolling_amplitude_per_row(arr_2d: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """Rolling (max - min) per row."""
    N, T = arr_2d.shape
    out = np.zeros((N, T), dtype=np.float32)
    for n in range(N):
        s = pd.Series(arr_2d[n])
        rmax = s.rolling(window, min_periods=min_periods).max().fillna(0.0).to_numpy()
        rmin = s.rolling(window, min_periods=min_periods).min().fillna(0.0).to_numpy()
        out[n] = (rmax - rmin).astype(np.float32)
    return out


def _ewma_per_row(arr_2d: np.ndarray, halflife: float) -> np.ndarray:
    """Causal EWMA per row, fillna 0."""
    N, T = arr_2d.shape
    out = np.zeros((N, T), dtype=np.float32)
    for n in range(N):
        out[n] = (
            pd.Series(arr_2d[n])
            .ewm(halflife=halflife, adjust=False, min_periods=_MIN_PERIODS)
            .mean()
            .fillna(0.0)
            .to_numpy(dtype=np.float32)
        )
    return out


def compute_microprice_trajectory_features(x_raw: np.ndarray) -> np.ndarray:
    """Compute 4 microprice trajectory features per (sample, timestep).

    Parameters
    ----------
    x_raw : (N, T, n_levels, 4) — raw LOB tensor, level 0 contains
        [bid_Δbps, bid_log_amt, ask_Δbps, ask_log_amt].

    Returns
    -------
    tv_feats : (N, T, 4) float32 — matches TV overlay format.
        Channel order: [ema_60s, slope_60s, persistence_60s, amplitude_60s]
    """
    if x_raw.ndim != 4 or x_raw.shape[-1] != 4:
        raise ValueError(f"x_raw must be (N, T, L, 4), got {x_raw.shape}")
    if x_raw.shape[2] < 1:
        raise ValueError(f"x_raw must have at least 1 level, got {x_raw.shape[2]}")
    N, T, L, _ = x_raw.shape

    # Microprice deviation (bps) per tick — uses level 0 only
    micro_dev = _micro_dev_bps_from_xraw(x_raw[..., 0, :])  # (N, T)
    # Clip extreme outliers (sometimes log_amt computation can blow up)
    micro_dev = np.clip(np.nan_to_num(micro_dev, nan=0.0, posinf=0.0, neginf=0.0), -100.0, 100.0)

    # 4 trajectory features
    ema = _ewma_per_row(micro_dev, halflife=float(_W_60S))
    slope = _rolling_linear_slope_per_row(micro_dev, window=_W_60S, min_periods=_MIN_PERIODS)
    persistence = _rolling_persistence_per_row(micro_dev, window=_W_60S, min_periods=_MIN_PERIODS)
    amplitude = _rolling_amplitude_per_row(micro_dev, window=_W_60S, min_periods=_MIN_PERIODS)

    tv_feats = np.stack([ema, slope, persistence, amplitude], axis=-1).astype(np.float32)
    return tv_feats

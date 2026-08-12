"""σ_local computation for vol-adaptive label normalization.

Both functions are deterministic + look-ahead-free (output[t] uses only [t-window, t-1]).
Designed for offline NPZ overlay build (per Phase 1 of design doc).
"""
from __future__ import annotations

import numpy as np


def compute_sigma_local_mad(returns: np.ndarray, window: int = 720,
                             min_periods: int = 60, mad_scale: float = 1.4826) -> np.ndarray:
    """Rolling MAD-σ over a fixed window of past returns.

    Parameters
    ----------
    returns : 1-d array of mid-price log-returns at 1s resolution (typical)
    window : window length in samples (720 = 12 min at 1s stride; tunable)
    min_periods : minimum samples required to emit a non-NaN sigma
    mad_scale : 1.4826 makes MAD a Gaussian-σ-equivalent estimator

    Returns
    -------
    sigma : 1-d array same length as returns. sigma[t] uses returns[t-window:t]
            (excluding t itself for strict no-look-ahead). NaN for t < min_periods.

    Notes
    -----
    Uses np.median pairs in a sliding window. O(N × window). For N=86400 (1 day at 1s)
    and window=720, ~6e7 ops, runs in a few seconds.
    """
    returns = np.asarray(returns, dtype=np.float64).ravel()
    n = len(returns)
    sigma = np.full(n, np.nan, dtype=np.float64)

    for t in range(min_periods, n):
        lo = max(0, t - window)
        past = returns[lo:t]  # strictly before t; t itself NOT included
        if len(past) < min_periods:
            continue
        med = np.median(past)
        mad = np.median(np.abs(past - med))
        sigma[t] = mad_scale * mad

    return sigma


def compute_sigma_local_ewma(returns: np.ndarray, alpha: float = 0.06,
                              warmup_periods: int = 200) -> np.ndarray:
    """EWMA of squared returns (variance), then sqrt.

    Faster than MAD (O(N)). Smoother but less robust to single-tick spikes.

    Parameters
    ----------
    returns : 1-d array of returns
    alpha : EWMA decay parameter; effective half-life ≈ ln(0.5)/ln(1-α)
            alpha=0.06 → half-life ≈ 11 samples
    warmup_periods : how many samples to mask as NaN at start (insufficient stats)

    Returns
    -------
    sigma : same shape as returns, NaN for first warmup_periods entries.
    """
    returns = np.asarray(returns, dtype=np.float64).ravel()
    n = len(returns)
    if n == 0:
        return np.empty(0)
    var_sq = np.zeros(n, dtype=np.float64)
    var_sq[0] = max(returns[0] * returns[0], 1e-12)
    for t in range(1, n):
        var_sq[t] = (1 - alpha) * var_sq[t - 1] + alpha * returns[t] * returns[t]

    sigma = np.sqrt(var_sq)
    if warmup_periods > 0 and warmup_periods < n:
        sigma[:warmup_periods] = np.nan
    return sigma


def normalize_y_with_sigma_local(y: np.ndarray, sigma_local: np.ndarray,
                                  min_sigma: float = 1e-6) -> np.ndarray:
    """Element-wise y / sigma_local, returning NaN where sigma_local is NaN or below min.

    For training-target normalization. Inference path multiplies back: y_raw = y_z * sigma_local.

    Parameters
    ----------
    y : raw log-returns (target)
    sigma_local : per-timestamp σ_local (same length)
    min_sigma : floor to avoid divide-by-near-zero (ratio explodes)

    Returns
    -------
    y_normed : y / sigma_local where valid; NaN otherwise.
    """
    y = np.asarray(y, dtype=np.float64)
    sigma_local = np.asarray(sigma_local, dtype=np.float64)
    if y.shape != sigma_local.shape:
        raise ValueError(f"shape mismatch: y={y.shape} vs sigma_local={sigma_local.shape}")

    out = np.full_like(y, np.nan)
    valid = np.isfinite(sigma_local) & (sigma_local > min_sigma) & np.isfinite(y)
    out[valid] = y[valid] / sigma_local[valid]
    return out

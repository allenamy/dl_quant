"""Advanced microstructure features derived from depth + trade flow.

All features are **strictly causal**: the value at time *t* depends only on
data at time *t* and earlier.  No future information is used.

These features augment the base 43 microstructure features (from
``microstructure.py``) and 9 trade-flow features (from ``trade_features.py``)
with 6 theoretically justified signals from the LOB literature:

1. ``microprice_dev_bps`` — (microprice - mid) / mid * 10_000.  Stationary
   by construction, positive when the bid queue dominates (Stoikov 2018).
2. ``roll_spread_60s`` — Roll (1984) effective-spread estimator.
3. ``vpin_60s`` — Easley / Lopez de Prado / O'Hara (2012) informed-trading
   proxy over a 60-second window (fixed-time bucket approximation).
4. ``vpin_300s`` — same estimator over a 300-second window.
5. ``book_pressure_imbalance`` — depth-weighted multi-level OBI with
   exponential level decay.
6. ``price_impact_30s`` — proper Kyle's lambda using **trade volume**
   (not LOB depth).  Replaces the buggy ``kyle_lambda_30s`` that lived in
   ``microstructure.py`` and used ``bid_depth_L5`` as a volume proxy.

Every function returns a ``np.ndarray`` of the same length as its inputs.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


_EPS = 1e-12


# ---------------------------------------------------------------------------
# 1. Microprice
# ---------------------------------------------------------------------------

def compute_microprice(
    bids_price: np.ndarray,
    bids_amt: np.ndarray,
    asks_price: np.ndarray,
    asks_amt: np.ndarray,
) -> np.ndarray:
    """Volume-weighted mid price using top-of-book queues (Stoikov 2018).

    ``microprice = (bid_vol * ask_price + ask_vol * bid_price)
                   / (bid_vol + ask_vol)``

    When ``bid_vol >> ask_vol`` the microprice pulls toward the ask (likely
    to trade up).  When the queues are balanced it equals the mid.

    Parameters
    ----------
    bids_price, asks_price : np.ndarray, shape (N,)
        Best bid / ask prices.
    bids_amt, asks_amt : np.ndarray, shape (N,)
        Queued size at the best bid / ask.

    Returns
    -------
    np.ndarray, shape (N,)
        The microprice.  When both queues are empty we fall back to the mid.
    """
    bids_price = np.asarray(bids_price, dtype=np.float64)
    asks_price = np.asarray(asks_price, dtype=np.float64)
    bids_amt = np.asarray(bids_amt, dtype=np.float64)
    asks_amt = np.asarray(asks_amt, dtype=np.float64)

    total = bids_amt + asks_amt
    mid = 0.5 * (bids_price + asks_price)

    # Numerator is the classical Stoikov form: the side with more volume
    # pulls the price toward the *opposite* top-of-book.
    numer = bids_amt * asks_price + asks_amt * bids_price
    with np.errstate(divide="ignore", invalid="ignore"):
        micro = np.where(total > 0, numer / (total + _EPS), mid)
    return micro


def compute_microprice_deviation_bps(
    mid: np.ndarray,
    microprice: np.ndarray,
) -> np.ndarray:
    """``(microprice - mid) / mid * 10_000``.

    Stationary by construction (a ratio of near-equal quantities).
    Positive when the bid queue dominates — interpreted as upward pressure.
    """
    mid = np.asarray(mid, dtype=np.float64)
    microprice = np.asarray(microprice, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(
            mid > 0, (microprice - mid) / (mid + _EPS) * 10_000.0, 0.0
        )
    return out


# ---------------------------------------------------------------------------
# 2. Roll's implied spread
# ---------------------------------------------------------------------------

def compute_roll_spread(
    log_returns: np.ndarray,
    window: int = 60,
) -> np.ndarray:
    """Roll (1984) implied effective-spread estimator.

    ``roll_spread = 2 * sqrt(max(-cov(Δp_t, Δp_{t-1}), 0))``

    We use rolling *window*-second covariance of ``log_returns`` against
    their lag-1 counterpart.  The estimator is only defined when the serial
    covariance is negative; positive values are clipped to 0 per Roll's
    original recommendation.

    Parameters
    ----------
    log_returns : np.ndarray, shape (N,)
        One-step log returns of the mid price (already a "Δp" series).
    window : int
        Rolling window length in samples (default 60 seconds).

    Returns
    -------
    np.ndarray, shape (N,)
        Rolling Roll-spread estimates (in the same units as ``log_returns``).
    """
    r = pd.Series(np.asarray(log_returns, dtype=np.float64))
    r_lag = r.shift(1)

    # Compute rolling covariance of (r_t, r_{t-1}).  ``.cov`` over two
    # Series is strictly backward-looking in pandas.
    roll_cov = r.rolling(window, min_periods=2).cov(r_lag)

    # Roll's measure is only meaningful for negative serial covariance.
    clipped = np.where(roll_cov.values < 0, -roll_cov.values, 0.0)
    spread = 2.0 * np.sqrt(np.maximum(clipped, 0.0))
    return np.nan_to_num(spread, nan=0.0, posinf=0.0, neginf=0.0)


# ---------------------------------------------------------------------------
# 3. VPIN (Easley, Lopez de Prado, O'Hara 2012)
# ---------------------------------------------------------------------------

def compute_vpin(
    buy_volume: np.ndarray,
    sell_volume: np.ndarray,
    window: int = 60,
) -> np.ndarray:
    """Fixed-*time* VPIN approximation over a rolling window.

    ``VPIN_t = sum(|buy_vol - sell_vol|) / sum(buy_vol + sell_vol)`` over the
    trailing ``window`` seconds.

    The original Easley/López de Prado/O'Hara (2012) definition uses
    **volume-synchronized** buckets.  Aligning volume buckets to our 1-second
    grid would break the rest of the pipeline; this time-bucket variant is
    the standard low-frequency approximation and is itself commonly used in
    the literature (see e.g. Abad & Yagüe 2012 on intraday VPIN proxies).

    Parameters
    ----------
    buy_volume, sell_volume : np.ndarray, shape (N,)
        Signed 1-second executed volume.
    window : int
        Rolling window length in samples.

    Returns
    -------
    np.ndarray, shape (N,)
        VPIN values in [0, 1].  Returns 0 when the window has no volume.
    """
    buy = pd.Series(np.asarray(buy_volume, dtype=np.float64))
    sell = pd.Series(np.asarray(sell_volume, dtype=np.float64))

    abs_imb = (buy - sell).abs()
    total = buy + sell

    num = abs_imb.rolling(window, min_periods=1).sum()
    den = total.rolling(window, min_periods=1).sum()

    with np.errstate(divide="ignore", invalid="ignore"):
        vpin = np.where(den.values > 0, num.values / (den.values + _EPS), 0.0)

    # Numerical safety — |buy-sell| <= buy+sell by construction, so VPIN is
    # algebraically in [0, 1]; we still clip to defend against rounding.
    return np.clip(vpin, 0.0, 1.0)


# ---------------------------------------------------------------------------
# 4. Book-pressure imbalance (multi-level weighted OBI)
# ---------------------------------------------------------------------------

def compute_book_pressure_imbalance(
    bid_depths: np.ndarray,
    ask_depths: np.ndarray,
    weights: Optional[np.ndarray] = None,
    alpha: float = 0.5,
) -> np.ndarray:
    """Depth-weighted imbalance across LOB levels.

    ``bpi = Σ_i w_i (b_i - a_i)/(b_i + a_i)  /  Σ_i w_i``

    with ``w_i = exp(-alpha * i)`` (exponential decay by level).  Unlike
    ``obi_L1`` which only reads the top of book, this feature weights deeper
    levels with decaying influence — matching the intuition that nearer
    levels are more informative.

    Parameters
    ----------
    bid_depths, ask_depths : np.ndarray, shape (N, K)
        Per-level depth at each time step.  ``K`` is the number of levels.
    weights : np.ndarray, shape (K,), optional
        Custom weights.  If ``None`` uses ``exp(-alpha * i)``.
    alpha : float
        Decay rate for the default exponential weights.

    Returns
    -------
    np.ndarray, shape (N,)
        Weighted imbalance values in [-1, 1].
    """
    bid = np.asarray(bid_depths, dtype=np.float64)
    ask = np.asarray(ask_depths, dtype=np.float64)
    if bid.ndim != 2 or ask.ndim != 2:
        raise ValueError("bid_depths / ask_depths must be 2-D (N, K)")
    if bid.shape != ask.shape:
        raise ValueError("bid_depths and ask_depths shape mismatch")

    K = bid.shape[1]
    if weights is None:
        weights = np.exp(-alpha * np.arange(K, dtype=np.float64))
    else:
        weights = np.asarray(weights, dtype=np.float64)
        if weights.shape != (K,):
            raise ValueError(f"weights must have shape ({K},)")

    w_sum = weights.sum()
    if w_sum <= 0:
        return np.zeros(bid.shape[0], dtype=np.float64)

    denom = bid + ask
    with np.errstate(divide="ignore", invalid="ignore"):
        level_imb = np.where(denom > 0, (bid - ask) / (denom + _EPS), 0.0)

    # Weighted mean across the level axis.
    bpi = (level_imb * weights[np.newaxis, :]).sum(axis=1) / w_sum
    return bpi


# ---------------------------------------------------------------------------
# 5. Price impact proxy (proper Kyle's lambda on trade volume)
# ---------------------------------------------------------------------------

def compute_price_impact_proxy(
    trade_volume: np.ndarray,
    returns: np.ndarray,
    window: int = 30,
) -> np.ndarray:
    """Rolling mean of ``|return| / trade_volume`` — proper Kyle's lambda.

    The previous implementation in ``microstructure.py`` used
    ``bid_depth_L5`` as a volume proxy.  That quantity measures *available*
    liquidity at the bid, not the *executed* flow required by Kyle (1985),
    so it inverts the sign of the intended signal (high bid depth looked
    like low lambda, but liquid books actually have low impact per unit of
    volume, not low depth).  This function uses actual executed volume.

    Parameters
    ----------
    trade_volume : np.ndarray, shape (N,)
        Total executed volume per 1-second bucket (``buy + sell``).
    returns : np.ndarray, shape (N,)
        1-second log returns.
    window : int
        Rolling mean length in samples.

    Returns
    -------
    np.ndarray, shape (N,)
        Rolling price-impact proxy.  Bars with zero volume contribute a 0
        per-sample value (cannot infer impact).
    """
    vol = np.asarray(trade_volume, dtype=np.float64)
    ret = np.asarray(returns, dtype=np.float64)
    abs_ret = np.abs(ret)

    # |r| / (vol + 1) — the +1 matches the task spec and is a conservative
    # denominator shift that keeps the feature finite for zero-volume bars.
    impact = abs_ret / (vol + 1.0)

    out = pd.Series(impact).rolling(window, min_periods=1).mean().values
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


# ---------------------------------------------------------------------------
# Convenience: names in canonical order
# ---------------------------------------------------------------------------

DERIVED_FEATURE_NAMES: list[str] = [
    "microprice_dev_bps",
    "roll_spread_60s",
    "vpin_60s",
    "vpin_300s",
    "book_pressure_imbalance",
    "price_impact_30s",
]


def compute_derived_features(
    *,
    bid_prices: np.ndarray,
    ask_prices: np.ndarray,
    bid_amounts: np.ndarray,
    ask_amounts: np.ndarray,
    mid: np.ndarray,
    log_returns_1s: np.ndarray,
    buy_volume_1s: Optional[np.ndarray] = None,
    sell_volume_1s: Optional[np.ndarray] = None,
    roll_window: int = 60,
    impact_window: int = 30,
    bpi_alpha: float = 0.5,
) -> pd.DataFrame:
    """Compute the 6 causal derived-feature columns on a 1-second grid.

    The microprice itself is *not* returned as a feature (non-stationary);
    only the bps deviation is.

    Parameters
    ----------
    bid_prices, ask_prices, bid_amounts, ask_amounts : np.ndarray
        Shape ``(N, K)`` per-level LOB arrays.
    mid : np.ndarray, shape (N,)
        Mid price.
    log_returns_1s : np.ndarray, shape (N,)
        1-second log returns (already the diff of log mid).
    buy_volume_1s, sell_volume_1s : np.ndarray, optional, shape (N,)
        Signed executed volume.  If either is ``None`` the VPIN and
        price-impact columns are zeroed (pipeline fallback when no trades
        are available).

    Returns
    -------
    pd.DataFrame
        Columns in ``DERIVED_FEATURE_NAMES`` order.
    """
    n = mid.shape[0]

    # ------- 1. Microprice deviation ---------------------------------------
    micro = compute_microprice(
        bids_price=bid_prices[:, 0],
        bids_amt=bid_amounts[:, 0],
        asks_price=ask_prices[:, 0],
        asks_amt=ask_amounts[:, 0],
    )
    micro_dev_bps = compute_microprice_deviation_bps(mid=mid, microprice=micro)

    # ------- 2. Roll spread ------------------------------------------------
    roll_spread = compute_roll_spread(log_returns_1s, window=roll_window)

    # ------- 3. VPIN @ 60s, 300s ------------------------------------------
    if buy_volume_1s is not None and sell_volume_1s is not None:
        vpin_60 = compute_vpin(
            buy_volume=buy_volume_1s,
            sell_volume=sell_volume_1s,
            window=60,
        )
        vpin_300 = compute_vpin(
            buy_volume=buy_volume_1s,
            sell_volume=sell_volume_1s,
            window=300,
        )
    else:
        vpin_60 = np.zeros(n, dtype=np.float64)
        vpin_300 = np.zeros(n, dtype=np.float64)

    # ------- 4. Book-pressure imbalance ------------------------------------
    bpi = compute_book_pressure_imbalance(
        bid_depths=bid_amounts,
        ask_depths=ask_amounts,
        alpha=bpi_alpha,
    )

    # ------- 5. Price impact (Kyle's lambda, proper) -----------------------
    if buy_volume_1s is not None and sell_volume_1s is not None:
        total_vol = np.asarray(buy_volume_1s, dtype=np.float64) + np.asarray(
            sell_volume_1s, dtype=np.float64
        )
        impact = compute_price_impact_proxy(
            trade_volume=total_vol,
            returns=log_returns_1s,
            window=impact_window,
        )
    else:
        impact = np.zeros(n, dtype=np.float64)

    out = pd.DataFrame({
        "microprice_dev_bps": micro_dev_bps,
        "roll_spread_60s": roll_spread,
        "vpin_60s": vpin_60,
        "vpin_300s": vpin_300,
        "book_pressure_imbalance": bpi,
        "price_impact_30s": impact,
    })
    out = out.fillna(0.0)
    return out

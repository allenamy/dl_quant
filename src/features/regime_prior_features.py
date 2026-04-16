"""Regime-prior features — 6 hourly-scale external signals for PPNet gate.

Unlike microstructure features (5-min window), regime features span the full
past 1–6 hours, providing explicit context about the current market state so
the model can condition predictions on regime. All strictly causal.

Callers must supply finite inputs; the upstream pipeline (`build_npz_for_day`)
sanitizes via `np.nan_to_num` before feeding this module.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

REGIME_PRIOR_FEATURE_NAMES: list[str] = [
    "vol_1h",
    "spread_mean_1h",
    "obi_trend_1h",
    "price_return_6h",
    "hour_sin",
    "hour_cos",
]

_WINDOW_1H = 3600
_WINDOW_6H = 21600
_US_PER_SEC = 1_000_000
_SEC_PER_DAY = 86_400


def _rolling_linear_slope(y: np.ndarray, window: int) -> np.ndarray:
    """Causal rolling OLS slope of y over a trailing window.

    Returns an array the same length as y. Values before the window is full
    use the available history (min_periods=2, else 0).

    NOTE: This is O(n × window) Python-loop — acceptable for typical
    single-day NPZ generation (~86 400 rows × 3600 window). Will be
    vectorized in a follow-up if it becomes a bottleneck during
    multi-day NPZ regen (Task 14).
    """
    y = np.asarray(y, dtype=np.float64)
    n = len(y)
    out = np.zeros(n, dtype=np.float64)
    for t in range(n):
        start = max(0, t - window + 1)
        seg = y[start:t + 1]
        m = len(seg)
        if m < 2:
            continue
        x = np.arange(m, dtype=np.float64)
        xm = x.mean()
        ym = seg.mean()
        denom = np.sum((x - xm) ** 2)
        if denom <= 0:
            continue
        out[t] = float(np.sum((x - xm) * (seg - ym)) / denom)
    return out


def compute_regime_prior_features(df: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "mid_price", "log_return_1s", "obi_L5", "spread_bps"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"compute_regime_prior_features missing columns: {missing}")

    ts = df["timestamp"].to_numpy().astype(np.int64)
    mid = df["mid_price"].to_numpy().astype(np.float64)
    log_ret = df["log_return_1s"].to_numpy().astype(np.float64)
    obi = df["obi_L5"].to_numpy().astype(np.float64)
    spread = df["spread_bps"].to_numpy().astype(np.float64)

    out = pd.DataFrame({"timestamp": ts})

    log_ret_s = pd.Series(log_ret)
    out["vol_1h"] = (
        log_ret_s.rolling(window=_WINDOW_1H, min_periods=2)
        .std(ddof=0)
        .fillna(0.0)
        .to_numpy()
    )

    out["spread_mean_1h"] = (
        pd.Series(spread)
        .rolling(window=_WINDOW_1H, min_periods=1)
        .mean()
        .to_numpy()
    )

    out["obi_trend_1h"] = _rolling_linear_slope(obi, _WINDOW_1H)

    pret = np.zeros_like(mid)
    if len(mid) > _WINDOW_6H:
        safe_past = np.where(mid[:-_WINDOW_6H] > 0, mid[:-_WINDOW_6H], 1.0)
        pret[_WINDOW_6H:] = np.log(mid[_WINDOW_6H:] / safe_past)
    out["price_return_6h"] = pret

    seconds_of_day = (ts // _US_PER_SEC) % _SEC_PER_DAY
    theta = 2 * np.pi * seconds_of_day / _SEC_PER_DAY
    out["hour_sin"] = np.sin(theta)
    out["hour_cos"] = np.cos(theta)

    return out

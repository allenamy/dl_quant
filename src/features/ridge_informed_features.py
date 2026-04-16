"""Ridge-informed derived features.

Six features motivated by Phase A1 Ridge weight analysis (top signals:
net_trade_flow_1s, OBI_*, book pressure). All strictly causal.

Inputs expected on the dataframe:
    timestamp
    net_trade_flow_1s
    spread_bps
    realized_vol_30s
    obi_L5
    book_pressure_imbalance

Contract: callers must provide finite inputs (no NaN/inf). Upstream
`build_npz_for_day` already sanitizes via ``np.nan_to_num``; this module
relies on that guarantee rather than re-sanitizing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RIDGE_INFORMED_FEATURE_NAMES: list[str] = [
    "net_flow_x_spread",
    "net_flow_x_vol",
    "obi_L5_rank_1h",
    "net_flow_rank_1h",
    "large_trade_arrival_60s",
    "book_pressure_delta_60s",
]

_WINDOW_1H = 3600
_WINDOW_60 = 60
_LARGE_TRADE_QUANTILE = 0.95


def _rolling_rank(series: pd.Series, window: int, min_periods: int = 1) -> pd.Series:
    """Per-row percentile rank over the TRAILING window."""
    return (
        series.rolling(window=window, min_periods=min_periods)
        .apply(lambda v: (v[-1] >= v[:-1]).sum() / max(len(v) - 1, 1), raw=True)
        .astype(np.float64)
    )


def compute_ridge_informed_features(df: pd.DataFrame) -> pd.DataFrame:
    required = {
        "timestamp",
        "net_trade_flow_1s",
        "spread_bps",
        "realized_vol_30s",
        "obi_L5",
        "book_pressure_imbalance",
    }
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"compute_ridge_informed_features missing columns: {missing}")

    out = pd.DataFrame({"timestamp": df["timestamp"].to_numpy()})

    out["net_flow_x_spread"] = (
        df["net_trade_flow_1s"].to_numpy() * df["spread_bps"].to_numpy()
    )
    out["net_flow_x_vol"] = (
        df["net_trade_flow_1s"].to_numpy() * df["realized_vol_30s"].to_numpy()
    )
    out["obi_L5_rank_1h"] = _rolling_rank(df["obi_L5"], _WINDOW_1H).to_numpy()
    out["net_flow_rank_1h"] = _rolling_rank(df["net_trade_flow_1s"], _WINDOW_1H).to_numpy()

    abs_flow = df["net_trade_flow_1s"].abs()
    # Causal p95 threshold: computed over the trailing 1-hour window so no
    # future data influences the threshold at time t. Strict `>` plus a
    # non-degenerate guard prevents the event from firing trivially when
    # abs_flow is flat/zero (rolling_p95 would equal rolling_max otherwise).
    rolling_p95 = abs_flow.rolling(window=_WINDOW_1H, min_periods=_WINDOW_60).quantile(
        _LARGE_TRADE_QUANTILE
    )
    rolling_max_flow = abs_flow.rolling(window=_WINDOW_60, min_periods=1).max()
    is_nondegenerate = rolling_p95 > 0
    out["large_trade_arrival_60s"] = (
        (rolling_max_flow > rolling_p95) & is_nondegenerate
    ).astype(np.float64).to_numpy()

    bpi = df["book_pressure_imbalance"].to_numpy()
    delta = np.zeros_like(bpi, dtype=np.float64)
    delta[_WINDOW_60:] = bpi[_WINDOW_60:] - bpi[:-_WINDOW_60]
    out["book_pressure_delta_60s"] = delta

    return out

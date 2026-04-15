"""Compute trade-flow features from raw trade tick data.

All features are **strictly causal**: the feature at time *t* depends only on
data at time *t* and earlier.  No future information is used.

The 9 trade features complement the 43 microstructure features from
``compute_microstructure_features`` and the 6 derived features from
``derived_features``, bringing the base total to 58.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Step 1: Aggregate raw trade ticks into 1-second bars
# ---------------------------------------------------------------------------

def aggregate_trades_to_1s(
    trades_df: pd.DataFrame,
    start_ts_us: int | None = None,
    end_ts_us: int | None = None,
    mid_prices_1s: np.ndarray | None = None,
) -> pd.DataFrame:
    """Aggregate raw trade ticks into 1-second bars.

    Parameters
    ----------
    trades_df : pd.DataFrame
        Raw trades.  Must contain columns:
        ``timestamp`` (int64, microseconds), ``price`` (float),
        ``size`` (float), ``side`` (str, "Buy" or "Sell").
    start_ts_us : int, optional
        First 1-second boundary (microseconds).  If None, derived from data.
    end_ts_us : int, optional
        Last 1-second boundary (microseconds).  If None, derived from data.
    mid_prices_1s : np.ndarray, optional
        Mid prices on the 1s grid, used to fill vwap for seconds with
        no trades.  If None, vwap for no-trade seconds is filled with 0.

    Returns
    -------
    pd.DataFrame
        One row per second with columns:
        ``timestamp``, ``trade_count``, ``buy_volume``, ``sell_volume``,
        ``net_trade_flow``, ``trade_imbalance``, ``vwap``, ``trade_intensity``.

        Seconds with no trades get zeros for volume/flow/imbalance.
        VWAP for no-trade seconds is filled with ``mid_prices_1s`` when
        available, otherwise 0.
    """
    us_per_sec = 1_000_000

    if trades_df is None or len(trades_df) == 0:
        # Return empty DataFrame with correct schema
        return pd.DataFrame(columns=[
            "timestamp", "trade_count", "buy_volume", "sell_volume",
            "net_trade_flow", "trade_imbalance", "vwap", "trade_intensity",
        ])

    df = trades_df.copy()
    # Defensive dedup: trade collectors may produce duplicate exec_ids due to
    # REST polling overlap. Without this, volumes are inflated 2-3x and models
    # learn fake signal. Safe to run on already-clean data (no-op).
    if "exec_id" in df.columns:
        df = df.drop_duplicates(subset=["exec_id"]).reset_index(drop=True)
    df["_ts_sec"] = (df["timestamp"] // us_per_sec) * us_per_sec

    # Per-second aggregation
    is_buy = df["side"] == "Buy"
    df["_buy_vol"] = df["size"] * is_buy.astype(float)
    df["_sell_vol"] = df["size"] * (~is_buy).astype(float)
    df["_dollar_vol"] = df["size"] * df["price"]

    grouped = df.groupby("_ts_sec", sort=True).agg(
        trade_count=("size", "count"),
        buy_volume=("_buy_vol", "sum"),
        sell_volume=("_sell_vol", "sum"),
        total_volume=("size", "sum"),
        dollar_volume=("_dollar_vol", "sum"),
    ).reset_index()

    # VWAP: dollar_volume / total_volume
    with np.errstate(divide="ignore", invalid="ignore"):
        grouped["vwap"] = np.where(
            grouped["total_volume"] > 0,
            grouped["dollar_volume"] / grouped["total_volume"],
            0.0,
        )

    # Net trade flow
    grouped["net_trade_flow"] = grouped["buy_volume"] - grouped["sell_volume"]

    # Trade imbalance: (buy - sell) / (buy + sell), bounded [-1, 1]
    total = grouped["buy_volume"] + grouped["sell_volume"]
    with np.errstate(divide="ignore", invalid="ignore"):
        grouped["trade_imbalance"] = np.where(
            total > 0,
            grouped["net_trade_flow"] / total,
            0.0,
        )

    # Trade intensity: trade_count (raw; normalization done downstream)
    grouped["trade_intensity"] = grouped["trade_count"].astype(float)

    # Build full 1-second grid
    if start_ts_us is None:
        start_ts_us = int(grouped["_ts_sec"].iloc[0])
    if end_ts_us is None:
        end_ts_us = int(grouped["_ts_sec"].iloc[-1])

    full_grid = pd.DataFrame(
        {"_ts_sec": np.arange(start_ts_us, end_ts_us + us_per_sec, us_per_sec)}
    )

    result = full_grid.merge(grouped, on="_ts_sec", how="left")

    # Fill NaN with 0 for seconds with no trades (except vwap)
    fill_zero_cols = [
        "trade_count", "buy_volume", "sell_volume",
        "net_trade_flow", "trade_imbalance", "trade_intensity",
    ]
    for col in fill_zero_cols:
        if col in result.columns:
            result[col] = result[col].fillna(0.0)

    # Fill vwap: use mid prices if available, else 0
    if "vwap" in result.columns:
        if mid_prices_1s is not None and len(mid_prices_1s) == len(result):
            # Fill no-trade seconds with mid price
            vwap_na = result["vwap"].isna()
            result.loc[vwap_na, "vwap"] = mid_prices_1s[vwap_na.values]
        result["vwap"] = result["vwap"].fillna(0.0)

    result.rename(columns={"_ts_sec": "timestamp"}, inplace=True)
    output_cols = [
        "trade_count", "buy_volume", "sell_volume",
        "net_trade_flow", "trade_imbalance", "vwap", "trade_intensity",
    ]
    result = result[["timestamp"] + output_cols].copy()
    result.reset_index(drop=True, inplace=True)

    return result


# ---------------------------------------------------------------------------
# Step 2: Rolling trade flow features from 1-second trade bars
# ---------------------------------------------------------------------------

def compute_trade_flow_features(
    trade_bars_1s: pd.DataFrame,
    mid_prices: np.ndarray | None = None,
) -> pd.DataFrame:
    """Compute rolling trade flow features from 1s trade bars.

    Parameters
    ----------
    trade_bars_1s : pd.DataFrame
        Output of ``aggregate_trades_to_1s``.  Must contain columns:
        ``timestamp``, ``buy_volume``, ``sell_volume``, ``net_trade_flow``,
        ``trade_imbalance``, ``trade_count``, ``vwap``.
    mid_prices : np.ndarray, optional
        Mid prices aligned to the same 1s grid (from depth features).
        Used to compute ``vwap_return_1s``.  If None, this feature is 0.

    Returns
    -------
    pd.DataFrame
        DataFrame with ``timestamp`` plus 9 trade feature columns:
        ``buy_volume_1s``, ``sell_volume_1s``, ``net_trade_flow_1s``,
        ``trade_imbalance_1s``, ``cumulative_net_flow_30s``,
        ``cumulative_net_flow_300s``, ``trade_intensity_30s``,
        ``vwap_return_1s``, ``kyle_lambda_30s``.

        All features are backward-looking (causal).
    """
    n = len(trade_bars_1s)
    out = pd.DataFrame()
    out["timestamp"] = trade_bars_1s["timestamp"].values.copy()

    # --- Raw 1s values (4) ---
    out["buy_volume_1s"] = trade_bars_1s["buy_volume"].values.astype(np.float64)
    out["sell_volume_1s"] = trade_bars_1s["sell_volume"].values.astype(np.float64)
    out["net_trade_flow_1s"] = trade_bars_1s["net_trade_flow"].values.astype(np.float64)
    out["trade_imbalance_1s"] = trade_bars_1s["trade_imbalance"].values.astype(np.float64)

    # --- Rolling sums/means (3) --- all backward-looking (causal)
    ntf_s = pd.Series(trade_bars_1s["net_trade_flow"].values, dtype=np.float64)
    tc_s = pd.Series(trade_bars_1s["trade_count"].values, dtype=np.float64)

    out["cumulative_net_flow_30s"] = ntf_s.rolling(30, min_periods=1).sum().values
    out["cumulative_net_flow_300s"] = ntf_s.rolling(300, min_periods=1).sum().values
    out["trade_intensity_30s"] = tc_s.rolling(30, min_periods=1).mean().values

    # --- VWAP return (1) --- log(vwap / mid_price)
    vwap = trade_bars_1s["vwap"].values.astype(np.float64)
    if mid_prices is not None and len(mid_prices) == n:
        mid = mid_prices.astype(np.float64)
        # Where vwap or mid is 0, set return to 0
        valid = (vwap > 0) & (mid > 0)
        vwap_ret = np.zeros(n, dtype=np.float64)
        vwap_ret[valid] = np.log(vwap[valid] / mid[valid])
        out["vwap_return_1s"] = vwap_ret
    else:
        vwap_ret = np.zeros(n, dtype=np.float64)
        out["vwap_return_1s"] = vwap_ret

    # --- Kyle's lambda (1) --- |log_return_1s| / (total_volume_1s + eps)
    # This is the *proper* Kyle's lambda using executed volume (not LOB
    # depth).  ``mid_prices`` must be supplied so we can compute the
    # 1-second log return; when absent we fall back to zeros.
    if mid_prices is not None and len(mid_prices) == n:
        mid = mid_prices.astype(np.float64)
        log_mid = np.log(np.maximum(mid, 1e-10))
        log_ret_1s = pd.Series(log_mid).diff(1).fillna(0.0).values
        total_vol = (
            out["buy_volume_1s"].values + out["sell_volume_1s"].values
        )
        impact = np.abs(log_ret_1s) / (total_vol + 1.0)
        kyle = (
            pd.Series(impact)
            .rolling(30, min_periods=1)
            .mean()
            .fillna(0.0)
            .values
        )
        out["kyle_lambda_30s"] = kyle
    else:
        out["kyle_lambda_30s"] = np.zeros(n, dtype=np.float64)

    # Fill any remaining NaN with 0.0
    out = out.fillna(0.0)

    return out


# ---------------------------------------------------------------------------
# Canonical list of 9 trade feature names (in order)
# ---------------------------------------------------------------------------

TRADE_FEATURE_NAMES: list[str] = [
    "buy_volume_1s",
    "sell_volume_1s",
    "net_trade_flow_1s",
    "trade_imbalance_1s",
    "cumulative_net_flow_30s",
    "cumulative_net_flow_300s",
    "trade_intensity_30s",
    "vwap_return_1s",
    "kyle_lambda_30s",
]


# ---------------------------------------------------------------------------
# Quick smoke test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Creating synthetic trade data ...")
    rng = np.random.default_rng(42)
    n = 5000
    start_ts = 1_700_000_000_000_000

    trades = pd.DataFrame({
        "timestamp": start_ts + np.sort(rng.integers(0, 60_000_000, size=n)),
        "price": 30_000.0 + rng.normal(0, 10, n),
        "size": rng.uniform(0.001, 1.0, n),
        "side": rng.choice(["Buy", "Sell"], size=n),
        "exec_id": [f"exec_{i}" for i in range(n)],
    })

    bars = aggregate_trades_to_1s(trades)
    print(f"  1s trade bars shape: {bars.shape}")
    print(bars.head())

    features = compute_trade_flow_features(bars)
    print(f"  trade features shape: {features.shape}")
    feat_cols = [c for c in features.columns if c != "timestamp"]
    print(f"  feature count: {len(feat_cols)}")
    print(f"  feature names: {feat_cols}")
    print(features.head())
    print("OK")

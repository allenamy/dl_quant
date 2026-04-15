"""Compute 44 microstructure features from 1-second LOB bars.

All features are **strictly causal**: the feature at time *t* depends only on
data at time *t* and earlier.  No future information is used.

The 44 base features comprise the original 39 (excluding mid_price) plus
5 order flow features.  An optional Savitzky-Golay filtering step
(``apply_savgol_filter``) can produce smoothed variants of selected noisy
features.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter


def compute_microstructure_features(
    df: pd.DataFrame,
    n_levels: int = 25,
) -> pd.DataFrame:
    """Compute 44 microstructure features from 1-second LOB bars.

    Parameters
    ----------
    df : pd.DataFrame
        1-second LOB bars produced by ``resample_lob_to_1s``.  Must contain a
        ``timestamp`` column and ``asks[i].price``, ``asks[i].amount``,
        ``bids[i].price``, ``bids[i].amount`` for *i* in ``range(n_levels)``.
    n_levels : int
        Number of order-book levels (default 25).

    Returns
    -------
    pd.DataFrame
        DataFrame with ``timestamp`` plus exactly 44 feature columns
        (excluding ``mid_price``).
        NaN values are filled with 0.0.
    """

    out = pd.DataFrame()
    out["timestamp"] = df["timestamp"].values

    # ------------------------------------------------------------------
    # Helper arrays – bid/ask prices and amounts as 2-D numpy arrays
    # Shape: (n_rows, n_levels)
    # ------------------------------------------------------------------
    bid_prices = np.column_stack(
        [df[f"bids[{i}].price"].values for i in range(n_levels)]
    )
    ask_prices = np.column_stack(
        [df[f"asks[{i}].price"].values for i in range(n_levels)]
    )
    bid_amounts = np.column_stack(
        [df[f"bids[{i}].amount"].values for i in range(n_levels)]
    )
    ask_amounts = np.column_stack(
        [df[f"asks[{i}].amount"].values for i in range(n_levels)]
    )

    # ==================================================================
    # 1. PRICE features (4)
    # ==================================================================
    mid = (bid_prices[:, 0] + ask_prices[:, 0]) / 2.0
    mid = np.maximum(mid, 1e-10)  # guard against zero
    out["mid_price"] = mid

    mid_s = pd.Series(mid)
    log_mid = np.log(mid)
    log_mid_s = pd.Series(log_mid)

    # .diff() is backward-looking => causal
    out["log_return_1s"] = log_mid_s.diff(1).values
    out["log_return_5s"] = log_mid_s.diff(5).values
    out["log_return_30s"] = log_mid_s.diff(30).values

    # ==================================================================
    # 2. SPREAD features (2)
    # ==================================================================
    spread = ask_prices[:, 0] - bid_prices[:, 0]
    spread_bps = (spread / mid) * 10_000.0
    out["spread_bps"] = spread_bps
    out["spread_change"] = pd.Series(spread_bps).diff(1).values

    # ==================================================================
    # 3. IMBALANCE features (5)
    # ==================================================================
    def _obi(bid_amt: np.ndarray, ask_amt: np.ndarray) -> np.ndarray:
        denom = bid_amt + ask_amt
        # handle zero denominator
        with np.errstate(divide="ignore", invalid="ignore"):
            result = np.where(denom != 0, (bid_amt - ask_amt) / denom, 0.0)
        return result

    out["obi_L1"] = _obi(bid_amounts[:, :1].sum(axis=1), ask_amounts[:, :1].sum(axis=1))
    out["obi_L5"] = _obi(bid_amounts[:, :5].sum(axis=1), ask_amounts[:, :5].sum(axis=1))
    out["obi_L10"] = _obi(bid_amounts[:, :10].sum(axis=1), ask_amounts[:, :10].sum(axis=1))
    out["obi_L25"] = _obi(bid_amounts[:, :25].sum(axis=1), ask_amounts[:, :25].sum(axis=1))
    out["obi_L1_delta"] = pd.Series(out["obi_L1"].values).diff(1).values

    # ==================================================================
    # 4. DEPTH features (5)
    # ==================================================================
    bid_depth_5 = bid_amounts[:, :5].sum(axis=1)
    ask_depth_5 = ask_amounts[:, :5].sum(axis=1)
    bid_depth_25 = bid_amounts[:, :25].sum(axis=1)
    ask_depth_25 = ask_amounts[:, :25].sum(axis=1)

    out["bid_depth_L5"] = np.log1p(bid_depth_5)
    out["ask_depth_L5"] = np.log1p(ask_depth_5)
    out["bid_depth_L25"] = np.log1p(bid_depth_25)
    out["ask_depth_L25"] = np.log1p(ask_depth_25)

    depth_sum_5 = bid_depth_5 + ask_depth_5
    with np.errstate(divide="ignore", invalid="ignore"):
        out["depth_ratio_L5"] = np.where(
            depth_sum_5 != 0, bid_depth_5 / depth_sum_5, 0.5
        )

    # ==================================================================
    # 5. PRESSURE features (3)
    # ==================================================================
    # Weighted average bid price over L10 (weighted by amount)
    bid_amt_10 = bid_amounts[:, :10]
    ask_amt_10 = ask_amounts[:, :10]
    bid_px_10 = bid_prices[:, :10]
    ask_px_10 = ask_prices[:, :10]

    bid_wt_sum = bid_amt_10.sum(axis=1)
    ask_wt_sum = ask_amt_10.sum(axis=1)

    with np.errstate(divide="ignore", invalid="ignore"):
        wpb = np.where(
            bid_wt_sum != 0,
            (bid_px_10 * bid_amt_10).sum(axis=1) / bid_wt_sum,
            bid_prices[:, 0],
        )
        wpa = np.where(
            ask_wt_sum != 0,
            (ask_px_10 * ask_amt_10).sum(axis=1) / ask_wt_sum,
            ask_prices[:, 0],
        )

    out["weighted_price_bid_L10"] = ((wpb - mid) / mid) * 10_000.0
    out["weighted_price_ask_L10"] = ((wpa - mid) / mid) * 10_000.0
    # price_pressure: difference between weighted mid and mid, in bps
    weighted_mid = (wpb + wpa) / 2.0
    out["price_pressure"] = ((weighted_mid - mid) / mid) * 10_000.0

    # ==================================================================
    # 6. VOLATILITY features (3) — rolling std of log_return_1s
    # ==================================================================
    lr1 = pd.Series(out["log_return_1s"].values, dtype=float)
    out["realized_vol_30s"] = lr1.rolling(30, min_periods=1).std().values
    out["realized_vol_60s"] = lr1.rolling(60, min_periods=1).std().values
    out["realized_vol_300s"] = lr1.rolling(300, min_periods=1).std().values

    # ==================================================================
    # 7. MICROSTRUCTURE features (2) — rolling means
    # ==================================================================
    # Kyle's lambda proxy: |return| / volume (bid_depth_L5 as volume proxy)
    abs_ret = lr1.abs()
    with np.errstate(divide="ignore", invalid="ignore"):
        kyle_raw = np.where(bid_depth_5 != 0, abs_ret.values / bid_depth_5, 0.0)
    out["kyle_lambda_30s"] = pd.Series(kyle_raw).rolling(30, min_periods=1).mean().values

    # Amihud illiquidity: |return| / dollar_volume
    dollar_vol = bid_depth_5 * mid
    with np.errstate(divide="ignore", invalid="ignore"):
        amihud_raw = np.where(dollar_vol != 0, abs_ret.values / dollar_vol, 0.0)
    out["amihud_30s"] = pd.Series(amihud_raw).rolling(30, min_periods=1).mean().values

    # ==================================================================
    # 8. SLOPES features (2) — price impact per level (bps)
    # ==================================================================
    # Bid slope: (best_bid - bid[9]) / 9 levels, normalised by mid => bps
    bid_range = bid_prices[:, 0] - bid_prices[:, 9]
    ask_range = ask_prices[:, 9] - ask_prices[:, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        out["bid_slope_L10"] = np.where(mid != 0, (bid_range / 9.0) / mid * 10_000.0, 0.0)
        out["ask_slope_L10"] = np.where(mid != 0, (ask_range / 9.0) / mid * 10_000.0, 0.0)

    # ==================================================================
    # 9. CONCENTRATION features (2) — L1 / L25 amount ratio
    # ==================================================================
    with np.errstate(divide="ignore", invalid="ignore"):
        out["bid_concentration"] = np.where(
            bid_depth_25 != 0, bid_amounts[:, 0] / bid_depth_25, 0.0
        )
        out["ask_concentration"] = np.where(
            ask_depth_25 != 0, ask_amounts[:, 0] / ask_depth_25, 0.0
        )

    # ==================================================================
    # 10. PER-LEVEL amount ratios (10): amount[i] / depth_L5
    # ==================================================================
    for i in range(5):
        with np.errstate(divide="ignore", invalid="ignore"):
            out[f"bid_amt_ratio_L{i}"] = np.where(
                bid_depth_5 != 0, bid_amounts[:, i] / bid_depth_5, 0.0
            )
            out[f"ask_amt_ratio_L{i}"] = np.where(
                ask_depth_5 != 0, ask_amounts[:, i] / ask_depth_5, 0.0
            )

    # ==================================================================
    # 11. TEMPORAL features (2)
    # ==================================================================
    # timestamp is microseconds since epoch
    seconds_of_day = (df["timestamp"].values % (86_400 * 1_000_000)) / 1_000_000
    out["second_of_day_sin"] = np.sin(2 * np.pi * seconds_of_day / 86_400)
    out["second_of_day_cos"] = np.cos(2 * np.pi * seconds_of_day / 86_400)

    # ==================================================================
    # 12. ORDER FLOW features (5)
    # ==================================================================
    bid_depth_5_s = pd.Series(bid_depth_5)
    ask_depth_5_s = pd.Series(ask_depth_5)

    delta_bid = bid_depth_5_s.diff(1)
    delta_ask = ask_depth_5_s.diff(1)

    out["delta_bid_depth_L5"] = delta_bid.values
    out["delta_ask_depth_L5"] = delta_ask.values
    out["net_order_flow_L5"] = (delta_bid - delta_ask).values

    obi_L5_s = pd.Series(out["obi_L5"].values)
    out["delta_obi_L5_5s"] = obi_L5_s.diff(5).values

    price_pressure_s = pd.Series(out["price_pressure"].values)
    out["delta_pressure_5s"] = price_pressure_s.diff(5).values

    # ==================================================================
    # Fill NaN with 0.0
    # ==================================================================
    out = out.fillna(0.0)

    return out


# ---------------------------------------------------------------------------
# Savitzky-Golay feature filtering
# ---------------------------------------------------------------------------

# Features to smooth — inherently noisy signals that benefit from denoising.
# Returns, OBI, temporal features, and order flow deltas are NOT filtered.
_SG_TARGET_PREFIXES = (
    "realized_vol_",
    "kyle_lambda_",
    "amihud_",
    "bid_depth_L",
    "ask_depth_L",
    "bid_slope_",
    "ask_slope_",
)


def apply_savgol_filter(
    df: pd.DataFrame,
    window_length: int = 11,
    polyorder: int = 3,
) -> pd.DataFrame:
    """DEPRECATED — this function is NON-CAUSAL and must not be used in training.

    scipy.signal.savgol_filter with mode='nearest' uses a CENTERED window,
    meaning each smoothed value at time t depends on (window_length-1)/2
    FUTURE samples. Applying it to features would inject a ~5-second
    look-ahead into every smoothed column, silently corrupting training
    and inflating validation metrics.

    The function is kept only for the existing unit test and will raise
    on any real use until replaced with a true causal filter.

    A correct causal implementation would use savgol_coeffs with a
    one-sided window applied via np.convolve (only past samples).
    """
    raise RuntimeError(
        "apply_savgol_filter is non-causal (uses future data); "
        "disabled to prevent training data leakage. "
        "Implement a one-sided causal SG filter if needed."
    )


# ---------------------------------------------------------------------------
# Quick smoke test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from resample import resample_lob_to_1s

    print("Reading BTCUSDT.csv (first 10 000 rows) ...")
    raw = pd.read_csv("BTCUSDT.csv", nrows=10_000)
    bars = resample_lob_to_1s(raw)
    print(f"  1-sec bars shape: {bars.shape}")

    features = compute_microstructure_features(bars)
    print(f"  features shape: {features.shape}")
    feature_cols = [c for c in features.columns if c != "timestamp"]
    print(f"  base feature count (excl mid_price): {len(feature_cols) - 1}")
    print(f"  feature names: {feature_cols}")

    filtered = apply_savgol_filter(features)
    sg_cols = [c for c in filtered.columns if c.endswith("_sg")]
    print(f"  SG-filtered columns added: {len(sg_cols)}")
    print(f"  total columns (incl SG): {len(filtered.columns)}")
    print(filtered.head())
    print("OK")

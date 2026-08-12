"""Extract raw LOB tensor from 1-second bars for the learned (Path B) encoder.

The raw tensor preserves orderbook spatial structure that hand-crafted features
discard: depth profile shape, liquidity gaps, cross-level correlations.

All operations are **strictly causal**: the tensor at time t depends only on
data at time t (no temporal mixing).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def extract_raw_lob_tensor(
    df_1s: pd.DataFrame,
    n_levels: int = 20,
) -> np.ndarray:
    """Extract normalized raw LOB tensor from 1-second bars.

    Parameters
    ----------
    df_1s : pd.DataFrame
        1-second bars from ``resample_lob_to_1s()``. Must have columns:
        ``asks[i].price``, ``asks[i].amount``, ``bids[i].price``,
        ``bids[i].amount`` for ``i`` in ``range(n_levels)``.
    n_levels : int
        Number of LOB levels to extract (default 20, max available from
        Binance stream).

    Returns
    -------
    np.ndarray
        Shape ``(N, n_levels, 4)`` where the 4 channels are:
        ``[bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt]``

        - ``bid_delta_bps``: ``(bid_price[i] - mid) / mid * 10000``
          (always negative, in bps)
        - ``bid_log_amt``: ``log1p(bid_amount[i])``
        - ``ask_delta_bps``: ``(ask_price[i] - mid) / mid * 10000``
          (always positive, in bps)
        - ``ask_log_amt``: ``log1p(ask_amount[i])``

    Notes
    -----
    - Price normalization as bps-from-mid removes non-stationarity
      (raw prices drift).
    - ``log1p`` on amounts compresses heavy-tailed distribution.
    - Result is stationary and bounded, suitable for neural network input.
    - All operations are strictly causal (per-row, no temporal mixing).
    """
    n_rows = len(df_1s)

    # --- Build 2-D arrays: (n_rows, n_levels) for prices and amounts --------
    bid_prices = np.column_stack(
        [df_1s[f"bids[{i}].price"].values for i in range(n_levels)]
    ).astype(np.float64)
    ask_prices = np.column_stack(
        [df_1s[f"asks[{i}].price"].values for i in range(n_levels)]
    ).astype(np.float64)
    bid_amounts = np.column_stack(
        [df_1s[f"bids[{i}].amount"].values for i in range(n_levels)]
    ).astype(np.float64)
    ask_amounts = np.column_stack(
        [df_1s[f"asks[{i}].amount"].values for i in range(n_levels)]
    ).astype(np.float64)

    # --- Mid price: (best_bid + best_ask) / 2 --------------------------------
    mid = (bid_prices[:, 0] + ask_prices[:, 0]) / 2.0  # (n_rows,)

    # Guard against zero mid price (extremely unlikely for BTC but be safe)
    mid = np.where(mid == 0.0, 1.0, mid)

    # --- Price deltas in bps from mid -----------------------------------------
    # bid_delta_bps[i] = (bid_price[i] - mid) / mid * 10000  (negative)
    # ask_delta_bps[i] = (ask_price[i] - mid) / mid * 10000  (positive)
    mid_col = mid[:, np.newaxis]  # (n_rows, 1) for broadcasting
    bid_delta_bps = (bid_prices - mid_col) / mid_col * 10_000.0  # (n_rows, n_levels)
    ask_delta_bps = (ask_prices - mid_col) / mid_col * 10_000.0  # (n_rows, n_levels)

    # --- Log amounts ----------------------------------------------------------
    # Ensure non-negative before log1p
    bid_amounts = np.maximum(bid_amounts, 0.0)
    ask_amounts = np.maximum(ask_amounts, 0.0)
    bid_log_amt = np.log1p(bid_amounts)  # (n_rows, n_levels)
    ask_log_amt = np.log1p(ask_amounts)  # (n_rows, n_levels)

    # --- Stack into (N, n_levels, 4) tensor -----------------------------------
    # Channel order: [bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt]
    tensor = np.stack(
        [bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt],
        axis=-1,
    )  # (n_rows, n_levels, 4)

    # --- Clean up: NaN/Inf -> 0.0 ---------------------------------------------
    tensor = np.nan_to_num(tensor, nan=0.0, posinf=0.0, neginf=0.0)

    return tensor.astype(np.float32)

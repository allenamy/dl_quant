"""Streaming (incremental) feature computer for live trading.

Maintains a rolling buffer of ``input_len`` seconds and computes features
incrementally.  The output is model-ready tensors identical to what the
batch pipeline produces.

**CRITICAL invariant:** ``StreamingFeatureComputer.get_tensors()`` must
return outputs that are bit-for-bit identical (within float32 tolerance)
to the batch pipeline applied to the same data.  Any discrepancy between
training and inference feature computation will silently degrade model
performance.
"""

from __future__ import annotations

from collections import deque
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from src.features.microstructure import compute_microstructure_features
from src.features.raw_lob import extract_raw_lob_tensor
from src.features.trade_features import (
    TRADE_FEATURE_NAMES,
    aggregate_trades_to_1s,
    compute_trade_flow_features,
)


class StreamingFeatureComputer:
    """Maintains a rolling buffer for real-time feature computation.

    In live trading, this replaces the batch pipeline:
    - Receives one depth snapshot + trade batch per second
    - Maintains a rolling buffer of ``input_len`` (300) seconds
    - Computes features incrementally
    - Outputs model-ready tensors: ``(1, L, n_feat)`` and ``(1, L, n_levels, 4)``

    CRITICAL: The output of this class MUST be identical to what the batch
    pipeline produces.  Any discrepancy = training-inference skew = model
    failure.

    The strategy for guaranteeing consistency is simple: we store raw data
    in the buffer and recompute features from scratch using the **exact same
    functions** as the batch pipeline.  This is more expensive than true
    incremental computation, but for a 300-row buffer at 1 Hz the cost is
    negligible (~5 ms) and correctness is guaranteed.

    Parameters
    ----------
    input_len : int
        Number of 1-second rows in the model input window (default 300).
    n_levels : int
        Number of orderbook levels in depth snapshots (default 25).
    use_trades : bool
        Whether to include trade features (default True).
    feature_clip : float
        Clip feature values to ``[-feature_clip, +feature_clip]``.
    """

    def __init__(
        self,
        input_len: int = 300,
        n_levels: int = 25,
        use_trades: bool = True,
        feature_clip: float = 10.0,
    ) -> None:
        self.input_len = input_len
        self.n_levels = n_levels
        self.use_trades = use_trades
        self.feature_clip = feature_clip
        self.raw_levels = min(n_levels, 20)

        # Rolling buffers (deques with maxlen for automatic eviction)
        # Each element is a dict with keys matching DataFrame columns.
        self._depth_buffer: deque[dict] = deque(maxlen=input_len)
        self._trade_buffer: deque[dict] = deque(maxlen=input_len)

    def update(
        self,
        depth_snapshot: dict,
        trades: Optional[List[dict]] = None,
    ) -> bool:
        """Feed one second of data.

        Parameters
        ----------
        depth_snapshot : dict
            A single 1-second depth snapshot.  Must contain:
            - ``timestamp`` (int64, microseconds, 1-second boundary)
            - ``bids[i].price``, ``bids[i].amount`` for i in range(n_levels)
            - ``asks[i].price``, ``asks[i].amount`` for i in range(n_levels)
        trades : list[dict], optional
            List of trade dicts for this second.  Each dict must contain:
            ``timestamp``, ``price``, ``size``, ``side`` ("Buy"/"Sell").
            If None or empty, a zero-volume bar is recorded.

        Returns
        -------
        bool
            True when buffer is full (ready for inference).
        """
        self._depth_buffer.append(depth_snapshot)

        if self.use_trades:
            ts = depth_snapshot["timestamp"]
            if trades and len(trades) > 0:
                trades_df = pd.DataFrame(trades)
                bar = aggregate_trades_to_1s(
                    trades_df, start_ts_us=ts, end_ts_us=ts
                )
                if len(bar) > 0:
                    self._trade_buffer.append(bar.iloc[0].to_dict())
                else:
                    self._trade_buffer.append(self._zero_trade_bar(ts))
            else:
                self._trade_buffer.append(self._zero_trade_bar(ts))

        return self.is_ready()

    def get_tensors(self) -> Tuple[np.ndarray, np.ndarray]:
        """Compute features from current buffer.

        Returns
        -------
        x_feat : np.ndarray
            Shape ``(1, input_len, n_features)`` -- microstructure + trade
            features, float32.
        x_raw : np.ndarray
            Shape ``(1, input_len, raw_levels, 4)`` -- raw LOB tensor,
            float32.

        Raises
        ------
        RuntimeError
            If the buffer is not full (``is_ready()`` returns False).

        Notes
        -----
        This method reuses the **exact same functions** as the batch
        pipeline to guarantee identical outputs:
        - ``compute_microstructure_features()``
        - ``extract_raw_lob_tensor()``
        - ``compute_trade_flow_features()``
        """
        if not self.is_ready():
            raise RuntimeError(
                f"Buffer not full: {len(self._depth_buffer)}/{self.input_len}. "
                f"Call update() until is_ready() returns True."
            )

        # --- Convert depth buffer to DataFrame --------------------------------
        df_1s = pd.DataFrame(list(self._depth_buffer))

        # --- Compute microstructure features (same function as batch) ----------
        feat_df = compute_microstructure_features(df_1s, n_levels=self.n_levels)

        feature_cols = [
            c for c in feat_df.columns if c not in ("timestamp", "mid_price")
        ]
        mid_prices = feat_df["mid_price"].values.astype(np.float64)

        feat_matrix = feat_df[feature_cols].values.astype(np.float32)

        # --- Add trade features if enabled ------------------------------------
        if self.use_trades and len(self._trade_buffer) > 0:
            trade_bars_df = pd.DataFrame(list(self._trade_buffer))
            trade_feat_df = compute_trade_flow_features(
                trade_bars_df, mid_prices=mid_prices
            )
            trade_cols = [
                c for c in trade_feat_df.columns if c != "timestamp"
            ]
            trade_matrix = trade_feat_df[trade_cols].values.astype(np.float32)
            feat_matrix = np.concatenate([feat_matrix, trade_matrix], axis=1)
            feature_cols = feature_cols + trade_cols

        # --- Clean: nan_to_num then clip --------------------------------------
        feat_matrix = np.nan_to_num(
            feat_matrix, nan=0.0, posinf=0.0, neginf=0.0
        )
        feat_matrix = np.clip(
            feat_matrix, -self.feature_clip, self.feature_clip
        )

        # --- Extract raw LOB tensor (same function as batch) ------------------
        raw_tensor = extract_raw_lob_tensor(df_1s, n_levels=self.raw_levels)

        # --- Shape into batch-of-1 tensors ------------------------------------
        x_feat = feat_matrix[np.newaxis, :, :]    # (1, input_len, n_features)
        x_raw = raw_tensor[np.newaxis, :, :, :]   # (1, input_len, raw_levels, 4)

        return x_feat, x_raw

    def get_feature_names(self) -> List[str]:
        """Return the ordered list of feature names matching ``get_tensors()`` output."""
        # We must compute a dummy to get the canonical list, but we can
        # construct it from known column order.
        base_cols = self._microstructure_feature_names()
        if self.use_trades:
            return base_cols + list(TRADE_FEATURE_NAMES)
        return base_cols

    def is_ready(self) -> bool:
        """True when buffer has ``input_len`` rows."""
        return len(self._depth_buffer) >= self.input_len

    def reset(self) -> None:
        """Clear all buffers."""
        self._depth_buffer.clear()
        self._trade_buffer.clear()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _zero_trade_bar(ts: int) -> dict:
        """Create a zero-volume trade bar for a second with no trades."""
        return {
            "timestamp": ts,
            "trade_count": 0,
            "buy_volume": 0.0,
            "sell_volume": 0.0,
            "net_trade_flow": 0.0,
            "trade_imbalance": 0.0,
            "vwap": 0.0,
            "trade_intensity": 0.0,
        }

    @staticmethod
    def _microstructure_feature_names() -> List[str]:
        """Return the canonical list of 44 microstructure feature names.

        This must match the column order produced by
        ``compute_microstructure_features`` (excluding timestamp and mid_price).
        """
        return [
            # Price (3)
            "log_return_1s", "log_return_5s", "log_return_30s",
            # Spread (2)
            "spread_bps", "spread_change",
            # Imbalance (5)
            "obi_L1", "obi_L5", "obi_L10", "obi_L25", "obi_L1_delta",
            # Depth (5)
            "bid_depth_L5", "ask_depth_L5", "bid_depth_L25", "ask_depth_L25",
            "depth_ratio_L5",
            # Pressure (3)
            "weighted_price_bid_L10", "weighted_price_ask_L10", "price_pressure",
            # Volatility (3)
            "realized_vol_30s", "realized_vol_60s", "realized_vol_300s",
            # Microstructure (2)
            "kyle_lambda_30s", "amihud_30s",
            # Slopes (2)
            "bid_slope_L10", "ask_slope_L10",
            # Concentration (2)
            "bid_concentration", "ask_concentration",
            # Per-level ratios (10)
            "bid_amt_ratio_L0", "ask_amt_ratio_L0",
            "bid_amt_ratio_L1", "ask_amt_ratio_L1",
            "bid_amt_ratio_L2", "ask_amt_ratio_L2",
            "bid_amt_ratio_L3", "ask_amt_ratio_L3",
            "bid_amt_ratio_L4", "ask_amt_ratio_L4",
            # Temporal (2)
            "second_of_day_sin", "second_of_day_cos",
            # Order flow (5)
            "delta_bid_depth_L5", "delta_ask_depth_L5",
            "net_order_flow_L5", "delta_obi_L5_5s", "delta_pressure_5s",
        ]

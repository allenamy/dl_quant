"""Bar 5-level raw-LOB tensor extractor (Path B) for multi-asset DL.

Replicates the single-asset learned-encoder input
(`src/features/raw_lob.py::extract_raw_lob_tensor`) so a fair dual-path model can
be trained on bar data. Per orderbook level the 4 channels are, in order:

    [bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt]

    bid_delta_bps = (bid_price[i] - mid) / mid * 1e4   (<= 0 for a normal book)
    bid_log_amt   = log1p(bid_size[i])
    ask_delta_bps = (ask_price[i] - mid) / mid * 1e4   (>= 0)
    ask_log_amt   = log1p(ask_size[i])

This matches the single-asset channel convention, sign, and log1p exactly. Two
deliberate divergences from the single-asset reference (bar-data specifics):

  - `mid` is read from the `mid` COLUMN of the bar panel (bar data carries an
    explicit mid) rather than recomputed as (best_bid + best_ask) / 2.
  - leading-NaN rows (mid NaN during warmup) are LEFT as NaN so downstream masks
    can drop them. The single-asset path nan_to_num's them to 0; here we do NOT,
    so a masked/NaN-aware trainer never sees fabricated zeros.

Strictly per-bar (naturally causal — only bar t's own snapshot is used; no
temporal mixing). Columns are consumed BY NAME via `panel.cols.index(...)`.
QTY (size) columns arrive already scaled by the loader.
"""
from __future__ import annotations

import numpy as np

# 5-level LOB column names (level 0 has no suffix in the bar schema).
_BID_PX = ["bid", "bid_1", "bid_2", "bid_3", "bid_4"]
_ASK_PX = ["ask", "ask_1", "ask_2", "ask_3", "ask_4"]
_BID_SZ = ["bidsz", "bidsz_1", "bidsz_2", "bidsz_3", "bidsz_4"]
_ASK_SZ = ["asksz", "asksz_1", "asksz_2", "asksz_3", "asksz_4"]

N_LEVELS = 5


def build_raw_lob_tensor(panel, sym: str) -> np.ndarray:
    """Build the (T, 5, 4) raw-LOB tensor for `sym` from a bar `DayPanel`.

    Parameters
    ----------
    panel : DayPanel
        From `bar_loader.load_day_panel`. Columns consumed by name.
    sym : str
        Symbol to extract (must be present in `panel.data`).

    Returns
    -------
    np.ndarray, shape (T, 5, 4), float32
        Channels per level: [bid_delta_bps, bid_log_amt, ask_delta_bps,
        ask_log_amt]. Rows whose `mid` is NaN propagate NaN in the price-delta
        channels; rows with a NaN size propagate NaN in that level's log-amt
        channel. Nothing is fabricated to 0.
    """
    arr = panel.data[sym]
    cols = panel.cols
    T = arr.shape[0]

    def col(name: str) -> np.ndarray:
        return arr[:, cols.index(name)].astype(np.float64)

    mid = col("mid")  # (T,)
    mid_col = mid[:, np.newaxis]  # (T, 1) for broadcasting

    # Stack the 5 levels: (T, 5) per quantity.
    bid_px = np.column_stack([col(c) for c in _BID_PX])  # (T, 5)
    ask_px = np.column_stack([col(c) for c in _ASK_PX])
    bid_sz = np.column_stack([col(c) for c in _BID_SZ])
    ask_sz = np.column_stack([col(c) for c in _ASK_SZ])

    # Price deltas in bps from mid (NaN mid -> NaN here, by design).
    bid_delta_bps = (bid_px - mid_col) / mid_col * 1e4
    ask_delta_bps = (ask_px - mid_col) / mid_col * 1e4

    # log1p amounts. Clamp negatives to 0 (matches single-asset reference) but
    # leave NaN as NaN so warmup/bad cells stay maskable (np.maximum propagates
    # NaN, unlike np.fmax which would silently fabricate 0).
    bid_log_amt = np.log1p(np.maximum(bid_sz, 0.0))
    ask_log_amt = np.log1p(np.maximum(ask_sz, 0.0))

    tensor = np.stack(
        [bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt],
        axis=-1,
    )  # (T, 5, 4)

    return tensor.astype(np.float32)

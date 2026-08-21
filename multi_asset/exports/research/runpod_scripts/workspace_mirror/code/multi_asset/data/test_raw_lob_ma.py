"""Tests for the bar 5-level raw-LOB tensor extractor (Path B).

TDD-first. Mirrors the single-asset `src/features/raw_lob.py::extract_raw_lob_tensor`
channel convention exactly: per level the 4 channels are
    [bid_delta_bps, bid_log_amt, ask_delta_bps, ask_log_amt]
with delta_bps = (price - mid) / mid * 1e4 and log_amt = log1p(size).

Two divergences from the single-asset reference, BY TASK SPEC:
  - mid comes from the `mid` COLUMN (bar data carries it) rather than being
    recomputed from (best_bid+best_ask)/2.
  - leading-NaN (mid NaN) rows are LEFT as NaN — downstream masks them — instead
    of being nan_to_num'd to 0. (The single-asset path zeroes them.)

Runs without the share mount: synthetic panel mimics the bar schema. A real-day
smoke test is opt-in via env MA_RAWLOB_REAL_DAY=YYYYMMDD (jpline only).

    python3 -m pytest multi_asset/data/test_raw_lob_ma.py -v
"""
from __future__ import annotations

import os

import numpy as np
import pytest

from multi_asset.data.bar_loader import FEATURE_COLUMNS, DayPanel
from multi_asset.data.raw_lob_ma import build_raw_lob_tensor

SYM = "bnfbtc"

_BID_PX = ["bid", "bid_1", "bid_2", "bid_3", "bid_4"]
_ASK_PX = ["ask", "ask_1", "ask_2", "ask_3", "ask_4"]
_BID_SZ = ["bidsz", "bidsz_1", "bidsz_2", "bidsz_3", "bidsz_4"]
_ASK_SZ = ["asksz", "asksz_1", "asksz_2", "asksz_3", "asksz_4"]


# ---------------------------------------------------------------------------
# Synthetic panel fixtures
# ---------------------------------------------------------------------------

def _make_synthetic_panel(T: int = 2000, seed: int = 0, leading_nan: int = 3) -> DayPanel:
    """Single-symbol synthetic panel with the real 57-column schema.

    A normal book: bids below mid, asks above, |distance| grows with level.
    Leading rows are NaN to mimic warmup.
    """
    rng = np.random.default_rng(seed)
    cols = FEATURE_COLUMNS
    arr = np.empty((T, len(cols)), dtype=np.float64)

    mid = 50000.0 + np.cumsum(rng.normal(0, 0.5, size=T))
    half_spread = 0.5

    def put(name, vals):
        arr[:, cols.index(name)] = vals

    put("mid", mid)
    for lvl in range(5):
        # bids: 1 tick below best, descending; asks: 1 tick above, ascending
        put(_BID_PX[lvl], mid - half_spread - lvl)
        put(_ASK_PX[lvl], mid + half_spread + lvl)
        szb = np.abs(rng.normal(10.0, 2.0, T)) * (0.8 ** lvl) + 1.0
        sza = np.abs(rng.normal(10.0, 2.0, T)) * (0.8 ** lvl) + 1.0
        put(_BID_SZ[lvl], szb)
        put(_ASK_SZ[lvl], sza)

    # fill the rest of the schema with benign finite values so the array is well-formed
    for c in cols:
        if c in (_BID_PX + _ASK_PX + _BID_SZ + _ASK_SZ + ["mid"]):
            continue
        arr[:, cols.index(c)] = 1.0

    arr[:leading_nan, :] = np.nan

    return DayPanel(symbols=[SYM], ts=np.arange(T, dtype=np.int64) * 1_000_000_000,
                    data={SYM: arr}, cols=list(cols))


@pytest.fixture
def panel():
    return _make_synthetic_panel(T=2000, seed=7, leading_nan=3)


# ---------------------------------------------------------------------------
# 1. Shape
# ---------------------------------------------------------------------------

def test_shape(panel):
    tens = build_raw_lob_tensor(panel, SYM)
    T = panel.data[SYM].shape[0]
    assert tens.shape == (T, 5, 4), f"expected (T,5,4) got {tens.shape}"
    assert tens.dtype == np.float32


# ---------------------------------------------------------------------------
# 2. Channel correctness — exact values on a hand-built bar
# ---------------------------------------------------------------------------

def test_channel_exact_values():
    """Known book -> assert exact channel values per the single-asset formula."""
    cols = FEATURE_COLUMNS
    T = 4
    arr = np.zeros((T, len(cols)), dtype=np.float64)

    def put(name, vals):
        arr[:, cols.index(name)] = vals

    mid = np.array([10000.0, 10000.0, 10000.0, 10000.0])
    put("mid", mid)
    # craft known per-level prices/sizes (same every row for simplicity)
    bid_px = [9999.0, 9998.0, 9997.0, 9996.0, 9995.0]
    ask_px = [10001.0, 10002.0, 10003.0, 10004.0, 10005.0]
    bid_sz = [5.0, 4.0, 3.0, 2.0, 1.0]
    ask_sz = [6.0, 5.0, 4.0, 3.0, 2.0]
    for lvl in range(5):
        put(_BID_PX[lvl], np.full(T, bid_px[lvl]))
        put(_ASK_PX[lvl], np.full(T, ask_px[lvl]))
        put(_BID_SZ[lvl], np.full(T, bid_sz[lvl]))
        put(_ASK_SZ[lvl], np.full(T, ask_sz[lvl]))

    panel = DayPanel(symbols=[SYM], ts=np.arange(T, dtype=np.int64),
                     data={SYM: arr}, cols=list(cols))
    tens = build_raw_lob_tensor(panel, SYM)

    for lvl in range(5):
        exp_bid_bps = (bid_px[lvl] - 10000.0) / 10000.0 * 1e4
        exp_ask_bps = (ask_px[lvl] - 10000.0) / 10000.0 * 1e4
        exp_bid_amt = np.log1p(bid_sz[lvl])
        exp_ask_amt = np.log1p(ask_sz[lvl])
        # check across all rows
        np.testing.assert_allclose(tens[:, lvl, 0], exp_bid_bps, rtol=0, atol=1e-4)
        np.testing.assert_allclose(tens[:, lvl, 1], exp_bid_amt, rtol=0, atol=1e-6)
        np.testing.assert_allclose(tens[:, lvl, 2], exp_ask_bps, rtol=0, atol=1e-4)
        np.testing.assert_allclose(tens[:, lvl, 3], exp_ask_amt, rtol=0, atol=1e-6)


# ---------------------------------------------------------------------------
# 3. Monotonic-levels sanity — normal book sign + magnitude growth
# ---------------------------------------------------------------------------

def test_monotonic_levels(panel):
    tens = build_raw_lob_tensor(panel, SYM)
    # use a healthy interior row (post-warmup)
    row = tens[1000]
    bid_bps = row[:, 0]
    ask_bps = row[:, 2]
    # bids below mid -> <= 0 ; asks above -> >= 0
    assert (bid_bps <= 0).all(), f"bid_delta_bps must be <=0, got {bid_bps}"
    assert (ask_bps >= 0).all(), f"ask_delta_bps must be >=0, got {ask_bps}"
    # |delta| grows (strictly here, our book steps 1 tick per level) with level
    assert np.all(np.diff(np.abs(bid_bps)) > 0), "bid |delta| must grow with level"
    assert np.all(np.diff(np.abs(ask_bps)) > 0), "ask |delta| must grow with level"


# ---------------------------------------------------------------------------
# 4. NaN passthrough — mid NaN row stays NaN, no crash
# ---------------------------------------------------------------------------

def test_nan_passthrough(panel):
    tens = build_raw_lob_tensor(panel, SYM)
    # leading_nan=3 -> rows 0,1,2 have NaN mid -> price-delta channels NaN
    nan_block = tens[:3]
    assert np.isnan(nan_block).any(), "leading NaN rows should propagate NaN, not 0"
    # specifically the price-delta channels (0 and 2) must be NaN where mid is NaN
    assert np.isnan(tens[:3, :, 0]).all()
    assert np.isnan(tens[:3, :, 2]).all()
    # healthy rows are finite
    assert np.isfinite(tens[1000]).all()


def test_nan_does_not_crash_on_size_nan():
    """A NaN size on an otherwise valid row must not crash; log1p(NaN)=NaN passes."""
    cols = FEATURE_COLUMNS
    T = 5
    arr = np.ones((T, len(cols)), dtype=np.float64)
    arr[:, cols.index("mid")] = 100.0
    for lvl in range(5):
        arr[:, cols.index(_BID_PX[lvl])] = 100.0 - 1 - lvl
        arr[:, cols.index(_ASK_PX[lvl])] = 100.0 + 1 + lvl
        arr[:, cols.index(_BID_SZ[lvl])] = 2.0
        arr[:, cols.index(_ASK_SZ[lvl])] = 2.0
    arr[2, cols.index("bidsz")] = np.nan  # one bad size cell
    panel = DayPanel(symbols=[SYM], ts=np.arange(T, dtype=np.int64),
                     data={SYM: arr}, cols=list(cols))
    tens = build_raw_lob_tensor(panel, SYM)  # must not raise
    assert np.isnan(tens[2, 0, 1])           # bid_log_amt at level 0 NaN
    assert np.isfinite(tens[2, 0, 0])        # but price delta still finite


# ---------------------------------------------------------------------------
# Optional: real-day smoke (jpline only)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not os.environ.get("MA_RAWLOB_REAL_DAY"),
                    reason="set MA_RAWLOB_REAL_DAY=YYYYMMDD on jpline to run")
def test_real_day_smoke():
    from multi_asset.data.bar_loader import load_day_panel
    date = int(os.environ["MA_RAWLOB_REAL_DAY"])
    dp = load_day_panel(date, [SYM])
    tens = build_raw_lob_tensor(dp, SYM)
    T = dp.data[SYM].shape[0]
    assert tens.shape == (T, 5, 4)
    # post-warmup rows finite
    finite_rows = np.isfinite(tens).all(axis=(1, 2))
    assert finite_rows[300:].mean() > 0.99
    print(f"\nreal-day {date}: T={T}, shape={tens.shape}, "
          f"finite_frac_after_warmup={finite_rows[300:].mean():.4f}")

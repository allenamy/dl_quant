"""Tests for the windowed-NPZ builder (single-asset-format dual-path NPZ).

Covers the three contracts the task requires:

  1. SHAPE — output keys + shapes match the single-asset format the proven
     REG_arch trainer (`src/training/dataset.py::LOBDatasetV2`) consumes:
        X (N, 600, 47), X_raw (N, 600, 5, 4), y_600 (N,), y_mask_600 (N,),
        regime_prior (N, 6), timestamps (N,), features (47,), aliases y/y_mask.

  2. LEAKAGE (critical) — window i's X/X_raw use ONLY bars <= its pred-index;
     y_600 uses ONLY bars > its pred-index (the forward horizon). We perturb a
     single future bar and assert:
        (a) every window whose pred-index < the perturbed bar has IDENTICAL
            X and X_raw (no future bar leaked into the lookback);
        (b) an earlier window's y_600 is UNAFFECTED by bars strictly after its
            own y-horizon (target_idx).

  3. ALIGNMENT — each window's stored timestamp equals the bar timestamp at its
     pred-index, and y_600 equals log(mid[pred_idx+600]/mid[pred_idx]).

Runs WITHOUT the share mount (synthetic panel mirrors the 57-col bar schema).
Importing the builder pulls in `bar_loader` (h5py) at module top, so these
tests require h5py to be importable (true on jpline env hsy_v5push).

    python3 -m pytest multi_asset/data/test_windowed_npz.py -v
"""
from __future__ import annotations

import numpy as np
import pytest

from multi_asset.data.bar_loader import FEATURE_COLUMNS, DayPanel
from multi_asset.data.build_windowed_npz import (
    INPUT_LEN,
    STRIDE,
    build_day_npz,
)
from multi_asset.data.features_ma import HORIZON

SYM = "bnfbtc"

_BID_PX = ["bid", "bid_1", "bid_2", "bid_3", "bid_4"]
_ASK_PX = ["ask", "ask_1", "ask_2", "ask_3", "ask_4"]
_BID_SZ = ["bidsz", "bidsz_1", "bidsz_2", "bidsz_3", "bidsz_4"]
_ASK_SZ = ["asksz", "asksz_1", "asksz_2", "asksz_3", "asksz_4"]

_NS_PER_SEC = 1_000_000_000


# ---------------------------------------------------------------------------
# Synthetic bar panel (full 57-col schema, normal book, 1s ns grid)
# ---------------------------------------------------------------------------

def _make_panel(T: int, seed: int = 0) -> DayPanel:
    """Single-symbol synthetic panel with the real bar schema and a random-walk
    mid so log-returns / features are non-degenerate. All cells finite (no
    warmup NaNs) so masks are driven purely by the forward-horizon range."""
    rng = np.random.default_rng(seed)
    cols = FEATURE_COLUMNS
    arr = np.empty((T, len(cols)), dtype=np.float64)
    mid = 50000.0 + np.cumsum(rng.normal(0.0, 1.0, size=T))

    def put(name, vals):
        arr[:, cols.index(name)] = vals

    put("mid", mid)
    put("vwap", mid + rng.normal(0.0, 0.2, T))
    put("twap", mid + rng.normal(0.0, 0.2, T))
    for lvl in range(5):
        put(_BID_PX[lvl], mid - 0.5 - lvl)
        put(_ASK_PX[lvl], mid + 0.5 + lvl)
        put(_BID_SZ[lvl], np.abs(rng.normal(10.0, 2.0, T)) * (0.8 ** lvl) + 1.0)
        put(_ASK_SZ[lvl], np.abs(rng.normal(10.0, 2.0, T)) * (0.8 ** lvl) + 1.0)
    # fill remaining schema columns with benign positive finite values
    done = set(_BID_PX + _ASK_PX + _BID_SZ + _ASK_SZ + ["mid", "vwap", "twap"])
    for c in cols:
        if c in done:
            continue
        arr[:, cols.index(c)] = np.abs(rng.normal(5.0, 1.0, T)) + 1.0

    ts = (1_700_000_000 * _NS_PER_SEC) + np.arange(T, dtype=np.int64) * _NS_PER_SEC
    return DayPanel(symbols=[SYM], ts=ts, data={SYM: arr}, cols=list(cols))


# A day must be long enough for at least a couple of windows WITH a valid
# forward label: need n_total > input_len + horizon. Use a comfortable margin.
_T = INPUT_LEN + HORIZON + 3 * STRIDE + 200  # 1664


@pytest.fixture
def panel():
    return _make_panel(_T, seed=7)


# ---------------------------------------------------------------------------
# 1. SHAPE / KEYS — single-asset format
# ---------------------------------------------------------------------------

def test_keys_and_shapes(panel):
    out = build_day_npz(panel, SYM)
    n_total = panel.data[SYM].shape[0]
    n_win = len(range(0, n_total - INPUT_LEN + 1, STRIDE))

    # exact key set the trainer expects
    expected_keys = {
        "X", "X_raw", "timestamps", "features", "horizons_sec",
        "y_600", "y_mask_600", "y", "y_mask", "regime_prior",
    }
    assert set(out.keys()) == expected_keys, set(out.keys()) ^ expected_keys

    assert out["X"].shape == (n_win, INPUT_LEN, 47)
    assert out["X_raw"].shape == (n_win, INPUT_LEN, 5, 4)
    assert out["timestamps"].shape == (n_win,)
    assert out["y_600"].shape == (n_win,)
    assert out["y_mask_600"].shape == (n_win,)
    assert out["regime_prior"].shape == (n_win, 6)
    assert out["features"].shape == (47,)
    assert list(out["horizons_sec"]) == [HORIZON]

    # dtypes mirror single-asset quantize_features=True
    assert out["X"].dtype == np.float32
    assert out["X_raw"].dtype == np.float16
    assert out["timestamps"].dtype == np.int64
    assert out["y_600"].dtype == np.float32
    assert out["y_mask_600"].dtype == np.uint8
    assert out["regime_prior"].dtype == np.float32

    # back-compat aliases are the same arrays (values)
    np.testing.assert_array_equal(out["y"], out["y_600"])
    np.testing.assert_array_equal(out["y_mask"], out["y_mask_600"])

    # X/X_raw finite (sanitized); at least one valid label exists
    assert np.isfinite(out["X"]).all()
    assert np.isfinite(out["X_raw"].astype(np.float32)).all()
    assert int(out["y_mask_600"].sum()) >= 1


def test_no_quantize_keeps_x_raw_float32(panel):
    out = build_day_npz(panel, SYM, quantize=False)
    assert out["X_raw"].dtype == np.float32


# ---------------------------------------------------------------------------
# 2. ALIGNMENT — timestamp + label match the bar at pred-index
# ---------------------------------------------------------------------------

def test_alignment_timestamp_and_label(panel):
    out = build_day_npz(panel, SYM)
    n_total = panel.data[SYM].shape[0]
    mid = panel.data[SYM][:, panel.cols.index("mid")]
    starts = list(range(0, n_total - INPUT_LEN + 1, STRIDE))

    for win_i, start in enumerate(starts):
        pred_idx = start + INPUT_LEN - 1
        # timestamp at the window == bar ts at pred_idx
        assert int(out["timestamps"][win_i]) == int(panel.ts[pred_idx])
        target_idx = pred_idx + HORIZON
        if int(out["y_mask_600"][win_i]) == 1:
            expected = float(np.log(mid[target_idx] / mid[pred_idx]))
            np.testing.assert_allclose(
                float(out["y_600"][win_i]), expected, rtol=0, atol=1e-6
            )
        else:
            # masked windows carry y=0 and must be beyond the forward range
            assert float(out["y_600"][win_i]) == 0.0
            assert target_idx >= n_total


def test_mask_zero_for_windows_without_forward_horizon(panel):
    """The last windows (pred_idx + 600 >= n_total) must be masked out."""
    out = build_day_npz(panel, SYM)
    n_total = panel.data[SYM].shape[0]
    starts = list(range(0, n_total - INPUT_LEN + 1, STRIDE))
    for win_i, start in enumerate(starts):
        pred_idx = start + INPUT_LEN - 1
        if pred_idx + HORIZON >= n_total:
            assert int(out["y_mask_600"][win_i]) == 0


# ---------------------------------------------------------------------------
# 3. LEAKAGE (critical) — future bars never touch a past window's X/X_raw,
#    and bars after a window's y-horizon never touch its y_600.
# ---------------------------------------------------------------------------

def test_future_bar_does_not_leak_into_past_window_inputs(panel):
    """Perturb ONE future bar's mid/sizes; every window whose pred-index is
    strictly before that bar must have BYTE-IDENTICAL X and X_raw."""
    base = build_day_npz(panel, SYM)
    n_total = panel.data[SYM].shape[0]
    starts = list(range(0, n_total - INPUT_LEN + 1, STRIDE))

    # pick a perturbation bar near the end (well after the first windows' inputs)
    perturb_bar = n_total - 50
    pert = DayPanel(
        symbols=[SYM],
        ts=panel.ts.copy(),
        data={SYM: panel.data[SYM].copy()},
        cols=list(panel.cols),
    )
    arr = pert.data[SYM]
    # large perturbation to mid + all top-of-book sizes at that single bar
    arr[perturb_bar, pert.cols.index("mid")] += 500.0
    for c in _BID_SZ + _ASK_SZ + _BID_PX + _ASK_PX:
        arr[perturb_bar, pert.cols.index(c)] += 500.0

    out = build_day_npz(pert, SYM)

    checked = 0
    for win_i, start in enumerate(starts):
        pred_idx = start + INPUT_LEN - 1
        if pred_idx < perturb_bar:
            # this window's lookback is [pred_idx-599, pred_idx], all < perturb_bar
            np.testing.assert_array_equal(
                base["X"][win_i], out["X"][win_i],
                err_msg=f"X leaked future bar into window {win_i} "
                        f"(pred_idx={pred_idx} < perturb_bar={perturb_bar})",
            )
            np.testing.assert_array_equal(
                base["X_raw"][win_i], out["X_raw"][win_i],
                err_msg=f"X_raw leaked future bar into window {win_i}",
            )
            checked += 1
    assert checked >= 2, f"leakage test was vacuous (checked={checked})"


def test_bars_after_y_horizon_do_not_affect_label(panel):
    """A window's y_600 = log(mid[pred+600]/mid[pred]). Perturbing a bar STRICTLY
    after that window's target_idx must leave its y_600 unchanged; perturbing the
    target bar itself MUST change it (sanity that the test can detect leakage)."""
    base = build_day_npz(panel, SYM)
    n_total = panel.data[SYM].shape[0]
    starts = list(range(0, n_total - INPUT_LEN + 1, STRIDE))

    # earliest window (its target_idx is far from the day end -> bars after exist)
    win_i = 0
    start = starts[win_i]
    pred_idx = start + INPUT_LEN - 1
    target_idx = pred_idx + HORIZON
    assert target_idx + 5 < n_total, "need bars strictly after the y-horizon"

    # (a) perturb a bar AFTER target_idx -> y_600[win_i] unchanged
    after = DayPanel(symbols=[SYM], ts=panel.ts.copy(),
                     data={SYM: panel.data[SYM].copy()}, cols=list(panel.cols))
    after.data[SYM][target_idx + 5, after.cols.index("mid")] += 1000.0
    out_after = build_day_npz(after, SYM)
    np.testing.assert_array_equal(
        base["y_600"][win_i], out_after["y_600"][win_i],
        err_msg="bar after y-horizon leaked into y_600",
    )

    # (b) perturb the target bar itself -> y_600[win_i] MUST change (test is live)
    on = DayPanel(symbols=[SYM], ts=panel.ts.copy(),
                  data={SYM: panel.data[SYM].copy()}, cols=list(panel.cols))
    on.data[SYM][target_idx, on.cols.index("mid")] += 1000.0
    out_on = build_day_npz(on, SYM)
    assert float(out_on["y_600"][win_i]) != float(base["y_600"][win_i]), \
        "perturbing the target bar did not change y_600 — test cannot detect leakage"


def test_regime_prior_is_causal(panel):
    """regime_prior at a window's pred-index must not change when a strictly
    later bar is perturbed (the 6-dim context is built from trailing windows)."""
    base = build_day_npz(panel, SYM)
    n_total = panel.data[SYM].shape[0]
    starts = list(range(0, n_total - INPUT_LEN + 1, STRIDE))

    perturb_bar = n_total - 30
    pert = DayPanel(symbols=[SYM], ts=panel.ts.copy(),
                    data={SYM: panel.data[SYM].copy()}, cols=list(panel.cols))
    pert.data[SYM][perturb_bar, pert.cols.index("mid")] += 1000.0
    out = build_day_npz(pert, SYM)

    for win_i, start in enumerate(starts):
        pred_idx = start + INPUT_LEN - 1
        if pred_idx < perturb_bar:
            np.testing.assert_array_equal(
                base["regime_prior"][win_i], out["regime_prior"][win_i],
                err_msg=f"regime_prior leaked future bar into window {win_i}",
            )

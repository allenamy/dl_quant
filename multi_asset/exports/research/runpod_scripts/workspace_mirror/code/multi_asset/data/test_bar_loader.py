"""Tests for the read-only multi-asset bar loader (Task 0.3).

Run on the jpline server (data + h5py live there):
    python3 -m pytest multi_asset/data/test_bar_loader.py -v
"""
import numpy as np

from multi_asset.data.bar_loader import load_day_panel


def test_load_day_panel_shapes():
    syms = ["bnfbtc", "bnfeth"]
    panel = load_day_panel(20250105, syms)
    assert set(panel.symbols) == set(syms)
    assert panel.ts.shape[0] == panel.data["bnfbtc"].shape[0]   # time aligned
    assert panel.ts.shape[0] > 80000                            # ~85800 bars/day
    assert (panel.ts == panel.ts_for("bnfeth")).all()           # SAME grid across symbols


def test_columns_correct():
    """cols names the 57 real feature columns (leading 'index' excluded), and
    every per-symbol array has exactly that many columns in that order."""
    syms = ["bnfbtc", "bnfeth"]
    panel = load_day_panel(20250105, syms)

    # 58 BAR_COLUMNS minus the leading row-index column = 57 features.
    assert len(panel.cols) == 57
    assert "index" not in panel.cols
    # spot-check a few expected feature names are present and ordered as in schema.
    assert panel.cols[0] == "open"
    assert "mid" in panel.cols
    assert "vwap" in panel.cols
    for sym in syms:
        assert panel.data[sym].shape[1] == len(panel.cols)


def test_nan_handling_and_qty_scaling():
    """Leading bars may be NaN -> exposed as NaN, no crash; a mid-day mid is finite.
    QTY columns are scaled by 1 / QTY_MULTIPLIER[sym] exactly like the share loader."""
    syms = ["bnfbtc"]
    panel = load_day_panel(20250105, syms)
    arr = panel.data["bnfbtc"]
    mid_idx = panel.cols.index("mid")

    # leading bar(s) NaN, exposed (not crashed / not filled)
    assert np.isnan(arr[0, mid_idx])
    # a mid-day index is finite
    assert np.isfinite(arr[arr.shape[0] // 2, mid_idx])

    # QTY scaling: re-read the raw dataset and confirm divide-by-multiplier semantics.
    import h5py
    from multi_asset.data.bar_loader import _BAR_PATH, _day_file, QTY_MULTIPLIER

    bidsz_idx = panel.cols.index("bidsz")
    with h5py.File(_day_file(_BAR_PATH, 20250105), "r") as f:
        raw_bidsz = f["bidsz_bnfbtc"][:]
    mult = QTY_MULTIPLIER["bnfbtc"]
    loaded = arr[:, bidsz_idx]
    finite = np.isfinite(raw_bidsz) & np.isfinite(loaded)
    assert finite.any()
    np.testing.assert_allclose(loaded[finite], raw_bidsz[finite] / mult, rtol=1e-9)

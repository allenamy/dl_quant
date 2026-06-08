"""Read-only multi-asset 1-second bar loader (Task 0.3).

Reads the share-mounted daily HDF5 bar files and returns a timestamp-synchronized
day panel: one (T, n_cols) array per symbol, all sharing the same 1s timestamp grid.

Data location (READ-ONLY):
    /mnt/storage/share/bar_data/bar_1s/YYYYMMDD/data_YYYY-MM-DD.hdf5
Each daily file has a `time64` dataset (shared timestamps) and one dataset per
(column, symbol) keyed `{col}_{sym}` (e.g. `mid_bnfbtc`).

Why read h5py directly (vs wrapping `load_bar_utils.load_bar`):
    The share `load_bar` returns a long-format multi-symbol DataFrame indexed by
    (date, sym, ts); building our per-symbol (T, n_cols) panel from it would mean
    pivoting it straight back apart. Reading h5py directly is simpler and lets us
    return contiguous numpy arrays. We reproduce the share loader's QTY scaling
    EXACTLY (QTY columns divided by QTY_MULTIPLIER[sym]) so downstream feature
    semantics match the share loader bit-for-bit.

This module only loads a day into a panel. Feature engineering lives elsewhere.
"""
from __future__ import annotations

import os.path as p
from dataclasses import dataclass

import h5py
import numpy as np

# --- Schema mirrored from /mnt/storage/share/bar_data/load_bar_utils.py ---
# Must stay in sync with the share loader; values copied verbatim.

_BAR_PATH = "/mnt/storage/share/bar_data/bar_1s"

# Full 58-column schema. The leading "index" is a row index, not a feature,
# and is excluded from the panel (see FEATURE_COLUMNS below).
BAR_COLUMNS = [
    "index",
    "open", "high", "close", "low",
    "bid", "bid_1", "bid_2", "bid_3", "bid_4",
    "bidsz", "bidsz_1", "bidsz_2", "bidsz_3", "bidsz_4",
    "ask", "ask_1", "ask_2", "ask_3", "ask_4",
    "asksz", "asksz_1", "asksz_2", "asksz_3", "asksz_4",
    "tdCntBuy", "tdCntSell", "tdQtyBuy", "tdQtySell", "tdQtyPxBuy", "tdQtyPxSell",
    "bkAddBid", "bkAddAsk", "bkDelBid", "bkDelAsk",
    "mid", "midChgDn", "midChgUp",
    "cumu_bidsz_dep_0.1", "cumu_bidsz_dep_0.3", "cumu_bidsz_dep_1.0",
    "cumu_bidsz_dep_3.0", "cumu_bidsz_dep_10.0", "cumu_bidsz_dep_30.0",
    "cumu_bidsz_dep_100.0", "cumu_bidsz_dep_300.0", "cumu_bidsz_dep_1000.0",
    "cumu_asksz_dep_0.1", "cumu_asksz_dep_0.3", "cumu_asksz_dep_1.0",
    "cumu_asksz_dep_3.0", "cumu_asksz_dep_10.0", "cumu_asksz_dep_30.0",
    "cumu_asksz_dep_100.0", "cumu_asksz_dep_300.0", "cumu_asksz_dep_1000.0",
    "twap", "vwap",
]

# Real feature columns (axis-1 of each per-symbol array), "index" excluded.
FEATURE_COLUMNS = [c for c in BAR_COLUMNS if c != "index"]

QTY_COLUMNS = frozenset([
    "bidsz", "bidsz_1", "bidsz_2", "bidsz_3", "bidsz_4",
    "asksz", "asksz_1", "asksz_2", "asksz_3", "asksz_4",
    "tdCntBuy", "tdCntSell", "tdQtyBuy", "tdQtySell", "tdQtyPxBuy", "tdQtyPxSell",
    "bkAddBid", "bkAddAsk", "bkDelBid", "bkDelAsk",
    "cumu_bidsz_dep_0.1", "cumu_bidsz_dep_0.3", "cumu_bidsz_dep_1.0",
    "cumu_bidsz_dep_3.0", "cumu_bidsz_dep_10.0", "cumu_bidsz_dep_30.0",
    "cumu_bidsz_dep_100.0", "cumu_bidsz_dep_300.0", "cumu_bidsz_dep_1000.0",
    "cumu_asksz_dep_0.1", "cumu_asksz_dep_0.3", "cumu_asksz_dep_1.0",
    "cumu_asksz_dep_3.0", "cumu_asksz_dep_10.0", "cumu_asksz_dep_30.0",
    "cumu_asksz_dep_100.0", "cumu_asksz_dep_300.0", "cumu_asksz_dep_1000.0",
])

QTY_MULTIPLIER = {
    "bnfbtc": 1000.0, "bnfeth": 1000.0, "bnfsol": 1.0, "bnfbnb": 100.0,
    "bnfxrp": 10.0, "bnfdog": 1.0, "bnfada": 1.0, "bnflink": 100.0,
    "bnfbch": 1000.0, "bnftrx": 1.0, "bnfltc": 1000.0, "bnfdot": 10.0,
    "bnffil": 10.0, "bnfetc": 100.0,
    "bnfbtcusc": 1000.0, "bnfethusc": 1000.0, "bnfsolusc": 100.0,
    "bnfbnbusc": 100.0, "bnfxrpusc": 10.0,
}


def _format_date_int(date_int: int) -> str:
    s = str(date_int)
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def _day_file(bar_path: str, date: int) -> str:
    """Absolute path to the daily HDF5 file for `date` under `bar_path`."""
    return p.join(bar_path, str(date), f"data_{_format_date_int(date)}.hdf5")


@dataclass(frozen=True)
class DayPanel:
    """A timestamp-synchronized cross-section of bars for one trading day.

    symbols : requested symbols, in request order.
    ts      : int64 ns timestamps, the shared 1s grid for the day (shape (T,)).
    data    : symbol -> (T, n_cols) float64 array (n_cols == len(cols)).
    cols    : feature column names, order matching axis-1 of every data array.
    """
    symbols: list[str]
    ts: np.ndarray
    data: dict[str, np.ndarray]
    cols: list[str]

    def ts_for(self, sym: str) -> np.ndarray:
        """Timestamp grid for `sym`. All symbols share the day grid, so this
        returns the same `ts` (after validating `sym` was loaded)."""
        if sym not in self.data:
            raise KeyError(f"symbol {sym!r} not in panel (have {self.symbols})")
        return self.ts


def load_day_panel(date: int, syms: list[str], bar_path: str = _BAR_PATH) -> DayPanel:
    """Load one day of bars for `syms` into a timestamp-synchronized panel.

    Reads the share HDF5 file in mode="r" only. QTY columns are divided by
    QTY_MULTIPLIER[sym], reproducing `load_bar_utils.load_bar_one_day` exactly.
    Leading bars may be NaN (e.g. mid[0]); they are passed through as NaN.

    Parameters
    ----------
    date : int   trading day as YYYYMMDD.
    syms : list[str]   symbols to load (any subset of the project symbols).
    bar_path : str   base dir of the daily HDF5 files (default: the share mount).
    """
    if not syms:
        raise ValueError("syms must be a non-empty list of symbols")

    hdf5_path = _day_file(bar_path, date)
    cols = FEATURE_COLUMNS
    data: dict[str, np.ndarray] = {}

    with h5py.File(hdf5_path, "r") as cfile:
        # int64 ns timestamps — the shared 1s grid for the whole day.
        ts = cfile["time64"][:].astype(np.int64)
        T = ts.shape[0]

        for sym in syms:
            if sym not in QTY_MULTIPLIER:
                raise KeyError(
                    f"symbol {sym!r} has no QTY_MULTIPLIER entry; refusing to "
                    f"load without exact scaling"
                )
            mult = QTY_MULTIPLIER[sym]
            arr = np.empty((T, len(cols)), dtype=np.float64)
            for j, col in enumerate(cols):
                col_dat = cfile[f"{col}_{sym}"][:].astype(np.float64)
                if col in QTY_COLUMNS:
                    col_dat = col_dat / mult
                arr[:, j] = col_dat
            data[sym] = arr

    return DayPanel(symbols=list(syms), ts=ts, data=data, cols=list(cols))

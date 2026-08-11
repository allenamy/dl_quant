"""Shared helpers for the Phase-1 EDA batch (A1/A4/A6/A7).

All analyses share: the 14-symbol universe, the trading-day calendar, a
date-sampling routine, and a clean (non-overlap) y_600 builder. Everything is
read-only over the share mount via `bar_loader.load_day_panel`.
"""
from __future__ import annotations

import os
import os.path as p
from typing import List

import numpy as np

import sys
sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.bar_loader import load_day_panel, _BAR_PATH  # noqa: E402

SYMBOLS: List[str] = [
    "bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
    "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc",
]

BTC = "bnfbtc"

HORIZON = 600  # y_600 forward seconds (1s bars => 600 bars)

EXPORT_DIR = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda"


def list_all_days(bar_path: str = _BAR_PATH) -> List[int]:
    """Sorted list of available trading days (YYYYMMDD int) on the share."""
    days = []
    for name in os.listdir(bar_path):
        if name.isdigit() and len(name) == 8:
            days.append(int(name))
    return sorted(days)


def day_exists(date_int: int, bar_path: str = _BAR_PATH) -> bool:
    s = str(date_int)
    f = p.join(bar_path, s, f"data_{s[:4]}-{s[4:6]}-{s[6:]}.hdf5")
    return p.exists(f)


def sample_days(all_days: List[int], step: int) -> List[int]:
    """Every `step`-th day across the full calendar (deterministic stride)."""
    return all_days[::step]


def sample_days_spread(all_days: List[int], n: int, start=None, end=None) -> List[int]:
    """`n` roughly-evenly-spaced days, optionally within [start, end] (YYYYMMDD ints)."""
    days = [d for d in all_days if (start is None or d >= start) and (end is None or d <= end)]
    if n >= len(days):
        return days
    idx = np.linspace(0, len(days) - 1, n).round().astype(int)
    idx = sorted(set(idx.tolist()))
    return [days[i] for i in idx]


def col(dp, sym, name):
    return dp.data[sym][:, dp.cols.index(name)]


def y600_full(mid: np.ndarray, h: int = HORIZON) -> np.ndarray:
    """Dense forward log-return y[t] = log(mid[t+h]) - log(mid[t]); last h are NaN."""
    y = np.full(mid.shape, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        lm = np.log(mid)
    y[:-h] = lm[h:] - lm[:-h]
    return y


def clean_mask(T: int, h: int = HORIZON, stride: int = None) -> np.ndarray:
    """Boolean mask selecting non-overlap samples: every `stride` bars, valid forward window.
    stride defaults to h (>=horizon => non-overlapping labels)."""
    if stride is None:
        stride = h
    m = np.zeros(T, dtype=bool)
    m[: T - h : stride] = True
    return m


def mad_sigma(x: np.ndarray) -> float:
    """Robust sigma = MAD * 1.4826 (median-centered)."""
    x = x[np.isfinite(x)]
    if x.size == 0:
        return np.nan
    med = np.median(x)
    return float(np.median(np.abs(x - med)) * 1.4826)


def ensure_export_dir():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    return EXPORT_DIR

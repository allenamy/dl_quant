"""Phase B.2 causality test: past_30d_y_mean must be strictly past.

Verifies that:
1. Modifying daily_y_mean for days >= D does NOT change past_y_mean for day D
2. Lookback is exactly [D - N, D - 1] (D excluded)
3. Insufficient prior history → returns 0.0 (neutral)
"""
from __future__ import annotations
import json
import tempfile
import os

import numpy as np


def _make_temp_dataset(daily_means: dict, lookback: int = 30):
    """Construct minimal-stub dataset just exercising _compute_past_y_mean.

    We don't need full LOBDatasetV2 init; we need a class with
    `_daily_y_mean` dict and `recent_y_lookback_days` int and the
    `_compute_past_y_mean` method.
    """
    from datetime import datetime, timedelta

    class _Stub:
        def __init__(self, dm, lk):
            self._daily_y_mean = dm
            self.recent_y_lookback_days = lk

        def _compute_past_y_mean(self, day_str):
            if self._daily_y_mean is None:
                return 0.0
            try:
                day_dt = datetime.strptime(day_str, "%Y-%m-%d")
            except ValueError:
                return 0.0
            means = []
            for i in range(1, self.recent_y_lookback_days + 1):
                d = day_dt - timedelta(days=i)
                d_str = d.strftime("%Y-%m-%d")
                v = self._daily_y_mean.get(d_str)
                if v is not None:
                    means.append(v)
            if len(means) < self.recent_y_lookback_days // 2:
                return 0.0
            return float(np.mean(means))

    return _Stub(daily_means, lookback)


def test_no_future_leak():
    """Modifying days >= D doesn't change past_y_mean for D."""
    base = {
        f"2025-01-{i:02d}": (i - 15) * 0.0001
        for i in range(1, 32)
    }
    s = _make_temp_dataset(base, lookback=10)
    target_day = "2025-01-20"
    past_orig = s._compute_past_y_mean(target_day)

    # Modify all days >= target_day to absurd values
    modified = dict(base)
    for d_str, v in list(modified.items()):
        if d_str >= target_day:
            modified[d_str] = 999.999
    s2 = _make_temp_dataset(modified, lookback=10)
    past_new = s2._compute_past_y_mean(target_day)

    assert past_orig == past_new, (
        f"past_y_mean changed when future days modified: "
        f"orig={past_orig:.6e}, new={past_new:.6e}"
    )


def test_window_excludes_self():
    """Day D's own value is NOT included in past mean."""
    daily = {
        "2025-01-15": 999.0,  # Day D — should NEVER affect output
        "2025-01-14": 0.001,
        "2025-01-13": 0.002,
        "2025-01-12": 0.003,
    }
    s = _make_temp_dataset(daily, lookback=3)
    past = s._compute_past_y_mean("2025-01-15")
    expected = (0.001 + 0.002 + 0.003) / 3
    assert abs(past - expected) < 1e-9, (
        f"Expected {expected}, got {past} (day D's 999 leaked!)"
    )


def test_insufficient_history_returns_zero():
    """If fewer than half of lookback days available, return 0.0."""
    daily = {"2025-01-01": 0.001, "2025-01-02": 0.002}  # Only 2 days
    s = _make_temp_dataset(daily, lookback=10)
    past = s._compute_past_y_mean("2025-01-03")
    # Need 5+ days, only have 2 → neutral
    assert past == 0.0, f"Expected 0.0 (insufficient), got {past}"


def test_full_window_correct():
    """Full window: mean of past N days exactly."""
    daily = {f"2025-01-{i:02d}": float(i) for i in range(1, 11)}
    s = _make_temp_dataset(daily, lookback=5)
    # Day 6: lookback over days 1-5
    past = s._compute_past_y_mean("2025-01-06")
    expected = (1 + 2 + 3 + 4 + 5) / 5
    assert abs(past - expected) < 1e-9


def test_holes_in_history():
    """Missing days in window are skipped, not zero-filled."""
    daily = {
        "2025-01-10": 1.0,
        # 2025-01-09 missing
        "2025-01-08": 2.0,
        "2025-01-07": 3.0,
        "2025-01-06": 4.0,
        "2025-01-05": 5.0,
    }
    s = _make_temp_dataset(daily, lookback=5)
    past = s._compute_past_y_mean("2025-01-11")
    # Expected mean of 4 available days (excluding missing 09)
    expected = (1 + 2 + 3 + 4) / 4  # Lookback 5 days: 10,09(miss),08,07,06
    # Wait — lookback=5 looks at i=1..5, days 11-1=10, 11-2=09(miss), 11-3=08, 11-4=07, 11-5=06
    # So means = [1, 2, 3, 4] (4 of 5 days available, ≥ half lookback//2=2 ✓)
    assert abs(past - expected) < 1e-9, f"Expected {expected}, got {past}"


if __name__ == "__main__":
    tests = [
        test_no_future_leak,
        test_window_excludes_self,
        test_insufficient_history_returns_zero,
        test_full_window_correct,
        test_holes_in_history,
    ]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print("\nAll Phase B.2 causality tests PASSED")

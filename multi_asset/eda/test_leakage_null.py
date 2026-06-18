"""TDD test for multi_asset/eda/leakage_null.py (single-asset perp gate harness).

Two guarantees under test:

1. permute_y_null(pred, y, n): returns the 97.5th-percentile |IC| under y-permutation
   (the null band). A feature is "real" only if |actual IC| exceeds this band.
   - A leak (pred == future y) has |IC| == 1.0 >> null band  -> flagged real.
   - An uninformative feature (pred independent of y) has |IC| within/near the
     null band -> NOT flagged real.

2. shuffle_future_null(build_fn, cut_second): corrupts all raw inputs strictly
   AFTER cut_second, rebuilds via build_fn, and asserts windows whose
   prediction-time <= cut_second are byte-identical.
   - A leaky build (feature at time t peeks at raw input at t+H, i.e. future)
     has its <=cut windows CHANGED by future corruption  -> leakage_free == False.
   - A strictly-past build (feature at t uses only raw inputs <= t) has <=cut
     windows unchanged -> leakage_free == True.

All deterministic (seeded). No data files touched.
"""
from __future__ import annotations

import os.path as _p
import sys

import numpy as np

_REPO = _p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__))))  # repo root
sys.path.insert(0, _REPO)
from multi_asset.eda.leakage_null import permute_y_null, shuffle_future_null


# ----------------------------------------------------------------------------
# permute_y_null
# ----------------------------------------------------------------------------
def test_permute_y_null_flags_leak():
    rng = np.random.default_rng(0)
    y = rng.standard_normal(2000)
    pred_leak = y.copy()  # perfect leak: pred IS the target
    band = permute_y_null(pred_leak, y, n=500)
    actual_ic = abs(np.corrcoef(pred_leak, y)[0, 1])
    assert 0.0 < band < 0.2, f"null band should be small, got {band}"
    assert actual_ic > band, "leak IC (==1.0) must exceed the null band"


def test_permute_y_null_passes_noise():
    rng = np.random.default_rng(1)
    y = rng.standard_normal(2000)
    pred_noise = rng.standard_normal(2000)  # independent of y
    band = permute_y_null(pred_noise, y, n=500)
    actual_ic = abs(np.corrcoef(pred_noise, y)[0, 1])
    # an uninformative feature's IC sits within/near the null band (not above it)
    assert actual_ic <= band, (
        f"noise IC {actual_ic:.4f} must NOT exceed null band {band:.4f}")


def test_permute_y_null_deterministic():
    rng = np.random.default_rng(2)
    y = rng.standard_normal(1000)
    pred = rng.standard_normal(1000)
    b1 = permute_y_null(pred, y, n=300, seed=123)
    b2 = permute_y_null(pred, y, n=300, seed=123)
    assert b1 == b2, "same seed must give identical null band"


# ----------------------------------------------------------------------------
# shuffle_future_null
# ----------------------------------------------------------------------------
# Synthetic raw inputs: a (T,) time series `raw`. A "window" predicts at time t.
# pred_times[i] = t_i. We build features two ways and corrupt raw[t > cut].
T = 400
H = 10  # leak horizon
CUT = 200


def _raw():
    rng = np.random.default_rng(7)
    return rng.standard_normal(T)


def _build_past(raw):
    """LEAKAGE-FREE: feature at t uses only raw[t] and raw[t-1] (strictly <= t).
    Prediction time of window i is t = i. Windows start at index 1."""
    t_idx = np.arange(1, T)
    feat = raw[t_idx] - raw[t_idx - 1]            # uses <= t only
    pred_times = t_idx.astype(np.int64)
    return feat.astype(np.float64), pred_times


def _build_leak(raw):
    """LEAKY: feature at t peeks at raw[t + H] (the future). Same pred_times so
    the <=cut windows are directly comparable to the past build."""
    t_idx = np.arange(1, T - H)
    feat = raw[t_idx + H] - raw[t_idx - 1]        # uses t+H  -> future leak
    pred_times = t_idx.astype(np.int64)
    return feat.astype(np.float64), pred_times


def test_shuffle_future_null_flags_leak():
    raw0 = _raw()
    res = shuffle_future_null(_build_leak, CUT, raw0, seed=11)
    assert res["leakage_free"] is False, (
        "future-peeking build must be caught (<=cut windows change)")
    assert res["n_changed"] > 0


def test_shuffle_future_null_passes_past():
    raw0 = _raw()
    res = shuffle_future_null(_build_past, CUT, raw0, seed=11)
    assert res["leakage_free"] is True, (
        "strictly-past build must pass (<=cut windows byte-identical)")
    assert res["n_changed"] == 0


def test_shuffle_future_null_deterministic():
    raw0 = _raw()
    r1 = shuffle_future_null(_build_past, CUT, raw0, seed=11)
    r2 = shuffle_future_null(_build_past, CUT, raw0, seed=11)
    assert r1 == r2


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print("PASS", fn.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL", fn.__name__, "->", e)
        except Exception as e:  # noqa
            failed += 1
            print("ERROR", fn.__name__, "->", type(e).__name__, e)
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)

"""Leakage / null-band harness for the single-asset perp Ridge gate.

Two independent guards:

* ``permute_y_null(pred, y, n, seed)`` -- the *statistical* null. Under the null
  that ``pred`` carries no information about ``y``, any non-zero sample IC is
  sampling noise. We estimate that noise band by permuting ``y`` ``n`` times and
  returning the 97.5th percentile of ``|IC|`` (two-sided 5% band). A feature is
  "real" iff ``|actual IC| > band``. This is the cheap guard used for the
  prebuilt npz_spot cache (features there are already <= t by construction, so
  there is nothing to shuffle-corrupt -- only "is the IC above chance?" matters).

* ``shuffle_future_null(build_fn, cut_second, raw, seed)`` -- the *causal* null.
  Given a feature-build closure over raw time-indexed inputs, corrupt every raw
  input strictly AFTER ``cut_second``, rebuild, and require that every window
  whose prediction-time is ``<= cut_second`` is byte-identical before vs after.
  If any such window changes, the build peeked into the future -> NOT
  leakage-free. This is the guard you run on any *new* feature builder before it
  is allowed near the model.

Both are deterministic given ``seed``. Pure-numpy, no data files.
"""
from __future__ import annotations

from typing import Callable

import numpy as np


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation on finite pairs; 0.0 if undefined (zero variance)."""
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return 0.0
    a, b = a[m], b[m]
    sa, sb = a.std(), b.std()
    if sa <= 0.0 or sb <= 0.0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


# ---------------------------------------------------------------------------
# statistical null: y-permutation band
# ---------------------------------------------------------------------------
def permute_y_null(pred: np.ndarray, y: np.ndarray, n: int = 500,
                   seed: int = 0, pct: float = 97.5) -> float:
    """97.5th-percentile of ``|Pearson(pred, permuted y)|`` over ``n`` shuffles.

    Returns the (two-sided) null band. Compare ``abs(actual_ic)`` against it:
    the feature carries real, above-chance signal iff it exceeds this value.
    """
    pred = np.asarray(pred, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=np.float64).ravel()
    m = np.isfinite(pred) & np.isfinite(y)
    pred, y = pred[m], y[m]
    if pred.size < 3 or pred.std() <= 0 or y.std() <= 0:
        return float("nan")
    rng = np.random.default_rng(seed)
    ics = np.empty(n, dtype=np.float64)
    yp = y.copy()
    for i in range(n):
        rng.shuffle(yp)
        ics[i] = abs(_pearson(pred, yp))
    return float(np.percentile(ics, pct))


# ---------------------------------------------------------------------------
# causal null: shuffle-the-future
# ---------------------------------------------------------------------------
def _corrupt_future(raw: np.ndarray, cut_second: int, rng) -> np.ndarray:
    """Return a copy of ``raw`` (time on axis 0) with all rows whose time-index
    is strictly greater than ``cut_second`` replaced by seeded Gaussian noise
    scaled to the data's own std (so the corruption is real, not a no-op)."""
    raw = np.asarray(raw)
    out = raw.copy()
    t = np.arange(raw.shape[0])
    fut = t > cut_second
    if not fut.any():
        return out
    scale = float(np.nanstd(raw)) or 1.0
    noise = rng.standard_normal(size=out[fut].shape) * (scale * 10.0 + 1.0)
    # add a large constant offset too, so even sign-blind features must change
    out[fut] = noise + scale * 1000.0
    return out


def shuffle_future_null(build_fn: Callable[[np.ndarray], tuple],
                        cut_second: int, raw: np.ndarray,
                        seed: int = 0) -> dict:
    """Corrupt raw inputs strictly after ``cut_second``, rebuild, and check that
    all windows with prediction-time ``<= cut_second`` are byte-identical.

    ``build_fn(raw) -> (features, pred_times)`` where ``features`` is a 1-D or
    2-D array (one row per window) and ``pred_times`` is the integer
    prediction-time of each window (same length as ``features``' first axis).

    Returns ``{"leakage_free": bool, "n_changed": int, "n_checked": int}``.
    ``leakage_free`` is True iff no ``<= cut_second`` window changed.
    """
    rng = np.random.default_rng(seed)

    feat0, pt0 = build_fn(raw)
    feat0 = np.asarray(feat0)
    pt0 = np.asarray(pt0).ravel()

    raw_c = _corrupt_future(raw, cut_second, rng)
    feat1, pt1 = build_fn(raw_c)
    feat1 = np.asarray(feat1)
    pt1 = np.asarray(pt1).ravel()

    # restrict to windows predicting at <= cut_second; align the two builds by
    # their prediction-time so a length change (e.g. leaky build truncates the
    # tail) does not masquerade as / hide a leak in the protected region.
    keep0 = pt0 <= cut_second
    keep1 = pt1 <= cut_second
    common = np.intersect1d(pt0[keep0], pt1[keep1])
    n_checked = int(common.size)

    # map pred_time -> row index for each build
    idx0 = {int(t): i for i, t in enumerate(pt0)}
    idx1 = {int(t): i for i, t in enumerate(pt1)}

    n_changed = 0
    for t in common:
        r0 = feat0[idx0[int(t)]]
        r1 = feat1[idx1[int(t)]]
        a0 = np.asarray(r0, dtype=np.float64).ravel()
        a1 = np.asarray(r1, dtype=np.float64).ravel()
        # NaNs compare equal here (NaN==NaN -> treat as identical)
        same = np.array_equal(a0, a1) or np.array_equal(
            np.nan_to_num(a0, nan=0.0), np.nan_to_num(a1, nan=0.0))
        if not same:
            n_changed += 1

    return {
        "leakage_free": bool(n_changed == 0),
        "n_changed": int(n_changed),
        "n_checked": int(n_checked),
    }

"""Walk-forward cross-validation for time-series model evaluation.

Standard k-fold CV leaks future information into training and is unsafe
for financial time series. Walk-forward CV slides a train/test window
through time: train on ``[0, t]``, test on ``[t, t + fold_size]``, then
increment ``t``. This gives multiple out-of-sample windows while
preserving strict temporal ordering.

Two entry points:

* ``walk_forward_evaluate`` -- caller supplies a ``predict_fn`` that
  returns ``(pred, target, mask)`` for a given ``(train_end, test_end)``.
  Useful when wrapping existing predictors (Ridge, naive baselines).

* ``evaluate_across_folds`` -- caller supplies a model factory and a
  training function. Used for full train-from-scratch comparison across
  folds with a PyTorch model.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _metric_correlation(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> float:
    """Pearson correlation on masked samples; NaN if either side is constant."""
    mask = np.asarray(mask, dtype=bool).ravel()
    p = np.asarray(pred, dtype=np.float64).ravel()[mask]
    t = np.asarray(target, dtype=np.float64).ravel()[mask]
    if len(p) < 2 or np.std(p) == 0 or np.std(t) == 0:
        return float("nan")
    return float(np.corrcoef(p, t)[0, 1])


def _metric_r2(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> float:
    mask = np.asarray(mask, dtype=bool).ravel()
    p = np.asarray(pred, dtype=np.float64).ravel()[mask]
    t = np.asarray(target, dtype=np.float64).ravel()[mask]
    if len(t) == 0:
        return float("nan")
    ss_res = float(np.sum((t - p) ** 2))
    ss_tot = float(np.sum((t - np.mean(t)) ** 2))
    if ss_tot == 0:
        return float("nan")
    return 1.0 - ss_res / ss_tot


def _build_fold_boundaries(
    n_samples: int,
    n_folds: int,
    fold_size: Optional[int],
    min_train_size: Optional[int],
) -> List[Tuple[int, int]]:
    """Return a list of ``(train_end, test_end)`` index pairs.

    The test windows partition the tail of the dataset; each fold's
    training set is everything from 0 up to that fold's test start.
    """
    if n_folds < 1:
        raise ValueError(f"n_folds must be >= 1, got {n_folds}")
    if n_samples < 2:
        raise ValueError(f"n_samples must be >= 2, got {n_samples}")

    if fold_size is None:
        # Reserve roughly the last ~1/(n_folds+1) of data for each test fold
        fold_size = max(1, n_samples // (n_folds + 1))

    if min_train_size is None:
        min_train_size = max(1, n_samples - fold_size * n_folds)

    min_train_size = max(1, min_train_size)

    boundaries: List[Tuple[int, int]] = []
    for k in range(n_folds):
        train_end = min_train_size + k * fold_size
        test_end = train_end + fold_size
        if train_end >= n_samples:
            break
        if test_end > n_samples:
            test_end = n_samples
        if test_end <= train_end:
            break
        boundaries.append((train_end, test_end))

    if not boundaries:
        raise ValueError(
            f"Cannot build any fold with n_samples={n_samples}, "
            f"n_folds={n_folds}, fold_size={fold_size}, "
            f"min_train_size={min_train_size}"
        )

    return boundaries


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def walk_forward_evaluate(
    predict_fn: Callable[[int, int], Tuple[np.ndarray, np.ndarray, np.ndarray]],
    n_samples: int,
    n_folds: int = 5,
    fold_size: Optional[int] = None,
    min_train_size: Optional[int] = None,
) -> dict:
    """Walk-forward CV: train on ``[0, t]``, test on ``[t, t + fold_size]``,
    slide forward.

    Parameters
    ----------
    predict_fn : callable ``(train_end, test_end) -> (preds, targets, mask)``
        Produces predictions for a single fold. The caller is responsible
        for any model training or feature preparation inside this
        function. Returned arrays must be 1D of length ``test_end - train_end``.
    n_samples : int
        Total number of samples in the dataset.
    n_folds : int
        Number of walk-forward folds.
    fold_size : int, optional
        Number of samples in each test fold. Default reserves roughly
        ``n_samples / (n_folds + 1)`` samples per fold.
    min_train_size : int, optional
        Minimum training-set size for the first fold. Default leaves
        ``n_samples - fold_size * n_folds`` samples for the initial
        training set.

    Returns
    -------
    dict with keys
        ``corrs`` : list[float] -- per-fold correlation
        ``r2s`` : list[float] -- per-fold R^2
        ``mean_corr`` : float
        ``std_corr`` : float
        ``ci_95`` : tuple[float, float] -- mean +/- 1.96 * std/sqrt(n)
        ``fold_boundaries`` : list[(train_end, test_end)]
        ``n_folds`` : int (actual number of folds evaluated)
    """
    boundaries = _build_fold_boundaries(n_samples, n_folds, fold_size, min_train_size)

    corrs: List[float] = []
    r2s: List[float] = []
    for train_end, test_end in boundaries:
        preds, targets, mask = predict_fn(train_end, test_end)
        corrs.append(_metric_correlation(preds, targets, mask))
        r2s.append(_metric_r2(preds, targets, mask))

    valid = [c for c in corrs if not np.isnan(c)]
    mean_corr = float(np.mean(valid)) if valid else float("nan")
    std_corr = float(np.std(valid, ddof=1)) if len(valid) > 1 else float("nan")

    if len(valid) > 1:
        se = std_corr / np.sqrt(len(valid))
        ci_95 = (mean_corr - 1.96 * se, mean_corr + 1.96 * se)
    else:
        ci_95 = (float("nan"), float("nan"))

    return {
        "corrs": corrs,
        "r2s": r2s,
        "mean_corr": mean_corr,
        "std_corr": std_corr,
        "ci_95": ci_95,
        "fold_boundaries": boundaries,
        "n_folds": len(boundaries),
    }


def evaluate_across_folds(
    model_fn: Callable[[], Any],
    dataset: Any,
    train_fn: Callable[[Any, Any, Any], Any],
    predict_fn: Optional[Callable[[Any, Any], Tuple[np.ndarray, np.ndarray, np.ndarray]]] = None,
    n_folds: int = 5,
    fold_size: Optional[int] = None,
    min_train_size: Optional[int] = None,
    val_fraction: float = 0.2,
) -> pd.DataFrame:
    """Run walk-forward CV with a model factory + training function.

    Each fold:

      1. Split data at the fold boundary.
      2. Call ``train_fn(model, train_slice, val_slice) -> trained_model``.
      3. Predict on the test slice via ``predict_fn(model, test_slice)``.
      4. Record metrics.

    Parameters
    ----------
    model_fn : callable ``() -> model``
        Factory producing a fresh model instance for each fold.
    dataset : object with ``__len__`` and ``.X`` / ``.y`` / ``.mask`` attributes
        (e.g. ``LOBDatasetV2``). Must expose ``X`` (N, L, F), ``y`` (N,)
        and ``mask`` (N,) as numpy arrays. A slice object is passed to
        ``train_fn`` / ``predict_fn`` so they can materialise sub-datasets.
    train_fn : callable ``(model, train_slice, val_slice) -> trained_model``
        Trains the model on the train slice (with optional validation
        slice). The returned object is what ``predict_fn`` receives.
    predict_fn : optional callable ``(trained_model, test_slice) -> (preds, y, mask)``
        When ``None``, a default is used that calls
        ``trained_model.predict(X)`` and uses dataset y / mask.
    n_folds, fold_size, min_train_size : see ``walk_forward_evaluate``.
    val_fraction : float
        Fraction of the training slice to hold out as validation.

    Returns
    -------
    pd.DataFrame
        One row per fold with columns: ``fold_id``, ``train_start``,
        ``train_end``, ``test_start``, ``test_end``, ``test_corr``,
        ``test_r2``, ``n_samples``.
    """
    n_samples = len(dataset)
    boundaries = _build_fold_boundaries(n_samples, n_folds, fold_size, min_train_size)

    if predict_fn is None:
        def predict_fn(model, test_slice):  # type: ignore[no-redef]
            X_te = dataset.X[test_slice]
            y_te = dataset.y[test_slice]
            m_te = dataset.mask[test_slice]
            preds = model.predict(X_te)
            return np.asarray(preds), np.asarray(y_te), np.asarray(m_te, dtype=bool)

    rows: List[dict] = []
    for fold_id, (train_end, test_end) in enumerate(boundaries):
        val_size = max(1, int((train_end) * val_fraction))
        val_start = max(0, train_end - val_size)

        train_slice = slice(0, val_start) if val_start > 0 else slice(0, train_end)
        val_slice = slice(val_start, train_end) if val_start > 0 else None
        test_slice = slice(train_end, test_end)

        model = model_fn()
        trained = train_fn(model, train_slice, val_slice)
        preds, targets, mask = predict_fn(trained, test_slice)

        corr = _metric_correlation(preds, targets, mask)
        r2 = _metric_r2(preds, targets, mask)

        rows.append({
            "fold_id": fold_id,
            "train_start": 0,
            "train_end": int(train_end),
            "test_start": int(train_end),
            "test_end": int(test_end),
            "test_corr": corr,
            "test_r2": r2,
            "n_samples": int(test_end - train_end),
        })

    return pd.DataFrame(rows)

"""Signal-verification baseline runner.

This is the Layer-1 entry point of CLAUDE.md: before we invest in deep-learning
architectures, we use the simplest possible models to verify that a signal
exists in our engineered features.  The runner loads all NPZ files from a
directory, performs a single 80 / 10 / 10 *temporal* split, and evaluates:

    - ``RidgeBaseline``          : sklearn Ridge on the last-timestep features.
    - ``TemporalRidgeBaseline``  : Ridge with (last, mean, std, trend)
                                   aggregates across the full window.
    - ``FITSModel``              : tiny frequency-domain net (~26K params).
    - Four naive single-feature baselines (no training): OBI, Momentum,
      Flow, MicropriceDeviation.

The split is strictly chronological: we sort NPZ files by filename (day
stems) and slice by day, then concatenate to samples.  No same-day splits
(CLAUDE.md anti-pattern).

The intent is **signal verification**, not model selection.  If every
baseline delivers ~0 correlation on held-out data, we should stop and
improve features before training the full V3 model.

CLI
---
    python run_baselines.py --npz-dir data/npz_full \\
        --output experiments/v3_full/baselines.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# ``src`` is a top-level package in this repo; make the project root importable
# no matter where the script is launched from.
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.baselines.linear_baseline import RidgeBaseline
from src.baselines.naive_baselines import (
    OBIBaseline,
    MomentumBaseline,
    FlowBaseline,
    MicropriceDeviationBaseline,
)
from src.evaluation.metrics import evaluate_predictions

logger = logging.getLogger("run_baselines")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _day_from_path(path: Path) -> str:
    return path.stem


def _load_single_day(path: Path) -> Dict[str, np.ndarray]:
    """Load one NPZ file.  Returns a dict with numpy arrays (no torch).

    Used only by ``_load_days_full``.  The streaming loaders below read
    per-field slices of the NPZ directly to keep peak memory low.
    """
    with np.load(str(path), allow_pickle=True) as npz:
        fields = set(npz.files)
        out: Dict[str, Any] = {
            "X": npz["X"].astype(np.float32),
            "y": npz["y"].astype(np.float32),
            "y_mask": npz["y_mask"].astype(np.float32),
        }
        if "timestamps" in fields:
            out["timestamps"] = npz["timestamps"]
        if "features" in fields:
            out["features"] = list(npz["features"])
    return out


def _read_features_array(npz) -> Optional[List[str]]:
    """Return the ``features`` list from an opened NPZ, or ``None``."""
    if "features" in npz.files:
        return [str(f) for f in npz["features"]]
    return None


def _check_feature_names(
    existing: Optional[List[str]],
    new_names: Optional[List[str]],
    day: str,
) -> List[str]:
    """Validate per-day feature names against the running reference.

    Raises ``ValueError`` if the new names exist and disagree with the
    reference list.  Returns the effective (possibly first-seen)
    reference list.
    """
    if existing is None:
        return new_names if new_names is not None else existing
    if new_names is None:
        return existing
    if new_names != existing:
        raise ValueError(
            f"Feature-name mismatch in {day}.npz: "
            f"first file has {len(existing)} names, "
            f"this file has {len(new_names)}. "
            f"Rebuild NPZs with a single pipeline version."
        )
    return existing


def _finalise_arrays(
    xs: List[np.ndarray],
    ys: List[np.ndarray],
    ms: List[np.ndarray],
    feature_names: Optional[List[str]],
    feature_dim: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """Concatenate per-day lists and sanitise in place.

    Consolidates the nan-fix / mask-zero step that every loader needs,
    so we don't duplicate it four times.
    """
    X = np.concatenate(xs, axis=0)
    y = np.concatenate(ys, axis=0)
    mask = np.concatenate(ms, axis=0)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    mask = np.nan_to_num(mask, nan=0.0, posinf=0.0, neginf=0.0)
    y[mask == 0] = 0.0
    if feature_names is None:
        feature_names = [f"f{i}" for i in range(feature_dim)]
    return X, y, mask, feature_names


def _resolve_paths(
    npz_dir_or_paths, ctx: str = "loader",
) -> List[Path]:
    """Accept either a directory string or a pre-collected path list.

    When the caller passes a directory we glob + sort.  When they pass a
    list (e.g. a snapshot captured before a sequence of loads) we honour
    the order as-is -- this keeps the three loaders (last / agg / full)
    perfectly in sync even if the underlying directory is being written
    to in the background.
    """
    if isinstance(npz_dir_or_paths, (list, tuple)):
        paths = [Path(p) for p in npz_dir_or_paths]
    else:
        paths = sorted(Path(npz_dir_or_paths).glob("*.npz"))
    if not paths:
        raise FileNotFoundError(f"No .npz files found by {ctx}")
    return paths


def snapshot_npz_paths(npz_dir: str) -> List[Path]:
    """Return a sorted snapshot of the NPZ paths in ``npz_dir``.

    Capturing the list once and reusing it across every loader prevents
    a concurrent data collector from injecting new files between passes
    (which would cause day-count mismatches in the orchestration).
    """
    return _resolve_paths(npz_dir, ctx=f"snapshot({npz_dir})")


def load_last_step_features(
    npz_dir_or_paths,
) -> Tuple[List[str], np.ndarray, np.ndarray, np.ndarray, List[str], List[int]]:
    """Load per-day NPZs and keep only the **last timestep** of each window.

    Memory-efficient variant of ``_load_days_full`` used by baselines that
    never look further back than ``X[:, -1, :]`` (Ridge, XGBoost, naive
    single-feature baselines).  Output ``X`` has shape ``(N, F)`` -- about
    ``L`` times smaller than the full ``(N, L, F)`` tensor.

    Parameters
    ----------
    npz_dir_or_paths : str | list[Path]
        Either a directory (globbed then sorted) or a pre-collected path
        list.  Passing a list keeps repeated loads perfectly in sync
        even when the directory is being written to concurrently.

    Returns
    -------
    days : list[str]
        Day stems in chronological order.
    X : (N, F) float32
    y : (N,) float32
    mask : (N,) float32 (0/1)
    feature_names : list[str]
    per_day_counts : list[int]
    """
    paths = _resolve_paths(npz_dir_or_paths, ctx="load_last_step_features")

    days: List[str] = []
    xs: List[np.ndarray] = []
    ys: List[np.ndarray] = []
    ms: List[np.ndarray] = []
    per_day_counts: List[int] = []
    feature_names: Optional[List[str]] = None

    for path in paths:
        with np.load(str(path), allow_pickle=True) as npz:
            X_full = npz["X"]
            n_win = X_full.shape[0]
            if n_win == 0:
                logger.warning("Day %s has 0 windows, skipping", path.stem)
                continue
            # Explicit copy so the NPZ's mmap/read buffer can be released
            # at context-manager exit; otherwise large per-day views would
            # keep the file open and defeat the memory-saving point.
            X_last = X_full[:, -1, :].astype(np.float32, copy=True)
            y_day = npz["y"].astype(np.float32, copy=True)
            mask_day = npz["y_mask"].astype(np.float32, copy=True)
            new_names = _read_features_array(npz)
        feature_names = _check_feature_names(feature_names, new_names, path.stem)

        days.append(path.stem)
        xs.append(X_last)
        ys.append(y_day)
        ms.append(mask_day)
        per_day_counts.append(int(n_win))

    if not days:
        raise RuntimeError("All NPZ files had 0 windows")

    X, y, mask, feature_names = _finalise_arrays(
        xs, ys, ms, feature_names, feature_dim=xs[0].shape[-1]
    )
    return days, X, y, mask, feature_names, per_day_counts


def load_temporal_features(
    npz_dir_or_paths,
) -> Tuple[List[str], np.ndarray, np.ndarray, np.ndarray, List[str], List[int]]:
    """Load per-day NPZs and compute ``(last, mean, std, trend)`` aggregates.

    Used by ``TemporalRidgeBaseline``.  Output ``X`` has shape ``(N, 4F)``
    -- about ``L/4`` times smaller than the full tensor (e.g. 75x on
    ``L=300``).  Aggregates are computed per day **before** concatenation
    so we never hold the full per-day ``(n_win, L, F)`` slice of more than
    one day simultaneously.

    Parameters
    ----------
    npz_dir_or_paths : str | list[Path]
        Directory string or pre-collected path list (see
        ``load_last_step_features``).

    Returns
    -------
    days : list[str]
    X_agg : (N, 4F) float32
    y : (N,) float32
    mask : (N,) float32
    feature_names : list[str]
        Original F feature names (not the 4F expanded set).  Naive
        baselines use this list to look up columns in the raw NPZ, and
        they are never called on the aggregated tensor.
    per_day_counts : list[int]
    """
    paths = _resolve_paths(npz_dir_or_paths, ctx="load_temporal_features")

    days: List[str] = []
    xs: List[np.ndarray] = []
    ys: List[np.ndarray] = []
    ms: List[np.ndarray] = []
    per_day_counts: List[int] = []
    feature_names: Optional[List[str]] = None

    for path in paths:
        with np.load(str(path), allow_pickle=True) as npz:
            X_full = npz["X"]
            n_win = X_full.shape[0]
            if n_win == 0:
                logger.warning("Day %s has 0 windows, skipping", path.stem)
                continue
            # Force a float32 read for the day's window -- we need the whole
            # (n_win, L, F) slice briefly to compute mean/std, but only for
            # ONE day at a time, and we drop it before reading the next.
            X_day = X_full.astype(np.float32, copy=True)
            last = X_day[:, -1, :]
            mean = X_day.mean(axis=1)
            std = X_day.std(axis=1)
            trend = X_day[:, -1, :] - X_day[:, 0, :]
            X_agg = np.concatenate([last, mean, std, trend], axis=1).astype(
                np.float32, copy=False
            )
            y_day = npz["y"].astype(np.float32, copy=True)
            mask_day = npz["y_mask"].astype(np.float32, copy=True)
            new_names = _read_features_array(npz)
            # Drop the per-day 3D tensor eagerly -- Python will collect
            # it once the with-block exits but we want that to happen
            # before we accumulate the next day.
            del X_day, last, mean, std, trend
        feature_names = _check_feature_names(feature_names, new_names, path.stem)

        days.append(path.stem)
        xs.append(X_agg)
        ys.append(y_day)
        ms.append(mask_day)
        per_day_counts.append(int(n_win))

    if not days:
        raise RuntimeError("All NPZ files had 0 windows")

    X, y, mask, feature_names = _finalise_arrays(
        xs, ys, ms, feature_names, feature_dim=xs[0].shape[-1]
    )
    return days, X, y, mask, feature_names, per_day_counts


def _load_days_full(
    npz_dir_or_paths,
) -> Tuple[List[str], np.ndarray, np.ndarray, np.ndarray, List[str], List[int]]:
    """Load and concatenate the **full** ``(N, L, F)`` NPZ tensor.

    This is the original ``load_days`` behaviour, renamed to emphasise it
    is memory-expensive: ``N * L * F * 4`` bytes.  For the full 1004-day
    run that is ~100 GB which will OOM.  Only FITS needs the raw 3D
    windows; everything else should use ``load_last_step_features`` or
    ``load_temporal_features``.

    Returns ``(days, X, y, mask, feature_names, per_day_counts)`` with
    ``X.shape == (N, L, F)``.
    """
    paths = _resolve_paths(npz_dir_or_paths, ctx="_load_days_full")

    days: List[str] = []
    xs: List[np.ndarray] = []
    ys: List[np.ndarray] = []
    ms: List[np.ndarray] = []
    per_day_counts: List[int] = []
    feature_names: Optional[List[str]] = None

    for path in paths:
        d = _load_single_day(path)
        day = _day_from_path(path)
        n_win = d["X"].shape[0]
        if n_win == 0:
            logger.warning("Day %s has 0 windows, skipping", day)
            continue
        days.append(day)
        xs.append(d["X"])
        ys.append(d["y"])
        ms.append(d["y_mask"])
        per_day_counts.append(n_win)
        new_names = list(d["features"]) if "features" in d else None
        feature_names = _check_feature_names(feature_names, new_names, day)

    if not days:
        raise RuntimeError("All NPZ files had 0 windows")

    X, y, mask, feature_names = _finalise_arrays(
        xs, ys, ms, feature_names, feature_dim=xs[0].shape[-1]
    )
    return days, X, y, mask, feature_names, per_day_counts


# Back-compat alias -- keep the original name callable for tests / scripts
# that imported ``load_days`` before the streaming loaders were introduced.
load_days = _load_days_full


def temporal_split(
    per_day_counts: Sequence[int],
    train_frac: float = 0.80,
    val_frac: float = 0.10,
) -> Tuple[slice, slice, slice]:
    """Produce 3 slices (train / val / test) that split along **day** boundaries.

    Splitting inside a day would mix adjacent windows that share most of
    their look-back (stride << horizon in some setups), an anti-pattern
    flagged in CLAUDE.md.  So we accumulate day-wise sample counts and
    assign whole days to train / val / test.

    Parameters
    ----------
    per_day_counts : sequence of int
        Number of windows per day in chronological order.
    train_frac, val_frac : float
        Fraction of *days* (not samples) assigned to train / val.  Test
        gets the remainder.

    Returns
    -------
    (train_slice, val_slice, test_slice) : 3 ``slice`` objects into the
    concatenated sample axis.
    """
    if not (0.0 < train_frac < 1.0 and 0.0 < val_frac < 1.0):
        raise ValueError("train_frac and val_frac must each be in (0, 1)")
    if train_frac + val_frac >= 1.0:
        raise ValueError("train_frac + val_frac must leave room for test")

    n_days = len(per_day_counts)
    if n_days < 3:
        raise ValueError(
            f"Need at least 3 days for temporal split, got {n_days}"
        )

    # Days per split: ceiling for train to prefer >= requested train fraction.
    n_train_days = max(1, int(round(train_frac * n_days)))
    n_val_days = max(1, int(round(val_frac * n_days)))
    # Ensure at least one test day
    if n_train_days + n_val_days >= n_days:
        n_val_days = max(1, n_days - n_train_days - 1)
    if n_train_days + n_val_days >= n_days:
        n_train_days = max(1, n_days - n_val_days - 1)

    cumulative = [0]
    for c in per_day_counts:
        cumulative.append(cumulative[-1] + int(c))

    train_end = cumulative[n_train_days]
    val_end = cumulative[n_train_days + n_val_days]
    total = cumulative[-1]

    return (
        slice(0, train_end),
        slice(train_end, val_end),
        slice(val_end, total),
    )


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def compute_stats(
    X: np.ndarray, y: np.ndarray, mask: np.ndarray
) -> Dict[str, Any]:
    """Per-feature z-score stats + robust MAD sigma for the target.

    Stats are computed on the *training* portion only (caller passes the
    sliced arrays).  ``mask`` is applied to the target so zero-mask samples
    don't pull the median.

    Accepts both 3D ``(N, L, F)`` windows and 2D ``(N, F)`` last-timestep
    slices so we can share this helper between the full loader and the
    streaming loaders.
    """
    if X.ndim == 3:
        x_mean = X.mean(axis=(0, 1)).astype(np.float32)
        x_std = X.std(axis=(0, 1)).astype(np.float32)
    elif X.ndim == 2:
        x_mean = X.mean(axis=0).astype(np.float32)
        x_std = X.std(axis=0).astype(np.float32)
    else:
        raise ValueError(f"compute_stats expects 2D or 3D X, got shape {X.shape}")

    m = mask.astype(bool)
    y_valid = y[m] if m.any() else y
    y_median = float(np.median(y_valid)) if len(y_valid) > 0 else 0.0
    y_mad = float(np.median(np.abs(y_valid - y_median))) if len(y_valid) > 0 else 0.0
    # 1.4826 converts MAD to a Gaussian-equivalent sigma
    y_sigma = max(1.4826 * y_mad, 1e-9)

    return {
        "x_mean": x_mean,
        "x_std": x_std,
        "y_median": y_median,
        "y_sigma": y_sigma,
    }


def apply_stats(
    X: np.ndarray, y: np.ndarray, stats: Dict[str, Any]
) -> Tuple[np.ndarray, np.ndarray]:
    """Z-score X (with dead-feature guard), MAD-normalise y.

    Broadcasting handles both 2D and 3D X -- ``x_mean`` / ``x_std`` are
    1D over the feature axis, and numpy broadcasts them against a
    trailing-feature axis regardless of whether there's a time axis.
    """
    safe_std = np.where(stats["x_std"] < 1e-4, 1.0, stats["x_std"]).astype(np.float32)
    X_n = (X - stats["x_mean"]) / safe_std
    X_n = np.clip(X_n, -10.0, 10.0).astype(np.float32)

    y_n = ((y - stats["y_median"]) / stats["y_sigma"]).astype(np.float32)
    return X_n, y_n


# ---------------------------------------------------------------------------
# Baseline runners
# ---------------------------------------------------------------------------

def _safe_fit_predict_ridge(
    model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    mask_train: np.ndarray,
    X_test: np.ndarray,
) -> np.ndarray:
    """Fit a Ridge-style baseline on valid-target training samples only."""
    m = mask_train.astype(bool)
    X_tr = X_train[m] if m.any() else X_train
    y_tr = y_train[m] if m.any() else y_train
    if len(X_tr) < 2:
        return np.zeros(len(X_test), dtype=np.float64)
    model.fit(X_tr, y_tr)
    return np.asarray(model.predict(X_test)).ravel().astype(np.float64)


def _score_predictions(
    name: str,
    pred: np.ndarray,
    target: np.ndarray,
    mask: np.ndarray,
    target_sigma: float,
) -> Dict[str, Any]:
    """Compute correlation, R2, score_bps summary for a single model.

    ``score_bps`` is back-scaled from normalized-target R^2 using the
    training-time MAD sigma, so values are directly comparable across
    baselines and easy to sanity-check against the raw target scale.
    """
    metrics = evaluate_predictions(pred, target, mask)
    # Metrics.score_bps uses the std of the normalized test target, which
    # can differ from the training sigma.  Rebuild it on the RAW scale so
    # the units match "BTCUSDT return, bps" intuitively.
    r2 = metrics.get("r2", float("nan"))
    if (not np.isnan(r2)) and target_sigma > 0:
        metrics["score_bps"] = float(np.sqrt(max(r2, 0.0)) * target_sigma * 10000)
    return {
        "model": name,
        "correlation": float(metrics.get("correlation", float("nan"))),
        "rank_correlation": float(metrics.get("rank_correlation", float("nan"))),
        "r2": float(metrics.get("r2", float("nan"))),
        "direction_accuracy": float(metrics.get("direction_accuracy", float("nan"))),
        "residual_autocorr_lag1": float(metrics.get("residual_autocorr_lag1",
                                                    float("nan"))),
        "score_bps": float(metrics.get("score_bps", float("nan"))),
        "n": int(metrics.get("n", 0)),
    }


def _pick_feature(
    wanted: Sequence[str], feature_names: Sequence[str]
) -> Optional[str]:
    """Return the first name in ``wanted`` that appears in ``feature_names``.

    We keep a small compatibility list because historical NPZ schemas use
    both ``net_trade_flow_L5`` and ``net_trade_flow_1s`` etc.  Returning
    ``None`` tells the caller to skip that baseline.
    """
    names = set(feature_names)
    for w in wanted:
        if w in names:
            return w
    return None


def run_naive_baselines(
    X_test: np.ndarray,
    y_test: np.ndarray,
    mask_test: np.ndarray,
    feature_names: Sequence[str],
    target_sigma: float,
) -> List[Dict[str, Any]]:
    """Run each naive baseline, auto-selecting a compatible feature name.

    Returns a list of result dicts (one per baseline).  Baselines whose
    required feature is missing are skipped with a warning -- this lets us
    work across NPZ schemas without hard-coding one name.
    """
    results: List[Dict[str, Any]] = []

    # (display_name, factory, candidate feature names)
    naive_specs = [
        (
            "OBI[contrarian]",
            lambda feat: OBIBaseline(obi_feature=feat, contrarian=True),
            ["obi_L5", "obi_L10", "obi_L1"],
        ),
        (
            "Momentum",
            lambda feat: MomentumBaseline(horizon=feat),
            ["log_return_30s", "log_return_5s", "log_return_1s"],
        ),
        (
            "Flow",
            lambda feat: FlowBaseline(flow_feature=feat),
            [
                "net_trade_flow_L5",  # V2 schema
                "net_trade_flow_1s",  # V3 schema
                "net_order_flow_L5",  # fallback
                "cumulative_net_flow_30s",
            ],
        ),
        (
            "MicropriceDeviation",
            lambda feat: MicropriceDeviationBaseline(feature=feat),
            ["microprice_deviation_bps", "microprice_dev_bps"],
        ),
    ]

    for display, factory, candidates in naive_specs:
        chosen = _pick_feature(candidates, feature_names)
        if chosen is None:
            logger.warning(
                "Skipping naive baseline %s: none of %s in feature list",
                display, candidates,
            )
            continue
        baseline = factory(chosen)
        try:
            pred = baseline.predict(X_test, feature_names)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Naive baseline %s failed: %s", display, exc)
            continue
        pred = np.asarray(pred, dtype=np.float64).ravel()
        row = _score_predictions(
            f"{display}[{chosen}]", pred, y_test, mask_test, target_sigma
        )
        results.append(row)

    return results


def run_fits_baseline(
    X_train_n: np.ndarray,
    y_train_n: np.ndarray,
    mask_train: np.ndarray,
    X_test_n: np.ndarray,
    y_test_n: np.ndarray,
    mask_test: np.ndarray,
    target_sigma: float,
    *,
    n_epochs: int = 30,
    batch_size: int = 256,
    lr: float = 1e-3,
    device: str = "cpu",
) -> Optional[Dict[str, Any]]:
    """Train a small FITS model; return one result row or ``None`` on failure.

    FITS depends on PyTorch.  If torch or the FITS module can't be
    imported (e.g. an old local torch that lacks ``nn.init.trunc_normal_``
    used elsewhere in the repo), we degrade gracefully.
    """
    try:
        import torch
        from src.baselines.fits_baseline import FITSModel
        from src.training.losses import quantile_loss
    except Exception as exc:  # pragma: no cover - env-dependent
        logger.warning("FITS unavailable (%s); skipping.", exc)
        return None

    _, seq_len, n_features = X_train_n.shape
    if seq_len < 4:
        logger.warning("FITS requires seq_len >= 4, got %d; skipping.", seq_len)
        return None

    # Keep params comfortably under 30K for signal verification.
    cut_freq = min(50, seq_len // 2 + 1)

    model = FITSModel(
        n_features=n_features,
        seq_len=seq_len,
        cut_freq=cut_freq,
        d_compress=8,
        d_hidden=32,
        n_quantiles=3,
        dropout=0.1,
    ).to(device)

    optimiser = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    valid = mask_train.astype(bool)
    X_tr = X_train_n[valid]
    y_tr = y_train_n[valid]
    if len(X_tr) == 0:
        logger.warning("FITS: no valid training samples, skipping.")
        return None

    model.train()
    for epoch in range(n_epochs):
        perm = np.random.permutation(len(X_tr))
        for i in range(0, len(X_tr), batch_size):
            idx = perm[i:i + batch_size]
            xb = torch.tensor(X_tr[idx], dtype=torch.float32, device=device)
            yb = torch.tensor(y_tr[idx], dtype=torch.float32, device=device)
            out = model(xb)
            loss = quantile_loss(out["quantiles"], yb)
            optimiser.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()

    # Inference
    model.eval()
    preds: List[np.ndarray] = []
    with torch.no_grad():
        for i in range(0, len(X_test_n), batch_size):
            xb = torch.tensor(
                X_test_n[i:i + batch_size], dtype=torch.float32, device=device
            )
            out = model(xb)
            preds.append(out["point_pred"].cpu().numpy())
    pred = np.concatenate(preds, axis=0).astype(np.float64)

    return _score_predictions("FITS", pred, y_test_n, mask_test, target_sigma)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _json_safe(obj: Any) -> Any:
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("(no baseline results to display)")
        return
    # Dynamically widen the Model column to the longest actual row name so
    # long naive-baseline names like
    # ``MicropriceDeviation[microprice_dev_bps]`` don't break the table.
    model_col = max(len("Model"), max(len(r["model"]) for r in rows)) + 2
    header = (
        f"{'Model':<{model_col}} {'n':>7} {'Corr':>8} {'RankCorr':>9} "
        f"{'R2':>9} {'DirAcc':>8} {'Autocorr':>10} {'ScoreBps':>10}"
    )
    bar = "=" * len(header)
    print("\n" + bar)
    print("BASELINE RESULTS (80/10/10 temporal split, CLAUDE.md Layer 1)")
    print(bar)
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['model']:<{model_col}} "
            f"{r['n']:>7} "
            f"{r['correlation']:>8.4f} "
            f"{r['rank_correlation']:>9.4f} "
            f"{r['r2']:>9.6f} "
            f"{r['direction_accuracy']:>8.4f} "
            f"{r['residual_autocorr_lag1']:>10.4f} "
            f"{r['score_bps']:>10.4f}"
        )
    print(bar + "\n")


#: Heuristic threshold above which we refuse to load the full 3D tensor
#: for FITS unless the user explicitly opts in.  At L=300, F=58,
#: 500K windows -> ~33 GB float32, which most workstations can't hold.
_FITS_FULL_AUTOSKIP_WINDOWS = 500_000


def _peek_npz_dims(npz_dir_or_paths) -> Optional[Tuple[int, int, int]]:
    """Read one NPZ header to discover ``(approx_total_windows, L, F)``.

    Used to decide whether to auto-skip FITS on large datasets without
    actually materialising the full tensor.  Returns ``None`` if the
    directory is empty or the first file can't be opened.

    ``approx_total_windows`` is estimated as ``first_file_windows *
    n_files`` -- not exact, but good enough for the 500K threshold
    (tens of MB of error tolerance).
    """
    try:
        paths = _resolve_paths(npz_dir_or_paths, ctx="_peek_npz_dims")
    except FileNotFoundError:
        return None
    first = paths[0]
    try:
        with np.load(str(first), allow_pickle=True) as npz:
            X = npz["X"]
            if X.ndim != 3:
                return None
            n_win_first, seq_len, n_feat = int(X.shape[0]), int(X.shape[1]), int(X.shape[2])
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Could not peek at %s (%s); skipping dim estimate", first, exc)
        return None
    approx_total = n_win_first * len(paths)
    return approx_total, seq_len, n_feat


def run_baselines(
    npz_dir: str,
    output_path: str,
    *,
    device: str = "cpu",
    fits_epochs: int = 30,
    fits_lr: float = 1e-3,
    fits_batch_size: int = 256,
    run_fits: bool = True,
    include_fits_full: bool = False,
) -> Dict[str, Any]:
    """End-to-end: load NPZ days, 80/10/10 split, evaluate baselines, save.

    Uses **streaming loaders** to keep peak memory low: the full
    ``(N, L, F)`` tensor is never materialised except when FITS is
    explicitly enabled via ``include_fits_full=True``.

    - Ridge / XGBoost / naive baselines read ``(N, F)`` (last timestep only).
    - TemporalRidge reads ``(N, 4F)`` aggregates.
    - FITS needs ``(N, L, F)`` -- so it's **auto-skipped** when the
      dataset exceeds ``_FITS_FULL_AUTOSKIP_WINDOWS`` unless
      ``include_fits_full=True``.

    Returns the same dict that's written to ``output_path``.
    """
    # --- Snapshot the file list BEFORE any loads so we get consistent ------
    # per-day counts across every pass.  Without this, a concurrent data
    # collector writing new NPZs between the last-step load and the
    # temporal-aggregate load would cause a day-count mismatch and
    # silently kill TemporalRidge.
    snapshot_paths = snapshot_npz_paths(npz_dir)
    logger.info(
        "Snapshot: %d NPZ files in %s", len(snapshot_paths), npz_dir,
    )

    # --- Load last-timestep features once for all non-FITS baselines --------
    # Every other model path only needs (N, F).  Loading once keeps us
    # from touching 100 GB of per-window data 4 times.
    logger.info("Loading last-timestep features")
    (
        days,
        X_last,
        y,
        mask,
        feature_names,
        per_day_counts,
    ) = load_last_step_features(snapshot_paths)
    n_windows = X_last.shape[0]
    n_features = X_last.shape[-1]
    logger.info(
        "Loaded %d days, %d windows, %d features",
        len(days), n_windows, n_features,
    )

    # --- Probe sequence length without materialising the full tensor --------
    dims = _peek_npz_dims(snapshot_paths)
    seq_len = dims[1] if dims is not None else None

    # --- Decide whether FITS will run (needs full 3D) -----------------------
    fits_will_run = run_fits
    fits_skip_reason: Optional[str] = None
    if fits_will_run and not include_fits_full and n_windows > _FITS_FULL_AUTOSKIP_WINDOWS:
        fits_will_run = False
        fits_skip_reason = (
            f"auto-skipped: {n_windows:,} windows > "
            f"{_FITS_FULL_AUTOSKIP_WINDOWS:,}. "
            f"Pass --include-fits-full to force-enable (requires "
            f"~{n_windows * (seq_len or 300) * n_features * 4 / 1e9:.1f} GB RAM)."
        )
        logger.warning("FITS %s", fits_skip_reason)

    # --- Temporal split on the (N, F) concat axis ---------------------------
    tr, va, te = temporal_split(per_day_counts, train_frac=0.80, val_frac=0.10)
    logger.info(
        "Split: train=%d windows (%s..%s), val=%d, test=%d",
        tr.stop - tr.start, days[0],
        days[min(len(days) - 1, max(0, _day_index_at(per_day_counts, tr.stop - 1)))],
        va.stop - va.start,
        te.stop - te.start,
    )

    X_train_last, y_train, m_train = X_last[tr], y[tr], mask[tr]
    X_test_last, y_test, m_test = X_last[te], y[te], mask[te]

    # --- Normalisation (train-only stats, on the last-timestep view) --------
    stats = compute_stats(X_train_last, y_train, m_train)
    X_train_ln, y_train_n = apply_stats(X_train_last, y_train, stats)
    X_test_ln, y_test_n = apply_stats(X_test_last, y_test, stats)

    # Target sigma -> bps back-scaling
    target_sigma = float(stats["y_sigma"])

    all_rows: List[Dict[str, Any]] = []

    # --- Ridge on last timestep ---------------------------------------------
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        ridge = RidgeBaseline(alpha=1.0)
        ridge_pred = _safe_fit_predict_ridge(
            ridge, X_train_ln, y_train_n, m_train, X_test_ln
        )
        all_rows.append(
            _score_predictions(
                "Ridge", ridge_pred, y_test_n, m_test, target_sigma
            )
        )

    # --- TemporalRidge: reload with (last, mean, std, trend) aggregates ------
    # Separate pass keeps peak memory at (N, 4F) rather than combining with
    # the last-timestep buffer.  Once this block exits, the aggregated
    # tensor is freed before XGBoost / naive baselines run.  Uses the
    # same snapshot path list so day counts match exactly.
    try:
        logger.info("Loading temporal aggregates for TemporalRidge")
        (
            _tr_days, X_agg, y_agg, mask_agg, _tr_feats, _tr_counts,
        ) = load_temporal_features(snapshot_paths)
        # Split must match the last-step split since it uses the same
        # per_day_counts (sanity-checked below for defensive parity).
        assert _tr_counts == per_day_counts, (
            "temporal-loader day counts differ from last-step loader"
        )
        X_train_agg = X_agg[tr]
        X_test_agg = X_agg[te]
        agg_stats = compute_stats(X_train_agg, y_agg[tr], mask_agg[tr])
        X_train_agg_n, _ = apply_stats(X_train_agg, y_agg[tr], agg_stats)
        X_test_agg_n, _ = apply_stats(X_test_agg, y_agg[te], agg_stats)
        # Use the generic RidgeBaseline on the pre-aggregated (N, 4F)
        # features; its _extract_features is a no-op on 2D input so it
        # just forwards to sklearn.Ridge.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            temp_ridge = RidgeBaseline(alpha=1.0)
            temp_pred = _safe_fit_predict_ridge(
                temp_ridge,
                X_train_agg_n,
                y_train_n,  # same normalised y as the Ridge block
                m_train,
                X_test_agg_n,
            )
            all_rows.append(
                _score_predictions(
                    "TemporalRidge", temp_pred, y_test_n, m_test, target_sigma
                )
            )
        # Free the aggregated buffers before moving on
        del X_agg, X_train_agg, X_test_agg, X_train_agg_n, X_test_agg_n
    except Exception as exc:
        logger.warning("TemporalRidge failed: %s", exc)

    # --- XGBoost baseline (non-linear signal detection) ---------------------
    try:
        from src.baselines.xgb_baseline import XGBoostBaseline

        xgb_model = XGBoostBaseline()
        xgb_pred = _safe_fit_predict_ridge(
            xgb_model, X_train_ln, y_train_n, m_train, X_test_ln
        )
        all_rows.append(
            _score_predictions(
                "XGBoost", xgb_pred, y_test_n, m_test, target_sigma
            )
        )
    except ImportError:
        logger.warning(
            "xgboost not installed -- skipping XGBoost baseline. "
            "Install with: pip install xgboost"
        )
    except Exception as exc:
        logger.warning("XGBoost baseline failed: %s", exc)

    # --- FITS baseline (full 3D tensor only if explicitly allowed) ----------
    if fits_will_run:
        try:
            logger.info("Loading full (N, L, F) tensor for FITS")
            (
                _f_days, X_full, y_full, mask_full, _f_feats, _f_counts,
            ) = _load_days_full(snapshot_paths)
            assert _f_counts == per_day_counts, (
                "full-loader day counts differ from last-step loader"
            )
            X_train_full = X_full[tr]
            X_test_full = X_full[te]
            full_stats = compute_stats(X_train_full, y_full[tr], mask_full[tr])
            X_train_fn, _ = apply_stats(X_train_full, y_full[tr], full_stats)
            X_test_fn, _ = apply_stats(X_test_full, y_full[te], full_stats)

            fits_row = run_fits_baseline(
                X_train_fn, y_train_n, m_train,
                X_test_fn, y_test_n, m_test,
                target_sigma=target_sigma,
                n_epochs=fits_epochs,
                batch_size=fits_batch_size,
                lr=fits_lr,
                device=device,
            )
            if fits_row is not None:
                all_rows.append(fits_row)
            del X_full, X_train_full, X_test_full, X_train_fn, X_test_fn
        except MemoryError:
            logger.error(
                "FITS OOM'd while materialising the full tensor. "
                "Re-run without --include-fits-full or on a smaller dataset."
            )
        except Exception as exc:
            logger.warning("FITS run failed: %s", exc)
    elif run_fits and not fits_will_run:
        # User passed --run-fits (implicit default) but we auto-skipped.
        all_rows.append({
            "model": "FITS",
            "correlation": float("nan"),
            "rank_correlation": float("nan"),
            "r2": float("nan"),
            "direction_accuracy": float("nan"),
            "residual_autocorr_lag1": float("nan"),
            "score_bps": float("nan"),
            "n": 0,
            "note": fits_skip_reason or "skipped",
        })

    # --- Naive baselines ----------------------------------------------------
    # Naive baselines read *raw* features from the last timestep.  They
    # accept (N, F) directly (see NaiveBaseline._last_step), so we pass
    # the un-normalised last-step tensor slice.
    naive_rows = run_naive_baselines(
        X_test_last, y_test, m_test, feature_names, target_sigma
    )
    all_rows.extend(naive_rows)

    _print_table(all_rows)

    # --- Persist ------------------------------------------------------------
    output = {
        "npz_dir": npz_dir,
        "n_days": len(days),
        "n_windows": int(n_windows),
        "seq_len": int(seq_len) if seq_len is not None else None,
        "n_features": int(n_features),
        "fits_skipped_reason": fits_skip_reason,
        "split": {
            "train_windows": int(tr.stop - tr.start),
            "val_windows": int(va.stop - va.start),
            "test_windows": int(te.stop - te.start),
        },
        "target_sigma_train": target_sigma,
        "results": all_rows,
    }
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=_json_safe)
    logger.info("Wrote %s", output_path)

    return output


def _day_index_at(per_day_counts: Sequence[int], sample_idx: int) -> int:
    """Return the day index containing ``sample_idx`` (safe-clamped)."""
    if sample_idx < 0:
        return 0
    cumulative = 0
    for i, c in enumerate(per_day_counts):
        cumulative += int(c)
        if sample_idx < cumulative:
            return i
    return max(0, len(per_day_counts) - 1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Layer-1 signal-verification baselines on NPZ windows."
    )
    parser.add_argument(
        "--npz-dir", default="data/npz_full",
        help="Directory containing <day>.npz files (default: data/npz_full)",
    )
    parser.add_argument(
        "--output", default="experiments/v3_full/baselines.json",
        help="Where to write the JSON results summary.",
    )
    parser.add_argument(
        "--device", default="cpu",
        help="Device for FITS training (cpu / cuda / mps).",
    )
    parser.add_argument(
        "--fits-epochs", type=int, default=30,
        help="FITS training epochs (default 30).",
    )
    parser.add_argument(
        "--fits-lr", type=float, default=1e-3,
        help="FITS learning rate.",
    )
    parser.add_argument(
        "--fits-batch-size", type=int, default=256,
        help="FITS mini-batch size.",
    )
    parser.add_argument(
        "--no-fits", action="store_true",
        help="Skip FITS (e.g. in restricted-torch environments).",
    )
    parser.add_argument(
        "--include-fits-full", action="store_true",
        help=(
            "Force-enable FITS even when the dataset has > "
            f"{_FITS_FULL_AUTOSKIP_WINDOWS:,} windows.  Materialises the "
            "full (N, L, F) tensor in RAM -- can easily exceed 100 GB on "
            "the full 1004-day corpus."
        ),
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable INFO logging.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    run_baselines(
        npz_dir=args.npz_dir,
        output_path=args.output,
        device=args.device,
        fits_epochs=args.fits_epochs,
        fits_lr=args.fits_lr,
        fits_batch_size=args.fits_batch_size,
        run_fits=not args.no_fits,
        include_fits_full=args.include_fits_full,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

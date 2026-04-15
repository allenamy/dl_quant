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

from src.baselines.linear_baseline import RidgeBaseline, TemporalRidgeBaseline
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
    """Load one NPZ file.  Returns a dict with numpy arrays (no torch)."""
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


def load_days(npz_dir: str) -> Tuple[List[str], np.ndarray, np.ndarray,
                                      np.ndarray, List[str], List[int]]:
    """Load and concatenate all ``<day>.npz`` files in ``npz_dir``.

    Returns
    -------
    days : list[str]
        Day stems in chronological order.
    X : (N, L, F) float32
    y : (N,) float32
    mask : (N,) float32 (0/1)
    feature_names : list[str]
        Feature names from the first file (verified consistent across days).
    per_day_counts : list[int]
        Number of windows contributed by each day, same order as ``days``.
        Useful for slicing into day-respecting train / val / test splits.
    """
    paths = sorted(Path(npz_dir).glob("*.npz"))
    if not paths:
        raise FileNotFoundError(f"No .npz files in {npz_dir}")

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
            # Skip empty days silently; they'd otherwise inflate the day list
            # without contributing samples.
            logger.warning("Day %s has 0 windows, skipping", day)
            continue
        days.append(day)
        xs.append(d["X"])
        ys.append(d["y"])
        ms.append(d["y_mask"])
        per_day_counts.append(n_win)
        if feature_names is None and "features" in d:
            feature_names = list(d["features"])
        elif feature_names is not None and "features" in d:
            if list(d["features"]) != feature_names:
                # Fail fast: subsequent np.concatenate would either crash
                # (same count, different order → silent corruption) or raise
                # (different counts). Either way, a mismatched NPZ is a
                # build-pipeline bug and must be rebuilt before use.
                raise ValueError(
                    f"Feature-name mismatch in {day}.npz: "
                    f"first file has {len(feature_names)} names, "
                    f"this file has {len(d['features'])}. "
                    f"Rebuild NPZs with a single pipeline version."
                )

    if not days:
        raise RuntimeError(f"All NPZ files in {npz_dir} had 0 windows")

    X = np.concatenate(xs, axis=0).astype(np.float32)
    y = np.concatenate(ys, axis=0).astype(np.float32)
    mask = np.concatenate(ms, axis=0).astype(np.float32)

    # Sanitise
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    mask = np.nan_to_num(mask, nan=0.0, posinf=0.0, neginf=0.0)
    y[mask == 0] = 0.0

    if feature_names is None:
        # Fallback: generate f0..fK so naive baselines fail loudly by KeyError
        # rather than silently mis-indexing.
        feature_names = [f"f{i}" for i in range(X.shape[-1])]

    return days, X, y, mask, feature_names, per_day_counts


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
    """
    x_mean = X.mean(axis=(0, 1)).astype(np.float32)
    x_std = X.std(axis=(0, 1)).astype(np.float32)

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
    """Z-score X (with dead-feature guard), MAD-normalise y."""
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


def run_baselines(
    npz_dir: str,
    output_path: str,
    *,
    device: str = "cpu",
    fits_epochs: int = 30,
    fits_lr: float = 1e-3,
    fits_batch_size: int = 256,
    run_fits: bool = True,
) -> Dict[str, Any]:
    """End-to-end: load NPZ days, 80/10/10 split, evaluate baselines, save.

    Returns the same dict that's written to ``output_path``.
    """
    logger.info("Loading NPZ files from %s", npz_dir)
    days, X, y, mask, feature_names, per_day_counts = load_days(npz_dir)
    logger.info(
        "Loaded %d days, %d windows, %d features",
        len(days), X.shape[0], X.shape[-1] if X.ndim == 3 else 0,
    )

    tr, va, te = temporal_split(per_day_counts, train_frac=0.80, val_frac=0.10)
    logger.info(
        "Split: train=%d windows (%s..%s), val=%d, test=%d",
        tr.stop - tr.start, days[0],
        days[min(len(days) - 1, max(0, _day_index_at(per_day_counts, tr.stop - 1)))],
        va.stop - va.start,
        te.stop - te.start,
    )

    X_train, y_train, m_train = X[tr], y[tr], mask[tr]
    X_test, y_test, m_test = X[te], y[te], mask[te]
    # (val is not used for hyper-tuning in this signal-verification runner;
    # kept for future extension.)

    # Normalisation (train-only stats)
    stats = compute_stats(X_train, y_train, m_train)
    X_train_n, y_train_n = apply_stats(X_train, y_train, stats)
    X_test_n, y_test_n = apply_stats(X_test, y_test, stats)

    # We report scores in bps at the original target scale.
    target_sigma = float(stats["y_sigma"])

    all_rows: List[Dict[str, Any]] = []

    # --- Trainable baselines -------------------------------------------------
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        ridge = RidgeBaseline(alpha=1.0)
        ridge_pred = _safe_fit_predict_ridge(
            ridge, X_train_n, y_train_n, m_train, X_test_n
        )
        all_rows.append(
            _score_predictions(
                "Ridge", ridge_pred, y_test_n, m_test, target_sigma
            )
        )

        temp_ridge = TemporalRidgeBaseline(alpha=1.0)
        temp_pred = _safe_fit_predict_ridge(
            temp_ridge, X_train_n, y_train_n, m_train, X_test_n
        )
        all_rows.append(
            _score_predictions(
                "TemporalRidge", temp_pred, y_test_n, m_test, target_sigma
            )
        )

    if run_fits:
        fits_row = run_fits_baseline(
            X_train_n, y_train_n, m_train,
            X_test_n, y_test_n, m_test,
            target_sigma=target_sigma,
            n_epochs=fits_epochs,
            batch_size=fits_batch_size,
            lr=fits_lr,
            device=device,
        )
        if fits_row is not None:
            all_rows.append(fits_row)

    # --- Naive baselines -----------------------------------------------------
    # Naive baselines read *raw* features; run them on un-normalised X_test
    # to keep the feature values on their natural scale.
    naive_rows = run_naive_baselines(
        X_test, y_test, m_test, feature_names, target_sigma
    )
    all_rows.extend(naive_rows)

    _print_table(all_rows)

    # --- Persist -------------------------------------------------------------
    output = {
        "npz_dir": npz_dir,
        "n_days": len(days),
        "n_windows": int(X.shape[0]),
        "seq_len": int(X.shape[1]) if X.ndim == 3 else None,
        "n_features": int(X.shape[-1]) if X.ndim == 3 else None,
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
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

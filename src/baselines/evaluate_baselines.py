"""Unified evaluation runner for all baseline models.

Discovers NPZ day files, builds temporal CV folds, trains/evaluates each
baseline (Ridge, TemporalRidge, XGBoost, FITS), and produces a summary
table with OOS metrics.

Usage:
    python -m src.baselines.evaluate_baselines --npz-dir data/npz --output-dir results/baselines
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from src.baselines.linear_baseline import RidgeBaseline, TemporalRidgeBaseline
from src.baselines.fits_baseline import FITSModel
from src.evaluation.metrics import evaluate_predictions
from src.training.dataset import build_time_series_folds
from src.training.losses import quantile_loss

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def discover_days(npz_dir: str) -> List[str]:
    """Find all .npz files in directory, return sorted day stems."""
    if not os.path.isdir(npz_dir):
        raise FileNotFoundError(f"NPZ directory not found: {npz_dir}")

    days = []
    for fname in sorted(os.listdir(npz_dir)):
        if fname.endswith(".npz"):
            days.append(fname[:-4])  # strip .npz

    if not days:
        raise FileNotFoundError(f"No .npz files found in {npz_dir}")

    return days


def load_days(
    npz_dir: str,
    days: List[str],
    *,
    horizon_key: str = "y",
    mask_key: str = "y_mask",
    use_last_timestep: bool = False,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load and concatenate X, y, y_mask from multiple day NPZ files.

    Parameters
    ----------
    horizon_key : str
        NPZ field name for the label array (e.g. ``"y_180"`` on V4 NPZ to
        pin the 180s horizon and avoid silently reading the y_60 alias).
    mask_key : str
        NPZ field name for the mask array, matched to ``horizon_key``.
    use_last_timestep : bool
        If True, slice ``X[:, -1:, :]`` per day BEFORE concatenation so the
        memory footprint is ~600x smaller (one timestep per window, not L).
        Ridge/TemporalRidge/XGBoost baselines already internally use
        last-timestep features; pre-slicing here just avoids materialising
        the full (N, L, F) tensor in RAM — critical for running on a local
        machine with less than ~80 GB.
        Note: when True, ``TemporalRidgeBaseline`` (which computes std, trend
        over the time axis) becomes degenerate (std=0, trend=0) and yields
        the same result as ``RidgeBaseline``. ``FITSBaseline`` needs a
        sequence and is skipped by ``run_all_baselines`` in this mode.

    Returns
    -------
    X : (N, L, F) float32 when use_last_timestep=False
        (N, 1, F) float32 when use_last_timestep=True
    y : (N,) float32
    mask : (N,) float32
    """
    xs, ys, masks = [], [], []
    for day in days:
        path = os.path.join(npz_dir, f"{day}.npz")
        npz = np.load(path, allow_pickle=True)
        x_day = npz["X"]  # (N, L, F)
        if use_last_timestep:
            # Keep 3D with L=1 so downstream ``X[:, -1, :]`` slicing still works.
            x_day = x_day[:, -1:, :]
        xs.append(x_day)
        if horizon_key not in npz.files:
            raise KeyError(
                f"{path}: missing horizon key {horizon_key!r}; "
                f"available keys: {sorted(k for k in npz.files if k.startswith('y'))}"
            )
        if mask_key not in npz.files:
            raise KeyError(
                f"{path}: missing mask key {mask_key!r}"
            )
        ys.append(npz[horizon_key])
        masks.append(npz[mask_key])

    X = np.concatenate(xs, axis=0).astype(np.float32)
    y = np.concatenate(ys, axis=0).astype(np.float32)
    mask = np.concatenate(masks, axis=0).astype(np.float32)

    # Sanitise
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    mask = np.nan_to_num(mask, nan=0.0, posinf=0.0, neginf=0.0)
    y[mask == 0] = 0.0

    return X, y, mask


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def compute_normalisation_stats(
    X: np.ndarray, y: np.ndarray
) -> Dict[str, np.ndarray]:
    """Compute feature-wise z-score stats and target MAD sigma from training data.

    Parameters
    ----------
    X : (N, L, F) training features.
    y : (N,) training targets.

    Returns
    -------
    dict with keys: x_mean, x_std, y_median, y_mad_sigma
    """
    x_mean = X.mean(axis=(0, 1))  # (F,)
    x_std = X.std(axis=(0, 1))    # (F,)

    y_median = np.median(y)
    y_mad = np.median(np.abs(y - y_median))
    y_mad_sigma = y_mad * 1.4826  # MAD -> sigma estimate

    return {
        "x_mean": x_mean,
        "x_std": x_std,
        "y_median": y_median,
        "y_mad_sigma": max(y_mad_sigma, 1e-8),
    }


def normalise_data(
    X: np.ndarray,
    y: np.ndarray,
    stats: Dict[str, Any],
) -> Tuple[np.ndarray, np.ndarray]:
    """Apply z-score normalisation to X and MAD sigma normalisation to y."""
    X_norm = (X - stats["x_mean"]) / (stats["x_std"] + 1e-8)
    X_norm = np.clip(X_norm, -10.0, 10.0)

    y_norm = (y - stats["y_median"]) / stats["y_mad_sigma"]

    return X_norm, y_norm


# ---------------------------------------------------------------------------
# Baseline runners
# ---------------------------------------------------------------------------

def run_ridge_baselines(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    alpha: float = 1.0,
) -> Dict[str, np.ndarray]:
    """Run Ridge and TemporalRidge, return predictions."""
    results = {}

    ridge = RidgeBaseline(alpha=alpha)
    ridge.fit(X_train, y_train)
    results["Ridge"] = ridge.predict(X_test)

    temp_ridge = TemporalRidgeBaseline(alpha=alpha)
    temp_ridge.fit(X_train, y_train)
    results["TemporalRidge"] = temp_ridge.predict(X_test)

    return results


def run_xgboost_baseline(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
) -> Optional[np.ndarray]:
    """Run XGBoost on last-timestep features. Returns None if xgboost unavailable."""
    try:
        import xgboost as xgb
    except ImportError:
        warnings.warn(
            "xgboost not installed -- skipping XGBoost baseline. "
            "Install with: pip install xgboost",
            stacklevel=2,
        )
        return None

    # Extract last-timestep features
    if X_train.ndim == 3:
        X_tr = X_train[:, -1, :]
        X_te = X_test[:, -1, :]
    else:
        X_tr, X_te = X_train, X_test

    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=1.0,
        reg_lambda=1.0,
        random_state=42,
        verbosity=0,
    )
    model.fit(X_tr, y_train)
    return model.predict(X_te)


def run_fits_baseline(
    X_train: np.ndarray,
    y_train: np.ndarray,
    mask_train: np.ndarray,
    X_test: np.ndarray,
    device: str = "cpu",
    n_epochs: int = 30,
    batch_size: int = 256,
    lr: float = 1e-3,
) -> np.ndarray:
    """Train FITS model and return test predictions (point_pred).

    Parameters
    ----------
    X_train : (N_tr, L, F)
    y_train : (N_tr,)
    mask_train : (N_tr,)
    X_test : (N_te, L, F)
    device : "cpu" or "cuda"
    n_epochs : training epochs
    batch_size : mini-batch size
    lr : learning rate

    Returns
    -------
    (N_te,) predicted returns
    """
    _, seq_len, n_features = X_train.shape

    model = FITSModel(
        n_features=n_features,
        seq_len=seq_len,
        cut_freq=min(50, seq_len // 2 + 1),
        d_compress=8,
        d_hidden=32,
        n_quantiles=3,
        dropout=0.1,
    )
    model = model.to(device)

    optimiser = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimiser, T_max=n_epochs)

    # Filter to valid samples
    valid = mask_train.astype(bool)
    X_tr_valid = X_train[valid]
    y_tr_valid = y_train[valid]

    n_samples = len(X_tr_valid)
    if n_samples == 0:
        logger.warning("No valid training samples for FITS -- returning zeros")
        return np.zeros(len(X_test), dtype=np.float32)

    # Training loop
    model.train()
    for epoch in range(n_epochs):
        # Shuffle
        perm = np.random.permutation(n_samples)
        epoch_loss = 0.0
        n_batches = 0

        for i in range(0, n_samples, batch_size):
            idx = perm[i : i + batch_size]
            x_batch = torch.tensor(X_tr_valid[idx], dtype=torch.float32, device=device)
            y_batch = torch.tensor(y_tr_valid[idx], dtype=torch.float32, device=device)

            out = model(x_batch)
            loss = quantile_loss(out["quantiles"], y_batch)

            optimiser.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()

            epoch_loss += loss.item()
            n_batches += 1

        scheduler.step()

    # Inference
    model.eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(X_test), batch_size):
            x_batch = torch.tensor(
                X_test[i : i + batch_size], dtype=torch.float32, device=device
            )
            out = model(x_batch)
            preds.append(out["point_pred"].cpu().numpy())

    return np.concatenate(preds, axis=0)


# ---------------------------------------------------------------------------
# Main evaluation orchestrator
# ---------------------------------------------------------------------------

def run_all_baselines(
    npz_dir: str,
    output_dir: str,
    device: str = "cpu",
    train_days: int = 5,
    val_days: int = 1,
    test_days: int = 1,
    fold_stride: int = 1,
    horizon_key: str = "y",
    mask_key: str = "y_mask",
    use_last_timestep: bool = False,
) -> Dict[str, Any]:
    """Run Ridge, TemporalRidge, XGBoost (if available), and FITS on multi-day data.

    Parameters
    ----------
    npz_dir : str
        Directory containing <day>.npz files.
    output_dir : str
        Directory to save results JSON.
    device : str
        Device for FITS training ("cpu" or "cuda").
    train_days, val_days, test_days : int
        Window sizes for temporal CV folds.
    fold_stride : int
        Stride for sliding-window CV.

    Returns
    -------
    dict with per-fold and aggregate results.
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Discover days
    days = discover_days(npz_dir)
    logger.info(f"Found {len(days)} days: {days}")

    # 2. Build temporal CV folds
    folds = build_time_series_folds(
        days=days,
        train_days=train_days,
        val_days=val_days,
        test_days=test_days,
        stride=fold_stride,
    )

    if not folds:
        # Not enough days for even one fold -- use simple train/test split
        logger.warning(
            f"Not enough days ({len(days)}) for {train_days}+{val_days}+{test_days} "
            f"fold. Using first {max(1, len(days)-1)} days for train, last day for test."
        )
        n_train = max(1, len(days) - 1)
        folds = [{"train": days[:n_train], "val": days[:n_train], "test": days[n_train:]}]
        if not folds[0]["test"]:
            folds[0]["test"] = days[-1:]

    logger.info(f"Built {len(folds)} temporal CV folds")

    # 3. Run baselines per fold
    all_results: Dict[str, List[dict]] = {}
    baseline_names = ["Ridge", "TemporalRidge", "XGBoost", "FITS"]
    for name in baseline_names:
        all_results[name] = []

    for fold_idx, fold in enumerate(folds):
        logger.info(
            f"Fold {fold_idx}: train={fold['train']}, "
            f"val={fold['val']}, test={fold['test']}"
        )

        # Load data (honor the horizon_key so V4 multi-horizon NPZ is loaded
        # on the intended horizon rather than the shortest-horizon `y` alias).
        X_train, y_train, mask_train = load_days(
            npz_dir, fold["train"], horizon_key=horizon_key, mask_key=mask_key,
            use_last_timestep=use_last_timestep,
        )
        X_test, y_test, mask_test = load_days(
            npz_dir, fold["test"], horizon_key=horizon_key, mask_key=mask_key,
            use_last_timestep=use_last_timestep,
        )

        # Compute normalisation from train
        norm_stats = compute_normalisation_stats(X_train, y_train)

        # Normalise
        X_train_n, y_train_n = normalise_data(X_train, y_train, norm_stats)
        X_test_n, y_test_n = normalise_data(X_test, y_test, norm_stats)

        # --- Ridge baselines ---
        ridge_preds = run_ridge_baselines(X_train_n, y_train_n, X_test_n)

        for name in ["Ridge", "TemporalRidge"]:
            pred = ridge_preds[name]
            metrics = evaluate_predictions(pred, y_test_n, mask_test)
            metrics["fold"] = fold_idx
            metrics["model"] = name
            all_results[name].append(metrics)

        # --- XGBoost ---
        xgb_pred = run_xgboost_baseline(X_train_n, y_train_n, X_test_n)
        if xgb_pred is not None:
            metrics = evaluate_predictions(xgb_pred, y_test_n, mask_test)
            metrics["fold"] = fold_idx
            metrics["model"] = "XGBoost"
            all_results["XGBoost"].append(metrics)

        # --- FITS ---
        if X_train.ndim == 3 and X_train.shape[1] > 1:
            fits_pred = run_fits_baseline(
                X_train_n, y_train_n, mask_train, X_test_n,
                device=device,
            )
            metrics = evaluate_predictions(fits_pred, y_test_n, mask_test)
            metrics["fold"] = fold_idx
            metrics["model"] = "FITS"
            all_results["FITS"].append(metrics)
        else:
            logger.warning("Skipping FITS: requires 3D input with seq_len > 1")

    # 4. Aggregate results
    summary = {}
    for name in baseline_names:
        fold_metrics = all_results[name]
        if not fold_metrics:
            continue
        agg = {}
        metric_keys = [
            "correlation", "rank_correlation", "r2", "direction_accuracy",
            "residual_autocorr_lag1", "score_bps",
        ]
        for key in metric_keys:
            values = [m[key] for m in fold_metrics if not np.isnan(m.get(key, np.nan))]
            if values:
                agg[f"{key}_mean"] = float(np.mean(values))
                agg[f"{key}_std"] = float(np.std(values))
            else:
                agg[f"{key}_mean"] = float("nan")
                agg[f"{key}_std"] = float("nan")
        agg["n_folds"] = len(fold_metrics)
        summary[name] = agg

    # 5. Save results
    output = {
        "per_fold": {k: v for k, v in all_results.items() if v},
        "summary": summary,
        "config": {
            "npz_dir": npz_dir,
            "n_days": len(days),
            "train_days": train_days,
            "val_days": val_days,
            "test_days": test_days,
            "fold_stride": fold_stride,
        },
    }

    output_path = os.path.join(output_dir, "baseline_results.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=_json_serialise)
    logger.info(f"Results saved to {output_path}")

    # 6. Print summary table
    _print_summary_table(summary)

    return output


def _json_serialise(obj: Any) -> Any:
    """JSON serialiser for numpy types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _print_summary_table(summary: Dict[str, dict]) -> None:
    """Print a formatted summary table of baseline results."""
    if not summary:
        print("No results to display.")
        return

    header = f"{'Model':<18} {'Corr':>10} {'Rank Corr':>10} {'R2':>10} {'Dir Acc':>10} {'Autocorr':>10}"
    print("\n" + "=" * len(header))
    print("BASELINE RESULTS SUMMARY")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for name, agg in summary.items():
        corr = agg.get("correlation_mean", float("nan"))
        rank_corr = agg.get("rank_correlation_mean", float("nan"))
        r2 = agg.get("r2_mean", float("nan"))
        dir_acc = agg.get("direction_accuracy_mean", float("nan"))
        autocorr = agg.get("residual_autocorr_lag1_mean", float("nan"))

        print(
            f"{name:<18} "
            f"{corr:>10.4f} "
            f"{rank_corr:>10.4f} "
            f"{r2:>10.6f} "
            f"{dir_acc:>10.4f} "
            f"{autocorr:>10.4f}"
        )

    print("=" * len(header) + "\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run baseline models on LOB NPZ data"
    )
    parser.add_argument("--npz-dir", required=True, help="Directory with <day>.npz files")
    parser.add_argument("--output-dir", default="results/baselines", help="Output directory")
    parser.add_argument("--device", default="cpu", help="Device for FITS (cpu or cuda)")
    parser.add_argument("--train-days", type=int, default=5)
    parser.add_argument("--val-days", type=int, default=1)
    parser.add_argument("--test-days", type=int, default=1)
    parser.add_argument("--fold-stride", type=int, default=1)
    parser.add_argument(
        "--horizon-key", default="y",
        help="NPZ field for labels (e.g. 'y_180' on V4 NPZ). Default 'y' (back-compat).",
    )
    parser.add_argument(
        "--mask-key", default="y_mask",
        help="NPZ field for the label mask. Default 'y_mask'.",
    )
    parser.add_argument(
        "--use-last-timestep", action="store_true",
        help=(
            "Slice X[:, -1, :] per day BEFORE concatenation (memory = L× smaller). "
            "Ridge/XGBoost already use last-timestep internally; this just avoids "
            "materialising the full (N, L, F) tensor, enabling local runs with "
            "<16GB RAM on 200-700 day folds. TemporalRidge becomes degenerate "
            "(std=0, trend=0) and FITS is auto-skipped in this mode."
        ),
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    run_all_baselines(
        npz_dir=args.npz_dir,
        output_dir=args.output_dir,
        device=args.device,
        train_days=args.train_days,
        val_days=args.val_days,
        test_days=args.test_days,
        fold_stride=args.fold_stride,
        horizon_key=args.horizon_key,
        mask_key=args.mask_key,
        use_last_timestep=args.use_last_timestep,
    )


if __name__ == "__main__":
    main()

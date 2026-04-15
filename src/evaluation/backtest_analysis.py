"""Backtest analysis and visualization helpers.

Provides functions for:
- Performance breakdown by volatility regime
- Performance breakdown by hour of day
- Optimal threshold search (grid search, for analysis only)
- Multi-model comparison
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .backtest_v2 import BacktestEngine, BacktestResult


def analyze_by_regime(
    result: BacktestResult,
    vol_series: np.ndarray,
    n_regimes: int = 3,
) -> Dict[str, Dict[str, float]]:
    """Break down performance by volatility regime (low/medium/high).

    Parameters
    ----------
    result : BacktestResult
        Backtest result (must contain pnl_timeseries and position_timeseries).
    vol_series : (N,) array
        Volatility measure (e.g., realized vol) aligned with the result
        timeseries. Must have the same length as result.pnl_timeseries.
    n_regimes : int
        Number of regimes to split into (default 3 = low/medium/high).

    Returns
    -------
    dict[str, dict]
        Keys are regime names ("low", "medium", "high").
        Values contain: n_periods, net_pnl, sharpe, win_rate.
    """
    vol = np.asarray(vol_series, dtype=np.float64).ravel()

    # Reconstruct per-period net P&L from cumulative
    cum_pnl = result.pnl_timeseries
    if len(cum_pnl) == 0 or len(vol) == 0:
        return {}

    n = min(len(cum_pnl), len(vol))
    cum_pnl = cum_pnl[:n]
    vol = vol[:n]
    positions = result.position_timeseries[:n]

    per_period_pnl = np.diff(cum_pnl, prepend=0.0)

    # Split into regimes by volatility percentile
    regime_names = ["low", "medium", "high"][:n_regimes]
    boundaries = np.linspace(0, 100, n_regimes + 1)

    results: Dict[str, Dict[str, float]] = {}

    for i, name in enumerate(regime_names):
        lo = np.percentile(vol, boundaries[i])
        hi = np.percentile(vol, boundaries[i + 1])
        if i == n_regimes - 1:
            regime_mask = (vol >= lo) & (vol <= hi)
        else:
            regime_mask = (vol >= lo) & (vol < hi)

        regime_pnl = per_period_pnl[regime_mask]
        regime_pos = positions[regime_mask]
        n_regime = int(np.sum(regime_mask))

        if n_regime == 0:
            results[name] = {
                "n_periods": 0,
                "net_pnl": 0.0,
                "sharpe": 0.0,
                "win_rate": 0.0,
            }
            continue

        active = regime_pos != 0
        n_active = int(np.sum(active))
        win_rate = float(np.mean(regime_pnl[active] > 0)) if n_active > 0 else 0.0
        mean_pnl = np.mean(regime_pnl)
        std_pnl = np.std(regime_pnl, ddof=1) if n_regime > 1 else 0.0

        from .backtest_v2 import PERIODS_PER_YEAR
        sharpe = float(
            (mean_pnl / std_pnl) * np.sqrt(PERIODS_PER_YEAR)
        ) if std_pnl > 0 else 0.0

        results[name] = {
            "n_periods": n_regime,
            "net_pnl": float(np.sum(regime_pnl)),
            "sharpe": sharpe,
            "win_rate": win_rate,
        }

    return results


def analyze_by_hour(
    result: BacktestResult,
    timestamps: np.ndarray,
) -> Dict[int, Dict[str, float]]:
    """Break down performance by hour of day (UTC).

    Parameters
    ----------
    result : BacktestResult
        Backtest result.
    timestamps : (N,) array
        Microsecond timestamps aligned with the result timeseries.

    Returns
    -------
    dict[int, dict]
        Keys are hour (0-23 UTC).
        Values contain: n_periods, net_pnl, avg_pnl, win_rate.
    """
    cum_pnl = result.pnl_timeseries
    ts = np.asarray(timestamps, dtype=np.int64).ravel()

    if len(cum_pnl) == 0 or len(ts) == 0:
        return {}

    n = min(len(cum_pnl), len(ts))
    cum_pnl = cum_pnl[:n]
    ts = ts[:n]
    positions = result.position_timeseries[:n]

    per_period_pnl = np.diff(cum_pnl, prepend=0.0)

    # Convert microsecond timestamps to hour of day (UTC)
    # timestamp_us -> seconds -> datetime
    seconds = ts / 1_000_000.0
    hours = (seconds % 86400) / 3600
    hours = hours.astype(int) % 24

    results: Dict[int, Dict[str, float]] = {}

    for h in range(24):
        hour_mask = hours == h
        n_hour = int(np.sum(hour_mask))

        if n_hour == 0:
            results[h] = {
                "n_periods": 0,
                "net_pnl": 0.0,
                "avg_pnl": 0.0,
                "win_rate": 0.0,
            }
            continue

        hour_pnl = per_period_pnl[hour_mask]
        hour_pos = positions[hour_mask]
        active = hour_pos != 0
        n_active = int(np.sum(active))
        win_rate = float(np.mean(hour_pnl[active] > 0)) if n_active > 0 else 0.0

        results[h] = {
            "n_periods": n_hour,
            "net_pnl": float(np.sum(hour_pnl)),
            "avg_pnl": float(np.mean(hour_pnl)),
            "win_rate": win_rate,
        }

    return results


def optimal_threshold_search(
    predictions: np.ndarray,
    targets: np.ndarray,
    mask: np.ndarray,
    fee_bps: float = 4.0,
    slippage_bps: float = 1.0,
    thresholds: Optional[np.ndarray] = None,
) -> Dict[str, object]:
    """Grid search over signal thresholds to find optimal entry point.

    WARNING: This is for analysis only, NOT for setting live parameters.
    In-sample threshold optimization leads to overfitting. Always validate
    on held-out data.

    Parameters
    ----------
    predictions : (N, 3) array
        Quantile predictions [q10, q50, q90].
    targets : (N,) array
        Realized returns.
    mask : (N,) array
        Boolean mask.
    fee_bps : float
        Round-trip fee in bps.
    slippage_bps : float
        Slippage per side in bps.
    thresholds : array, optional
        Custom threshold grid. Defaults to np.linspace(0, 0.5, 21).

    Returns
    -------
    dict
        Keys: best_threshold, best_sharpe, best_net_pnl, results_df.
        results_df is a DataFrame with columns: threshold, sharpe, net_pnl,
        n_trades, win_rate.
    """
    if thresholds is None:
        thresholds = np.linspace(0, 0.5, 21)

    records: List[Dict[str, float]] = []
    best_sharpe = -np.inf
    best_threshold = 0.0
    best_net_pnl = 0.0

    for thresh in thresholds:
        engine = BacktestEngine(
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            signal_threshold=float(thresh),
            confidence_sizing=True,
        )
        res = engine.run(predictions, targets, mask)

        records.append({
            "threshold": float(thresh),
            "sharpe": res.sharpe_annual,
            "net_pnl": res.net_pnl_bps,
            "n_trades": res.n_trades,
            "trade_rate": res.trade_rate,
            "win_rate": res.win_rate,
            "max_drawdown": res.max_drawdown_bps,
        })

        if res.sharpe_annual > best_sharpe:
            best_sharpe = res.sharpe_annual
            best_threshold = float(thresh)
            best_net_pnl = res.net_pnl_bps

    results_df = pd.DataFrame(records)

    return {
        "best_threshold": best_threshold,
        "best_sharpe": float(best_sharpe),
        "best_net_pnl": float(best_net_pnl),
        "results_df": results_df,
    }


def compare_predictions_table(
    predictions_dict: Dict[str, tuple],
    targets: np.ndarray,
    timestamps: Optional[np.ndarray] = None,
    baseline_key: Optional[str] = None,
    run_backtest: bool = False,
    fee_bps: float = 4.0,
    slippage_bps: float = 1.0,
) -> pd.DataFrame:
    """Side-by-side comparison of multiple prediction sets.

    Parameters
    ----------
    predictions_dict : dict[str, tuple]
        ``{name: (preds, mask)}``. ``preds`` may be 1D (point predictions)
        or 2D ``(N, 3)`` quantiles; ``mask`` is a boolean/float (N,) array.
    targets : (N,) array of realised returns / targets.
    timestamps : optional (N,) array of microsecond timestamps.
        Currently unused but accepted for future time-slice extensions.
    baseline_key : optional str
        When provided, computes a ``win_rate_vs_baseline`` column = fraction
        of samples where ``|pred - target| < |baseline_pred - target|``.
    run_backtest : bool
        When ``True`` and a prediction has 3 columns, run ``BacktestEngine``
        to produce ``sharpe_bt`` and ``net_pnl_bps`` columns. Off by default
        because it is slow and not always desired.
    fee_bps, slippage_bps : float
        Passed through to ``BacktestEngine`` when ``run_backtest=True``.

    Returns
    -------
    pd.DataFrame
        Rows = model names, columns at minimum ``n``, ``correlation``,
        ``rank_correlation``, ``r2``, ``direction_accuracy``.
        Additional columns added based on options.
    """
    from .metrics import evaluate_predictions

    targets = np.asarray(targets, dtype=np.float64).ravel()

    # Extract baseline predictions (point form) if requested
    baseline_pred: Optional[np.ndarray] = None
    if baseline_key is not None:
        if baseline_key not in predictions_dict:
            raise KeyError(
                f"baseline_key '{baseline_key}' not in predictions_dict "
                f"(keys: {list(predictions_dict.keys())})"
            )
        bp, _ = predictions_dict[baseline_key]
        bp = np.asarray(bp)
        baseline_pred = bp[:, 1] if bp.ndim == 2 else bp.ravel()

    rows: List[Dict[str, object]] = []
    for name, (preds, mask) in predictions_dict.items():
        preds_arr = np.asarray(preds)
        mask_arr = np.asarray(mask, dtype=bool).ravel()
        point_pred = (
            preds_arr[:, 1] if preds_arr.ndim == 2 else preds_arr.ravel()
        )
        metrics = evaluate_predictions(point_pred, targets, mask_arr)
        row: Dict[str, object] = {"model": name}
        for key in [
            "n", "correlation", "rank_correlation", "r2",
            "direction_accuracy", "residual_autocorr_lag1",
        ]:
            row[key] = metrics.get(key, float("nan"))

        if baseline_pred is not None and name != baseline_key:
            err_model = np.abs(point_pred - targets)
            err_base = np.abs(baseline_pred - targets)
            both = mask_arr & ~np.isnan(err_model) & ~np.isnan(err_base)
            if both.sum() > 0:
                row["win_rate_vs_baseline"] = float(
                    np.mean(err_model[both] < err_base[both])
                )
            else:
                row["win_rate_vs_baseline"] = float("nan")
        elif baseline_pred is not None:
            row["win_rate_vs_baseline"] = float("nan")  # baseline vs itself

        if run_backtest and preds_arr.ndim == 2 and preds_arr.shape[1] == 3:
            engine = BacktestEngine(
                fee_bps=fee_bps, slippage_bps=slippage_bps,
            )
            res = engine.run(preds_arr, targets, mask_arr)
            row["sharpe_bt"] = res.sharpe_annual
            row["net_pnl_bps"] = res.net_pnl_bps
            row["trade_rate"] = res.trade_rate

        rows.append(row)

    df = pd.DataFrame(rows)
    if len(df) > 0:
        df = df.set_index("model")
    return df


def bootstrap_confidence_interval(
    predictions: np.ndarray,
    targets: np.ndarray,
    mask: np.ndarray,
    metric: str = "correlation",
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    block_size: int = 1,
    seed: Optional[int] = None,
) -> tuple:
    """Bootstrap CI for a metric.

    With stride < horizon, samples are autocorrelated, so use block
    bootstrap with ``block_size = horizon / stride``. This preserves
    short-range dependence so the CI is not artificially tight.

    Parameters
    ----------
    predictions : (N,) or (N, 3) array.
    targets : (N,) array.
    mask : (N,) boolean/float mask.
    metric : str
        One of ``"correlation"``, ``"r2"``, ``"sharpe"`` (Sharpe uses
        prediction * target as per-period PnL, no cost modelling).
    n_bootstrap : int
        Number of bootstrap resamples.
    ci_level : float
        Confidence level (0-1). Default 0.95 -> 2.5% / 97.5% percentiles.
    block_size : int
        Block size for moving-block bootstrap. Set to ``horizon / stride``
        when labels are autocorrelated. Default 1 (iid bootstrap).
    seed : optional int
        RNG seed for reproducibility.

    Returns
    -------
    (lower, upper) : tuple[float, float]
    """
    if metric not in {"correlation", "r2", "sharpe"}:
        raise ValueError(
            f"Unsupported metric '{metric}'. "
            f"Use one of 'correlation', 'r2', 'sharpe'."
        )
    if not 0.0 < ci_level < 1.0:
        raise ValueError(f"ci_level must be in (0, 1), got {ci_level}")
    if block_size < 1:
        raise ValueError(f"block_size must be >= 1, got {block_size}")

    preds_arr = np.asarray(predictions)
    point_pred = (
        preds_arr[:, 1] if preds_arr.ndim == 2 else preds_arr.ravel()
    ).astype(np.float64)
    targets = np.asarray(targets, dtype=np.float64).ravel()
    mask_bool = np.asarray(mask, dtype=bool).ravel()

    p = point_pred[mask_bool]
    t = targets[mask_bool]
    n = len(p)
    if n < 2:
        return (float("nan"), float("nan"))

    def _compute(pp: np.ndarray, tt: np.ndarray) -> float:
        if metric == "correlation":
            if np.std(pp) == 0 or np.std(tt) == 0:
                return float("nan")
            return float(np.corrcoef(pp, tt)[0, 1])
        if metric == "r2":
            ss_tot = float(np.sum((tt - np.mean(tt)) ** 2))
            if ss_tot == 0:
                return float("nan")
            return 1.0 - float(np.sum((tt - pp) ** 2)) / ss_tot
        # Sharpe of prediction-as-position strategy
        pnl = pp * tt
        if len(pnl) < 2:
            return float("nan")
        std = np.std(pnl, ddof=1)
        if std == 0 or not np.isfinite(std):
            return float("nan")
        return float(np.mean(pnl) / std)

    rng = np.random.default_rng(seed)
    samples: List[float] = []

    if block_size <= 1:
        # iid bootstrap
        for _ in range(n_bootstrap):
            idx = rng.integers(0, n, size=n)
            val = _compute(p[idx], t[idx])
            if np.isfinite(val):
                samples.append(val)
    else:
        # Moving-block bootstrap: sample starting indices with replacement,
        # then glue blocks of length ``block_size`` together to length >= n.
        n_blocks = int(np.ceil(n / block_size))
        max_start = max(1, n - block_size + 1)
        for _ in range(n_bootstrap):
            starts = rng.integers(0, max_start, size=n_blocks)
            idx = np.concatenate([
                np.arange(s, s + block_size) for s in starts
            ])[:n]
            val = _compute(p[idx], t[idx])
            if np.isfinite(val):
                samples.append(val)

    if not samples:
        return (float("nan"), float("nan"))

    alpha = (1.0 - ci_level) / 2.0
    lower = float(np.percentile(samples, 100 * alpha))
    upper = float(np.percentile(samples, 100 * (1 - alpha)))
    return (lower, upper)


def compare_models(results: Dict[str, BacktestResult]) -> pd.DataFrame:
    """Compare multiple backtest results side by side.

    Parameters
    ----------
    results : dict[str, BacktestResult]
        Keys are model names, values are BacktestResult instances.

    Returns
    -------
    pd.DataFrame
        One row per model with key metrics.
    """
    records: List[Dict[str, object]] = []

    for name, res in results.items():
        record = {"model": name}
        record.update(res.to_dict())
        records.append(record)

    df = pd.DataFrame(records)
    if len(df) > 0:
        df = df.set_index("model")
    return df

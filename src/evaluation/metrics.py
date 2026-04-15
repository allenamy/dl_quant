"""Evaluation metrics for LOB Transformer V2 predictions."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


def evaluate_predictions(
    pred: np.ndarray,
    target: np.ndarray,
    mask: np.ndarray,
    uncertainty: Optional[np.ndarray] = None,
    quantiles_pred: Optional[np.ndarray] = None,
) -> dict:
    """Compute comprehensive evaluation metrics for predictions.

    Parameters
    ----------
    pred : (N,) array of predicted values.
    target : (N,) array of true target values.
    mask : (N,) boolean array; True = valid observation.
    uncertainty : optional (N,) array of predicted uncertainty (std-dev).
    quantiles_pred : optional (N, Q) array of quantile predictions.
        Columns correspond to quantile levels [0.10, 0.50, 0.90].

    Returns
    -------
    dict with evaluation metrics.
    """
    pred = np.asarray(pred, dtype=np.float64).ravel()
    target = np.asarray(target, dtype=np.float64).ravel()
    mask = np.asarray(mask, dtype=bool).ravel()

    # Apply mask
    p = pred[mask]
    t = target[mask]
    n = len(p)

    result: dict = {"n": n}

    # Edge case: too few observations
    if n < 10:
        for key in [
            "correlation", "correlation_pval", "rank_correlation",
            "r2", "residual_mean", "residual_std", "residual_skew",
            "residual_kurtosis", "residual_autocorr_lag1",
            "direction_accuracy", "left_tail_corr", "left_tail_bias",
            "right_tail_corr", "right_tail_bias", "score_bps",
        ]:
            result[key] = np.nan
        return result

    # --- Correlation ---
    t_std = np.std(t)
    p_std = np.std(p)
    if t_std == 0 or p_std == 0:
        result["correlation"] = np.nan
        result["correlation_pval"] = np.nan
        result["rank_correlation"] = np.nan
    else:
        corr, pval = stats.pearsonr(p, t)
        result["correlation"] = corr
        result["correlation_pval"] = pval
        rho, _ = stats.spearmanr(p, t)
        result["rank_correlation"] = rho

    # --- R-squared ---
    residuals = t - p
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((t - np.mean(t)) ** 2)
    if ss_tot == 0:
        result["r2"] = np.nan
    else:
        result["r2"] = 1.0 - ss_res / ss_tot

    # --- Residual statistics ---
    result["residual_mean"] = np.mean(residuals)
    result["residual_std"] = np.std(residuals, ddof=1) if n > 1 else np.nan
    result["residual_skew"] = float(stats.skew(residuals)) if n > 2 else np.nan
    result["residual_kurtosis"] = float(stats.kurtosis(residuals)) if n > 3 else np.nan

    # --- Residual autocorrelation lag-1 ---
    if n > 2:
        r0 = residuals[:-1]
        r1 = residuals[1:]
        r0_std = np.std(r0)
        r1_std = np.std(r1)
        if r0_std == 0 or r1_std == 0:
            result["residual_autocorr_lag1"] = np.nan
        else:
            result["residual_autocorr_lag1"] = float(np.corrcoef(r0, r1)[0, 1])
    else:
        result["residual_autocorr_lag1"] = np.nan

    # --- Direction accuracy ---
    sign_match = np.sign(p) == np.sign(t)
    # Exclude zeros in target for direction accuracy
    nonzero = t != 0
    if np.sum(nonzero) > 0:
        result["direction_accuracy"] = float(np.mean(sign_match[nonzero]))
    else:
        result["direction_accuracy"] = np.nan

    # --- Tail analysis ---
    # Left tail: bottom 10% of targets
    q10 = np.percentile(t, 10)
    left_mask = t <= q10
    if np.sum(left_mask) >= 5:
        p_left, t_left = p[left_mask], t[left_mask]
        if np.std(p_left) == 0 or np.std(t_left) == 0:
            result["left_tail_corr"] = np.nan
        else:
            result["left_tail_corr"] = float(np.corrcoef(p_left, t_left)[0, 1])
        result["left_tail_bias"] = float(np.mean(p_left - t_left))
    else:
        result["left_tail_corr"] = np.nan
        result["left_tail_bias"] = np.nan

    # Right tail: top 10% of targets
    q90 = np.percentile(t, 90)
    right_mask = t >= q90
    if np.sum(right_mask) >= 5:
        p_right, t_right = p[right_mask], t[right_mask]
        if np.std(p_right) == 0 or np.std(t_right) == 0:
            result["right_tail_corr"] = np.nan
        else:
            result["right_tail_corr"] = float(np.corrcoef(p_right, t_right)[0, 1])
        result["right_tail_bias"] = float(np.mean(p_right - t_right))
    else:
        result["right_tail_corr"] = np.nan
        result["right_tail_bias"] = np.nan

    # --- Score in bps ---
    r2_val = result.get("r2", np.nan)
    if np.isnan(r2_val) or t_std == 0:
        result["score_bps"] = np.nan
    else:
        result["score_bps"] = float(np.sqrt(max(r2_val, 0.0)) * t_std * 10000)

    # --- Quantile coverage ---
    if quantiles_pred is not None:
        qp = np.asarray(quantiles_pred, dtype=np.float64)
        if qp.ndim == 1:
            qp = qp.reshape(-1, 1)
        qp = qp[mask]
        quantile_levels = [0.10, 0.50, 0.90]
        for i, ql in enumerate(quantile_levels):
            col_name = f"q{int(ql * 100)}_coverage"
            if i < qp.shape[1]:
                coverage = float(np.mean(t <= qp[:, i]))
                result[col_name] = coverage
                result[f"q{int(ql * 100)}_calibration_error"] = float(
                    coverage - ql
                )
            else:
                result[col_name] = np.nan
                result[f"q{int(ql * 100)}_calibration_error"] = np.nan

    # --- Uncertainty-error correlation ---
    if uncertainty is not None:
        unc = np.asarray(uncertainty, dtype=np.float64).ravel()[mask]
        abs_res = np.abs(residuals)
        if np.std(unc) == 0 or np.std(abs_res) == 0:
            result["uncertainty_error_correlation"] = np.nan
        else:
            corr_ue, _ = stats.pearsonr(unc, abs_res)
            result["uncertainty_error_correlation"] = float(corr_ue)

    return result


# ---------------------------------------------------------------------------
# Stratified metrics (time-of-day, volatility regime)
# ---------------------------------------------------------------------------


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def _safe_r2(pred: np.ndarray, target: np.ndarray) -> float:
    if len(target) < 2:
        return float("nan")
    ss_tot = float(np.sum((target - np.mean(target)) ** 2))
    if ss_tot == 0:
        return float("nan")
    ss_res = float(np.sum((target - pred) ** 2))
    return 1.0 - ss_res / ss_tot


def stratified_metrics_by_hour(
    predictions: np.ndarray,
    targets: np.ndarray,
    mask: np.ndarray,
    timestamps: np.ndarray,
) -> pd.DataFrame:
    """Compute correlation / R^2 stratified by hour-of-day (0-23 UTC).

    Useful for detecting time-of-day effects. If a model works in Asian
    hours but fails in US hours, we want to see that.

    Parameters
    ----------
    predictions, targets, mask : (N,) arrays.
    timestamps : (N,) microsecond timestamps (int/float).

    Returns
    -------
    pd.DataFrame
        Rows sorted by ``hour`` (0..23). Columns: ``hour``, ``n_samples``,
        ``corr``, ``r2``, ``mean_pred``, ``std_pred``. Hours with no
        valid samples are included with NaN metrics and n_samples=0.
    """
    pred = np.asarray(predictions, dtype=np.float64).ravel()
    tgt = np.asarray(targets, dtype=np.float64).ravel()
    m = np.asarray(mask, dtype=bool).ravel()
    ts = np.asarray(timestamps, dtype=np.int64).ravel()

    n = min(len(pred), len(tgt), len(m), len(ts))
    pred, tgt, m, ts = pred[:n], tgt[:n], m[:n], ts[:n]

    # Apply validity mask
    pred, tgt, ts = pred[m], tgt[m], ts[m]

    # microseconds -> hour of day (UTC)
    seconds = ts / 1_000_000.0
    hours = ((seconds % 86400) / 3600).astype(int) % 24

    rows = []
    for h in range(24):
        sel = hours == h
        n_h = int(sel.sum())
        if n_h == 0:
            rows.append({
                "hour": h, "n_samples": 0,
                "corr": float("nan"), "r2": float("nan"),
                "mean_pred": float("nan"), "std_pred": float("nan"),
            })
            continue
        p_h, t_h = pred[sel], tgt[sel]
        rows.append({
            "hour": h,
            "n_samples": n_h,
            "corr": _safe_corr(p_h, t_h),
            "r2": _safe_r2(p_h, t_h),
            "mean_pred": float(np.mean(p_h)),
            "std_pred": float(np.std(p_h, ddof=1)) if n_h > 1 else float("nan"),
        })

    return pd.DataFrame(rows)


def stratified_metrics_by_vol_regime(
    predictions: np.ndarray,
    targets: np.ndarray,
    mask: np.ndarray,
    realized_vol: np.ndarray,
    n_buckets: int = 3,
) -> pd.DataFrame:
    """Split samples into volatility regimes (by quantile), compute metrics.

    Detects "model works in low vol but fails in high vol" type failures.

    Parameters
    ----------
    predictions, targets, mask : (N,) arrays.
    realized_vol : (N,) per-sample volatility measurement.
    n_buckets : int
        Number of quantile buckets (default 3 -> low / medium / high).

    Returns
    -------
    pd.DataFrame
        One row per regime (ordered low -> high). Columns:
        ``regime``, ``vol_range``, ``n_samples``, ``corr``, ``r2``.
    """
    if n_buckets < 2:
        raise ValueError(f"n_buckets must be >= 2, got {n_buckets}")

    pred = np.asarray(predictions, dtype=np.float64).ravel()
    tgt = np.asarray(targets, dtype=np.float64).ravel()
    m = np.asarray(mask, dtype=bool).ravel()
    vol = np.asarray(realized_vol, dtype=np.float64).ravel()

    n = min(len(pred), len(tgt), len(m), len(vol))
    pred, tgt, m, vol = pred[:n], tgt[:n], m[:n], vol[:n]
    pred, tgt, vol = pred[m], tgt[m], vol[m]

    if n_buckets == 3:
        names = ["low", "medium", "high"]
    elif n_buckets == 2:
        names = ["low", "high"]
    else:
        names = [f"q{i+1}of{n_buckets}" for i in range(n_buckets)]

    boundaries = np.linspace(0.0, 100.0, n_buckets + 1)
    edges = [np.percentile(vol, b) for b in boundaries] if len(vol) > 0 else [0.0] * (n_buckets + 1)

    rows = []
    for i in range(n_buckets):
        lo, hi = edges[i], edges[i + 1]
        if i == n_buckets - 1:
            sel = (vol >= lo) & (vol <= hi)
        else:
            sel = (vol >= lo) & (vol < hi)
        n_r = int(sel.sum())
        vol_range = f"[{lo:.4g}, {hi:.4g}]"
        if n_r == 0:
            rows.append({
                "regime": names[i], "vol_range": vol_range, "n_samples": 0,
                "corr": float("nan"), "r2": float("nan"),
            })
            continue
        p_r, t_r = pred[sel], tgt[sel]
        rows.append({
            "regime": names[i],
            "vol_range": vol_range,
            "n_samples": n_r,
            "corr": _safe_corr(p_r, t_r),
            "r2": _safe_r2(p_r, t_r),
        })

    return pd.DataFrame(rows)

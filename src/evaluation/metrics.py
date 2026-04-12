"""Evaluation metrics for LOB Transformer V2 predictions."""

from __future__ import annotations

from typing import Optional

import numpy as np
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

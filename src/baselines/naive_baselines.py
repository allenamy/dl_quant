"""Single-feature naive baselines for LOB return prediction.

These are NOT trainable models. Each baseline extracts a single feature
from the most recent timestep of the input window and uses it directly
as a prediction signal. They serve as the absolute-floor comparison:
if a complex model cannot beat a single-feature signal, there is no
justification for complexity (CLAUDE.md: "earn every unit of complexity
with OOS evidence").

Typical usage::

    df = run_all_naive_baselines(
        X_train, y_train, X_test, y_test, mask_test, feature_names,
    )
    # df has one row per baseline with correlation / r2

Nothing here is fitted on ``X_train`` / ``y_train`` -- those arguments
are accepted for signature consistency with the Ridge baseline workflow.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np
import pandas as pd

from src.evaluation.metrics import evaluate_predictions


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class NaiveBaseline:
    """Base class for single-feature signal generators.

    These are NOT trainable. They extract a single feature from the
    input window and use it directly as a prediction signal.

    Subclasses must set ``self.name`` (str) and implement ``predict``.
    """

    name: str = "NaiveBaseline"

    def predict(self, X: np.ndarray, feature_names: Sequence[str]) -> np.ndarray:
        """X: (N, L, F). Returns (N,) predictions."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    @staticmethod
    def _lookup_index(feature: str, feature_names: Sequence[str]) -> int:
        """Return index of ``feature`` in ``feature_names`` or raise KeyError.

        We raise ``KeyError`` with a clear message rather than let
        ``list.index`` raise a generic ``ValueError``.
        """
        names = list(feature_names)
        if feature not in names:
            raise KeyError(
                f"Feature '{feature}' not found in feature_names. "
                f"Available ({len(names)}): {names[:10]}"
                f"{'...' if len(names) > 10 else ''}"
            )
        return names.index(feature)

    @staticmethod
    def _last_step(X: np.ndarray, idx: int) -> np.ndarray:
        """Extract the last timestep of the ``idx``-th feature.

        Supports both 3D ``(N, L, F)`` and 2D ``(N, F)`` inputs.
        """
        X = np.asarray(X)
        if X.ndim == 3:
            return X[:, -1, idx].astype(np.float64, copy=False)
        if X.ndim == 2:
            return X[:, idx].astype(np.float64, copy=False)
        raise ValueError(f"X must be 2D or 3D, got shape {X.shape}")


# ---------------------------------------------------------------------------
# Concrete baselines
# ---------------------------------------------------------------------------


class OBIBaseline(NaiveBaseline):
    """Signal = (-)OBI. Heavy bid queue suggests near-term downturn (contrarian).

    Order-book imbalance (OBI) measures relative bid vs ask size.
    Empirically, at short horizons (seconds to a few minutes) a heavy
    bid queue often precedes a *down* move as passive buyers get picked
    off and price reverts -- hence the contrarian default.
    """

    def __init__(self, obi_feature: str = "obi_L5", contrarian: bool = True) -> None:
        self.obi_feature = obi_feature
        self.contrarian = bool(contrarian)
        direction = "neg" if self.contrarian else "pos"
        self.name = f"OBI[{self.obi_feature}|{direction}]"

    def predict(self, X: np.ndarray, feature_names: Sequence[str]) -> np.ndarray:
        idx = self._lookup_index(self.obi_feature, feature_names)
        value = self._last_step(X, idx)
        return -value if self.contrarian else value


class MomentumBaseline(NaiveBaseline):
    """Signal = recent log return (momentum continues).

    The classic "trend follows" baseline: use a recent realised return
    directly as the prediction. If the feature ``log_return_30s`` is the
    30-second realised return, this predicts the sign and rough magnitude
    of the next window-horizon return.
    """

    def __init__(self, horizon: str = "log_return_30s") -> None:
        self.horizon = horizon
        self.name = f"Momentum[{self.horizon}]"

    def predict(self, X: np.ndarray, feature_names: Sequence[str]) -> np.ndarray:
        idx = self._lookup_index(self.horizon, feature_names)
        return self._last_step(X, idx)


class FlowBaseline(NaiveBaseline):
    """Signal = net trade flow (buying pressure predicts up-move).

    Aggregated signed trade flow (buys - sells) over a short window.
    Standard market-microstructure prior: net buy pressure -> price up.
    """

    def __init__(self, flow_feature: str = "net_trade_flow_L5") -> None:
        self.flow_feature = flow_feature
        self.name = f"Flow[{self.flow_feature}]"

    def predict(self, X: np.ndarray, feature_names: Sequence[str]) -> np.ndarray:
        idx = self._lookup_index(self.flow_feature, feature_names)
        return self._last_step(X, idx)


class MicropriceDeviationBaseline(NaiveBaseline):
    """Signal = microprice deviation from mid (queue imbalance indicator).

    Microprice = (bid_size * ask_px + ask_size * bid_px) / (bid_size + ask_size).
    Deviation from mid indicates imminent price move toward the thinner
    side of the book.
    """

    def __init__(self, feature: str = "microprice_deviation_bps") -> None:
        self.feature = feature
        self.name = f"MicropriceDev[{self.feature}]"

    def predict(self, X: np.ndarray, feature_names: Sequence[str]) -> np.ndarray:
        idx = self._lookup_index(self.feature, feature_names)
        return self._last_step(X, idx)


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------


def _safe_correlation(pred: np.ndarray, target: np.ndarray) -> float:
    """Pearson correlation; returns NaN when either side is constant."""
    if len(pred) < 2 or np.std(pred) == 0 or np.std(target) == 0:
        return float("nan")
    return float(np.corrcoef(pred, target)[0, 1])


def _safe_r2(pred: np.ndarray, target: np.ndarray) -> float:
    """R^2 in the usual regression sense (1 - SS_res/SS_tot).

    Naive baselines are on an arbitrary scale, so this R^2 can be very
    negative -- that just means "the raw signal's magnitude doesn't
    match the target's magnitude", which is fine for a comparison
    diagnostic. Correlation is the primary metric.
    """
    ss_res = float(np.sum((target - pred) ** 2))
    ss_tot = float(np.sum((target - np.mean(target)) ** 2))
    if ss_tot == 0:
        return float("nan")
    return 1.0 - ss_res / ss_tot


def run_all_naive_baselines(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    mask_test: np.ndarray,
    feature_names: Sequence[str],
    baselines: Optional[List[NaiveBaseline]] = None,
) -> pd.DataFrame:
    """Run all naive baselines, return comparison DataFrame with corr, R2.

    Parameters
    ----------
    X_train, y_train : np.ndarray
        Unused -- naive baselines do not train. Kept for signature
        consistency with the Ridge baseline workflow.
    X_test : (N, L, F) array.
    y_test : (N,) array.
    mask_test : (N,) bool/float array; True/1 = valid observation.
    feature_names : sequence of str
        Names corresponding to the last axis of ``X_test``.
    baselines : optional list of ``NaiveBaseline``
        When ``None`` the default set is used: OBI, Momentum, Flow,
        MicropriceDeviation. Pass a custom list to test specific
        feature choices.

    Returns
    -------
    pd.DataFrame
        One row per baseline with columns:
        ``model``, ``feature``, ``n``, ``correlation``, ``rank_correlation``,
        ``r2``, ``direction_accuracy``, ``error`` (None unless a baseline
        was skipped because its feature is missing).
    """
    del X_train, y_train  # explicitly unused

    if baselines is None:
        baselines = [
            OBIBaseline(),
            MomentumBaseline(),
            FlowBaseline(),
            MicropriceDeviationBaseline(),
        ]

    y = np.asarray(y_test, dtype=np.float64).ravel()
    mask = np.asarray(mask_test, dtype=bool).ravel()

    rows: List[dict] = []
    for bl in baselines:
        feature = (
            getattr(bl, "obi_feature", None)
            or getattr(bl, "horizon", None)
            or getattr(bl, "flow_feature", None)
            or getattr(bl, "feature", None)
            or ""
        )
        row = {
            "model": bl.name,
            "feature": feature,
            "n": int(mask.sum()),
            "correlation": float("nan"),
            "rank_correlation": float("nan"),
            "r2": float("nan"),
            "direction_accuracy": float("nan"),
            "error": None,
        }
        try:
            pred = bl.predict(X_test, feature_names)
        except KeyError as exc:
            row["error"] = str(exc)
            rows.append(row)
            continue

        pred = np.asarray(pred, dtype=np.float64).ravel()
        # Evaluate on masked samples only
        metrics = evaluate_predictions(pred, y, mask)
        row["correlation"] = metrics.get("correlation", float("nan"))
        row["rank_correlation"] = metrics.get("rank_correlation", float("nan"))
        row["r2"] = metrics.get("r2", float("nan"))
        row["direction_accuracy"] = metrics.get("direction_accuracy", float("nan"))
        rows.append(row)

    return pd.DataFrame(rows)

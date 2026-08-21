"""Ridge regression baselines for LOB return prediction.

Two variants:
- RidgeBaseline: uses only the most recent timestep's features.
- TemporalRidgeBaseline: concatenates temporal aggregates (last, mean, std, trend)
  for richer input at the cost of 4x feature dimensionality.

Both follow sklearn-style fit/predict interface and serve as Layer-1 signal
verification (CLAUDE.md: "earn every unit of complexity with OOS evidence").
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from sklearn.linear_model import Ridge


class RidgeBaseline:
    """Ridge regression on the last timestep's features.

    Takes (N, L, F) sliding windows and extracts x[:, -1, :] as features,
    discarding temporal structure. This is the simplest possible baseline:
    if Ridge on the most recent snapshot cannot beat zero, there is no
    instantaneous linear signal.

    Parameters
    ----------
    alpha : float
        Ridge regularisation strength (default 1.0).
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha
        self.model = Ridge(alpha=alpha)

    def _extract_features(self, X: np.ndarray) -> np.ndarray:
        """Extract last-timestep features: (N, L, F) -> (N, F)."""
        if X.ndim == 3:
            return X[:, -1, :]
        return X  # already 2D

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RidgeBaseline":
        """Fit Ridge on last-timestep features.

        Parameters
        ----------
        X : (N, L, F) or (N, F) array.
        y : (N,) target returns.

        Returns
        -------
        self
        """
        feats = self._extract_features(X)
        self.model.fit(feats, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict returns from last-timestep features.

        Parameters
        ----------
        X : (N, L, F) or (N, F) array.

        Returns
        -------
        (N,) predicted returns.
        """
        feats = self._extract_features(X)
        return self.model.predict(feats)


class TemporalRidgeBaseline:
    """Ridge regression with hand-crafted temporal aggregates.

    Extracts four summary statistics per feature across the time dimension:
      1. last   = x[:, -1, :]            -- most recent value
      2. mean   = x.mean(axis=1)         -- average level
      3. std    = x.std(axis=1)          -- variability
      4. trend  = x[:, -1, :] - x[:, 0, :]  -- first-to-last change

    Total feature dimension: n_features * 4.

    This tests whether simple temporal summaries contain predictive information
    beyond the instantaneous snapshot.

    Parameters
    ----------
    alpha : float
        Ridge regularisation strength (default 1.0).
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha
        self.model = Ridge(alpha=alpha)

    def _extract_features(self, X: np.ndarray) -> np.ndarray:
        """Build temporal aggregate features: (N, L, F) -> (N, 4*F)."""
        if X.ndim == 2:
            # No temporal dimension -- replicate the same features 4x
            return np.concatenate([X, X, np.zeros_like(X), np.zeros_like(X)], axis=1)

        last = X[:, -1, :]                      # (N, F)
        mean = X.mean(axis=1)                    # (N, F)
        std = X.std(axis=1)                      # (N, F)
        trend = X[:, -1, :] - X[:, 0, :]         # (N, F)

        return np.concatenate([last, mean, std, trend], axis=1)  # (N, 4*F)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "TemporalRidgeBaseline":
        """Fit Ridge on temporal aggregate features.

        Parameters
        ----------
        X : (N, L, F) array.
        y : (N,) target returns.

        Returns
        -------
        self
        """
        feats = self._extract_features(X)
        self.model.fit(feats, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict returns from temporal aggregate features.

        Parameters
        ----------
        X : (N, L, F) array.

        Returns
        -------
        (N,) predicted returns.
        """
        feats = self._extract_features(X)
        return self.model.predict(feats)

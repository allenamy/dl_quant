"""XGBoost baseline -- the non-linear bridge between Ridge and V3.

Provides a simple wrapper around ``xgboost.XGBRegressor`` that:

- Accepts 3D (B, L, F) inputs by extracting the last timestep (like Ridge)
- Exposes ``feature_importances()`` for signal attribution
- Uses conservative hyperparameters (shallow trees, strong regularization)
  appropriate for low-SNR financial prediction

This baseline answers the question: "Is there non-linear signal in our
features that Ridge misses?"  If XGBoost significantly outperforms Ridge,
the neural net (V3) has room to capture non-linear interactions.  If not,
the signal is likely linear and a simpler model suffices.

Usage:
    from src.baselines.xgb_baseline import XGBoostBaseline

    model = XGBoostBaseline()
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    importances = model.feature_importances()
"""

from __future__ import annotations

from typing import Dict

import numpy as np


class XGBoostBaseline:
    """XGBoost regressor baseline for LOB feature windows.

    Parameters
    ----------
    n_estimators : int
        Number of boosting rounds.
    max_depth : int
        Maximum tree depth.  Kept shallow (4) to avoid overfitting
        in a low-SNR regime.
    learning_rate : float
        Step size shrinkage.
    reg_lambda : float
        L2 regularization on leaf weights.
    reg_alpha : float
        L1 regularization on leaf weights.
    min_child_weight : float
        Minimum sum of instance weight needed in a child.  Higher
        values prevent splits on thin evidence.
    subsample : float
        Row subsampling ratio per tree.
    colsample_bytree : float
        Column subsampling ratio per tree.
    random_state : int
        Random seed for reproducibility.
    """

    name = "XGBoost"

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        reg_lambda: float = 1.0,
        reg_alpha: float = 0.0,
        min_child_weight: float = 5.0,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
    ):
        import xgboost as xgb

        self.model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            reg_lambda=reg_lambda,
            reg_alpha=reg_alpha,
            min_child_weight=min_child_weight,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            random_state=random_state,
            tree_method="hist",
            n_jobs=4,
        )

    def fit(self, X_train: np.ndarray, y_train: np.ndarray) -> "XGBoostBaseline":
        """Fit on training data.

        Parameters
        ----------
        X_train : np.ndarray
            Shape ``(N, F)`` or ``(N, L, F)``.  If 3D, the last timestep
            is extracted (consistent with RidgeBaseline).
        y_train : np.ndarray
            Shape ``(N,)`` -- target values.

        Returns
        -------
        self
        """
        if X_train.ndim == 3:
            X_train = X_train[:, -1, :]
        self.model.fit(X_train, y_train)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate predictions.

        Parameters
        ----------
        X : np.ndarray
            Shape ``(N, F)`` or ``(N, L, F)``.

        Returns
        -------
        np.ndarray
            Shape ``(N,)`` -- predicted values.
        """
        if X.ndim == 3:
            X = X[:, -1, :]
        return self.model.predict(X)

    def feature_importances(self) -> np.ndarray:
        """Return feature importance scores from the trained model.

        Returns
        -------
        np.ndarray
            Shape ``(F,)`` -- importance scores (gain-based by default).
        """
        return self.model.feature_importances_

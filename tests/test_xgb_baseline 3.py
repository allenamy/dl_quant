"""Unit tests for the XGBoost baseline.

Verifies that XGBoostBaseline can:
1. Detect a planted non-linear signal (f0 * f1 interaction)
2. Handle both 2D and 3D inputs
3. Expose feature importances

Run directly:
    python3 tests/test_xgb_baseline.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

# Make ``src.*`` importable when running from the repo root without pytest.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.baselines.xgb_baseline import XGBoostBaseline  # noqa: E402


def test_nonlinear_signal_detection() -> None:
    """XGBoost should catch a planted f0 * f1 interaction (corr > 0.15)."""
    rng = np.random.RandomState(42)
    N = 2000
    F = 10

    X = rng.randn(N, F).astype(np.float32)
    # Plant a non-linear interaction signal: y = f0 * f1 + noise
    signal = X[:, 0] * X[:, 1]
    noise = rng.randn(N).astype(np.float32) * 0.5
    y = (signal + noise).astype(np.float32)

    # Train/test split (temporal: first 80% train, last 20% test)
    split = int(0.8 * N)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    model = XGBoostBaseline(n_estimators=100, max_depth=4)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    corr = float(np.corrcoef(pred, y_test)[0, 1])
    assert corr > 0.15, (
        f"XGBoost should detect non-linear f0*f1 interaction, got corr={corr:.4f}"
    )

    print(f"PASS: test_nonlinear_signal_detection (corr={corr:.4f})")


def test_3d_input() -> None:
    """XGBoost should handle (N, L, F) input by extracting last timestep."""
    rng = np.random.RandomState(123)
    N, L, F = 500, 30, 5

    X_3d = rng.randn(N, L, F).astype(np.float32)
    # Signal is in the last timestep's feature 0
    y = X_3d[:, -1, 0] * 0.5 + rng.randn(N).astype(np.float32) * 0.3

    model = XGBoostBaseline(n_estimators=50, max_depth=3)
    model.fit(X_3d, y)
    pred = model.predict(X_3d)

    assert pred.shape == (N,), f"Expected shape ({N},), got {pred.shape}"
    assert np.isfinite(pred).all(), "Predictions contain non-finite values"

    print("PASS: test_3d_input")


def test_feature_importances() -> None:
    """Feature importances should be available and sum to ~1."""
    rng = np.random.RandomState(7)
    N, F = 300, 8

    X = rng.randn(N, F).astype(np.float32)
    y = X[:, 0] + rng.randn(N).astype(np.float32) * 0.5

    model = XGBoostBaseline(n_estimators=50, max_depth=3)
    model.fit(X, y)

    imp = model.feature_importances()
    assert imp.shape == (F,), f"Expected shape ({F},), got {imp.shape}"
    assert np.isfinite(imp).all(), "Importances contain non-finite values"
    # Feature importances should sum to approximately 1
    assert abs(imp.sum() - 1.0) < 0.01, f"Importances sum to {imp.sum():.4f}, expected ~1.0"

    print("PASS: test_feature_importances")


if __name__ == "__main__":
    test_nonlinear_signal_detection()
    test_3d_input()
    test_feature_importances()
    print("\nAll XGBoost baseline tests passed.")

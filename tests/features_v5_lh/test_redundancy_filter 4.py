import numpy as np
from src.features_v5_lh.redundancy_filter import select_features


def test_drops_correlated_pair():
    """Two identical features + 1 independent — redundancy filter keeps 2."""
    np.random.seed(0)
    n = 500
    X = np.random.randn(n, 3).astype(np.float32)
    X[:, 1] = X[:, 0] + 1e-6 * np.random.randn(n)  # near-duplicate
    y = np.random.randn(n)
    kept = select_features(X, y, r_threshold=0.95)
    assert len(kept) == 2
    assert set(kept).issubset({0, 1, 2})
    # Feature 2 (independent) should be kept
    assert 2 in kept


def test_keeps_feature_with_higher_ic_to_target():
    """Of two correlated features, keep the one with higher |corr(x, y)|."""
    np.random.seed(1)
    n = 500
    y = np.random.randn(n).astype(np.float32)
    f0 = 0.3 * y + np.random.randn(n).astype(np.float32)  # IC ~ 0.3
    f1 = f0 + 0.001 * np.random.randn(n).astype(np.float32)  # same but lower IC
    f2 = 0.5 * y + np.random.randn(n).astype(np.float32)  # IC ~ 0.45, independent from f0/f1
    X = np.stack([f0, f1, f2], axis=1).astype(np.float32)
    kept = select_features(X, y, r_threshold=0.95)
    # f2 always kept (high IC + independent)
    assert 2 in kept
    # Of f0/f1 pair, whichever has higher |IC| should remain
    ic0 = abs(np.corrcoef(f0, y)[0, 1])
    ic1 = abs(np.corrcoef(f1, y)[0, 1])
    winner = 0 if ic0 >= ic1 else 1
    assert winner in kept


def test_nothing_dropped_when_all_independent():
    np.random.seed(2)
    X = np.random.randn(300, 5).astype(np.float32)
    y = np.random.randn(300)
    kept = select_features(X, y, r_threshold=0.95)
    assert len(kept) == 5

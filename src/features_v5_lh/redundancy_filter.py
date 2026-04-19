"""Greedy correlation-based feature selection.

For each pair of features with |r| > r_threshold, drop the one with lower
|corr(feature, y)|. Produces a sorted list of kept feature indices.

Used at V5-LH NPZ build time (Task 13) on the first fold's training days:
compute |IC| per feature, build feature-feature correlation matrix, drop
redundant features greedily.
"""
from typing import List

import numpy as np


def select_features(
    X: np.ndarray,
    y: np.ndarray,
    r_threshold: float = 0.95,
) -> List[int]:
    """Return list of kept feature indices.

    Parameters
    ----------
    X : (N, F) feature matrix. Non-finite values are replaced with 0.
    y : (N,) target for IC tie-breaking. Non-finite replaced with 0.
    r_threshold : drop pairs with |r| > r_threshold (strict >).
    """
    if X.ndim != 2 or X.shape[1] == 0:
        return []

    F = X.shape[1]
    # Sanitize (NaN/Inf → 0)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)

    # Compute |IC| of each feature with target
    ics = np.zeros(F)
    for i in range(F):
        if np.std(X[:, i]) < 1e-12:
            ics[i] = 0.0
        else:
            ics[i] = abs(np.corrcoef(X[:, i], y)[0, 1])

    # Feature-feature correlation (absolute values)
    C = np.abs(np.corrcoef(X, rowvar=False))

    # Greedy: iterate over pairs in order, drop lower-IC feature of each
    # correlated pair; once a feature is dropped it cannot drop others
    kept = set(range(F))
    for i in range(F):
        for j in range(i + 1, F):
            if i not in kept or j not in kept:
                continue
            if C[i, j] > r_threshold:
                if ics[i] >= ics[j]:
                    kept.discard(j)
                else:
                    kept.discard(i)

    return sorted(kept)

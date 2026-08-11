"""Unit tests for build_long_context_overlay_y1800.

Smoke test on a synthetic mid-price grid + sample timestamps: verify
all 6 long-context features compute without nan/inf, mask covers
samples with sufficient lookback, and shapes are right.
"""
import numpy as np
import pytest


@pytest.fixture
def synthetic_mid_npz_dict():
    """Synthetic 1-day mid-price npz dict (matches midprice_per_day format)."""
    # 1 day = 86400 seconds, mid drifts upward with vol
    np.random.seed(0)
    T = 86400
    t0 = 1_700_000_000  # any plausible POSIX seconds
    ts = np.arange(t0, t0 + T, dtype=np.int64)
    log_ret = np.random.normal(0, 1e-4, size=T)
    log_ret[0] = 0
    mid = 50000.0 * np.exp(np.cumsum(log_ret))
    return {
        "timestamps_s": ts,
        "mid_price": mid,
        "best_bid": mid - 0.5,
        "best_ask": mid + 0.5,
    }


@pytest.fixture
def synthetic_y1800_npz_dict():
    """Synthetic y_1800 NPZ with stride=600 timestamps, 60 samples spanning 10h."""
    t0 = 1_700_000_000
    # First sample at t0+0s, stride 600s
    timestamps = np.arange(60, dtype=np.int64) * 600 * 1_000_000 + t0 * 1_000_000
    return {
        "timestamps": timestamps,
        # We don't need X for the overlay generator; only timestamps used
    }


def test_compute_long_context_shapes(synthetic_mid_npz_dict, synthetic_y1800_npz_dict):
    """Output shape (N, 6) and finite values for sufficient-lookback samples."""
    from scripts.build_long_context_overlay_y1800 import build_second_grid, compute_long_context

    mid_ts, mid_grid = build_second_grid(synthetic_mid_npz_dict)
    out = compute_long_context(synthetic_y1800_npz_dict, mid_ts, mid_grid)

    N = len(synthetic_y1800_npz_dict["timestamps"])
    assert out["long_context_feats"].shape == (N, 6)
    assert out["mask"].shape == (N,)
    assert out["timestamps"].shape == (N,)

    # The first ~7200/600 = 12 samples may have insufficient lookback.
    # All masked samples must have finite features.
    mk = out["mask"].astype(bool)
    assert np.isfinite(out["long_context_feats"][mk]).all()
    # At least half the day's samples should be masked-in
    assert mk.sum() >= N // 2, f"only {mk.sum()}/{N} masked-in"


def test_compute_long_context_lookback_consistency(synthetic_mid_npz_dict):
    """Samples with offset < 7200s must have mask=0 (insufficient history)."""
    from scripts.build_long_context_overlay_y1800 import build_second_grid, compute_long_context

    mid_ts, mid_grid = build_second_grid(synthetic_mid_npz_dict)
    t0 = mid_ts[0]
    # Sample at offset=3600s (only 1h history available, less than 7200s required)
    early_ts = np.array([(t0 + 3600) * 1_000_000], dtype=np.int64)
    out = compute_long_context({"timestamps": early_ts}, mid_ts, mid_grid)
    assert out["mask"][0] == 0

    # Sample at offset=8000s (>7200s history)
    later_ts = np.array([(t0 + 8000) * 1_000_000], dtype=np.int64)
    out2 = compute_long_context({"timestamps": later_ts}, mid_ts, mid_grid)
    assert out2["mask"][0] == 1
    # All 6 features must be finite
    assert np.isfinite(out2["long_context_feats"][0]).all()


def test_compute_long_context_empty_input():
    """Empty timestamps must return well-shaped empty arrays."""
    from scripts.build_long_context_overlay_y1800 import compute_long_context

    out = compute_long_context(
        {"timestamps": np.zeros(0, dtype=np.int64)},
        mid_ts=np.zeros(0, dtype=np.int64),
        mid_grid=np.zeros(0, dtype=np.float64),
    )
    assert out["long_context_feats"].shape == (0, 6)
    assert out["mask"].shape == (0,)
    assert out["timestamps"].shape == (0,)


def test_compute_long_context_no_lookahead(synthetic_mid_npz_dict, synthetic_y1800_npz_dict):
    """Modifying mid AFTER the sample anchor must NOT change the features.
    This guards against future-leak in the overlay generator.
    """
    from scripts.build_long_context_overlay_y1800 import build_second_grid, compute_long_context

    # Compute features on original
    mid_ts, mid_grid = build_second_grid(synthetic_mid_npz_dict)
    out_orig = compute_long_context(synthetic_y1800_npz_dict, mid_ts, mid_grid)

    # Pick a sample that is masked-in
    mk = out_orig["mask"].astype(bool)
    sample_idx = int(np.where(mk)[0][len(np.where(mk)[0]) // 2])
    sample_ts_us = int(synthetic_y1800_npz_dict["timestamps"][sample_idx])
    sample_ts_s = sample_ts_us // 1_000_000
    grid_start = int(mid_ts[0])
    sample_off = sample_ts_s - grid_start

    # Perturb mid AFTER the anchor (offset > sample_off)
    mid_perturbed = synthetic_mid_npz_dict["mid_price"].copy()
    mid_perturbed[sample_off + 1:] *= 2.0  # extreme change in future
    perturbed_dict = dict(synthetic_mid_npz_dict)
    perturbed_dict["mid_price"] = mid_perturbed

    mid_ts2, mid_grid2 = build_second_grid(perturbed_dict)
    out_pert = compute_long_context(synthetic_y1800_npz_dict, mid_ts2, mid_grid2)

    # The sample's features should be unchanged (no lookahead)
    assert np.allclose(
        out_orig["long_context_feats"][sample_idx],
        out_pert["long_context_feats"][sample_idx],
        atol=1e-6,
    ), "future perturbation leaked into overlay features (lookahead bug)"

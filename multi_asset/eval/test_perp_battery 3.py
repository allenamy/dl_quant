"""TDD test for perp_battery dual-caliber eval harness.

Validates the metric kernels on synthetic (q50, y) with KNOWN ground truth:
  - y = 2*q50 + noise  -> Pearson high & positive, beta ~= 2.0
  - a strictly monotone (q50, y) relation -> decile monotonicity ~= +1.0
  - sigma-ratio = std(q50)/std(y) computed exactly
  - bias_bps = mean(q50)*1e4 computed exactly
  - clean-stride subsample factor derived from median ts gap so spacing >= 600s

Deterministic (fixed seed). Pure-numpy/scipy; no GPU, no real data needed.
Run:  python3 multi_asset/eval/test_perp_battery.py   (exit 0 = PASS)
"""
from __future__ import annotations

import numpy as np

from perp_battery import (
    compute_metrics,
    clean_subsample_factor,
    pearson,
    spearman,
    beta_slope,
    monotonicity,
)

TOL = 1e-6
RTOL = 0.02  # 2% for noisy-regression quantities


def _approx(a, b, tol=TOL, msg=""):
    assert abs(a - b) <= tol, f"{msg}: got {a!r}, expected {b!r} (tol {tol})"


def _rel(a, b, rtol=RTOL, msg=""):
    assert abs(a - b) <= rtol * abs(b) + 1e-9, f"{msg}: got {a!r}, expected ~{b!r} (rtol {rtol})"


def test_pearson_and_beta_known_slope():
    """y = 2*q50 + noise -> Pearson high positive, beta ~= 2.0."""
    rng = np.random.default_rng(0)
    n = 200_000
    q50 = rng.standard_normal(n)
    noise = rng.standard_normal(n) * 0.5  # SNR high enough for tight estimates
    y = 2.0 * q50 + noise

    # closed-form Pearson for y=2q+e (indep): rho = 2 / sqrt(4 + var(e)) = 2/sqrt(4.25)
    expected_rho = 2.0 / np.sqrt(4.0 + 0.25)
    p = pearson(q50, y)
    _rel(p, expected_rho, msg="pearson")

    b = beta_slope(q50, y)  # OLS slope of y on q50
    _rel(b, 2.0, msg="beta")

    # monotonicity of a strong linear relation must be +1 (deciles strictly ordered)
    mono = monotonicity(q50, y)
    _approx(mono, 1.0, tol=1e-9, msg="monotonicity (strong linear)")


def test_spearman_perfect_monotone():
    """Strictly increasing nonlinear map -> Spearman == 1 and monotonicity == 1."""
    q50 = np.linspace(-3, 3, 5000)
    y = np.exp(q50)  # strictly increasing, nonlinear
    s = spearman(q50, y)
    _approx(s, 1.0, tol=1e-9, msg="spearman (perfect monotone)")
    mono = monotonicity(q50, y)
    _approx(mono, 1.0, tol=1e-9, msg="monotonicity (perfect monotone)")
    # and a strictly DEcreasing map -> -1
    s_dec = spearman(q50, -y)
    _approx(s_dec, -1.0, tol=1e-9, msg="spearman (decreasing)")
    mono_dec = monotonicity(q50, -y)
    _approx(mono_dec, -1.0, tol=1e-9, msg="monotonicity (decreasing)")


def test_sigma_ratio_and_bias_exact():
    """sigma-ratio and bias_bps must equal their closed-form definitions exactly."""
    rng = np.random.default_rng(1)
    n = 50_000
    q50 = rng.standard_normal(n) * 0.3 + 0.01  # std~0.3, mean 0.01
    y = rng.standard_normal(n) * 1.0
    m = compute_metrics(q50, y)
    _approx(m["sigma_ratio"], np.std(q50) / np.std(y), tol=1e-9, msg="sigma_ratio")
    _approx(m["bias_bps"], float(np.mean(q50)) * 1e4, tol=1e-6, msg="bias_bps")
    _approx(m["pearson"], pearson(q50, y), tol=1e-12, msg="pearson via compute_metrics")
    assert m["n"] == n, f"n mismatch: {m['n']} != {n}"


def test_compute_metrics_full_dict_on_known():
    """End-to-end compute_metrics on y=2q+noise: every field sane & beta~2."""
    rng = np.random.default_rng(2)
    n = 100_000
    q50 = rng.standard_normal(n)
    y = 2.0 * q50 + rng.standard_normal(n) * 0.5
    m = compute_metrics(q50, y)
    _rel(m["beta"], 2.0, msg="beta full")
    _rel(m["pearson"], 2.0 / np.sqrt(4.25), msg="pearson full")
    _approx(m["monotonicity"], 1.0, tol=1e-9, msg="mono full")
    assert 0.0 < m["sigma_ratio"], "sigma_ratio must be positive"
    # for q50~N(0,1), std~1, so sigma-ratio ~ 1/sqrt(4.25) since std(y)=sqrt(4.25)
    _rel(m["sigma_ratio"], 1.0 / np.sqrt(4.25), msg="sigma_ratio full")


def test_clean_subsample_factor_from_gap():
    """Factor = ceil(600 / median_gap_sec); spacing after subsample must be >=600s."""
    # 180s grid (real perp models) -> need every 4th (720s >= 600)
    ts_180 = (np.arange(1000) * 180 * 1_000_000).astype(np.int64)
    f = clean_subsample_factor(ts_180)
    assert f == 4, f"180s gap should give factor 4, got {f}"
    assert (np.median(np.diff(ts_180)) / 1e6) * f >= 600

    # 600s grid -> factor 1 (already non-overlapping)
    ts_600 = (np.arange(1000) * 600 * 1_000_000).astype(np.int64)
    assert clean_subsample_factor(ts_600) == 1, "600s gap should give factor 1"

    # 60s grid -> factor 10
    ts_60 = (np.arange(1000) * 60 * 1_000_000).astype(np.int64)
    assert clean_subsample_factor(ts_60) == 10, "60s gap should give factor 10"

    # 1s grid -> factor 600
    ts_1 = (np.arange(2000) * 1_000_000).astype(np.int64)
    assert clean_subsample_factor(ts_1) == 600, "1s gap should give factor 600"


def test_mask_and_nan_handling():
    """compute_metrics must operate only on the finite/masked subset already passed in."""
    rng = np.random.default_rng(3)
    n = 10_000
    q50 = rng.standard_normal(n)
    y = 1.5 * q50 + rng.standard_normal(n) * 0.4
    # inject NaNs; caller is expected to mask, but compute_metrics should also guard
    q50_bad = q50.copy(); q50_bad[::500] = np.nan
    y_bad = y.copy(); y_bad[1::500] = np.nan
    m = compute_metrics(q50_bad, y_bad)
    # should drop non-finite pairs and still recover beta ~ 1.5
    _rel(m["beta"], 1.5, rtol=0.05, msg="beta with NaNs dropped")
    assert m["n"] < n, "NaN rows should have been dropped"


def main():
    tests = [
        test_pearson_and_beta_known_slope,
        test_spearman_perfect_monotone,
        test_sigma_ratio_and_bias_exact,
        test_compute_metrics_full_dict_on_known,
        test_clean_subsample_factor_from_gap,
        test_mask_and_nan_handling,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests)-failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()

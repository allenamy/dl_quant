"""TDD for the Stage-C1 cross-venue interaction factors.

Runs on a REAL 2-day spot/perp pair (positionally joined) — stronger than a
synthetic pair because it also exercises the constant-shift join the gate uses —
with a synthetic fallback if the npz caches are absent (e.g. local Mac).

Asserts:
  * 6 factors, correct shape (N, 6), all finite after finite_factors().
  * perp_spot_obi_diff_L5  == perp.obi_L5 − spot.obi_L5 at the verified index.
  * perp_spot_microdev_diff == perp.micro_dev − spot.micro_dev.
  * basis_proxy_dev is STRICTLY CAUSAL: perturbing the FUTURE tail of the basis
    series leaves all earlier basis_proxy_dev rows byte-identical (the causal
    EMA / shift(1) never peeks at ≥ t).
  * basis_proxy_dev[t] = basis[t] − causal_EMA(basis)[t]; EMA[0]=0.
  * the causal-z variant of factor 3 differs from the whole-day-z variant
    (sanity that causal_z actually changes the normalization).

Run: python multi_asset/data/test_interaction_factors.py
"""
from __future__ import annotations

import os.path as p
import sys

import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))  # repo root
from multi_asset.data.build_interaction_factors import (  # noqa: E402
    EMA_ALPHA, FACTOR_NAMES, IDX_MICRO_DEV_BPS, IDX_OBI_L5, IDX_WPB_L10,
    N_FACTORS, _causal_ema, compute_interaction_factors, finite_factors)

DATA_DIR = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data"
DAYS = ["2025-04-14", "2025-04-15"]


def _load_real_pair():
    """Positional spot/perp join over 2 days; None if caches absent."""
    sl_all, pl_all = [], []
    for day in DAYS:
        sp = p.join(DATA_DIR, "npz_spot", f"{day}.npz")
        pp = p.join(DATA_DIR, "npz_perp", f"{day}.npz")
        if not (p.exists(sp) and p.exists(pp)):
            return None, None
        s = np.load(sp, allow_pickle=True)
        q = np.load(pp, allow_pickle=True)
        sts = s["timestamps"].astype(np.int64)
        pts = q["timestamps"].astype(np.int64)
        assert sts.shape == pts.shape, f"{day}: len mismatch"
        diff = pts - sts
        assert np.all(diff == diff[0]), f"{day}: non-constant shift"
        assert abs(int(diff[0])) <= 10_000_000, f"{day}: shift out of tol"
        sl_all.append(s["X"][:, -1, :].astype(np.float64))
        pl_all.append(q["X"][:, -1, :].astype(np.float64))
    return np.concatenate(sl_all), np.concatenate(pl_all)


def _synthetic_pair(n=900, seed=0):
    rng = np.random.default_rng(seed)
    spot = rng.standard_normal((n, 64))
    perp = spot + rng.standard_normal((n, 64)) * 0.3   # correlated venues
    # make the price/vol cols positive-ish where it matters
    spot[:, 19] = np.abs(spot[:, 19]) * 1e-4 + 1e-6     # realized_vol_60s
    perp[:, 19] = np.abs(perp[:, 19]) * 1e-4 + 1e-6
    return spot, perp


def test_shape_and_finite(spot, perp):
    F = compute_interaction_factors(spot, perp)
    assert F.shape == (spot.shape[0], N_FACTORS), F.shape
    assert len(FACTOR_NAMES) == N_FACTORS
    Ff = finite_factors(F)
    assert np.all(np.isfinite(Ff)), "finite_factors must remove all non-finite"
    print(f"[PASS] shape {F.shape} + finite_factors all-finite")


def test_obi_identity(spot, perp):
    F = compute_interaction_factors(spot, perp)
    expect = perp[:, IDX_OBI_L5] - spot[:, IDX_OBI_L5]
    assert np.allclose(F[:, 0], expect, equal_nan=True), "obi_diff identity"
    micro = perp[:, IDX_MICRO_DEV_BPS] - spot[:, IDX_MICRO_DEV_BPS]
    assert np.allclose(F[:, 1], micro, equal_nan=True), "microdev_diff identity"
    print("[PASS] obi_diff_L5 == perp.obi_L5 − spot.obi_L5 (and microdev_diff)")


def test_basis_dev_causal(spot, perp):
    """Perturbing the FUTURE tail of the basis series must not change any earlier
    basis_proxy_dev row -> the EMA is strictly ≤ t-1."""
    F0 = compute_interaction_factors(spot, perp)
    n = spot.shape[0]
    cut = n // 2
    perp2 = perp.copy()
    # corrupt the basis driver (perp weighted_price_bid_L10) strictly AFTER cut
    perp2[cut + 1:, IDX_WPB_L10] += 1e6
    F1 = compute_interaction_factors(spot, perp2)
    # basis_proxy_dev (col 5) and basis_proxy_bps (col 4) for rows ≤ cut unchanged
    assert np.allclose(F0[:cut + 1, 5], F1[:cut + 1, 5], equal_nan=True), \
        "basis_proxy_dev LEAKED future info"
    assert np.allclose(F0[:cut + 1, 4], F1[:cut + 1, 4], equal_nan=True), \
        "basis_proxy_bps LEAKED future info"
    # and it SHOULD change AT/after the cut (proves the perturbation was real)
    assert not np.allclose(F0[cut + 1:, 4], F1[cut + 1:, 4]), \
        "perturbation had no effect — test is vacuous"
    print(f"[PASS] basis_proxy_dev strictly causal (rows ≤{cut} unchanged under "
          f"future corruption; rows >{cut} did change)")


def test_basis_dev_formula(spot, perp):
    F = compute_interaction_factors(spot, perp)
    basis = perp[:, IDX_WPB_L10] - spot[:, IDX_WPB_L10]
    ema = _causal_ema(basis, EMA_ALPHA)
    assert ema[0] == 0.0, "causal EMA row0 must be 0 (no past)"
    assert np.allclose(F[:, 5], basis - ema, equal_nan=True), "dev = basis − causalEMA"
    print("[PASS] basis_proxy_dev = basis − causal_EMA(basis), EMA[0]=0")


def test_causal_z_differs(spot, perp):
    F_full = compute_interaction_factors(spot, perp, causal_z=False)
    F_caus = compute_interaction_factors(spot, perp, causal_z=True)
    # all cols except factor 3 identical; factor 3 differs
    for j in range(N_FACTORS):
        if j == 2:
            assert not np.allclose(F_full[:, j], F_caus[:, j]), \
                "causal_z did not change factor 3"
        else:
            assert np.allclose(F_full[:, j], F_caus[:, j], equal_nan=True), \
                f"causal_z changed factor {j} (should only touch factor 3)"
    print("[PASS] causal_z toggles only factor 3 (spot_flow_lead_perp)")


def main():
    spot, perp = _load_real_pair()
    src = "REAL 2-day pair"
    if spot is None:
        spot, perp = _synthetic_pair()
        src = "SYNTHETIC pair (npz caches absent)"
    print(f"=== test_interaction_factors on {src}: N={spot.shape[0]} ===")
    test_shape_and_finite(spot, perp)
    test_obi_identity(spot, perp)
    test_basis_dev_causal(spot, perp)
    test_basis_dev_formula(spot, perp)
    test_causal_z_differs(spot, perp)
    print("=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    main()

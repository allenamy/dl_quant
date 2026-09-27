"""A fixed-gross zero-net counterexample, not a strategy or market estimate."""
import hashlib
import json
import math
from pathlib import Path


def dot(x, y):
    return math.fsum(a * b for a, b in zip(x, y))


def norm(x):
    return math.sqrt(dot(x, x))


def main():
    rho = .9441
    base = [.5, -.5, 0., 0.]
    orthogonal = [0., 0., .5, -.5]
    residual_ratio = math.sqrt(1. - rho * rho)
    raw = [rho * a + residual_ratio * b for a, b in zip(base, orthogonal)]
    candidate = [x / math.fsum(map(abs, raw)) for x in raw]
    measured = dot(base, candidate) / (norm(base) * norm(candidate))
    projection = dot(base, candidate) / dot(base, base)
    residual = [b - projection * a for a, b in zip(base, candidate)]
    orthogonal_share = math.fsum(map(abs, residual))
    returns = [0., 0., .1, -.1]
    # Replication preserves the construction and meets the actual diagnostic's
    # union-of-nonzero population >=20 requirement (dlarch_t2_pregate_2026.py).
    expanded_base = [x / 100 for x in base] * 100
    expanded_candidate = [x / 100 for x in candidate] * 100
    expanded_returns = returns * 100
    expanded_rho = dot(expanded_base, expanded_candidate) / (norm(expanded_base) * norm(expanded_candidate))
    result = {
        "status": "CORRELATION_IS_NOT_CAPACITY_OR_PNL_BOUND",
        "rho": measured,
        "claimed_one_minus_rho": 1. - rho,
        "base_weights": base,
        "candidate_weights": candidate,
        "both_gross": [math.fsum(map(abs, x)) for x in (base, candidate)],
        "both_net": [math.fsum(x) for x in (base, candidate)],
        "residual_l2_fraction_of_candidate": norm(residual) / norm(candidate),
        "orthogonal_l1_gross_fraction_in_this_construction": orthogonal_share,
        "synthetic_returns": returns,
        "base_pnl": dot(base, returns),
        "candidate_pnl": dot(candidate, returns),
        "sign_reversed_candidate_pnl": -dot(candidate, returns),
        "expanded_400_name_control": {
            "correlation": expanded_rho,
            "union_nonzero_names": sum(a != 0 or b != 0 for a, b in zip(expanded_base, expanded_candidate)),
            "both_gross": [math.fsum(map(abs, x)) for x in (expanded_base, expanded_candidate)],
            "both_net": [math.fsum(x) for x in (expanded_base, expanded_candidate)],
            "candidate_pnl": dot(expanded_candidate, expanded_returns),
        },
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limits": [
            "Algebraic counterexample only; no market data or performance estimate.",
            "Neither sqrt(1-rho^2) nor this example's L1 share is a production capacity estimate.",
            "Does not reverse any observed T0/T3/F10_FULL trial result.",
            "Does not prove these weights are reachable by the production mapping.",
        ],
    }
    assert abs(measured - rho) < 1e-14
    assert all(abs(x - 1.) < 1e-14 for x in result["both_gross"])
    assert result["both_net"] == [0., 0.]
    assert abs(norm(residual) / norm(candidate) - residual_ratio) < 1e-14
    assert orthogonal_share > 1. - rho
    assert result["candidate_pnl"] > 0. and result["base_pnl"] == 0.
    assert abs(expanded_rho - rho) < 1e-14
    assert result["expanded_400_name_control"]["union_nonzero_names"] == 400
    assert all(abs(x - 1.) < 1e-14 for x in result["expanded_400_name_control"]["both_gross"])
    assert result["expanded_400_name_control"]["both_net"] == [0., 0.]
    assert abs(dot(expanded_candidate, expanded_returns) - result["candidate_pnl"]) < 1e-14
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

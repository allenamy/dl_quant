"""Pure scalar oracle: current-target causality does not erase prior-target gradients.

No model fitting, engine imports, market data, credentials, or production writes.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

A1, OFFSET = 14400, 1440
# Economic milliseconds. At equal time FUNDING precedes FILL.
FUNDING = ((1, 8.0, .005), ((A1 * 1000) + 12, 10.0, .01),
           ((A1 + OFFSET) * 1000, 9.0, .03), ((A1 + 7200) * 1000, 12.0, -.02))


def cash(q_initial, q0, q1):
    events = [(ms, 0, price, rate) for ms, price, rate in FUNDING]
    events += [(OFFSET * 1000, 1, q0, None), ((A1 + OFFSET) * 1000, 1, q1, None)]
    q, rows = q_initial, []
    for ms, priority, value, rate in sorted(events):
        if priority == 1:
            q = value
        else:
            rows.append((ms, q, -q * value * rate))
    return rows


def fd(fn, x, eps=1e-6):
    return (fn(x + eps) - fn(x - eps)) / (2 * eps)


def main():
    x0, x1, initial, theta = 2.0, -3.0, 3.0, .7
    rows = cash(initial, theta * x0, theta * x1)
    # Both the early settlement and the exact-time settlement still own q0.
    assert [x[1] for x in rows] == [initial, theta*x0, theta*x0, theta*x1]
    old_component = -x0 * (10 * .01 + 9 * .03)
    new_component = -x1 * 12 * -.02
    expected = old_component + new_component
    derivative = fd(lambda t: math.fsum(x[2] for x in cash(initial, t*x0, t*x1)), theta)
    derivative_at_zero = fd(lambda t: math.fsum(x[2] for x in cash(initial, t*x0, t*x1)), 0.0)
    current_early = fd(lambda q1: cash(initial, theta*x0, q1)[1][2], theta*x1)
    prior_early = fd(lambda q0: cash(initial, q0, theta*x1)[1][2], theta*x0)
    initial_gradient = fd(lambda t: cash(initial, t*x0, t*x1)[0][2], theta)
    assert abs(derivative-expected) < 1e-9
    assert abs(derivative_at_zero-expected) < 1e-9
    assert current_early == initial_gradient == 0.0
    assert abs(prior_early + .1) < 1e-9
    # Two wrong contracts are rejected numerically by this same oracle.
    dropped_old_cash_gradient = new_component
    wrongly_backdated_gradient = -x1 * (10*.01 + 9*.03 + 12*-.02)
    assert abs(derivative-dropped_old_cash_gradient) > .1
    assert abs(derivative-wrongly_backdated_gradient) > .1
    print(json.dumps({"status": "SHARED_PARAMETER_CLOCK_ORACLE_PASS", "scope": "synthetic scalar cash only",
                      "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      "shared_theta_gradient": derivative, "analytic_gradient": expected,
                      "gradient_at_zero_baseline_quantity": derivative_at_zero,
                      "early_cash_d_current_target": current_early, "early_cash_d_prior_target": prior_early,
                      "initial_inventory_d_theta": initial_gradient,
                      "wrong_drop_predecision_cash": dropped_old_cash_gradient,
                      "wrong_charge_current_target": wrongly_backdated_gradient,
                      "limits": ["No neural-network or optimizer validation", "No profitability claim",
                                 "Quantities replace inventory at frozen execution times, not a new fill model"]}, indent=2))


if __name__ == "__main__":
    main()

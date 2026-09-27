"""Independent inventory/cash verification of a frozen simulated tape, no imports of the engine."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

TAPE_SHA = "9a5f21755eb5bd5954853d064c4e4a416d6ce69573cb6e90c2ec11e97e46c727"


def verify(tape):
    initial = tape["initial_state"]
    assert initial["positions_qty"] == {} and initial["n_positions"] == 0
    assert initial["cash_K0"] == initial["nav0_usdt"] == 100000.0
    start, end = 1672531200, 1674259200
    assert initial["t0"] == start
    trades, events = tape["trade_log"], tape["independent_ms_cash_rows"]
    assert all(start < t[0] <= end for t in trades)
    assert all(trades[i][0] <= trades[i + 1][0] for i in range(len(trades) - 1))
    assert all(events[i][0] <= events[i + 1][0] for i in range(len(events) - 1))
    logged = {}
    for ts, symbol, qty, price, rate, cash in tape["fund_log"]:
        key = (round(ts * 1000), symbol)
        assert key not in logged, (key, "duplicate cash record")
        logged[key] = (qty, price, rate, cash)
    q, used, ti = {}, set(), 0
    max_q = max_cash = 0.0
    buckets = [[] for _ in range(120)]
    for ms, symbol, recorded_q, price, rate, recorded_cash in events:
        assert type(ms) is int and start * 1000 < ms <= end * 1000
        key = (ms, symbol)
        assert key not in used
        used.add(key)
        when = ms / 1000
        # Equal-time funding belongs to the inventory before that fill.
        while ti < len(trades) and trades[ti][0] < when:
            t = trades[ti]
            old = q.get(t[1], 0.0)
            new = old + t[2]
            # The canonical engine's declared inventory cleanup, not an inferred tolerance.
            if abs(new) < 1e-9 * max(1.0, abs(old)):
                new = 0.0
            q[t[1]] = new
            ti += 1
        qty = q.get(symbol, 0.0)
        assert math.isfinite(qty) and math.isfinite(rate)
        if qty:
            assert price is not None and math.isfinite(price) and price > 0
        cash = -qty * price * rate if qty else 0.0
        dq, dc = abs(qty - recorded_q), abs(cash - recorded_cash)
        max_q, max_cash = max(max_q, dq), max(max_cash, dc)
        assert dq <= 1e-9 and dc <= 1e-8, (key, dq, dc)
        r = logged.pop(key, None)
        if r is None:
            assert cash == 0.0, (key, "missing charge")
        else:
            assert abs(qty - r[0]) <= 1e-9 and r[1] == price and r[2] == rate
            assert abs(cash - r[3]) <= 1e-8, (key, "cash disagreement")
        # Integer arithmetic defines (A, A+4h], including exact right edges.
        idx = (ms - start * 1000 - 1) // 14400000
        buckets[idx].append(cash)
    assert not logged
    assert len(trades) == 5225 and len(events) == 9104
    return {"events": len(events), "fills": len(trades), "max_quantity_error": max_q,
            "max_event_cash_error_usd": max_cash,
            "window_cash_usd": [math.fsum(x) for x in buckets]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tape", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = args.tape.read_bytes()
    assert hashlib.sha256(data).hexdigest() == TAPE_SHA
    tape = json.loads(data)
    positive = verify(tape)
    controls = {}
    for label in ("cash_plus_cent", "quantity_plus_one", "initial_inventory", "duplicate_cash"):
        x = copy.deepcopy(tape)
        if label == "cash_plus_cent":
            x["fund_log"][0][5] += .01
        elif label == "quantity_plus_one":
            x["fund_log"][0][2] += 1
        elif label == "initial_inventory":
            x["initial_state"]["positions_qty"] = {"BTCUSDT": 1}
        else:
            x["fund_log"].append(x["fund_log"][0])
        try:
            verify(x)
        except AssertionError:
            controls[label] = "REJECTED"
        else:
            raise AssertionError("mutation accepted: " + label)
    result = {"status": "ROOT_INVENTORY_CASH_PASS_FIXED_TAPE_ONLY", "tape_sha256": TAPE_SHA,
              "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "positive": positive, "controls": controls,
              "limits": ["Prices/rates are the archived engine tap, not independent venue truth",
                         "No independent window price PnL or strategy profitability claim",
                         "One seed, 120 anchors, only 9 published and 111 HOLD",
                         "No model update or deployment"]}
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "events": positive["events"],
                      "max_quantity_error": positive["max_quantity_error"],
                      "max_event_cash_error_usd": positive["max_event_cash_error_usd"],
                      "controls": controls}, indent=2))


if __name__ == "__main__":
    main()

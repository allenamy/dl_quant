"""Acceptance for FundingLedger. DRY_RUN throughout: no credentials, no venue contacted.

The property that matters most here is negative: **the §3f sign check must be able to FAIL**.
It would be trivial to build a version that never fails — derive the position from the cash flow
and the rate, and both sides of the comparison become the same two numbers. A check that cannot
fail is a green light with no bulb behind it, so the tests below deliberately feed it a wired-wrong
ledger and require it to say so.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import binance_broker as BB    # noqa: E402
import binance_funding as FL   # noqa: E402
import pilot_log as PL         # noqa: E402

FAILS = 0
DAY = 86400_000


def check(name, cond, extra=""):
    global FAILS
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(extra)) if extra else ''}")
    if not cond:
        FAILS += 1
    return cond


def mk():
    return FL.FundingLedger(BB.BinanceBroker())


NOW = 1_780_000_000_000     # fixed ms timestamp; no wall-clock dependence in assertions

print("[A] retention is treated as a hard wall, not a soft preference")
lg = mk()
check("floor is exactly 90 days back",
      lg.retention_floor_ms(NOW) == NOW - 90 * DAY)
cold = lg.gap_report(None, NOW)
check("cold start is labelled COLD_START, not silently 'fine'", cold["status"] == "COLD_START")
cont = lg.gap_report(NOW - 3 * DAY, NOW)
check("a 3-day-old ledger resumes continuously", cont["status"] == "CONTINUOUS")
gap = lg.gap_report(NOW - 200 * DAY, NOW)
check("a 200-day-old ledger reports a PERMANENT gap", gap["status"] == "PERMANENT_GAP")
check("the permanent gap states its size in days", gap["gap_days"] > 100, gap["gap_days"])
check("it says explicitly that the data cannot be recovered",
      "cannot be recovered" in gap["note"])

print("\n[B] rows are schema-shaped")
income = [{"symbol": "BTCUSDT", "time": NOW, "income": "-1.50"}]
rates = {"BTCUSDT": [(NOW, 0.0001)]}
pos = {("BTCUSDT", NOW): 15_000.0}          # long 15k, rate +1bp -> long PAYS -> income negative
rows = lg.build_rows(income, rates, pos)
missing = set(PL.SCHEMA["funding"]["required"]) - set(rows[0])
check("every required funding field present", not missing, sorted(missing) or "complete")
check("position came from OUR record, not from paid/rate",
      rows[0]["position_notional_at_settlement"] == 15_000.0)

print("\n[C] ★ the sign check PASSES on a correctly wired ledger")
v = lg.sign_consistency(rows)
check("verdict OK", v["verdict"] == "OK", v)
check("one settlement was actually checked (not vacuously zero)", v["checked"] == 1, v["checked"])

print("\n[D] ★★ the sign check FAILS on a wired-wrong ledger — it must be able to fail")
bad = [dict(r) for r in rows]
bad[0]["funding_paid"] = +1.50               # long, positive rate, yet we RECEIVED money
v2 = lg.sign_consistency(bad)
check("verdict WIRING_ERROR", v2["verdict"] == "WIRING_ERROR", v2["verdict"])
check("mismatch fraction is 100%", v2["mismatch_frac"] == 1.0, v2["mismatch_frac"])
check("an offending example is surfaced for diagnosis", len(v2["examples"]) == 1)

print("\n[E] a settlement it cannot verify is counted as UNVERIFIABLE, never as a pass")
partial = [dict(rows[0]), dict(rows[0])]
partial[1]["position_notional_at_settlement"] = None      # our record missing for this one
v3 = lg.sign_consistency(partial)
check("checked counts only the verifiable one", v3["checked"] == 1, v3["checked"])
check("the other is reported as unverifiable, not silently OK", v3["unverifiable"] == 1)

print("\n[F] with no data at all the verdict is NO_DATA, not OK")
v4 = lg.sign_consistency([])
check("empty ledger => NO_DATA (an empty check must never read as a pass)",
      v4["verdict"] == "NO_DATA", v4["verdict"])

print("\n[G] short-side sign convention is right (this is where sign bugs actually hide)")
short_rows = [{"settlement_ts": NOW / 1000, "symbol": "ETHUSDT",
               "position_notional_at_settlement": -8_000.0,     # short
               "funding_rate": 0.0002,                          # positive rate
               "funding_paid": +1.60}]                          # short RECEIVES
check("short + positive rate + received money => OK",
      lg.sign_consistency(short_rows)["verdict"] == "OK")
short_bad = [dict(short_rows[0])]
short_bad[0]["funding_paid"] = -1.60
check("short + positive rate + PAID money => WIRING_ERROR",
      lg.sign_consistency(short_bad)["verdict"] == "WIRING_ERROR")

print("\n[H] rate matching is time-bounded (a far-away rate must not be silently attached)")
far = {"BTCUSDT": [(NOW - 3600_000, 0.0001)]}       # one hour away, tolerance is 5 minutes
rows_far = lg.build_rows(income, far, pos)
check("no rate attached when none is within tolerance",
      rows_far[0]["funding_rate"] is None, rows_far[0]["funding_rate"])
check("and that settlement then counts as unverifiable, not as a pass",
      lg.sign_consistency(rows_far)["verdict"] == "NO_DATA")

print("\n[I] DRY_RUN performs no network call")
check("fetch_income returns empty without contacting the venue", lg.fetch_income(NOW - DAY) == [])
check("fetch_rates returns empty without contacting the venue", lg.fetch_rates("BTCUSDT", NOW - DAY) == [])

print(f"\n{'ALL PASS' if FAILS == 0 else str(FAILS) + ' FAIL'}")
sys.exit(1 if FAILS else 0)

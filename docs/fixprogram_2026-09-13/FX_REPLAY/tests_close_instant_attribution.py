#!/usr/bin/env python3
"""FP2-5 (PENDING_DECISIONS D5, 2026-09-17): the CLOSE-instant funding attribution rule, certified on the FROZEN engine.

Engine under test: frozen_codex_engine_7a05b4f4/ (independent researcher's book_engine_lifecycle, shas in SOURCE.txt; not modified).
RULE (written here so it is a contract, not an inference):
  R1 a funding event at exactly the CLOSE instant t, with a non-zero OLD-generation quantity, is counted ONCE, on the old
     generation, BEFORE the settlement (ORDER funding → close → open);
  R2 a funding event after the CLOSE instant for the closed generation is NOT counted (quantity is 0 after settlement);
  R3 a funding event at the OPEN instant of the new generation is NOT counted (the new generation holds 0 at that instant);
  R4 the result does not depend on the ORDER of same-ms events in the INPUT list (the engine sorts by time and kind);
  R5 a same-ms ambiguity that the engine cannot order with evidence is REFUSED, not guessed (lifecycle_events.settle);
  R6 the settlement is counted exactly once and the closed instrument cannot trade or accrue afterwards;
  R7 the funding coverage window never extends past the generation's end (coverage clipped at termination — their test kept).
Every cell below runs the real replay_book_lifecycle through their own fixture helpers; nothing is mocked.
"""
import json, os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ENG = os.path.join(HERE, "frozen_codex_engine_7a05b4f4"); sys.path.insert(0, ENG)
from tests_book_lifecycle import fixture, event, run                       # their helpers, frozen
from lifecycle_events import settle, new_state, funding as lf_funding, load_registry  # noqa: F401
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:220]) if detail is not None else ""), flush=True)
CLOSE_MS = 1500                                                            # fixture: CLOSE effective 1500; OPEN (opened=True) later
def open_ms(life):
    return [row[0] for row in life.events if row[3] == "OPEN"][0]

print("[R1] funding at the CLOSE instant on non-zero old quantity: counted once, before settlement")
life = fixture(price=100, fee=0)
r_at = run([1000, 2000], [[100], [np.nan]], [[1], [0]], life, [event(CLOSE_MS, rate=.01)])          # funding at t=CLOSE
r_none = run([1000, 2000], [[100], [np.nan]], [[1], [0]], life, [])
check("★★★ funding@CLOSE with old qty 1 ⇒ total_funding_proxy == −1 (one settlement of q·mark·rate = 1·100·0.01), settlement count 1",
      abs(r_at["state"]["total_funding_proxy"] - (-1.0)) < 1e-12 and r_at["state"]["settlement_event_count"] == 1, (r_at["state"]["total_funding_proxy"], r_at["state"]["settlement_event_count"]))
check("★★ …and exactly one funding-event's worth relative to the no-funding run", abs((r_at["research_proxy_net"] - r_none["research_proxy_net"]) - (-1.0)) < 1e-9, (r_at["research_proxy_net"], r_none["research_proxy_net"]))
print("\n[R2] funding AFTER the CLOSE instant for the closed generation is not counted")
r_after = run([1000, 2000], [[100], [np.nan]], [[1], [0]], life, [event(CLOSE_MS + 1, rate=.01)])
check("★★★ funding@CLOSE+1ms ⇒ total_funding_proxy == 0 (quantity is 0 after settlement)", r_after["state"]["total_funding_proxy"] == 0, r_after["state"]["total_funding_proxy"])
r_late = run([1000, 2000], [[100], [np.nan]], [[1], [0]], life, [event(1900, rate=.01)])
check("★★ funding well after CLOSE ⇒ 0", r_late["state"]["total_funding_proxy"] == 0, r_late["state"]["total_funding_proxy"])
print("\n[R3] funding at the OPEN instant of the new generation is not counted (it holds 0 at that instant)")
lifeo = fixture(opened=True); OPEN_MS = open_ms(lifeo)
r_open = run([1000, 2000, 3000], [[100], [np.nan], [20]], [[1], [0], [1]], lifeo, [event(OPEN_MS, rate=.01)])
check(f"★★★ funding@OPEN({OPEN_MS}) ⇒ 0 funding; new generation trades afterwards (q_after last = 5 at price 20)", r_open["state"]["total_funding_proxy"] == 0 and r_open["q_after"][-1, 0] == 5, (r_open["state"]["total_funding_proxy"], r_open["q_after"][:, 0].tolist()))
# an event AT the row where the new generation first trades is applied to the quantity held BEFORE that row's rebalance (0) —
# engine order: events at ts < limit are consumed before the row's trade; so the first funding the new generation PAYS is at a later row
r_open_same = run([1000, 2000, 3000], [[100], [np.nan], [20]], [[1], [0], [1]], lifeo, [event(3000, rate=.01)])
check("★★ funding at the SAME instant as the new generation's first trade ⇒ applied to the pre-trade quantity (0): nothing counted", r_open_same["state"]["total_funding_proxy"] == 0, r_open_same["state"]["total_funding_proxy"])
r_open_after = run([1000, 2000, 3000, 4000], [[100], [np.nan], [20], [20]], [[1], [0], [1], [1]], lifeo, [event(3500, rate=.01)])
check("★★ funding after the new generation traded (q=5 held, event mark 100, rate 0.01) ⇒ counted on the NEW quantity only: −5",
      abs(r_open_after["state"]["total_funding_proxy"] - (-5.0)) < 1e-9, r_open_after["state"]["total_funding_proxy"])
print("\n[R4] input order of same-ms events does not change the result")
lifeXY = fixture(("X", "Y"), 100, 0)
ev_a = [event(CLOSE_MS, 0, .01), event(CLOSE_MS, 1, .01)]; ev_b = list(reversed(ev_a))
ra = run([1000, 2000], [[100, 100], [np.nan, np.nan]], [[.5, .5], [0, 0]], lifeXY, ev_a)
rb = run([1000, 2000], [[100, 100], [np.nan, np.nan]], [[.5, .5], [0, 0]], lifeXY, ev_b)
check("★★★ two names, funding@CLOSE for both, either input order ⇒ identical state, funding −1 total, 2 settlements",
      ra["state"]["total_funding_proxy"] == rb["state"]["total_funding_proxy"] and abs(ra["state"]["total_funding_proxy"] - (-1.0)) < 1e-12 and ra["state"]["settlement_event_count"] == 2 == rb["state"]["settlement_event_count"] and ra["state"]["funding_prefix_sha256"] == rb["state"]["funding_prefix_sha256"],
      (ra["state"]["total_funding_proxy"], rb["state"]["total_funding_proxy"]))
print("\n[R5] same-ms ambiguity without evidence is REFUSED at the settlement primitive")
import lifecycle_events as LE
_close_rows = [row for row in life.events if row[3] == "CLOSE"]; _ev_close = _close_rows[0][4]     # the CLOSE event dict from the frozen calendar
st = new_state(100.0, {_ev_close["instrument_id"]: 1.0}); st = lf_funding(st, _ev_close["instrument_id"], CLOSE_MS, 100.0, 0.01)
def _settle_same_ms(order):
    return settle(st, _ev_close, life.registry, asof_ms=CLOSE_MS, same_time_order=order)
try:
    _settle_same_ms(None); refused = False; why = "no exception"
except ValueError as e:
    refused = True; why = str(e)
check("★★★ settlement at the same ms as a prior FUNDING with no declared order ⇒ ValueError (refused, not guessed)", refused and "same_time" in why, why)
why2 = None
try:
    s_ok = _settle_same_ms("funding_before_settlement"); ok2 = s_ok["q"][_ev_close["instrument_id"]] == 0.0 and _ev_close["instrument_id"] in s_ok["closed"]
except ValueError as e:
    ok2 = False; why2 = str(e); s_ok = None
check("★★ …and with the explicit order 'funding_before_settlement' it settles: quantity → 0, instrument closed", ok2, why2)
print("\n[R6] the closed instrument cannot accrue or trade afterwards")
why3 = "s_ok unavailable"; traded = None
if s_ok is not None:
    try:
        LE.trade(s_ok, _ev_close["instrument_id"], CLOSE_MS + 10, 1.0, 100.0); traded = True; why3 = "traded"
    except ValueError as e:
        traded = False; why3 = str(e)
check("★★★ trade on a terminated instrument ⇒ refused", traded is False and "terminated" in why3, why3)
print("\n[R7] coverage is clipped at termination (their own cell, re-run on the frozen engine)")
import unittest, io
suite = unittest.defaultTestLoader.loadTestsFromName("tests_book_lifecycle.BookLifecycleTests.test_coverage_is_clipped_at_termination")
res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
check("★★ frozen test_coverage_is_clipped_at_termination passes", res.wasSuccessful(), (res.failures, res.errors))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")

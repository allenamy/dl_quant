#!/usr/bin/env python3
"""tests_interval_d10.py -- the D10 stage 2 interval rule (lead's DECISION_RULE_D10_stage2_2026-09-26.md §1).

The load-bearing cells are the ones that would pass under the OLD behaviour too, and the ones that pin lead's
boundary ordering:

  * D3 a 3h gap must now return exactly 3.0 as SPACING_EXACT. Under the FX-DATA rule the same row is
    UNRESOLVED_NONSTANDARD_SPACING, and D11 pins that BOTH remain true at once -- two rules for two consumers,
    which is the thing most likely to be "tidied" into one by a later reader.
  * D5 a 30h gap uses the DECLARED interval and is NOT clamped to 8.0. The long-gap check must run BEFORE the
    clamp, and a device that clamps first would still pass every other cell here.
  * D6 a gap of exactly 24h is NOT "> 24h", so it clamps. Boundary wording turned into a test.
  * D8 when the declared value is needed and absent, the answer is UNRESOLVED and the iv is None -- never 8.0.
    `declared -> else spacing -> else 8.0` is the defect family this whole module exists to kill, so a silent
    8.0 here would reintroduce it at the new rule's edge.
  * D12 is the no-snapping control: one extra SECOND in the timestamp must change the returned interval. If
    anyone reintroduces grid snapping, every other cell in this file still passes and only D12 goes red.

  python3 -B tests_interval_d10.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import funding_interval as F

H = 3600
fails = []
ran = []          # derived, not restated: a hardcoded cell count drifts from the number of cell() calls
                  # (it already did -- the summary said 15/15 while 16 cells had run)


def cell(name, got, want):
    ran.append(name)
    ok = got == want
    if not ok:
        fails.append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print(f"          got  {got}")
        print(f"          want {want}")


def run():
    # D1 baseline: a clean 4h series is exact, and the value is the spacing itself
    r = F.interval_d10(1000 * H, 1004 * H, "4.0")
    cell("D1 clean 4h gap -> SPACING_EXACT 4.0", (r["tier"], r["iv"]), (F.SPACING_EXACT, 4.0))

    # D2 1h spike
    r = F.interval_d10(1000 * H, 1001 * H, "1.0")
    cell("D2 1h gap -> SPACING_EXACT 1.0", (r["tier"], r["iv"]), (F.SPACING_EXACT, 1.0))

    # D3 ★ the behaviour lead changed: 3h is an ANSWER here, not an unresolved
    r = F.interval_d10(1000 * H, 1003 * H, "4.0")
    cell("D3 ★ 3h gap -> SPACING_EXACT 3.0 (declared says 4.0 and is NOT used)",
         (r["tier"], r["iv"], r["declared_iv"]), (F.SPACING_EXACT, 3.0, 4.0))

    # D4 first event falls back to the declared interval
    r = F.interval_d10(None, 1000 * H, "8.0")
    cell("D4 first event -> DECLARED_FIRST_EVENT 8.0", (r["tier"], r["iv"]), (F.DECLARED_FIRST_EVENT, 8.0))

    # D5 ★ long gap uses declared and is NOT clamped; the order of the two rules is the test
    r = F.interval_d10(1000 * H, 1030 * H, "4.0")
    cell("D5 ★ 30h gap -> DECLARED_LONG_GAP 4.0 (not clamped to 8.0)",
         (r["tier"], r["iv"]), (F.DECLARED_LONG_GAP, 4.0))

    # D6 ★ exactly 24h is not "> 24h"
    r = F.interval_d10(1000 * H, 1024 * H, "4.0")
    cell("D6 ★ exactly 24h gap -> SPACING_CLAMPED_HIGH 8.0 (24 is not > 24)",
         (r["tier"], r["iv"], r["gap_h"]), (F.SPACING_CLAMPED_HIGH, 8.0, 24.0))

    # D7 clamps in both directions, and the raw gap is still reported
    r = F.interval_d10(1000 * H, 1012 * H, "8.0")
    cell("D7a 12h gap -> CLAMPED_HIGH 8.0, gap_h preserved",
         (r["tier"], r["iv"], r["gap_h"]), (F.SPACING_CLAMPED_HIGH, 8.0, 12.0))
    r = F.interval_d10(1000 * H, 1000 * H + 1800, "1.0")
    cell("D7b 0.5h gap -> CLAMPED_LOW 1.0, gap_h preserved",
         (r["tier"], r["iv"], r["gap_h"]), (F.SPACING_CLAMPED_LOW, 1.0, 0.5))

    # D8 ★ the defect family must not come back at the new rule's edge
    r = F.interval_d10(None, 1000 * H, None)
    cell("D8 ★ first event with NO declared -> UNRESOLVED, iv None, never 8.0",
         (r["tier"], r["iv"]), (F.DECLARED_UNAVAILABLE, None))
    r = F.interval_d10(1000 * H, 1030 * H, None)
    cell("D8b ★ long gap with NO declared -> UNRESOLVED, iv None, never 8.0",
         (r["tier"], r["iv"]), (F.DECLARED_UNAVAILABLE, None))

    # D9 non-increasing time is refused, not guessed
    r = F.interval_d10(1004 * H, 1000 * H, "4.0")
    cell("D9 non-increasing timestamps -> UNRESOLVED_NON_INCREASING_TIME, iv None",
         (r["tier"], r["iv"]), (F.NON_INCREASING_TIME, None))

    # D10 the series helper counts clamps per event, which lead requires
    fts = [1000 * H, 1004 * H, 1007 * H, 1019 * H, 1100 * H]
    out, tiers = F.interval_d10_series(fts, ["4.0"] * 5)
    cell("D10 series tiers counted per event",
         (tiers[F.DECLARED_FIRST_EVENT], tiers[F.SPACING_EXACT], tiers[F.SPACING_CLAMPED_HIGH],
          tiers[F.DECLARED_LONG_GAP], sum(tiers.values())),
         (1, 2, 1, 1, 5))
    cell("D10b series values follow the tiers",
         [x["iv"] for x in out], [4.0, 4.0, 3.0, 8.0, 4.0])

    # D11 ★ the two rules coexist deliberately: same 3h row, opposite answers, both correct
    res = F.resolve({"iv_zip": None, "iv_best": None, "iv_likely": None,
                     "iv_gap_back": "3.0", "iv_gap_fwd": "3.0"}, allow_spacing=True)
    d10 = F.interval_d10(1000 * H, 1003 * H, None)
    cell("D11 ★ 3h: FX-DATA resolve() = UNRESOLVED_NONSTANDARD_SPACING, D10 rule = SPACING_EXACT 3.0",
         (res["tier"], res["iv"], d10["tier"], d10["iv"]),
         (F.NONSTANDARD_SPACING, None, F.SPACING_EXACT, 3.0))

    # D12 ★ the no-snapping control. One extra SECOND must change the answer. If grid snapping were
    # reintroduced, every cell above still passes and only this one fails.
    a = F.interval_d10(1000 * H, 1004 * H, "4.0")["iv"]
    b = F.interval_d10(1000 * H, 1004 * H + 1, "4.0")["iv"]
    cell("D12 ★ no-snapping control: +1 second changes the interval",
         (a != b, round(b - a, 10)), (True, round(1 / 3600.0, 10)))

    # D13 constants live here and nowhere else (lead: import, never restate)
    cell("D13 boundary constants exposed for import",
         (F.SPACING_MIN_H, F.SPACING_MAX_H, F.DECLARED_FALLBACK_GAP_H), (1.0, 8.0, 24.0))

    n = len(ran)
    assert n == len(set(ran)), ("two cells share a name; a duplicate name hides a result", ran)
    print(f"\nSUMMARY {n - len(fails)}/{n} cells pass" + (f"  FAILED: {fails}" if fails else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())

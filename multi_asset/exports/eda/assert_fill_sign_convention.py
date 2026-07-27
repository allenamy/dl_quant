"""0C — make "which sign convention does this log use?" a MEASURED property, not an assumption.

> created 2026-07-27 | Session: 0C | 状态: permanent audit instrument | 作废条件: 两侧写入端统一并加了写入侧断言后, 本工具降为回归探针

WHY
---
`filled_notional` carries two different conventions in two logs that share the field name:

    testnet (real venue)   SIGNED    — buy positive, sell negative
    shadow  (simulator)    UNSIGNED  — magnitude; the direction lives in `side`

Each metrics implementation matches its own log and is 16-33x wrong on the other. The disagreement
surfaced only because two implementations were run side by side and produced different numbers —
i.e. by accident. **A convention that can only be discovered by getting an answer wrong is not a
convention, it is a trap.** This makes it a reading.

The generator is visible in one place: `engine/live/shadow_pilot_log.py` writes
`intended_notional = sgn * remaining` and, three lines later, `filled_notional = float(filled)`.
Two sibling fields on the same row, opposite conventions, one writer, no assertion between them.

WHAT IT REPORTS
---------------
  SIGNED        every filled sell is negative and every filled buy positive
  UNSIGNED      every filled row is positive AND BOTH SIDES ARE PRESENT
  MIXED         both signed and unsigned sells occur — the worst state, and the one a consumer
                cannot compensate for at all
  UNDETERMINED  too few filled rows, or only one side present. ★ A buy-only log is UNSIGNED and
                SIGNED at the same time; calling it either is inventing evidence.

★ UNDETERMINED IS NOT A PASS. `--expect` fails on it, on purpose: "I could not tell" must not be
recorded as "it matches".

Usage:
    python assert_fill_sign_convention.py --root <pilot_log dir> [--expect signed|unsigned]
    python assert_fill_sign_convention.py --selftest
Exit: 0 matches expectation (or reporting-only run that determined a convention)
      1 mismatch, or MIXED
      2 UNDETERMINED
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

MIN_FILLED_ROWS = 20          # below this, a convention reading is noise; report UNDETERMINED
MIN_PER_SIDE = 3


def read_orders(root):
    """Read order rows from a pilot_log tree without importing either pilot_log implementation.

    Deliberately dependency-free: this instrument exists to adjudicate BETWEEN the two stacks, so
    borrowing a reader from either one would make it a participant instead of a referee.
    """
    rows = []
    for p in sorted(glob.glob(os.path.join(root, "*", "orders.jsonl"))):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def classify(rows):
    filled = []
    for r in rows:
        f = r.get("filled_notional")
        if f is None:
            continue
        f = float(f)
        if f == 0:
            continue
        filled.append((str(r.get("side", "")).lower(), f))
    n = len(filled)
    tab = {("buy", "pos"): 0, ("buy", "neg"): 0, ("sell", "pos"): 0, ("sell", "neg"): 0}
    other_side = 0
    for side, f in filled:
        if side not in ("buy", "sell"):
            other_side += 1
            continue
        tab[(side, "pos" if f > 0 else "neg")] += 1
    rep = {"n_rows": len(rows), "n_filled": n, "table": {f"{a}/{b}": c for (a, b), c in tab.items()},
           "n_unknown_side": other_side,
           "n_none_filled_notional": sum(1 for r in rows if r.get("filled_notional") is None)}

    n_buy = tab[("buy", "pos")] + tab[("buy", "neg")]
    n_sell = tab[("sell", "pos")] + tab[("sell", "neg")]
    if n < MIN_FILLED_ROWS or n_buy < MIN_PER_SIDE or n_sell < MIN_PER_SIDE:
        rep["convention"] = "UNDETERMINED"
        rep["why"] = (f"needs >= {MIN_FILLED_ROWS} filled rows with >= {MIN_PER_SIDE} per side; got "
                      f"{n} filled ({n_buy} buy / {n_sell} sell). ★ A one-sided log is UNSIGNED and "
                      f"SIGNED simultaneously — there is no reading to take, only a guess.")
        return rep

    sells_neg, sells_pos = tab[("sell", "neg")], tab[("sell", "pos")]
    buys_pos, buys_neg = tab[("buy", "pos")], tab[("buy", "neg")]
    if sells_neg and sells_pos:
        rep["convention"] = "MIXED"
        rep["why"] = (f"{sells_neg} filled sells are negative and {sells_pos} are positive. No "
                      f"consumer can compensate for this: the same column means two things "
                      f"row by row.")
    elif sells_neg and not sells_pos and buys_pos and not buys_neg:
        rep["convention"] = "SIGNED"
        rep["why"] = "buys positive, sells negative, no exceptions — the venue-real convention"
    elif not sells_neg and not buys_neg:
        rep["convention"] = "UNSIGNED"
        rep["why"] = (f"all {n} filled rows positive across both sides ({n_buy} buy / {n_sell} "
                      f"sell) — a magnitude; the direction lives in `side`")
    else:
        rep["convention"] = "MIXED"
        rep["why"] = (f"neither convention fits: buy pos/neg = {buys_pos}/{buys_neg}, "
                      f"sell pos/neg = {sells_pos}/{sells_neg}")
    return rep


def exit_for(conv, expect):
    """THE exit rule, in one place. The battery below calls this, it does not restate it —
    a test that re-implements the rule it is testing agrees with itself by construction."""
    if conv == "MIXED":
        return 1
    if conv == "UNDETERMINED":
        return 2                      # never 0: "I could not tell" is not "it matches"
    if expect is None:
        return 0
    return 0 if conv.lower() == expect.lower() else 1


def run(root, expect=None, verbose=True):
    rep = classify(read_orders(root))
    rep["root"] = root
    rep["expected"] = expect
    conv = rep["convention"]
    if verbose:
        print(f"root       : {root}")
        print(f"rows       : {rep['n_rows']}  filled: {rep['n_filled']}  "
              f"filled_notional None: {rep['n_none_filled_notional']}")
        print(f"side x sign: {rep['table']}")
        print(f"CONVENTION : {conv}\n  {rep['why']}")
    rc = exit_for(conv, expect)
    if verbose and expect:
        print(f"EXPECTED   : {expect.upper()}  ->  {'MATCH' if rc == 0 else 'MISMATCH'}")
    rep["exit"] = rc
    return rc, rep


# ── red/green battery on synthetic rows: hermetic, no repo or server state ───────────────────────
def selftest():
    def rows(spec):
        out = []
        for side, sign, k in spec:
            for _ in range(k):
                out.append({"side": side, "filled_notional": sign * 100.0})
        return out

    cases = []

    def case(name, spec, expect_conv, expect_rc, expect_arg, why_red):
        conv = classify(rows(spec))["convention"]
        rc = exit_for(conv, expect_arg)          # THE rule, not a copy of it
        ok = (conv == expect_conv) and (rc == expect_rc)
        cases.append((name, conv, rc, expect_conv, expect_rc, ok, why_red))

    case("G1 venue-real shape -> SIGNED",
         [("buy", +1, 30), ("sell", -1, 25)], "SIGNED", 0, "signed",
         "red if a signed log were read as unsigned — the drop-in error that cost 32.6x")
    case("G2 simulator shape -> UNSIGNED",
         [("buy", +1, 30), ("sell", +1, 25)], "UNSIGNED", 0, "unsigned",
         "red if an unsigned log were read as signed")
    case("R1 signed log asserted as unsigned -> MISMATCH",
         [("buy", +1, 30), ("sell", -1, 25)], "SIGNED", 1, "unsigned",
         "this is the assertion that would have blocked the naive vendoring")
    case("R2 ★ MIXED (both signed and unsigned sells) -> FAIL",
         [("buy", +1, 30), ("sell", -1, 12), ("sell", +1, 13)], "MIXED", 1, "signed",
         "the state no consumer can compensate for; must never resolve to either convention")
    case("R3 ★ buy-only log -> UNDETERMINED, not UNSIGNED",
         [("buy", +1, 40)], "UNDETERMINED", 2, "unsigned",
         "a one-sided log satisfies BOTH conventions; calling it either invents evidence")
    case("R4 too few filled rows -> UNDETERMINED",
         [("buy", +1, 5), ("sell", -1, 4)], "UNDETERMINED", 2, "signed",
         "a convention read off 9 rows is noise wearing a verdict")
    case("R5 negative buys -> MIXED",
         [("buy", -1, 30), ("sell", -1, 25)], "MIXED", 1, "signed",
         "neither convention fits; the fallback must not silently pick the closer one")

    print(f"fill-sign convention battery — {len(cases)} cases\n")
    fails = [c for c in cases if not c[5]]
    for name, conv, rc, ec, erc, ok, why in cases:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}\n        got {conv}/rc={rc}, "
              f"expected {ec}/rc={erc}\n        red-when: {why}")
    print(f"\n{len(cases)-len(fails)} passed, {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--expect", choices=["signed", "unsigned"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.root:
        ap.error("--root is required (or --selftest)")
    sys.exit(run(a.root, a.expect)[0])

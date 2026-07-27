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

★★ SCOPE — MEASURED, AND NARROWER THAN "THE TWO LOGS DISAGREE" (0C, 2026-07-27)
The divergence is confined to `orders.filled_notional`. The CHILD-FILL stream agrees on both sides:

    fills.fill_notional     testnet  buy/pos 990   sell/pos 692     UNSIGNED
                            shadow   buy/pos 11934 sell/pos 11801   UNSIGNED

⇒ **Do not "harmonise" `fills.fill_notional`.** It is a different quantity — a fill MAGNITUDE used
  to weight markout — and signing it would break M2 while inventing a divergence that does not
  exist. Note the consequence: even the venue-real log carries two conventions across its two
  streams, correctly, because they answer two different questions (exposure vs size). A convention
  is a property of a COLUMN, not of a log; "make everything consistent" is the wrong repair.

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

# ★ THE CUTOVER IS DATA, NOT PROSE. `shadow_pilot_log.py` wrote UNSIGNED magnitudes until this day
# and SIGNED notionals from it onward; `run()` skips anchors already logged, so the older days stay
# as they were written (team-lead ruling: do not recompute, do not rewrite). A tree spanning the
# boundary is therefore legitimately MIXED, and a probe that reported MIXED for it would be raising
# an alarm on correct data — the failure mode 0B named, and the one that gets assertions switched
# off. Hence `--since`, and hence this constant lives here rather than in a comment.
SHADOW_SIGN_CUTOVER_DAY = "20260728"   # first day written under the signed convention


# ── the row-level rule, in ONE place: writer, tree probe and acceptance suite all call this ──────
def check_row(row):
    """(ok, reason). THE per-row convention rule — three branches, per 0B's condition (relayed by
    team-lead 2026-07-27) and adopted as a hard requirement.

      filled_notional is None  -> SKIP.  Unknown is not a violation. `skipped_unknown_fill` rows
                                  carry None precisely because the fill could not be read.
      filled_notional == 0.0   -> PASS.  ★ A MEASURED ZERO HAS NO DIRECTION. The literal two-branch
                                  form (`sign(f) must equal side`) fires on every genuine zero fill,
                                  and 0B's reason for refusing it is the one that matters:
                                  "an assertion that alarms on correct data will eventually be
                                  switched off — and once switched off it guards nothing; tonight's
                                  0-byte fingerprint file is the finished form of that outcome."
      otherwise                -> sign(filled_notional) must match the direction implied by `side`.

    ★ SIGN AUTHORITY (0B's clause, adopted): anything derived from `allOrders` / `userTrades` takes
      the VENUE-REPORTED trade direction; only the submit-response path — where no venue side
      exists yet — may use the side we submitted. His reason, recorded because it is the general
      lesson: **today the two always agree, but that is an INVARIANT, not a FACT.** A convention
      that does not name its authority will flip silently the first time either side changes.
      This function therefore reads whatever `side` the caller put on the row and does not choose
      the authority itself — choosing it is the caller's job, and the caller must be the one that
      knows which path the row came from.

    ★ ZERO SEMANTICS must be aligned row for row with 0B's edge-case table: 0.0 appears only on
      TERMINAL states; non-terminal or unread is None. Otherwise "0.0" means two different things
      on the two sides and nothing about the number reveals it.
    """
    f = row.get("filled_notional")
    if f is None:
        return True, "None — unread fill; unknown is not a violation"
    f = float(f)
    if f == 0.0:
        return True, "0.0 — a measured zero has no direction"
    side = str(row.get("side", "")).lower()
    if side not in ("buy", "sell"):
        return False, f"side is {row.get('side')!r}; cannot check a sign against no direction"
    want_pos = side == "buy"
    if (f > 0) != want_pos:
        return False, (f"filled_notional {f:+.6f} contradicts side={side} "
                       f"(buy must be positive, sell negative)")
    return True, "sign agrees with side"


def assert_row(row):
    """Raise on a violating row. Used at WRITE time, where the row can still be fixed at source.

    ★ Without this at the writer, the next vendoring recurs the same way: the convention would
    again be carried only by whoever happened to write the column, and again be discoverable only
    by two implementations disagreeing about a number.
    """
    ok, why = check_row(row)
    if not ok:
        raise ValueError(f"fill sign-convention violation: {why} | row={ {k: row.get(k) for k in ('symbol','side','terminal_reason','filled_notional')} }")


def read_orders(root, since=None):
    """Read order rows from a pilot_log tree without importing either pilot_log implementation.

    Deliberately dependency-free: this instrument exists to adjudicate BETWEEN the two stacks, so
    borrowing a reader from either one would make it a participant instead of a referee.

    `since` = "YYYYMMDD"; days before it are excluded. Used to scope past a declared convention
    cutover instead of alarming on days that are correct under the convention in force when they
    were written.
    """
    rows = []
    for p in sorted(glob.glob(os.path.join(root, "*", "orders.jsonl"))):
        day = os.path.basename(os.path.dirname(p))
        if since and day < since:
            continue
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


def exit_for(conv, expect, n_row_violations=0):
    """THE exit rule, in one place. The battery below calls this, it does not restate it —
    a test that re-implements the rule it is testing agrees with itself by construction.

    ⇒ `n_row_violations` counts rows failing `check_row`, which encodes the SIGNED convention. It
      gates the exit only where that convention is the one in force — under `--expect unsigned`
      every filled sell is a "violation" of a rule that does not apply to it, and letting that fail
      the run would be an alarm on correct data, i.e. the thing 0B's three-branch condition exists
      to prevent.
    """
    if conv == "MIXED":
        return 1
    if conv == "UNDETERMINED":
        return 2                      # never 0: "I could not tell" is not "it matches"
    signed_in_force = (expect or "").lower() == "signed" or (expect is None and conv == "SIGNED")
    if signed_in_force and n_row_violations:
        return 1
    if expect is None:
        return 0
    return 0 if conv.lower() == expect.lower() else 1


def run(root, expect=None, verbose=True, since=None):
    rows = read_orders(root, since)
    rep = classify(rows)
    # per-row violations are reported even when the tree-level verdict is clean: a single
    # contradicting row is the shape a convention breaks in, and it is invisible in the aggregate
    # until enough of them accumulate to flip the classification.
    bad = [(r, why) for r in rows for ok, why in [check_row(r)] if not ok]
    rep["n_row_violations"] = len(bad)
    rep["row_violation_examples"] = [why for _, why in bad[:3]]
    rep["since"] = since
    rep["root"] = root
    rep["expected"] = expect
    conv = rep["convention"]
    if verbose:
        print(f"root       : {root}")
        print(f"rows       : {rep['n_rows']}  filled: {rep['n_filled']}  "
              f"filled_notional None: {rep['n_none_filled_notional']}")
        print(f"side x sign: {rep['table']}")
        print(f"CONVENTION : {conv}\n  {rep['why']}")
    rc = exit_for(conv, expect, rep["n_row_violations"])
    if verbose:
        if rep["n_row_violations"]:
            print(f"row checks : {rep['n_row_violations']} row(s) fail the SIGNED per-row rule"
                  + ("" if exit_for(conv, expect, 0) == rc else "  <- this decides the exit"))
            for w in rep["row_violation_examples"]:
                print(f"             e.g. {w}")
        if expect:
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

    # ── the three branches of the per-row rule, each stated as its own case ──────────────────────
    row_cases = [
        ("B1 None filled_notional -> SKIP (unknown is not a violation)",
         {"side": "sell", "filled_notional": None}, True,
         "would go red if `skipped_unknown_fill` rows were treated as violations — punishing the "
         "writer for honestly recording that it could not read the fill"),
        ("B2 ★ 0.0 -> PASS (a measured zero has no direction)",
         {"side": "sell", "filled_notional": 0.0}, True,
         "★ THE HARD CONDITION. The literal two-branch rule fails here, i.e. on every genuine "
         "zero fill. An assertion that alarms on correct data gets switched off, and then it "
         "guards nothing."),
        ("B3 signed sell -> PASS", {"side": "sell", "filled_notional": -100.0}, True,
         "the convention itself"),
        ("B4 unsigned sell -> VIOLATION", {"side": "sell", "filled_notional": +100.0}, False,
         "this is the row shape that would have blocked the naive vendoring"),
        ("B5 negative buy -> VIOLATION", {"side": "buy", "filled_notional": -100.0}, False,
         "the mirror of B4; a rule that only checks one side checks nothing on the other"),
        ("B6 unknown side with a non-zero fill -> VIOLATION",
         {"side": None, "filled_notional": 100.0}, False,
         "a sign cannot be checked against no direction, and defaulting to 'fine' would exempt "
         "exactly the malformed rows"),
    ]
    for name, row, want_ok, why_red in row_cases:
        got_ok, why = check_row(row)
        cases.append((name, f"row_ok={got_ok}", 0 if got_ok else 1,
                      f"row_ok={want_ok}", 0 if want_ok else 1, got_ok == want_ok, why_red))

    # assert_row must RAISE on a violation — the write-time half of the same rule
    _raised = False
    try:
        assert_row({"side": "sell", "filled_notional": 100.0, "symbol": "X"})
    except ValueError:
        _raised = True
    cases.append(("B7 assert_row raises at write time", f"raised={_raised}", 0 if _raised else 1,
                  "raised=True", 0, _raised,
                  "a check that only reports cannot stop a bad row from being written; the writer "
                  "is the last place the row can still be fixed at source"))

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

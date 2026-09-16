#!/usr/bin/env python3
"""tests_spec_v2_redtests.py — the red tests of SPEC_TRADABILITY_v2_2026-09-16 section 4 (FX-DATA, FXR-DATA-1).

RT-1 and RT-2 are the independent review's own counter-examples (REVIEW_fixprogram_progress_2026-09-14.md section 4), reproduced as
running fixtures rather than paraphrased. Both are constructed markets, exactly as the review constructed them, so the cells need no
pod2 input and anyone can run them.

Each cell states which object it tests and what turns it red. The v1 branches are asserted to be WRONG on purpose: a cell that
shows v1 answering `True` where it cannot know is the evidence, not a failure of the test.

Run: python3 tests_spec_v2_redtests.py   (one line per cell, exit 1 on any failure)
"""
import os, sys, ast, inspect
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tradability as T
import holdings_register as H
import bound_bars as B

RES = []
def cell(name, obj, fn):
    try:
        fn(); RES.append((name, obj, True, ""))
    except AssertionError as e:
        RES.append((name, obj, False, "assert: %s" % e))
    except Exception as e:
        RES.append((name, obj, False, "%s: %s" % (type(e).__name__, e)))

def raises(exc, fn, needle=None):
    try:
        fn()
    except exc as e:
        assert needle is None or needle in str(e), "wrong message: %s" % e
        return
    raise AssertionError("did not raise %s" % exc.__name__)

BAR = 300
def grid(n, t0=1_600_000_000):
    return np.arange(t0, t0 + n * BAR, BAR, dtype=np.int64)

def market(n_traded_bars, n_frozen_bars):
    """one synthetic symbol: `n_traded_bars` bars with trades, then `n_frozen_bars` bars with a frozen close and zero trades"""
    lc = np.concatenate([np.full(n_traded_bars, np.float32(np.log1p(50.0))), np.zeros(n_frozen_bars, np.float32)])
    return grid(n_traded_bars + n_frozen_bars), lc.reshape(-1, 1)

# ---------------------------------------------------------------- RT-1: the 24 h tail is the window, not the venue
def _rt1():
    ts, lc = market(288, 300)                       # last trade at index 287; then frozen
    S = T.bar_states(lc)
    D = int(ts[287])
    probes = {"D+5min": D + 300, "D+23h55": D + 23 * 3600 + 55 * 60, "D+24h": D + 24 * 3600}
    st, _ = T.window_states(ts, S, np.array([probes[k] for k in ("D+5min", "D+23h55", "D+24h")], np.int64), window="W24H")
    got = {k: int(st[i, 0]) for i, k in enumerate(("D+5min", "D+23h55", "D+24h"))}
    assert got["D+5min"] == T.TRADABLE, got
    assert got["D+23h55"] == T.TRADABLE, got        # the review's number: still "tradable" almost a day after the last trade
    assert got["D+24h"] != T.TRADABLE, got
    # the v1 section 5 rule, applied verbatim: payable iff tradable
    v1_payable_at_D_plus_23h55 = (got["D+23h55"] == T.TRADABLE)
    assert v1_payable_at_D_plus_23h55 is True, "v1 would have to say False for there to be no defect"
cell("RT1_v1_calls_a_halted_name_tradable_for_23h55", "A", _rt1)

def _rt1_v2():
    raises(H.RegisterError, lambda: H.payable(1, 2), "not an activity question")
cell("RT1_v2_refuses_to_answer_payability_from_the_proxy", "A", _rt1_v2)

# ---------------------------------------------------------------- RT-2: the proxy cannot see the number that matters
def _rt2():
    """two markets, identical marks and frozen quotes, true settlement 100 vs 50, one long entered at 100"""
    tsA, lcA = market(288, 300); tsB, lcB = market(288, 300)
    assert np.array_equal(lcA, lcB) and np.array_equal(tsA, tsB)
    SA, SB = T.bar_states(lcA), T.bar_states(lcB)
    probe = np.array([int(tsA[-1])], np.int64)
    stA, _ = T.window_states(tsA, SA, probe, window="W24H")
    stB, _ = T.window_states(tsB, SB, probe, window="W24H")
    assert stA.tobytes() == stB.tobytes(), "the proxy must be shown to be blind, not assumed blind"

    ENTRY, QTY = 100.0, 1.0
    true_exit = {"A": 100.0, "B": 50.0}
    v1_pnl = {k: 0.0 for k in true_exit}            # v1: the name leaves the member set and nothing is booked
    true_pnl = {k: QTY * (v - ENTRY) for k, v in true_exit.items()}
    err = {k: v1_pnl[k] - true_pnl[k] for k in true_exit}
    assert true_pnl == {"A": 0.0, "B": -50.0}, true_pnl
    assert err == {"A": 0.0, "B": 50.0}, err        # v1 is exactly right in A and wrong by the whole loss in B
    assert v1_pnl["A"] == v1_pnl["B"], "two backtests that both refuse to price the exit agree exactly"

    # v2: identical while unresolved, different once evidence arrives
    regs, eps = {}, {}
    for k in ("A", "B"):
        r = H.HoldingsRegister(); e = r.open("X" + k, int(tsA[0]), QTY, ENTRY)
        r.mark(e, int(tsA[287]), activity=H.ACTIVE, price=ENTRY, price_evidence="TRADE", sigma24=0.05)
        r.mark(e, int(tsA[-1]), activity=H.QUIET, price=ENTRY, price_evidence="FROZEN_CLOSE")
        regs[k], eps[k] = r, e
    assert eps["A"].state == H.HELD_QUIET and eps["B"].state == H.HELD_QUIET
    assert eps["A"].price_evidence == "TRADE", "a frozen close must not be promoted to a reliable price"
    bA = eps["A"].stress_pnl(stress_basis="TO_ZERO"); bB = eps["B"].stress_pnl(stress_basis="TO_ZERO")
    assert bA == bB == (-100.0, 0.0), (bA, bB)      # identical and bounded BEFORE evidence, and they contain the true -50
    assert bA[0] <= true_pnl["B"] <= bA[1], "the registered interval must contain the true loss"
    for k in ("A", "B"):
        regs[k].close_by_evidence(eps[k], int(tsA[-1]) + 3600, true_exit[k],
                                  evidence="ANNOUNCEMENT", source="venue_notice_%s:1" % k)
    got = {k: H.settlement_pnl(QTY, ENTRY, eps[k].exit_price) for k in ("A", "B")}
    assert got == true_pnl, got                     # different once evidence differs
cell("RT2_identical_marks_different_settlement_v1_books_zero_in_both", "A+B", _rt2)

# ---------------------------------------------------------------- RT-3: archive absence is not ineligibility
def _rt3():
    ts, lc = market(0, 0) if False else (grid(300), np.full((300, 1), np.nan, np.float32))
    S = T.bar_states(lc)
    st, _ = T.window_states(ts, S, np.array([int(ts[-1])], np.int64), window="W24H")
    assert int(st[0, 0]) == T.NODATA
    # v1 section 2: "NODATA is never treated as tradable" -> an absence became a claim about ability to trade
    v1_claims_untradable = (int(st[0, 0]) != T.TRADABLE)
    assert v1_claims_untradable is True, "v1 has to make that claim for there to be a defect"
    # v2: the same admission decision, but the state is named as missing evidence
    v2 = H.activity_state(0, 0, 288, window="W24H")
    assert v2 == H.ACTIVITY_UNKNOWN, v2
    assert H.admits(v2) is False, "admission stays conservative"
    assert v2 != "INACTIVE" and "UNKNOWN" in v2, "the state must name the absence, not assert inability"
cell("RT3_nodata_is_unknown_activity_not_proven_ineligibility", "A", _rt3)

# ---------------------------------------------------------------- RT-4: zero compensation is refused
def _rt4():
    r = H.HoldingsRegister(); e = r.open("XUSDT", 1000, 1.0, 100.0)
    r.mark_unpriceable(e, 2000, "no trade-backed price in the reliability window")
    assert e.state == H.HELD_UNPRICEABLE
    assert e.exit_price is None, "an unpriceable exit must stay None, never 0"
    assert e.unknown_flag is True
    assert e.stress_pnl(stress_basis="TO_ZERO") == (None, None), "no last reliable price -> no invented interval"
    raises(H.RegisterError, lambda: H.settlement_pnl(1.0, 100.0, e.exit_price), "not defined without an exit price")
    raises(H.RegisterError, lambda: r.close_by_evidence(e, 3000, None, evidence="ANNOUNCEMENT", source="x:1"), "must name a price")
    raises(H.RegisterError, lambda: r.close_by_evidence(e, 3000, 50.0, evidence="NONE", source="x:1"))
    raises(H.RegisterError, lambda: r.close_by_evidence(e, 3000, 50.0, evidence="ANNOUNCEMENT", source=""), "name its source")
cell("RT4_no_path_writes_zero_for_an_unpriced_exit", "B", _rt4)

# ---------------------------------------------------------------- RT-5: no future information in a transition
def _rt5():
    banned = ("last_traded_ts", "dead_after", "first_traded_ts", "data_end_ts")
    for nm, fn in inspect.getmembers(H.HoldingsRegister, predicate=inspect.isfunction):
        params = set(inspect.signature(fn).parameters)
        bad = sorted(params & set(banned))
        assert not bad, "%s takes future-dependent input %s" % (nm, bad)
    src = open(H.__file__).read(); tree = ast.parse(src)
    doc_free = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name): doc_free.append(node.id)
        elif isinstance(node, ast.Attribute): doc_free.append(node.attr)
    hits = sorted(set(doc_free) & set(banned))
    assert not hits, "module code references future-dependent names %s outside its docstrings" % hits
cell("RT5_no_transition_reads_the_future", "B", _rt5)

# ---------------------------------------------------------------- RT-6: a net number may not travel alone
def _rt6():
    r = H.HoldingsRegister(); e = r.open("XUSDT", 1000, 1.0, 100.0)
    r.mark(e, 1300, activity=H.ACTIVE, price=100.0, price_evidence="TRADE", sigma24=0.04)
    r.mark(e, 1600, activity=H.QUIET)
    rep = r.report_net(0.6342, stress_basis="TO_ZERO")
    assert rep["unresolved_episodes"] == 1 and rep["interval"] is not None, rep
    assert rep["interval"][0] < rep["point"] <= rep["interval"][1], rep
    assert "unresolved" in rep["statement"] and rep["stress_basis"] == "TO_ZERO"
    r.close_by_trade(e, 1900, 100.0)
    rep2 = r.report_net(0.6342, stress_basis="TO_ZERO")
    assert rep2["unresolved_episodes"] == 0 and rep2["interval"] is None, rep2
cell("RT6_net_number_carries_the_register_interval", "B", _rt6)

# ---------------------------------------------------------------- RT-7: exit prices never from the clipped channel
def _rt7():
    bb = B.BoundBars.load(expected_sha256=B.DATA_SHA256)
    LUNA_T = 1652274600
    raises(B.BoundBarError, lambda: bb.assert_clean(["LUNAUSDT"], LUNA_T - 1, LUNA_T, window="(lo, hi]", what="exit price window"),
           "clipped ret5 bar")
    assert bb.clean(["BTCUSDT"], LUNA_T - 1, LUNA_T, window="(lo, hi]")
cell("RT7_exit_price_window_must_be_free_of_clipped_bars", "C", _rt7)

# ---------------------------------------------------------------- no-default guards carried over
def _nd():
    raises(H.RegisterError, lambda: H.activity_state(1, 0, 0, window="24h"), "no default")
    raises(TypeError, lambda: H.activity_state(1, 0, 0))
    r = H.HoldingsRegister(); e = r.open("XUSDT", 1000, 1.0, 100.0)
    raises(TypeError, lambda: e.stress_prices())
    raises(H.RegisterError, lambda: e.stress_prices(stress_basis="GUESS"), "no default")
cell("RT0_no_default_window_and_no_default_stress_basis", "A+B", _nd)

ok = sum(1 for _, _, o, _ in RES if o)
for n, obj, o, m in RES:
    print("%-58s [%-3s] %s%s" % (n, obj, "PASS" if o else "FAIL", "" if o else "   " + m))
print("SUMMARY %d/%d cells pass" % (ok, len(RES)))
sys.exit(0 if ok == len(RES) else 1)

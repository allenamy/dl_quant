#!/usr/bin/env python3
"""tests_bound_bars.py — every cell here must go red if the corresponding guard in bound_bars.py is removed (FX-DATA, RET-02).

Run: python3 tests_bound_bars.py   (prints one line per cell, exits 1 on any failure)
"""
import os, sys, time, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bound_bars as B

RES = []
def cell(name, fn):
    try:
        fn(); RES.append((name, True, ""))
    except AssertionError as e:
        RES.append((name, False, "assert: %s" % e))
    except Exception as e:
        RES.append((name, False, "%s: %s" % (type(e).__name__, e)))

def raises(exc, fn, needle=None):
    try:
        fn()
    except exc as e:
        assert needle is None or needle in str(e), "wrong message: %s" % e
        return
    raise AssertionError("did not raise %s" % exc.__name__)

# --- loading discipline -------------------------------------------------------
cell("load_requires_expected_sha", lambda: raises(TypeError, lambda: B.BoundBars.load()))
cell("load_rejects_short_sha", lambda: raises(B.BoundBarError, lambda: B.BoundBars.load(expected_sha256="94e8e8c1"), "no default"))
cell("load_rejects_wrong_sha", lambda: raises(B.BoundBarError, lambda: B.BoundBars.load(expected_sha256="0" * 64), "!= expected"))
BB = B.BoundBars.load(expected_sha256=B.DATA_SHA256)

# --- the index is the committed one ------------------------------------------
cell("index_size_955", lambda: (_ for _ in ()).throw(AssertionError("n=%d" % len(BB.ts))) if len(BB.ts) != 955 else None)
cell("index_sha_matches_r6_receipt", lambda: None if BB.sha256 == "94e8e8c119ea719a4ed1544813d433d00c39148a8e916018435ac10402a6f149"
     else (_ for _ in ()).throw(AssertionError(BB.sha256)))
cell("every_stored_value_is_the_bound", lambda: None if (np.abs(BB.clip16) == B.BOUND).all() else (_ for _ in ()).throw(AssertionError("not all at the bound")))
cell("both_signs_present", lambda: None if ((BB.raw32 > 0).any() and (BB.raw32 < 0).any()) else (_ for _ in ()).throw(AssertionError("one-sided")))

# --- window discipline: no default, and the three conventions differ ----------
cell("window_is_required", lambda: raises(TypeError, lambda: BB.hits("LUNAUSDT", 0, 1)))
cell("window_rejects_unknown", lambda: raises(B.BoundBarError, lambda: BB.hits("LUNAUSDT", 0, 1, window="24h"), "no default"))
LUNA_T = 1652274600      # 2022-05-11T13:10Z, the first row of the index
def _conventions():
    inc = BB.hits("LUNAUSDT", LUNA_T, LUNA_T, window="[lo, hi]")
    exc = BB.hits("LUNAUSDT", LUNA_T, LUNA_T, window="(lo, hi]")
    halfopen = BB.hits("LUNAUSDT", LUNA_T, LUNA_T + 1, window="[lo, hi)")
    assert len(inc) == 1 and inc[0]["ts"] == LUNA_T, inc
    assert len(exc) == 0, exc                      # (lo, hi] with lo == hi is empty
    assert len(halfopen) == 1, halfopen
cell("three_window_conventions_differ", _conventions)

# --- the guard actually fires -------------------------------------------------
cell("hits_finds_the_known_cell", lambda: None if BB.hits("LUNAUSDT", LUNA_T - 1, LUNA_T, window="(lo, hi]")[0]["raw32"] > 0.32
     else (_ for _ in ()).throw(AssertionError("raw32 not recovered")))
cell("assert_clean_raises_on_a_dirty_window",
     lambda: raises(B.BoundBarError, lambda: BB.assert_clean(["LUNAUSDT"], LUNA_T - 1, LUNA_T, window="(lo, hi]", what="unit test"), "clipped ret5 bar"))
cell("assert_clean_passes_on_a_clean_window",
     lambda: None if BB.assert_clean(["BTCUSDT"], 1652274600, 1652274600 + 86400, window="(lo, hi]") else None)
cell("clean_is_the_negation_of_hits",
     lambda: None if BB.clean("LUNAUSDT", LUNA_T - 1, LUNA_T, window="(lo, hi]") is False else (_ for _ in ()).throw(AssertionError("clean() said True on a dirty window")))
cell("unknown_symbol_is_clean_not_an_error", lambda: None if BB.clean("NOTASYMBOLUSDT", 0, 1000, window="(lo, hi]") else (_ for _ in ()).throw(AssertionError()))

# --- coverage: the index must refuse to vouch for bars it never saw -----------
cell("refuses_past_coverage_end",
     lambda: raises(B.BoundBarError, lambda: BB.clean("BTCUSDT", B.COVERAGE_END, B.COVERAGE_END + 300, window="(lo, hi]"), "past the index coverage end"))
cell("accepts_up_to_coverage_end", lambda: None if BB.clean("BTCUSDT", B.COVERAGE_END - 300, B.COVERAGE_END, window="(lo, hi]") else None)
cell("rejects_empty_window", lambda: raises(B.BoundBarError, lambda: BB.hits("BTCUSDT", 100, 99, window="(lo, hi]"), "empty window"))

# --- raw_of -------------------------------------------------------------------
cell("raw_of_returns_the_unclipped_value", lambda: None if abs(BB.raw_of("LUNAUSDT", LUNA_T) - 0.3291367) < 1e-6 else (_ for _ in ()).throw(AssertionError(str(BB.raw_of("LUNAUSDT", LUNA_T)))))
cell("raw_of_returns_None_off_index", lambda: None if BB.raw_of("BTCUSDT", LUNA_T) is None else (_ for _ in ()).throw(AssertionError("expected None")))

ok = sum(1 for _, o, _ in RES if o)
for n, o, m in RES:
    print("%-42s %s%s" % (n, "PASS" if o else "FAIL", "" if o else "   " + m))
print("SUMMARY %d/%d cells pass" % (ok, len(RES)))
sys.exit(0 if ok == len(RES) else 1)

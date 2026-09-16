#!/usr/bin/env python3
"""tests_funding_interval.py — red tests for the FND interval resolver (FX-DATA)."""
import os, sys, ast, inspect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import funding_interval as F

RES = []
def cell(n, fn):
    try: fn(); RES.append((n, True, ""))
    except AssertionError as e: RES.append((n, False, "assert: %s" % e))
    except Exception as e: RES.append((n, False, "%s: %s" % (type(e).__name__, e)))
def raises(exc, fn, needle=None):
    try: fn()
    except exc as e:
        assert needle is None or needle in str(e), "wrong message: %s" % e
        return
    raise AssertionError("did not raise %s" % exc.__name__)

ZIP = {"iv_zip": "8.0", "iv_best": "8.0", "iv_best_source": "zip", "iv_gap_back": "8.0", "iv_gap_fwd": "8.0"}
STRUCT = {"iv_zip": "", "iv_best": "4.0", "iv_best_source": "structure_steady", "iv_gap_back": "4.0", "iv_gap_fwd": "4.0"}
LIKELY = {"iv_zip": "", "iv_best": "", "iv_best_source": "unresolved_transition", "iv_likely": "4.0",
          "iv_likely_support": "structure_gap2_into_longer", "iv_gap_back": "2.0", "iv_gap_fwd": "4.0"}
EDGE = {"iv_zip": "", "iv_best": "", "iv_best_source": "unresolved_edge", "iv_likely": "", "iv_gap_back": "", "iv_gap_fwd": ""}
CONFLICT = {"iv_zip": "", "iv_best": "", "iv_best_source": "conflicting_rules:zip|interest", "iv_gap_back": "1.0", "iv_gap_fwd": "1.0"}
SWITCH = {"iv_zip": "", "iv_best": "", "iv_best_source": "", "iv_gap_back": "1.0", "iv_gap_fwd": "8.0"}
SAFE_SPACE = {"iv_zip": "", "iv_best": "", "iv_best_source": "", "iv_gap_back": "8.0", "iv_gap_fwd": "8.0"}

cell("FI1_likely_never_satisfies_a_gate", lambda: (
    (lambda r: (raises(F.IntervalError, lambda: F.gate_interval(r, what="t"), "refusing to use a LIKELY"),
                (_ for _ in ()).throw(AssertionError("iv must stay None")) if r["iv"] is not None else None,
                (_ for _ in ()).throw(AssertionError("guess must be carried separately")) if r.get("likely_iv") != 4.0 else None))
     (F.resolve(LIKELY, allow_spacing=True))))
def _fi2():
    """The column decides, in BOTH directions. The second fixture is the one that matters and my first version lacked it:
    an EMPTY iv_best with a source string that looks exact. A resolver keyed on the string would call it EXACT with iv None.
    Asserting only 'gate_interval raises' would not catch that, because it raises for the wrong reason, so the TIER is asserted."""
    a = F.resolve(dict(STRUCT, iv_best_source="unresolved_edge"), allow_spacing=False)
    assert a["tier"] == F.EXACT, "a non-null iv_best with an odd source must still be EXACT: %s" % a["tier"]
    b = F.resolve(EDGE, allow_spacing=False)
    assert b["tier"] != F.EXACT, b["tier"]
    c = F.resolve({"iv_zip": "", "iv_best": "", "iv_best_source": "structure_steady", "iv_likely": "",
                   "iv_gap_back": "", "iv_gap_fwd": ""}, allow_spacing=False)
    assert c["tier"] == F.EVIDENCE_NOT_AVAILABLE, "empty iv_best with an exact-looking source must NOT be EXACT: %s" % c["tier"]
    assert c["iv"] is None, c["iv"]
    raises(F.IntervalError, lambda: F.gate_interval(c, what="empty-best"), "refusing to use a UNRESOLVED")
cell("FI2_reads_the_column_not_the_source_string", _fi2)
cell("FI3_switch_row_is_not_spacing_safe", lambda: (
    (_ for _ in ()).throw(AssertionError("back!=fwd must be unsafe")) if F.spacing_is_safe(SWITCH) else None,
    raises(F.IntervalError, lambda: F.gate_interval(F.resolve(SWITCH, allow_spacing=True), what="switch"))))
cell("FI3b_safe_spacing_is_usable_only_when_allowed", lambda: (
    (_ for _ in ()).throw(AssertionError()) if F.gate_interval(F.resolve(SAFE_SPACE, allow_spacing=True), what="s") != 8.0 else None,
    raises(F.IntervalError, lambda: F.gate_interval(F.resolve(SAFE_SPACE, allow_spacing=False), what="s"))))
cell("FI4_two_unresolved_kinds_stay_distinguishable", lambda: (
    (_ for _ in ()).throw(AssertionError()) if F.resolve(EDGE, allow_spacing=False)["tier"] != F.EVIDENCE_NOT_AVAILABLE else None,
    (_ for _ in ()).throw(AssertionError()) if F.resolve(CONFLICT, allow_spacing=False)["tier"] != F.SOURCES_CONFLICT else None))
def _fi5():
    banned = ("sep_iv", "aug_iv", "iv_map", "intervals", "per_symbol")
    for nm, fn in inspect.getmembers(F, predicate=inspect.isfunction):
        p = set(inspect.signature(fn).parameters)
        assert not (p & set(banned)), "%s accepts a per-symbol interval map %s" % (nm, sorted(p & set(banned)))
    names = [n.id for n in ast.walk(ast.parse(open(F.__file__).read())) if isinstance(n, ast.Name)]
    assert not (set(names) & set(banned)), "module code references a per-symbol map"
cell("FI5_cannot_accept_a_pull_time_per_symbol_map", _fi5)
cell("FI6_absent_row_is_flagged_not_guessed", lambda: (
    (_ for _ in ()).throw(AssertionError()) if F.resolve(None, allow_spacing=True)["tier"] != F.NOT_IN_P9 else None,
    raises(F.IntervalError, lambda: F.gate_interval(F.resolve(None, allow_spacing=True), what="absent"))))
cell("FI7_allow_spacing_has_no_default", lambda: (
    raises(TypeError, lambda: F.resolve(ZIP)),
    raises(F.IntervalError, lambda: F.resolve(ZIP, allow_spacing="yes"), "explicit bool")))
cell("FI8_zip_column_wins_and_off_grid_iv_is_refused", lambda: (
    (_ for _ in ()).throw(AssertionError()) if F.gate_interval(F.resolve(ZIP, allow_spacing=False), what="z") != 8.0 else None,
    raises(F.IntervalError, lambda: F.gate_interval(F.resolve(dict(ZIP, iv_zip="3.0"), allow_spacing=False), what="z"), "not in the allowed set")))

ok = sum(1 for _, o, _ in RES if o)
for n, o, m in RES: print("%-52s %s%s" % (n, "PASS" if o else "FAIL", "" if o else "   " + m))
print("SUMMARY %d/%d cells pass" % (ok, len(RES)))
sys.exit(0 if ok == len(RES) else 1)

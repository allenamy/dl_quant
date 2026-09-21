#!/usr/bin/env python3
"""bt_agg_test.py — the RED TEST FOR THE CLASS behind E-0920-C, against bt_agg.py (AMENDMENT 4 §A / §D).

The class: *no aggregate may encode "not applicable / no measurement in this window" as a benign value and then average it with
real measurements* — and its twin, *no aggregate may silently drop a member and still be quoted for the whole population.*

Shape of every case here (and the reason for the order):
  1. the BASELINE IS ASSERTED GREEN FIRST on the NEW aggregator — a fully measured population must aggregate, exit green, and agree
     bit-for-bit with a naive np.mean. A red-capability check made on an already-red baseline is vacuous (that is its own ledger
     entry), so each case below prints its baseline value AND its mutated value.
  2. then the OLD aggregator (`agg_old` / `agg_old_filtered` below are the pre-fix code, copied from bt_p2_reading.py as it stood at
     sha 1e4ecf1c) is shown reporting a BENIGN number on the same input,
  3. and the NEW one is asserted to REFUSE or to SEPARATE the unmeasured members out of the headline.

  C1  no measurement because the member was HALTED BEFORE THE WINDOW   — the E-0920-C instance
  C2  no measurement for a DIFFERENT REASON: the member never had a day-stop event at all, so its per-event cost is not applicable
      — the old code dropped it with a comprehension filter, so the population it was quoted for appeared nowhere. C2 is what makes
      this a test of the CLASS rather than of `never`.
  C3  no measurement with NO convention available (the anchor at which a path breached −25%, for a path that never breached):
      the whole-population figure must come back null WITH a reason, not as some number
  C4  "someone adds an aggregate tomorrow": a brand-new block in the document that carries a mean without n_eff — the structural
      sweep must refuse the document although nothing in the sweep knows what that block is. This is the acceptance line: the fix
      has to catch a quantity that did not exist when the fix was written.
  C5  the guard itself must not pass vacuously: a document with no aggregate block at all must be REFUSED, not waved through
  C6  A5 both directions: measured-but-None is refused; unmeasured-but-carries-a-value is refused
  C7  A1/A2: a non-list population and a missing applicability classifier are refused

usage: /usr/bin/python3 bt_agg_test.py <out.json>
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bt_agg as AG

T0 = time.time()
OUTP = sys.argv[1]
RES = []


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail))
    print(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:300] if detail is not None else "", flush=True)


def refuses(fn, needle):
    """returns (did_refuse, message) — a refusal only counts when it is an AggRefusal naming the clause"""
    try:
        fn()
        return False, "no refusal"
    except AG.AggRefusal as e:
        return (needle in str(e)), str(e)[:200]


# ---------------------------------------------------------------- the PRE-FIX aggregators, copied verbatim in behaviour
def agg_old(vals, key):
    """bt_p2_reading.py's aggregator before the fix: it drops None, counts what is left, and averages whatever value it is handed
    — including a 0.0 that some upstream step substituted for 'this member did not trade in the window'."""
    v = [x[key] for x in vals if x.get(key) is not None]
    return {"mean": (float(np.mean(v)) if v else None), "p05": (float(np.percentile(v, 5)) if v else None),
            "median": (float(np.percentile(v, 50)) if v else None), "p95": (float(np.percentile(v, 95)) if v else None), "n": len(v)}


def agg_old_filtered(members, value_key, applicable):
    """the other pre-fix shape, from flatten_costs_per_path: the population is filtered by a comprehension BEFORE aggregation, so
    the members that were dropped appear nowhere in the output at all."""
    return agg_old([m for m in members if applicable(m)], value_key)


MEASURED = lambda m: None                                                   # noqa: E731 - every member has a measurement


# ================================================================ C0  baseline GREEN on the NEW aggregator, asserted first
base_pop = [{"id": i, "v": float(x)} for i, x in enumerate([-0.2594, -0.2521, -0.2482, -0.2392, -0.2292])]
b = AG.block("end_return_P2", base_pop, lambda m: m["v"], MEASURED, population_name="5 fill paths", id_of=lambda m: m["id"])
naive = float(np.mean([m["v"] for m in base_pop]))
ok("C0.BASELINE_GREEN new aggregator on a fully measured population == naive np.mean, bit for bit",
   b["measured"]["n_eff"] == 5 and b["no_measurement"]["n"] == 0 and abs(b["measured"]["mean"] - naive) < 1e-15
   and b["whole_population"]["equals_measured"] is True and abs(b["whole_population"]["mean"] - naive) < 1e-15,
   {"new_mean": b["measured"]["mean"], "naive_mean": naive, "n_eff": b["measured"]["n_eff"]})
ok("C0.BASELINE_GREEN the same population also passes the structural sweep (so a later refusal is a real signal)",
   AG.sweep_or_refuse({"x": b}, min_blocks=2)["violations"] == 0,
   AG.sweep_or_refuse({"x": b}, min_blocks=2))

# ================================================================ C1  no measurement: halted BEFORE the reporting window
WINDOW = "2023-06-30T04:00Z → 2026-08-31T00:00Z"
c1 = [{"id": i, "v": v, "why": w} for i, (v, w) in enumerate([
    (-0.2594, None), (-0.2521, None), (-0.2482, None), (-0.2392, None), (-0.2292, None), (-0.2511, None),
    (None, "day-stopped before the window started, so no anchor of this window was ever traded"),
    (None, "day-stopped before the window started, so no anchor of this window was ever traded")])]
c1_measured = [m["v"] for m in c1 if m["why"] is None]
# step 2: what the OLD aggregator says, once the upstream substitution has already happened
c1_as_old_saw_it = [{"end": (m["v"] if m["why"] is None else 0.0)} for m in c1]
old1 = agg_old(c1_as_old_saw_it, "end")
ok("C1.the OLD aggregator reports a benign mean, and its n EQUALS the population — so 'n was reported' was never the guard",
   old1["n"] == len(c1) and old1["mean"] > float(np.mean(c1_measured)) + 0.02,
   {"old_mean": old1["mean"], "old_n": old1["n"], "population": len(c1), "truth_on_measured": float(np.mean(c1_measured))})
# step 3: the NEW aggregator separates them
new1 = AG.block("end_return_P2", c1, lambda m: m["v"], lambda m: m["why"], population_name="8 fill paths, window " + WINDOW,
                id_of=lambda m: m["id"],
                whole_population_convention={"name": "a path withheld for the entire window contributes its flat-book return of "
                                                     "exactly 0", "value_for_unmeasured": 0.0})
ok("C1.the NEW aggregator keeps the unmeasured members OUT of the headline mean",
   new1["measured"]["n_eff"] == 6 and abs(new1["measured"]["mean"] - float(np.mean(c1_measured))) < 1e-15,
   {"measured_mean": new1["measured"]["mean"], "n_eff": new1["measured"]["n_eff"]})
ok("C1.the NEW aggregator NAMES the subset and lists its members (they are findable, not just excluded)",
   new1["no_measurement"]["n"] == 2 and len(new1["no_measurement"]["by_reason"]) == 1
   and list(new1["no_measurement"]["by_reason"].values())[0]["members"] == [6, 7],
   new1["no_measurement"])
ok("C1.the NEW aggregator still reports the whole-population figure, under a NAMED convention (A3'): the old number is not hidden",
   new1["whole_population"]["equals_measured"] is False and abs(new1["whole_population"]["mean"] - old1["mean"]) < 1e-15
   and "flat-book" in new1["whole_population"]["convention"],
   {"whole_population_mean": new1["whole_population"]["mean"], "old_mean": old1["mean"],
    "convention": new1["whole_population"]["convention"]})
ok("C1.the two figures differ by the amount the defect was worth, and both carry n_eff",
   abs((new1["whole_population"]["mean"] - new1["measured"]["mean"]) - (old1["mean"] - float(np.mean(c1_measured)))) < 1e-15
   and new1["measured"]["n_eff"] == 6 and new1["whole_population"]["n_eff"] == 8,
   {"pp_gap": 100 * (new1["whole_population"]["mean"] - new1["measured"]["mean"])})

# ================================================================ C2  a DIFFERENT reason: no day-stop event at all in this member
c2 = [{"id": i, "cost": c, "why": w} for i, (c, w) in enumerate([
    (5.38, None), (5.32, None), (5.49, None),
    (None, "this path had no day-stop event at all, so a per-event cost is not applicable to it"),
    (None, "this path had no day-stop event at all, so a per-event cost is not applicable to it")])]
old2 = agg_old_filtered(c2, "cost", lambda m: m["why"] is None)
ok("C2.the OLD shape silently shrank the population: it reports n=3 while being quoted for 5, and the 2 dropped members appear "
   "NOWHERE in its output", old2["n"] == 3 and "population" not in old2 and abs(old2["mean"] - 5.3966666666666665) < 1e-12,
   {"old": old2, "quoted_for": len(c2)})
new2 = AG.block("window_fee_bps_of_gross", c2, lambda m: m["cost"], lambda m: m["why"],
                population_name="5 fill paths", id_of=lambda m: m["id"])
ok("C2.the NEW aggregator declares the population of 5, measures 3, and NAMES the other reason class",
   new2["population"]["n"] == 5 and new2["measured"]["n_eff"] == 3 and new2["no_measurement"]["n"] == 2
   and "no day-stop event" in list(new2["no_measurement"]["by_reason"])[0],
   {"population_n": new2["population"]["n"], "n_eff": new2["measured"]["n_eff"],
    "reasons": list(new2["no_measurement"]["by_reason"])})
ok("C2.this reason is NOT the C1 reason — the fix is about the class, not about 'never'",
   list(new2["no_measurement"]["by_reason"])[0] != list(new1["no_measurement"]["by_reason"])[0],
   {"C1_reason": list(new1["no_measurement"]["by_reason"])[0], "C2_reason": list(new2["no_measurement"]["by_reason"])[0]})
ok("C2.with no convention declared, the whole-population figure is null WITH a reason — not a number, not an absent key",
   new2["whole_population"]["mean"] is None and "no whole-population convention" in new2["whole_population"]["refused_because"]
   and new2["whole_population"]["n_eff"] == 3 and new2["whole_population"]["population_n"] == 5,
   new2["whole_population"])

# ================================================================ C3  a quantity for which NO convention can exist
c3 = [{"id": i, "t": t, "why": w} for i, (t, w) in enumerate([
    (1710720000.0, None), (1710806400.0, None),
    (None, "this path never breached −25% in this window, so it has no breach anchor")])]
new3 = AG.block("cum25_anchor_epoch", c3, lambda m: m["t"], lambda m: m["why"], population_name="3 fill paths",
                id_of=lambda m: m["id"], unit="epoch seconds")
ok("C3.a genuinely undefined quantity refuses its whole-population figure instead of inventing one",
   new3["whole_population"]["mean"] is None and new3["measured"]["n_eff"] == 2, new3["whole_population"])

# ================================================================ C4  THE ACCEPTANCE LINE: an aggregate added tomorrow
doc_tomorrow = {"runs": {"A0": {"bases": {"FULL_RECIPE": {"never": {"end_return_P2": new1, "anchors_withheld": new2}}}}},
                # someone adds this next week, by hand, without going through bt_agg.block():
                "new_diagnostic_added_later": {"turnover_ratio": {"mean": 1.0005, "median": 0.9999, "p95": 1.0056}}}
red4, msg4 = refuses(lambda: AG.sweep_or_refuse(doc_tomorrow, min_blocks=2), "A4 structural sweep")
ok("C4.a NEW aggregate nobody wrote a rule for is refused, because the sweep walks the document rather than a list of quantities",
   red4 and "new_diagnostic_added_later" in msg4, {"refusal": msg4})
del doc_tomorrow["new_diagnostic_added_later"]
ok("C4.BASELINE_GREEN the same document WITHOUT that block passes — so C4's red is the block, not a document that was always red",
   AG.sweep_or_refuse(doc_tomorrow, min_blocks=2)["violations"] == 0, AG.sweep_or_refuse(doc_tomorrow, min_blocks=2))

# ================================================================ C5  the guard must not pass vacuously
red5, msg5 = refuses(lambda: AG.sweep_or_refuse({"notes": "no aggregates here at all"}, min_blocks=1), "vacuously")
ok("C5.a document with zero aggregate blocks is REFUSED, not waved through ('zero measurements also passes' does not exempt the "
   "guard itself)", red5, {"refusal": msg5})

# ================================================================ C6  A5, both directions
red6a, msg6a = refuses(lambda: AG.block("x", [{"id": 0, "v": None}], lambda m: m["v"], MEASURED, population_name="p",
                                        id_of=lambda m: m["id"]), "(A5)")
ok("C6.measured-but-None is refused: an unexplained missing value must be NAMED before it can be excluded", red6a, {"refusal": msg6a})
red6b, msg6b = refuses(lambda: AG.block("x", [{"id": 0, "v": 1.0}], lambda m: m["v"], lambda m: "not applicable",
                                        population_name="p", id_of=lambda m: m["id"]), "(A5)")
ok("C6.unmeasured-but-carries-a-value is refused: the classifier and the data must be reconciled first", red6b, {"refusal": msg6b})

# ================================================================ C7  A1 / A2
red7a, msg7a = refuses(lambda: AG.block("x", (m for m in base_pop), lambda m: m["v"], MEASURED, population_name="p"), "(A1)")
ok("C7.a population that is not an explicit closed list is refused (a generator has already hidden its filtering)", red7a,
   {"refusal": msg7a})
red7b, msg7b = refuses(lambda: AG.block("x", base_pop, lambda m: m["v"], None, population_name="p"), "(A2)")
ok("C7.aggregating without declaring an applicability classifier is refused", red7b, {"refusal": msg7b})

# ================================================================ ROUND-7 REVIEW G-04 / G-05
# Same shape as everything above: the PRE-FIX code is reproduced here verbatim in behaviour, shown GREEN on the very input the
# fixed code refuses, so no row is a red-red pair and no red is claimed on a baseline that was already red.
STAT_TRIGGER_PREFIX = ("mean", "median", "p05", "p95")          # bt_agg.py:32 as it stood at commit 2814d4fd6


def sweep_prefix(doc, min_blocks):
    """A4 EXACTLY as it was before 2026-09-21: a WHITELIST of four statistic names, key presence only, no block relations at all"""
    bad, seen = [], []

    def walk(o, path):
        if isinstance(o, dict):
            if any(k in o for k in STAT_TRIGGER_PREFIX):
                seen.append(path)
                if [k for k in ("n_eff", "population_n") if k not in o]: bad.append(path)
            for k, v in o.items(): walk(v, f"{path}.{k}")
        elif isinstance(o, (list, tuple)):
            for i, v in enumerate(o): walk(v, f"{path}[{i}]")

    walk(doc, "$")
    if bad: raise AG.AggRefusal("PRE-FIX A4 structural sweep: " + json.dumps(bad[:4]))
    if len(seen) < int(min_blocks): raise AG.AggRefusal("PRE-FIX A4 structural sweep inspected %d, vacuously" % len(seen))
    return {"aggregate_blocks_swept": len(seen)}


def count_contract_blocks_prefix(doc):
    """the census as it was: `whole_population` was NOT part of a block's identity, so deleting one side left the count unchanged"""
    n = [0]

    def walk(o):
        if isinstance(o, dict):
            if "quantity" in o and "population" in o and "measured" in o and "no_measurement" in o: n[0] += 1
            for v in o.values(): walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o: walk(v)

    walk(doc)
    return n[0]


def prefix_is_green(fn):
    try:
        fn(); return True, "green"
    except AG.AggRefusal as e:
        return False, str(e)[:160]


import copy as _copy                                                                                    # noqa: E402
import tempfile as _tempfile                                                                            # noqa: E402

REAL = {"runs": {"A0": {"12": {"W_ENTRY": {"summary": {"end_return_P2": new1, "anchors_withheld": new2, "fully_measured": b}}}}}}
MINB = 6                                                                      # three blocks x two sides
g0_new = AG.sweep_or_refuse(REAL, MINB)
g0_old = prefix_is_green(lambda: sweep_prefix(REAL, MINB))
ok("G0.BASELINE_GREEN a document of three real contract blocks passes BOTH the pre-fix sweep and the fixed one — every G-04/G-05 "
   "red below is therefore the mutation, not a document that was always red",
   g0_new["violations"] == 0 and g0_old[0] and AG.count_contract_blocks(REAL) == 3,
   {"fixed_sweep": g0_new, "prefix_sweep": g0_old[1], "contract_blocks": AG.count_contract_blocks(REAL)})

# ---------------------------------------------------------------- G-04  the two sides must AGREE, not merely be present
g4a = _copy.deepcopy(REAL); _wp = g4a["runs"]["A0"]["12"]["W_ENTRY"]["summary"]["fully_measured"]["whole_population"]
_wp["mean"], _wp["n_eff"] = 123456.0, 999                                  # equals_measured stays true — the reviewer's mutation
ok("G4a.the PRE-FIX write side accepts whole_population.mean=123456 / n_eff=999 with equals_measured still true",
   prefix_is_green(lambda: sweep_prefix(g4a, MINB))[0], {"mutation": "equals_measured=true but the two sides now differ"})
_p4a = os.path.join(_tempfile.mkdtemp(), "g4a.json")
red4a, msg4a = refuses(lambda: AG.write_json_checked(g4a, _p4a, min_blocks=MINB), "equals_measured")
ok("G4a.the fixed write side REFUSES it at the real persistence entry point, and writes no file",
   red4a and not os.path.exists(_p4a), {"refusal": msg4a, "file_written": os.path.exists(_p4a)})

g4b = _copy.deepcopy(REAL); _s = g4b["runs"]["A0"]["12"]["W_ENTRY"]["summary"]
_s["fully_measured"] = {k: v for k, v in _s["fully_measured"].items() if k != "whole_population"}
_s["an_unrelated_stats_dict"] = {"mean": 0.1, "median": 0.1, "p05": 0.0, "p95": 0.2, "n_eff": 3, "population_n": 3}
ok("G4b.the PRE-FIX side accepts a block with one side DELETED, and its census count is unchanged because `whole_population` was "
   "not part of a block's identity — so the count could be padded back with an unrelated statistics dict",
   prefix_is_green(lambda: sweep_prefix(g4b, MINB))[0] and count_contract_blocks_prefix(g4b) == 3,
   {"prefix_census": count_contract_blocks_prefix(g4b), "fixed_census": AG.count_contract_blocks(g4b)})
_p4b = os.path.join(_tempfile.mkdtemp(), "g4b.json")
red4b, msg4b = refuses(lambda: AG.write_json_checked(g4b, _p4b, min_blocks=MINB), "required side(s)")
ok("G4b.the fixed side REFUSES the mutilated block by NAME, writes no file, and its census drops to 2 (the padding cannot "
   "compensate)", red4b and not os.path.exists(_p4b) and AG.count_contract_blocks(g4b) == 2,
   {"refusal": msg4b, "fixed_census": AG.count_contract_blocks(g4b)})

g4c = _copy.deepcopy(REAL); _wc = g4c["runs"]["A0"]["12"]["W_ENTRY"]["summary"]["end_return_P2"]["whole_population"]
_wc["mean"] = float(_wc["mean"]) + 0.05                                    # a compensated total under the NAMED convention
ok("G4c.the PRE-FIX side accepts a whole-population mean that its own named convention does not produce",
   prefix_is_green(lambda: sweep_prefix(g4c, MINB))[0], {"mutation": "convention mean moved by +0.05"})
red4c, msg4c = refuses(lambda: AG.sweep_or_refuse(g4c, MINB), "named convention forces")
ok("G4c.the fixed side re-derives (n_measured·mean_measured + n_unmeasured·value_for_unmeasured)/n and REFUSES", red4c,
   {"refusal": msg4c})

red4d, msg4d = refuses(lambda: AG.block("x", [{"id": 0, "v": 1.0}, {"id": 0, "v": 2.0}], lambda m: m["v"], MEASURED,
                                        population_name="p", id_of=lambda m: m["id"]), "more than once")
ok("G4d.a population that names the same member twice is refused — [seed0, seed0] has the COUNT of the closed population, which "
   "is why counts were never the guard (A1)", red4d, {"refusal": msg4d})

g4e = _copy.deepcopy(REAL); _bk = g4e["runs"]["A0"]["12"]["W_ENTRY"]["summary"]["end_return_P2"]
_bk["no_measurement"]["by_reason"][list(_bk["no_measurement"]["by_reason"])[0]]["members"][-1] = 9999   # count kept, id foreign
ok("G4e.the PRE-FIX side accepts a no-measurement member that is not in the declared population",
   prefix_is_green(lambda: sweep_prefix(g4e, MINB))[0], {"mutation": "unmeasured member id 9999, not a member"})
red4e, msg4e = refuses(lambda: AG.sweep_or_refuse(g4e, MINB), "not in the declared population")
ok("G4e.the fixed side REFUSES it (membership closure between the population and the named subsets)", red4e, {"refusal": msg4e})

# ---------------------------------------------------------------- G-05  the statistic trigger is INVERTED, not extended
g5 = {}
for _k in ("min", "max", "p50", "median_element", "std", "iqr", "cvar95"):
    d = _copy.deepcopy(REAL); d["a_diagnostic_added_later"] = {"two": {"levels": {_k: 0.0}}}
    old_ok = prefix_is_green(lambda dd=d: sweep_prefix(dd, MINB))[0]
    new_red, new_msg = refuses(lambda dd=d: AG.sweep_or_refuse(dd, MINB), "A4 structural sweep")
    g5[_k] = {"prefix_gate_green": old_ok, "fixed_gate_red": new_red, "refusal": new_msg[:120]}
ok("G5.every one of min/max/p50/median_element/std — AND names nobody has used yet (iqr, cvar95) — is GREEN on the pre-fix "
   "whitelist and RED on the inverted trigger. The acceptance question is the last two: a statistic invented tomorrow is caught "
   "by NOT being classified, instead of by being remembered.",
   all(v["prefix_gate_green"] and v["fixed_gate_red"] for v in g5.values()), g5)
d_ctl = _copy.deepcopy(REAL); d_ctl["a_diagnostic_added_later"] = {"two": {"levels": {"mean": 0.0}}}
ok("G5.POSITIVE_CONTROL the same injection keyed `mean` IS red on the pre-fix sweep — so the seven rows above are the whitelist's "
   "blind spot and not a harness that cannot refuse anything",
   not prefix_is_green(lambda: sweep_prefix(d_ctl, MINB))[0], {"prefix": prefix_is_green(lambda: sweep_prefix(d_ctl, MINB))[1]})

# the two shapes the inverted trigger found ALREADY PUBLISHED in the committed receipts (34 per P document, 244 per P2 document)
for _name, _val in (("cum25_anchor_median_utc", "2024-03-18T00:00:00Z"), ("first_breach_median", "2024-03-18T00:00:00Z")):
    d = _copy.deepcopy(REAL); d["runs"]["A0"]["12"]["W_ENTRY"]["summary"][_name] = _val
    old_ok = prefix_is_green(lambda dd=d: sweep_prefix(dd, MINB))[0]
    new_red, new_msg = refuses(lambda dd=d: AG.sweep_or_refuse(dd, MINB), _name)
    ok(f"G5.REAL_SHAPE `{_name}` persisted as a bare median beside a summary is green on the pre-fix whitelist and RED now — this "
       f"is the shape the committed P/P2 receipts actually carry, and a STRING value, so a type-based trigger would have missed "
       f"it too", old_ok and new_red, {"prefix_green": old_ok, "refusal": new_msg[:180]})
    d2 = _copy.deepcopy(REAL)
    d2["runs"]["A0"]["12"]["W_ENTRY"]["summary"][_name] = AG.one_value_block(_val, 5, 8, "the element rule sorted(fired)[k // 2]")
    ok(f"G5.the FIXED producer shape for `{_name}` (bt_agg.one_value_block, carrying its own n_eff/population_n) passes",
       AG.sweep_or_refuse(d2, MINB)["violations"] == 0, AG.sweep_or_refuse(d2, MINB))

red5s, msg5s = refuses(lambda: AG.sweep_or_refuse(dict(REAL, a_key_nobody_classified={"deeper": {"turnover_ratio": 1.0}}), MINB),
                       "NON_STATISTIC_KEYS")
ok("G5.the refusal NAMES the remedy: an unclassified scalar key is refused with the instruction to classify it in "
   "bt_agg.NON_STATISTIC_KEYS with its reason — failing closed, with the way out written down", red5s, {"refusal": msg5s})

fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_agg_test.py", self_sha256=AG.__dict__ and __import__("hashlib").sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           tested=__import__("hashlib").sha256(open(os.path.join(HERE, "bt_agg.py"), "rb").read()).hexdigest(),
           argv=sys.argv, numpy=np.__version__, checks=RES, failed=fails, VERDICT="PASS" if not fails else "RED",
           runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
print("BT_AGG_TEST VERDICT: " + ("ALL PASS %d/%d checks (baseline asserted GREEN on the new aggregator first; every pre-fix shape "
                                 "shown benign and every new one red)" % (len(RES), len(RES))
                                 if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails)), flush=True)
sys.exit(0 if not fails else 3)

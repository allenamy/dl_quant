#!/usr/bin/env python3
"""bt_agg.py — the AGGREGATION CONTRACT of AMENDMENT 4 (docs/AMENDMENT_4_baseline_tables_aggregation_contract_2026-09-20.md),
written after E-0920-C ("永不恢复" summary encoded "halted before the window ⇒ no trading in the window" as end = 0.0 and averaged
it together with real losses, lifting the mean by 3.14 pp).

THE CLASS, not the instance: *no aggregate may encode "not applicable / no measurement in this window" as a benign value and then
average it with real measurements.* Same family as "unknown is not zero" and "zero measurements also passes" — this is their
AGGREGATE form.

The five clauses, all enforced here, none of them a list of affected quantities:
  A1 CLOSED POPULATION — the caller hands in an explicit list; filtering members out before the call is the defect itself, because a
     dropped member appears nowhere in the output. `block()` refuses anything that is not a list/tuple, records every member id, and
     (round-7 G-03/G-04) refuses a population that names the same member twice: `[seed0, seed0]` is a selected population wearing the
     size of the full one.
  A2 NAMED NO-MEASUREMENT SUBSET — `applicability(member)` returns None (measured) or a NON-EMPTY STRING naming why there is none.
     Those members go to no_measurement.by_reason[<name>] with their ids and NEVER enter a mean or a percentile.
  A3' BOTH FIGURES OR REFUSE — `measured` (the headline: n_eff/mean/median/p05/p95/min/max) AND `whole_population`. The whole
     population figure exists only under a NAMED convention for what an unmeasured member contributes; without one its mean is null
     with `refused_because`. Neither side may simply be absent.
  A3'' RELATIONS BETWEEN THE SIDES ARE VERIFIED, NOT BELIEVED (added 2026-09-21, round-7 review G-04). Presence was the whole of the
     old write-side check, so the reviewer could set `whole_population.mean = 123456, n_eff = 999` while leaving
     `equals_measured = true`, or delete one side and pad the block census with an unrelated statistics dict, and the document still
     wrote. `validate_aggregate_block()` now re-derives every relation from the block's own contents on the way out:
     population.members is closed and duplicate-free; measured.n_eff + no_measurement.n == population.n; every no-measurement id is a
     member, named once, under exactly one reason; `equals_measured = true` MEANS the two sides are equal (checked key by key) and
     that nothing was unmeasured; and under a named convention the whole-population mean must equal the weighted combination
     (n_measured·mean_measured + n_unmeasured·value_for_unmeasured) / n — a compensated total is no longer a way through.
  A4 n_eff BESIDE EVERY PERSISTED STATISTIC — enforced by `sweep_or_refuse()` over the WHOLE output document just before it is
     written. THE TRIGGER IS INVERTED (2026-09-21, round-7 review G-05). It used to be the whitelist
     `STAT_TRIGGER = (mean, median, p05, p95)`, which answers "is this one of the four aggregates I have already seen?" — so a dict
     keyed `min` / `max` / `p50` / `median_element` / `std` carried no n_eff and sailed straight through, and `median_element` is a
     name the sibling P device actually uses. Now every SCALAR-valued key is a persisted statistic UNLESS it is declared in
     `NON_STATISTIC_KEYS` as something else (a member value, a count, a population size, a configuration echo, provenance, prose).
     A name nobody classified fails CLOSED, naming its path and its key, so tomorrow's `std` / `cvar95` / `skew` is caught by not
     being on a list rather than by being on one. Strings count too: `cum25_anchor_median_utc` is a median whose value is an ISO
     string, and a type-based trigger would have missed it exactly as the name-based one did.
     `min_blocks` stops the sweep from passing vacuously on a document with no statistics.
  A5 NO BENIGN SUBSTITUTION — a member classified measured whose value is None is refused (an unexplained missing value is not a
     class; name it first); a member classified unmeasured that still carries a value is refused (classifier and data disagree).

COST OF FAILING CLOSED, stated on purpose: adding a new non-statistic field to one of these documents is a REFUSAL until it is
classified in `NON_STATISTIC_KEYS`. That is the point — "the sweep did not recognise this key" must never read the same as "the
sweep checked this key". The refusal message says exactly which key at which path to classify.

Import-only library: it has no __main__ and reads nothing from the environment.
"""
import json
import math
import os

import numpy as np

# ---------------------------------------------------------------------------------------------------------------------------
# A4 INVERTED TRIGGER (round-7 G-05). Every scalar-valued key is treated as a persisted statistic unless it is named here with the
# reason it is NOT one. Derived from a census of every document this contract actually writes (the six committed P/P2 receipts
# BT_P_READING_{A0,A0X,V4} and BT_P2_READING_{A0,A0ext,V4}, 86 distinct scalar-valued keys, of which nine are statistics:
# mean median p05 p95 min max median_element first_breach_median cum25_anchor_median_utc). Kept as a dict so every entry carries
# the reason it is exempt; an unexplained entry is the same defect one level up.
NON_STATISTIC_KEYS = {
    # --- per-member values: one member's own number, not a summary of a population -------------------------------------------
    "anchors_after_halt": "per path: anchors left after its halt", "anchors_in_window": "per path: window length",
    "anchors_to_breach_by": "per start: anchors from the start to breach_by", "anchors_traded_in_window": "per path",
    "anchors_withheld": "per flatten event: anchors that event withheld", "anchors_withheld_by_day_stop": "per path",
    "cum25_anchor": "per path: the anchor at which it breached", "cum25_anchor_epoch": "per path, the same in epoch seconds",
    "cum_at_cum25": "per path: its cumulative return at the breach", "cum_at_halt": "per path: cumulative return at its halt",
    "day_stop_events_in_scope": "per path", "day_stop_events_in_window": "per path",
    "end_return_P2": "per path (and the mean path, which is its own named whole-population object)",
    "end_return_no_halt": "per path", "end_return_nohalt": "per path (reading P spelling)", "end_return_phalt": "per path",
    "halt_anchor": "per path: the anchor at which it halted", "halt_index": "per path: that anchor's index",
    "share_anchors_after_halt": "per path", "turnover_flatten_over_gross": "per flatten event of one example path",
    "window_fee_bps_of_gross": "per flatten event of one example path", "seed": "which member this is",
    # --- counts and population sizes: A4 asks for n_eff BESIDE a statistic, these ARE the sample sizes ------------------------
    "n": "population size (A1)", "n_eff": "effective sample size (A4 itself)", "population_n": "declared population size (A4)",
    "n_asked": "count_block: members that were asked", "n_true": "count_block: members the predicate held for",
    "n_paths": "how many paths this document reads", "fired_paths": "count of paths that breached",
    "paths_with_no_traded_anchor_in_window": "census count beside the mean path",
    "base_index": "index of the base anchor on the path axis", "start_index": "index of the quarterly start",
    "aggregate_blocks_swept": "this sweep's own receipt", "min_blocks_required": "this sweep's own receipt",
    "violations": "this sweep's own receipt", "statistic_blocks_swept": "this sweep's own receipt",
    "contract_blocks_validated": "this sweep's own receipt", "unclassified_scalar_keys": "this sweep's own receipt",
    # --- configuration echoes: what the run was told to do --------------------------------------------------------------------
    "breach_by": "config echo", "threshold_cum_return": "config echo", "resume_hours_main": "config echo",
    "H": "which resume rule this cell is", "window_semantics_main": "config echo", "halt_semantics": "config echo",
    "W_ENTRY": "the name of a window semantics", "W_CARRY": "the name of a window semantics",
    "anchor": "an anchor timestamp", "base": "which base anchor", "dir": "the run directory", "run": "which run",
    "label": "a run label", "scope": "which reporting scope a flatten-cost block covers", "name": "a population's name",
    # --- provenance and prose: not measurements at all ---------------------------------------------------------------------
    "device": "provenance", "self_sha256": "provenance", "sha256": "provenance", "path": "provenance", "utc": "provenance",
    "commit": "provenance", "library": "provenance", "amendment": "provenance", "bt_agg_sha256": "provenance",
    "doc": "provenance", "produced_by": "provenance stamp of this contract's own statistics producer",
    "runtime_s": "wall-clock, not a measurement of the strategy", "clause": "which clause a receipt belongs to",
    "quantity": "what a block aggregates", "unit": "the unit of a block", "convention": "the NAMED A3' convention",
    "value_for_unmeasured": "the substitute the named convention declares", "refused_because": "why a figure does not exist",
    "reason": "why a member has no measurement", "no_measurement_reason": "why one path has no window end",
    "rule": "prose naming the rule", "caliber": "prose naming what the number is", "resume_rule": "prose naming the resume rule",
    "semantics_prose": "prose naming the window semantics", "window_semantics": "which semantics this cell used",
    "note_window_end": "prose note", "flatten_utc": "when a flatten happened", "resume_anchor": "when trading resumed",
    "note": "prose note", "notes": "prose note", "status": "prose status of a start that is not in the window",
}
REQUIRED_BESIDE_STATS = ("n_eff", "population_n")
_STATS_PRODUCER = "bt_agg._stats"
# the sides a dict that CLAIMS to be a contract aggregate must carry — an absent side is a refusal, never a skip
CONTRACT_SIDES = ("population", "measured", "no_measurement", "whole_population")
_REL_TOL = 1e-9


class AggRefusal(Exception):
    """raised instead of writing a document that violates the contract; the devices let it reach the exit code"""


def _is_scalar(v):
    return v is None or (isinstance(v, (int, float, str)) and not isinstance(v, bool))


def statistic_keys(d):
    """A4's INVERTED classifier: which keys of this dict are persisted statistics. Everything scalar that nobody declared to be
    something else is one. Returns them sorted, so the refusal message and the block's own `statistic_keys` stamp agree."""
    return sorted(k for k, v in d.items() if _is_scalar(v) and k not in NON_STATISTIC_KEYS)


def _pct(v, q):
    return None if not len(v) else float(np.percentile(np.asarray(v, float), q))


def _stats(v, pop_n):
    """the statistics of ONE subset, always carrying its own n_eff (A4). An empty subset gives n_eff 0 and null statistics —
    visible as "nothing was measured", never as a benign number. The block stamps WHAT IT IS (`produced_by` + the list of the
    statistic keys it persists), so the sweep can check a marked block against its own declared schema instead of against a list
    of names it happens to know (round-7 G-05)."""
    v = list(v)
    out = {"n_eff": len(v), "population_n": int(pop_n),
           "mean": (float(np.mean(v)) if v else None), "median": _pct(v, 50), "p05": _pct(v, 5), "p95": _pct(v, 95),
           "min": (float(min(v)) if v else None), "max": (float(max(v)) if v else None)}
    out["produced_by"] = _STATS_PRODUCER
    out["statistic_keys"] = statistic_keys(out)
    return out


def one_value_block(value, n_eff, population_n, rule, **extra):
    """a SINGLE published statistic (a median element, a chosen anchor) that is not a whole _stats spread. It exists so that such a
    number cannot be persisted as a bare scalar beside a summary: it carries its own n_eff and population_n like everything else.
    (round-7 G-05 found two of these already published as bare scalars: bt_p2_reading's `cum25_anchor_median_utc`, 118 per document,
    and bt_p_reading's `first_breach_median`, 18 per document.)"""
    out = dict(extra)
    out.update({"value": value, "n_eff": int(n_eff), "population_n": int(population_n), "rule": rule,
                "produced_by": "bt_agg.one_value_block"})
    out["statistic_keys"] = statistic_keys(out)
    return out


def block(quantity, members, value_of, applicability, *, population_name, id_of=lambda m: m, whole_population_convention=None,
          unit=None):
    """ONE aggregate under the contract.

    quantity   : what is being aggregated (goes into every refusal message)
    members    : the CLOSED population, an explicit list — NOT a comprehension that has already filtered someone out (A1)
    value_of   : member -> float or None
    applicability : member -> None if this member HAS a measurement, else a non-empty string NAMING why it has none (A2)
    whole_population_convention : None, or {"name": <prose>, "value_for_unmeasured": <float>} — the declared substitute that makes
                 a whole-population figure exist at all. Naming it is the point: the substitution becomes a stated convention
                 instead of the silent 0.0 that caused E-0920-C (A3').
    """
    if not callable(applicability):
        raise AggRefusal(f"{quantity}: no applicability classifier was declared — a population cannot be aggregated until every "
                         f"member is classified measured / named-not-measured (A2)")
    if not isinstance(members, (list, tuple)):
        raise AggRefusal(f"{quantity}: the population must be an explicit closed list, got {type(members).__name__} (A1)")
    if whole_population_convention is not None:
        if not isinstance(whole_population_convention, dict) or not str(whole_population_convention.get("name", "")).strip() \
                or "value_for_unmeasured" not in whole_population_convention:
            raise AggRefusal(f"{quantity}: whole_population_convention must name itself and give value_for_unmeasured (A3')")

    ids, measured, whole, by_reason = [], [], [], {}
    for m in members:
        mid = id_of(m)
        ids.append(mid)
        why = applicability(m)
        v = value_of(m)
        if why is None:
            if v is None:
                raise AggRefusal(f"{quantity}: member {mid!r} is classified as MEASURED but its value is None — an unexplained "
                                 f"missing value is not a class, name it in applicability() first (A5)")
            measured.append(float(v))
            whole.append(float(v))
        else:
            if not isinstance(why, str) or not why.strip():
                raise AggRefusal(f"{quantity}: member {mid!r} has no measurement but applicability() did not NAME a reason (A2)")
            if v is not None:
                raise AggRefusal(f"{quantity}: member {mid!r} is classified {why!r} yet carries the value {v!r} — the classifier "
                                 f"and the data disagree, reconcile before aggregating (A5)")
            by_reason.setdefault(why, []).append(mid)
            if whole_population_convention is not None:
                whole.append(float(whole_population_convention["value_for_unmeasured"]))

    dup = _dups(ids)
    if dup:
        raise AggRefusal(f"{quantity}: the population names the same member more than once ({dup[:6]}) — a population with a "
                         f"repeated member is a SELECTED population wearing the size of the closed one (A1)")
    n = len(ids)
    n_un = sum(len(x) for x in by_reason.values())
    out = {"quantity": quantity, "unit": unit,
           "population": {"name": population_name, "n": n, "members": ids},
           "measured": _stats(measured, n),
           "no_measurement": {"n": n_un, "by_reason": {k: {"n": len(v), "members": v} for k, v in sorted(by_reason.items())}}}
    if n_un == 0:
        out["whole_population"] = dict(_stats(whole, n), equals_measured=True,
                                       convention="every member of the population has a measurement")
    elif whole_population_convention is not None:
        out["whole_population"] = dict(_stats(whole, n), equals_measured=False,
                                       convention=whole_population_convention["name"],
                                       value_for_unmeasured=float(whole_population_convention["value_for_unmeasured"]))
    else:
        out["whole_population"] = {"n_eff": len(measured), "population_n": n, "equals_measured": False,
                                   "mean": None, "median": None, "p05": None, "p95": None, "min": None, "max": None,
                                   "produced_by": _STATS_PRODUCER,
                                   "refused_because": f"{n_un}/{n} members have no measurement and no whole-population convention "
                                                      f"was declared for them (A3')"}
        out["whole_population"]["statistic_keys"] = statistic_keys(out["whole_population"])
    # A3': both sides must be present, whatever happened above; A3'': and they must AGREE with each other.
    for side in CONTRACT_SIDES:
        if side not in out:
            raise AggRefusal(f"{quantity}: the {side} figure is missing — all of {'/'.join(CONTRACT_SIDES)} are required (A3')")
    validate_aggregate_block(out, "$<block() return>")
    return out


def _dups(ids):
    """the member ids that appear more than once, compared by (type, value) so that 0 / False / 0.0 are three members, not one.
    Sets and Counters would silently merge them, which is the very collapse A1 is about."""
    keys = [(type(i).__name__, repr(i)) for i in ids]
    seen, out = {}, []
    for k, i in zip(keys, ids):
        seen[k] = seen.get(k, 0) + 1
        if seen[k] == 2: out.append(i)
    return out


def count_block(quantity, members, predicate, *, population_name, id_of=lambda m: m, applicability=None):
    """a COUNT over a closed population: how many members satisfy `predicate`, out of how many, and which. Counts carry no
    statistic keys, so A4 does not apply to them — but A1/A2 still do: the population is declared and listed, and a member with no
    measurement is counted in a NAMED not_applicable subset rather than silently counted as a False (which is the count-shaped
    version of the same defect: "k/32 fired" reads as "32 members were asked" when some were never asked at all)."""
    if not isinstance(members, (list, tuple)):
        raise AggRefusal(f"{quantity}: the population must be an explicit closed list (A1)")
    hits, na = [], {}
    ids = [id_of(m) for m in members]
    dup = _dups(ids)
    if dup:
        raise AggRefusal(f"{quantity}: the population names the same member more than once ({dup[:6]}) (A1)")
    for m in members:
        mid = id_of(m)
        why = None if applicability is None else applicability(m)
        if why is not None:
            if not isinstance(why, str) or not why.strip():
                raise AggRefusal(f"{quantity}: member {mid!r} is not applicable but no reason was NAMED (A2)")
            if predicate(m):
                raise AggRefusal(f"{quantity}: member {mid!r} is classified {why!r} yet the predicate is True for it (A5)")
            na.setdefault(why, []).append(mid)
        elif predicate(m):
            hits.append(mid)
    n_na = sum(len(v) for v in na.values())
    out = {"quantity": quantity, "population": {"name": population_name, "n": len(members), "members": ids},
           "n_true": len(hits), "n_asked": len(members) - n_na, "members_true": hits,
           "not_applicable": {"n": n_na, "by_reason": {k: {"n": len(v), "members": v} for k, v in sorted(na.items())}}}
    validate_count_block(out, "$<count_block() return>")
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# A3'' — the relations, re-derived from the block's own contents (round-7 G-04)
def _ids_of(sub):
    out = []
    for r, v in (sub.get("by_reason") or {}).items():
        if not isinstance(v, dict) or not isinstance(v.get("members"), list):
            raise AggRefusal(f"no-measurement reason {r!r} does not list its members (A2)")
        if len(v["members"]) != v.get("n"):
            raise AggRefusal(f"no-measurement reason {r!r} says n={v.get('n')} but lists {len(v['members'])} members (A2)")
        out += list(v["members"])
    return out


def _close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(float(a), float(b), rel_tol=_REL_TOL, abs_tol=1e-12)


def validate_aggregate_block(b, path):
    """every relation a reader would otherwise have to take on trust. Raises AggRefusal naming the path and the relation."""
    def bad(msg):
        raise AggRefusal(f"A3'' block relations at {path} ({b.get('quantity')!r}): {msg}")

    missing = [s for s in CONTRACT_SIDES if s not in b]
    if missing:
        bad(f"required side(s) {missing} are absent — a block missing a side is not a smaller block, it is an unreadable one "
            f"(an absent key must never be a skip)")
    pop, meas, nom, whole = b["population"], b["measured"], b["no_measurement"], b["whole_population"]
    for nm, side in (("measured", meas), ("whole_population", whole)):
        if not isinstance(side, dict) or any(k not in side for k in REQUIRED_BESIDE_STATS):
            bad(f"{nm} does not carry {'/'.join(REQUIRED_BESIDE_STATS)} (A4)")
    if not isinstance(pop.get("members"), list):
        bad("population.members is not an explicit list (A1)")
    ids = pop["members"]
    if len(ids) != pop.get("n"):
        bad(f"population.n = {pop.get('n')} but {len(ids)} members are listed (A1)")
    dup = _dups(ids)
    if dup:
        bad(f"population lists the same member twice ({dup[:6]}) — a repeated member is a selected population wearing the size "
            f"of the closed one (A1)")
    n = len(ids)
    un_ids = _ids_of(nom)
    if len(un_ids) != nom.get("n"):
        bad(f"no_measurement.n = {nom.get('n')} but the named reasons list {len(un_ids)} members (A2)")
    dup_un = _dups(un_ids)
    if dup_un:
        bad(f"member(s) {dup_un[:6]} appear under more than one no-measurement reason (A2)")
    stray = [i for i in un_ids if i not in ids]
    if stray:
        bad(f"no-measurement member(s) {stray[:6]} are not in the declared population (A1/A2)")
    n_un = len(un_ids)
    if meas.get("n_eff") != n - n_un:
        bad(f"measured.n_eff = {meas.get('n_eff')} but the population is {n} with {n_un} named as unmeasured — "
            f"{n - n_un} members were measured (A2)")
    for nm, side in (("measured", meas), ("whole_population", whole)):
        if side.get("population_n") != n:
            bad(f"{nm}.population_n = {side.get('population_n')} but the declared population is {n} (A1)")
    if "equals_measured" not in whole:
        bad("whole_population does not say whether it equals the measured figure — an absent claim is not a true one (A3')")
    stat_ks = [k for k in statistic_keys(whole) if k in meas]
    if whole["equals_measured"]:
        if n_un:
            bad(f"whole_population claims equals_measured but {n_un}/{n} members have no measurement (A3')")
        if whole.get("n_eff") != meas.get("n_eff"):
            bad(f"whole_population claims equals_measured but its n_eff {whole.get('n_eff')} != measured's {meas.get('n_eff')}")
        diff = [k for k in stat_ks if not _close(whole.get(k), meas.get(k))]
        if diff:
            bad(f"whole_population claims equals_measured but differs from measured on {diff}: "
                f"{ {k: [whole.get(k), meas.get(k)] for k in diff[:4]} } (A3'')")
    elif whole.get("mean") is None and "refused_because" in whole:
        if not n_un:
            bad("whole_population refuses a figure although every member has a measurement (A3')")
        if whole.get("n_eff") != meas.get("n_eff"):
            bad(f"a refused whole_population must keep the measured n_eff ({meas.get('n_eff')}), got {whole.get('n_eff')}")
        live = [k for k in stat_ks if whole.get(k) is not None]
        if live:
            bad(f"whole_population says it was refused yet still persists {live} (A3')")
    else:
        if not str(whole.get("convention", "")).strip():
            bad("a whole_population figure that is not the measured one exists only under a NAMED convention (A3')")
        if "value_for_unmeasured" not in whole:
            bad("the named convention does not say what an unmeasured member contributes (A3')")
        v = float(whole["value_for_unmeasured"])
        if whole.get("n_eff") != n:
            bad(f"under a convention every member contributes, so whole_population.n_eff must be {n}, got {whole.get('n_eff')}")
        n_m = int(meas.get("n_eff") or 0)
        want = (((n_m * float(meas["mean"])) if n_m else 0.0) + n_un * v) / n if n else None
        if not _close(whole.get("mean"), want):
            bad(f"whole_population.mean = {whole.get('mean')} but the named convention forces "
                f"({n_m}·{meas.get('mean')} + {n_un}·{v}) / {n} = {want} (A3'')")
        for k, fn in (("min", min), ("max", max)):
            if meas.get(k) is not None:
                want_k = fn(float(meas[k]), v) if n_un else float(meas[k])
                if not _close(whole.get(k), want_k):
                    bad(f"whole_population.{k} = {whole.get(k)} but the population is the measured members plus {n_un}·{v}, "
                        f"so it must be {want_k} (A3'')")
    return True


def validate_count_block(b, path):
    def bad(msg):
        raise AggRefusal(f"A1/A2 count relations at {path} ({b.get('quantity')!r}): {msg}")

    for k in ("population", "n_true", "n_asked", "members_true", "not_applicable"):
        if k not in b:
            bad(f"a count block must carry {k} — an absent key is a refusal, not a skip")
    pop, na = b["population"], b["not_applicable"]
    n = pop.get("n")
    na_ids = _ids_of(na)
    if len(na_ids) != na.get("n"):
        bad(f"not_applicable.n = {na.get('n')} but the named reasons list {len(na_ids)} members (A2)")
    if b["n_asked"] != (n or 0) - len(na_ids):
        bad(f"n_asked = {b['n_asked']} but the population is {n} with {len(na_ids)} not applicable (A1)")
    if len(b["members_true"]) != b["n_true"]:
        bad(f"n_true = {b['n_true']} but {len(b['members_true'])} members are listed (A1)")
    if b["n_true"] > b["n_asked"]:
        bad(f"n_true = {b['n_true']} exceeds n_asked = {b['n_asked']} (A1)")
    if isinstance(pop.get("members"), list):
        stray = [i for i in list(b["members_true"]) + na_ids if i not in pop["members"]]
        if stray:
            bad(f"member(s) {stray[:6]} are not in the declared population (A1)")
    return True


def _claims_to_be_a_block(o):
    return isinstance(o, dict) and "quantity" in o and "population" in o


def sweep_or_refuse(doc, min_blocks, where="$"):
    """A4 + A3'', the class-shaped clauses: walk the WHOLE document and refuse it if

      * any dict that persists a statistic does not carry n_eff and population_n beside it — where "persists a statistic" means
        "carries a scalar-valued key that NOBODY CLASSIFIED as something else" (the inverted trigger, round-7 G-05), so a name
        that did not exist when this was written fails closed instead of sailing through;
      * a dict stamped as this contract's own statistics block disagrees with its own declared `statistic_keys`;
      * a dict that CLAIMS to be a contract aggregate (it carries `quantity` and `population`) is missing a side, or any of its
        internal relations does not hold (round-7 G-04: presence used to be the whole check).

    It is deliberately ignorant of every quantity in this project: a block added tomorrow is caught because it is in the document.
    `min_blocks` exists because a sweep that inspected nothing would pass — "zero measurements also passes" is the very family this
    contract is about, and a guard is not exempt from it.
    """
    bad, seen, blocks = [], [], [0, 0]

    def walk(o, path):
        if isinstance(o, dict):
            if _claims_to_be_a_block(o):
                if any(k in o for k in ("measured", "no_measurement", "whole_population")):
                    validate_aggregate_block(o, path); blocks[0] += 1
                elif "n_true" in o or "n_asked" in o:
                    validate_count_block(o, path); blocks[1] += 1
                else:
                    raise AggRefusal("A3'' at %s: this dict carries `quantity` and `population` but is neither an aggregate nor "
                                     "a count block — a mutilated contract block is a refusal, not a dict the sweep skips "
                                     "(keys: %s)" % (path, sorted(o)[:12]))
            ks = statistic_keys(o)
            if ks:
                seen.append(path)
                missing = [k for k in REQUIRED_BESIDE_STATS if k not in o]
                if missing:
                    bad.append({"path": path, "statistics_with_no_sample_size": ks, "missing": missing,
                                "keys_present": sorted(o)[:12]})
                elif o.get("produced_by") and o.get("statistic_keys") is not None and list(o["statistic_keys"]) != ks:
                    bad.append({"path": path, "declared_statistic_keys": list(o["statistic_keys"]), "actually_present": ks,
                                "missing": ["<declared schema disagrees with the block's own contents>"]})
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, (list, tuple)):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk(doc, where)
    if bad:
        raise AggRefusal("A4 structural sweep: %d block(s) persist a statistic with no %s beside it. First offenders: %s . The "
                         "trigger is INVERTED: a scalar-valued key IS a statistic unless bt_agg.NON_STATISTIC_KEYS classifies it "
                         "as something else, so if one of these keys is not a statistic, classify it there with its reason."
                         % (len(bad), "/".join(REQUIRED_BESIDE_STATS), json.dumps(bad[:6], default=str)))
    if len(seen) < int(min_blocks):
        raise AggRefusal("A4 structural sweep inspected only %d aggregate block(s) but at least %d were expected — a sweep that "
                         "finds nothing passes vacuously, which is the defect family this contract exists for"
                         % (len(seen), int(min_blocks)))
    return {"clause": "A4+A3''", "aggregate_blocks_swept": len(seen), "min_blocks_required": int(min_blocks), "violations": 0,
            "statistic_blocks_swept": len(seen), "contract_blocks_validated": blocks[0] + blocks[1],
            "unclassified_scalar_keys": 0}


def count_contract_blocks(doc):
    """how many dicts in the document are aggregates produced by block() — identified by their own marker keys, not by position.
    The devices assert this against their own call count, so a block that was BUILT but never made it into the document (or one
    created outside the contract) is caught, independently of how many other compliant dicts the document happens to carry.
    `whole_population` is part of the identity (round-7 G-04): deleting one side used to leave the census unchanged, so the count
    could be padded back up with an unrelated statistics dict."""
    n = [0]

    def walk(o):
        if isinstance(o, dict):
            if all(k in o for k in ("quantity", "population", "measured", "no_measurement", "whole_population")): n[0] += 1
            for v in o.values(): walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o: walk(v)

    walk(doc)
    return n[0]


def write_json_checked(doc, path, min_blocks, indent=1):
    """sweep first, write only if the sweep passes; the sweep receipt goes INTO the document it certifies"""
    receipt = sweep_or_refuse(doc, min_blocks)
    doc["aggregation_contract"] = {"amendment": "AMENDMENT_4_baseline_tables_aggregation_contract_2026-09-20.md",
                                   "library": "bt_agg.py", "sweep": receipt}
    again = sweep_or_refuse(doc, min_blocks)                 # the document that is actually written is the one that was swept
    if again["aggregate_blocks_swept"] != receipt["aggregate_blocks_swept"]:
        raise AggRefusal("the sweep receipt changed the document it certifies (%d -> %d blocks)"
                         % (receipt["aggregate_blocks_swept"], again["aggregate_blocks_swept"]))
    json.dump(doc, open(path + ".tmp", "w"), indent=indent, default=float)
    os.replace(path + ".tmp", path)
    return receipt

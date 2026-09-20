#!/usr/bin/env python3
"""bt_agg.py — the AGGREGATION CONTRACT of AMENDMENT 4 (docs/AMENDMENT_4_baseline_tables_aggregation_contract_2026-09-20.md),
written after E-0920-C ("永不恢复" summary encoded "halted before the window ⇒ no trading in the window" as end = 0.0 and averaged
it together with real losses, lifting the mean by 3.14 pp).

THE CLASS, not the instance: *no aggregate may encode "not applicable / no measurement in this window" as a benign value and then
average it with real measurements.* Same family as "unknown is not zero" and "zero measurements also passes" — this is their
AGGREGATE form.

The five clauses, all enforced here, none of them a list of affected quantities:
  A1 CLOSED POPULATION — the caller hands in an explicit list; filtering members out before the call is the defect itself, because a
     dropped member appears nowhere in the output. `block()` refuses anything that is not a list/tuple and records every member id.
  A2 NAMED NO-MEASUREMENT SUBSET — `applicability(member)` returns None (measured) or a NON-EMPTY STRING naming why there is none.
     Those members go to no_measurement.by_reason[<name>] with their ids and NEVER enter a mean or a percentile.
  A3' BOTH FIGURES OR REFUSE — `measured` (the headline: n_eff/mean/median/p05/p95/min/max) AND `whole_population`. The whole
     population figure exists only under a NAMED convention for what an unmeasured member contributes; without one its mean is null
     with `refused_because`. Neither side may simply be absent.
  A4 n_eff BESIDE EVERY PERSISTED MEAN — enforced by `sweep_or_refuse()` over the WHOLE output document just before it is written.
     This clause knows nothing about `never` or about any quantity: an aggregate someone adds tomorrow is caught because it is in
     the document, not because it is on a list. `min_blocks` stops the sweep from passing vacuously on a document with no statistics.
  A5 NO BENIGN SUBSTITUTION — a member classified measured whose value is None is refused (an unexplained missing value is not a
     class; name it first); a member classified unmeasured that still carries a value is refused (classifier and data disagree).

Import-only library: it has no __main__ and reads nothing from the environment.
"""
import json
import os

import numpy as np

# A4: a dict that persists ANY of these keys is an aggregate and must carry its effective sample size beside it.
STAT_TRIGGER = ("mean", "median", "p05", "p95")
REQUIRED_BESIDE_STATS = ("n_eff", "population_n")


class AggRefusal(Exception):
    """raised instead of writing a document that violates the contract; the devices let it reach the exit code"""


def _pct(v, q):
    return None if not len(v) else float(np.percentile(np.asarray(v, float), q))


def _stats(v, pop_n):
    """the statistics of ONE subset, always carrying its own n_eff (A4). An empty subset gives n_eff 0 and null statistics —
    visible as "nothing was measured", never as a benign number."""
    v = list(v)
    return {"n_eff": len(v), "population_n": int(pop_n),
            "mean": (float(np.mean(v)) if v else None), "median": _pct(v, 50), "p05": _pct(v, 5), "p95": _pct(v, 95),
            "min": (float(min(v)) if v else None), "max": (float(max(v)) if v else None)}


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
                                   "refused_because": f"{n_un}/{n} members have no measurement and no whole-population convention "
                                                      f"was declared for them (A3')"}
    # A3': both sides must be present, whatever happened above.
    for side in ("measured", "whole_population"):
        if side not in out:
            raise AggRefusal(f"{quantity}: the {side} figure is missing — both are required (A3')")
    return out


def count_block(quantity, members, predicate, *, population_name, id_of=lambda m: m, applicability=None):
    """a COUNT over a closed population: how many members satisfy `predicate`, out of how many, and which. Counts carry no
    statistic keys, so A4 does not apply to them — but A1/A2 still do: the population is declared and listed, and a member with no
    measurement is counted in a NAMED not_applicable subset rather than silently counted as a False (which is the count-shaped
    version of the same defect: "k/32 fired" reads as "32 members were asked" when some were never asked at all)."""
    if not isinstance(members, (list, tuple)):
        raise AggRefusal(f"{quantity}: the population must be an explicit closed list (A1)")
    hits, na = [], {}
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
    return {"quantity": quantity, "population": {"name": population_name, "n": len(members)},
            "n_true": len(hits), "n_asked": len(members) - n_na, "members_true": hits,
            "not_applicable": {"n": n_na, "by_reason": {k: {"n": len(v), "members": v} for k, v in sorted(na.items())}}}


def sweep_or_refuse(doc, min_blocks, where="$"):
    """A4, the class-shaped clause: walk the WHOLE document and refuse it if any dict that persists a statistic does not carry
    n_eff and population_n beside it.

    It is deliberately ignorant of every quantity in this project: a block added tomorrow is caught because it is in the document.
    `min_blocks` exists because a sweep that inspected nothing would pass — "zero measurements also passes" is the very family this
    contract is about, and a guard is not exempt from it.
    """
    bad, seen = [], []

    def walk(o, path):
        if isinstance(o, dict):
            if any(k in o for k in STAT_TRIGGER):
                seen.append(path)
                missing = [k for k in REQUIRED_BESIDE_STATS if k not in o]
                if missing:
                    bad.append({"path": path, "missing": missing, "keys_present": sorted(o)[:12]})
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, (list, tuple)):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk(doc, where)
    if bad:
        raise AggRefusal("A4 structural sweep: %d aggregate block(s) persist a statistic with no effective sample size beside it "
                         "(missing %s). First offenders: %s" % (len(bad), "/".join(REQUIRED_BESIDE_STATS), json.dumps(bad[:6])))
    if len(seen) < int(min_blocks):
        raise AggRefusal("A4 structural sweep inspected only %d aggregate block(s) but at least %d were expected — a sweep that "
                         "finds nothing passes vacuously, which is the defect family this contract exists for"
                         % (len(seen), int(min_blocks)))
    return {"clause": "A4", "aggregate_blocks_swept": len(seen), "min_blocks_required": int(min_blocks), "violations": 0}


def count_contract_blocks(doc):
    """how many dicts in the document are aggregates produced by block() — identified by their own marker keys, not by position.
    The devices assert this against their own call count, so a block that was BUILT but never made it into the document (or one
    created outside the contract) is caught, independently of how many other compliant dicts the document happens to carry."""
    n = [0]

    def walk(o):
        if isinstance(o, dict):
            if "quantity" in o and "population" in o and "measured" in o and "no_measurement" in o: n[0] += 1
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

#!/usr/bin/env python3
"""d10_interval_rule_on_real_data.py -- what lead's D10 interval rule does to the REAL settlement population.

Unit tests pin the rule's branches; this runs it over the CHECKSUM-verified archive so the October rebuild is
not the first time anyone sees its effect on real data. Three questions:

  1. does it reproduce the four measured transition cases that justified it (DEXE/ACE/PROM 2.0h, COTI 1.0h)?
  2. over every settlement in the verified months, what is the tier distribution -- in particular how often do
     the DECLARED fallbacks and the CLAMPS fire, which lead requires to be counted per event and named?
  3. how often does the rule's answer differ from the archive's declared column, and by how much?

The rule is IMPORTED from common/funding_interval.py. It is not reimplemented here: "using the frozen caliber"
only holds when the code is called.
"""
import collections
import csv
import datetime
import glob
import hashlib
import io
import json
import os
import sys
import zipfile

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "funding_interval.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/funding_interval.py not found; this device must not reimplement the rule")
import funding_interval as FI


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def iso(t):
    return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


CASES = {("DEXEUSDT", "2026-08-07T08:00Z"): 2.0, ("ACEUSDT", "2026-08-10T04:00Z"): 2.0,
         ("PROMUSDT", "2026-08-14T12:00Z"): 2.0, ("COTIUSDT", "2026-08-31T20:00Z"): 1.0}


def main():
    zips_root, months_csv, out = sys.argv[1], sys.argv[2], sys.argv[3]
    months = [m.strip() for m in months_csv.split(",") if m.strip()]
    tiers = collections.Counter()
    differs = collections.Counter()
    clamp_examples, declared_examples, case_hits = [], [], {}
    n_events = 0
    per_symbol = collections.defaultdict(list)

    for m in months:
        for zp in sorted(glob.glob(os.path.join(zips_root, m, f"*-fundingRate-{m}.zip"))):
            s = os.path.basename(zp).split("-fundingRate-")[0]
            z = zipfile.ZipFile(zp)
            for r in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8"))):
                if r and r[0].strip().isdigit():
                    per_symbol[s].append((int(round(int(r[0]) / 1000)), float(r[1])))
    for s, ev in per_symbol.items():
        ev.sort()
        fts = [t for t, _ in ev]
        decl = [d for _, d in ev]
        res, t = FI.interval_d10_series(fts, decl)
        tiers.update(t)
        n_events += len(res)
        for k, x in enumerate(res):
            iv, d = x["iv"], x["declared_iv"]
            if iv is not None and d is not None:
                differs["differs_from_declared" if iv != d else "equals_declared"] += 1
            key = (s, iso(fts[k]))
            if key in CASES:
                case_hits[f"{s}@{iso(fts[k])}"] = {"rule_iv": iv, "tier": x["tier"],
                                                   "declared": d, "expected_from_measurement": CASES[key],
                                                   "matches": iv == CASES[key]}
            if x["tier"] in FI.D10_CLAMPED and len(clamp_examples) < 20:
                clamp_examples.append({"symbol": s, "utc": iso(fts[k]), "tier": x["tier"],
                                       "gap_h": x["gap_h"], "iv": iv, "declared": d})
            if x["tier"] == FI.DECLARED_LONG_GAP and len(declared_examples) < 20:
                declared_examples.append({"symbol": s, "utc": iso(fts[k]), "gap_h": round(x["gap_h"], 3),
                                          "iv": iv})

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "rule_module_sha256": sha(os.path.realpath(FI.__file__)),
           "rule": "common/funding_interval.py interval_d10 -- IMPORTED, not reimplemented",
           "criteria": "docs/DECISION_RULE_D10_stage2_2026-09-26.md (1814d4334) §1",
           "months": months, "symbols": len(per_symbol), "events": n_events,
           "tier_counts": {k: int(v) for k, v in tiers.items()},
           "vs_declared_column": {k: int(v) for k, v in differs.items()},
           "measured_transition_cases": case_hits,
           "all_measured_cases_reproduced": all(v["matches"] for v in case_hits.values()) and len(case_hits) > 0,
           "clamp_examples": clamp_examples, "long_gap_examples": declared_examples}
    assert sum(tiers.values()) == n_events, "tier counts do not close against the event count"

    print(f"D10 interval rule over {n_events} settlements, {len(per_symbol)} symbols, months {','.join(months)}")
    print(f"  rule module sha {rec['rule_module_sha256'][:16]} (imported)")
    for k, v in sorted(tiers.items(), key=lambda kv: -kv[1]):
        print(f"     {k:34s} {v:>8d}  {100.0*v/n_events:6.3f}%")
    print(f"  vs the declared column: {rec['vs_declared_column']}")
    print(f"  the four measured transition cases reproduced: {rec['all_measured_cases_reproduced']}")
    for k, v in sorted(case_hits.items()):
        print(f"     {k:34s} rule={v['rule_iv']} declared={v['declared']} "
              f"expected={v['expected_from_measurement']} tier={v['tier']}")
    json.dump(rec, open(out, "w"), indent=1)
    print(f"  receipt -> {out}  sha256={sha(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

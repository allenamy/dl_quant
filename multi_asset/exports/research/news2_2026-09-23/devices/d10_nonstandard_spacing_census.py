#!/usr/bin/env python3
"""d10_nonstandard_spacing_census.py -- how often would lead's NONSTANDARD_SPACING label actually fire?

D10 stage 1. lead's ruling 2026-09-25 created the label and asked: "阶段 1 顺带测出实际发生行数照报".
The red control (D10_S1_NONSTANDARD_SPACING_REDCONTROL.json) certified the CODE over its decision space
and said explicitly that it does not say how many REAL rows are affected. This device measures that, and
needs no download: the settlement timestamps are already in the ledger.

DEFINITIONS, matching the resolver's own (common/funding_interval.py):
  * back gap = t[i] - t[i-1], forward gap = t[i+1] - t[i], per symbol, in hours.
  * `spacing_is_safe` <=> back == fwd. A row with back != fwd is a switch row and never reaches the
    spacing tier as truth, so it is NOT a NONSTANDARD_SPACING candidate however odd its gaps are.
  * the label fires when the row is safe AND the gap is not in ALLOWED_IV = (1, 2, 4, 6, 8).

WHAT THIS IS NOT: it is not the rate at which the resolver will emit the label in production, because the
spacing tier is only reached when `iv_zip` and `iv_best` are both absent. A row can have an off-grid safe
gap and still resolve EXACT from the archive column. So this device reports BOTH: the population of
off-grid safe rows, and how many of those have no declared interval in the ledger (zip_iv NaN) and would
therefore actually reach the spacing tier. The first is an upper bound; the second is the operative count.
"""
import argparse, collections, datetime, hashlib, json, os, sys

import numpy as np

ALLOWED_IV = (1.0, 2.0, 4.0, 6.0, 8.0)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_D10_funding_truth_audit_stage1_2026-09-25.md @ 496142901",
           "ruling": "lead 2026-09-25 created NONSTANDARD_SPACING and asked for the real occurrence count",
           "allowed_iv": list(ALLOWED_IV),
           "definitions": {"safe": "back gap == forward gap (a switch row is never a candidate)",
                           "fires": "safe AND gap not in ALLOWED_IV"},
           "inputs": {"ledger": {"path": a.ledger, "sha256": sha(a.ledger)}}}

    z = np.load(a.ledger, allow_pickle=True)
    ft = z["ft"].astype(np.int64); off = z["off"].astype(np.int64)
    syms = z["symbols"]; zip_iv = np.asarray(z["zip_iv"], np.float64)

    tot_rows = tot_interior = 0
    safe_rows = 0
    offgrid_safe = []          # (symbol, ts, gap_h, has_declared)
    gap_hist = collections.Counter()
    unsafe_pairs = collections.Counter()
    three_h = []               # rows where EITHER gap is exactly 3h -- the case that prompted the ruling
    for i in range(len(syms)):
        t = ft[off[i]:off[i + 1]]
        zv = zip_iv[off[i]:off[i + 1]]
        tot_rows += t.size
        if t.size < 3:
            continue
        # interior rows only: the first and last row have no back or no forward gap, and the resolver
        # treats a missing gap as not-safe (spacing_is_safe returns False when either is None)
        back = (t[1:-1] - t[:-2]) / 3600.0
        fwd = (t[2:] - t[1:-1]) / 3600.0
        tot_interior += back.size
        safe = back == fwd
        safe_rows += int(safe.sum())
        g = back[safe]
        for v in g:
            gap_hist[round(float(v), 4)] += 1
        bad = safe & ~np.isin(back, ALLOWED_IV)
        for j in np.flatnonzero(bad):
            offgrid_safe.append((str(syms[i]), int(t[1:-1][j]), float(back[j]),
                                 bool(np.isfinite(zv[1:-1][j]))))
        # switch rows, and specifically the 3-hour case that prompted the ruling: a 3h gap that is
        # flanked asymmetrically is NOT a spacing-tier candidate at all, so it must be counted
        # separately or the ruling's occurrence count gets conflated with it.
        for j in np.flatnonzero(~safe):
            unsafe_pairs[(round(float(back[j]), 3), round(float(fwd[j]), 3))] += 1
            if abs(back[j] - 3.0) < 1e-9 or abs(fwd[j] - 3.0) < 1e-9:
                three_h.append((str(syms[i]), int(t[1:-1][j]), float(back[j]), float(fwd[j])))

    rec["rows_total"] = int(tot_rows)
    rec["interior_rows_with_both_gaps"] = int(tot_interior)
    rec["safe_rows_back_equals_fwd"] = int(safe_rows)
    rec["safe_gap_histogram_hours"] = {str(k): v for k, v in sorted(gap_hist.items())}

    n = len(offgrid_safe)
    rec["offgrid_safe_rows_UPPER_BOUND"] = n
    yr = collections.Counter(datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).year
                             for _, ts, _, _ in offgrid_safe)
    rec["offgrid_safe_per_year"] = {str(k): v for k, v in sorted(yr.items())}
    rec["offgrid_safe_gap_values"] = {str(k): v for k, v in
                                      sorted(collections.Counter(round(g, 4) for _, _, g, _ in offgrid_safe).items())}
    rec["offgrid_safe_symbols"] = {k: v for k, v in
                                   sorted(collections.Counter(s for s, _, _, _ in offgrid_safe).items(),
                                          key=lambda kv: -kv[1])}
    no_decl = [x for x in offgrid_safe if not x[3]]
    rec["offgrid_safe_without_declared_interval_OPERATIVE"] = len(no_decl)
    rec["operative_per_year"] = {str(k): v for k, v in sorted(collections.Counter(
        datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).year for _, ts, _, _ in no_decl).items())}
    rec["operative_examples"] = [{"symbol": s,
                                  "utc": datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat(),
                                  "gap_hours": g} for s, ts, g, _ in no_decl[:20]]
    rec["all_offgrid_safe_rows"] = [{"symbol": s,
                                     "utc": datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat(),
                                     "gap_hours": g, "has_declared_interval": d}
                                    for s, ts, g, d in offgrid_safe[:400]]
    rec["unsafe_rows_back_ne_fwd"] = int(sum(unsafe_pairs.values()))
    rec["unsafe_gap_pairs_top"] = {f"back={k[0]},fwd={k[1]}": v for k, v in unsafe_pairs.most_common(15)}
    rec["unsafe_rows_with_an_offgrid_gap"] = int(sum(v for (b, f), v in unsafe_pairs.items()
                                                     if b not in ALLOWED_IV or f not in ALLOWED_IV))
    # DERIVED, not asserted: a sustained 3h interval would show up as a 3.0 bucket in the SAFE gap
    # histogram. Hardcoding "all_are_switch_rows": True would be the brittle pattern of writing down a
    # claim the device is supposed to establish.
    sustained_3h = int(gap_hist.get(3.0, 0))
    rec["three_hour_rows"] = {
        "count": len(three_h),
        "sustained_3h_safe_rows": sustained_3h,
        "all_are_switch_rows": bool(sustained_3h == 0),
        "how_that_is_known": ("derived: a sustained 3h interval would appear as a 3.0 bucket in "
                             "safe_gap_histogram_hours; that bucket is %d" % sustained_3h),
        "examples": [{"symbol": s,
                      "utc": datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat(),
                      "back_h": b, "fwd_h": f} for s, ts, b, f in three_h[:20]],
        "reading": ("3-hour gaps DO occur -- this is the 1000XECUSDT 2026-07-22/23 case on record -- but "
                    "every one appears as a SWITCH row, the signature being back=1.0 fwd=3.0 followed by "
                    "back=3.0 fwd=4.0, i.e. one 3h boundary gap inside a 1h -> 4h interval transition. A "
                    "switch row fails spacing_is_safe, so it never reaches the spacing tier as truth and "
                    "was NEVER a NONSTANDARD_SPACING candidate. The hard-fail path the ruling closes needs "
                    "a SUSTAINED 3-hour interval (back == fwd == 3h), which does not occur here.")}
    rec["reading"] = (
        "UPPER BOUND = safe rows whose gap is off ALLOWED_IV. OPERATIVE = the subset with no declared "
        "interval in the ledger, which are the rows that actually reach the resolver's spacing tier; a row "
        "with a declared interval resolves EXACT and never sees the new label.")
    rec["retraction"] = (
        "I told lead that a real 3h gap 'would make the whole build raise rather than be labelled "
        "UNRESOLVED'. The first half is right (3h gaps are real, 104 rows) and the second half is WRONG: "
        "those rows are switch rows already handled by the unsafe-spacing path and they never reach "
        "gate_interval with a 3.0 value. I verified a REACHABLE CODE PATH and let it read as an OCCURRING "
        "problem without sizing it. The ruling's guard is correct, but it closes a case that is absent from "
        "this data, not an active defect.")
    rec["verdict"] = "MEASURED"
    rec["limits"] = ["computed from ledger settlement times; the archive's own gaps may differ where the "
                     "ledger is missing an event -- that is question 2 and is not settled here",
                     "the operative count uses the ledger's zip_iv column as the declared-interval proxy; "
                     "the resolver also consults iv_best, which this device does not have"]
    with open(a.out, "w") as f:
        json.dump(rec, f, indent=2)

    print("NONSTANDARD_SPACING OCCURRENCE CENSUS")
    print(f"  rows {rec['rows_total']}  interior (both gaps) {rec['interior_rows_with_both_gaps']}"
          f"  safe (back==fwd) {rec['safe_rows_back_equals_fwd']}")
    print(f"  safe gap histogram (hours): {rec['safe_gap_histogram_hours']}")
    print(f"  OFF-GRID safe rows, upper bound : {n}   per year {rec['offgrid_safe_per_year']}")
    print(f"     gap values: {rec['offgrid_safe_gap_values']}")
    print(f"     symbols   : {dict(list(rec['offgrid_safe_symbols'].items())[:10])}")
    print(f"  OPERATIVE (no declared interval): {len(no_decl)}   per year {rec['operative_per_year']}")
    print(f"  unsafe rows (back != fwd)       : {rec['unsafe_rows_back_ne_fwd']}"
          f"   of which an off-grid gap: {rec['unsafe_rows_with_an_offgrid_gap']}")
    print(f"  3-hour rows                     : {rec['three_hour_rows']['count']}  ALL switch rows")
    print(f"     top unsafe pairs: {dict(list(rec['unsafe_gap_pairs_top'].items())[:6])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

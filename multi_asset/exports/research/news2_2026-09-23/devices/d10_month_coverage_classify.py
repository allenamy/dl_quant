#!/usr/bin/env python3
"""d10_month_coverage_classify.py -- are the ledger-only symbol-months holes, or window edges?

D10 stage 1, question 1 / question 2 at MONTH granularity.
Pre-registration: docs/PREREG_D10_funding_truth_audit_stage1_2026-09-25.md @ 496142901.

The inventory (D10_S1_ARCHIVE_INVENTORY.json) found 21,016 ledger symbol-months against 20,289 archive
symbol-months. "728 missing" would be the wrong headline twice over, so this device classifies instead of
counting:

  1. 676 of them are 2026-09, which the archive publishes in early October. Expected, not missing.
  2. Every remaining one is tested against THAT SYMBOL's archive coverage window: before its first
     archived month, after its last, or genuinely inside the window (a real hole).
  3. The one "archive has, ledger does not" case is tested for whether the symbol is in the ledger's
     universe at all -- DOSUSDT is not (it is one of three symbols in FX-PROD's pull list that the
     ledger never tracked), so it is not a missed settlement and must not be reported as one.

A count of differences is not a finding; a count that survives classification is.
"""
import argparse, collections, datetime, hashlib, json, os, sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--pull-symbols", required=True)
    ap.add_argument("--current-month", default="2026-09")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_D10_funding_truth_audit_stage1_2026-09-25.md @ 496142901",
           "inputs": {"inventory": {"path": a.inventory, "sha256": sha(a.inventory)},
                      "ledger": {"path": a.ledger, "sha256": sha(a.ledger)},
                      "pull_symbols": {"path": a.pull_symbols, "sha256": sha(a.pull_symbols)}},
           "method": "classify each difference against that symbol's archive coverage window, never pool a count"}

    inv = json.load(open(a.inventory))["inventory"]
    z = np.load(a.ledger, allow_pickle=True)
    ft = z["ft"].astype(np.int64); off = z["off"].astype(np.int64); syms = z["symbols"]
    led = collections.defaultdict(collections.Counter)
    for i in range(len(syms)):
        for t in ft[off[i]:off[i + 1]]:
            led[str(syms[i])][datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc)
                              .strftime("%Y-%m")] += 1
    led_syms = set(map(str, syms.tolist()))
    pull_syms = {l.strip() for l in open(a.pull_symbols) if l.strip()}

    arc = {(s, m) for s, d in inv.items() for m in d["months"]}
    ledp = {(s, m) for s, c in led.items() for m in c}

    only_led = sorted(ledp - arc)
    only_arc = sorted(arc - ledp)
    rec["totals"] = {"ledger_symbol_months": len(ledp), "archive_symbol_months": len(arc),
                     "both": len(ledp & arc), "ledger_only": len(only_led), "archive_only": len(only_arc)}

    cur = [x for x in only_led if x[1] == a.current_month]
    rest = [x for x in only_led if x[1] != a.current_month]
    cls = collections.Counter()
    holes, detail = [], []
    for s, m in rest:
        ms = sorted(inv.get(s, {}).get("months", {}))
        if not ms:
            k = "symbol_absent_from_archive_entirely"
            holes.append({"symbol": s, "month": m, "why": "no archived month at all for this symbol"})
        elif m < ms[0]:
            k = "before_archive_first_month"
        elif m > ms[-1]:
            k = "after_archive_last_month"
        else:
            k = "INSIDE_archive_window_a_real_hole"
            holes.append({"symbol": s, "month": m, "archive_window": [ms[0], ms[-1]]})
        cls[k] += 1
        detail.append({"symbol": s, "month": m, "ledger_events": int(led[s][m]),
                       "archive_window": [ms[0], ms[-1]] if ms else None, "class": k})

    rec["ledger_only_breakdown"] = {
        "current_month_not_yet_published": {"count": len(cur), "month": a.current_month,
                                            "why": "the archive publishes month M in early M+1"},
        "classified_rest": dict(cls), "rest_total": len(rest),
        "window_edge_total": cls["before_archive_first_month"] + cls["after_archive_last_month"],
        "real_holes_inside_window": cls["INSIDE_archive_window_a_real_hole"],
        "hypothesis": "the archive's per-symbol coverage window is NARROWER than the ledger's at both ends",
        "hypothesis_confirmed_for": f"{cls['before_archive_first_month'] + cls['after_archive_last_month']} of {len(rest)}",
        "unexplained": holes, "detail": detail}

    arc_only = []
    for s, m in only_arc:
        arc_only.append({"symbol": s, "month": m,
                         "in_ledger_symbol_axis": s in led_syms,
                         "in_pull_list": s in pull_syms,
                         "reading": ("NOT a missed settlement: this symbol is not in the ledger's universe "
                                     "at all" if s not in led_syms else
                                     "the ledger tracks this symbol but recorded no event that month -- a "
                                     "genuine missed-settlement candidate")})
    rec["archive_only_classified"] = arc_only
    rec["archive_only_that_are_real_candidates"] = sum(1 for x in arc_only if x["in_ledger_symbol_axis"])
    rec["symbols_in_pull_list_not_in_ledger_axis"] = sorted(pull_syms - led_syms)

    rec["truth_available_scoring_set"] = {
        "symbol_months_with_both_sides": len(ledp & arc),
        "note": ("question 4's held-out scoring can only use months where archive truth exists, i.e. this "
                 "set; the window edges above are exactly where no truth exists to score against")}
    rec["verdict"] = "MEASURED"
    rec["limits"] = ["month granularity; event-level completeness still needs the zip contents",
                     "a listing proves a file exists, not that its contents are complete"]
    with open(a.out, "w") as f:
        json.dump(rec, f, indent=2)

    t = rec["totals"]; b = rec["ledger_only_breakdown"]
    print("MONTH-GRANULARITY CLASSIFICATION")
    print(f"  ledger {t['ledger_symbol_months']}  archive {t['archive_symbol_months']}  both {t['both']}")
    print(f"  ledger-only {t['ledger_only']} = {b['current_month_not_yet_published']['count']} unpublished "
          f"{a.current_month} + {b['rest_total']} others")
    for k, v in sorted(b["classified_rest"].items()):
        print(f"     {k:38s} {v}")
    print(f"  hypothesis (archive window narrower at both ends) confirmed for {b['hypothesis_confirmed_for']}")
    print(f"  REAL holes inside an archive window: {b['real_holes_inside_window']}")
    print(f"  archive-only {t['archive_only']}, of which real candidates: "
          f"{rec['archive_only_that_are_real_candidates']}")
    for x in arc_only:
        print(f"     {x['symbol']} {x['month']}: in_ledger_axis={x['in_ledger_symbol_axis']} -> {x['reading'][:60]}")
    print(f"  truth-available scoring set: {rec['truth_available_scoring_set']['symbol_months_with_both_sides']}"
          " symbol-months")
    return 0


if __name__ == "__main__":
    sys.exit(main())

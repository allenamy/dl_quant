#!/usr/bin/env python3
"""d10_p2_src_composition.py -- P2 ledger_full.npz provenance composition per month, and the truth-source
conclusion lead asked to have written into a receipt rather than left in a message.

src semantics from the builder that writes them (p2_prep_inputs.py L7, L70-77, L89), not from the names:
  1 = API (fund_aug) only        2 = zip only
  3 = both present and EQUAL     4 = both present and UNEQUAL (the API rate is kept)
zip_iv is NaN exactly when src == 1, by construction -- a provenance fact, not a missing interval.

Why the composition matters for the truth-source question: a month that is 100% src==3 is largely CIRCULAR
evidence when checked against the monthly archive, because the ledger's zip side IS that archive. A month
that is 100% src==1 is an INDEPENDENT check against a later-published zip. So the composition is what tells
you which months' agreement actually carries weight.
"""
import collections
import datetime
import hashlib
import json
import os
import sys

import numpy as np

LEDGER = "/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz"
PIN = "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else LEDGER
    out = sys.argv[2] if len(sys.argv) > 2 else None
    s = sha(path)
    assert s == PIN, ("not the pinned ledger", s)
    Z = np.load(path, allow_pickle=True)
    ft = Z["ft"].astype(np.int64)
    src = Z["src"].astype(np.int8)
    ziv = Z["zip_iv"].astype(np.float64)

    per = collections.defaultdict(collections.Counter)
    for t, v in zip(ft, src):
        per[datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m")][int(v)] += 1

    glob = collections.Counter(int(v) for v in src)
    rows = []
    for m in sorted(per):
        c = per[m]
        tot = sum(c.values())
        rows.append({"month": m, "rows": tot, "api_only_1": c[1], "zip_only_2": c[2],
                     "both_equal_3": c[3], "both_unequal_4": c[4],
                     "pct_api_only": round(100.0 * c[1] / tot, 2),
                     "independence": ("INDEPENDENT_vs_monthly_zip" if c[1] == tot else
                                      ("LARGELY_CIRCULAR_vs_monthly_zip" if c[3] + c[2] == tot else "MIXED"))})

    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "ledger": {"path": path, "sha256": s, "rows": int(ft.size),
                      "span": [datetime.datetime.fromtimestamp(int(ft.min()), datetime.timezone.utc).isoformat(),
                               datetime.datetime.fromtimestamp(int(ft.max()), datetime.timezone.utc).isoformat()]},
           "src_codes": {"1": "API(fund_aug) only", "2": "zip only", "3": "both equal",
                         "4": "both UNEQUAL, API kept", "source": "p2_prep_inputs.py L7,L70-77"},
           "global": {"api_only_1": glob[1], "zip_only_2": glob[2], "both_equal_3": glob[3],
                      "both_unequal_4": glob[4], "total": int(src.size)},
           "nan_zip_iv_iff_src1": bool(np.array_equal(~np.isfinite(ziv), src == 1)),
           "per_month": rows,
           "conclusion_requested_by_lead": {
               "src4_across_whole_ledger": glob[4],
               "statement": ("src==4 -- the API and the monthly zip disagreeing on a shared second -- is "
                             f"{glob[4]} across all {int(src.size)} rows, i.e. the two sources never once "
                             "conflicted where both were present. Combined with 2026-08 matching the "
                             "later-published zip BITWISE on 103,527 events and rates while being 100% "
                             "API-only in the ledger (an independent, non-circular check), P2 ledger_full.npz "
                             "is adopted as the truth source for the October retrain and the final FX verdict. "
                             "Months that are 100% src==3 are largely circular evidence and are not what "
                             "carries this conclusion."),
               "audited_by": "D10_P2_LEDGER_VS_ARCHIVE_full.json (6,294/6,294 switch-window settlements "
                             "present; 463,715 rates bitwise equal) with its positive control "
                             "D10_P2_POSITIVE_CONTROL_2026-08.json (1 ULP and an in-window drop both seen)",
               "limits": ("the ledger ends 2026-09-01T02:00Z, so September is NOT covered by it either; "
                          "and the API side cannot be checked against a zip for any month whose zip the "
                          "builder never had"),
               "LIMIT_ADDED_BY_LEAD_RULING_REVISION_1": (
                   "src == 4 only covers conflicts that survive a BY-SECOND comparison. It does NOT cover a "
                   "settlement discarded INSIDE one second: p2_prep_inputs.py unions by t_ms // 1000, so when "
                   "the venue publishes two settlements milliseconds apart only one survives, and the "
                   "surviving row is marked src == 3 ('both sources present and equal') because the collision "
                   "was resolved before the sources were compared. The detector sits DOWNSTREAM of the "
                   "transformation that causes the loss, so it is structurally blind to it -- and so was my "
                   "own audit, which compared by second and therefore returned 463,715 rates bitwise equal. "
                   "Two independently built chains agreed while sharing one key convention, which counts a "
                   "single blind spot twice. Measured instances: MSFTUSDT 2026-05-21T00:00Z (6 ms apart, lost "
                   "-0.00217887) and AAPLUSDT 2026-05-11T00:00Z (3 ms apart, lost -0.00092193), found by the "
                   "UNRESOLVED_NON_INCREASING_TIME branch of interval_d10. Book impact is STRUCTURALLY zero, "
                   "verified rather than assumed: both names are book members at 0 of 10,333 anchors and "
                   "carry crypto = False in the candidate mask (680 of 829 symbols are crypto). Fixed as a "
                   "class per lead's DECISION_RULE_D10_stage2_2026-09-26.md revision 1: the October rebuild "
                   "keys events by fundingTime MILLISECONDS, keeps every settlement inside a second, takes "
                   "the later millisecond as the as-of, and counts such events by name."),
               "src4_does_not_cover": "within-second discards; see the limit above"}}

    print(f"P2 ledger_full src composition   sha {s[:16]}  rows {int(ft.size)}")
    print(f"  GLOBAL  api_only={glob[1]}  zip_only={glob[2]}  both_equal={glob[3]}  both_UNEQUAL={glob[4]}")
    print(f"  NaN zip_iv <=> src==1 : {rec['nan_zip_iv_iff_src1']}")
    print(f"  {'month':9s} {'rows':>8s} {'api_only':>9s} {'zip_only':>9s} {'both_eq':>9s} {'uneq':>5s}  independence")
    for r in rows:
        if r["month"] >= "2025-10" or r["api_only_1"] or r["both_unequal_4"]:
            print(f"  {r['month']:9s} {r['rows']:>8d} {r['api_only_1']:>9d} {r['zip_only_2']:>9d} "
                  f"{r['both_equal_3']:>9d} {r['both_unequal_4']:>5d}  {r['independence']}")
    print(f"  ({len(rows)} months total; only 2025-10 onward and any month with API-only/conflict rows shown)")
    if out:
        json.dump(rec, open(out, "w"), indent=1)
        print(f"  receipt -> {out}  sha256={sha(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

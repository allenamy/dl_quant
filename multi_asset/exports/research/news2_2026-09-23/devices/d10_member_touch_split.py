#!/usr/bin/env python3
"""d10_member_touch_split.py -- of the wrong cells, how many actually touched the book?

fresh's point, which applies to my own reporting: their parity denominator turned out to be 13 rather than
2,021 because almost none of those cells were BOOK MEMBERS at their anchor, and they measured the same shape
twice more (404 RN8 differing cells but only 16 moved the clamp population; 529,856 overlap cells with NC
stale but 0 book members). So a raw count of wrong cells overstates what reached the book, and I reported
5,613 and 100% without splitting them. This device does the split.

THE MEMBER SET, taken from the construction dlarch uses in the trainer, not from a mask whose name sounds
right:
    F   = NEWS_FEATURES.npz            # sha 3c886a2b, the clean feature file
    off = F['off']; ps = F['m']
    members[i] = ps[off[i]:off[i+1]]   # per-anchor member COLUMN INDICES into F['symbols']
Measured before use: m is int16 with max 828 against 829 symbols, count max 400, and count[i] is asserted
equal to off[i+1]-off[i] for every anchor. dlarch flagged explicitly that `cand = mask & crypto` is a
DIFFERENT quantity -- the tradable/candidate mask, not the column RN8 is filled at -- so it is not used here.

This device does not re-judge anything. It only partitions cells that another device already judged, so the
verdicts are untouched and only the denominator changes.
"""
import collections
import csv
import datetime
import hashlib
import json
import os
import sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    feats, cells_csv, out = sys.argv[1], sys.argv[2], sys.argv[3]
    F = np.load(feats, allow_pickle=True)
    anchors = F["anchors"].astype(np.int64)
    syms = [str(s) for s in F["symbols"]]
    off = F["off"].astype(np.int64)
    ps = F["m"].astype(np.int64)
    count = F["count"].astype(np.int64)

    # the construction must close before it is used
    assert len(off) == len(anchors) + 1, ("off length", len(off), len(anchors))
    diffs = np.diff(off)
    assert np.array_equal(diffs, count), "count[i] != off[i+1]-off[i]: the member construction does not close"
    assert ps.max() < len(syms), ("member index beyond the symbol axis", int(ps.max()), len(syms))

    sidx = {s: j for j, s in enumerate(syms)}
    aidx = {int(t): i for i, t in enumerate(anchors)}
    member_at = {}
    for i in range(len(anchors)):
        member_at[i] = set(int(x) for x in ps[off[i]:off[i + 1]])

    rows = [r for r in csv.DictReader(l for l in open(cells_csv) if not l.startswith("#"))]
    c = collections.Counter()
    by_verdict = collections.defaultdict(collections.Counter)
    member_examples = []
    per_anchor_members = collections.Counter()
    for r in rows:
        s, au, v = r["symbol"], r["anchor_utc"], r["verdict"]
        A = int(datetime.datetime.strptime(au, "%Y-%m-%dT%H:%MZ")
                .replace(tzinfo=datetime.timezone.utc).timestamp())
        i, j = aidx.get(A), sidx.get(s)
        if i is None:
            c["EXCLUDED_anchor_not_on_feature_axis"] += 1
            by_verdict[v]["EXCLUDED_anchor_not_on_feature_axis"] += 1
            continue
        if j is None:
            c["EXCLUDED_symbol_not_on_feature_axis"] += 1
            by_verdict[v]["EXCLUDED_symbol_not_on_feature_axis"] += 1
            continue
        if j in member_at[i]:
            c["BOOK_MEMBER"] += 1
            by_verdict[v]["BOOK_MEMBER"] += 1
            per_anchor_members[au] += 1
            if len(member_examples) < 40:
                member_examples.append({k: r.get(k) for k in
                                        ("symbol", "anchor_utc", "verdict", "p2_truth_rate",
                                         "panel_value", "ledger_value", "asof_event_utc", "asof_age_s")})
        else:
            c["NOT_A_MEMBER_at_that_anchor"] += 1
            by_verdict[v]["NOT_A_MEMBER_at_that_anchor"] += 1

    tot = len(rows)
    assert sum(c.values()) == tot, ("split does not close", sum(c.values()), tot)
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "question": "of the judged wrong cells, how many were BOOK MEMBERS at that anchor?",
           "prompted_by": ("fresh: their parity denominator was 13 not 2,021 because nearly none of those "
                           "cells were book members; the same shape appeared twice more in their work "
                           "(404 RN8 cells but 16 moved the clamp population; 529,856 stale-overlap cells "
                           "but 0 book members). A raw wrong-cell count overstates what reached the book."),
           "member_source": {"path": feats, "sha256": sha(feats),
                             "construction": "members[i] = m[off[i]:off[i+1]] -> column indices into symbols",
                             "cited": "the construction dlarch's trainer and leg devices use",
                             "explicitly_not": "cand = mask & crypto (the tradable/candidate mask) is a "
                                               "DIFFERENT quantity and is not used here",
                             "closure_asserted": "count[i] == off[i+1]-off[i] for all anchors; "
                                                 "max member index < len(symbols)",
                             "anchors": int(len(anchors)), "symbols": len(syms),
                             "axis_span": [datetime.datetime.fromtimestamp(int(anchors.min()), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                                           datetime.datetime.fromtimestamp(int(anchors.max()), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")],
                             "total_member_cells_on_axis": int(count.sum())},
           "cells_csv": {"path": cells_csv, "sha256": sha(cells_csv), "rows": tot},
           "split": {k: int(v) for k, v in c.items()},
           "split_by_verdict": {k: dict(v) for k, v in by_verdict.items()},
           "book_touch_pct_of_all_judged": round(100.0 * c["BOOK_MEMBER"] / tot, 4) if tot else None,
           "anchors_with_at_least_one_member_cell": len(per_anchor_members),
           "worst_anchors": per_anchor_members.most_common(10),
           "member_cell_examples": member_examples}
    print(f"member-touch split over {tot} judged cells")
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print(f"   {k:34s} {v:>6d}  {100.0*v/tot:6.2f}%")
    print(f"   anchors carrying at least one member cell: {len(per_anchor_members)}")
    print(f"   worst anchors: {per_anchor_members.most_common(5)}")
    json.dump(rec, open(out, "w"), indent=1)
    print(f"   receipt -> {out}  sha256={sha(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

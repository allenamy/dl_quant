#!/usr/bin/env python3
"""d10_fx_stall_decomposition.py -- is the replay's as-of OLDER than the truth's, on the FX population?

fresh's discriminating signature ("the gate was active AND the ledger held settlements the replay never
fetched") explains 89.1% of THEIR 404 cells -- the NEW_S vs NC legs disagreements. That is a different
population from the 5,613 FX cells (panel f_fund_now vs replay last_rate), so running their signature on mine
would compare unlike quantities; their 404 and my 5,613 are not the same thing measured twice.

What CAN be tested independently, and on a population 14x larger, is the MECHANISM: if the replay's as-of
froze, then for a wrong cell the replay's own last_ft must be EARLIER than the true as-of event. That is a
different instrument (replay's recorded timestamp vs P2 ledger's as-of) on a different population, reaching
the same mechanism -- which is the kind of agreement no single chain's receipts can establish.

Classes are the same shape I used for item 2 and the legs audit, so a same-second value difference is never
counted as a stall:
  STALE_ASOF          replay last_ft < the truth's as-of ft   -> the freeze signature
  SAME_ASOF_DIFF_VALUE  same second, different value          -> an interval/caliber issue, NOT a freeze
  REPLAY_AHEAD        replay last_ft > truth's as-of ft       -> would be causality-violating; investigate
  NO_REPLAY_ASOF      replay has no row at or before the anchor
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


def iso(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def main():
    cells_csv, replay, out = sys.argv[1], sys.argv[2], sys.argv[3]
    R = np.load(replay, allow_pickle=True)
    ra = R["anchors"].astype(np.int64)
    rs = [str(s) for s in R["symbols"]]
    LFT = R["last_ft"].astype(np.int64)
    ri = {int(t): i for i, t in enumerate(ra)}
    rj = {s: j for j, s in enumerate(rs)}

    rows = [r for r in csv.DictReader(l for l in open(cells_csv) if not l.startswith("#"))]
    c = collections.Counter()
    behind = []
    examples = collections.defaultdict(list)
    for r in rows:
        s, au = r["symbol"], r["anchor_utc"]
        A = int(datetime.datetime.strptime(au, "%Y-%m-%dT%H:%MZ")
                .replace(tzinfo=datetime.timezone.utc).timestamp())
        i, j = ri.get(A), rj.get(s)
        if i is None or j is None:
            c["EXCLUDED_not_on_replay_axis"] += 1
            continue
        rft = int(LFT[i, j])
        tft = int(datetime.datetime.strptime(r["asof_event_utc"], "%Y-%m-%dT%H:%MZ")
                  .replace(tzinfo=datetime.timezone.utc).timestamp())
        if rft < 0:
            k = "NO_REPLAY_ASOF"
        elif rft < tft:
            k = "STALE_ASOF"
            behind.append(tft - rft)
        elif rft == tft:
            k = "SAME_ASOF_DIFF_VALUE"
        else:
            k = "REPLAY_AHEAD_investigate"
        c[k] += 1
        if len(examples[k]) < 5:
            examples[k].append({"symbol": s, "anchor": au, "replay_asof": iso(rft) if rft > 0 else None,
                                "truth_asof": r["asof_event_utc"], "behind_s": (tft - rft) if rft > 0 else None,
                                "panel": r["panel_value"], "replay_value": r["ledger_value"],
                                "truth": r["p2_truth_rate"]})

    judged = sum(v for k, v in c.items() if not k.startswith("EXCLUDED"))
    assert judged + c["EXCLUDED_not_on_replay_axis"] == len(rows), "classification does not close"
    behind.sort()
    rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.realpath(__file__)),
           "question": "on the FX population, is the replay's as-of older than the truth's?",
           "why_not_freshs_signature": ("fresh's signature is defined on their 404 NEW_S-vs-NC cells; these "
                                        "5,613 are panel-vs-replay cells. Different populations, so running "
                                        "their signature here would compare unlike quantities. This tests the "
                                        "same MECHANISM with a different instrument on a larger population."),
           "inputs": {"cells_csv": {"path": cells_csv, "sha256": sha(cells_csv), "rows": len(rows)},
                      "replay": {"path": replay, "sha256": sha(replay)}},
           "counts": {k: int(v) for k, v in c.items()},
           "cells_judged": judged,
           "stale_share_pct": round(100.0 * c["STALE_ASOF"] / judged, 2) if judged else None,
           "behind_s": {"median": behind[len(behind) // 2] if behind else None,
                        "min": behind[0] if behind else None, "max": behind[-1] if behind else None,
                        "median_hours": round(behind[len(behind) // 2] / 3600.0, 2) if behind else None},
           "examples": {k: v for k, v in examples.items()}}
    print(f"FX stall decomposition over {len(rows)} cells")
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print(f"   {k:28s} {v:>6d}  {100.0*v/max(1,judged):5.1f}%")
    print(f"   behind_s median={rec['behind_s']['median']} ({rec['behind_s']['median_hours']} h) "
          f"min={rec['behind_s']['min']} max={rec['behind_s']['max']}")
    json.dump(rec, open(out, "w"), indent=1)
    print(f"   receipt -> {out}  sha256={sha(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

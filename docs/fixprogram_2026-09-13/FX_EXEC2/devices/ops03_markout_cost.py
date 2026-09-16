#!/usr/bin/python3
"""OPS-03 A — what the sliding weight shaper COSTS the markout backfill, as a number. Offline, read-only.

THE QUESTION. Option A delays requests so that no sliding 60 s window exceeds the self-cap. The anchor has a hard
wall-clock cap (3,600 s) and the markout backfill's deadline is derived from it (`max_seconds = cap − elapsed − 90`),
so any delay taken earlier in the anchor comes straight out of the backfill's budget. The backfill is metronome-paced
at `PACE_S` seconds per venue request (`ops/backfill_markout.py:111`), so the cost converts exactly:

    fewer_requests = added_delay_s / PACE_S
    fewer_marks    = fewer_requests × (marks written / requests spent) on THAT anchor

★ AND IT IS ZERO WHERE THE BACKFILL WAS NOT DEADLINE-BOUND. A run that drained its pending queue before the deadline
  loses no marks at all — it simply finishes later. Only a run whose own log line says `CAPPED(deadline)` pays. Quoting
  one average over all anchors would hide that, so each anchor is reported with its own cap state.

★ THE RATIO IS MEASURED PER ANCHOR, NOT ASSUMED. One aggTrades request resolves a CLUSTER of pending marks, and the
  cluster size varies with how the fills bunch; `marks written / requests spent` is read from that run's own line.

Usage:
  /usr/bin/python3 ops03_markout_cost.py <anchor_runs.log> <OPS03_sliding_shaper_replay.json> <pace_s> <out.json>
"""
import hashlib
import json
import os
import re
import sys

LOG, REPLAY, PACE_S, OUT = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]

MARK = re.compile(r"^(?P<ts>\S+Z) markout_backfill: day=(?P<day>\d{8}) .*?written=(?P<w>\d+) .*?requests=(?P<r>\d+)"
                  r"(?P<cap> CAPPED\((?P<why>[a-z_]+)\))?\s*$")
RID = re.compile(r'"rebalance_id":\s*"(A\d+)"')
DONE = re.compile(r"^(?P<ts>\S+Z) anchor done")


def sha(p):
    raw = open(p, "rb").read()
    assert len(raw) == os.stat(p).st_size, f"short read {p}"
    return hashlib.sha256(raw).hexdigest()


# ── split the log into RUNS at each `anchor done`, and label each run by the rid it names ──
runs, cur = [], {"rids": set(), "marks": []}
for line in open(LOG, errors="replace"):
    for m in RID.finditer(line):
        cur["rids"].add(m.group(1))
    mk = MARK.match(line.rstrip("\n"))
    if mk:
        cur["marks"].append({"utc": mk.group("ts"), "day": mk.group("day"),
                             "written": int(mk.group("w")), "requests": int(mk.group("r")),
                             "capped_by": mk.group("why")})
    if DONE.match(line):
        cur["done_utc"] = DONE.match(line).group("ts")
        runs.append(cur)
        cur = {"rids": set(), "marks": []}
if cur["marks"] or cur["rids"]:
    runs.append(cur)

by_rid = {}
for r in runs:
    for rid in r["rids"]:
        by_rid.setdefault(rid, r)

replay = json.load(open(REPLAY))
rows, unmatched = [], []
for rid, a in replay["anchors"].items():
    run = by_rid.get(rid)
    if run is None:
        unmatched.append(rid)
        continue
    delay = float((a.get("sliding_replay") or {}).get("total_delay_s") or 0.0)
    written = sum(m["written"] for m in run["marks"])
    requests = sum(m["requests"] for m in run["marks"])
    capped = any(m["capped_by"] == "deadline" for m in run["marks"])
    mpr = (written / requests) if requests else None
    fewer_req = delay / PACE_S
    rows.append({
        "rebalance_id": rid, "anchor_done_utc": run.get("done_utc"),
        "added_delay_s_sliding": delay,
        "markout_written": written, "markout_requests": requests,
        "marks_per_request": mpr, "deadline_capped": capped,
        "fewer_requests": fewer_req,
        # zero where the run was NOT deadline-bound: it finishes later, it does not write less
        "fewer_marks": (round(fewer_req * mpr, 1) if (capped and mpr is not None) else 0.0),
        "cost_basis": ("deadline-bound: the delay comes out of the backfill's own budget" if capped
                       else "not deadline-bound: the run drained its queue, so the delay costs marks only if it "
                            "would push the run past the deadline, which it did not here"),
        "recorded_sliding60_max": a.get("recorded_sliding60_max"),
        "venue_header_used_weight_1m_max": a.get("venue_header_used_weight_1m_max"),
    })

rows.sort(key=lambda r: r["anchor_done_utc"] or "")
capped_rows = [r for r in rows if r["deadline_capped"]]
rec = {"device": os.path.basename(__file__), "device_sha256": sha(os.path.abspath(__file__)),
       "anchor_runs_log_sha256": sha(LOG), "replay_receipt_sha256": sha(REPLAY),
       "pace_s": PACE_S, "n_anchors": len(rows), "unmatched_rids": unmatched,
       "totals": {"n_deadline_capped": len(capped_rows),
                  "fewer_marks_total_on_capped": round(sum(r["fewer_marks"] for r in rows), 1),
                  "worst_anchor_fewer_marks": (max((r["fewer_marks"] for r in rows), default=0.0)),
                  "worst_anchor": (max(rows, key=lambda r: r["fewer_marks"])["rebalance_id"] if rows else None)},
       "rows": rows}
json.dump(rec, open(OUT, "w"), ensure_ascii=False, indent=1)

print(f"anchors {len(rows)} (unmatched {unmatched}) · pace {PACE_S}s/request")
for r in rows:
    print(f"  {r['anchor_done_utc']}  {r['rebalance_id']:<12} delay {r['added_delay_s_sliding']:6.1f}s  "
          f"written {r['markout_written']:>4} / req {r['markout_requests']:>4} = {(r['marks_per_request'] or 0):.3f} "
          f"marks/req  capped {str(r['deadline_capped']):<5} ⇒ FEWER MARKS {r['fewer_marks']}")
print(f"total fewer marks across the replayed anchors: {rec['totals']['fewer_marks_total_on_capped']} "
      f"(deadline-capped anchors: {rec['totals']['n_deadline_capped']} of {len(rows)})")
print(f"receipt -> {OUT}")

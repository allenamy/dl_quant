"""W6C-I6 (READ-ONLY): how often does an OFF-SCHEDULE run happen, in which mode, and what did the
watchdog make of the anchor it wrote?

Parses state/anchor_runs.log by pairing every `anchor start mode=` line with the phase_A / phase_C
JSON that follows it, then — for the LIVE off-schedule runs — looks up how position_break judged
that anchor in the pilot_log.

usage: probe_i6_offschedule.py <code_tree> <state_root>     (state_root holds anchor_runs.log and live/pilot_log)
"""
import sys, os, json, re, collections, time

CODE, STATE = sys.argv[1], sys.argv[2]
for d in ("live", "scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(CODE, d))
import pilot_log as PL, position_break as PB, reconcile as RC      # noqa: E402

runs, cur = [], None
for line in open(os.path.join(STATE, "anchor_runs.log"), errors="replace"):
    m = re.search(r"anchor start mode=([A-Z_]+)", line)
    if m:
        if cur:
            runs.append(cur)
        cur = {"mode": m.group(1), "utc": line[:20], "phase_A": None, "phase_C": None}
        continue
    if cur is None:
        continue
    for tag in ("phase_A", "phase_C"):
        if f" {tag}: " in line:
            try:
                cur[tag] = json.loads(line.split(f" {tag}: ", 1)[1])
            except Exception:
                pass
if cur:
    runs.append(cur)

counts = collections.Counter()
live_off = []
for r in runs:
    off = bool((r["phase_A"] or {}).get("off_schedule_halt"))
    counts[(r["mode"], off)] += 1
    if off and r["mode"] == "LIVE":
        live_off.append(r)

# how position_break judged each LIVE off-schedule anchor, from the rows themselves
ROOT = os.path.join(STATE, "live", "pilot_log")
judged = []
for r in live_off:
    a = r["phase_A"] or {}
    wall = a.get("anchor_wall_ts")
    day = time.strftime("%Y%m%d", time.gmtime(wall)) if wall else None
    rec = {"utc": r["utc"], "offset_min": (a.get("off_schedule_halt") or {}).get("offset_min"),
           "action": a.get("action"), "anchor_wall_ts": wall, "day": day,
           "phase_C": r["phase_C"]}
    if day and os.path.isdir(os.path.join(ROOT, day)):
        one = PL.read_day(ROOT, day)
        dd = [(day, one)]
        pb = PB.evaluate(dd, residual_by_anchor=RC.reconcile(dd).get("residual_by_anchor"))
        near = [x for x in pb["per_anchor"] if wall and abs(float(x["anchor_ts"]) - wall) < 600]
        if near:
            row = min(near, key=lambda x: abs(float(x["anchor_ts"]) - wall))
            rb = [q for q in one.get("position_readback", [])
                  if abs(float(q["anchor_ts"]) - float(row["anchor_ts"])) < 1]
            rec["judged"] = {k: row.get(k) for k in
                             ("anchor_ts", "anchor_kind", "judged", "state", "triggered",
                              "trip_gate", "target_gross", "n_submitted",
                              "portfolio_dev_usdt", "portfolio_dev_frac", "portfolio_limit_frac")}
            rec["readback_gross_usdt"] = round(
                sum(abs(float(q["venue_position_notional"])) for q in rb), 2)
            rec["n_readback_rows"] = len(rb)
    judged.append(rec)

print(json.dumps({"state_root": STATE, "n_runs": len(runs),
                  "by_mode_off_schedule": {f"{k[0]}|off={k[1]}": v for k, v in sorted(counts.items(), key=str)},
                  "live_off_schedule": judged}, indent=1, default=str))

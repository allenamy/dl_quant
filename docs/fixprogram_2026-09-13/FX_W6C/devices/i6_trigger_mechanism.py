"""W6C-I6 trigger mechanism (READ-ONLY on the live tree): was each LIVE off-schedule run started by
launchd (a catch-up after sleep/shutdown) or by a human?

THE DISCRIMINATOR IS THE PLIST'S OWN REDIRECT, not a guess. `com.dlquant.live.anchor` sets
StandardOutPath = state/launchd_out.log, so EVERY launchd-started run's stdout lands there. A run
started by hand from a shell does not. `state/anchor_runs.log` is written by the process itself and
therefore holds every run however it was started. So:

    in anchor_runs.log AND in launchd_out.log  -> launchd started it
    in anchor_runs.log but NOT in launchd_out  -> something else started it (a human)

It also answers the second question — has launchd's StartCalendarInterval catch-up EVER fired? —
by two independent counts: how many launchd-started anchors begin away from :00:0xZ, and how many
expected 4-hour slots have no launchd-started anchor at all.

usage: i6_trigger_mechanism.py <live_state_root>
"""
import sys, os, re, json, datetime

STATE = sys.argv[1]
RUNS = os.path.join(STATE, "anchor_runs.log")
LD = os.path.join(STATE, "launchd_out.log")
PAT = re.compile(r'^(2026-\d\d-\d\dT\d\d:\d\d:\d\d)Z anchor start mode=(\w+)')


def starts(path):
    out = []
    for line in open(path, errors="replace"):
        m = PAT.match(line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


all_runs, launchd = starts(RUNS), starts(LD)
ld_set = {t for t, _ in launchd}

# the LIVE runs that gate 0c refused (off-schedule), read from the run's own phase_A record
off = []
cur = None
for line in open(RUNS, errors="replace"):
    m = PAT.match(line)
    if m:
        cur = {"utc": m.group(1), "mode": m.group(2), "phase_A": None}
        continue
    if cur is not None and " phase_A: " in line:
        try:
            cur["phase_A"] = json.loads(line.split(" phase_A: ", 1)[1])
        except Exception:
            pass
        a = cur["phase_A"] or {}
        if cur["mode"] == "LIVE" and a.get("off_schedule_halt"):
            off.append({"utc": cur["utc"],
                        "offset_min": (a.get("off_schedule_halt") or {}).get("offset_min"),
                        "action": a.get("action"),
                        "in_launchd_out_log": cur["utc"] in ld_set})
        cur = None

# neighbours within 30 min, from anchor_runs.log — a human at the keyboard leaves DRY_RUN runs
for o in off:
    t0 = datetime.datetime.strptime(o["utc"], "%Y-%m-%dT%H:%M:%S")
    near = []
    for t, mode in all_runs:
        dt = (datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S") - t0).total_seconds() / 60.0
        if t != o["utc"] and abs(dt) <= 30:
            near.append({"utc": t, "mode": mode, "minutes": round(dt, 2)})
    o["runs_within_30min"] = near

# has a catch-up ever fired?
off_slot = [t for t, _ in launchd if not re.match(r'^2026-\d\d-\d\dT\d\d:00:0\d$', t)]
first, last = datetime.datetime(2026, 8, 1), datetime.datetime(2026, 9, 16, 4)
expected, missing, cur2 = 0, [], first
while cur2 <= last:
    if cur2.hour % 4 == 0:
        expected += 1
        if cur2.strftime('%Y-%m-%dT%H') not in {t[:13] for t in ld_set}:
            missing.append(cur2.strftime('%Y-%m-%dT%HZ'))
    cur2 += datetime.timedelta(hours=4)

print(json.dumps({
    "state_root": STATE,
    "n_runs_in_anchor_runs_log": len(all_runs),
    "n_runs_in_launchd_out_log": len(launchd),
    "live_off_schedule_runs": off,
    "catch_up_evidence": {
        "launchd_started_anchors_not_at_00_0xZ": off_slot,
        "n_launchd_started_anchors": len(launchd),
        "expected_4h_slots_20260801T00_to_20260916T04": expected,
        "slots_with_no_launchd_anchor": missing,
        "reading": ("a StartCalendarInterval catch-up is ALWAYS LATE and would appear as a "
                    "launchd-started anchor away from :00:0xZ, or as a slot with no anchor at "
                    "its nominal minute. Both counts are the evidence.")},
}, indent=1, default=str))

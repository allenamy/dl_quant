"""E4 population census (read-only, census copy 2026-09-13T13:04:09Z): how many chase-experiment assignments were stopped names (plan-time stop set =
previous LIVE anchor's phase_C per_name_stop.stopped), i.e. how much of the experiment's population E4 removes."""
import json, re, glob, collections, calendar, time, sys
P = sys.argv[1] if len(sys.argv) > 1 else "/Users/haosiyu/cc_tmp/fx_exec_census"
PAT = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (.*)$")
blocks, cur = [], None
for ln in open(P + "/anchor_runs.log", errors="replace"):
    m = PAT.match(ln.rstrip("\n"))
    if not m: continue
    ts, rest = m.groups()
    if rest.startswith("anchor start mode="):
        cur = {"mode": rest.split("=", 1)[1].strip(), "ph": {}}; blocks.append(cur); continue
    if cur is None: continue
    for t in ("phase_A", "phase_C"):
        if rest.startswith(t + ": "):
            try: cur["ph"][t] = json.loads(rest[len(t) + 2:])
            except Exception: pass
live = [b for b in blocks if b["mode"] == "LIVE" and (b["ph"].get("phase_A") or {}).get("rebalance_id")]
stop_after = {}          # rid -> stopped set written at that anchor's end
order = []
for b in live:
    rid = b["ph"]["phase_A"]["rebalance_id"]
    pc = (b["ph"].get("phase_C") or {}).get("per_name_stop")
    if rid not in stop_after:
        order.append(rid)
    if isinstance(pc, dict):
        stop_after[rid] = set(pc.get("stopped") or [])
prev_stop = {}
last = None
for rid in order:
    if last is not None:
        prev_stop[rid] = stop_after.get(last)
    last = rid
rows = []
for f in sorted(glob.glob(P + "/pilot_log/*/anchors.jsonl")):
    for l in open(f):
        if l.strip():
            r = json.loads(l)
            if r.get("chase_experiment"):
                rows.append(r)
RESTART = calendar.timegm(time.strptime("2026-09-01T16:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))
START = calendar.timegm(time.strptime("2026-08-20T04:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))
agg = collections.defaultdict(lambda: {"anchors": 0, "population": 0, "stopped_in_population": 0, "arms": collections.Counter(), "no_stop_state": 0})
ex = []
for r in rows:
    ats = float(r["anchor_ts"])
    if ats < START: continue
    per = "policyA_08-20..09-01_12Z" if ats < RESTART else "restart_09-01_16Z..09-13"
    ce = r["chase_experiment"]
    arm = ce.get("arm_assigned") or ce.get("arm") or {}
    st = prev_stop.get(r["rebalance_id"])
    a = agg[per]; a["anchors"] += 1; a["population"] += len(arm)
    if st is None:
        a["no_stop_state"] += 1; continue
    hit = sorted(s for s in arm if s in st)
    a["stopped_in_population"] += len(hit)
    for s in hit:
        a["arms"][arm[s]] += 1
        ex.append((time.strftime("%m-%d %H:%MZ", time.gmtime(ats)), s, arm[s]))
for per, a in sorted(agg.items()):
    share = a["stopped_in_population"] / a["population"] if a["population"] else None
    print(per, {k: (dict(v) if isinstance(v, collections.Counter) else v) for k, v in a.items()}, "share", None if share is None else f"{share:.4%}")
print("instances:", ex)

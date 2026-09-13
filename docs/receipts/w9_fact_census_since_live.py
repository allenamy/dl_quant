"""W9 fact F-CENSUS: every (anchor, stopped-and-held name) since the stop went live (0bcc089, 2026-08-20), recorded clamp bucket by side.
Stop set at plan time = previous LIVE anchor's phase_C per_name_stop.stopped; held = previous anchor readback notional; bucket = phase_A untradable_names.
Reads the frozen T5b private copy (read-only)."""
import json, re, calendar, time, collections
P = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T5b/private"
def G(t): return int(float(t) // 14400) * 14400
blocks = collections.defaultdict(list); cur = None; pat = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (.*)$")
for ln in open(P + "/exec/anchor_runs.log", errors="replace"):
    m = pat.match(ln.rstrip("\n"))
    if not m: continue
    ts, rest = m.groups()
    if rest.startswith("anchor start mode="):
        if cur is not None and cur["ph"]: blocks[cur["key"]].append(cur)
        cur = dict(mode=rest.split("=", 1)[1].strip(), ph={}, key=G(calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")))); continue
    if cur is None: continue
    for tag in ("phase_A", "phase_C"):
        if rest.startswith(tag + ": "):
            try:
                cur["ph"][tag] = json.loads(rest[len(tag) + 2:])
                if tag == "phase_A" and cur["ph"][tag].get("anchor_ts"): cur["key"] = G(cur["ph"][tag]["anchor_ts"])
            except Exception: pass
    if rest.startswith("anchor done rc="): blocks[cur["key"]].append(cur); cur = None
def lb(A):
    bl = [b for b in blocks.get(A, []) if b["mode"] == "LIVE"]; wc = [b for b in bl if "phase_C" in b["ph"]]
    return wc[-1] if wc else (bl[-1] if bl else None)
RB = {}
import os
for d in sorted(os.listdir(P + "/exec/pilot_log")):
    p = f"{P}/exec/pilot_log/{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p, errors="replace"):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get("anchor_ts") is not None: RB[(G(r["anchor_ts"]), r["symbol"])] = r
start = G(calendar.timegm(time.strptime("2026-08-20T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")))
end = G(calendar.timegm(time.strptime("2026-09-12T12:00:00Z", "%Y-%m-%dT%H:%M:%SZ")))
cnt = collections.Counter(); per_win = collections.Counter(); first_stop = None; examples = collections.defaultdict(list)
for A in range(start, end + 1, 14400):
    b, bp = lb(A), lb(A - 14400)
    if not b or not bp: continue
    pcp = (bp["ph"].get("phase_C") or {}).get("per_name_stop")
    if not isinstance(pcp, dict) or not pcp.get("stopped"): continue
    pa = b["ph"].get("phase_A") or {}
    if not isinstance(pa, dict): continue
    un = pa.get("untradable_names") or {}
    for s in pcp["stopped"]:
        rb = RB.get((A - 14400, s)); held = float(rb["venue_position_notional"]) if rb else 0.0
        if held == 0.0: continue
        first_stop = first_stop or A
        side = "long" if held > 0 else "short"
        recb = ",".join(k for k, v in un.items() if isinstance(v, list) and s in v) or ("UNLISTED" if un else "NO_PHASE_A_BUCKETS")
        win = "08-20..08-25" if A < G(calendar.timegm(time.strptime("2026-08-26T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))) else "08-26..09-12"
        cnt[(side, recb)] += 1; per_win[(win, side, recb)] += 1
        if len(examples[(side, recb)]) < 3: examples[(side, recb)].append(f"{time.strftime('%m-%d %H:%MZ', time.gmtime(A))} {s} {held:+.1f}")
print("first stopped-and-held anchor:", time.strftime('%Y-%m-%d %H:%MZ', time.gmtime(first_stop)) if first_stop else None)
print("by side x recorded bucket (all anchors 08-20..09-12 12Z):", dict(cnt), "total", sum(cnt.values()))
print("by window:", dict(per_win))
for k, v in examples.items(): print("  e.g.", k, v)

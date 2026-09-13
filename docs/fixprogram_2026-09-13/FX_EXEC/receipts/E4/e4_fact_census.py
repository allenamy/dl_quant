"""E4 fact census (read-only; inputs = /Users/haosiyu/cc_tmp/fx_exec_census, copied from ~/dl_quant_live/state at 2026-09-13T13:04:09Z).
For every LIVE anchor with a stopped-and-held name (stop set = previous LIVE anchor's phase_C per_name_stop.stopped, as the executor reads it
at plan time; held = previous anchor readback notional), classify what the execution channel did for that name at this anchor:
maker row terminal, top-up row terminal / topup_source / chase_arm / sent. Also the same for every other flatten_only name (non-stop).
Periods: policy A weights {chase 0, no_chase 1} (164285b, 08-10) until the 09-01 16:00Z anchor; restart {0.5, 0.5} (8b7a61e) after."""
import json, re, calendar, time, collections, os, sys
P = sys.argv[1] if len(sys.argv) > 1 else "/Users/haosiyu/cc_tmp/fx_exec_census"
def G(t): return int(float(t) // 14400) * 14400
def T(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
blocks = collections.defaultdict(list); cur = None; pat = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (.*)$")
for ln in open(P + "/anchor_runs.log", errors="replace"):
    m = pat.match(ln.rstrip("\n"))
    if not m: continue
    ts, rest = m.groups()
    if rest.startswith("anchor start mode="):
        if cur is not None and cur["ph"]: blocks[cur["key"]].append(cur)
        cur = dict(mode=rest.split("=", 1)[1].strip(), ph={}, key=G(T(ts))); continue
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
RB, ORD = {}, collections.defaultdict(list)
for d in sorted(os.listdir(P + "/pilot_log")):
    for fn, tgt in (("position_readback.jsonl", "rb"), ("orders.jsonl", "ord")):
        p = f"{P}/pilot_log/{d}/{fn}"
        if not os.path.exists(p): continue
        for ln in open(p, errors="replace"):
            try: r = json.loads(ln)
            except Exception: continue
            if not isinstance(r, dict) or r.get("anchor_ts") is None: continue
            if tgt == "rb": RB[(G(r["anchor_ts"]), r["symbol"])] = r
            else: ORD[(r.get("rebalance_id"), r.get("symbol"))].append(r)
RESTART = T("2026-09-01T16:00:00Z"); W9 = T("2026-09-13T12:00:00Z")
start = T("2026-08-20T04:00:00Z"); end = max(blocks)
def period(A): return "A_policyA_0/1(08-20..09-01 12Z)" if A < RESTART else ("B_restart_0.5/0.5(09-01 16Z..09-13 08Z)" if A < W9 else "C_post_W9(09-13 12Z..)")
def leg_class(rows):
    mk = [r for r in rows if r.get("order_type") == "maker"]; tu = [r for r in rows if r.get("order_type") == "topup_taker"]
    m = ",".join(sorted({str(r.get("terminal_reason")) for r in mk})) or "no_maker_row"
    if not tu: return m, "no_topup_row"
    t = tu[-1]
    sent = t.get("submit_ts") is not None
    return m, f"{t.get('terminal_reason')}|src={t.get('topup_source')}|arm={t.get('chase_arm')}|sent={sent}"
stop_cnt = collections.Counter(); other_cnt = collections.Counter(); ex = collections.defaultdict(list)
n_anchor = 0
for A in range(start, end + 1, 14400):
    b, bp = lb(A), lb(A - 14400)
    if not b or not bp: continue
    pa = b["ph"].get("phase_A") or {}
    if not isinstance(pa, dict) or not pa.get("rebalance_id"): continue
    n_anchor += 1
    rid = pa["rebalance_id"]
    pcp = (bp["ph"].get("phase_C") or {}).get("per_name_stop") or {}
    stopped = set(pcp.get("stopped") or []) if isinstance(pcp, dict) else set()
    un = pa.get("untradable_names") or {}
    fo = set(un.get("flatten_only") or []) if isinstance(un, dict) else set()
    for s in sorted(stopped):
        rb = RB.get((A - 14400, s)); held = float(rb["venue_position_notional"]) if rb else 0.0
        if held == 0.0: continue
        bucket = ",".join(k for k, v in un.items() if isinstance(v, list) and s in v) or "UNLISTED"
        mk, tu = leg_class(ORD.get((rid, s), []))
        key = (period(A), bucket, mk, tu); stop_cnt[key] += 1
        if len(ex[key]) < 3: ex[key].append(f"{time.strftime('%m-%d %H:%MZ', time.gmtime(A))} {s} {held:+.1f}")
    for s in sorted(fo - stopped):
        mk, tu = leg_class(ORD.get((rid, s), []))
        other_cnt[(period(A), tu.split("|")[0] + "|" + tu.split("|")[1] if "|" in tu else tu)] += 1
print("inputs:", P, "live anchors walked:", n_anchor, "last anchor:", time.strftime('%Y-%m-%d %H:%MZ', time.gmtime(end)))
print("\n== STOPPED-AND-HELD names: (period, recorded clamp bucket, maker terminal, top-up row) -> count ==")
for k in sorted(stop_cnt): print(f"  {stop_cnt[k]:4d}  {k}  e.g. {ex[k]}")
agg = collections.Counter()
for (per, bucket, mk, tu), n in stop_cnt.items():
    sent = "sent=True" in tu
    agg[(per, "taker_IOC_sent" if sent else ("withheld_no_chase_arm" if "skipped_no_chase_arm" in tu else ("no_topup_row" if tu == "no_topup_row" else tu.split("|")[0])))] += n
print("\n== STOPPED-AND-HELD, top-up outcome by period ==")
for k in sorted(agg): print(f"  {agg[k]:4d}  {k}")
src = collections.Counter()
for (per, bucket, mk, tu), n in stop_cnt.items():
    if "sent=True" in tu: src[(per, tu.split("|")[1], tu.split("|")[2])] += n
print("\n== STOPPED-AND-HELD taker IOC actually sent: by period, topup_source, chase_arm ==")
for k in sorted(src): print(f"  {src[k]:4d}  {k}")
print("\n== OTHER (non-stop) flatten_only names: (period, top-up terminal|source) -> count ==")
for k in sorted(other_cnt): print(f"  {other_cnt[k]:5d}  {k}")

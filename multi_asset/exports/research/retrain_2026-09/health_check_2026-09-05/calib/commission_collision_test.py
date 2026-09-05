"""Test: does the venue COMMISSION in daily_nav equal the log commission of OPENING fills only?
Hypothesis: broker income pagination dedupes on tranId; a closing fill's COMMISSION and REALIZED_PNL rows share a tranId -> one dropped."""
import json, os, calendar, time, collections
import numpy as np
PL=os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
days=[d for d in sorted(os.listdir(PL)) if d.isdigit() and "20260825"<=d<="20260905"]
def jl(d,n):
    p=f"{PL}/{d}/{n}.jsonl"; return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
A=[r for d in days for r in jl(d,"anchors")]; RB=[r for d in days for r in jl(d,"position_readback")]; F=[r for d in days for r in jl(d,"fills")]; NAV=[r for d in days for r in jl(d,"daily_nav")]
byid={}
for r in F:
    if r["trade_id"] not in byid or r.get("supersedes_trade_id") is not None: byid[r["trade_id"]]=r
FD=sorted(byid.values(), key=lambda r: float(r["fill_ts"]))
# post-anchor readback qty per (actual anchor_ts, symbol); also the flatten readback (all zero) at 08-26 12:49Z
pos=collections.defaultdict(dict)
for r in RB: pos[float(r["anchor_ts"])][r["symbol"]]=float(r["venue_position_qty"])
snaps=sorted((float(r["anchor_ts"]), r["rebalance_id"]) for r in A)
# for each fill: pre-anchor position = readback of the previous anchor (by actual ts), then walk fills of this anchor in time order
prev_of={}
for i,(at,rid) in enumerate(snaps): prev_of[rid]=snaps[i-1][0] if i>0 else None
# flatten at 08-26 12:49Z zeroed everything before the 16Z (halted) and 20Z anchors: the 20Z anchor's prev = 16Z readback (empty book) -> qty 0. handled since pos[16Z] has no rows -> default 0
running={}   # (rid, sym) -> running qty within the anchor
cls=[]
for r in FD:
    rid=r["rebalance_id"]; s=r["symbol"]; pa=prev_of.get(rid)
    if (rid,s) not in running: running[(rid,s)] = pos.get(pa,{}).get(s,0.0) if pa is not None else 0.0
    q=running[(rid,s)]; px=float(r["fill_px"]); dq=float(r["fill_notional"])/px*(1 if r["side"]=="buy" else -1)
    reducing = (q*dq<0)
    running[(rid,s)]=q+dq
    cls.append((float(r["fill_ts"]), reducing, float(r["commission"]), r["order_type"]))
print("fills classified:", len(cls), "reducing:", sum(1 for c in cls if c[1]), "opening:", sum(1 for c in cls if not c[1]))
last={}
for n in NAV: last[n["day"]]=n
print("day | venue COMMISSION (BNB) | log all BNB | log opening-only BNB | log reducing-only BNB | venue/all | venue/opening")
tot=collections.Counter()
for D,n in sorted(last.items()):
    if D<"20260826": continue
    d00=calendar.timegm(time.strptime(D,"%Y%m%d")); t1=float(n["nav_ts"])
    fs=[c for c in cls if d00<=c[0]<=t1]
    a=sum(c[2] for c in fs); o=sum(c[2] for c in fs if not c[1]); rd=sum(c[2] for c in fs if c[1])
    v=-float((n.get("realised_by_type") or {}).get("COMMISSION") or 0)
    tot["v"]+=v; tot["a"]+=a; tot["o"]+=o
    print(f"{D} | {v:.6f} | {a:.6f} | {o:.6f} | {rd:.6f} | {v/a if a else float('nan'):.3f} | {v/o if o else float('nan'):.3f}")
print(f"TOTAL venue {tot['v']:.6f} vs log all {tot['a']:.6f} (ratio {tot['v']/tot['a']:.3f}) vs opening-only {tot['o']:.6f} (ratio {tot['v']/tot['o']:.3f})")

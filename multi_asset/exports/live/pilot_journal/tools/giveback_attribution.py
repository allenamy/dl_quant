#!/usr/bin/env python3
"""Read-only live attribution: positions (post-anchor readback) × mid change to next anchor; long/short split, market factor, top names.
Usage: giveback_attribution.py [start_anchor_ts]   (default 1787356800 = 2026-08-18 00Z)"""
import json, glob, collections, statistics as st, sys
from datetime import datetime, timezone
L="/Users/haosiyu/dl_quant_live/state/live"; START=int(sys.argv[1]) if len(sys.argv)>1 else 1787356800
def utc(t): return datetime.fromtimestamp(float(t), tz=timezone.utc).strftime("%m-%d %HZ")
anch=[]
for p in sorted(glob.glob(L+"/pilot_log/2026*/anchors.jsonl")):
    for l in open(p):
        r=json.loads(l); A=int(round(float(r["anchor_ts"])/14400)*14400)
        mv=r.get("mid_at_anchor_vector"); mv=json.loads(mv) if isinstance(mv,str) else mv
        if mv and A>=START: anch.append((A, mv))
anch=sorted({a[0]:a for a in anch}.values(), key=lambda x:x[0]); AM=dict(anch)
pos=collections.defaultdict(dict)
for p in sorted(glob.glob(L+"/pilot_log/2026*/position_readback.jsonl")):
    for l in open(p):
        r=json.loads(l); A=int(round(float(r["anchor_ts"])/14400)*14400); pos[A][r["symbol"]]=float(r["venue_position_notional"])
rows=[]
for i in range(len(anch)-1):
    A,m0=anch[i]; B,m1=anch[i+1]
    if B-A!=14400 or A not in pos: continue
    P=pos[A]; g=sum(abs(v) for v in P.values())
    if g<1000: continue
    rets={s:(m1[s]/m0[s]-1) for s in m0 if s in m1 and m0[s] and m1[s]}
    pnl={s:P[s]*rets[s] for s in P if s in rets}
    if not pnl: continue
    tot=sum(pnl.values()); lo=sum(v for s,v in pnl.items() if P[s]>0); sh=tot-lo
    alt=[rets[s] for s in rets if s!="BTCUSDT"]; altew=sum(alt)/len(alt); disp=(sum((x-altew)**2 for x in alt)/len(alt))**0.5; btc=rets.get("BTCUSDT",float('nan'))
    top5=sum(sorted(pnl.values())[:5]); rows.append((A,tot,lo,sh,g,altew,btc,disp,top5,sorted(pnl.items(), key=lambda kv: kv[1])[:3]))
tots=[r[1]/r[4]*1e4 for r in rows]
print(f"period {utc(rows[0][0])} → {utc(rows[-1][0])}: n={len(rows)}; bps/gross mean {st.mean(tots):+.1f} sd {st.pstdev(tots):.1f} min {min(tots):+.1f} max {max(tots):+.1f} sum {sum(tots):+.0f}; long {sum(r[2]/r[4]*1e4 for r in rows):+.0f} short {sum(r[3]/r[4]*1e4 for r in rows):+.0f}")
print("anchor | bps | long | short | BTC | altEW | disp | top5 | worst names")
for A,tot,lo,sh,g,altew,btc,disp,top5,w in rows:
    print(f"{utc(A)} {tot/g*1e4:+6.1f} | {lo/g*1e4:+6.1f} | {sh/g*1e4:+6.1f} | {100*btc:+5.2f}% | {100*altew:+5.2f}% | {100*disp:4.2f}% | {top5/g*1e4:+6.1f} | " + ", ".join(f"{s}:{v:+.0f}({'L' if pos[A][s]>0 else 'S'},{100*(AM[A+14400][s]/AM[A][s]-1):+.1f}%)" for s,v in w))
big=[t for t in tots if abs(t)>=40]; print(f"|P&L|>=40 bps anchors: {len(big)}/{len(tots)} sum {sum(big):+.0f}; others {sum(tots)-sum(big):+.0f}")
w3=[(sum(rows[i+k][1]/rows[i+k][4]*1e4 for k in range(3)), utc(rows[i][0])) for i in range(len(rows)-2)]; print("worst 3-anchor:", sorted(w3)[:3], "best:", sorted(w3, reverse=True)[:3])
agg=collections.defaultdict(float)
for A,tot,lo,sh,g,altew,btc,disp,top5,w in rows:
    for s,v in pos[A].items():
        m0=AM[A]; m1=AM.get(A+14400,{})
        if s in m0 and s in m1 and m0[s] and m1[s]: agg[s]+=v*(m1[s]/m0[s]-1)
srt=sorted(agg.items(), key=lambda kv: kv[1]); print("worst names:", [(s,round(v)) for s,v in srt[:10]]); print("best names:", [(s,round(v)) for s,v in srt[-10:][::-1]])

#!/usr/bin/env python3
"""TRACK B step 2b: split realised traded notional into (i) genuine target change, (ii) price-drift
re-balancing, (iii) leverage/NAV rescale.  The replay holds WEIGHTS and charges nothing for keeping
them constant while prices move; the live book holds QUANTITIES and must trade to keep weights. READ-ONLY."""
import json, os
from collections import defaultdict
import numpy as np
LOG="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
COMBO=1787716800.0
days=sorted(d for d in os.listdir(LOG) if d.isdigit())
mid={}
for d in days:
    p=f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); ts=r.get("anchor_ts")
        if ts is None: continue
        m=r.get("mid_at_anchor_vector"); m=json.loads(m) if isinstance(m,str) else (m or {})
        mid[ts]=m
Q=defaultdict(dict); N=defaultdict(dict)
for d in days:
    p=f"{LOG}/{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); Q[r["anchor_ts"]][r["symbol"]]=float(r.get("venue_position_qty") or 0.0); N[r["anchor_ts"]][r["symbol"]]=float(r.get("venue_position_notional") or 0.0)
ats=sorted(Q)
rows=[]
for k in range(1,len(ats)):
    t0,t1=ats[k-1],ats[k]
    if t1-t0>20000: continue          # only consecutive 4h anchors (gaps break the comparison)
    m1=mid.get(t1,{})
    if not m1: continue
    names=set(Q[t0])|set(Q[t1])
    G1=sum(abs(v) for v in N[t1].values()); G0=sum(abs(v) for v in N[t0].values())
    if G1<=0 or G0<=0: continue
    dtrade=0.0; ddrift=0.0; dnaive=0.0; cov=0; miss=0
    for s in names:
        q0=Q[t0].get(s,0.0); n0=N[t0].get(s,0.0); n1=N[t1].get(s,0.0)
        px=m1.get(s)
        if px is None:
            if q0!=0.0 or n1!=0.0: miss+=1
            dnaive+=abs(n1-n0); continue
        held=q0*px                      # value at t1 of the quantity we held at t0 (no trade)
        dtrade+=abs(n1-held); ddrift+=abs(held-n0); dnaive+=abs(n1-n0); cov+=1
    rows.append(dict(ts=t1,G=G1,dtrade=dtrade,ddrift=ddrift,dnaive=dnaive,
                     lev=abs(G1-G0)/G0, miss=miss))
def rep(lab,sel):
    R=[r for r in rows if sel(r)]
    if not R: return
    S=lambda k: sum(r[k] for r in R); G=S("G"); n=len(R)
    print(f"\n===== {lab}  n={n} anchor pairs, mean gross {G/n:,.0f}, names missing a mid/anchor {sum(r['miss'] for r in R)} =====")
    print(f"  ACTUAL TRADED (|pos_t - qty_(t-1)*mid_t|) / gross : {S('dtrade')/G*100:7.3f} %/anchor")
    print(f"  pure PRICE DRIFT (|qty_(t-1)*Δmid|)      / gross : {S('ddrift')/G*100:7.3f} %/anchor   <- costs nothing, the replay ignores it")
    print(f"  naive |Δnotional|                        / gross : {S('dnaive')/G*100:7.3f} %/anchor   <- conflates the two")
    print(f"  gross rescale |ΔG|/G (NAV / leverage)            : {np.mean([r['lev'] for r in R])*100:7.3f} %/anchor")
rep("ALL",lambda r:True); rep("COMBO ERA",lambda r:r["ts"]>=COMBO); rep("PRE-COMBO",lambda r:r["ts"]<COMBO)

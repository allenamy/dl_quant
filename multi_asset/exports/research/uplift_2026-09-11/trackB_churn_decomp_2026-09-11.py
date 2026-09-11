#!/usr/bin/env python3
"""TRACK B step 2: mechanically decompose intended vs realised trading. READ-ONLY.
Answers: of the notional the executor asks for each anchor, how much is genuine position change
and how much is re-issued intent on the SAME target (churn)?
Also computes execution slippage vs the ANCHOR MID -- the reference price the replay marks at --
which is the caliber that says whether the replay's COST_B over- or under-charges."""
import json, os
from collections import defaultdict
import numpy as np
LOG = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
COMBO_START = 1787716800.0
days = sorted(d for d in os.listdir(LOG) if d.isdigit())

mid_at = {}; 
for d in days:
    p=f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); ts=r.get("anchor_ts")
        if ts is None: continue
        m=r.get("mid_at_anchor_vector")
        if isinstance(m,str): m=json.loads(m)
        mid_at[ts]=m or {}
POS = defaultdict(dict)
for d in days:
    p=f"{LOG}/{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); POS[r["anchor_ts"]][r["symbol"]]=float(r.get("venue_position_notional") or 0.0)
ats=sorted(POS)

# orders by attempt
ORD=defaultdict(lambda: defaultdict(lambda: dict(intent=0.0,filled=0.0,n=0)))
PREVW=defaultdict(dict); TGTW=defaultdict(dict)
for d in days:
    p=f"{LOG}/{d}/orders.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); ts=r.get("anchor_ts"); 
        if ts is None: continue
        ai=int(r.get("attempt_idx") or 1)
        e=ORD[ts][ai]; e["intent"]+=abs(float(r.get("intended_notional") or 0.0)); e["filled"]+=abs(float(r.get("filled_notional") or 0.0)); e["n"]+=1
        if ai==1:
            if r.get("target_w") is not None: TGTW[ts][r["symbol"]]=float(r["target_w"])
            if r.get("prev_w") is not None: PREVW[ts][r["symbol"]]=float(r["prev_w"])

# fills -> slippage vs anchor mid (deduped)
F={}
for d in days:
    p=f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); k=(r["symbol"],r["trade_id"])
        if k not in F or (r.get("mid_at_fill_plus_60s") is not None and F[k].get("mid_at_fill_plus_60s") is None): F[k]=r
SL=defaultdict(lambda: dict(mk_num=0.0,mk_den=0.0,tk_num=0.0,tk_den=0.0,fee=0.0,notional=0.0))
for r in F.values():
    ts=r.get("anchor_ts"); 
    if ts is None: continue
    am=mid_at.get(ts,{}).get(r["symbol"])
    if not am or am<=0: continue
    px=float(r.get("fill_px") or 0.0); nz=abs(float(r.get("fill_notional") or 0.0))
    if px<=0 or nz<=0: continue
    sgn = 1.0 if r.get("side")=="buy" else -1.0
    slip = sgn*(px-am)/am            # +ve = we paid WORSE than the anchor mid = COST
    mk = bool(r.get("venue_maker_flag")) if r.get("venue_maker_flag") is not None else (r.get("order_type")=="maker")
    e=SL[ts]
    if mk: e["mk_num"]+=slip*nz; e["mk_den"]+=nz
    else:  e["tk_num"]+=slip*nz; e["tk_den"]+=nz
    c=float(r.get("commission") or 0.0)
    e["fee"]+= c if (r.get("commission_asset") or "USDT")=="USDT" else c*(mid_at.get(ts,{}).get("BNBUSDT") or 0.0)
    e["notional"]+=nz

rows=[]
for k,ts in enumerate(ats):
    if k==0: continue
    prev=POS[ats[k-1]]; cur=POS[ts]
    names=set(prev)|set(cur)
    dpos=sum(abs(cur.get(s,0.0)-prev.get(s,0.0)) for s in names)
    G=sum(abs(v) for v in cur.values())
    if G<=0: continue
    o=ORD.get(ts,{})
    i1=o.get(1,{}).get("intent",0.0); i2=sum(v["intent"] for a,v in o.items() if a>=2)
    f1=o.get(1,{}).get("filled",0.0); f2=sum(v["filled"] for a,v in o.items() if a>=2)
    e=SL.get(ts,{})
    rows.append(dict(ts=ts,gross=G,dpos=dpos,intent1=i1,intent2p=i2,fill1=f1,fill2p=f2,
                     mk_num=e.get("mk_num",0.0),mk_den=e.get("mk_den",0.0),tk_num=e.get("tk_num",0.0),tk_den=e.get("tk_den",0.0),
                     fee=e.get("fee",0.0),notional=e.get("notional",0.0)))
json.dump(rows,open(f"{OUT}/trackB_churn_rows.json","w"),indent=1)

def rep(lab,sel):
    R=[r for r in rows if sel(r)]
    if not R: return
    G=sum(r["gross"] for r in R); n=len(R)
    S=lambda k: sum(r[k] for r in R)
    print(f"\n===== {lab}  n={n} anchors, mean gross {G/n:,.0f} =====")
    print(f"  GENUINE position change |Δpos| / gross      : {S('dpos')/G*100:7.3f} %/anchor   <- the book actually moved this much")
    print(f"  intent, attempt 1        / gross            : {S('intent1')/G*100:7.3f} %/anchor")
    print(f"  intent, attempts >=2     / gross            : {S('intent2p')/G*100:7.3f} %/anchor   <- re-issued on the SAME target = churn")
    print(f"  filled,  attempt 1       / gross            : {S('fill1')/G*100:7.3f} %/anchor")
    print(f"  filled,  attempts >=2    / gross            : {S('fill2p')/G*100:7.3f} %/anchor")
    print(f"  total filled             / gross            : {(S('fill1')+S('fill2p'))/G*100:7.3f} %/anchor")
    print(f"  ratio  total intent / genuine position move : {(S('intent1')+S('intent2p'))/max(S('dpos'),1e-9):7.3f} x")
    print(f"  ratio  total filled / genuine position move : {(S('fill1')+S('fill2p'))/max(S('dpos'),1e-9):7.3f} x")
    mkb=S('mk_num')/max(S('mk_den'),1e-9)*1e4; tkb=S('tk_num')/max(S('tk_den'),1e-9)*1e4
    tot=(S('mk_num')+S('tk_num'))/max(S('mk_den')+S('tk_den'),1e-9)*1e4
    feeb=S('fee')/max(S('notional'),1e-9)*1e4
    print(f"  -- execution vs the ANCHOR MID (the replay's reference price); + = worse than mid = COST --")
    print(f"     maker slippage {mkb:+7.4f} bps  (share {S('mk_den')/max(S('mk_den')+S('tk_den'),1e-9)*100:.1f}%)   taker slippage {tkb:+7.4f} bps")
    print(f"     blended slippage {tot:+7.4f} bps   + fees {feeb:+7.4f} bps  =  ALL-IN {tot+feeb:+7.4f} bps per unit traded notional")
rep("ALL",lambda r:True)
rep("COMBO ERA",lambda r:r["ts"]>=COMBO_START)
rep("PRE-COMBO",lambda r:r["ts"]<COMBO_START)

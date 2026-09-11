import json,os
from collections import defaultdict
import numpy as np
LOG="/Users/haosiyu/dl_quant_live/state/live/pilot_log"; COMBO=1787716800.0
days=sorted(d for d in os.listdir(LOG) if d.isdigit())
anch={}
for d in days:
    p=f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); ts=r.get("anchor_ts")
        if ts is None: continue
        m=r.get("mid_at_anchor_vector")
        if isinstance(m,str): m=json.loads(m)
        anch[ts]=m or {}
ats=sorted(anch)
bnbc=[t for t in ats if anch[t].get("BNBUSDT")]
def bnb(ts):
    if not bnbc: return None
    t=min(bnbc,key=lambda t:abs(t-ts)); return anch[t]["BNBUSDT"]
F={}
for d in days:
    p=f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); k=(r["symbol"],r["trade_id"]); c=F.get(k)
        if c is None: F[k]=r; continue
        if r.get("mid_at_fill_plus_60s") is not None and c.get("mid_at_fill_plus_60s") is None: F[k]=r
pbg=defaultdict(float)
for d in days:
    p=f"{LOG}/{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p): 
        r=json.loads(ln); pbg[r["anchor_ts"]]+=abs(float(r.get("venue_position_notional") or 0.0))
bnbv={t:bnb(t) for t in ats}
print("BNB mid sample:",[round(bnbv[t],1) for t in ats[:3] if bnbv[t]])
for lab,sel in (("COMBO era",lambda t:t>=COMBO),):
    fee=0.;nz=0.;mkn=0.;tkn=0.;mkf=0.;tkf=0.;ancs=set()
    smk=0.;smkw=0.;stk=0.;stkw=0.
    for r in F.values():
        ts=r.get("anchor_ts")
        if ts is None or not sel(ts): continue
        ancs.add(ts)
        c=float(r.get("commission") or 0)
        if (r.get("commission_asset") or "USDT")=="BNB": c*= (bnbv.get(ts) or bnb(ts) or 0.0)
        n=abs(float(r.get("fill_notional") or 0)); mk=bool(r.get("venue_maker_flag"))
        fee+=c; nz+=n
        if mk: mkn+=n; mkf+=c
        else: tkn+=n; tkf+=c
        px=float(r.get("fill_px") or 0); sg=1.0 if r.get("side")=="buy" else -1.0
        am=anch.get(ts,{}).get(r["symbol"])
        if am and px>0:
            sl=sg*(px-float(am))/float(am)
            if mk: smk+=sl*n; smkw+=n
            else: stk+=sl*n; stkw+=n
    G=sum(pbg[t] for t in ancs if t in pbg)
    print(f"\n{lab}: anchors {len(ancs)} gross {G:,.0f} traded {nz:,.0f}")
    print(f"  fee/unit (BNB converted) {fee/nz*1e4:+.4f} bps   maker {mkf/mkn*1e4:+.4f} taker {tkf/tkn*1e4:+.4f}  maker share(notional) {mkn/nz*100:.2f}%")
    print(f"  fee bps of gross/anchor  {fee/G*1e4:+.4f}   (candidate: +0.2366)")
    blend=(smk+stk)/(smkw+stkw)*1e4
    print(f"  anchor-mid slip blended  {blend:+.4f} bps/unit (candidate -2.113)")
    print(f"  CASH = fee+slip          {fee/nz*1e4+blend:+.4f} bps/unit  (candidate +0.286)  => {(fee/nz*1e4+blend)*nz/G:+.4f} bps of gross/anchor (candidate +0.0282)")

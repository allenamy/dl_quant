"""INDEPENDENT recompute of TRACK B candidate B4's live cost numbers. READ-ONLY."""
import json,os,glob
from collections import defaultdict
import numpy as np
LOG="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
COMBO=1787716800.0
days=sorted(d for d in os.listdir(LOG) if d.isdigit())
# anchor mids
anch={}
for d in days:
    p=f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); ts=r.get("anchor_ts")
        if ts is None: continue
        mid=r.get("mid_at_anchor_vector")
        if isinstance(mid,str): mid=json.loads(mid)
        anch[ts]=mid or {}
# fills dedupe
raw=0; F={}; same=0; diff=0
for d in days:
    p=f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); raw+=1
        k=(r["symbol"],r["trade_id"]); c=F.get(k)
        if c is None: F[k]=r; continue
        s=(c.get("fill_notional")==r.get("fill_notional") and c.get("commission")==r.get("commission") and c.get("fill_px")==r.get("fill_px"))
        same+=s; diff+=(not s)
        if r.get("mid_at_fill_plus_60s") is not None and c.get("mid_at_fill_plus_60s") is None: F[k]=r
print(f"fills rows {raw} -> dedup {len(F)} (dropped {raw-len(F)}: identical {same}, differing {diff})")
# gross from position_readback
pbg=defaultdict(float)
for d in days:
    p=f"{LOG}/{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); pbg[r["anchor_ts"]]+=abs(float(r.get("venue_position_notional") or 0.0))
for lab,sel in (("ALL",lambda t:True),("COMBO era",lambda t:t>=COMBO)):
    fee=0.;nz=0.;mkn=0.;tkn=0.;mkf=0.;tkf=0.
    slip_mk=0.;slip_mk_w=0.;slip_tk=0.;slip_tk_w=0.;nomid=0
    mo=0.;mow=0.
    ancs=set()
    for r in F.values():
        ts=r.get("anchor_ts")
        if ts is None or not sel(ts): continue
        ancs.add(ts)
        c=float(r.get("commission") or 0.0); n=abs(float(r.get("fill_notional") or 0.0))
        mk=bool(r.get("venue_maker_flag"))
        fee+=c; nz+=n
        if mk: mkn+=n; mkf+=c
        else: tkn+=n; tkf+=c
        px=float(r.get("fill_px") or 0.0); sgn=1.0 if r.get("side")=="buy" else -1.0
        am=anch.get(ts,{}).get(r["symbol"])
        if am and px>0:
            # cost sign: buying above the anchor mid costs; selling below costs
            sl=sgn*(px-float(am))/float(am)
            if mk: slip_mk+=sl*n; slip_mk_w+=n
            else: slip_tk+=sl*n; slip_tk_w+=n
        else: nomid+=n
        m60=r.get("mid_at_fill_plus_60s")
        if m60 is not None and px>0:
            mo+=sgn*(float(m60)-px)/px*n; mow+=n
    G=sum(pbg[t] for t in ancs if t in pbg)
    print(f"\n== {lab}  n_anchors={len(ancs)}  sum_gross={G:,.0f}  traded={nz:,.0f} ({nz/G*100:.3f}% of gross/anchor) ==")
    print(f"  fee/unit traded      {fee/nz*1e4:+8.4f} bps   (maker {mkf/mkn*1e4:+.4f}  taker {tkf/tkn*1e4:+.4f}  maker share {mkn/nz*100:.2f}%)")
    print(f"  fee bps of gross/anc {fee/G*1e4:+8.4f}")
    print(f"  slip vs ANCHOR MID   maker {slip_mk/slip_mk_w*1e4:+8.4f}  taker {slip_tk/slip_tk_w*1e4:+8.4f}  blended {(slip_mk+slip_tk)/(slip_mk_w+slip_tk_w)*1e4:+8.4f} bps/unit  [mid coverage {(slip_mk_w+slip_tk_w)/nz*100:.1f}%]")
    print(f"  markout60/unit       {mo/mow*1e4:+8.4f} bps (+ = moved our way)  coverage {mow/nz*100:.1f}%")
    cash=(fee/nz*1e4)+((slip_mk+slip_tk)/(slip_mk_w+slip_tk_w)*1e4)
    print(f"  CASH (fee + anchor-mid slip)  {cash:+8.4f} bps/unit traded  =  {cash*nz/G:+8.4f} bps of gross/anchor")
    print(f"  fee + (-markout60)            {(fee/nz*1e4)-(mo/mow*1e4):+8.4f} bps/unit traded")

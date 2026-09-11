#!/usr/bin/env python3
"""TRACK B step 1 (v2): realized cost per anchor. READ-ONLY on live tree.
Dedupe rule: (symbol,trade_id); keep the BACKFILLED row (it supersedes and carries mid_at_fill_plus_60s)."""
import json,os,datetime as dt
from collections import defaultdict
import numpy as np
LOG="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
days=sorted(d for d in os.listdir(LOG) if d.isdigit())

anch={}
for d in days:
    p=f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); ts=r.get("anchor_ts")
        if ts is None: continue
        mid=r.get("mid_at_anchor_vector")
        if isinstance(mid,str): mid=json.loads(mid)
        anch[ts]=dict(day=d,G=r.get("realized_gross") or r.get("target_gross"),
                      Gt=r.get("target_gross"),mid=mid or {},regime=r.get("regime_at_anchor"))
ats=sorted(anch)
def bnb_at(ts):
    cands=[t for t in ats if anch[t]["mid"].get("BNBUSDT")]
    if not cands: return None
    t=min(cands,key=lambda t:abs(t-ts)); return anch[t]["mid"]["BNBUSDT"]

# fills
F=defaultdict(dict)  # day -> key -> row
for d in days:
    p=f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); k=(r["symbol"],r["trade_id"])
        cur=F[d].get(k)
        if cur is None or (r.get("mid_at_fill_plus_60s") is not None and cur.get("mid_at_fill_plus_60s") is None):
            F[d][k]=r
fills=[r for d in F for r in F[d].values()]
print(f"deduped fills: {len(fills)}  (dedupe = (symbol,trade_id), keep backfilled)")
bnbp={}
for ts in ats: bnbp[ts]=bnb_at(ts)
print("BNBUSDT mid used (first/last):",bnbp[ats[0]],bnbp[ats[-1]])

# ---- fee reconciliation vs venue income ledger (last daily_nav row of each day = cumulative since 00:00Z)
print("\n--- FEE RECONCILIATION: fills.jsonl (deduped) vs /fapi/v1/income COMMISSION")
print(f"{'day':10} {'fills_fee_USDT':>15} {'venue_COMMISSION':>17} {'ratio':>7}")
rec=[]
for d in days:
    p=f"{LOG}/{d}/daily_nav.jsonl"
    ven=None
    if os.path.exists(p):
        last=None
        for ln in open(p):
            r=json.loads(ln)
            if r.get("day")==d: last=r
        if last: ven=-(last.get("realised_by_type",{}).get("COMMISSION") or 0.0)
    ff=0.0
    for r in F.get(d,{}).values():
        c=r.get("commission") or 0.0; ca=r.get("commission_asset") or "USDT"
        ts=r.get("anchor_ts")
        px=bnbp.get(ts) or bnbp[ats[-1]]
        ff += c*(px if ca=="BNB" else 1.0) if ca in ("USDT","BNB") else c
    rat = ff/ven if ven else float('nan')
    rec.append((d,ff,ven,rat))
    print(f"{d:10} {ff:15.2f} {(ven if ven is not None else float('nan')):17.2f} {rat:7.3f}")
tf=sum(x[1] for x in rec); tv=sum(x[2] or 0 for x in rec)
print(f"{'TOTAL':10} {tf:15.2f} {tv:17.2f} {tf/tv:7.3f}")
json.dump([{"day":a,"fills_fee":b,"venue_comm":c,"ratio":d_} for a,b,c,d_ in rec],open(f"{OUT}/trackB_fee_recon.json","w"),indent=1)

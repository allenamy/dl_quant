#!/usr/bin/env python3
import json, glob, os, time
import numpy as np
PL="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
# last daily_nav row per day
last={}
for d in sorted(glob.glob(f"{PL}/2026*")):
    p=f"{d}/daily_nav.jsonl"
    if not os.path.exists(p): continue
    for l in open(p):
        r=json.loads(l); last[r["day"]]=r
days=sorted(last)
print("day      nav        prev_nav   flow      equity_delta  ret_flowadj%   FUNDING   REALIZED   COMM")
cum=1.0
for dd in days:
    r=last[dd]
    nav=r["nav"]; pn=r.get("prev_nav"); fl=r.get("external_flow_usdt") or 0.0
    if pn:
        ret=(nav-pn-fl)/pn; cum*= (1+ret)
    else: ret=float('nan')
    bt=r.get("realised_by_type") or {}
    print(f"{dd} {nav:10.1f} {pn if pn else 0:10.1f} {fl:9.1f} {nav-(pn or 0)-fl:12.1f} {ret*100:8.3f}   {bt.get('FUNDING_FEE',0):9.2f} {bt.get('REALIZED_PNL',0):10.2f} {bt.get('COMMISSION',0):8.3f}")
print("cum flow-adj return whole period: %.4f%%"%((cum-1)*100))
c2=1.0
for dd in days:
    if dd<"20260826": continue
    r=last[dd]; pn=r.get("prev_nav"); fl=r.get("external_flow_usdt") or 0.0
    if pn: c2*=1+(r["nav"]-pn-fl)/pn
print("cum flow-adj 08-26..: %.4f%%"%((c2-1)*100))

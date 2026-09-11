#!/usr/bin/env python3
import json, glob, os, collections
import numpy as np
PL="/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
# BNB mid per anchor from anchors.jsonl
bnb={}
for d in sorted(glob.glob(f"{PL}/2026*")):
    p=f"{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for l in open(p):
        r=json.loads(l); mv=r.get("mid_at_anchor_vector")
        if isinstance(mv,str):
            try: mv=json.loads(mv)
            except Exception: mv={}
        if mv and "BNBUSDT" in mv: bnb[float(r["anchor_ts"])]=float(mv["BNBUSDT"])
bts=sorted(bnb)
def bnb_px(t):
    if not bts: return None
    i=min(range(len(bts)), key=lambda k: abs(bts[k]-t)); return bnb[bts[i]]
agg=collections.defaultdict(lambda: {"usdt":0.0,"bnb":0.0,"notional":0.0,"maker_n":0,"n":0})
for d in sorted(glob.glob(f"{PL}/2026*")):
    p=f"{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for l in open(p):
        r=json.loads(l); t=float(r.get("anchor_ts") or 0); A=int(t//14400*14400)
        a=agg[A]; c=float(r.get("commission") or 0.0)
        if r.get("commission_asset")=="BNB": a["bnb"]+=c
        else: a["usdt"]+=c
        a["notional"]+=abs(float(r.get("fill_notional") or 0.0)); a["n"]+=1
        a["maker_n"]+= 1 if r.get("venue_maker_flag") else 0
LIVE={r["grid_anchor"]:r for r in json.load(open(f"{OUT}/live_anchor_table.json"))}
rows=[]
for A,a in sorted(agg.items()):
    px=bnb_px(A+1400) or 0.0
    fee=a["usdt"]+a["bnb"]*px
    g=LIVE.get(A,{}).get("gross")
    rows.append({"A":A,"fee_usdt_total":fee,"fee_usdt_leg":a["usdt"],"fee_bnb_leg_usdt":a["bnb"]*px,
                 "bnb_px":px,"traded_notional":a["notional"],"n_fills":a["n"],"maker_frac":a["maker_n"]/max(a["n"],1),
                 "gross":g,"fee_bps_of_gross": fee/g*1e4 if g else None,
                 "fee_bps_of_traded": fee/a["notional"]*1e4 if a["notional"] else None,
                 "turnover_frac": a["notional"]/g if g else None})
json.dump(rows,open(f"{OUT}/fee_table.json","w"),indent=1)
C=[r for r in rows if r["A"]>=1787716800 and r["gross"]]
def a_(k,s=C): return np.array([x[k] for x in s if x[k] is not None],float)
print("combo era anchors with fees:",len(C))
for k in ("fee_bps_of_gross","fee_bps_of_traded","turnover_frac","maker_frac"):
    v=a_(k); print(f"  {k:20s} mean {v.mean():8.4f} sd {v.std(ddof=1):7.4f} n {len(v)}")
print(f"  combo era total fees USD: {sum(x['fee_usdt_total'] for x in C):.1f} (usdt-leg {sum(x['fee_usdt_leg'] for x in C):.1f}, bnb-leg {sum(x['fee_bnb_leg_usdt'] for x in C):.1f})")
print(f"  combo era traded notional: {sum(x['traded_notional'] for x in C):.0f}")
ALL=[r for r in rows if r["gross"]]
print(f"  whole period fees USD: {sum(x['fee_usdt_total'] for x in ALL):.1f}  traded {sum(x['traded_notional'] for x in ALL):.0f}")

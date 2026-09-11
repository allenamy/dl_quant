import json,os
from collections import defaultdict, Counter
import numpy as np
LOG="/Users/haosiyu/dl_quant_live/state/live/pilot_log"; COMBO=1787716800.0
days=sorted(d for d in os.listdir(LOG) if d.isdigit())
F={}
for d in days:
    p=f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); k=(r["symbol"],r["trade_id"]); c=F.get(k)
        if c is None: F[k]=r; continue
        if r.get("mid_at_fill_plus_60s") is not None and c.get("mid_at_fill_plus_60s") is None: F[k]=r
ca=Counter(r.get("commission_asset") for r in F.values()); print("commission_asset:",ca)
# per-anchor, combo era
A=defaultdict(lambda: dict(fee=0.,nz=0.,mkn=0.,tkn=0.,mkf=0.,tkf=0.))
for r in F.values():
    ts=r.get("anchor_ts")
    if ts is None or ts<COMBO: continue
    a=A[ts]; c=float(r.get("commission") or 0); n=abs(float(r.get("fill_notional") or 0))
    mk=bool(r.get("venue_maker_flag")); a["fee"]+=c; a["nz"]+=n
    if mk: a["mkn"]+=n; a["mkf"]+=c
    else: a["tkn"]+=n; a["tkf"]+=c
print("n anchors with fills, combo era:",len(A))
fe=sum(a["fee"] for a in A.values()); tn=sum(a["nz"] for a in A.values())
print("NOTIONAL-WEIGHTED  fee/unit %.4f bps | maker share %.2f%% | maker %.4f taker %.4f"%(
  fe/tn*1e4, sum(a["mkn"] for a in A.values())/tn*100,
  sum(a["mkf"] for a in A.values())/sum(a["mkn"] for a in A.values())*1e4,
  sum(a["tkf"] for a in A.values())/sum(a["tkn"] for a in A.values())*1e4))
mks=[a["mkn"]/a["nz"] for a in A.values() if a["nz"]>0]
mkb=[a["mkf"]/a["mkn"]*1e4 for a in A.values() if a["mkn"]>0]
tkb=[a["tkf"]/a["tkn"]*1e4 for a in A.values() if a["tkn"]>0]
print("UNWEIGHTED MEAN OF PER-ANCHOR RATIOS  maker share %.2f%% | maker %.4f taker %.4f  <-- the candidate's 85.5 / 1.852 / 4.625"%(
  np.mean(mks)*100,np.mean(mkb),np.mean(tkb)))
# blended unit cost using the candidate's own mix vs the weighted mix
for lab,share,mkslip,tkslip in (("candidate mix 85.5%",0.855,-4.8816,12.0012),("weighted mix 67.98%",0.6798,-4.8816,12.0012)):
    slip=share*mkslip+(1-share)*tkslip
    print(f"  {lab}: blended anchor-mid slip {slip:+.4f} bps/unit")

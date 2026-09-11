#!/usr/bin/env python3
"""INFRA-1 step 3: liquidity structure of the live cost, finer than 3 tiers + impact probe."""
import json, numpy as np
from collections import defaultdict
BASE="/workspace/uplift_2026-09-11/infra1_cost"
R=json.load(open(f"{BASE}/fill_cost_rows.json")); rows=R["rows"]
P=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
M=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
psym=[str(s) for s in P["symbols"]]; sidx={s:i for i,s in enumerate(psym)}
E=M["E_ts"].astype(np.int64); erow={int(t):i for i,t in enumerate(E)}
QV=np.expm1(np.clip(M["qvk"],0,30))*48.0
LAST=np.full(len(psym),np.nan)
for c in range(len(psym)):
    v=QV[-42:,c]; f=v[np.isfinite(v)]
    if len(f): LAST[c]=float(np.median(f))
g4=lambda ts:int(np.floor(ts/14400.0)*14400)
for r in rows:
    k=g4(r["anchor_ts"]); c=sidx.get(r["symbol"]); j=erow.get(k)
    r["qv4h"]=None
    if c is None: continue
    if j is not None and np.isfinite(QV[j,c]): r["qv4h"]=float(QV[j,c]); r["qsrc"]="panel"
    elif np.isfinite(LAST[c]): r["qv4h"]=float(LAST[c]); r["qsrc"]="cf"
use=[r for r in rows if r["qv4h"] is not None and r["qv4h"]>0]
print("usable rows",len(use))
lq=np.array([np.log10(r["qv4h"]) for r in use])
edges=np.quantile(lq,np.linspace(0,1,11))
print("log10(qv4h) deciles:",np.round(edges,2))
print("\n%-22s %7s %10s %10s %8s %8s %8s %8s %8s"%("bucket log10 qv4h","rows","intentA1","filled","fill%","mk_shr","spread","fee_mk","fee_tk"))
B=defaultdict(lambda: defaultdict(float))
for r,l in zip(use,lq):
    b=min(int(np.searchsorted(edges,l,side="right"))-1,9); b=max(b,0)
    d=B[b]
    d["n"]+=1; d["i1"]+=r["intent_a1"]
    for tag in ("mk","tk"):
        d[tag+"nz"]+=r[tag+"_nz"]; d[tag+"fee"]+=r[tag+"_fee"]
        if r[tag+"_slip_cov"]>0: d[tag+"sw"]+=r[tag+"_slip_bps"]*r[tag+"_slip_cov"]; d[tag+"sn"]+=r[tag+"_slip_cov"]
    if r.get("spread_bps") is not None and r["intent_a1"]>0: d["spw"]+=r["spread_bps"]*r["intent_a1"]; d["spn"]+=r["intent_a1"]
    if r["intent_a1"]>0: d["pw"]+=(r["intent_a1"]/r["qv4h"])*r["intent_a1"]
    d["lqw"]+=l*max(r["intent_a1"],0)
rowsout=[]
for b in range(10):
    d=B[b]; fl=d["mknz"]+d["tknz"]
    sp=d["spw"]/d["spn"] if d["spn"]>0 else float("nan")
    rec=dict(bucket=b, lo=float(edges[b]), hi=float(edges[b+1]), n=int(d["n"]), intent=d["i1"], filled=fl,
             fill=fl/d["i1"] if d["i1"]>0 else float("nan"),
             mkshare=d["mknz"]/fl if fl>0 else float("nan"), spread=sp,
             fee_mk=d["mkfee"]/d["mknz"]*1e4 if d["mknz"]>0 else float("nan"),
             fee_tk=d["tkfee"]/d["tknz"]*1e4 if d["tknz"]>0 else float("nan"),
             slip_mk=d["mksw"]/d["mksn"] if d["mksn"]>0 else float("nan"),
             slip_tk=d["tksw"]/d["tksn"] if d["tksn"]>0 else float("nan"),
             part=d["pw"]/d["i1"] if d["i1"]>0 else float("nan"),
             lqbar=d["lqw"]/d["i1"] if d["i1"]>0 else float("nan"))
    rowsout.append(rec)
    print("%-22s %7d %10.0f %10.0f %8.3f %8.3f %8.3f %8.4f %8.4f  part %.2e slip_mk %7.2f slip_tk %7.2f"%(
        "[%.2f,%.2f)"%(rec["lo"],rec["hi"]),rec["n"],rec["intent"],rec["filled"],rec["fill"],rec["mkshare"],rec["spread"],rec["fee_mk"],rec["fee_tk"],rec["part"],rec["slip_mk"],rec["slip_tk"]))
x=np.array([r["lqbar"] for r in rowsout]); y=np.array([r["spread"] for r in rowsout]); w=np.array([r["intent"] for r in rowsout])
ok=np.isfinite(x)&np.isfinite(y)
A=np.vstack([np.ones(ok.sum()),x[ok]]).T
b,_,_,_=np.linalg.lstsq(A*np.sqrt(w[ok])[:,None],y[ok]*np.sqrt(w[ok]),rcond=None)
print("\nWLS  spread_bps = %.4f %+.4f * log10(qv4h)   (intent-weighted over 10 buckets)"%(b[0],b[1]))
xs=np.array([r["lqbar"] for r in rowsout]); ys=np.array([r["mkshare"] for r in rowsout])
b2,_,_,_=np.linalg.lstsq(np.vstack([np.ones(len(xs)),xs]).T*np.sqrt(w)[:,None],ys*np.sqrt(w),rcond=None)
print("WLS  maker_share = %.4f %+.4f * log10(qv4h)"%(b2[0],b2[1]))
json.dump(rowsout,open(f"{BASE}/decile_stats.json","w"),indent=1)

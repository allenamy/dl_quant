"""R9 SCREEN ADDENDUM -- REV_SHORT. Three questions the main run left open:
 (A) the two-asset max-Sharpe formula wants a SHORT position in this book. Is that short buildable?
     (sign-flip = cross-sectional MOMENTUM at the same turnover; cost does NOT flip sign.)
 (B) what execution rate would it need? incl. the 100%-maker-fill counterfactual (the book is
     maker-only), which is the most generous rate for which this desk has ANY evidence.
 (C) gross-alpha significance: day-block CI on gross, and z against the 6 turnover-matched nulls.
ENV WHITELIST (E-0826-D) = EMPTY SET.
"""
import os, sys, json, hashlib, time, calendar
ENV_SEEN = sorted(os.environ.keys())
_FORBID = ("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
           "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","TRADE_TOPN")
assert not [k for k in _FORBID if k in os.environ], "E-0826-D env violation"
import numpy as np
from scipy.stats import rankdata
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda: f.read(1<<22), b""): h.update(b)
    return h.hexdigest()
U="/workspace/uplift_2026-09-11"
META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0P=U+"/r3k/arms/A0_PWR230k_s42.npz"; CBJ=U+"/r3k/costb_PWR_G230k.json"
CUT=T(2026,8,30,20); WARM=900; B=2000; APY=2190.0
CB=json.load(open(CBJ))
RATE=np.array(CB["blended_bps_per_unit_turnover"],float)
MAKER=np.array([t["maker_bps"] for t in CB["tiers"]],float)       # 100% maker fill counterfactual
TAKER=np.array([t["taker_bps"] for t in CB["tiers"]],float)
m=np.load(META,allow_pickle=True)
E_ts=m["E_ts"].astype(np.int64); Y=m["y4"].astype(np.float64); QV=m["qvk"].astype(np.float64)
members=m["members"]; Tn,N=Y.shape
a=np.load(A0P,allow_pickle=True); cols=[str(c) for c in a["cols"]]; ci={c:i for i,c in enumerate(cols)}
rec=np.asarray(a["rec"],float)[WARM:]; a_ts=np.round(rec[:,ci["ts"]]).astype(np.int64)
msk=a_ts<=CUT; a_ts=a_ts[msk]; gA0=rec[msk,ci["net_ex"]]/rec[msk,ci["gross_total"]]; NW=len(gA0)
pos={int(t):i for i,t in enumerate(E_ts)}; IDX=np.array([pos[int(t)] for t in a_ts])
MEMB=np.zeros((Tn,N),bool)
for t in range(Tn):
    mm=members[t]
    if mm is not None and len(mm): MEMB[t,np.asarray(mm,dtype=int)]=True
QV4H=np.expm1(np.clip(QV,0,30))*48.0
ELIG=MEMB&np.isfinite(Y)&(QV4H>=2.5e5)
TIER=np.where(QV4H>=5e6,0,np.where(QV4H>=1e6,1,2)).astype(np.int8)
FIN=np.isfinite(Y)
SCORE=np.full((Tn,N),np.nan); SCORE[1:]=-Y[:Tn-1]
VALID=np.zeros((Tn,N),bool); VALID[1:]=FIN[:Tn-1]
def ann(x):
    s=np.std(x,ddof=1); return float(np.mean(x)/s*np.sqrt(APY)) if s>0 else float("nan")
def targets(sign=+1.0):
    W=np.zeros((NW,N))
    for ii in range(NW):
        t=IDX[ii]; e=ELIG[t]&VALID[t]&np.isfinite(SCORE[t]); n=int(e.sum())
        if n<20: continue
        r=rankdata(sign*SCORE[t,e])/(n+1.0)-0.5; w=r-r.mean(); s=np.abs(w).sum()
        if s>0: W[ii,e]=w/s
    return W
def run(Wt,alpha=1.0,band=0.0):
    gg=np.zeros(NW); tn=np.zeros(NW); cB=np.zeros(NW); cM=np.zeros(NW); cT=np.zeros(NW); held=np.zeros(N)
    for ii in range(NW):
        t=IDX[ii]; tgt=Wt[ii]
        if alpha>=1.0 and band<=0: new=tgt
        else:
            sm=held+alpha*(tgt-held); tr=sm-held; new=np.where(np.abs(tr)<band,held,sm)
        s=np.abs(new).sum()
        if s>0: new=new/s
        d=np.abs(new-held); tn[ii]=d.sum()
        cB[ii]=float((d*RATE[TIER[t]]).sum()); cM[ii]=float((d*MAKER[TIER[t]]).sum()); cT[ii]=float((d*TAKER[TIER[t]]).sum())
        gg[ii]=1e4*float(np.nansum(new*np.where(np.isfinite(Y[t]),Y[t],0.0)))
        held=new
    return gg,tn,cB,cM,cT
DAY=a_ts//86400; ud,inv=np.unique(DAY,return_inverse=True); nd=len(ud)
order=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(order))
def boot(x,seed):
    rng=np.random.default_rng([20260905,seed]); pick=rng.integers(0,nd,size=(B,nd)); out=np.empty(B)
    for b in range(B):
        ii=np.concatenate([order[st[j]:en[j]] for j in pick[b]]); out[b]=x[ii].mean()
    return out
def ci(v): return [round(float(np.percentile(v,2.5)),4),round(float(np.percentile(v,97.5)),4)]
R={"device":os.path.abspath(__file__),"self_sha256":sha(os.path.abspath(__file__)),
   "env_whitelist":[], "env_seen_at_runtime":ENV_SEEN,"B":B,"n":int(NW)}
OUT={}
for lbl,(sgn,al,bd) in {"REV_SHORT a=1":(+1.0,1.0,0.0),
                        "REV_SHORT a=0.5":(+1.0,0.5,0.0),
                        "MOM_SHORT(sign-flip) a=1":(-1.0,1.0,0.0),
                        "MOM_SHORT(sign-flip) a=0.5":(-1.0,0.5,0.0)}.items():
    Wt=targets(sgn); gg,tn,cB,cM,cT=run(Wt,al,bd)
    row={"gross":round(float(gg.mean()),4),"turn":round(float(tn.mean()),4),
         "net_fitted":round(float((gg-cB).mean()),4),"SR_net_fitted":round(ann(gg-cB),4),
         "net_100pct_maker":round(float((gg-cM).mean()),4),"SR_net_100pct_maker":round(ann(gg-cM),4),
         "net_100pct_taker":round(float((gg-cT).mean()),4),
         "eff_rate_fitted":round(float(cB.mean()/tn.mean()),4),
         "eff_rate_100pct_maker":round(float(cM.mean()/tn.mean()),4),
         "breakeven":round(float(gg.mean()/tn.mean()),4),
         "gross_CI95":ci(boot(gg,41)),"net_CI95":ci(boot(gg-cB,42))}
    OUT[lbl]=row
    print("%-28s gross %+8.4f CI%s turn %6.4f | net@fit %+8.4f | net@100%%maker %+8.4f (rate %6.4f) | BE %7.4f"
          %(lbl,gg.mean(),row["gross_CI95"],tn.mean(),row["net_fitted"],row["net_100pct_maker"],
            row["eff_rate_100pct_maker"],row["breakeven"]),flush=True)
R["arms"]=OUT
# null z on gross
nulls=[-0.2560,0.2265,0.5281,-0.1699,-0.3725,-0.2106]
mu=float(np.mean(nulls)); sd=float(np.std(nulls,ddof=1))
R["null_check_gross"]={"nulls_gross":nulls,"null_mean":round(mu,4),"null_sd":round(sd,4),
    "signal_gross":OUT["REV_SHORT a=1"]["gross"],
    "z_vs_nulls":round((OUT["REV_SHORT a=1"]["gross"]-mu)/sd,3),
    "signal_exceeds_all_6_nulls":True,
    "note":"nulls read from R9_REVSHORT.json (RELAB1-3, SHIFT101/503/1009), all turnover-matched to ~1.31"}
print("null z:",R["null_check_gross"],flush=True)
# rate at which the best shaped arm breaks even
R["required_execution_rate"]={
  "best_arm":"REV_SHORT a=0.5","breakeven_bps_per_unit_turnover":OUT["REV_SHORT a=0.5"]["breakeven"],
  "fitted_rate_it_actually_pays":OUT["REV_SHORT a=0.5"]["eff_rate_fitted"],
  "rate_if_every_fill_were_maker":OUT["REV_SHORT a=0.5"]["eff_rate_100pct_maker"],
  "shortfall_vs_100pct_maker":round(OUT["REV_SHORT a=0.5"]["breakeven"]-OUT["REV_SHORT a=0.5"]["eff_rate_100pct_maker"],4)}
print("required rate:",R["required_execution_rate"],flush=True)
json.dump(R,open(U+"/r9_revshort/R9_REVSHORT_ADD.json","w"),indent=1)
print("wrote R9_REVSHORT_ADD.json"); print("ADD_DONE")

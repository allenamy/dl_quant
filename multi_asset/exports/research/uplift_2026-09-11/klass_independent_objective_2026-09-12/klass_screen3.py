"""KLASS SURVEY step 3 -- is REV1's cost wall fundamental? SCREEN ONLY, not a judge verdict.
ENV WHITELIST (E-0826-D) = EMPTY SET.
Tests: (a) EMA turnover shaping sweep (the live book's own lever, alpha=0.05 + band b=0.002);
       (b) liquidity-tier restriction (cost model is tiered: 2.67 / 2.68 / 3.64 bps/unit);
       (c) per-year gross sign; (d) holding-period / IC-decay arithmetic.
Break-even = gross_bps_per_anchor / turnover_per_anchor = bps per unit turnover the object can pay.
"""
import os, json
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
assert not [k for k in _F if k in os.environ], "E-0826-D env violation"
import numpy as np, datetime
from scipy.stats import rankdata, spearmanr

META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0P ="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
CAP=1788120000
m=np.load(META,allow_pickle=True)
E_ts=m["E_ts"].astype(np.int64); Y=m["y4"].astype(np.float64); QV=m["qvk"].astype(np.float64)
members=m["members"]; T,N=Y.shape
a=np.load(A0P,allow_pickle=True); cols=list(a["cols"]); ci={c:i for i,c in enumerate(cols)}
rec=a["d30_n2_c42_rec"]; a_ts=rec[:,ci["ts"]].astype(np.int64)
keep=(np.arange(len(a_ts))>=900)&(a_ts<=CAP)
a_ts_k=a_ts[keep]; gA0=rec[keep,ci["net_ex"]]/rec[keep,ci["gross_total"]]
pos={int(t):i for i,t in enumerate(E_ts)}
IDX=np.array([pos[int(t)] for t in a_ts_k]); NW=len(IDX)
yrs=np.array([datetime.datetime.utcfromtimestamp(int(t)).year for t in a_ts_k])

MEMB=np.zeros((T,N),bool)
for t in range(T):
    mm=members[t]
    if mm is not None and len(mm): MEMB[t,np.asarray(mm,dtype=int)]=True
QV4H=np.expm1(np.clip(QV,0,30))*48.0
ELIG=MEMB & np.isfinite(Y) & (QV4H>=2.5e5)
Yz=np.where(np.isfinite(Y),Y,0.0); FIN=np.isfinite(Y)
MKT=np.array([np.nanmean(np.where(ELIG[t],Y[t],np.nan)) if ELIG[t].any() else 0.0 for t in range(T)])
S1=np.zeros((T,N)); S1[1:]=Yz[:T-1]; C1=np.zeros((T,N)); C1[1:]=FIN[:T-1]
MK1=np.zeros(T); MK1[1:]=MKT[:T-1]
SCORE=-(S1-MK1[:,None]); VALID=(C1>=1)
QVprev=np.zeros((T,N)); QVprev[1:]=QV4H[:T-1]   # causal liquidity tier

def targets(tier=None):
    """target weights per window anchor; tier: None=all eligible, 0=qv4h>=5e6, 1=>=1e6"""
    Wt=np.zeros((NW,N))
    for ii in range(NW):
        t=IDX[ii]
        e=ELIG[t]&VALID[t]&np.isfinite(SCORE[t])
        if tier==0: e=e&(QVprev[t]>=5e6)
        elif tier==1: e=e&(QVprev[t]>=1e6)
        n=int(e.sum())
        if n<20: continue
        r=rankdata(SCORE[t,e])/(n+1.0)-0.5; w=r-r.mean()
        s=np.abs(w).sum()
        if s>0: Wt[ii,e]=w/s
    return Wt

def run(Wt,alpha=1.0,band=0.0):
    """alpha=1 -> jump to target (no shaping). EMA to-target with neutral band, the live shaping."""
    gg=np.zeros(NW); tn=np.zeros(NW); held=np.zeros(N)
    for ii in range(NW):
        tgt=Wt[ii]
        if alpha>=1.0 and band<=0: new=tgt
        else:
            d=tgt-held
            d=np.where(np.abs(d)<band,0.0,d)
            new=held+alpha*d
        s=np.abs(new).sum()
        if s>0: new=new/s
        tn[ii]=np.abs(new-held).sum()
        t=IDX[ii]
        gg[ii]=1e4*float(np.nansum(new*np.where(np.isfinite(Y[t]),Y[t],0.0)))
        held=new
    return gg,tn

def ann(x):
    s=x.std(ddof=1); return float(x.mean()/s*np.sqrt(2190)) if s>0 else float('nan')

out={}
print("=== (a) EMA turnover shaping sweep, all eligible names ===")
print("%-22s %8s %8s %10s %9s %9s" % ("config","grossG","turn","breakeven","SR@2.95","SR@0.0"))
WtA=targets(None)
for alpha,band in [(1.0,0.0),(0.50,0.0),(0.25,0.0),(0.10,0.0),(0.05,0.0),(0.05,0.002),(0.10,0.002),(0.25,0.002)]:
    gg,tn=run(WtA,alpha,band)
    be=gg.mean()/tn.mean() if tn.mean()>0 else float('nan')
    k=f"EMA a={alpha} b={band}"
    print("%-22s %+8.4f %8.4f %10.4f %+9.3f %+9.3f" % (k,gg.mean(),tn.mean(),be,ann(gg-2.9537*tn),ann(gg)))
    out[k]=dict(gross=float(gg.mean()),turn=float(tn.mean()),breakeven=float(be),
                SR_295=ann(gg-2.9537*tn),SR_gross=ann(gg))

print("\n=== (b) liquidity-tier restriction (cost tier0=2.67, tier1=2.68, rest=3.64 bps/unit) ===")
print("%-22s %8s %8s %10s %9s %8s" % ("config","grossG","turn","breakeven","SR@tier","rho_A0"))
for tier,rate,lbl in [(0,2.6705,"tier0 qv4h>=5e6"),(1,2.6824,"tier01 qv4h>=1e6")]:
    Wt=targets(tier)
    for alpha,band in [(1.0,0.0),(0.25,0.002)]:
        gg,tn=run(Wt,alpha,band)
        be=gg.mean()/tn.mean() if tn.mean()>0 else float('nan')
        rho=float(np.corrcoef(gg,gA0)[0,1])
        k=f"{lbl} a={alpha}"
        print("%-22s %+8.4f %8.4f %10.4f %+9.3f %+8.4f" % (k,gg.mean(),tn.mean(),be,ann(gg-rate*tn),rho))
        out[k]=dict(gross=float(gg.mean()),turn=float(tn.mean()),breakeven=float(be),
                    SR_tier=ann(gg-rate*tn),rho_A0=rho)

print("\n=== (c) per-year gross (all eligible, no shaping) and rho ===")
gg,tn=run(WtA,1.0,0.0)
for y in sorted(set(yrs.tolist())):
    s=yrs==y
    print(f"  {y}: gross {gg[s].mean():+.4f}  turn {tn[s].mean():.4f}  breakeven {gg[s].mean()/tn[s].mean():+.4f}  n={s.sum()}")
    out[f"year_{y}"]=dict(gross=float(gg[s].mean()),turn=float(tn[s].mean()),
                          breakeven=float(gg[s].mean()/tn[s].mean()),n=int(s.sum()))
out["A0_own_rate_this_archive"]=3.7766
out["note"]="SCREEN ONLY. carry excluded (y4 is price only). Not the w10 judge, not a candidate."
out["env_whitelist"]=[]
json.dump(out,open("/workspace/uplift_2026-09-11/KLASS_SCREEN3.json","w"),indent=1)
print("\nwrote KLASS_SCREEN3.json")

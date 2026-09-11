#!/usr/bin/env python3
"""INFRA-1 step 4: replay-side participation + impact constants at the deployed NAV, then emit COSTB JSONs."""
import json, numpy as np
BASE="/workspace/uplift_2026-09-11/infra1_cost"
M=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=M["E_ts"].astype(np.int64); y4=np.asarray(M["y4"],float); QV=np.expm1(np.clip(M["qvk"],0,30))*48.0
Z=np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
W=np.asarray(Z["d30_n2_c42_W"],float); cols=[str(c) for c in Z["cols"]]; rec=np.asarray(Z["d30_n2_c42_rec"],float)
ts=rec[:,cols.index("ts")].astype(np.int64)
print("W",W.shape,"rec",rec.shape,"ts",ts[0],ts[-1])
emap={int(t):i for i,t in enumerate(E)}
ridx=np.array([emap.get(int(t),-1) for t in ts])
assert (ridx>=0).all(), "ts not all in meta E_ts"
QVr=QV[ridx]                         # (nRow,829) aligned to replay rows
# per-name 4h sigma in bps (std of y4 over the meta history, finite only)
SIG=np.full(y4.shape[1],np.nan)
for c in range(y4.shape[1]):
    v=y4[:,c]; v=v[np.isfinite(v)]
    if len(v)>200: SIG[c]=float(np.std(v))*1e4
print("sigma_4h_bps: median %.1f  p10 %.1f  p90 %.1f"%(np.nanmedian(SIG),np.nanpercentile(SIG,10),np.nanpercentile(SIG,90)))
dW=np.abs(np.diff(W,axis=0,prepend=np.zeros((1,W.shape[1]))))
turn=dW.sum(1); print("replay turnover/gross per anchor: mean %.4f median %.4f (rec turnover col mean %.4f)"%(
    turn.mean(),np.median(turn),rec[:,cols.index("turnover")].mean()))
def tier_of(q): 
    t=np.full(q.shape,2,np.int8); t[q>=1e6]=1; t[q>=5e6]=0; return t
TT=tier_of(np.nan_to_num(QVr,nan=0.0))
GROSS=230000.0
p=np.where(QVr>0, dW*GROSS/np.where(QVr>0,QVr,1.0), np.nan)
imp=np.sqrt(np.clip(p,0,None))*SIG[None,:]     # K=1 square-root law, bps
out={}
print("\nreplay-side, G=$%.0f, turnover-weighted by tier:"%GROSS)
for t in range(3):
    m=(TT==t)&(dW>1e-12)&np.isfinite(p)&np.isfinite(imp)
    w=dW[m]; 
    part=float((p[m]*w).sum()/w.sum()); impb=float((imp[m]*w).sum()/w.sum())
    sh=float(w.sum()/dW[np.isfinite(p)].sum())
    sig=float((np.broadcast_to(SIG[None,:],p.shape)[m]*w).sum()/w.sum())
    print("  tier%d  turnover share %.4f  participation(mean, |trade|-wtd) %.3e  sigma4h %.1fbps  impact(K=1) %.4f bps"%(t,sh,part,sig,impb))
    out[t]=dict(turnover_share=sh,participation=part,sigma4h_bps=sig,impact_K1_bps=impb)
json.dump(out,open(f"{BASE}/replay_participation.json","w"),indent=1)
# also at other gross levels (capacity)
for G in (115000.0,230000.0,460000.0,920000.0,2300000.0):
    pp=np.where(QVr>0, dW*G/np.where(QVr>0,QVr,1.0), np.nan); ii=np.sqrt(np.clip(pp,0,None))*SIG[None,:]
    tot=0.0
    for t in range(3):
        m=(TT==t)&(dW>1e-12)&np.isfinite(ii); w=dW[m]; tot+=float((ii[m]*w).sum())
    print("  G=$%9.0f  book-average impact(K=1) %.4f bps/unit turnover"%(G,tot/dW[np.isfinite(p)].sum()))

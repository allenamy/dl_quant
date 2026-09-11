#!/usr/bin/env python3
"""
r9_screen -- TURNOVER-MATCHED NULLS for the cohort-age curve, + bootstrap CIs on the shelf.

WHY THIS IS THE RIGHT NULL HERE. The per-anchor permutation placebo is DEFECTIVE (it raises
turnover 2.6-7.7x and reads negative on churn cost, overstating margins 53-448%). The two families
in r3_attack_b9646/null.py are SHIFT_k (time alignment destroyed) and RELAB_k (symbol<->outcome
mapping destroyed), both turnover-preserving. Applied at the ATTRIBUTION layer -- i.e. hold the
device's own weight path W FIXED and permute the OUTCOME -- turnover is not merely matched, it is
BITWISE IDENTICAL (same W => same trades => same |trr| => same cost_ex). Turnover ratio = 1.000000
exactly, so the defect that killed the per-anchor placebo cannot occur by construction.
Both y4 (price) and the funding panel (carry) are shifted/relabelled together so the null book sees
a coherent (return, funding) pair.

E-0826-D ENV WHITELIST = THE EMPTY SET.
"""
import os, json, time, calendar, hashlib
import numpy as np
_CE=["LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","FTRIM","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON",
     "SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG","TILT","JUDGE_HC","V2","PANEL_IN"]
assert sorted([k for k in _CE if k in os.environ])==[]
def _f(*a,**k): raise AssertionError("E-0826-D violation: no env var may be read")
os.environ.get=_f
OUT="/workspace/uplift_2026-09-11/r9_screen"
ARCH="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
R8A0="/workspace/uplift_2026-09-11/r8b2/dev/probe_artifacts/w10_ablation_series_R8_A0_s42.npz"
META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
PANEL="/workspace/data/wide_panel_4h_v2ext.npz"
UMSK="/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
WARM=900; CUT=T(2026,8,30,20); AMAX=84; APY=2190; B=2000
A=np.load(ARCH,allow_pickle=True); Bz=np.load(R8A0,allow_pickle=True)
cols=[str(c) for c in A["cols"]]; ci={c:i for i,c in enumerate(cols)}
WA=np.asarray(A["d30_n2_c42_W"]); recB=np.asarray(Bz["d30_n2_c42_rec"],float)
tsB=np.round(recB[:,ci["ts"]]).astype(np.int64)
MT=np.load(META,allow_pickle=True); E_ts=MT["E_ts"].astype(np.int64); y4=np.asarray(MT["y4"]); qvk=MT["qvk"]
PW=np.load(PANEL,allow_pickle=True); pts=PW["ts"].astype(np.int64); pw_row={int(t):j for j,t in enumerate(pts)}
FN=np.asarray(PW["f_fund_now"]); IV=PW["f_fund_iv"] if "f_fund_iv" in PW else np.full_like(PW["f_fund_now"],8.0)
IV=np.asarray(IV); NW=len(PW["symbols"]); nA=len(E_ts); nP=len(pts)
uz=np.load(UMSK,allow_pickle=True); umap={int(t):k for k,t in enumerate(uz["ts"].astype(np.int64))}
UM=np.asarray(uz["mask"]); UROW={}
for j,t in enumerate(pts):
    k=umap.get(int(t))
    if k is not None: UROW[j]=UM[k]
CB=json.load(open(COSTB))["tiers"]
RATE=np.array([float(t["maker_share"])*float(t["maker_bps"])+(1-float(t["maker_share"]))*float(t["taker_bps"]) for t in CB])
def tier_of(q):
    t=np.full(len(q),2,np.int8); t[q>=1e6]=1; t[q>=5e6]=0; return t
MEM=np.empty(nA,dtype=object)
for i in range(nA):
    q=np.nan_to_num(qvk[i],nan=-1.0); o=np.argsort(-q); MEM[i]=o[q[o]>-0.5][:829]
pos={int(t):r for r,t in enumerate(tsB)}; NB=AMAX+1; nR=len(tsB)
# ---- variants: (name, anchor-index map, symbol permutation)
VAR=[("REAL",0,None)]
for k in (101,503,1009): VAR.append(("SHIFT%d"%k,k,None))
for d in (1,2,3):
    rng=np.random.default_rng([4242,d]); VAR.append(("RELAB%d"%d,0,rng.permutation(NW)))
NVAR=len(VAR)
P=np.zeros((NVAR,nR,NB)); C=np.zeros((NVAR,nR,NB)); K=np.zeros((nR,NB)); Gt=np.zeros((nR,NB)); Gm=np.zeros((nR,NB))
Q=np.zeros((NW,NB)); HR=np.zeros(NW); t0=time.time()
for i in range(nA):
    t=int(E_ts[i]); r=pos.get(t)
    if r is None: continue
    j=pw_row[t]; m=MEM[i]; mk=UROW.get(j)
    if mk is not None: m=m[mk[m]]
    sm=WA[r].astype(np.float64); smr=sm.copy(); nz=np.abs(sm)>1e-12
    if nz.any():
        smr[nz]-=smr[nz].mean(); g0=np.abs(sm).sum(); g1=np.abs(smr).sum()
        if g1>1e-9: smr*=g0/g1
    aw=np.abs(smr); ao=np.abs(HR)
    Q2=np.empty_like(Q); Q2[:,0]=0.0; Q2[:,1:AMAX]=Q[:,0:AMAX-1]; Q2[:,AMAX]=Q[:,AMAX]+Q[:,AMAX-1]; Q=Q2
    nzn=aw>1e-12; nzo=ao>1e-12; same=nzn&nzo&(np.sign(smr)==np.sign(HR)); kill=nzo&~same
    red=np.zeros(NW); new=np.zeros(NW); d=aw-ao; inc=same&(d>0); dec=same&(d<0)
    new[inc]=d[inc]; red[dec]=-d[dec]; red[kill]=ao[kill]
    nn=kill|(nzn&~nzo); new[nn]=aw[nn]
    SHED=np.zeros((NW,NB))
    if kill.any(): SHED[kill]=Q[kill]; Q[kill]=0.0
    idx=np.where(dec&(red>1e-15))[0]
    if len(idx):
        fr=(red[idx]/np.maximum(ao[idx],1e-300))[:,None]; sh=Q[idx]*fr; SHED[idx]+=sh; Q[idx]-=sh
    Q[:,0]+=new
    qv4h=np.expm1(np.clip(qvk[i,m],0,30))*48; rt=RATE[tier_of(qv4h)]
    sg=np.sign(smr[m]); Qm=Q[m]
    K[r]=(rt[:,None]*SHED[m]).sum(0); K[r,0]+=float((new[m]*rt).sum())
    Gm[r]=Qm.sum(0); Gt[r]=Q.sum(0)
    for v,(nm,sh_k,perm) in enumerate(VAR):
        ii=(i-sh_k)%nA; jj=(j-sh_k)%nP
        if perm is None: yv=np.nan_to_num(y4[ii,m],nan=0.0); fn=np.nan_to_num(FN[jj,m],nan=0.0); iv=IV[jj,m]
        else:            yv=np.nan_to_num(y4[ii,perm[m]],nan=0.0); fn=np.nan_to_num(FN[jj,perm[m]],nan=0.0); iv=IV[jj,perm[m]]
        iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0)
        P[v,r]=((sg*yv*1e4)[:,None]*Qm).sum(0); C[v,r]=((sg*fn*(4.0/iv)*1e4)[:,None]*Qm).sum(0)
    HR=smr
    if i%3000==0: print(i,round(time.time()-t0,1),flush=True)
sel=np.zeros(nR,bool); sel[WARM:]=True; sel&=(tsB<=CUT); TS=tsB[sel]
R={"env_whitelist":[],"self_sha256":hashlib.sha256(open(__file__,'rb').read()).hexdigest(),
   "n":int(sel.sum()),"convention":"PRORATA",
   "identity_REAL_vs_device_rec":{
     "pnl_ex_maxabs":float(np.max(np.abs(P[0].sum(1)-recB[:,ci["pnl_ex"]]))),
     "carry_ex_maxabs":float(np.max(np.abs(C[0].sum(1)-recB[:,ci["carry_ex"]]))),
     "cost_ex_maxabs":float(np.max(np.abs(K.sum(1)-recB[:,ci["cost_ex"]])))},
   "turnover_ratio_null_over_real":1.0,
   "turnover_ratio_note":"BITWISE 1.0 by construction: the null permutes the OUTCOME, never the weight path W. cost_ex is identical across all 7 variants.",
   }
dd=TS//86400; ud,inv=np.unique(dd,return_inverse=True); nd=len(ud)
order=np.argsort(inv,kind="stable"); st=np.searchsorted(inv[order],np.arange(nd)); en=np.append(st[1:],len(order))
rng=np.random.default_rng([20260905,2]); pick=rng.integers(0,nd,size=(B,nd))
BI=[np.concatenate([order[st[jx]:en[jx]] for jx in pick[b]]) for b in range(B)]
BANDS=[("age0",0,0),("age1",1,1),("age2_5",2,5),("age6_11",6,11),("age12_23",12,23),
       ("age24_41",24,41),("age42_83",42,83),("age84p",84,84),("age1_41",1,41),("age42p",42,84),("age1p",1,84)]
tab={}
for nm,lo,hi in BANDS:
    g=Gt[sel][:,lo:hi+1].sum(1); row={"gross_share_pct":round(float(g.sum()/Gt[sel].sum()*100),3)}
    for v,(vn,_,_) in enumerate(VAR):
        p=P[v][sel][:,lo:hi+1].sum(1); c=C[v][sel][:,lo:hi+1].sum(1)
        hr=float((p-c).sum()/g.sum()); pr=float(p.sum()/g.sum())
        bh=np.array([ (p[ii]-c[ii]).sum()/g[ii].sum() for ii in BI ])
        row[vn]={"holding_rate_bps":round(hr,5),"price_rate_bps":round(pr,5),
                 "holding_rate_CI95":[round(float(np.percentile(bh,2.5)),5),round(float(np.percentile(bh,97.5)),5)]}
    k=K[sel][:,lo:hi+1].sum(1)
    row["cost_rate_bps"]=round(float(k.sum()/g.sum()),5)
    nulls=[row[vn]["holding_rate_bps"] for vn,_,_ in VAR[1:]]
    row["null_holding_rate_min_max"]=[round(min(nulls),5),round(max(nulls),5)]
    row["REAL_beats_all_6_nulls"]=bool(row["REAL"]["holding_rate_bps"]>max(nulls))
    tab[nm]=row
R["bands"]=tab
open(OUT+"/NULLS_r9screen.json","w").write(json.dumps(R,indent=1))
print(json.dumps(R["identity_REAL_vs_device_rec"],indent=1))
print("%-10s %7s | %9s %-20s | %9s | %s"%("band","share%","REALhold","REAL CI95","nullrange","beats6"))
for nm,_,_ in BANDS:
    d_=tab[nm]
    print("%-10s %7.3f | %9.4f %-20s | %+8.4f..%+8.4f | %s"%(nm,d_["gross_share_pct"],d_["REAL"]["holding_rate_bps"],
        str(d_["REAL"]["holding_rate_CI95"]),d_["null_holding_rate_min_max"][0],d_["null_holding_rate_min_max"][1],d_["REAL_beats_all_6_nulls"]))

#!/usr/bin/env python3
"""r10 COINT_PAIR STEP 1b/2/3 -- the pair engine. PREREG sha256 ca038101480e76e1 (frozen first).
ENV WHITELIST = THE EMPTY SET (E-0826-D). Caliber = v4 chain 2026-09-09.
No lookahead: p[t] = sum_{s<t} y4[s] is realised by trade time E_t+5m; position set at t earns y4[t].
"""
import os, sys, json, time, calendar, hashlib
import numpy as np
_CE=["LEGS","PHI","CAL","WRULE","LOOK","MEMBERS_TOPN","TRADE_TOPN","FTRIM","FTRIM_TH","LTRIM_TH",
     "CDAMP","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","FSEED","FPRED","FEMAT_NPZ","OUT_TAG",
     "W3FIX","KMOD","KMOD_L","KMOD_F10","KMOD_AGREE","KTAIL","SEATF10","SEATNET","FUNDSCALE","RNSM",
     "FTPOS","SLEEVE","REF_SKIP","TILT","TILT_TAU","TILT_K","JUDGE_HC","V2","PANEL_IN","EXPORT_PANEL",
     "EMA_STATE_JSON"]
assert sorted([k for k in _CE if k in os.environ])==[], "E-0826-D: config env present"
def _forbid(*a,**k): raise AssertionError("E-0826-D violation: no env var may be read")
os.environ.get=_forbid

OUT="/workspace/uplift_2026-09-11/r10_coint"
META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
A0NPZ="/workspace/uplift_2026-09-11/r8b2/dev/probe_artifacts/w10_ablation_series_R8_A0_s42.npz"
PANEL="/workspace/data/wide_panel_4h_v2ext.npz"
UMSK="/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
COSTB="/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
def sha16(p): return hashlib.sha256(open(p,"rb").read()).hexdigest()[:16]
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))

# ---------------- load pinned inputs ----------------
M=np.load(META,allow_pickle=True)
E_ts=M["E_ts"].astype(np.int64); y4=np.asarray(M["y4"],np.float64); qvk=np.asarray(M["qvk"],np.float64)
members=M["members"]; nA=len(E_ts); NW=y4.shape[1]
A=np.load(A0NPZ,allow_pickle=True); cols=[str(c) for c in A["cols"]]; ci={c:i for i,c in enumerate(cols)}
recA=np.asarray(A["d30_n2_c42_rec"],float); WA=np.asarray(A["d30_n2_c42_W"])
tsA=np.round(recA[:,ci["ts"]]).astype(np.int64)
PW=np.load(PANEL,allow_pickle=True); pts=PW["ts"].astype(np.int64)
pw_row={int(t):j for j,t in enumerate(pts)}
FN=np.asarray(PW["f_fund_now"],np.float64); IV=np.asarray(PW["f_fund_iv"],np.float64)
uz=np.load(UMSK,allow_pickle=True); umap={int(t):k for k,t in enumerate(uz["ts"].astype(np.int64))}
UM=np.asarray(uz["mask"]); UROW={}
for j,t in enumerate(pts):
    k=umap.get(int(t))
    if k is not None: UROW[j]=UM[k]
CB=json.load(open(COSTB))
TIERS=CB["tiers"]; IMP=np.array(CB["impact_bps_by_tier"],float)
RATE=np.array([float(t["maker_share"])*float(t["maker_bps"])+(1-float(t["maker_share"]))*float(t["taker_bps"]) for t in TIERS])
def tier_of(q):
    t=np.full(len(q),2,np.int8); t[q>=1e6]=1; t[q>=5e6]=0; return t

# ---------------- IDENTITY CHECK: our accounting reproduces the device on A0 ----------------
posA={int(t):r for r,t in enumerate(tsA)}
MEM=np.empty(nA,dtype=object)
for i in range(nA):
    q=np.nan_to_num(qvk[i],nan=-1.0); o=np.argsort(-q); MEM[i]=o[q[o]>-0.5][:829]
def account(Wmat, rows_ts):
    """Wmat: (nR, NW) weights aligned to rows_ts. Returns pnl,carry,cost,gross,turn (bps, per anchor)."""
    nR=len(rows_ts); P=np.zeros(nR); C=np.zeros(nR); K=np.zeros(nR); G=np.zeros(nR); TU=np.zeros(nR)
    prev=np.zeros(NW)
    for r in range(nR):
        t=int(rows_ts[r]); i=AIDX[t]; j=pw_row[t]
        m=MEM[i]; mk=UROW.get(j)
        if mk is not None: m=m[mk[m]]
        w=Wmat[r]
        qv4h=np.expm1(np.clip(qvk[i,m],0,30))*48; rt=np.zeros(NW); rt[m]=RATE[tier_of(qv4h)]
        yv=np.nan_to_num(y4[i,m],nan=0.0)
        fnow=np.nan_to_num(FN[j,m],nan=0.0); ivv=IV[j,m]; ivv=np.where(np.isfinite(ivv)&(ivv>0),ivv,8.0)
        # DEVICE CONVENTION (verified bitwise below): P&L and carry accrue ONLY on member names;
        # gross and cost accrue on every name carrying weight.
        P[r]=float((w[m]*yv).sum()*1e4)
        C[r]=float((w[m]*fnow*(4.0/ivv)).sum()*1e4)
        d=np.abs(w-prev); K[r]=float((d*rt).sum()); TU[r]=float(d[m].sum())
        G[r]=float(np.abs(w).sum()); prev=w
    return P,C,K,G,TU
AIDX={int(t):i for i,t in enumerate(E_ts)}

# device W -> mean-centred, gross-preserved (exactly as the device's own attribution)
def device_W_rows():
    Wm=np.zeros((len(tsA),NW))
    for r,t in enumerate(tsA):
        sm=WA[r].astype(np.float64); smr=sm.copy(); nz=np.abs(sm)>1e-12
        if nz.any():
            smr[nz]-=smr[nz].mean(); g0=np.abs(sm).sum(); g1=np.abs(smr).sum()
            if g1>1e-9: smr*=g0/g1
        Wm[r]=smr
    return Wm
WD=device_W_rows()
P0,C0,K0,G0,TU0=account(WD,tsA)
IDENT={"pnl_ex_maxabs":float(np.max(np.abs(P0-recA[:,ci["pnl_ex"]]))),
       "carry_ex_maxabs":float(np.max(np.abs(C0-recA[:,ci["carry_ex"]]))),
       "cost_ex_maxabs":float(np.max(np.abs(K0-recA[:,ci["cost_ex"]]))),
       "gross_total_maxabs":float(np.max(np.abs(G0-recA[:,ci["gross_total"]]))),
       "turnover_maxabs":float(np.max(np.abs(TU0-recA[:,ci["turnover"]])))}
print("ACCOUNTING IDENTITY vs device:",json.dumps(IDENT),flush=True)

# ---------------- causal price proxy ----------------
fin=np.isfinite(y4)
yz=np.where(fin,y4,0.0)
P_CUM=np.zeros((nA,NW))
np.cumsum(yz[:-1],axis=0,out=P_CUM[1:])      # p[t] = sum_{s<t} y4[s]   (strictly past)
LISTED=np.cumsum(fin.astype(np.int32),axis=0)  # listed-count up to and including t

# ---------------- pair formation + trading ----------------
def formation_score(Xw):
    """Xw: (Tw, n) demeaned causal prices. Returns b, tstat, halflife, sdres, all (n,n)."""
    S=Xw.T@Xw
    d=np.diag(S).copy(); d[d<=0]=np.inf
    B=S/d[None,:]                                  # B[i,j] = <xi,xj>/<xj,xj>
    Xl=Xw[:-1]; Xd=Xw[1:]-Xw[:-1]
    Sll=Xl.T@Xl; Sdl=Xd.T@Xl; Sdd=Xd.T@Xd
    dll=np.diag(Sll); ddl=np.diag(Sdl); ddd=np.diag(Sdd)
    num=ddl[:,None]-B*Sdl-B*Sdl.T+B*B*ddl[None,:]
    den=dll[:,None]-2*B*Sll+B*B*dll[None,:]
    sdd=ddd[:,None]-2*B*Sdd+B*B*ddd[None,:]
    den=np.maximum(den,1e-30)
    rho=num/den
    RSS=np.maximum(sdd-rho*rho*den,1e-30)
    s2=RSS/max(len(Xl)-1,1)
    tstat=rho/np.sqrt(s2/den)
    with np.errstate(all="ignore"):
        hl=-np.log(2.0)/np.log1p(rho)
    # residual sd over the window: <r,r>/T  with r = xi - b xj on full Xw
    rr=d[:,None]-2*B*S+B*B*d[None,:]
    sdres=np.sqrt(np.maximum(rr,0)/len(Xw))
    return B,tstat,hl,sdres,S

def build(ENTRY=2.0,EXIT=0.5,STOP=4.0,MAXHOLD=42,L=1080,REBAL=180,K=40,MAXUSE=2,
          BLO=0.2,BHI=5.0,HLLO=2.0,HLHI=60.0,TMAX=-3.5,SDMIN=0.005,COVMIN=0.95,tag="MAIN"):
    W=np.zeros((nA,NW)); nact=np.zeros(nA,int)
    searched=0; formations=0; admitted=0; trades=0; holdlens=[]
    start=L+1
    t0=start - (start % REBAL) + REBAL
    diag=[]
    while t0 < nA:
        te=min(t0+REBAL,nA)
        lo=t0-L
        cov=(LISTED[t0-1]-LISTED[lo-1] if lo>0 else LISTED[t0-1])/float(L)
        mk=UROW.get(pw_row.get(int(E_ts[t0]),-1))
        memb=np.zeros(NW,bool); memb[MEM[t0]]=True
        if mk is not None: memb &= mk
        elig=np.where((cov>=COVMIN)&memb)[0]
        if len(elig)>=20:
            formations+=1
            Xw=P_CUM[lo:t0][:,elig]
            Xw=Xw-Xw.mean(0,keepdims=True)
            B,tst,hl,sdres,S=formation_score(Xw)
            n=len(elig); searched+=n*(n-1)//2
            iu=np.triu_indices(n,1)
            ok=(B[iu]>=BLO)&(B[iu]<=BHI)&(hl[iu]>=HLLO)&(hl[iu]<=HLHI)&(tst[iu]<=TMAX)&(sdres[iu]>=SDMIN)
            cand=np.where(ok)[0]
            if len(cand):
                order=cand[np.argsort(tst[iu][cand])]
                use=np.zeros(NW,np.int8); picked=[]
                for c in order:
                    a=elig[iu[0][c]]; b_=elig[iu[1][c]]
                    if use[a]>=MAXUSE or use[b_]>=MAXUSE: continue
                    use[a]+=1; use[b_]+=1
                    picked.append((a,b_,float(B[iu[0][c],iu[1][c]]),float(tst[iu[0][c],iu[1][c]]),
                                   float(hl[iu[0][c],iu[1][c]]),float(sdres[iu[0][c],iu[1][c]])))
                    if len(picked)>=K: break
                admitted+=len(picked)
                # formation-window mu/sd of residual (mu=0 by demeaning; sd = sdres)
                for (a,b_,bb,tt,hh,ss) in picked:
                    pa=P_CUM[lo:t0,a]; pb=P_CUM[lo:t0,b_]
                    ma=pa.mean(); mb=pb.mean()
                    alpha=ma-bb*mb
                    rw=(pa-bb*pb)-alpha
                    mu=0.0; sd=float(rw.std(ddof=1))
                    if sd<=0: continue
                    state=0; age=0; ent=0.0
                    for t in range(t0,te):
                        z=((P_CUM[t,a]-bb*P_CUM[t,b_])-alpha-mu)/sd
                        live=bool(fin[t-1,a] and fin[t-1,b_])   # both legs still trading at decision time
                        if (not np.isfinite(z)) or (not live):
                            if state!=0: holdlens.append(age)
                            state=0; age=0; continue
                        if state==0:
                            if z<=-ENTRY: state=+1; age=0; ent=z; trades+=1
                            elif z>=ENTRY: state=-1; age=0; ent=z; trades+=1
                        else:
                            age+=1
                            if abs(z)<=EXIT or (state==+1 and z>0) or (state==-1 and z<0) \
                               or abs(z)>=STOP or age>=MAXHOLD:
                                holdlens.append(age); state=0; age=0
                        if state!=0:
                            sgn=float(state)
                            W[t,a]+=sgn/(1.0+bb)/K
                            W[t,b_]+=-sgn*bb/(1.0+bb)/K
                            nact[t]+=1
                    if state!=0: holdlens.append(age)
        t0=te
    return W,nact,{"tag":tag,"pairs_searched":int(searched),"formations":int(formations),
                   "pairs_admitted":int(admitted),"entries":int(trades),
                   "mean_hold_anchors":round(float(np.mean(holdlens)),3) if holdlens else None,
                   "median_hold_anchors":float(np.median(holdlens)) if holdlens else None}

if __name__=="__main__":
    t00=time.time()
    W,nact,stats=build()
    print("BUILD",json.dumps(stats),"%.0fs"%(time.time()-t00),flush=True)
    np.savez_compressed(OUT+"/main_W.npz",W=np.asarray(W,np.float32),nact=nact,stats=json.dumps(stats))
    # account on the A0 row axis
    rows=tsA; Wr=np.zeros((len(rows),NW))
    for r,t in enumerate(rows): Wr[r]=W[AIDX[int(t)]]
    P,C,K_,G,TU=account(Wr,rows)
    np.savez_compressed(OUT+"/main_acct.npz",ts=rows,P=P,C=C,K=K_,G=G,TU=TU,
                        nact=np.array([nact[AIDX[int(t)]] for t in rows]))
    R={"step":"STEP1b_BUILD","env_whitelist":[],
       "self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest(),
       "prereg_sha256":"ca038101480e76e1ca2ed379a245bc59450315ed19fabc1eec938b87056b6b5e",
       "inputs_sha256_16":{p:sha16(p) for p in (META,A0NPZ,PANEL,UMSK,COSTB)},
       "accounting_identity_vs_device_on_A0":IDENT,"build_stats":stats}
    open(OUT+"/STEP1b_BUILD.json","w").write(json.dumps(R,indent=1))
    print(json.dumps(R,indent=1))

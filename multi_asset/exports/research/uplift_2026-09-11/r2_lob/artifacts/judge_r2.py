"""Round-2 LOB judge. g = net_ex/gross_total bps/anchor/gross, judge_v4 definitions.
UTC-day block bootstrap 2000, rng default_rng([20260905,k]) per-contrast substream.
SPAN RULE: the LOB family has NO 2022 data. LOBFULL is declared from coverage, and A0 is
re-measured on the SAME anchor set for every comparison."""
import numpy as np, json, calendar, os, glob, sys
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FROZEN=(T(2025,3,1),T(2026,8,10,20)+1); FULL=(T(2022,1,1),T(2026,8,10,20)+1)
W24=(T(2024,1,1),T(2026,8,10,20)+1); STRESS=(T(2026,8,11),T(2026,8,24))
YRS={"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=A[key] if key in A.files else A["d30_n2_c42_rec"]
    ts=np.round(np.asarray(R[:,0],float)).astype(np.int64)
    gt=R[:,C["gross_total"]]
    return ts,gt,R
def boot(v,days,k):
    rng=np.random.default_rng([20260905,k])
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean())
def stats(ts,g,R,sel):
    if sel.sum()<3: return None
    v=g[sel]; c=np.concatenate([[0.0],np.cumsum(v)])
    gt=R[sel,C["gross_total"]]
    return {"n":int(sel.sum()),"mean":float(v.mean()),
            "sharpe":float(v.mean()/v.std(ddof=1)*np.sqrt(APY)) if v.std(ddof=1)>0 else float("nan"),
            "se_sharpe":float(np.sqrt(2190.0/sel.sum())),
            "maxdd":float(np.max(np.maximum.accumulate(c)-c)),
            "turnover":float(R[sel,C["turnover"]].mean()),
            "cost":float((R[sel,C["cost_ex"]]/gt).mean()),
            "carry":float((R[sel,C["carry_ex"]]/gt).mean()),
            "pnl":float((R[sel,C["pnl_ex"]]/gt).mean()),
            "gross":float(gt.mean())}
if __name__=="__main__":
    A0P="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
    A0P2="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s2027.npz"
    t0,gt0,R0=load(A0P,"d30_n2_c42_rec"); g0=R0[:,C["net_ex"]]/gt0
    t0b,gt0b,R0b=load(A0P2,"d30_n2_c42_rec"); g0b=R0b[:,C["net_ex"]]/gt0b
    # reference sleeve: round-1 ORTH amihud
    AM=np.load("/workspace/uplift_2026-09-11/trackD_v4/SL_ORTH_f_amihud_24h__p.npz",allow_pickle=True)
    Ram=AM["rec"]; tam=np.round(np.asarray(Ram[:,0],float)).astype(np.int64)
    gam=Ram[:,C["net_ex"]]/Ram[:,C["gross_total"]]
    files=sorted(glob.glob("/workspace/uplift_2026-09-11/r2/arms/*.npz"))
    # --- LOBFULL span: anchors where EVERY r2 arm has strictly positive gross (the LOB book actually trades)
    # DEFECT FOUND 2026-09-11 (round 2): w10_health.w3_at line 166 returns [1/3,1/3,1/3] for the first
    # LOOK=900 anchors, IGNORING the LEGS mask. So rows 0..899 of EVERY sleeve arm are a three-leg
    # king+rev24+signal book, not the standalone sleeve. For a LOB arm the injected score is entirely NaN
    # there, so those 900 anchors carry +0.6333 bps/anchor of pure king+rev24 P&L with zero sleeve content.
    # Sleeve spans are therefore restricted to w3_fund == 1.0 (LEGS=001 actually in force).
    # span FROZEN from the 34 tranche-1 arms (freeze_span.py) so every later arm is judged on the SAME anchors
    LOBTS=np.load("/workspace/uplift_2026-09-11/r2/LOBTS_frozen.npy")
    span={"first":int(LOBTS[0]),"last":int(LOBTS[-1]),"n":int(len(LOBTS))}
    print("LOBFULL span:",span,flush=True)
    LOBSET=set(int(x) for x in LOBTS)
    def selmask(ts,lo,hi,lobonly=True):
        m=(ts>=lo)&(ts<hi)
        if lobonly: m=m&np.array([int(x) in LOBSET for x in ts])
        return m
    out={"span":span,"K_declared":32,"arms":{}}
    # baseline A0 on LOBFULL and on its own full cycle
    b={}
    b["A0_LOBFULL"]=stats(t0,g0,R0,selmask(t0,FULL[0],FULL[1]))
    b["A0_LOBFULL_s2027"]=stats(t0b,g0b,R0b,selmask(t0b,FULL[0],FULL[1]))
    b["A0_TRUEFULL"]=stats(t0,g0,R0,(t0>=FULL[0])&(t0<FULL[1]))
    _pw=np.arange(len(t0))>=900
    b["A0_TRUEFULL_postwarm"]=stats(t0,g0,R0,_pw&(t0>=FULL[0])&(t0<FULL[1]))
    b["AMI_TRUEFULL_postwarm"]=stats(tam,gam,Ram,(np.arange(len(tam))>=900)&(tam>=FULL[0])&(tam<FULL[1]))
    b["AMI_LOBFULL_postwarm"]=stats(tam,gam,Ram,(np.arange(len(tam))>=900)&selmask(tam,FULL[0],FULL[1]))
    b["A0_frozen"]=stats(t0,g0,R0,selmask(t0,*FROZEN))
    for y,(lo,hi) in YRS.items(): b["A0_"+y]=stats(t0,g0,R0,selmask(t0,lo,hi))
    m=selmask(t0,FULL[0],FULL[1]); b["A0_LOBFULL_ci"]=boot(g0[m],t0[m]//86400,0)
    # amihud reference on LOBFULL
    b["AMI_LOBFULL"]=stats(tam,gam,Ram,selmask(tam,FULL[0],FULL[1]))
    b["AMI_TRUEFULL"]=stats(tam,gam,Ram,(tam>=FULL[0])&(tam<FULL[1]))
    out["baseline"]=b
    k=1
    for f in files:
        tag=os.path.basename(f)[:-4]
        ts,gt,R=load(f); g=R[:,C["net_ex"]]/np.where(gt>1e-12,gt,np.nan)
        _ok=(R[:,C["w3_fund"]]>0.999)&(gt>1e-12)
        ts=ts[_ok]; gt=gt[_ok]; R=R[_ok]; g=g[_ok]
        e={}
        for w,(lo,hi) in [("LOBFULL",FULL),("frozen",FROZEN),("2024on",W24)]+list(YRS.items()):
            e[w]=stats(ts,np.nan_to_num(g),R,selmask(ts,lo,hi))
        e["stress"]=stats(ts,np.nan_to_num(g),R,(ts>=STRESS[0])&(ts<STRESS[1])&(gt>1e-12))
        m=selmask(ts,FULL[0],FULL[1])
        e["ci95"]=boot(g[m],ts[m]//86400,k); k+=1
        # correlations on the LOBFULL anchor set
        for nm,(tb,gb) in [("corr_A0",(t0,g0)),("corr_A0_s2027",(t0b,g0b)),("corr_AMI",(tam,gam))]:
            ca,ia,ib=np.intersect1d(ts,tb,return_indices=True)
            s2=np.array([int(x) in LOBSET for x in ca])&(ca>=FULL[0])&(ca<FULL[1])
            e[nm]=float(np.corrcoef(g[ia[s2]],gb[ib[s2]])[0,1]) if s2.sum()>10 else None
        # paired blend with A0 at equal gross on LOBFULL
        ca,ia,ib=np.intersect1d(ts,t0,return_indices=True)
        s2=np.array([int(x) in LOBSET for x in ca])&(ca>=FULL[0])&(ca<FULL[1])
        gb=0.5*g[ia[s2]]+0.5*g0[ib[s2]]; v=gb
        e["blend50"]={"mean":float(v.mean()),"sharpe":float(v.mean()/v.std(ddof=1)*np.sqrt(APY))}
        d=g[ia[s2]]-g0[ib[s2]]
        e["carry_frac"]=(e["LOBFULL"]["carry"]/e["LOBFULL"]["mean"]) if e["LOBFULL"] and e["LOBFULL"]["mean"]!=0 else None
        out["arms"][tag]=e
    json.dump(out,open("/workspace/uplift_2026-09-11/r2/JUDGE_r2.json","w"),indent=1)
    print("judged",len(files))

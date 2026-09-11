"""Is the LOB depth-level sleeve ADDITIVE to the round-1 Amihud sleeve, or the same bet re-expressed?
Equal-gross book blends on the frozen LOBFULL anchor set. Paired day-block bootstrap vs A0."""
import numpy as np, calendar, os, json
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL=(T(2022,1,1),T(2026,8,10,20)+1)
L=np.load("/workspace/uplift_2026-09-11/r2/LOBTS_frozen.npy")
Ls=set(int(x) for x in L)
def series(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=A[key] if key in A.files else A["d30_n2_c42_rec"]
    ts=np.round(R[:,0].astype(float)).astype(np.int64)
    ok=(R[:,C["w3_fund"]]>0.999)&(R[:,C["gross_total"]]>1e-12) if key=="rec" else (R[:,C["gross_total"]]>1e-12)
    ts=ts[ok]; R=R[ok]
    g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
    m=np.array([int(x) in Ls for x in ts])&(ts>=FULL[0])&(ts<FULL[1])
    return ts[m],g[m]
tA,gA=series("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
tM,gM=series("/workspace/uplift_2026-09-11/trackD_v4/SL_ORTH_f_amihud_24h__p.npz")
tD,gD=series("/workspace/uplift_2026-09-11/r2/arms/R2_DIAG_ORTH_R1MEAN__m.npz")
tV,gV=series("/workspace/uplift_2026-09-11/r2/arms/R2_LIVOL__p.npz")
assert np.array_equal(tA,tM) and np.array_equal(tA,tD) and np.array_equal(tA,tV), (len(tA),len(tM),len(tD),len(tV))
days=tA//86400
def sh(v): return float(v.mean()/v.std(ddof=1)*np.sqrt(APY))
def boot(d,k):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=d,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5))
print("n=%d  span frozen LOBFULL"%len(tA))
print("pairwise book-return correlations:")
for a,b,na,nb in [(gM,gD,"ORTH_amihud","ORTH_LOBdepth"),(gM,gV,"ORTH_amihud","LIVOL"),(gD,gV,"ORTH_LOBdepth","LIVOL"),(gA,gM,"A0","ORTH_amihud"),(gA,gD,"A0","ORTH_LOBdepth"),(gA,gV,"A0","LIVOL")]:
    print("   corr(%-13s, %-13s) = %+.3f"%(na,nb,float(np.corrcoef(a,b)[0,1])))
print()
print("standalone: A0 %+.3f/%.2f  AMI %+.3f/%.2f  DEPTH %+.3f/%.2f  LIVOL %+.3f/%.2f"%(
    gA.mean(),sh(gA),gM.mean(),sh(gM),gD.mean(),sh(gD),gV.mean(),sh(gV)))
print()
print("equal-gross blends into A0 (w = sleeve weight):")
k=800
for name,legs in [("A0+AMI",[gM]),("A0+DEPTH",[gD]),("A0+LIVOL",[gV]),
                  ("A0+AMI+DEPTH",[gM,gD]),("A0+AMI+LIVOL",[gM,gV]),("A0+AMI+DEPTH+LIVOL",[gM,gD,gV])]:
    for w in (0.25,0.5):
        s=np.mean(legs,axis=0); gb=(1-w)*gA+w*s; d=gb-gA
        lo,hi=boot(d,k); k+=1
        print("   %-20s w=%.2f  Sharpe %+.2f (A0 %+.2f)  dSharpe %+.2f  dmean %+.4f  CI95 [%+.3f,%+.3f]%s"%(
            name,w,sh(gb),sh(gA),sh(gb)-sh(gA),d.mean(),lo,hi," *" if lo>0 else ""))

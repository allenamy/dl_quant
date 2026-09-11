import numpy as np, calendar, os
APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
SPAN={"F23":(T(2023,1,1),T(2026,8,10,20)+1),"F24":(T(2024,1,1),T(2026,8,10,20)+1),
      "FROZEN":(T(2025,3,1),T(2026,8,10,20)+1),"y2026":(T(2026,1,1),T(2026,8,10,20)+1),
      "y2023":(T(2023,1,1),T(2024,1,1))}
HC="/workspace/review_scratch/health_check"; U="/workspace/uplift_2026-09-11"
A={}
def ld(k,p,key=None):
    if not os.path.exists(p): print("MISSING",k,p); return
    Z=np.load(p,allow_pickle=True); kk=key if key else ("rec" if "rec" in Z.files else "d30_n2_c42_rec")
    R=np.asarray(Z[kk],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
    ts=np.round(R[:,ix["ts"]]).astype(np.int64)
    g=np.where(R[:,ix["gross_total"]]>0,R[:,ix["net_ex"]]/np.maximum(R[:,ix["gross_total"]],1e-12),np.nan)
    A[k]=(ts,g,np.abs(R[:,ix["w3_rev24"]])>=1e-9)
ld("A0",HC+"/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
ld("XIB",U+"/infra2/arms/w10_ablation_series_V4_XIBLAG50_dyn_s42.npz","d30_n2_c42_rec")
ld("RS",U+"/r3_integrate/out/RS_RESID_SHARPE_s42_STD.npz")
ld("RS2027",U+"/r3_integrate/out/RS_RESID_SHARPE_s2027_STD.npz")
ld("A0_X1",U+"/infra1_cost/out/IB_PAR_X1_s42.npz")
ld("XIB_X1",U+"/infra1_cost/out/IB_LAG50_X1_s42.npz")
ld("RS_X1",U+"/r3_integrate/out/RS_RESID_SHARPE_s42_X1.npz")
ld("A0_2027",HC+"/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s2027.npz","d30_n2_c42_rec")
ld("XIB_2027",U+"/infra2/arms/w10_ablation_series_V4_XIBLAG50_dyn_s2027.npz","d30_n2_c42_rec")
def ser(k,w):
    ts,g,warm=A[k]; lo,hi=SPAN[w]; m=(ts>=lo)&(ts<hi)&np.isfinite(g)&(~warm); return ts[m],g[m]
def align(ks,w):
    S=[ser(k,w) for k in ks]; c=S[0][0]
    for t,_ in S[1:]: c=np.intersect1d(c,t)
    return c,[g[np.searchsorted(t,c)] for t,g in S]
def SR(v): return v.mean()/v.std(ddof=1)*np.sqrt(APY)
def dSR_ci(vA,vB,days,k,B=2000):
    """paired block bootstrap of SR(B)-SR(A)"""
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    grp=[np.nonzero(inv==z)[0] for z in range(nd)]; idx=rng.integers(0,nd,size=(B,nd)); o=[]
    for r in range(B):
        s=np.concatenate([grp[z] for z in idx[r]]); a=vA[s]; b=vB[s]
        if a.std(ddof=1)>0 and b.std(ddof=1)>0: o.append(SR(b)-SR(a))
    o=np.array(o); return float(np.percentile(o,2.5)),float(np.percentile(o,97.5)),float((o>0).mean())
print("### MARGINAL CONTRIBUTION OF RESID_SHARPE (equal-gross blend), paired block bootstrap")
print("%-6s %-16s %-7s %6s %8s %8s %8s %9s %9s %7s"%("cost","base","win","n","SR_base","SR_+RS","dSR","CI95lo","CI95hi","p>0"))
kk=1200
for cost,sfx in (("STD",""),("X1","_X1")):
    for base in (["XIB"],["A0"],["A0","XIB"]):
        bk=[b+sfx for b in base]; rk="RS"+sfx
        if any(x not in A for x in bk+[rk]): print("skip",base,cost); continue
        for w in ["F23","y2023","F24","FROZEN","y2026"]:
            c,V=align(bk+[rk],w)
            vb=np.mean(V[:-1],axis=0); va=np.mean(V,axis=0)
            lo,hi,p=dSR_ci(vb,va,c//86400,kk); kk+=1
            print("%-6s %-16s %-7s %6d %+8.3f %+8.3f %+8.3f %+9.3f %+9.3f %7.3f"%(
                cost,"+".join(base),w,len(c),SR(vb),SR(va),SR(va)-SR(vb),lo,hi,p))
    print()
print("### SEED 2027 CROSS-CHECK (same-seed pairing), STD")
for w in ["F23","y2023","F24","FROZEN","y2026"]:
    c,V=align(["XIB_2027","RS2027"],w); vb=V[0]; va=0.5*V[0]+0.5*V[1]
    lo,hi,p=dSR_ci(vb,va,c//86400,kk); kk+=1
    print("  XIB_s2027 -> +RS_s2027 %-7s n=%5d %+7.3f -> %+7.3f  d %+7.3f CI95[%+7.3f,%+7.3f] p %.3f"%(w,len(c),SR(vb),SR(va),SR(va)-SR(vb),lo,hi,p))

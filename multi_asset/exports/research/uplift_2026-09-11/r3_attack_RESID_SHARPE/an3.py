import numpy as np, calendar, os
APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
SPAN={"F23":(T(2023,1,1),T(2026,8,10,20)+1),"F24":(T(2024,1,1),T(2026,8,10,20)+1),
      "F25":(T(2025,1,1),T(2026,8,10,20)+1),"FROZEN":(T(2025,3,1),T(2026,8,10,20)+1),
      "y2023":(T(2023,1,1),T(2024,1,1)),"y2026":(T(2026,1,1),T(2026,8,10,20)+1)}
HC="/workspace/review_scratch/health_check"; U="/workspace/uplift_2026-09-11"
A={}
def ld(k,p,key=None):
    if not os.path.exists(p): print("MISSING",k); return
    Z=np.load(p,allow_pickle=True); kk=key if key else ("rec" if "rec" in Z.files else "d30_n2_c42_rec")
    R=np.asarray(Z[kk],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
    ts=np.round(R[:,ix["ts"]]).astype(np.int64)
    g=np.where(R[:,ix["gross_total"]]>0,R[:,ix["net_ex"]]/np.maximum(R[:,ix["gross_total"]],1e-12),np.nan)
    A[k]=(ts,g,np.abs(R[:,ix["w3_rev24"]])>=1e-9)
for t in ["STD","X1"]:
    sfx="" if t=="STD" else "_"+t
    ld("RS42"+sfx,U+"/r3_integrate/out/RS_RESID_SHARPE_s42_%s.npz"%t)
    ld("RS2027"+sfx,U+"/r3_integrate/out/RS_RESID_SHARPE_s2027_%s.npz"%t)
ld("A042",HC+"/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
ld("XIB42",U+"/infra2/arms/w10_ablation_series_V4_XIBLAG50_dyn_s42.npz","d30_n2_c42_rec")
ld("A042_X1",U+"/infra1_cost/out/IB_PAR_X1_s42.npz")
ld("XIB42_X1",U+"/infra1_cost/out/IB_LAG50_X1_s42.npz")
def ser(k,w):
    ts,g,warm=A[k]; lo,hi=SPAN[w]; m=(ts>=lo)&(ts<hi)&np.isfinite(g)&(~warm)
    return ts[m],g[m]
def SR(v): return v.mean()/v.std(ddof=1)*np.sqrt(APY)
def blkSR(v,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    grp=[np.nonzero(inv==z)[0] for z in range(nd)]; idx=rng.integers(0,nd,size=(B,nd)); o=[]
    for r in range(B):
        x=v[np.concatenate([grp[z] for z in idx[r]])]
        if x.std(ddof=1)>0: o.append(x.mean()/x.std(ddof=1)*np.sqrt(APY))
    return np.array(o)
print("### A. DROPPING 2023 (the year the programme closed as a dead axis)")
print("%-12s %-6s %6s %9s %8s %9s"%("arm","win","n","g_mean","SR","SE(SR)"))
for a in ["A042","RS42","RS2027","XIB42"]:
    for w in ["F23","F24","F25","FROZEN"]:
        ts,g=ser(a,w); print("%-12s %-6s %6d %+9.4f %+8.3f %9.3f"%(a,w,len(g),g.mean(),SR(g),np.sqrt(2190.0/len(g))))
print("\n### B. EQUAL-GROSS 50/50 PORTFOLIOS, my own series, post-warm")
def port(ks,w):
    S=[ser(k,w) for k in ks]
    c=S[0][0]
    for t,_ in S[1:]: c=np.intersect1d(c,t)
    V=[]
    for t,g in S:
        ii=np.searchsorted(t,c); V.append(g[ii])
    return c,np.mean(V,axis=0)
kk=900
for cost,sfx in (("STD",""),("X1","_X1")):
    for ks,nm in ((["XIB42"+sfx,"RS42"+sfx],"XIB+RS"),(["A042"+sfx,"RS42"+sfx],"A0+RS"),
                  (["A042"+sfx,"XIB42"+sfx],"A0+XIB"),(["A042"+sfx,"XIB42"+sfx,"RS42"+sfx],"A0+XIB+RS")):
        if any(k not in A for k in ks): print("  skip",nm,cost); continue
        for w in ["F23","F24","FROZEN","y2026"]:
            c,v=port(ks,w); b=blkSR(v,c//86400,kk); kk+=1
            print("  %-4s %-12s %-7s n=%5d SR %+7.3f  CI95[%+7.3f,%+7.3f]"%(cost,nm,w,len(v),SR(v),np.percentile(b,2.5),np.percentile(b,97.5)))
    print()
print("### C. rho(RS,A0) and rho(RS,XIB) rolling by year -- stationarity of the portfolio input")
for pair in (("RS42","A042"),("RS42","XIB42")):
    for w in ["F23","F24","FROZEN","y2023","y2026"]:
        ta,ga=ser(pair[0],w); tb,gb=ser(pair[1],w)
        c,ia,ib=np.intersect1d(ta,tb,return_indices=True)
        print("  rho(%s,%s) %-7s n=%5d  %+0.4f"%(pair[0],pair[1],w,len(c),np.corrcoef(ga[ia],gb[ib])[0,1]))

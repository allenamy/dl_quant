import numpy as np, json, calendar, os
APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
SPAN={"FULL":(T(2022,1,1),T(2026,8,10,20)+1),"F23":(T(2023,1,1),T(2026,8,10,20)+1),
      "FROZEN":(T(2025,3,1),T(2026,8,10,20)+1),"EXT":(T(2026,8,11),T(2026,9,1)),
      "y2023":(T(2023,1,1),T(2024,1,1)),"y2024":(T(2024,1,1),T(2025,1,1)),
      "y2025":(T(2025,1,1),T(2026,1,1)),"y2026":(T(2026,1,1),T(2026,8,10,20)+1)}
HC="/workspace/review_scratch/health_check"; U="/workspace/uplift_2026-09-11"
ARMS={
 "A0_s42":(HC+"/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec"),
 "A0_s2027":(HC+"/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s2027.npz","d30_n2_c42_rec"),
 "XIB_s42":(U+"/infra2/arms/w10_ablation_series_V4_XIBLAG50_dyn_s42.npz","d30_n2_c42_rec"),
 "XIB_s2027":(U+"/infra2/arms/w10_ablation_series_V4_XIBLAG50_dyn_s2027.npz","d30_n2_c42_rec"),
 "AMIlag_s42":(U+"/infra1_cost/out/SL_ORTHLAG_STD_s42.npz",None),
 "AMIr1_s42":(U+"/trackD_v4/SL_ORTH_f_amihud_24h__p.npz",None),
 "RS_s42":(U+"/r3_integrate/out/RS_RESID_SHARPE_s42_STD.npz",None),
 "RS_s2027":(U+"/r3_integrate/out/RS_RESID_SHARPE_s2027_STD.npz",None),
}
for t in ("H0","X1","X2","X3"):
    ARMS["RS_s42_"+t]=(U+"/r3_integrate/out/RS_RESID_SHARPE_s42_%s.npz"%t,None)
    ARMS["RS_s2027_"+t]=(U+"/r3_integrate/out/RS_RESID_SHARPE_s2027_%s.npz"%t,None)
    ARMS["A0_s42_"+t]=(U+"/infra1_cost/out/IB_PAR_%s_s42.npz"%t,None)
    ARMS["XIB_s42_"+t]=(U+"/infra1_cost/out/IB_LAG50_%s_s42.npz"%t,None)
    ARMS["AMIlag_s42_"+t]=(U+"/infra1_cost/out/SL_ORTHLAG_%s_s42.npz"%t,None)
D={}
for k,(p,key) in ARMS.items():
    if not os.path.exists(p): print("MISSING",k,p); continue
    Z=np.load(p,allow_pickle=True)
    kk=key if key else ("rec" if "rec" in Z.files else "d30_n2_c42_rec")
    R=np.asarray(Z[kk],float); cols=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cols)}
    ts=np.round(R[:,ix["ts"]]).astype(np.int64)
    g=np.where(R[:,ix["gross_total"]]>0,R[:,ix["net_ex"]]/np.maximum(R[:,ix["gross_total"]],1e-12),np.nan)
    warm=np.abs(R[:,ix["w3_rev24"]])>=1e-9   # True while seat warm-up overrides the mask
    D[k]=dict(ts=ts,g=g,warm=warm,turn=R[:,ix["turnover"]],gt=R[:,ix["gross_total"]],ix=ix,R=R)
print("loaded",len(D),"of",len(ARMS))
def sel(k,w,postwarm=True):
    d=D[k]; lo,hi=SPAN[w]; m=(d["ts"]>=lo)&(d["ts"]<hi)&np.isfinite(d["g"])
    if postwarm: m&=~d["warm"]
    return d["ts"][m],d["g"][m],m
def blkSR(v,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    grp=[np.nonzero(inv==z)[0] for z in range(nd)]; idx=rng.integers(0,nd,size=(B,nd)); out=[]
    for r in range(B):
        x=v[np.concatenate([grp[z] for z in idx[r]])]
        if x.std(ddof=1)>0: out.append(x.mean()/x.std(ddof=1)*np.sqrt(APY))
    return np.array(out)
print("\n### 1. STANDALONE LEVELS, post-warm, STD cost")
print("%-12s %-7s %6s %9s %8s %9s %9s"%("arm","win","n","g_mean","SR","SR_CI95lo","SR_CI95hi"))
LV={}
kk=300
for a in ["A0_s42","A0_s2027","RS_s42","RS_s2027","XIB_s42","XIB_s2027","AMIlag_s42"]:
    if a not in D: continue
    for w in ["FULL","F23","FROZEN","y2023","y2024","y2025","y2026","EXT"]:
        ts,g,_=sel(a,w)
        if len(g)<30: continue
        sr=g.mean()/g.std(ddof=1)*np.sqrt(APY)
        b=blkSR(g,ts//86400,kk); kk+=1
        LV[(a,w)]=(g.mean(),sr,len(g))
        print("%-12s %-7s %6d %+9.4f %+8.3f %+9.3f %+9.3f"%(a,w,len(g),g.mean(),sr,np.percentile(b,2.5),np.percentile(b,97.5)))
print("\n### 2. RETURN-SERIES CORRELATIONS (book layer, post-warm, my own)")
def corr(a,b,w):
    if a not in D or b not in D: return None,0
    ta,ga,_=sel(a,w); tb,gb,_=sel(b,w)
    c,ia,ib=np.intersect1d(ta,tb,return_indices=True)
    if len(c)<50: return None,len(c)
    return float(np.corrcoef(ga[ia],gb[ib])[0,1]),len(c)
pairs=[("RS_s42","A0_s42"),("RS_s2027","A0_s2027"),("RS_s42","XIB_s42"),("RS_s2027","XIB_s2027"),
       ("RS_s42","AMIlag_s42"),("RS_s42","AMIr1_s42"),("RS_s42","RS_s2027"),("XIB_s42","A0_s42"),
       ("AMIlag_s42","A0_s42")]
print("%-24s %8s %8s %8s %8s %8s %8s %8s"%("pair","F23","FULL","FROZEN","y2023","y2024","y2025","y2026"))
for a,b in pairs:
    row=[]
    for w in ["F23","FULL","FROZEN","y2023","y2024","y2025","y2026"]:
        r,n=corr(a,b,w); row.append("%+.4f"%r if r is not None else "  --  ")
    print("%-24s %8s %8s %8s %8s %8s %8s"%(a+"~"+b,*row[:6]),row[6])
print("\n### 3. COST ROBUSTNESS, SAME SPAN (F23 post-warm), SR by cost model")
print("%-14s %8s %8s %8s %8s %8s   %s"%("arm","STD","H0","X1","X2","X3","dSR STD->X1"))
for base in ["RS_s42","RS_s2027","A0_s42","XIB_s42","AMIlag_s42"]:
    row={}
    for t in ["","_H0","_X1","_X2","_X3"]:
        k=base+t
        if k not in D: row[t]=None; continue
        ts,g,_=sel(k,"F23")
        row[t]=g.mean()/g.std(ddof=1)*np.sqrt(APY)
    f=lambda t:("%8.3f"%row[t]) if row.get(t) is not None else "      --"
    d=(row.get("_X1")-row.get(""))if (row.get("_X1") is not None and row.get("") is not None) else None
    print("%-14s %s %s %s %s %s   %s"%(base,f(""),f("_H0"),f("_X1"),f("_X2"),f("_X3"),
        ("%+.3f"%d) if d is not None else "--"))
print("\n### 4. TURNOVER / GROSS, F23 post-warm")
print("%-14s %10s %10s %12s"%("arm","turnover","gross","turn/gross"))
for a in ["A0_s42","RS_s42","RS_s2027","XIB_s42","AMIlag_s42"]:
    if a not in D: continue
    ts,g,m=sel(a,"F23"); d=D[a]
    print("%-14s %10.5f %10.4f %12.5f"%(a,d["turn"][m].mean(),d["gt"][m].mean(),d["turn"][m].mean()/d["gt"][m].mean()))

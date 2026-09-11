"""P3 part C: PAIRED uplift of the best deployable portfolio over A0 alone, with day-block CI."""
import numpy as np, json, calendar
U="/workspace/uplift_2026-09-11"; R=U+"/r4p3"
def rd(p):
    Z=np.load(p,allow_pickle=True); k="rec" if "rec" in Z else "d30_n2_c42_rec"
    M=np.asarray(Z[k],float); ix={str(c):i for i,c in enumerate(np.asarray(Z["cols"]).ravel())}
    ts=np.round(M[:,ix["ts"]]).astype(np.int64); gt=M[:,ix["gross_total"]]
    return ts,np.where(gt>0,M[:,ix["net_ex"]]/np.maximum(gt,1e-12),np.nan)
A={"A0_s42":U+"/r3k/arms/A0_PWR230k_s42.npz","A0_s2027":U+"/r3k/arms/A0_PWR230k_s2027.npz",
   "XIB_s42":U+"/r3k/arms/XIB_PWR230k_s42.npz","XIB_s2027":U+"/r3k/arms/XIB_PWR230k_s2027.npz",
   "AMI":R+"/arms/SL_ORTHLAG_PWR230k_s42.npz"}
D={k:rd(p) for k,p in A.items()}
T=lambda y,m,d,h=0: calendar.timegm((y,m,d,h,0,0)); HI=T(2026,8,10,20)
WARM=900; WCUT=int(D["A0_s42"][0][WARM])
SP={"FULL_pw":(WCUT,HI),"F24on":(T(2024,1,1),HI),"FROZEN":(T(2025,3,1),HI)}
ANN=np.sqrt(2190.)
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*ANN)
def com(ks,sp):
    lo,hi=SP[sp]; S=[]
    for k in ks:
        ts,g=D[k]; m=(ts>=lo)&(ts<=hi)&np.isfinite(g); m[:WARM]=False; S.append((ts[m],g[m]))
    t=S[0][0]
    for tt,_ in S[1:]: t=np.intersect1d(t,tt)
    return t,np.array([g[np.searchsorted(tt,t)] for tt,g in S])
def blocks(ts):
    d=(ts//86400).astype(np.int64); u,inv=np.unique(d,return_inverse=True)
    return [np.where(inv==i)[0] for i in range(len(u))]
def bootd(fn,ts,G,k,B=2000):
    bl=blocks(ts); rng=np.random.default_rng([20260905,k]); nb=len(bl); o=np.empty(B)
    for b in range(B): o[b]=fn(G[:,np.concatenate([bl[i] for i in rng.integers(0,nb,nb)])])
    return [round(float(np.percentile(o,2.5)),4),round(float(np.percentile(o,97.5)),4)]
O={}
for sd in ("s42","s2027"):
    for sp in SP:
        t,G=com(["A0_"+sd,"AMI","XIB_"+sd],sp)
        v=G.std(1,ddof=1)
        w2=np.array([1/v[0],1/v[1]]); w2/=w2.sum()          # A0+AMI equal-vol, fixed
        w2x=np.array([1/v[2],1/v[1]]); w2x/=w2x.sum()        # XIB+AMI equal-vol
        def f_port(X): return sr(w2[0]*X[0]+w2[1]*X[1])
        def f_d_ami(X): return sr(w2[0]*X[0]+w2[1]*X[1])-sr(X[0])
        def f_d_xib(X): return sr(X[2])-sr(X[0])
        def f_d_xibami(X): return sr(w2x[0]*X[2]+w2x[1]*X[1])-sr(X[2])
        O[f"{sd}|{sp}"]={"n":int(G.shape[1]),
          "SR_A0":round(sr(G[0]),4),"SR_AMI":round(sr(G[1]),4),"SR_XIB":round(sr(G[2]),4),
          "w_eqvol_A0_AMI":[round(float(x),4) for x in w2],
          "SR_A0+AMI":round(f_port(G),4),
          "D_A0+AMI_minus_A0":round(f_d_ami(G),4),
          "D_CI95_k0":bootd(f_d_ami,t,G,0),"D_CI95_k9":bootd(f_d_ami,t,G,9),
          "D_XIB_minus_A0":round(f_d_xib(G),4),"DX_CI95_k0":bootd(f_d_xib,t,G,0),
          "SR_XIB+AMI":round(sr(w2x[0]*G[2]+w2x[1]*G[1]),4),
          "D_XIBAMI_minus_XIB":round(f_d_xibami(G),4),"DXA_CI95_k0":bootd(f_d_xibami,t,G,0)}
json.dump(O,open(R+"/RESULT_P3C.json","w"),indent=1); print(json.dumps(O,indent=1))

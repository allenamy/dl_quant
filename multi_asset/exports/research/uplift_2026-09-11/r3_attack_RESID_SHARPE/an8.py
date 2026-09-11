"""Does the RESID term do anything? Paired block bootstrap of SR(RESID_SHARPE) - SR(SHARPE), same seed."""
import numpy as np, calendar
APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
SPAN={"F23":(T(2023,1,1),T(2026,8,10,20)+1),"F24":(T(2024,1,1),T(2026,8,10,20)+1),
      "y2023":(T(2023,1,1),T(2024,1,1)),"y2026":(T(2026,1,1),T(2026,8,10,20)+1)}
U="/workspace/uplift_2026-09-11"
def ld(p):
    Z=np.load(p,allow_pickle=True); kk="rec" if "rec" in Z.files else "d30_n2_c42_rec"
    R=np.asarray(Z[kk],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
    gt=np.maximum(R[:,ix["gross_total"]],1e-12)
    return np.round(R[:,ix["ts"]]).astype(np.int64),R[:,ix["net_ex"]]/gt,np.abs(R[:,ix["w3_rev24"]])>=1e-9
def ser(Z,w):
    lo,hi=SPAN[w]; m=(Z[0]>=lo)&(Z[0]<hi)&np.isfinite(Z[1])&(~Z[2]); return Z[0][m],Z[1][m]
def SR(v): return v.mean()/v.std(ddof=1)*np.sqrt(APY)
def dci(a,b,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    grp=[np.nonzero(inv==z)[0] for z in range(nd)]; idx=rng.integers(0,nd,size=(B,nd)); o=[]
    for r in range(B):
        s=np.concatenate([grp[z] for z in idx[r]]); x,y=a[s],b[s]
        if x.std(ddof=1)>0 and y.std(ddof=1)>0: o.append(SR(y)-SR(x))
    o=np.array(o); return float(np.percentile(o,2.5)),float(np.percentile(o,97.5)),float((o>0).mean())
k=2000
for s in ("42","2027"):
    SH=ld(U+"/r2_learned/out/SL_SHARPE_s%s.npz"%s); RS=ld(U+"/r2_learned/out/SL_RESID_SHARPE_s%s.npz"%s)
    for w in ("F23","y2023","F24","y2026"):
        ta,ga=ser(SH,w); tb,gb=ser(RS,w); c,ia,ib=np.intersect1d(ta,tb,return_indices=True)
        a,b=ga[ia],gb[ib]
        lo,hi,p=dci(a,b,c//86400,k); k+=1
        print("s%-5s %-6s n=%5d  SHARPE %+6.3f -> RESID_SHARPE %+6.3f   d %+6.3f  CI95[%+6.3f,%+6.3f]  p %.3f  rho %.3f"%(
            s,w,len(c),SR(a),SR(b),SR(b)-SR(a),lo,hi,p,np.corrcoef(a,b)[0,1]))
    print()

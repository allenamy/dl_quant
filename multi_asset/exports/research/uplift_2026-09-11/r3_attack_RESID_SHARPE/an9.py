"""Final standalone statistics for RESID_SHARPE with Bonferroni at the declared K=10 and the
ACTUAL number of SL_ arms judged (20). Level statistic g = net_ex/gross_total, day-block bootstrap."""
import numpy as np, calendar
APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
SPAN={"F23":(T(2023,1,1),T(2026,8,10,20)+1),"F24":(T(2024,1,1),T(2026,8,10,20)+1),
      "FROZEN":(T(2025,3,1),T(2026,8,10,20)+1),"y2026":(T(2026,1,1),T(2026,8,10,20)+1)}
U="/workspace/uplift_2026-09-11"
def ld(p):
    Z=np.load(p,allow_pickle=True); kk="rec" if "rec" in Z.files else "d30_n2_c42_rec"
    R=np.asarray(Z[kk],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
    gt=np.maximum(R[:,ix["gross_total"]],1e-12)
    return np.round(R[:,ix["ts"]]).astype(np.int64),R[:,ix["net_ex"]]/gt,np.abs(R[:,ix["w3_rev24"]])>=1e-9
def boot(v,days,k,B=2000):
    rng=np.random.default_rng([20260905,k]); ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(B,nd)); return S[idx].sum(1)/N[idx].sum(1)
k=3000
print("%-8s %-7s %6s %9s %8s %9s %18s %18s"%("seed","win","n","g_mean","SR","SE(SR)","CI95 level","BONF20 level"))
for s in ("42","2027"):
    Z=ld(U+"/r3_integrate/out/RS_RESID_SHARPE_s%s_STD.npz"%s)
    for w in ("F23","F24","FROZEN","y2026"):
        lo,hi=SPAN[w]; m=(Z[0]>=lo)&(Z[0]<hi)&np.isfinite(Z[1])&(~Z[2]); v=Z[1][m]
        mn=boot(v,Z[0][m]//86400,k); k+=1
        a=100*(0.05/20)/2
        print("s%-7s %-7s %6d %+9.4f %+8.3f %9.3f  [%+7.4f,%+7.4f]  [%+7.4f,%+7.4f]"%(
            s,w,m.sum(),v.mean(),v.mean()/v.std(ddof=1)*np.sqrt(APY),np.sqrt(2190.0/m.sum()),
            np.percentile(mn,2.5),np.percentile(mn,97.5),np.percentile(mn,a),np.percentile(mn,100-a)))

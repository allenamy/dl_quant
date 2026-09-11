"""Did residualisation buy anything at the SIGNAL layer? Contrast each residual family against the
raw panel column it refines, on the same anchors: rank-IC(k=0), value-IC, D10-D1 forward return."""
import numpy as np, json
R="/workspace/uplift_2026-09-11/r2_factor"; FT=R+"/feat"
P=np.load(R+"/dev/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
Y4=np.asarray(P["Y4"],np.float64); B=np.load(FT+"/_B.npy")
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
def stats(Z):
    rr=[];vv=[];tb=[]
    for i in range(Z.shape[0]):
        a=Z[i]; b=Y4[i]; ok=np.isfinite(a)&np.isfinite(b)&B[i]
        if ok.sum()<50: continue
        x=a[ok]; y=b[ok]
        rx=np.argsort(np.argsort(x)).astype(float); ry=np.argsort(np.argsort(y)).astype(float)
        rx-=rx.mean(); ry-=ry.mean(); d=np.sqrt((rx*rx).sum()*(ry*ry).sum())
        if d>0: rr.append(float((rx*ry).sum()/d))
        xc=x-x.mean(); yc=y-y.mean(); d2=np.sqrt((xc*xc).sum()*(yc*yc).sum())
        if d2>0: vv.append(float((xc*yc).sum()/d2))
        q=np.quantile(x,[0.1,0.9]); hi=y[x>=q[1]]; lo=y[x<=q[0]]
        if len(hi)>2 and len(lo)>2: tb.append(float(hi.mean()-lo.mean())*1e4)
    f=lambda a:(float(np.mean(a)),float(np.mean(a)/np.std(a,ddof=1)*np.sqrt(len(a))))
    return f(rr),f(vv),f(tb)
def col(k): return np.where(B,np.asarray(P[k],np.float64),np.nan)
PAIRS=[("RESREV_1","-f_rev_4h",-col("f_rev_4h")),
       ("RESREV_6","-f_rev_24h",-col("f_rev_24h")),
       ("RESMOM_42","f_mom_7d",col("f_mom_7d")),
       ("IVOL_42","f_vol_7d",col("f_vol_7d")),
       ("RESMAX","f_range_24h",col("f_range_24h")),
       ("AMIRESID","f_amihud_24h(lag1)",None),
       ("FUNDRESID","f_fund_ema_v1",col("f_fund_ema_v1"))]
AM=col("f_amihud_24h"); AML=np.full_like(AM,np.nan); AML[1:]=AM[:-1]
print("%-20s %11s %8s %11s %8s %9s %8s"%("signal","rankIC","t","valueIC","t","D10-D1bps","t"))
for fam,rawname,RAW in PAIRS:
    if RAW is None: RAW=np.where(B,AML,np.nan)
    for nm,M in ((fam,np.load(FT+"/"+fam+".npy").astype(np.float64)),(rawname,RAW)):
        (ri,rt),(vi,vt),(ti,tt)=stats(rz(np.where(B,M,np.nan)))
        print("%-20s %+11.5f %+8.2f %+11.5f %+8.2f %+9.2f %+8.2f"%(nm,ri,rt,vi,vt,ti,tt),flush=True)
    print("")

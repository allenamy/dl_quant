import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/trackC")
from lib import *
import numpy as np, json, time
z=np.load("/workspace/uplift_2026-09-11/trackC/cand_v4.npz")
ts=z["ts"]; u=z["u"]; n=len(u); Y=np.array([time.gmtime(int(t)).tm_year for t in ts])
def ols(y,X):
    X=np.column_stack([np.ones(len(y))]+list(X)); b,*_=np.linalg.lstsq(X,y,rcond=None)
    r=y-X@b; s2=r@r/max(len(y)-X.shape[1],1); return b,np.sqrt(np.diag(s2*np.linalg.pinv(X.T@X)))
print("== G1p INCREMENTAL: u_t ~ a + b*z(x_t) + c*z(trailU30_t); x strictly trailing, v4 ==")
print("%-24s %8s %8s %8s %7s"%("x","beta","t(b)","t(trailU)","n"))
tr=z["book_trail30"]; res={}
NAMES=["disp_bps_trail30","disp_bps_trail120","bookvol_trail30","bookvol_trail60","bookvol_trail120",
       "turnover_trail30","fundema_sd_trail30","fund_sd_trail30","comov_trail30","breadth_pos_trail120",
       "sigfund_p30_ref2y","sigfund_p60_ref1y","disp_p60_ref6m","disp_p30_ref6m","legfund_trail120"]
for name in NAMES:
    x=z[name]; m=np.isfinite(x)&np.isfinite(u)&np.isfinite(tr)
    xs=(x[m]-x[m].mean())/x[m].std(); trs=(tr[m]-tr[m].mean())/tr[m].std()
    b,se=ols(u[m],[xs,trs])
    print("%-24s %+8.4f %+8.2f %+8.2f %7d"%(name,b[1],b[1]/se[1],b[2]/se[2],m.sum()))
    res[name]=dict(beta=float(b[1]),t=float(b[1]/se[1]),n=int(m.sum()))
print()
def buckets(name,nb=5,label=""):
    x=z[name]; m=np.isfinite(x)&np.isfinite(u)
    q=np.percentile(x[m],np.linspace(0,100,nb+1))
    print("-- %s %s  cuts=%s"%(name,label,[round(float(v),3) for v in q]))
    print("%4s %6s %11s %8s %9s %8s %11s"%("bkt","n","bps/anch","SE","Sharpe","SE(Sh)","cum %gross"))
    out=[]
    for i in range(nb):
        sel=m&(x>=q[i])&((x<q[i+1]) if i<nb-1 else (x<=q[i+1]))
        y=u[sel]
        if len(y)<20: continue
        s=sharpe(y)
        print("%4d %6d %+11.4f %8.4f %+9.2f %8.2f %+11.1f"%(i+1,len(y),y.mean(),y.std(ddof=1)/np.sqrt(len(y)),s,se_sharpe(len(y)),y.sum()/100))
        out.append(dict(b=i+1,n=int(len(y)),mean=float(y.mean()),sharpe=float(s)))
    return out
SH={}
for nm in ("disp_bps_trail30","bookvol_trail30","bookvol_trail120","disp_p60_ref6m","sigfund_p30_ref2y","fundema_sd_trail30"):
    SH[nm]=buckets(nm); print()
print("== WITHIN-YEAR: bottom-quintile-of-year vs rest (disp_bps_trail30, same-era by construction) ==")
print("%6s %7s %11s %9s %7s %11s %9s"%("year","n","botQ bps","botQ Sh","nbot","rest bps","rest Sh"))
x=z["disp_bps_trail30"]
for y in range(2022,2027):
    m=(Y==y)&np.isfinite(x)&np.isfinite(u)
    if m.sum()<100: continue
    cut=np.percentile(x[m],20); lo=m&(x<=cut); hi=m&(x>cut)
    print("%6d %7d %+11.4f %+9.2f %7d %+11.4f %+9.2f"%(y,m.sum(),u[lo].mean(),sharpe(u[lo]),lo.sum(),u[hi].mean(),sharpe(u[hi])))
json.dump({"incremental":res,"buckets":SH},open("/workspace/uplift_2026-09-11/trackC/shape_v4.json","w"),indent=1)

import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
import numpy as np
z=np.load(f"{OUT}/cand.npz"); ts=z['ts']; u=z['u']; n=len(u)
Y=np.array([time.gmtime(int(t)).tm_year for t in ts])
def ols(y,X):
    X=np.column_stack([np.ones(len(y))]+list(X)); b,*_=np.linalg.lstsq(X,y,rcond=None)
    r=y-X@b; s2=r@r/max(len(y)-X.shape[1],1)
    return b, np.sqrt(np.diag(s2*np.linalg.pinv(X.T@X)))
# G1 strict-intent test: does x_t predict u_t AFTER controlling for trailing book P&L?
print("== G1' INCREMENTAL LEAD TEST: u_t ~ a + b*x_t + c*trailU30_t  (x strictly trailing) ==")
print("%-24s %8s %8s %8s %8s" % ("x","beta","t(beta)","t(trailU)","n"))
tr=z['book_trail30']
res={}
for name in ('disp_bps_trail30','comov_trail30','fund_sd_trail30','fundema_sd_trail30','turnover_trail30',
             'bookvol_trail30','legfund_trail120','book_trail120','breadth_pos_trail30','share_new90_trail30',
             'sigfund_p30_ref2y','sigfund_p30_ref1y'):
    x=z[name]; m=np.isfinite(x)&np.isfinite(u)&np.isfinite(tr)
    xs=(x[m]-x[m].mean())/x[m].std()
    b,se=ols(u[m],[xs,(tr[m]-tr[m].mean())/tr[m].std()])
    print("%-24s %+8.4f %+8.2f %+8.2f %8d" % (name,b[1],b[1]/se[1],b[2]/se[2],m.sum()))
    res[name]=dict(beta=float(b[1]),t=float(b[1]/se[1]),n=int(m.sum()))
print()
# shape: quintiles of key inputs
def buckets(name, nb=5):
    x=z[name]; m=np.isfinite(x)&np.isfinite(u)
    q=np.percentile(x[m],np.linspace(0,100,nb+1))
    print(f"-- {name} quintiles (cuts {[round(v,3) for v in q]})")
    print("%6s %6s %10s %8s %8s %10s" % ("bkt","n","bps/anch","SE","Sharpe","cum %gross"))
    for i in range(nb):
        sel=m&(x>=q[i])&((x<q[i+1]) if i<nb-1 else (x<=q[i+1]))
        y=u[sel]
        if len(y)<20: continue
        print("%6d %6d %+10.4f %8.4f %+8.2f %+10.1f" % (i+1,len(y),y.mean(),y.std(ddof=1)/np.sqrt(len(y)),ann_sharpe(y),y.sum()/100))
for nm in ('disp_bps_trail30','comov_trail30','fundema_sd_trail30','bookvol_trail30'):
    buckets(nm); print()
json.dump(res, open(f"{OUT}/g1_incremental.json","w"), indent=1)

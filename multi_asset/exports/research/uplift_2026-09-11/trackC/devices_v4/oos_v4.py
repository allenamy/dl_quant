import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/trackC")
from lib import *
import numpy as np, json, time, calendar
z=np.load("/workspace/uplift_2026-09-11/trackC/cand_v4.npz"); Pz=np.load("/workspace/uplift_2026-09-11/trackC/pct_v4.npz")
ts=z["ts"]; u=z["u"]; n=len(u); Y=np.array([time.gmtime(int(t)).tm_year for t in ts])
def T(*x): return calendar.timegm(x+(0,)*(6-len(x)))
print("== (B) SAME-ERA PERCENTILE QUINTILES vs NEXT-ANCHOR u  (does within-era timing exist at all?) ==")
for key in ("bookvol_1y","disp_1y","sigfund_1y","fundema_1y","bookvol_6m","disp_6m"):
    p=Pz[key]; m=np.isfinite(p)&np.isfinite(u)
    print("-- %-12s n=%d  span %s..%s"%(key,m.sum(),time.strftime("%Y-%m",time.gmtime(int(ts[m][0]))),time.strftime("%Y-%m",time.gmtime(int(ts[m][-1])))))
    print("     %4s %6s %10s %8s %8s"%("bkt","n","bps/anch","SE","Sharpe"))
    for i in range(5):
        lo,hi=i/5,(i+1)/5
        s=m&(p>=lo)&((p<hi) if i<4 else (p<=hi)); y=u[s]
        if len(y)<50: continue
        print("     %4d %6d %+10.4f %8.4f %+8.2f"%(i+1,len(y),y.mean(),y.std(ddof=1)/np.sqrt(len(y)),sharpe(y)))
print()
print("== (A) OUT-OF-SAMPLE-IN-TIME: select best dSharpe on 2022-01..2024-12, apply 2025-01..2026-08 ==")
R=json.load(open("/workspace/uplift_2026-09-11/trackC/eval_v4.json"))
COST=3.52
def gseries(src,rl,th,L):
    p=Pz[f"{src}_{rl}"]; g=np.ones(n); cl=ch=0; cur=1.0
    for t in range(n):
        if not np.isfinite(p[t]): g[t]=cur; continue
        if p[t]<th: cl+=1; ch=0
        else: ch+=1; cl=0
        if cur==1.0 and cl>=L: cur=0.5
        elif cur==0.5 and ch>=L: cur=1.0
        g[t]=cur
    return g,p
def perf(g,span):
    gg=g[span]; uu=u[span]
    dg=np.abs(np.diff(np.concatenate([[1.0],gg]))); rr=gg*uu-COST*dg
    return float(rr.mean()),sharpe(rr),maxdd(np.cumsum(rr)),int(len(rr))
SPL=T(2025,1,1)
IN=(ts<SPL); OUT=(ts>=SPL)
rows=[]
for r in R:
    g,p=gseries(r["src"],r["ref"],r["th"],r["L"])
    fi=np.isfinite(p)&np.isfinite(u)
    si=IN&fi; so=OUT&fi
    if si.sum()<800 or so.sum()<800: continue
    mi,shi,ddi,ni=perf(g,si); bmi,bshi,bddi,_=perf(np.ones(n),si)
    mo,sho,ddo,no=perf(g,so); bmo,bsho,bddo,_=perf(np.ones(n),so)
    kk = "%s_%s_th%s_L%s" % (r["src"], r["ref"], r["th"], r["L"])
    rows.append(dict(k=kk,
        dIN=shi-bshi,dOUT=sho-bsho,ddIN=1-ddi/bddi,ddOUT=1-ddo/bddo,nIN=ni,nOUT=no,
        mOUT=100*mo/bmo if bmo!=0 else float("nan")))
rows.sort(key=lambda r:-r["dIN"])
print("  selected on IN-sample (2022..2024), top 10 by dSharpe_IN:")
print("  %-28s %8s %8s %8s %8s %7s"%("variant","dSh_IN","dSh_OUT","ddRed_IN","ddRed_OUT","mean%OUT"))
for r in rows[:10]:
    print("  %-28s %+8.3f %+8.3f %+8.1f %+8.1f %7.1f"%(r["k"],r["dIN"],r["dOUT"],100*r["ddIN"],100*r["ddOUT"],r["mOUT"]))
a=np.array([r["dIN"] for r in rows]); b=np.array([r["dOUT"] for r in rows])
print("  corr(dSharpe_IN, dSharpe_OUT) = %+0.3f over %d variants"%(float(np.corrcoef(a,b)[0,1]),len(rows)))
print("  top-10-by-IN mean dSharpe_OUT = %+0.3f ; all-variant mean dSharpe_OUT = %+0.3f"%(np.mean([r["dOUT"] for r in rows[:10]]),b.mean()))
json.dump(rows,open("/workspace/uplift_2026-09-11/trackC/oos_v4.json","w"),indent=1,default=float)

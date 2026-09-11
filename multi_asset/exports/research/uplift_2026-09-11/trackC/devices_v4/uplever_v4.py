import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/trackC")
from lib import *
import numpy as np, json, time, calendar
z=np.load("/workspace/uplift_2026-09-11/trackC/cand_v4.npz"); Pz=np.load("/workspace/uplift_2026-09-11/trackC/pct_v4.npz")
ts=z["ts"]; u=z["u"]; n=len(u); Y=np.array([time.gmtime(int(t)).tm_year for t in ts])
def T(*x): return calendar.timegm(x+(0,)*(6-len(x)))
COST=3.52; SPL=T(2025,1,1); FW=(T(2025,3,1),T(2026,8,10,20))
def daily(x,tt):
    dk=np.array([int(t)//86400 for t in tt]); o=[]
    for d in np.unique(dk):
        s=dk==d
        if s.sum()==6: o.append(x[s].sum())
    return np.array(o)
def perf(g,span):
    gg=g[span]; uu=u[span]; tt=ts[span]; yy=Y[span]
    dg=np.abs(np.diff(np.concatenate([[gg[0]],gg]))); rr=gg*uu-COST*dg
    dd=daily(rr,tt); navd=2.0*dd/1e4
    cv=float(np.sort(dd)[:max(1,int(round(0.05*len(dd))))].mean())
    return dict(n=int(len(rr)),mean=float(rr.mean()),sharpe=sharpe(rr),se=se_sharpe(len(rr)),
        maxdd=maxdd(np.cumsum(rr)),cvar5=cv,worst_day=float(dd.min()),breach=float((navd<-0.04).mean()),
        gm=float(gg.mean()),dg=float(dg.mean()),cost=float(COST*dg.mean()),
        yr={int(y):round(sharpe(rr[yy==y]),3) for y in np.unique(yy) if (yy==y).sum()>100})
print("== UP-LEVER / CAPACITY-NEUTRAL TILT, same-era percentile p (strictly trailing), walk-forward ==")
print("   LIN g=GLO+(GHI-GLO)*p  (no tuned threshold) | BIN g=GHI if p>=0.5 else GLO")
OUT=[]; K=0
for src in ("bookvol","disp","sigfund","fundema"):
  for rl in ("1y","6m","2y"):
    p=Pz["%s_%s"%(src,rl)]; fi=np.isfinite(p)&np.isfinite(u)
    if fi.sum()<1500: continue
    for form in ("LIN","BIN"):
      for (GLO,GHI) in ((0.7,1.3),(0.5,1.5),(0.8,1.2),(1.0,1.5)):
        K+=1
        if form=="LIN": g=np.where(fi,GLO+(GHI-GLO)*np.nan_to_num(p),1.0)
        else: g=np.where(fi,np.where(p>=0.5,GHI,GLO),1.0)
        for spanlab,span in (("FULL",fi),("IN",fi&(ts<SPL)),("OUT",fi&(ts>=SPL)),("FROZEN",fi&(ts>=FW[0])&(ts<=FW[1]))):
            if span.sum()<600: continue
            c=perf(g,span); b=perf(np.ones(n),span)
            OUT.append(dict(src=src,ref=rl,form=form,glo=GLO,ghi=GHI,span=spanlab,n=c["n"],
                sharpe=c["sharpe"],base_sharpe=b["sharpe"],d_sharpe=c["sharpe"]-b["sharpe"],
                mean=c["mean"],base_mean=b["mean"],maxdd=c["maxdd"],base_maxdd=b["maxdd"],
                cvar5=c["cvar5"],base_cvar5=b["cvar5"],breach=c["breach"],base_breach=b["breach"],
                gm=c["gm"],dg=c["dg"],cost=c["cost"],yr=c["yr"],base_yr=b["yr"]))
D={}
for r in OUT: D[(r["src"],r["ref"],r["form"],r["glo"],r["ghi"],r["span"])]=r
print("K variants =",K)
print("%-9s %-3s %-4s %-8s %8s %8s %8s %8s %8s %7s %7s"%("src","ref","form","lo-hi","dSh_FULL","dSh_IN","dSh_OUT","dSh_FROZ","mean%FUL","ddRed%","gmean"))
keys=sorted({(r["src"],r["ref"],r["form"],r["glo"],r["ghi"]) for r in OUT},
            key=lambda k:-(D.get(k+("FULL",),{}).get("d_sharpe",-9)))
for k in keys:
    f=D.get(k+("FULL",)); i=D.get(k+("IN",)); o=D.get(k+("OUT",)); fz=D.get(k+("FROZEN",))
    if f is None: continue
    print("%-9s %-3s %-4s %.1f-%.1f %8.3f %8.3f %8.3f %8.3f %8.1f %7.1f %7.3f"%(
      k[0],k[1],k[2],k[3],k[4],f["d_sharpe"],i["d_sharpe"] if i else float("nan"),
      o["d_sharpe"] if o else float("nan"), fz["d_sharpe"] if fz else float("nan"),
      100*f["mean"]/f["base_mean"], 100*(1-f["maxdd"]/f["base_maxdd"]), f["gm"]))
json.dump(OUT,open("/workspace/uplift_2026-09-11/trackC/uplever_v4.json","w"),indent=1,default=float)
kk=[k for k in keys if k+("IN",) in D and k+("OUT",) in D]
a=np.array([D[k+("IN",)]["d_sharpe"] for k in kk]); b=np.array([D[k+("OUT",)]["d_sharpe"] for k in kk])
print("corr(dSh_IN,dSh_OUT) = %+0.3f over %d"%(float(np.corrcoef(a,b)[0,1]),len(a)))
print("frac dSh_OUT>0 = %.2f ; median dSh_OUT = %+0.3f ; median dSh_FULL = %+0.3f"%((b>0).mean(),np.median(b),np.median([D[k+("FULL",)]["d_sharpe"] for k in keys])))

import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/trackC")
from lib import *
import numpy as np, json, time
z=np.load("/workspace/uplift_2026-09-11/trackC/cand_v4.npz"); Pz=np.load("/workspace/uplift_2026-09-11/trackC/pct_v4.npz")
ts=z["ts"]; u=z["u"]; n=len(u); Y=np.array([time.gmtime(int(t)).tm_year for t in ts])
COST=3.52; RNG=np.random.default_rng(20260911); BB=30; BN=2000
def daily(x,tt):
    dk=np.array([int(t)//86400 for t in tt]); o=[]
    for d in np.unique(dk):
        s=dk==d
        if s.sum()==6: o.append(x[s].sum())
    return np.array(o)
def worst_month(rr,tt):
    mk=np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in tt])
    return float(min(rr[mk==m].sum() for m in np.unique(mk)))
def ev(g,span,lab):
    gg=g[span]; uu=u[span]; tt=ts[span]; yy=Y[span]
    dg=np.abs(np.diff(np.concatenate([[1.0],gg]))); cost=COST*dg
    rr=gg*uu-cost; dd=daily(rr,tt); cum=np.cumsum(rr); navd=2.0*dd/1e4
    cv=float(np.sort(dd)[:max(1,int(round(0.05*len(dd))))].mean())
    return dict(label=lab,n=int(len(rr)),mean=float(rr.mean()),sharpe=sharpe(rr),se=se_sharpe(len(rr)),
        maxdd=maxdd(cum),cvar5=cv,worst_day=float(dd.min()),worst_month=worst_month(rr,tt),
        breach=float((navd<-0.04).mean()),ndays=int(len(dd)),dg=float(dg.mean()),costm=float(cost.mean()),gm=float(gg.mean()),
        yr={int(y):[round(sharpe(rr[yy==y]),3),round(float(rr[yy==y].sum()/100),2)] for y in np.unique(yy) if (yy==y).sum()>100},
        _r=rr)
def boot_p(a,b):
    m=len(a); nb=m//BB; st=np.arange(0,m-BB+1); d=np.empty(BN)
    for i in range(BN):
        s=RNG.choice(st,nb); ix=(s[:,None]+np.arange(BB)[None,:]).ravel()
        d[i]=sharpe(a[ix])-sharpe(b[ix])
    return float((d<=0).mean()), float(np.percentile(d,5)), float(np.percentile(d,95))
RES=[]; K=0
for src in ("bookvol","disp","sigfund","fundema","turn"):
    for rl in ("1y","6m","2y"):
        p=Pz[f"{src}_{rl}"]
        for th in (0.10,0.20,0.30,0.40,0.50):
            for L in (1,6,18,84):
                K+=1
                # confirmation: g=0.5 only after L consecutive anchors with p<th ; restore immediately when p>=th for L anchors
                lowf=(p<th).astype(float); lowf[~np.isfinite(p)]=np.nan
                g=np.ones(n); cl=0; ch=0; cur=1.0
                for t in range(n):
                    if not np.isfinite(p[t]): g[t]=cur; continue
                    if p[t]<th: cl+=1; ch=0
                    else: ch+=1; cl=0
                    if cur==1.0 and cl>=L: cur=0.5
                    elif cur==0.5 and ch>=L: cur=1.0
                    g[t]=cur
                span=np.isfinite(p)&np.isfinite(u)
                if span.sum()<1500: continue
                base=ev(np.ones(n),span,"base"); ctl=ev(g,span,f"{src}_{rl}_th{th}_L{L}")
                pval,lo,hi=boot_p(ctl["_r"],base["_r"])
                RES.append(dict(src=src,ref=rl,th=th,L=L,n=ctl["n"],
                    d_mean=ctl["mean"]-base["mean"], mean=ctl["mean"], base_mean=base["mean"],
                    sharpe=ctl["sharpe"], base_sharpe=base["sharpe"], d_sharpe=ctl["sharpe"]-base["sharpe"],
                    boot_p=pval, boot_lo=lo, boot_hi=hi,
                    maxdd=ctl["maxdd"], base_maxdd=base["maxdd"], dd_red=1-ctl["maxdd"]/base["maxdd"],
                    cvar5=ctl["cvar5"], base_cvar5=base["cvar5"], wm=ctl["worst_month"], base_wm=base["worst_month"],
                    breach=ctl["breach"], base_breach=base["breach"], gm=ctl["gm"], dg=ctl["dg"], costm=ctl["costm"],
                    yr=ctl["yr"], base_yr=base["yr"]))
RES.sort(key=lambda r:-r["d_sharpe"])
print("K (variants tested) =",K,"  evaluated:",len(RES))
print("%-9s %-4s %5s %4s %6s %8s %8s %8s %7s %7s %7s %7s %6s"%("src","ref","th","L","n","dSharpe","Sh","boot_p","dMean","%mean","ddRed%","dCVaR","gmean"))
for r in RES[:25]:
    print("%-9s %-4s %5.2f %4d %6d %+8.3f %8.3f %8.3f %+7.3f %6.1f%% %+7.1f %+7.3f %6.3f"%(
      r["src"],r["ref"],r["th"],r["L"],r["n"],r["d_sharpe"],r["sharpe"],r["boot_p"],r["d_mean"],
      100*r["mean"]/r["base_mean"],100*r["dd_red"],r["cvar5"]-r["base_cvar5"],r["gm"]))
json.dump([{k:v for k,v in r.items()} for r in RES],open("/workspace/uplift_2026-09-11/trackC/eval_v4.json","w"),indent=1,default=float)

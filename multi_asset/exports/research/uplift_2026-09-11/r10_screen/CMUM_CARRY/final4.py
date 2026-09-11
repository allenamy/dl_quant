"""Robustness: extra-lag causality test, worst-day forensics, per-year table, static-arm downside."""
import os,json,datetime as dt,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
W=os.path.dirname(os.path.abspath(__file__))
Z=np.load(W+"/book_inputs.npz",allow_pickle=True);K=np.load(W+"/klines_grid.npz",allow_pickle=True)
TSf=Z["TS"];D=Z["D"];R=Z["R"];H=Z["H"];A0gf=Z["A0g"];names=[str(x) for x in Z["names"]]
CMP=K["CMP"];UMP=K["UMP"];CMV=K["CMV"];UMV=K["UMV"];N,n=D.shape
def ret(P):
    r=np.full_like(P,np.nan);r[1:]=P[1:]/P[:-1]-1.0;return r
rCM=ret(CMP);rUM=ret(UMP)
cmq=np.where(np.isfinite(CMV)&np.isfinite(CMP),CMV*CMP,0.0);umq=np.nan_to_num(UMV,nan=0.0)
LIVE=np.zeros((N,n),bool);LIVE[1:]=(cmq[1:]>0)&(cmq[:-1]>0)&(umq[1:]>0)&(umq[:-1]>0)
EL=H&LIVE&np.isfinite(rCM)&np.isfinite(rUM)&(np.abs(rCM)<0.5)&(np.abs(rUM)<0.5)
CM_END=int(dt.datetime(2026,6,30,20,tzinfo=dt.timezone.utc).timestamp())
cov=(TSf<=CM_END)&(EL.sum(1)>=8);TS=TSf[cov];A0g=A0gf[cov]
CB=json.load(open(W+"/pin/costb_PWR_G230k.json"));TIER=np.array(CB["blended_bps_per_unit_turnover"])
def tier_of(q):
    t=np.full(q.shape,2,np.int64);t=np.where(q>=1e6,1,t);t=np.where(q>=5e6,0,t);return t
bpsUM=TIER[tier_of(umq)];bpsCM=TIER[tier_of(cmq)]
Rn=np.nan_to_num(R);DR=np.nan_to_num(rCM-rUM);Dn=np.nan_to_num(D);Df=np.where(H,Dn,np.nan)
def ema_sign(k,lag=0):
    a=2.0/(k+1);E=np.zeros_like(D);prev=np.zeros(n)
    for i in range(N):
        x=np.where(np.isfinite(Df[i]),Df[i],prev);prev=(1-a)*prev+a*x;E[i]=prev
    s=np.sign(E)
    if lag>0:
        q=np.zeros_like(s);q[lag:]=s[:-lag];s=q
    return s
def book(s,cmmult=1.0):
    sg=np.where(EL,s,0.0);M=np.abs(sg).sum(1);Ms=np.where(M==0,np.nan,M)
    wl=np.nan_to_num(sg/(2.0*Ms[:,None]))
    carry=1e4*(wl*Rn).sum(1);price=1e4*(wl*DR).sum(1)
    dwl=np.abs(np.vstack([wl[:1],np.diff(wl,axis=0)]))
    return dict(carry=carry[cov],price=price[cov],gross=(carry+price)[cov],cost=(dwl*(bpsUM+cmmult*bpsCM)).sum(1)[cov],turn=(2.0*dwl.sum(1))[cov])
OUT={}
print("extra-lag causality test (B_ema360):")
for lag in (0,1,2,6):
    B=book(ema_sign(360,lag));g=B["gross"]-B["cost"]
    OUT["lag%d"%lag]=dict(net=round(float(g.mean()),4),sr=round(float(g.mean()/g.std(ddof=1)*np.sqrt(2190)),3))
    print("  lag %d anchors: net %+.4f  SR %+.3f"%(lag,g.mean(),g.mean()/g.std(ddof=1)*np.sqrt(2190)))
day=(TS//86400).astype(np.int64);ud=np.unique(day)
for tag,s in (("B_ema360",ema_sign(360)),("E_static_shortCM",-np.ones((N,n)))):
    B=book(s);g=B["gross"]-B["cost"]
    gd=np.array([g[day==d].sum() for d in ud]);car=np.array([B["carry"][day==d].sum() for d in ud]);pr=np.array([B["price"][day==d].sum() for d in ud])
    o=int(gd.argmin())
    print("\n%s worst UTC day %s : net %.3f  (carry %.3f  price/basis %.3f)  daily sd %.3f  -> %.1f sigma"%(
       tag,dt.datetime.utcfromtimestamp(int(ud[o])*86400).date(),gd[o],car[o],pr[o],gd.std(ddof=1),gd[o]/gd.std(ddof=1)))
    w5=np.argsort(gd)[:5]
    print("   5 worst days:",[(str(dt.datetime.utcfromtimestamp(int(ud[i])*86400).date()),round(float(gd[i]),2)) for i in w5])
    cum=np.cumsum(gd)
    OUT[tag]=dict(worst_day=round(float(gd.min()),3),worst_day_date=str(dt.datetime.utcfromtimestamp(int(ud[o])*86400).date()),
      worst_day_carry=round(float(car[o]),3),worst_day_price=round(float(pr[o]),3),daily_sd=round(float(gd.std(ddof=1)),3),
      worst_day_sigma=round(float(gd[o]/gd.std(ddof=1)),1),maxDD=round(float((np.maximum.accumulate(cum)-cum).max()),2),
      worst5=[[str(dt.datetime.utcfromtimestamp(int(ud[i])*86400).date()),round(float(gd[i]),2)] for i in w5])
    yr=np.array([dt.datetime.utcfromtimestamp(t).year for t in TS])
    OUT[tag]["by_year"]={int(y):dict(n=int((yr==y).sum()),net=round(float(g[yr==y].mean()),4),
       sr=round(float(g[yr==y].mean()/g[yr==y].std(ddof=1)*np.sqrt(2190)),3)) for y in sorted(set(yr.tolist()))}
    print("   by year:",json.dumps(OUT[tag]["by_year"]))
json.dump(OUT,open(W+"/STEP4_robust.json","w"),indent=1)

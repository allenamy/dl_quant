import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/trackC")
from lib import *
import numpy as np, json, time, calendar
PA="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
z=np.load(PA+"/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"].astype(float)
ts=rec[:,cols.index("ts")].astype(np.int64); u=rec[:,cols.index("net_ex")]/rec[:,cols.index("gross_total")]
W=z["d30_n2_c42_W"]
m=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=m["E_ts"].astype(np.int64); y4=m["y4"]
emap={int(t):i for i,t in enumerate(E)}
n=len(ts)
def rankz(x):
    o=np.argsort(np.argsort(x)); return (o-o.mean())/(o.std()+1e-12)
ric=np.full(n,np.nan); vic=np.full(n,np.nan)
for i in range(n):
    j=emap.get(int(ts[i]))
    if j is None: continue
    w=W[i]; yy=y4[j]
    s=(np.abs(w)>0)&np.isfinite(yy)
    if s.sum()<30: continue
    a=w[s].astype(float); b=yy[s].astype(float)
    ric[i]=float(np.corrcoef(rankz(a),rankz(b))[0,1])
    vic[i]=float(np.corrcoef(a,b)[0,1])
print("per-anchor rank-IC of the DEPLOYED BOOK's own weights vs realized y4 (v4, position/book layer)")
print("  n finite = %d / %d ; mean %+0.5f ; sd %.5f"%(np.isfinite(ric).sum(),n,np.nanmean(ric),np.nanstd(ric)))
# sanity: does IC align with u?
mm=np.isfinite(ric)&np.isfinite(u)
print("  corr(rank_IC_t, u_t) = %+0.3f  (must be strongly positive or the IC series is the wrong quantity)"%np.corrcoef(ric[mm],u[mm])[0,1])
np.savez("/root/tc/ic_v4.npz",ts=ts,u=u,ric=ric,vic=vic)
# lead-lag of trailing IC
F6=np.full(n,np.nan); B6=np.full(n,np.nan)
for t in range(n-6): F6[t]=u[t:t+6].mean()
for t in range(6,n): B6[t]=u[t-6:t].mean()
def cr(a,b):
    s=np.isfinite(a)&np.isfinite(b); return (float(np.corrcoef(a[s],b[s])[0,1]),int(s.sum())) if s.sum()>200 else (float("nan"),0)
print()
print("== G1 LEAD TEST for trailing realized IC (strictly trailing means) ==")
print("%-18s %10s %10s %10s %7s %6s"%("input","c(x,fwd6)","c(x,bwd6)","c(x,u_t)","n","leads"))
ICT={}
for K in (24,48,96,192,384):
    x=trail_mean(ric,K); ICT["ric_trail%d"%K]=x
    cf,nf=cr(x,F6); cb,_=cr(x,B6); c1,_=cr(x,u)
    print("%-18s %+10.4f %+10.4f %+10.4f %7d %6s"%("ric_trail%d"%K,cf,cb,c1,nf,abs(cf)>abs(cb)))
for K in (24,48):
    x=trail_mean(vic,K); ICT["vic_trail%d"%K]=x
    cf,nf=cr(x,F6); cb,_=cr(x,B6); c1,_=cr(x,u)
    print("%-18s %+10.4f %+10.4f %+10.4f %7d %6s"%("vic_trail%d"%K,cf,cb,c1,nf,abs(cf)>abs(cb)))
print()
print("== QUINTILES of trailing rank-IC (r48, the live ic_monitor quantity) vs NEXT-anchor u ==")
x=ICT["ric_trail48"]; s=np.isfinite(x)&np.isfinite(u)
q=np.percentile(x[s],np.linspace(0,100,6))
print("   cuts:",[round(float(v),5) for v in q])
print("   %4s %6s %11s %8s %9s"%("bkt","n","bps/anch","SE","Sharpe"))
for i in range(5):
    sel=s&(x>=q[i])&((x<q[i+1]) if i<4 else (x<=q[i+1])); y=u[sel]
    print("   %4d %6d %+11.4f %8.4f %+9.2f"%(i+1,len(y),y.mean(),y.std(ddof=1)/np.sqrt(len(y)),sharpe(y)))
print()
print("== the LIVE ic_monitor DECIDE line, applied to full history ==")
print("   rule: r48 < -0.01656 (DECIDE).  What is the book's forward return while that line is breached?")
r48=trail_mean(ric,48)
brc=r48 < -0.01656
s=np.isfinite(r48)&np.isfinite(u)
for lab,sel in (("DECIDE breached",s&brc),("not breached",s&~brc)):
    y=u[sel]; print("   %-18s n=%5d (%.1f%% of anchors)  fwd bps/anchor %+0.4f (SE %.4f)  Sharpe %+0.2f"%(lab,len(y),100*len(y)/s.sum(),y.mean(),y.std(ddof=1)/np.sqrt(len(y)),sharpe(y)))

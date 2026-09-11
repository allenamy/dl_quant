import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/trackC")
from lib import *
import numpy as np, json
d=book(); r=regime()
rmap={int(t):i for i,t in enumerate(r["ts"])}
idx=np.array([rmap.get(int(t),-1) for t in d["ts"]])
print("align: book n=%d, matched=%d, unmatched=%d"%(len(idx),(idx>=0).sum(),(idx<0).sum()))
keep=idx>=0
u=d["u"][keep]; ts=d["ts"][keep]; idx=idx[keep]; n=len(u)
REG={k:r[k][idx] for k in r if k!="ts"}
LEG={k:d[k][keep] for k in ("leg_king","leg_rev24","leg_fund","turnover","gross_total","netlong")}
CAND={}
for K in (30,60,120,240):
    CAND["book_trail%d"%K]=trail_mean(u,K); CAND["bookvol_trail%d"%K]=trail_std(u,K)
    CAND["legfund_trail%d"%K]=trail_mean(LEG["leg_fund"],K); CAND["legking_trail%d"%K]=trail_mean(LEG["leg_king"],K)
for k in ("disp_bps","breadth_pos","comov","turnover","share_new90","med_age_d","fund_med","fund_absp75","fund_sd","fundema_sd","xs_mean_bps","btc_bps","altmbtc_bps"):
    CAND[k+"_trail30"]=trail_mean(REG[k],30); CAND[k+"_trail120"]=trail_mean(REG[k],120)
    CAND[k+"_now"]=np.concatenate([[np.nan],REG[k][:-1]])
for K in (30,60):
    for R,lab in ((1095,"6m"),(2190,"1y"),(4380,"2y")):
        CAND["sigfund_p%d_ref%s"%(K,lab)]=trail_pct(REG["fund_sd"],K,R)
        CAND["disp_p%d_ref%s"%(K,lab)]=trail_pct(REG["disp_bps"],K,R)
def corr(a,b):
    m=np.isfinite(a)&np.isfinite(b)
    if m.sum()<200: return float("nan"),0
    a=a[m];b=b[m]
    if a.std()==0 or b.std()==0: return float("nan"),int(m.sum())
    return float(np.corrcoef(a,b)[0,1]), int(m.sum())
F6=np.full(n,np.nan); B6=np.full(n,np.nan); F1=np.concatenate([u[0:],[]])
for t in range(n-6): F6[t]=u[t:t+6].mean()
for t in range(6,n): B6[t]=u[t-6:t].mean()
rows=[]
for name,x in CAND.items():
    cf,nf=corr(x,F6); cb,_=corr(x,B6); c1,_=corr(x,u)
    rows.append(dict(name=name,corr_fwd6=cf,corr_bwd6=cb,corr_now=c1,n=nf,
                     leads=bool(np.isfinite(cf) and np.isfinite(cb) and abs(cf)>abs(cb))))
rows.sort(key=lambda z:-(abs(z["corr_fwd6"]) if np.isfinite(z["corr_fwd6"]) else 0))
print("%-26s %10s %10s %10s %7s %6s"%("input (known at t)","c(x,fwd6)","c(x,bwd6)","c(x,u_t)","n","leads"))
for z in rows[:34]: print("%-26s %+10.4f %+10.4f %+10.4f %7d %6s"%(z["name"],z["corr_fwd6"],z["corr_bwd6"],z["corr_now"],z["n"],z["leads"]))
json.dump(rows,open("/workspace/uplift_2026-09-11/trackC/leadlag_v4.json","w"),indent=1)
np.savez("/workspace/uplift_2026-09-11/trackC/cand_v4.npz",ts=ts,u=u,**CAND,**{"LEG_"+k:v for k,v in LEG.items()})
print("saved cand_v4.npz n=%d %s..%s"%(n,time.strftime("%Y-%m-%d",time.gmtime(int(ts[0]))),time.strftime("%Y-%m-%d",time.gmtime(int(ts[-1])))))

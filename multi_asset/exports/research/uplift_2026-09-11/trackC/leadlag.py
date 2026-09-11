import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
import numpy as np
d=book(); r=regime()
# align regime onto book ts
rmap={int(t):i for i,t in enumerate(r['ts'])}
idx=np.array([rmap.get(int(t),-1) for t in d['ts']])
assert (idx>=0).all(), (idx<0).sum()
u=d['u']; n=len(u)
REG={k:r[k][idx] for k in r if k!='ts'}

def trail_mean(x,K):
    """mean of x over anchors [t-K, t-1] — strictly trailing, NaN-safe."""
    out=np.full(len(x),np.nan)
    for t in range(K,len(x)):
        w=x[t-K:t]; w=w[np.isfinite(w)]
        if len(w)>=max(3,K//2): out[t]=w.mean()
    return out
def trail_std(x,K):
    out=np.full(len(x),np.nan)
    for t in range(K,len(x)):
        w=x[t-K:t]; w=w[np.isfinite(w)]
        if len(w)>=max(3,K//2): out[t]=w.std(ddof=1)
    return out
def trail_pctile(x, K_roll, K_ref):
    """percentile of the K_roll-anchor trailing mean of x within the trailing K_ref window of that same
    rolling mean. Both strictly trailing. Same-era reference = K_ref."""
    rm=trail_mean(x,K_roll)
    out=np.full(len(x),np.nan)
    for t in range(K_ref+K_roll, len(x)):
        hist=rm[t-K_ref:t]; hist=hist[np.isfinite(hist)]
        cur=rm[t]
        if len(hist)>=K_ref//2 and np.isfinite(cur):
            out[t]=float((hist<=cur).mean())
    return out

CAND={}
for K in (30,60,120,240):
    CAND[f'legfund_trail{K}']=trail_mean(d['leg_fund'],K)
    CAND[f'legking_trail{K}']=trail_mean(d['leg_king'],K)
    CAND[f'book_trail{K}']=trail_mean(u,K)
    CAND[f'bookvol_trail{K}']=trail_std(u,K)
for K in (30,60):
    for R,lab in ((1095,'6m'),(2190,'1y'),(4380,'2y')):
        CAND[f'sigfund_p{K}_ref{lab}']=trail_pctile(REG['fund_sd'],K,R)
        CAND[f'fundema_p{K}_ref{lab}']=trail_pctile(REG['fundema_sd'],K,R)
for k in ('disp_bps','breadth_pos','comov','turnover','share_new90','med_age_d','fund_med','fund_absp75','fund_sd','fundema_sd','xs_mean_bps','btc_bps','altmbtc_bps'):
    CAND[f'{k}_trail30']=trail_mean(REG[k],30)
    CAND[f'{k}_now']=np.concatenate([[np.nan],REG[k][:-1]])   # value at t-1 (known at t)

def corr(a,b):
    m=np.isfinite(a)&np.isfinite(b)
    if m.sum()<200: return np.nan,0
    a=a[m]; b=b[m]
    if a.std()==0 or b.std()==0: return np.nan,m.sum()
    return float(np.corrcoef(a,b)[0,1]), int(m.sum())

def fwd(x,k):   # mean of u over t..t+k-1
    c=np.concatenate([np.cumsum(u),[np.nan]])
    out=np.full(n,np.nan)
    for t in range(n-k): out[t]=u[t:t+k].mean()
    return out
def bwd(x,k):   # mean of u over t-k..t-1
    out=np.full(n,np.nan)
    for t in range(k,n): out[t]=u[t-k:t].mean()
    return out
F6=fwd(u,6); B6=bwd(u,6); F1=fwd(u,1)
rows=[]
for name,x in CAND.items():
    cf,nf=corr(x,F6); cb,nb=corr(x,B6); c1,n1=corr(x,F1)
    rows.append(dict(name=name, corr_fwd6=cf, corr_bwd6=cb, corr_fwd1=c1, n=nf,
                     leads=bool(np.isfinite(cf) and np.isfinite(cb) and abs(cf)>abs(cb))))
rows.sort(key=lambda z: -(abs(z['corr_fwd6']) if np.isfinite(z['corr_fwd6']) else 0))
print("%-28s %9s %9s %9s %6s %5s" % ("input (known at t)","c(x,fwd6)","c(x,bwd6)","c(x,fwd1)","n","leads"))
for z in rows:
    print("%-28s %+9.4f %+9.4f %+9.4f %6d %5s" % (z['name'],z['corr_fwd6'],z['corr_bwd6'],z['corr_fwd1'],z['n'],z['leads']))
json.dump(rows, open(f"{OUT}/leadlag.json","w"), indent=1)
np.savez(f"{OUT}/cand.npz", ts=d['ts'], u=u, **{k:v for k,v in CAND.items()})

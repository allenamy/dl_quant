"""Reproduce the offline book trajectory (pod_export_bundle_v3.py L120-160 verbatim structure)
and per-leg single-leg books, + a no-stickiness (alpha=1, band=0) variant. Per-anchor output."""
import numpy as np, json, time, sys
sys.path.insert(0,'/workspace')
from scipy.stats import rankdata
M=np.load('/workspace/data/wide_fea_v2ext_meta.npz',allow_pickle=True)
E=M['E_ts'].astype(np.int64); members=M['members']; y4=M['y4']; qvk=M['qvk']
P=np.load('/workspace/data/wide_panel_4h_v2ext.npz',allow_pickle=True)
pts=P['ts'].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}
R24=P['f_rev_24h']; FE=P['f_fund_ema_v1']; FN=P['f_fund_now']; IV=P['f_fund_iv']
PRED=np.load('/workspace/uplift_2026-09-11/slow_pred_pinned.npy')
nA=len(E); NW=829
COST_B=[(-0.25,5.0,0.85),(0.5,6.0,0.75),(2.0,8.0,0.55)]
def tier_of(q):
    t=np.full(len(q),2,np.int8); t[q>=1e6]=1; t[q>=5e6]=0; return t
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan); n=ok.sum()
    if n>=10: out[ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
LRa=np.load('/workspace/uplift_2026-09-11/lr_cache.npz') if False else None
# msharpe weights need the LR series; recompute it here (same formula)
LR={l:[] for l in ('king','rev24','fund')}; idx=[]
for i in range(nA):
    j=prow.get(int(E[i]))
    if j is None: continue
    m=members[i]; ok=np.isfinite(y4[i,m])
    sc={'king':PRED[i,m],'rev24':-R24[j,m],'fund':FE[j,m]}
    for l in LR:
        z=np.nan_to_num(xz(sc[l])); z=np.where(ok,z,0.0); z-= (z[ok].mean() if ok.sum() else 0)
        g=np.abs(z).sum(); LR[l].append(float((z/g*np.nan_to_num(y4[i,m],nan=0.0)).sum()*1e4) if g>1e-9 else 0.0)
    idx.append(i)
LRa={k:np.array(v) for k,v in LR.items()}; pos={int(i):p for p,i in enumerate(idx)}
def msh(ip):
    if ip<900: return (1/3,1/3,1/3)
    sl=slice(ip-900,ip); r=np.stack([LRa['king'][sl],LRa['rev24'][sl],LRa['fund'][sl]])
    s=r.mean(1)/(r.std(1)+1e-9); s=np.maximum(s,0.0)
    return tuple(s/s.sum() if s.sum()>0 else np.array([1/3]*3))
ARMS={'base':dict(alpha=0.1,band=2.5e-4,legs='w3'),
      'fresh':dict(alpha=1.0,band=0.0,legs='w3'),
      'fund_only':dict(alpha=0.1,band=2.5e-4,legs='fund'),
      'king_only':dict(alpha=0.1,band=2.5e-4,legs='king')}
OUT={}
for arm,cf in ARMS.items():
    H=np.zeros(NW); rec=[]
    for i in range(nA):
        j=prow.get(int(E[i]))
        if j is None: continue
        m=members[i]
        sc={'king':PRED[i,m],'rev24':-R24[j,m],'fund':FE[j,m]}
        wk,wr,wf=msh(pos.get(int(i),0))
        if cf['legs']=='w3':
            z=wk*np.nan_to_num(xz(sc['king']))+wr*np.nan_to_num(xz(sc['rev24']))+wf*np.nan_to_num(xz(sc['fund']))
        else:
            z=np.nan_to_num(xz(sc[cf['legs']]))
        ok=np.isfinite(y4[i,m]); qv4h=np.expm1(np.clip(qvk[i,m],0,30))*48
        sel=ok&(qv4h>=2.5e5)
        if sel.sum()<80: continue
        w=np.where(sel,z,0.0); w-=w[sel].mean(); g=np.abs(w).sum()
        if g<1e-9: continue
        w/=g; capw=2.5/max(sel.sum(),1); w=np.clip(w,-capw,capw)
        g2=np.abs(w).sum()
        if g2>1e-9: w/=g2
        tgt=np.zeros(NW); tgt[m]=w
        sm=H+cf['alpha']*(tgt-H); tr=sm-H
        if cf['band']>0: sm=np.where(np.abs(tr)<cf['band'],H,sm)
        tr=sm-H
        trm=tier_of(qv4h); tabs=np.abs(tr[m])
        cb=sum(tabs[trm==tt].sum()*(fr*mk+(1-fr)*tk) for tt,(mk,tk,fr) in enumerate(COST_B))
        yv=np.nan_to_num(y4[i,m],nan=0.0)
        fnow=np.nan_to_num(FN[j,m],nan=0.0); ivv=IV[j,m]; ivv=np.where(np.isfinite(ivv)&(ivv>0),ivv,8.0)
        car=float((sm[m]*fnow*(4.0/ivv)).sum()*1e4)
        gr=float((sm[m]*yv).sum()*1e4)
        rec.append((int(E[i]),gr,car,float(cb),float(np.abs(sm).sum()),float(np.abs(tr).sum())))
        H=sm
    OUT[arm]=rec
    a=np.array([r[1]-r[2]-r[3] for r in rec if time.gmtime(r[0]).tm_year>=2024])
    print(f'{arm:10} n={len(rec)} net(2024+) {a.mean():.3f} sharpe {a.mean()/(a.std()+1e-12)*np.sqrt(6*365):.2f}',flush=True)
json.dump({k:v for k,v in OUT.items()},open('/workspace/uplift_2026-09-11/book_track.json','w'))
print('DONE')

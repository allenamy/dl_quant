"""TRUE live-measured rank-IC per leg, reconstructed from producer state only.
fund EMA rebuilt with shadow_loop_v3.py L340-349 verbatim (rn = rate*8/iv ; a = 1-0.5**(dt/3d)).
y4 from state/rolling.npz channel 0 (5m simple returns summed, >=46 finite bars) = producer caliber.
Deployed book IC = Spearman(combo weights, y4) on the same anchors."""
import json,numpy as np,glob,os,datetime as dt,collections
from statistics import NormalDist
WS='/Users/haosiyu/wide_shadow'
cfg=json.load(open(f'{WS}/shadow_bundle/config.json')); syms=cfg['symbols_panel']; NW=len(syms)
sidx={s:j for j,s in enumerate(syms)}
aux=json.load(open(f'{WS}/state/aux.json')); led=aux['ledger_tail']
z=np.load(f'{WS}/state/rolling.npz',allow_pickle=True)
cts=z['ts'].astype(np.int64); cd=z['data']; row={int(t):i for i,t in enumerate(cts)}
def spear(a,b):
    ok=np.isfinite(a)&np.isfinite(b)
    if ok.sum()<30: return np.nan
    x=a[ok]; y=b[ok]
    rx=np.argsort(np.argsort(x)).astype(float); ry=np.argsort(np.argsort(y)).astype(float)
    return float(np.corrcoef(rx,ry)[0,1])
def y4(a):
    ai=row.get(int(a)); pi=row.get(int(a)-14400)
    if ai is None or pi is None: return None
    seg=cd[pi+1:ai+1,:,0].astype(np.float32); fin=np.isfinite(seg)
    y=np.where(fin,seg,0).sum(0); y[fin.sum(0)<46]=np.nan; return y
# EMA trajectory per symbol -> value as of each anchor
anchors=sorted(set(int(t) for t in cts if t%14400==0))
EMA=np.full((len(anchors),NW),np.nan); FRESH=np.zeros((len(anchors),NW),bool)
apos={a:i for i,a in enumerate(anchors)}
for s,rows in led.items():
    j=sidx.get(s)
    if j is None: continue
    est=None; ai=0
    rows=sorted(rows)
    for t,rate,iv in rows:
        rn=rate*(8.0/(iv if iv and iv>0 else 8.0))
        if est is None: est={'acc':rn,'last_ts':t}
        else:
            a=1-0.5**(max(t-est['last_ts'],1)/(3*86400.0))
            est={'acc':est['acc']+a*(rn-est['acc']),'last_ts':t}
        # write this state to all anchors from t up to next settlement
        while ai<len(anchors) and anchors[ai]<t: ai+=1
        k=ai
        while k<len(anchors):
            EMA[k,j]=est['acc']; FRESH[k,j]= (anchors[k]-t)<=12*3600
            k+=1
res=[]
for a in anchors:
    y=y4(a+14400)
    if y is None: continue
    i=apos[a]
    fe=np.where(FRESH[i],EMA[i],np.nan)
    ic=spear(fe,y)
    cf=f'{WS}/state/weights_combo/{a}.npz'; kf=f'{WS}/state/weights/{a}.npz'
    icc=ick=np.nan
    if os.path.exists(cf):
        w=np.load(cf); v=np.zeros(NW); v[w['idx']]=w['val']; v[v==0]=np.nan; icc=spear(v,y)
    if os.path.exists(kf):
        w=np.load(kf); v=np.zeros(NW); v[w['idx']]=w['val']; v[v==0]=np.nan; ick=spear(v,y)
    res.append((a,ic,icc,ick,int(np.isfinite(fe).sum()),float(np.nanstd(y)*1e4)))
R=np.array(res,float)
def st(v):
    v=v[np.isfinite(v)]; n=len(v)
    if n<2: return n,np.nan,np.nan,np.nan
    m=v.mean(); se=v.std(ddof=1)/np.sqrt(n); return n,m,se,m/se
print('anchors',len(R),dt.datetime.utcfromtimestamp(int(R[0,0])),'..',dt.datetime.utcfromtimestamp(int(R[-1,0])))
eras=[('all live window',R[:,0]>0),
      ('pre-combo  ..08-26',R[:,0]<1787702400),
      ('combo era 08-26..',R[:,0]>=1787702400),
      ('post-deposit 09-03..',R[:,0]>=1788480000),
      ('2026-08a',(R[:,0]<1787097600)),
      ('2026-08b',(R[:,0]>=1787097600)&(R[:,0]<1788220800)),
      ('2026-09a',(R[:,0]>=1788220800))]
print(f"{'era':24}{'n':>5}{'fundIC':>10}{'+-95CI':>9}{'t':>7}   {'comboIC':>9}{'t':>7}   {'kingbookIC':>11}{'t':>7}")
for nm,s in eras:
    n,m,se,t=st(R[s,1]); n2,m2,se2,t2=st(R[s,2]); n3,m3,se3,t3=st(R[s,3])
    print(f'{nm:24}{n:5d}{m:+10.4f}{1.96*se:9.4f}{t:+7.2f}   {m2:+9.4f}{t2:+7.2f}   {m3:+11.4f}{t3:+7.2f}')
np.savez('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/live_leg_ic.npz',
         ts=R[:,0],fund_ic=R[:,1],combo_ic=R[:,2],king_ic=R[:,3],n_fresh=R[:,4],ysd=R[:,5])
print()
print('daily fund IC (live):')
day=collections.defaultdict(list)
for a,ic,icc,ick,n,s in res:
    day[dt.datetime.utcfromtimestamp(int(a)).strftime('%m-%d')].append((ic,icc))
for d in sorted(day):
    A=np.array(day[d],float); print(f'  {d}  n={len(A)}  fundIC {np.nanmean(A[:,0]):+.4f}   comboIC {np.nanmean(A[:,1]):+.4f}')

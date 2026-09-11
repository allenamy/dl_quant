"""Funding regime + cross-sectional return dispersion over the LIVE window, from producer state only."""
import json,numpy as np,datetime as dt,collections
WS='/Users/haosiyu/wide_shadow'
aux=json.load(open(f'{WS}/state/aux.json'))
led=aux['ledger_tail']
# bucket each settlement into the 4h anchor it belongs to; normalise to bps per 4h
by=collections.defaultdict(list)
for s,rows in led.items():
    for t,rate,iv in rows:
        a=int(t)//14400*14400
        by[a].append(rate*(4.0/(iv if iv and iv>0 else 8.0))*1e4)
ks=sorted(by)
print('=== funding regime, per 4h anchor, bps-per-4h across settling names (producer ledger_tail) ===')
print('anchors',len(ks),dt.datetime.utcfromtimestamp(ks[0]),'..',dt.datetime.utcfromtimestamp(ks[-1]))
lab=collections.defaultdict(list)
for a in ks:
    v=np.array(by[a])
    if len(v)<50: continue
    d=dt.datetime.utcfromtimestamp(a)
    lab[d.strftime('%Y-%m')+('a' if d.day<=15 else 'b')].append((len(v),v.mean(),v.std(),np.percentile(v,90)-np.percentile(v,10),(v<0).mean()))
print(f"{'bucket':10}{'anch':>5}{'n_names':>8}{'mean':>8}{'sd':>8}{'p90-p10':>9}{'frac<0':>8}")
for b in sorted(lab):
    A=np.array(lab[b])
    print(f'{b:10}{len(A):5d}{A[:,0].mean():8.0f}{A[:,1].mean():+8.3f}{A[:,2].mean():8.3f}{A[:,3].mean():9.3f}{A[:,4].mean():8.3f}')
# cross-sectional dispersion of y4 over live anchors
z=np.load(f'{WS}/state/rolling.npz',allow_pickle=True)
cts=z['ts'].astype(np.int64); cd=z['data']; row={int(t):i for i,t in enumerate(cts)}
anch=[t for t in cts if t%14400==0]
rows=[]
for a in anch:
    ai=row.get(int(a)); pi=row.get(int(a)-14400)
    if ai is None or pi is None: continue
    seg=cd[pi+1:ai+1,:,0].astype(np.float32); fin=np.isfinite(seg)
    y=np.where(fin,seg,0).sum(0); y[fin.sum(0)<46]=np.nan
    y=y[np.isfinite(y)]
    if len(y)<100: continue
    rows.append((int(a),len(y),np.nanstd(y)*1e4,np.nanmean(y)*1e4))
R=np.array(rows,float)
print()
print('=== cross-sectional sd of y4 (bps) per anchor, live window ===')
lab2=collections.defaultdict(list)
for a,n,sd,mu in rows:
    d=dt.datetime.utcfromtimestamp(a); lab2[d.strftime('%Y-%m')+('a' if d.day<=15 else 'b')].append((n,sd,mu))
for b in sorted(lab2):
    A=np.array(lab2[b]); print(f'{b:10} anchors {len(A):3d}  n {A[:,0].mean():5.0f}  xs-sd(y4) {A[:,1].mean():7.2f} bps  xs-mean(y4) {A[:,2].mean():+7.2f} bps')
np.savez('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/live_ysd.npz',ts=R[:,0],n=R[:,1],ysd=R[:,2],ymu=R[:,3])

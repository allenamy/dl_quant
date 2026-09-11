"""Deployed-book staleness: (a) weight autocorrelation across anchors, (b) book return at forward lag k,
(c) which lag of the signal the book best matches."""
import numpy as np,glob,os,json,datetime as dt
WS='/Users/haosiyu/wide_shadow'
z=np.load(f'{WS}/state/rolling.npz',allow_pickle=True)
cts=z['ts'].astype(np.int64); cd=z['data']; row={int(t):i for i,t in enumerate(cts)}
cfg=json.load(open(f'{WS}/shadow_bundle/config.json')); NW=len(cfg['symbols_panel'])
def y4(a):
    ai=row.get(int(a)); pi=row.get(int(a)-14400)
    if ai is None or pi is None: return None
    seg=cd[pi+1:ai+1,:,0].astype(np.float32); fin=np.isfinite(seg)
    y=np.where(fin,seg,0).sum(0); y[fin.sum(0)<46]=np.nan; return y
def load(d):
    out={}
    for f in sorted(glob.glob(f'{WS}/state/{d}/*.npz')):
        A=int(os.path.basename(f)[:-4]); w=np.load(f); v=np.zeros(NW); v[w['idx']]=w['val']; out[A]=v
    return out
for name,d in (('combo(deployed since 08-26)','weights_combo'),('king(producer form)','weights')):
    W=load(d); ks=sorted(W)
    ks=[k for k in ks if k>=1787702400]   # combo era only, same anchor set for both
    print(f'=== {name} : {len(ks)} anchors {dt.datetime.utcfromtimestamp(ks[0])}..{dt.datetime.utcfromtimestamp(ks[-1])} ===')
    ac=[]
    for k in range(1,19):
        c=[]
        for a in ks:
            b=a+k*14400
            if b in W:
                x,y=W[a],W[b]; m=(np.abs(x)>0)|(np.abs(y)>0)
                if m.sum()>50: c.append(np.corrcoef(x[m],y[m])[0,1])
        if c: ac.append((k,len(c),float(np.mean(c))))
    print('  weight autocorr by lag (anchors):', ' '.join(f'{k}:{v:.3f}' for k,_,v in ac))
    hl=[k for k,_,v in ac if v<0.5]
    print('  first lag with autocorr<0.5 :', hl[0] if hl else '>18', 'anchors')
    # forward book return at lag k
    print('  book gross_bps at forward lag k (bps/anchor, unit book gross):')
    for k in range(0,7):
        r=[]
        for a in ks:
            y=y4(a+14400*(k+1))
            if y is None: continue
            r.append(float((W[a]*np.nan_to_num(y,nan=0.0)).sum()*1e4)/max(np.abs(W[a]).sum(),1e-9))
        r=np.array(r)
        if len(r)>5: print(f'    k={k}: n={len(r):3d} mean {r.mean():+7.3f} se {r.std(ddof=1)/np.sqrt(len(r)):5.3f} t {r.mean()/(r.std(ddof=1)/np.sqrt(len(r))):+5.2f}')
    print()

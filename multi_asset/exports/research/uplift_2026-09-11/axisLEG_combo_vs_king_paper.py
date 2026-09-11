"""Score the DEPLOYED combo book with the producer's own y4 caliber, and compare to the
producer's `score` event (which scores the KING-form sm, not the deployed book)."""
import numpy as np, json, glob, os, datetime as dt
WS='/Users/haosiyu/wide_shadow'
z=np.load(f'{WS}/state/rolling.npz',allow_pickle=True)
cts=z['ts'].astype(np.int64); cd=z['data']
row_of={int(t):i for i,t in enumerate(cts)}
cfg=json.load(open(f'{WS}/shadow_bundle/config.json')); syms=cfg['symbols_panel']; NW=len(syms)
def y4_for(anchor):
    ai=row_of.get(int(anchor)); pi=row_of.get(int(anchor)-14400)
    if ai is None or pi is None: return None
    seg=cd[pi+1:ai+1,:,0].astype(np.float32)
    fin=np.isfinite(seg); y=np.where(fin,seg,0).sum(0)
    y[fin.sum(0)<46]=np.nan
    return y
sc={int(d['anchor_ts']):d for d in (json.loads(l) for l in open(f'{WS}/shadow_log.jsonl')) if d.get('e')=='score'}
rows=[]
for f in sorted(glob.glob(f'{WS}/state/weights_combo/*.npz')):
    A=int(os.path.basename(f)[:-4])
    y=y4_for(A+14400)          # forward 4h return realised over [A, A+4h]
    if y is None: continue
    w=np.load(f); cw=np.zeros(NW); cw[w['idx']]=w['val']
    kf=f'{WS}/state/weights/{A}.npz'
    kw_=np.zeros(NW)
    if os.path.exists(kf):
        k=np.load(kf); kw_[k['idx']]=k['val']
    yy=np.nan_to_num(y,nan=0.0)
    gc=float((cw*yy).sum()*1e4); gk=float((kw_*yy).sum()*1e4)
    s=sc.get(A)
    rows.append((A,gc,gk,float(s['gross_bps']) if s else np.nan,
                 float(s['carry_bps']) if s else np.nan, float(s['cost_bps']) if s else np.nan,
                 float(np.abs(cw).sum()),float(np.abs(kw_).sum())))
r=np.array(rows,float)
print('anchors scored:',len(r), dt.datetime.utcfromtimestamp(int(r[0,0])),'..',dt.datetime.utcfromtimestamp(int(r[-1,0])))
lab=['combo_gross_bps(recomputed)','king_gross_bps(recomputed)','king_gross_bps(producer score)']
for i,l in zip((1,2,3),lab):
    v=r[:,i]; v=v[np.isfinite(v)]
    print(f'  {l:34} n={len(v):3d} mean {v.mean():+7.3f}  sd {v.std(ddof=1):6.2f}  se {v.std(ddof=1)/np.sqrt(len(v)):5.3f}  t {v.mean()/(v.std(ddof=1)/np.sqrt(len(v))):+5.2f}')
ok=np.isfinite(r[:,2])&np.isfinite(r[:,3])
print(f'  validation: recomputed king vs producer score  corr {np.corrcoef(r[ok,2],r[ok,3])[0,1]:.4f}  mean|diff| {np.abs(r[ok,2]-r[ok,3]).mean():.3f}')
print(f'  gross_pos: combo {r[:,6].mean():.4f}  king {r[:,7].mean():.4f}')
print(f'  combo - king paper gross: {np.nanmean(r[:,1]-r[:,2]):+.3f} bps/anchor')
np.savez('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/combo_paper.npz',
         ts=r[:,0],combo=r[:,1],king=r[:,2],king_score=r[:,3],carry=r[:,4],cost=r[:,5],gc=r[:,6],gk=r[:,7])

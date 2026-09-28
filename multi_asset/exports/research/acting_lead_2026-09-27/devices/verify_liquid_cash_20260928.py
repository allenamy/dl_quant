"""Recalculate liquidity-population metrics from raw NPZs without original readers."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
from datetime import datetime
import json,hashlib,sys,re,math
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(root,out):
 root=Path(root);ep=root/'receipts/ECONOMIC_FULL_BOOK.json';e=json.loads(ep.read_text())
 terminal=json.loads((root/'TERMINAL.json').read_text())
 if terminal['rc']!=0:raise ValueError('batch did not complete')
 cached={};hashes={};checks=0;largest=0.
 def eq(a,b,context):
  nonlocal checks,largest
  a,b=np.asarray(a,float),np.asarray(b,float)
  if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('shape/finite '+context)
  err=float(np.max(abs(a-b)));largest=max(largest,err)
  if not np.allclose(a,b,atol=1e-9,rtol=1e-10):raise ValueError(f'{context}: {err}')
  checks+=1
 def population(kind,seed):
  key=(kind,seed)
  if key in cached:return cached[key]
  tag=f'DLARCH_REF_NC_s{seed}X_scaled_rule_raw_UAFE' if kind=='NC' else f'ADAPT_{kind}_s{seed}X_scaled_rule_raw_UAFE'
  base=Path(f'/workspace/dlarch_2026-09-24/chain/ref_nc_s{seed}X/runs') if kind=='NC' else root/f'cells/{kind}_s{seed}/runs'
  data={w:[] for w in e['windows']}
  for seedpath in range(32):
   p=base/tag/f'PATH_{tag}_seed_{seedpath:02d}.npz';h=sha(p);j=json.loads(p.with_suffix('.json').read_text())
   if h!=j['npz_sha256'] or j['seed']!=seedpath:raise ValueError('path identity')
   hashes[str(p)]=h
   with np.load(p) as z:
    a=z['A'];r=z['navm1']/z['navm0']-1
    if not np.isfinite(a).all() or not np.equal(a,np.floor(a)).all() or not np.all(a%14400==0) or not np.all(np.diff(a)==14400):raise ValueError('axis')
    eq(r,(z['price_trade']+z['funding']-z['fee']-z['unk_excluded']*(z['unk_price']+z['unk_funding']))/z['nav0'],'cash')
    for w,(lo,hi) in e['windows'].items():
     lo,hi=[int(datetime.fromisoformat(t.replace('Z','+00:00')).timestamp()) for t in (lo,hi)]
     m=(a>=lo)&(a<=hi);ds,counts=np.unique(a[m]//86400,return_counts=True);ds=ds[counts==6];ix=np.flatnonzero(m&np.isin(a//86400,ds))
     eq(a[ix].reshape(-1,6),ds[:,None]*86400+np.arange(6)*14400,'complete days')
     daily=np.prod(1+r[ix].reshape(-1,6),axis=1)-1
     stress=np.prod(1+(r[ix]-.25*z['fee'][ix]/z['nav0'][ix]).reshape(-1,6),axis=1)-1
     lo5=int((a[ix[0]]-int(z['nav5_t0']))//300);hi5=int((a[ix[-1]]+14400-int(z['nav5_t0']))//300)
     nav=z['nav5_main'][lo5:hi5+1]
     if len(nav)!=len(ix)*48+1 or not np.isfinite(nav).all() or np.any(nav<=0):raise ValueError('5m population')
     v={'return_compound':np.prod(1+daily)-1,'cagr':np.prod(1+daily)**(365/len(daily))-1,'sharpe_daily':daily.mean()/daily.std(ddof=1)*math.sqrt(365),'mean_daily_bps':daily.mean()*1e4,'maxdd_5m':np.min(nav/np.maximum.accumulate(nav)-1),'worst_day':daily.min(),'days_below_minus2pct':int((daily<-.02).sum()),'days_below_minus4pct':int((daily<-.04).sum()),'turnover_over_sizing_gross_per_anchor':np.mean(z['turnover'][ix]/(2*z['nav0'][ix]))}
     data[w].append((v,daily,stress,[len(ds),len(ix),a[ix[0]],a[ix[-1]]]))
  cached[key]=data;return data
 for name,row in e['results'].items():
  match=re.fullmatch(r'(LQ)_s(42|2027)_vs_(NC|U)',name)
  if not match:raise ValueError('pair identity')
  kind,seed,ref=match.groups();seed=int(seed);ca,ba=population(kind,seed),population(ref,seed)
  for w,r in row['results'].items():
   for label,data in [('candidate',ca[w]),('baseline',ba[w])]:
    for v,d,st,pop in data:eq(pop,[r['n_days'],r['n_anchors'],r['first_anchor'],r['last_anchor']],'population')
    for k in data[0][0]:eq(np.mean([x[0][k] for x in data]),r[label][k]['mean'],name+'/'+w+'/'+k)
   delta=np.mean([x[1]-y[1] for x,y in zip(ca[w],ba[w])],axis=0);stress=np.mean([x[2]-y[2] for x,y in zip(ca[w],ba[w])],axis=0)
   eq(delta,r['paired_daily_returns'],'paired daily');eq(delta.mean()*1e4,r['paired_daily_bps'],'paired mean');eq(stress.mean()*1e4,r['fee125_paired_daily_bps'],'fee125')
 result={'status':'RAW_ARRAY_RECALCULATION_PASS','source_sha256':sha(__file__),'economic_sha256':sha(ep),'unique_paths':len(hashes),'checks':checks,'max_abs_difference':largest,'paths':hashes,'limits':'Arithmetic and population check; shared simulator outputs, not independent live certification.'}
 Path(out).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print({k:v for k,v in result.items() if k!='paths'})
if __name__=='__main__':main(*sys.argv[1:])

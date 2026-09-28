"""Independent raw-prediction population/fold and metric audit; no refit."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
import hashlib,json,sys,time
import numpy as np
from scipy.stats import rankdata
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main(root):
 root=Path(root);r=json.loads((root/'RESULT.json').read_text());t=json.loads((root/'TERMINAL.json').read_text());assert t['rc']==0 and t['result_sha256']==sha(root/'RESULT.json')
 for n,h in r['outputs'].items():assert sha(root/n)==h
 z=np.load(root/'PREDICTIONS.npz');A=z['anchors'];cnt=z['count'];off=z['off'];m=z['m'];y=z['raw_y'];yr=z['rank_y'];p=z['pred'];peer=z['has_peer'];metrics=z['metrics'];coverage=z['coverage'];rid=np.repeat(np.arange(len(A)),cnt);at=A[rid]
 checks=0;largest=0.
 def eq(x,y,label,tol=1e-10):
  nonlocal checks,largest
  x,y=np.asarray(x),np.asarray(y);assert x.shape==y.shape,label
  assert np.array_equal(np.isnan(x),np.isnan(y)),label
  v=np.isfinite(x)&np.isfinite(y);d=float(np.max(np.abs(x[v]-y[v]))) if np.any(v) else 0.;largest=max(largest,d);assert d<=tol,(label,d);checks+=1
 assert np.array_equal(off,np.r_[0,np.cumsum(cnt)]) and len(m)==off[-1] and np.all(np.diff(A)==14400)
 for j in (2,3):eq(p[~peer,j],p[~peer,1],'unknown peer baseline fallback',0)
 for f in r['folds']:
  month=np.datetime64(f['month']);start=int(month.astype('datetime64[s]').astype('int64'));end=int((month+1).astype('datetime64[s]').astype('int64'))
  train=(at>=start-365*86400)&(at+14400<start-12*14400)&np.isfinite(yr);common=train&peer;test=(at>=start)&(at<end)
  eq([train.sum(),common.sum(),test.sum(),(test&peer).sum(),at[common].min(),at[common].max()+14400],[f[k] for k in ('train_rows','common_rows','test_rows','peer_test_rows','training_first_anchor','last_label_end')],'fold source population',0)
  assert (at[common]+14400).max()<start-48*3600
 for k in range(len(A)):
  sl=np.arange(off[k],off[k+1]);known=sl[np.isfinite(y[sl])]
  if len(known)>=50:eq(yr[known],rankdata(y[known])/(len(known)-1)-.5,'label rank raw population',0)
  good=sl[np.isfinite(y[sl])&np.isfinite(p[sl]).all(1)]
  for pop,ix in enumerate((good,good[peer[good]])):
   eq(len(ix),coverage[k,pop],'measured population',0)
   if len(ix)<50:continue
   for j in range(4):
    pp=p[ix,j].astype(float);yy=y[ix];rr=rankdata(pp);w=rr-rr.mean();v=[np.corrcoef(pp,yy)[0,1],np.corrcoef(rr,rankdata(yy))[0,1],float(np.sum(w*yy)/np.sum(np.abs(w))*1e4)]
    eq(v,metrics[k,pop,j],'raw price P/S and rank portfolio',1e-9)
 for w,(lo,hi) in r['windows'].items():
  st=lambda s:int(np.datetime64(s,'s').astype('int64'));mask=(A>=st(lo))&(A<st(hi))
  for pop,label in enumerate(('all_with_baseline_fallback','common_peer')):
   use=mask&np.isfinite(metrics[:,pop]).all((1,2));v=metrics[use,pop].mean(0);stored=r['results'][w][label]
   eq(v,stored['mean_price_P_S_and_rankprice_bps'],'window metrics');eq(v[2]-v[1],stored['peer_minus_matched_baseline'],'matched delta');eq(v[3]-v[1],stored['shuffle_minus_matched_baseline'],'shuffle delta')
   assert stored['anchors']==int(use.sum())
 rec={'status':'RAW_PREDICTION_AUDIT_PASS','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'result_sha256':sha(root/'RESULT.json'),'prediction_sha256':sha(root/'PREDICTIONS.npz'),'checks':checks,'max_abs_difference':largest,'folds':len(r['folds']),'limitations':['Arithmetic/fold/missingness audit; no independent refit','Bootstrap implementation not independently regenerated','Does not certify whole-book benefit or deployment']}
 (root/'INDEPENDENT_CHECK.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2))
if __name__=='__main__':main(*sys.argv[1:])

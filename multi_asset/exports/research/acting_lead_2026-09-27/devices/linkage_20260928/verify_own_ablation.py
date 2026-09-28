"""Independent arithmetic/population audit from exported arrays, not a refit."""
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
 root=Path(root);r=json.loads((root/'RESULT.json').read_text());t=json.loads((root/'TERMINAL.json').read_text())
 assert t['rc']==0 and t['result_sha256']==sha(root/'RESULT.json')
 for n,h in r['outputs'].items():assert sha(root/n)==h
 z=dict(np.load(root/'PREDICTIONS.npz'));T=z['anchors'];o=z['off'];m=z['m'];y=z['raw_y'];p=z['pred'];rid=np.repeat(np.arange(len(T)),z['count']);at=T[rid];metrics=z['metrics'];checks=0;largest=0.
 def eq(a,b,tol=1e-9):
  nonlocal checks,largest
  a,b=np.asarray(a),np.asarray(b);assert a.shape==b.shape and np.array_equal(np.isnan(a),np.isnan(b));assert not np.isinf(a).any() and not np.isinf(b).any();v=np.isfinite(a);d=float(np.max(np.abs(a[v]-b[v]))) if v.any() else 0.;assert d<=tol,(d,tol);largest=max(d,largest);checks+=1
 assert np.array_equal(o,np.r_[0,np.cumsum(z['count'])]) and np.all(np.diff(T)==14400)
 for f in r['folds']:
  mo=np.datetime64(f['month']);s=int(mo.astype('datetime64[s]').astype('int64'));e=int((mo+1).astype('datetime64[s]').astype('int64'));tr=(at>=s-365*86400)&(at+14400<s-48*3600)&np.isfinite(z['rank_y']);te=(at>=s)&(at<e)
  eq([tr.sum(),te.sum(),at[tr].max()+14400],[f['train_rows'],f['test_rows'],f['last_label_end']],0)
 for k in range(len(T)):
  sl=np.arange(o[k],o[k+1]);known=sl[np.isfinite(y[sl])];good=sl[np.isfinite(y[sl])&np.isfinite(p[sl]).all(1)];eq(len(good),z['coverage'][k],0)
  if len(known)>=50:eq(z['rank_y'][known],rankdata(y[known])/(len(known)-1)-.5,0)
  if len(good)<50:continue
  for j in range(7):
   pp=p[good,j].astype(float);yy=y[good];rr=rankdata(pp);ww=rr-rr.mean();v=[np.corrcoef(pp,yy)[0,1],np.corrcoef(rr,rankdata(yy))[0,1],np.sum(ww*yy)/np.sum(np.abs(ww))*1e4];eq(v,metrics[k,j])
 for name,(lo,hi) in r['windows'].items():
  st=lambda s:int(np.datetime64(s,'s').astype('int64'));use=(T>=st(lo))&(T<st(hi));v=metrics[use].mean(0);q=r['results'][name];eq(v,q['means']);eq(v[1:]-v[:-1],q['successive_deltas']);eq(v[1:]-v[0],q['vs_NC']);assert use.sum()==q['anchors'] and use.sum()==6*q['days']
 rec={'status':'INDEPENDENT_RAW_METRIC_AUDIT_PASS','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'result_sha256':sha(root/'RESULT.json'),'prediction_sha256':sha(root/'PREDICTIONS.npz'),'checks':checks,'max_abs_difference':largest,'limitations':['No independent refit or bootstrap regeneration','Not a whole-book cash or release gate']}
 (root/'INDEPENDENT_CHECK.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
if __name__=='__main__':main(sys.argv[1])

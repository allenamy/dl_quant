"""Independent original-array statistics and causal-fold audit. Does not refit."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
from pathlib import Path
import hashlib,json,sys,time
import numpy as np
from scipy.stats import rankdata

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def main(root,output):
 root=Path(root);r=json.loads((root/'RESULT.json').read_text());t=json.loads((root/'TERMINAL.json').read_text());assert t['rc']==0 and t['result_sha256']==sha(root/'RESULT.json')
 for n,h in r['outputs'].items():assert sha(root/n)==h,n
 z=dict(np.load(root/'PREDICTIONS.npz'));T=z['anchors'];m=z['m'];off=z['off'];cnt=z['count'];y=z['raw_y'];Y=z['labels'];P=z['pred'];Q=z['tail_metrics'];M=z['price_metrics'];at=np.repeat(T,cnt);checks=0;worst=0.
 assert np.array_equal(off,np.r_[0,np.cumsum(cnt)]) and np.all(np.diff(T)==14400) and len(m)==off[-1]
 parent=np.load('/dev/shm/conditional_strength_20260928/PREDICTIONS.npz');prior=parent['pred'];assert sha('/dev/shm/conditional_strength_20260928/PREDICTIONS.npz')==r['inputs']['/dev/shm/conditional_strength_20260928/PREDICTIONS.npz']
 def eq(a,b,tol=1e-10):
  nonlocal checks,worst
  a,b=np.asarray(a),np.asarray(b);assert a.shape==b.shape and np.array_equal(np.isnan(a),np.isnan(b));assert not np.isinf(a).any() and not np.isinf(b).any();v=np.isfinite(a);e=float(np.max(np.abs(a[v]-b[v]))) if v.any() else 0.;assert e<=tol,(e,tol);worst=max(e,worst);checks+=1
 def auc(p,y):
  ranks=rankdata(p);positive=y==1;np_=int(positive.sum());nn=len(y)-np_
  return (ranks[positive].sum()-np_*(np_+1)/2)/(np_*nn)
 for k in range(len(T)):
  sl=np.arange(off[k],off[k+1]);finite=sl[np.isfinite(y[sl])];expected=np.full((len(sl),2),np.nan)
  if len(finite)>=50:
   ix=np.argsort(y[finite],kind='stable');n=int(np.ceil(.05*len(finite)));expected[finite-off[k]]=0;expected[finite[ix[:n]]-off[k],1]=1;expected[finite[ix[-n:]]-off[k],0]=1
  eq(expected,Y[sl],0)
  for si in range(2):
   cols=np.arange(si*3,si*3+3);good=sl[np.isfinite(y[sl])&np.isfinite(P[sl][:,cols]).all((1,2))&np.isfinite(prior[sl,si*3+1])];eq(len(good),z['coverage'][k,si],0)
   if len(good)<50:continue
   yy=Y[good];tails=yy.sum(1)==1
   for j,col in enumerate(cols):
    pp=np.clip(P[good,col].astype(float),0,1);pp/=np.maximum(1,pp.sum(1,keepdims=True));q=[np.mean((pp[:,0]-yy[:,0])**2),np.mean((pp[:,1]-yy[:,1])**2),auc(pp[:,0],yy[:,0]),auc(pp[:,1],yy[:,1]),auc((pp[:,0]-pp[:,1])[tails],yy[tails,0])];eq(q,Q[k,col])
   vals=[(P[good,j,0]-P[good,j,1]).astype(float) for j in cols]+[prior[good,si*3+1].astype(float)]
   for j,v in enumerate(vals):
    ranks=rankdata(v);w=ranks-ranks.mean();q=[np.corrcoef(v,y[good])[0,1],np.corrcoef(ranks,rankdata(y[good]))[0,1],np.dot(w,y[good])/np.abs(w).sum()*1e4];eq(q,M[k,si*4+j])
 for f in r['folds']:
  si=(42,2027).index(f['seed']);mo=np.datetime64(f['month']);start=int(mo.astype('datetime64[s]').astype('int64'));end=int((mo+1).astype('datetime64[s]').astype('int64'));tr=(at>=start-365*86400)&(at+14400<start-48*3600)&np.isfinite(Y).all(1)&z['eligible'][:,si];te=(at>=start)&(at<end)&z['eligible'][:,si]
  eq([tr.sum(),te.sum(),at[tr].max()+14400,at[tr].min()],[f['train_rows'],f['test_rows'],f['last_label_end'],f['first_anchor']],0);assert len(np.unique(at[tr]//86400))>=180
 for window,(lo,hi) in r['windows'].items():
  stamp=lambda s:int(np.datetime64(s,'s').astype('int64'));use=(T>=stamp(lo))&(T<stamp(hi))
  for si,seed in enumerate(('42','2027')):
   q=Q[use,si*3:si*3+3].mean(0);p=M[use,si*4:si*4+4].mean(0);row=r['results'][window][seed];eq(q,row['tail_metrics_means']);eq(p,row['price_metric_means']);eq(q[1]-q[0],row['full_minus_score_only']);eq(p[1]-p[3],row['direction_minus_prior_rank_ridge']);assert use.sum()==row['anchors']==6*row['days']
 result={'status':'INDEPENDENT_TAIL_ARRAY_CHECK_PASS','utc':time.strftime('%FT%TZ',time.gmtime()),'checks':checks,'max_abs_error':worst,'models_verified':len(r['outputs'])-1,'prediction_sha256':sha(root/'PREDICTIONS.npz'),'result_sha256':sha(root/'RESULT.json'),'source_sha256':sha(__file__),'limits':['No independent model refit or bootstrap','Confirms stored labels/populations/chronology/metrics, not tradability or book value']}
 with Path(output).open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
 print(json.dumps(result))
if __name__=='__main__':main(*sys.argv[1:])

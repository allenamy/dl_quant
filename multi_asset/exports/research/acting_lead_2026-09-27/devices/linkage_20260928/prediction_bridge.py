"""Descriptive same-axis bridge of saved predictions; no model fit or promotion."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import hashlib,json,sys,time,traceback
import numpy as np
from scipy.stats import rankdata

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def align_prefix(a,b):
 n=len(b['anchors']);nr=int(b['off'][-1])
 for z in (a,b):
  if not np.array_equal(z['off'],np.r_[0,np.cumsum(z['count'])]) or len(z['m'])!=z['off'][-1]:raise ValueError('ragged axis')
  if not np.all(np.diff(z['anchors'])==14400):raise ValueError('time axis')
  if np.isinf(z['raw_y']).any():raise ValueError('infinite label')
 for k in ('anchors','count'):
  if not np.array_equal(a[k][:n],b[k]):raise ValueError('changed '+k)
 if not np.array_equal(a['symbols'],b['symbols']):raise ValueError('symbols')
 if not np.array_equal(a['off'][:n+1],b['off']):raise ValueError('offset')
 for k in ('m','raw_y','rank_y'):
  if not np.array_equal(a[k][:nr],b[k],equal_nan=True):raise ValueError('changed '+k)
 return n,nr

def complete_daily(t,v):
 out=[]
 for d in np.unique(t//86400):
  ix=t//86400==d
  if not np.array_equal(t[ix],d*86400+np.arange(6)*14400):raise ValueError('incomplete day')
  out.append(v[ix].mean(0))
 return np.array(out)

def corr(a,b):
 a=a-a.mean();b=b-b.mean();s=np.sqrt((a@a)*(b@b))
 return float(a@b/s) if s>0 else np.nan
def metric(p,y):
 r=rankdata(p);w=r-r.mean()
 return [corr(p,y),corr(r,rankdata(y)),float(w@y/np.abs(w).sum()*1e4)]
def ci(v,k):
 rng=np.random.default_rng(20260928+k);s=rng.integers(len(v)-k+1,size=(2000,int(np.ceil(len(v)/k))))
 ix=(s[:,:,None]+np.arange(k)).reshape(2000,-1)[:,:len(v)]
 return np.quantile(v[ix].mean(1),[.025,.975],axis=0).tolist()

def main(root,contract):
 start=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);c=json.loads(Path(contract).read_text())
 z=[];rr=[]
 for p,h in c['inputs'].items():
  if sha(p)!=h:raise ValueError('input identity '+p)
 for name in ('price_root','flow_root'):
  p=Path(c[name]);r=json.loads((p/'RESULT.json').read_text());t=json.loads((p/'TERMINAL.json').read_text())
  if t['rc']!=0 or t['result_sha256']!=sha(p/'RESULT.json') or r['outputs']['PREDICTIONS.npz']!=sha(p/'PREDICTIONS.npz'):raise ValueError('terminal binding')
  z.append(dict(np.load(p/'PREDICTIONS.npz')));rr.append(r)
 a,b=z;n,nr=align_prefix(a,b);T=b['anchors'];off=b['off'];m=b['m'];y=b['raw_y'];rid=np.repeat(np.arange(n),b['count'])
 if [(f['month'],f['train_rows']) for f in rr[0]['folds']]!=[(f['month'],f['train_rows']) for f in rr[1]['folds']]:raise ValueError('baseline train rows differ')
 # Full-population baseline vs full-population baseline. The price peer retains
 # its original common-training fallback; it is shown separately, not a control.
 P=np.column_stack([a['pred'][:nr,0],a['pred'][:nr,2],b['pred'][:,0]])
 R=np.column_stack([a['return_pred'][:nr,0],a['return_pred'][:nr,2],b['return_pred'][:,0]])
 M=np.full((n,3,3),np.nan);cnt=np.zeros(n,int);maxdiff=0.
 for k in range(n):
  sl=np.arange(off[k],off[k+1]);finite_pred=np.isfinite(P[sl])
  if not np.array_equal(finite_pred[:,0],finite_pred[:,1]) or not np.array_equal(finite_pred[:,0],finite_pred[:,2]):raise ValueError('prediction population differs')
  ix=sl[np.isfinite(y[sl])&finite_pred.all(1)];cnt[k]=len(ix)
  if len(ix)<50:continue
  for j in range(3):M[k,j]=metric(P[ix,j].astype(float),y[ix])
  expected=np.array([a['metrics'][k,0,0],a['metrics'][k,0,2],b['metrics'][k,0,0]])
  diff=float(np.max(np.abs(M[k]-expected)));maxdiff=max(maxdiff,diff)
  if diff>1e-9:raise ValueError('stored metric mismatch')
 windows=rr[1]['windows'];out={}
 for name,(lo,hi) in windows.items():
  stamp=lambda s:int(np.datetime64(s,'s').astype('int64'))
  use=(T>=stamp(lo))&(T<stamp(hi))
  if not np.isfinite(M[use]).all():raise ValueError('unknown window')
  day=complete_daily(T[use],M[use]);ds=np.stack([day[:,2]-day[:,0],day[:,2]-day[:,1]],axis=1)
  row=use[rid]&np.isfinite(y)&np.isfinite(P).all(1);per=[];cal=[]
  for s in np.unique(m[row]):
   ix=np.flatnonzero(row&(m==s))
   if len(ix)>=30:per.append([[corr(P[ix,j].astype(float),y[ix]),corr(rankdata(P[ix,j]),rankdata(y[ix]))] for j in range(3)])
  for j in range(3):
   pp=R[row,j].astype(float);yy=y[row];cal.append({'sigma':float(pp.std()/yy.std()),'beta':corr(pp,yy)*float(yy.std()/pp.std())})
  out[name]={'anchors':int(use.sum()),'days':len(day),'rows':int(row.sum()),'means':M[use].mean(0).tolist(),'new_minus_old_full_and_peer':ds.mean(0).tolist(),'descriptive_CI_5d':ci(ds,5),'descriptive_CI_10d':ci(ds,10),'per_asset_P_S':np.nanmean(per,axis=0).tolist(),'assets':len(per),'return_calibration':cal}
 np.savez_compressed(root/'ALIGNED_METRICS.npz',anchors=T,metrics=M,count=cnt)
 for p,h in c['inputs'].items():
  if sha(p)!=h:raise ValueError('input changed')
 res={'status':'DESCRIPTIVE_BRIDGE_ONLY','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'contract_sha256':sha(contract),'inputs':c['inputs'],'axis':{'anchors':n,'member_rows':nr,'old_excluded_tail_anchors':len(a['anchors'])-n,'members_labels_ranks':'exact including unknown mask','same_full_baseline_training_row_counts':True},'model_order':['old_full_78_NC','old_peer_82_NC_common_fallback','new_full_102_D10_own_pricepeer_controls'],'metric_order':['raw_P','rankIC','gross1_rank_price_bps_no_cost'],'windows':windows,'results':out,'max_original_metric_error':maxdiff,'outputs':{'ALIGNED_METRICS.npz':sha(root/'ALIGNED_METRICS.npz')},'seconds':time.monotonic()-start,'python':sys.executable,'numpy':np.__version__,'limitations':['Already viewed models and periods; no independent prospective selection','Bundled funding policy / own controls / price peers / missingness changes: cannot identify a single cause','Price-only static ranks; not whole-book cash or current King model','No refit and no new model promotion']}
 (root/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n')
 print(json.dumps({'status':res['status'],'seconds':res['seconds'],'axis':res['axis'],'recent':out['recent_H2']}))

if __name__=='__main__':
 try:main(*sys.argv[1:])
 except BaseException as e:
  r=Path(sys.argv[1]);r.mkdir(exist_ok=True);(r/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()})+'\n');raise

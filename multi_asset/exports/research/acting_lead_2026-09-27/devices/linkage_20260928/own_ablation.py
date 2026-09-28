"""Fixed ordered ablation, mechanism diagnosis only; no selection gate."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import json,sys,time,traceback,resource
import numpy as np
from scipy.stats import rankdata
from flow_ridge import sha,anchor_weights,month_masks,fit_ridge,predict,calibrate,metric,corr,add_own_interaction
from flow_funding import baseline_inputs
from prediction_bridge import align_prefix,complete_daily,ci

def encoded(x):return np.c_[np.where(np.isfinite(x),x,0),np.isfinite(x).astype(float)]
def own_designs(x,o):
 x=np.asarray(x);o=np.asarray(o)
 if x.ndim!=2 or x.shape[1]!=78 or o.shape!=(len(x),8) or not np.isfinite(x).all() or np.isinf(o).any():raise ValueError('design input')
 fund=np.c_[x[:,:76],encoded(o[:,:4])];price=np.c_[fund,encoded(o[:,4:6])];flow=np.c_[price,encoded(o[:,6:8])]
 product=add_own_interaction(flow,o)
 return [x,fund,price,flow,product]

def main(root,cp):
 begun=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);C=json.loads(Path(cp).read_text())
 for p,h in C['inputs'].items():
  if sha(p)!=h:raise ValueError('identity '+p)
 for n,h in C['helpers'].items():
  if sha(Path(__file__).with_name(n))!=h:raise ValueError('helper '+n)
 a=dict(np.load(Path(C['price_root'])/'PREDICTIONS.npz'));b=dict(np.load(Path(C['flow_root'])/'PREDICTIONS.npz'));n,nr=align_prefix(a,b)
 fr=json.loads((Path(C['flow_root'])/'RESULT.json').read_text());T=b['anchors'];off=b['off'];m=b['m'];y=b['raw_y'];yr=b['rank_y'];cnt=b['count'];rid=np.repeat(np.arange(n),cnt);at=T[rid]
 f=np.load(C['old_features']);g=np.load(C['new_features']);fo=f['off'];go=g['off'];fa=f['anchors'];ga=g['anchors'];begin=int(np.searchsorted(fa,T[0]));end=int(np.searchsorted(ga,T[-1],side='right'))
 if not np.array_equal(T,np.r_[fa[begin:],ga[1:end]]) or not np.array_equal(m,np.r_[f['m'][fo[begin]:],g['m'][go[1]:go[end]]]):raise ValueError('feature axis')
 if not np.array_equal(f['symbols'],b['symbols']) or not np.array_equal(g['symbols'],b['symbols']):raise ValueError('feature symbols')
 X=np.concatenate([f['X78'][fo[begin]:],g['king_X78'][go[1]:go[end]]]);newstart=len(fa)-begin
 # Recent saved features carry NC funding. Replace only these two slots with
 # causal D10 last-event values without an age filter, to isolate policy.
 fs=dict(np.load(C['fund_state']));lookup={int(c):i for i,c in enumerate(fs['cols'])};syms=b['symbols']
 for k in range(newstart,n):
  for row in range(off[k],off[k+1]):
   col=int(m[row]);si=lookup[col];lo,hi=fs['ev_off'][si:si+2];i=int(np.searchsorted(fs['ft'][lo:hi],T[k],side='right')-1)
   if i<0:raise ValueError('no D10 event')
   q=int(lo+i);X[row,-2:]=[fs['ema'][q],fs['rate'][q]]
 z=np.load(C['panel']);pa=z['anchors'];ai=np.searchsorted(pa,T)
 if not np.array_equal(pa[ai],T) or not np.array_equal(z['symbols'],syms):raise ValueError('panel axis')
 own=z['own'][ai[rid],m];price=z['price'][ai[rid],m];designs=own_designs(X,own)
 full=add_own_interaction(baseline_inputs(X,own,price),own)
 names=['NC78','D10_78','FUND84','PRICE88','FLOW92','PRODUCT94','FULL102']
 P=np.full((nr,7),np.nan,np.float32);RP=np.full_like(P,np.nan);P[:,0]=a['pred'][:nr,0];P[:,-1]=b['pred'][:,0];RP[:,0]=a['return_pred'][:nr,0];RP[:,-1]=b['return_pred'][:,0];folds=[]
 for f0 in fr['folds']:
  mo=np.datetime64(f0['month']);st=int(mo.astype('datetime64[s]').astype('int64'));en=int((mo+1).astype('datetime64[s]').astype('int64'));tr,te=month_masks(at,st,en);tr&=np.isfinite(yr);train=np.flatnonzero(tr);test=np.flatnonzero(te);w=anchor_weights(at[train])
  if len(train)!=f0['train_rows'] or len(np.unique(at[train]//86400))<180:raise ValueError('training population')
  # Strong positive control: rebuild stored FULL102 inference from this exact
  # panel, old frozen model and column ordering, not a self-copy of its score.
  saved=dict(np.load(Path(C['flow_root'])/f'{mo}_baseline_full.npz'))
  if not np.array_equal(predict(saved,full[test]).astype(np.float32),P[test,-1]):raise ValueError('FULL102 inference mismatch')
  for j,x in enumerate(designs,1):
   if time.monotonic()-begun>C['budget_seconds']:raise TimeoutError('budget')
   model=fit_ridge(x[train],yr[train],w);P[test,j]=predict(model,x[test]);cal=calibrate(predict(model,x[train]),y[train],w);RP[test,j]=cal[0]+cal[1]*P[test,j]
   np.savez_compressed(root/f'{mo}_{names[j]}.npz',**model,return_calibration=cal)
  folds.append({'month':str(mo),'train_rows':len(train),'test_rows':len(test),'last_label_end':int(at[train].max()+14400)})
  print('month',str(mo),'seconds',round(time.monotonic()-begun,2),flush=True)
 M=np.full((n,7,3),np.nan);coverage=np.zeros(n,int)
 for k in range(n):
  sl=np.arange(off[k],off[k+1]);mask=np.isfinite(P[sl]);
  if not np.array_equal(mask,np.broadcast_to(mask[:,0,None],mask.shape)):raise ValueError('prediction coverage')
  ix=sl[np.isfinite(y[sl])&mask.all(1)];coverage[k]=len(ix)
  if len(ix)>=50:
   for j in range(7):M[k,j]=metric(P[ix,j].astype(float),y[ix])
 results={};assetrows={j:np.flatnonzero(m==j) for j in np.unique(m)}
 for name,(lo,hi) in fr['windows'].items():
  st=lambda s:int(np.datetime64(s,'s').astype('int64'));use=(T>=st(lo))&(T<st(hi))
  if not np.isfinite(M[use]).all():raise ValueError('missing outcome')
  day=complete_daily(T[use],M[use]);delta=day[:,1:]-day[:,:-1];pairs=day[:,1:]-day[:,0,None,:]
  row=use[rid]&np.isfinite(y)&np.isfinite(P).all(1);per=[];cal=[]
  for ix0 in assetrows.values():
   ix=ix0[row[ix0]]
   if len(ix)>=30:per.append([[corr(P[ix,j].astype(float),y[ix]),corr(rankdata(P[ix,j]),rankdata(y[ix]))] for j in range(7)])
  for j in range(7):
   pp=RP[row,j].astype(float);yy=y[row];cal.append({'sigma':float(pp.std()/yy.std()),'beta':float(corr(pp,yy)*yy.std()/pp.std())})
  results[name]={'days':len(day),'anchors':int(use.sum()),'means':M[use].mean(0).tolist(),'successive_deltas':delta.mean(0).tolist(),'delta_CI_5d':ci(delta,5),'delta_CI_10d':ci(delta,10),'vs_NC':pairs.mean(0).tolist(),'vs_NC_CI_5d':ci(pairs,5),'per_asset_P_S':np.nanmean(per,axis=0).tolist(),'assets':len(per),'return_calibration':cal}
 np.savez_compressed(root/'PREDICTIONS.npz',anchors=T,count=cnt,off=off,m=m,symbols=syms,raw_y=y,rank_y=yr,pred=P,return_pred=RP,metrics=M,coverage=coverage)
 for p,h in C['inputs'].items():
  if sha(p)!=h:raise ValueError('input changed')
 res={'status':'ORDERED_MECHANISM_ONLY_NO_PROMOTION','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'contract_sha256':sha(cp),'inputs':C['inputs'],'model_order':names,'metric_order':['raw_P','rankIC','gross1_rank_price_bps_no_cost'],'folds':folds,'windows':fr['windows'],'results':results,'stored_FULL102_inference':'every scored row bitwise equal','seconds':time.monotonic()-begun,'peak_rss_gib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,'python':sys.executable,'numpy':np.__version__,'outputs':{p.name:sha(p) for p in root.glob('*.npz')},'limits':['Ex post fixed ordered ablation, ordering-dependent attribution','No GPU/promotion/deployment; prior failed gates remain','Static price only, no carry/cost/production combination','Does not identify whether a causal policy caused realized returns']}
 (root/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print('ABLATION COMPLETE',flush=True)

if __name__=='__main__':
 try:main(*sys.argv[1:])
 except BaseException as e:
  r=Path(sys.argv[1]);r.mkdir(exist_ok=True);(r/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2)+'\n');raise

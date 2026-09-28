"""Incremental peer-flow/funding Ridge screen on common D10 funding controls."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import hashlib,json,sys,time,traceback,resource
import numpy as np
from scipy.stats import rankdata
from flow_funding import baseline_inputs

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def anchor_weights(a):
 _,ix,c=np.unique(a,return_inverse=True,return_counts=True);w=1./c[ix];return w/w.sum()
def month_masks(t,start,end):
 t=np.asarray(t);return (t>=start-365*86400)&(t+14400<start-12*14400),(t>=start)&(t<end)
def fit_ridge(x,y,w,alpha=.01):
 x=np.asarray(x,float);y=np.asarray(y,float);w=np.asarray(w,float)
 if x.ndim!=2 or y.shape!=(len(x),) or w.shape!=y.shape or not all(np.isfinite(a).all() for a in (x,y,w)) or (w<0).any() or w.sum()<=0:raise ValueError('ridge finite input/weights')
 w=w/w.sum();mu=w@x;v=w@(x*x)-mu*mu;scale=np.sqrt(np.maximum(v,0));scale[scale<1e-12]=1
 z=(x-mu)/scale;ym=w@y;gram=z.T@(w[:,None]*z);rhs=z.T@(w*(y-ym));coef=np.linalg.solve(gram+alpha*np.eye(x.shape[1]),rhs)
 return {'mean':mu,'scale':scale,'coef':coef,'intercept':float(ym)}
def predict(model,x):return ((x-model['mean'])/model['scale'])@model['coef']+model['intercept']
def calibrate(score,raw_y,w):
 w=w/w.sum();pm=w@score;ym=w@raw_y;v=w@((score-pm)**2)
 slope=float(w@((score-pm)*(raw_y-ym))/v) if v>1e-16 else 0.
 return np.array([float(ym-slope*pm),slope])
def corr(x,y):
 x=x-x.mean();y=y-y.mean();d=np.sqrt(x@x*(y@y));return float(x@y/d) if d>0 else np.nan
def stamp(s):return int(np.datetime64(s,'s').astype('int64'))
def metric(p,y):
 r=rankdata(p);z=r-r.mean();g=np.abs(z).sum()
 return np.array([corr(p,y),corr(r,rankdata(y)),float(z@y/g*1e4) if g else np.nan])
def bci(d,block):
 if len(d)<2*block:return None
 rng=np.random.default_rng(20260928+block);starts=rng.integers(0,len(d)-block+1,size=(2000,int(np.ceil(len(d)/block))))
 ix=(starts[:,:,None]+np.arange(block)).reshape(2000,-1)[:,:len(d)]
 return np.quantile(d[ix].mean(1),[.025,.975]).tolist()

def main(root,contract_path):
 begun=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);C=json.loads(Path(contract_path).read_text());pins=C['inputs'].copy()
 panel=Path(C['panel_root']);t=json.loads((panel/'TERMINAL.json').read_text());pr=json.loads((panel/'RESULT.json').read_text())
 if t['rc']!=0 or t['result_sha256']!=sha(panel/'RESULT.json') or pr['contract_sha256']!=C['panel_contract_sha256']:raise ValueError('panel gate')
 for n,h in pr['outputs'].items():pins[str(panel/n)]=h
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('source identity '+p)
 for n,h in C['helpers'].items():
  if sha(Path(__file__).with_name(n))!=h:raise ValueError('helper identity '+n)
 z=np.load(panel/'FLOW_FUND_PEERS.npz');A=z['anchors'];sy=z['symbols'];PX=z['X'];Y=z['y4_raw'];OWN=z['own'];PRICE=z['price']
 old=np.load(C['old_features']);new=np.load(C['new_features']);assert np.array_equal(old['symbols'],sy) and np.array_equal(new['symbols'],sy)
 oa=old['anchors'];na=new['anchors'];oc=old['count'];oo=old['off'];nc=new['count'];no=new['off'];om=old['m'];nm=new['m'];ox=old['X78'];nx=new['king_X78']
 assert oa[-1]==na[0] and np.array_equal(om[oo[-2]:oo[-1]],nm[no[0]:no[1]]) and np.array_equal(ox[oo[-2]:oo[-1],:76],nx[no[0]:no[1],:76])
 begin=np.searchsorted(oa,C['data_start']);last=np.searchsorted(na,C['eval_end'],side='left')
 T=np.r_[oa[begin:],na[1:last]];count=np.r_[oc[begin:],nc[1:last]];off=np.r_[0,np.cumsum(count)];m=np.r_[om[oo[begin]:],nm[no[1]:no[last]]]
 X=np.concatenate([ox[oo[begin]:],nx[no[1]:no[last]]]);del ox,nx
 assert np.all(np.diff(T)==14400) and X.shape==(len(m),78) and np.isfinite(X).all()
 ai=np.searchsorted(A,T);assert np.all(ai<len(A)) and np.array_equal(A[ai],T)
 rid=np.repeat(np.arange(len(T)),count);rows=PX[ai[rid],m];own=OWN[ai[rid],m];price=PRICE[ai[rid],m];y=Y[ai[rid],m];finite=np.isfinite(y);haspeer=np.isfinite(rows).all(1)&np.isfinite(own).all(1)&np.isfinite(price).all(1);yr=np.full(len(y),np.nan)
 X=baseline_inputs(X,own,price);del OWN,PRICE,own,price
 shuffled=rows.copy();min_names=50
 for k in range(len(T)):
  sl=np.arange(off[k],off[k+1]);good=sl[finite[sl]]
  if len(good)>=min_names:yr[good]=rankdata(y[good])/(len(good)-1)-.5
  ps=sl[haspeer[sl]]
  if len(ps):
   # Fixed name rotation, identical at each anchor, no label use.
   ix=np.argsort(sy[m[ps]]);pp=ps[ix];shuffled[pp]=rows[np.roll(pp,max(1,len(pp)//2))]
 pred=np.full((len(m),4),np.nan,np.float32);return_pred=np.full_like(pred,np.nan);folds=[];allts=T[rid]
 months=np.arange(np.datetime64('2023-07'),np.datetime64('2026-10'),dtype='datetime64[M]')
 for mo in months:
  start=int(mo.astype('datetime64[s]').astype('int64'));end=int((mo+1).astype('datetime64[s]').astype('int64'));tr,te=month_masks(allts,start,end)
  tr &= np.isfinite(yr);common=tr&haspeer;test=np.flatnonzero(te);train=np.flatnonzero(tr);co=np.flatnonzero(common)
  if not len(test):continue
  if len(np.unique(allts[co]//86400))<180:raise ValueError('insufficient training days '+str(mo))
  if time.monotonic()-begun>C['budget_seconds']:raise TimeoutError('ridge budget')
  wf=anchor_weights(allts[train]);wc=anchor_weights(allts[co]);models=[]
  bfull=fit_ridge(X[train],yr[train],wf);b=fit_ridge(X[co],yr[co],wc)
  c=fit_ridge(np.c_[X[co],rows[co]],yr[co],wc);s=fit_ridge(np.c_[X[co],shuffled[co]],yr[co],wc)
  pred[test,0]=predict(bfull,X[test]);pred[test,1]=predict(b,X[test]);pred[test,2]=pred[test,1];pred[test,3]=pred[test,1]
  tv=test[haspeer[test]];pred[tv,2]=predict(c,np.c_[X[tv],rows[tv]]);pred[tv,3]=predict(s,np.c_[X[tv],shuffled[tv]])
  cc=[calibrate(predict(bfull,X[train]),y[train],wf),calibrate(predict(b,X[co]),y[co],wc),calibrate(predict(c,np.c_[X[co],rows[co]]),y[co],wc),calibrate(predict(s,np.c_[X[co],shuffled[co]]),y[co],wc)]
  for j in range(4):return_pred[test,j]=cc[j][0]+cc[j][1]*pred[test,j]
  for j in (2,3):return_pred[test[~haspeer[test]],j]=return_pred[test[~haspeer[test]],1]
  assert allts[co].max()+14400<start-12*14400
  for label,model in zip(('baseline_full','baseline_common','peer','shuffled'),(bfull,b,c,s)):
   np.savez_compressed(root/f'{mo}_{label}.npz',**model,return_calibration=cc[('baseline_full','baseline_common','peer','shuffled').index(label)])
  folds.append({'month':str(mo),'train_rows':len(train),'common_rows':len(co),'training_first_anchor':int(allts[co].min()),'last_label_end':int(allts[co].max()+14400),'test_rows':len(test),'peer_test_rows':len(tv)})
  print('fold',str(mo),'elapsed',round(time.monotonic()-begun,2),flush=True)
 metrics=np.full((len(T),2,4,3),np.nan);coverage=np.zeros((len(T),2),int)
 for k in range(len(T)):
  sl=np.arange(off[k],off[k+1]);good=sl[finite[sl]&np.isfinite(pred[sl]).all(1)]
  for pop,ix in enumerate((good,good[haspeer[good]])):
   coverage[k,pop]=len(ix)
   if len(ix)>=min_names:
    for j in range(4):metrics[k,pop,j]=metric(pred[ix,j].astype(float),y[ix])
 windows={'recent_H2':('2026-07-01','2026-09-27'),'september':('2026-09-01','2026-09-27'),'2026_H1':('2026-01-01','2026-07-01'),'2025':('2025-01-01','2026-01-01'),'2024':('2024-01-01','2025-01-01'),'2023_H2':('2023-07-01','2024-01-01')};results={};asset_rows={j:np.flatnonzero(m==j) for j in np.unique(m)}
 for name,(lo,hi) in windows.items():
  use=(T>=stamp(lo))&(T<stamp(hi));out={}
  for pop,label in enumerate(('all_with_baseline_fallback','common_peer')):
   good=use&np.isfinite(metrics[:,pop]).all((1,2));vals=metrics[good,pop];tt=T[good]
   mean=vals.mean(0);day=[]
   for d in np.unique(tt//86400):
    ix=tt//86400==d
    if ix.sum()==6:day.append((vals[ix,2,1]-vals[ix,1,1]).mean())
   byasset=[];calibration=[];rowgood=use[rid]&finite&np.isfinite(pred).all(1)&(haspeer if pop else True)
   for j,ix0 in asset_rows.items():
    ix=ix0[rowgood[ix0]]
    if len(ix)>=30:byasset.append([[corr(pred[ix,k].astype(float),y[ix]),corr(rankdata(pred[ix,k]),rankdata(y[ix]))] for k in range(4)])
   ix=np.flatnonzero(rowgood)
   for k in range(4):
    pp=return_pred[ix,k].astype(float);yy=y[ix];vp=float(pp.var());calibration.append({'sigma_pred_over_y':float(pp.std()/yy.std()),'beta_y_on_pred':float(np.mean((pp-pp.mean())*(yy-yy.mean()))/vp) if vp else None,'calibration_fit':'past training rows only'})
   out[label]={'anchors':int(good.sum()),'mean_price_P_S_and_rankprice_bps':mean.tolist(),'peer_minus_matched_baseline':(mean[2]-mean[1]).tolist(),'shuffle_minus_matched_baseline':(mean[3]-mean[1]).tolist(),'peer_coverage_ratio':float(coverage[good,1].sum()/coverage[good,0].sum()),'full_days_for_CI':len(day),'rankIC_delta_CI_5d':bci(np.array(day),5),'rankIC_delta_CI_10d':bci(np.array(day),10),'assets_measured':len(byasset),'per_asset_P_S_means':np.nanmean(byasset,axis=0).tolist(),'return_calibrated_diagnostics':calibration}
  results[name]=out
 r=results['recent_H2']['all_with_baseline_fallback'];s=results['september']['all_with_baseline_fallback']
 gates={'recent_rankIC_delta_ge_005':r['peer_minus_matched_baseline'][1]>=.005,'recent_raw_P_not_lower':r['peer_minus_matched_baseline'][0]>=0,'september_rankIC_not_lower':s['peer_minus_matched_baseline'][1]>=0,'september_rankprice_not_lower':s['peer_minus_matched_baseline'][2]>=0,'old_regime_no_severe_flip':all(results[w]['all_with_baseline_fallback']['peer_minus_matched_baseline'][1]>=-.005 for w in ('2023_H2','2024','2025','2026_H1')),'better_than_scrambled_context':r['peer_minus_matched_baseline'][1]>r['shuffle_minus_matched_baseline'][1]}
 gates['recent_calibrated_sigma_ratio_ge_002']=r['return_calibrated_diagnostics'][2]['sigma_pred_over_y']>=.02
 np.savez_compressed(root/'PREDICTIONS.npz',anchors=T,count=count,off=off,m=m,symbols=sy,raw_y=y,rank_y=yr,pred=pred,return_pred=return_pred,has_peer=haspeer,metrics=metrics,coverage=coverage)
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input changed '+p)
 res={'status':'EXPLORATORY_SCREEN_PASS' if all(gates.values()) else 'CRITERION_NOT_MET','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'contract_sha256':sha(contract_path),'inputs':pins,'folds':folds,'windows':windows,'results':results,'gates':gates,'metric_order':['raw_y_Pearson','raw_y_Spearman','gross_one_rank_price_bps_no_cost'],'prediction_order':['baseline_full','baseline_common','peer','shuffled'],'prediction_units':'cross-sectional rank scores, not calibrated returns','baseline_definition':'76 nonfund NC/D10 columns + 8 own D10/price/flow values and 8 availability flags + 4 prior price-peer values and 4 availability flags; candidate adds only three interactions','funding_policy':'D10 exact spacing convention, identical in every arm, not deployed NC policy','seconds':time.monotonic()-begun,'peak_rss_gib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,'python':sys.executable,'numpy':np.__version__,'outputs':{p.name:sha(p) for p in root.glob('*.npz')},'limits':['Historical windows have been seen: not confirmatory','No cash/fees/funding/combination state, no production model or release','Unknown peer entries revert exactly to matched baseline','Per-asset calibration/collapse interpretation requires return-unit prediction; these are rank scores']}
 (root/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print('RIDGE COMPLETE',res['status'],flush=True)
if __name__=='__main__':
 try:main(*sys.argv[1:])
 except BaseException as e:
  r=Path(sys.argv[1]);r.mkdir(exist_ok=True);(r/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2)+'\n');raise

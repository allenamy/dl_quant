"""Does own residual strength add to frozen OOF King/F10? Fixed CPU screen."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import json,sys,time,traceback,resource
import numpy as np
from scipy.stats import rankdata
from flow_ridge import sha,anchor_weights,month_masks,fit_ridge,predict,calibrate,metric,corr
from own_ablation import encoded
from prediction_bridge import complete_daily,ci

def score_ranks(v):
 v=np.asarray(v);ok=np.isfinite(v);r=np.full(v.shape,np.nan)
 if ok.sum()>1:r[ok]=(rankdata(v[ok])-1)/(ok.sum()-1)-.5
 return r
def conditional_design(x,own,scores):
 return np.c_[x[:,:76],encoded(own[:,:4]),scores],encoded(own[:,4:6])
def load_scores(old,new,T,syms):
 a=np.load(old);b=np.load(new);ta=a['E_ts'];tb=b['E_ts'];pa=a['P'];pb=b['P']
 if not np.array_equal(a['symbols'],syms) or not np.array_equal(b['symbols'],syms) or ta[-1]!=tb[0] or not np.array_equal(pa[-1],pb[0],equal_nan=True):raise ValueError('prediction boundary')
 ts=np.r_[ta,tb[1:]];p=np.r_[pa,pb[1:]];ix=np.searchsorted(ts,T)
 if not np.array_equal(ts[ix],T):raise ValueError('prediction axis')
 return p[ix]

def main(root,cp):
 begun=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);C=json.loads(Path(cp).read_text())
 for p,h in C['inputs'].items():
  if sha(p)!=h:raise ValueError('identity '+p)
 for n,h in C['helpers'].items():
  if sha(Path(__file__).with_name(n))!=h:raise ValueError('helper '+n)
 z=dict(np.load(C['reference_predictions']));T=z['anchors'];off=z['off'];cnt=z['count'];m=z['m'];y=z['raw_y'];yr=z['rank_y'];sy=z['symbols'];rid=np.repeat(np.arange(len(T)),cnt);at=T[rid]
 a=np.load(C['old_features']);b=np.load(C['new_features']);ao=a['off'];bo=b['off'];begin=np.searchsorted(a['anchors'],T[0]);end=np.searchsorted(b['anchors'],T[-1],side='right')
 if not np.array_equal(T,np.r_[a['anchors'][begin:],b['anchors'][1:end]]) or not np.array_equal(m,np.r_[a['m'][ao[begin]:],b['m'][bo[1]:bo[end]]]):raise ValueError('feature population')
 X=np.r_[a['X78'][ao[begin]:,:76],b['king_X78'][bo[1]:bo[end],:76]]
 panel=np.load(C['panel']);ix=np.searchsorted(panel['anchors'],T)
 if not np.array_equal(panel['anchors'][ix],T) or not np.array_equal(panel['symbols'],sy):raise ValueError('panel')
 own=panel['own'][ix[rid],m];king=load_scores(*C['king'],T,sy);kp=np.full(len(m),np.nan)
 for k in range(len(T)):kp[off[k]:off[k+1]]=score_ranks(king[k,m[off[k]:off[k+1]]])
 P=np.full((len(m),6),np.nan,np.float32);RP=np.full_like(P,np.nan);eligible=np.zeros((len(m),2),bool);folds=[]
 for si,seed in enumerate((42,2027)):
  f10=load_scores(*C['f10'][str(seed)],T,sy);sp=np.full(len(m),np.nan)
  for k in range(len(T)):sp[off[k]:off[k+1]]=score_ranks(f10[k,m[off[k]:off[k+1]]])
  base,extra=conditional_design(X,own,np.c_[kp,sp]);eligible[:,si]=np.isfinite(base).all(1);shuf=extra.copy()
  for k in range(len(T)):
   sl=np.arange(off[k],off[k+1]);j=sl[np.argsort(sy[m[sl]])];shuf[j]=extra[np.roll(j,max(1,len(j)//2))]
  designs=[base,np.c_[base,extra],np.c_[base,shuf]]
  for mo in np.arange(np.datetime64('2023-08'),np.datetime64('2026-10'),dtype='datetime64[M]'):
   st=int(mo.astype('datetime64[s]').astype('int64'));en=int((mo+1).astype('datetime64[s]').astype('int64'));tr,te=month_masks(at,st,en);tr&=np.isfinite(yr)&eligible[:,si];te&=eligible[:,si];train=np.flatnonzero(tr);test=np.flatnonzero(te)
   if len(np.unique(at[train]//86400))<180:raise ValueError('training days '+str(mo))
   w=anchor_weights(at[train])
   for j,x in enumerate(designs):
    if time.monotonic()-begun>C['budget_seconds']:raise TimeoutError('budget')
    model=fit_ridge(x[train],yr[train],w);P[test,si*3+j]=predict(model,x[test]);c=calibrate(predict(model,x[train]),y[train],w);RP[test,si*3+j]=c[0]+c[1]*P[test,si*3+j];np.savez_compressed(root/f's{seed}_{mo}_{j}.npz',**model,return_calibration=c)
   folds.append({'seed':seed,'month':str(mo),'train_rows':len(train),'test_rows':len(test),'last_label_end':int(at[train].max()+14400)})
   print('fold',seed,str(mo),'seconds',round(time.monotonic()-begun,2),flush=True)
 M=np.full((len(T),6,3),np.nan);coverage=np.zeros((len(T),2),int);total=np.zeros(len(T),int)
 for k in range(len(T)):
  sl=np.arange(off[k],off[k+1]);total[k]=np.isfinite(y[sl]).sum()
  for si in range(2):
   cols=np.arange(si*3,si*3+3);mask=np.isfinite(P[sl][:,cols]);assert np.array_equal(mask,np.broadcast_to(mask[:,0,None],mask.shape));good=sl[np.isfinite(y[sl])&mask.all(1)];coverage[k,si]=len(good)
   if len(good)>=50:
    for j in cols:M[k,j]=metric(P[good,j].astype(float),y[good])
 windows={'recent_H2':['2026-07-01','2026-09-27'],'september':['2026-09-01','2026-09-27'],'2026_H1':['2026-01-01','2026-07-01'],'2025':['2025-01-01','2026-01-01'],'2024':['2024-01-01','2025-01-01'],'2023_AugDec':['2023-08-01','2024-01-01']};results={};assetrows={j:np.flatnonzero(m==j) for j in np.unique(m)}
 for name,(lo,hi) in windows.items():
  st=lambda s:int(np.datetime64(s,'s').astype('int64'));use=(T>=st(lo))&(T<st(hi));out={}
  if not np.isfinite(M[use]).all():raise ValueError('unknown outcome '+name)
  for si,seed in enumerate((42,2027)):
   cols=np.arange(si*3,si*3+3);vals=M[use][:,cols];day=complete_daily(T[use],vals);d=day[:,1]-day[:,0];ds=day[:,2]-day[:,0];row=use[rid]&np.isfinite(y)&np.isfinite(P[:,cols]).all(1);per=[];cal=[]
   for ix0 in assetrows.values():
    ix=ix0[row[ix0]]
    if len(ix)>=30:per.append([[corr(P[ix,j].astype(float),y[ix]),corr(rankdata(P[ix,j]),rankdata(y[ix]))] for j in cols])
   for j in cols:
    pp=RP[row,j].astype(float);yy=y[row];cal.append({'sigma':float(pp.std()/yy.std()),'beta':float(corr(pp,yy)*yy.std()/pp.std())})
   out[str(seed)]={'anchors':int(use.sum()),'days':len(day),'coverage':float(coverage[use,si].sum()/total[use].sum()),'means':vals.mean(0).tolist(),'candidate_delta':d.mean(0).tolist(),'shuffle_delta':ds.mean(0).tolist(),'CI_5d':ci(d,5),'CI_10d':ci(d,10),'per_asset_P_S':np.nanmean(per,axis=0).tolist(),'assets':len(per),'return_calibration':cal}
  results[name]=out
 gates={}
 for seed in ('42','2027'):
  r=results['recent_H2'][seed];s=results['september'][seed];gates[seed]={'coverage':min(r['coverage'],s['coverage'])>=.99,'recent_rankIC_ge_005':r['candidate_delta'][1]>=.005,'recent_raw_P_nonnegative':r['candidate_delta'][0]>=0,'september_rankIC_nonnegative':s['candidate_delta'][1]>=0,'september_rankprice_nonnegative':s['candidate_delta'][2]>=0,'old_regime_bound':all(results[w][seed]['candidate_delta'][1]>=-.005 for w in ('2023_AugDec','2024','2025','2026_H1')),'beat_shuffled':r['candidate_delta'][1]>r['shuffle_delta'][1],'sigma_ge_002':r['return_calibration'][1]['sigma']>=.02}
 np.savez_compressed(root/'PREDICTIONS.npz',anchors=T,count=cnt,off=off,m=m,symbols=sy,raw_y=y,rank_y=yr,pred=P,return_pred=RP,metrics=M,coverage=coverage,eligible=eligible)
 for p,h in C['inputs'].items():
  if sha(p)!=h:raise ValueError('input changed')
 res={'status':'CONDITIONAL_SCREEN_PASS_NOT_RELEASE' if all(all(g.values()) for g in gates.values()) else 'CRITERION_NOT_MET','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'contract_sha256':sha(cp),'inputs':C['inputs'],'model_order':['s42_baseline','s42_candidate','s42_shuffle','s2027_baseline','s2027_candidate','s2027_shuffle'],'metric_order':['raw_P','rankIC','gross1_rank_price_bps_no_cost'],'folds':folds,'windows':windows,'results':results,'gates':gates,'seconds':time.monotonic()-begun,'peak_rss_gib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,'python':sys.executable,'numpy':np.__version__,'outputs':{p.name:sha(p) for p in root.glob('*.npz')},'limits':['Historical conditional feature screen, no prospective evidence','Conditions on existing NC King/F10, not D10-retrained versions','No whole-book cash or release decision','2023 starts August because OOF F10 training history is insufficient in July']}
 (root/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print('CONDITIONAL COMPLETE',res['status'],flush=True)

if __name__=='__main__':
 try:main(*sys.argv[1:])
 except BaseException as e:
  r=Path(sys.argv[1]);r.mkdir(exist_ok=True);(r/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2)+'\n');raise

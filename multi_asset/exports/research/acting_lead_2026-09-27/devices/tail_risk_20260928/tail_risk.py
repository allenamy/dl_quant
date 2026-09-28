"""Fixed monthly causal screen for two-sided outcome-tail information; not a book."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import sys,json,time,resource,traceback,signal
import numpy as np
from scipy.stats import rankdata
from flow_ridge import sha,anchor_weights,month_masks,predict,calibrate,metric,corr
from conditional_strength import score_ranks,conditional_design,load_scores
from prediction_bridge import complete_daily,ci


def tail_labels(y):
 y=np.asarray(y,float)
 if y.ndim!=1 or np.isinf(y).any():raise ValueError('target shape/inf')
 good=np.flatnonzero(np.isfinite(y))
 if len(good)<50:raise ValueError('insufficient label population')
 order=good[np.argsort(y[good],kind='stable')];n=int(np.ceil(.05*len(good)))
 out=np.full((len(y),2),np.nan);out[good]=0;out[order[-n:],0]=1;out[order[:n],1]=1
 return out

def fit_multi(x,y,w):
 x,y,w=[np.asarray(z,float) for z in (x,y,w)]
 if x.ndim!=2 or y.ndim!=2 or y.shape!=(len(x),2) or w.shape!=(len(x),) or not all(np.isfinite(z).all() for z in (x,y,w)) or (w<0).any() or w.sum()<=0:raise ValueError('fit finite population')
 w=w/w.sum();mu=w@x;scale=np.sqrt(np.maximum(w@(x*x)-mu*mu,0));scale[scale<1e-12]=1;z=(x-mu)/scale;ym=w@y
 coef=np.linalg.solve(z.T@(w[:,None]*z)+.01*np.eye(x.shape[1]),z.T@(w[:,None]*(y-ym)))
 return {'mean':mu,'scale':scale,'coef':coef,'intercept':ym}

def probabilities(raw):
 p=np.clip(np.asarray(raw,float),0,1)
 if p.ndim!=2 or p.shape[1]!=2 or not np.isfinite(p).all():raise ValueError('invalid probability score')
 return p/np.maximum(p.sum(1,keepdims=True),1.)

def auc(p,y):
 n=int(y.sum());m=len(y)-n
 if n==0 or m==0:raise ValueError('undefined auc')
 return float((rankdata(p)[y==1].sum()-n*(n+1)/2)/(n*m))

def probability_metrics(raw,y):
 p=probabilities(raw);y=np.asarray(y,float)
 if y.shape!=p.shape or not np.isfinite(y).all() or not np.isin(y,[0.,1.]).all() or (y.sum(1)>1).any():raise ValueError('invalid tail labels')
 tails=y.sum(1)==1
 return np.array([np.mean((p[:,0]-y[:,0])**2),np.mean((p[:,1]-y[:,1])**2),auc(p[:,0],y[:,0]),auc(p[:,1],y[:,1]),auc((p[:,0]-p[:,1])[tails],y[tails,0])])


def main(root,cp):
 begun=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);C=json.loads(Path(cp).read_text())
 resource.setrlimit(resource.RLIMIT_AS,(20*2**30,20*2**30));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 signal.signal(signal.SIGALRM,lambda *a:(_ for _ in ()).throw(TimeoutError('600s fixed budget')));signal.alarm(600)
 for p,h in C['inputs'].items():
  if sha(p)!=h:raise ValueError('input identity '+p)
 for n,h in C['helpers'].items():
  if sha(Path(__file__).with_name(n))!=h:raise ValueError('helper '+n)
 if sha(__file__)!=C['source_sha256']:raise ValueError('source identity')
 z=np.load(C['reference_predictions']);T=z['anchors'];off=z['off'];cnt=z['count'];m=z['m'];y=z['raw_y'];sy=z['symbols'];rid=np.repeat(np.arange(len(T)),cnt);at=T[rid]
 a=np.load(C['old_features']);b=np.load(C['new_features']);ao=a['off'];bo=b['off'];begin=np.searchsorted(a['anchors'],T[0]);end=np.searchsorted(b['anchors'],T[-1],side='right')
 if not np.array_equal(T,np.r_[a['anchors'][begin:],b['anchors'][1:end]]) or not np.array_equal(m,np.r_[a['m'][ao[begin]:],b['m'][bo[1]:bo[end]]]):raise ValueError('feature population')
 X=np.r_[a['X78'][ao[begin]:,:76],b['king_X78'][bo[1]:bo[end],:76]]
 panel=np.load(C['panel']);ix=np.searchsorted(panel['anchors'],T)
 if not np.array_equal(panel['anchors'][ix],T) or not np.array_equal(panel['symbols'],sy):raise ValueError('panel identity')
 own=panel['own'][ix[rid],m];king=load_scores(*C['king'],T,sy);kp=np.full(len(m),np.nan);Y=np.full((len(m),2),np.nan);perm=np.arange(len(m));tie_anchors=0
 for k in range(len(T)):
  sl=np.arange(off[k],off[k+1]);kp[sl]=score_ranks(king[k,m[sl]])
  if np.isfinite(y[sl]).sum()>=50:Y[sl]=tail_labels(y[sl]);tie_anchors+=int(np.ptp(y[sl][np.isfinite(y[sl])])==0)
  names=sl[np.isfinite(y[sl])];names=names[np.argsort(sy[m[names]])];perm[names]=np.roll(names,max(1,len(names)//2))
 nullY=Y[perm]
 prev=np.load(C['prior_predictions']);oldP=prev['pred'];oldRP=prev['return_pred']
 for key,value in [('anchors',T),('off',off),('m',m),('symbols',sy),('raw_y',y)]:
  if not np.array_equal(prev[key],value,equal_nan=(key=='raw_y')):raise ValueError('prior population '+key)
 P=np.full((len(m),6,2),np.nan,np.float32);RP=np.full((len(m),6),np.nan,np.float32);eligible=np.zeros((len(m),2),bool);folds=[]
 for si,seed in enumerate((42,2027)):
  f10=load_scores(*C['f10'][str(seed)],T,sy);sp=np.full(len(m),np.nan)
  for k in range(len(T)):
   sl=slice(off[k],off[k+1]);sp[sl]=score_ranks(f10[k,m[sl]])
  base,extra=conditional_design(X,own,np.c_[kp,sp]);full=np.c_[base,extra];scores=full[:,84:86];eligible[:,si]=np.isfinite(full).all(1)
  for mo in np.arange(np.datetime64('2023-08'),np.datetime64('2026-10'),dtype='datetime64[M]'):
   start=int(mo.astype('datetime64[s]').astype('int64'));stop=int((mo+1).astype('datetime64[s]').astype('int64'));tr,te=month_masks(at,start,stop);tr&=np.isfinite(Y).all(1)&eligible[:,si];te&=eligible[:,si];train=np.flatnonzero(tr);test=np.flatnonzero(te)
   if len(np.unique(at[train]//86400))<180:raise ValueError('training days '+str(mo))
   w=anchor_weights(at[train])
   for j,(design,lab) in enumerate(((scores,Y),(full,Y),(full,nullY))):
    if time.monotonic()-begun>C['budget_seconds']:raise TimeoutError('budget')
    model=fit_multi(design[train],lab[train],w);p=probabilities(predict(model,design[test]));P[test,si*3+j]=p
    fitp=probabilities(predict(model,design[train]));cal=calibrate(fitp[:,0]-fitp[:,1],y[train],w);RP[test,si*3+j]=cal[0]+cal[1]*(p[:,0]-p[:,1]);np.savez_compressed(root/f's{seed}_{mo}_{j}.npz',**model,return_calibration=cal)
   folds.append({'seed':seed,'month':str(mo),'train_rows':len(train),'test_rows':len(test),'last_label_end':int(at[train].max()+14400),'first_anchor':int(at[train].min())})
   print('fold',seed,str(mo),round(time.monotonic()-begun,2),flush=True)
  del full,base,extra
 Q=np.full((len(T),6,5),np.nan);M=np.full((len(T),8,3),np.nan);coverage=np.zeros((len(T),2),int);tot=np.zeros(len(T),int)
 for k in range(len(T)):
  sl=np.arange(off[k],off[k+1]);tot[k]=np.isfinite(y[sl]).sum()
  for si in range(2):
   cols=np.arange(si*3,si*3+3);good=sl[np.isfinite(y[sl])&np.isfinite(P[sl][:,cols]).all((1,2))&np.isfinite(oldP[sl,si*3+1])];coverage[k,si]=len(good)
   if len(good)<50:continue
   for j,col in enumerate(cols):Q[k,col]=probability_metrics(P[good,col],Y[good]);M[k,si*4+j]=metric((P[good,col,0]-P[good,col,1]).astype(float),y[good])
   M[k,si*4+3]=metric(oldP[good,si*3+1].astype(float),y[good])
 windows={'recent_H2':['2026-07-01','2026-09-27'],'september':['2026-09-01','2026-09-27'],'2026_H1':['2026-01-01','2026-07-01'],'2025':['2025-01-01','2026-01-01'],'2024':['2024-01-01','2025-01-01'],'2023_AugDec':['2023-08-01','2024-01-01']};results={}
 assetrows={j:np.flatnonzero(m==j) for j in np.unique(m)}
 for name,(lo,hi) in windows.items():
  stamp=lambda s:int(np.datetime64(s,'s').astype('int64'));use=(T>=stamp(lo))&(T<stamp(hi));out={}
  if not np.isfinite(Q[use]).all() or not np.isfinite(M[use]).all():raise ValueError('unmeasured window '+name)
  for si,seed in enumerate((42,2027)):
   cols=np.arange(si*3,si*3+3);q=Q[use][:,cols];p=M[use][:,si*4:si*4+4];day=complete_daily(T[use],q[:,1]-q[:,0]);dp=complete_daily(T[use],p[:,1]-p[:,3]);row=use[rid]&np.isfinite(y)&np.isfinite(P[:,cols]).all((1,2))&np.isfinite(oldP[:,si*3+1]);per=[];cal=[]
   for ix0 in assetrows.values():
    rr=ix0[row[ix0]]
    if len(rr)>=30:
     vals=[P[rr,j,0]-P[rr,j,1] for j in cols]+[oldP[rr,si*3+1]];per.append([[corr(v.astype(float),y[rr]),corr(rankdata(v),rankdata(y[rr]))] for v in vals])
   for j in cols:
    pp=RP[row,j].astype(float);yy=y[row];cal.append({'sigma':float(pp.std()/yy.std()),'beta':float(corr(pp,yy)*yy.std()/pp.std())})
   out[str(seed)]={'anchors':int(use.sum()),'days':len(day),'coverage':float(coverage[use,si].sum()/tot[use].sum()),'tail_metrics_means':q.mean(0).tolist(),'full_minus_score_only':day.mean(0).tolist(),'tail_delta_CI_5d':ci(day,5),'tail_delta_CI_10d':ci(day,10),'price_metric_means':p.mean(0).tolist(),'direction_minus_prior_rank_ridge':dp.mean(0).tolist(),'price_delta_CI_5d':ci(dp,5),'price_delta_CI_10d':ci(dp,10),'per_asset_P_S':np.nanmean(per,axis=0).tolist(),'assets':len(per),'return_calibration':cal}
  results[name]=out
 gates={};alpha={}
 for seed in ('42','2027'):
  r=results['recent_H2'][seed];s=results['september'][seed];gates[seed]={'coverage_ge99':min(r['coverage'],s['coverage'])>=.99,'upper_brier_better':r['full_minus_score_only'][0]<0,'lower_brier_better':r['full_minus_score_only'][1]<0,'direction_AUC_CI_5_and_10_positive':all(r[k][0][4]>0 for k in ('tail_delta_CI_5d','tail_delta_CI_10d')),'direction_beats_rotated_labels':r['tail_metrics_means'][1][4]>r['tail_metrics_means'][2][4],'september_direction_improves':s['full_minus_score_only'][4]>=0,'older_direction_above_random':all(results[w][seed]['tail_metrics_means'][1][4]>.5 for w in ('2023_AugDec','2024','2025','2026_H1'))}
  alpha[seed]={'rank_delta_ge003':r['direction_minus_prior_rank_ridge'][1]>=.003,'raw_P_nonnegative':r['direction_minus_prior_rank_ridge'][0]>=0,'september_rank_and_price_nonnegative':min(s['direction_minus_prior_rank_ridge'][1:])>=0,'older_rank_no_flip':all(results[w][seed]['direction_minus_prior_rank_ridge'][1]>=-.005 for w in ('2023_AugDec','2024','2025','2026_H1')),'return_sigma_ge002':r['return_calibration'][1]['sigma']>=.02}
 np.savez_compressed(root/'PREDICTIONS.npz',anchors=T,count=cnt,off=off,m=m,symbols=sy,raw_y=y,labels=Y,pred=P,return_pred=RP,eligible=eligible,coverage=coverage,tail_metrics=Q,price_metrics=M)
 for p,h in C['inputs'].items():
  if sha(p)!=h:raise ValueError('input changed '+p)
 rec={'status':'TAIL_MECHANISM_SUPPORTED_NOT_STRATEGY' if all(all(g.values()) for g in gates.values()) else 'NO_JOINT_TAIL_MECHANISM_EVIDENCE','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'contract_sha256':sha(cp),'inputs':C['inputs'],'folds':folds,'windows':windows,'results':results,'risk_gates':gates,'alpha_screen_gates':alpha,'tail_metric_order':['upper_Brier','lower_Brier','upper_AUC','lower_AUC','upper_vs_lower_AUC'],'model_order':['s42_score2','s42_full90','s42_rotated_labels','s2027_score2','s2027_full90','s2027_rotated_labels'],'price_model_per_seed':['score2_direction','full90_direction','rotated_direction','prior90_rank_ridge'],'zero_spread_label_anchors':tie_anchors,'seconds':time.monotonic()-begun,'peak_rss_gib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,'python':sys.executable,'numpy':np.__version__,'outputs':{p.name:sha(p) for p in root.glob('*.npz')},'limits':C['limits']}
 (root/'RESULT.json').write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print('TAIL COMPLETE',rec['status'],flush=True)

if __name__=='__main__':
 try:main(*sys.argv[1:])
 except BaseException as e:
  p=Path(sys.argv[1]);p.mkdir(exist_ok=True);(p/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2)+'\n');raise

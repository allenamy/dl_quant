"""Prediction diagnostics only; never changes the preregistered book decision."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,calendar,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.stats import rankdata


def corr(x,y):
 x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float);x=x-x.mean();y=y-y.mean()
 d=np.sqrt(np.dot(x,x)*np.dot(y,y))
 return float(np.dot(x,y)/d) if d>0 else None

def avg(v):return float(np.mean(v)) if len(v) else None

def metrics(p,y,mask):
 p,y,mask=np.asarray(p),np.asarray(y),np.asarray(mask,bool)
 if p.ndim!=2 or p.shape!=y.shape or p.shape!=mask.shape:raise ValueError('shape')
 ok=mask&np.isfinite(p)&np.isfinite(y);pcs=[];scs=[];pa=[];sa=[];bias=[]
 for i in range(len(p)):
  v=ok[i]
  if v.sum()<5:continue
  x,z=p[i,v].astype(float),y[i,v].astype(float)
  a=corr(x,z);b=corr(rankdata(x),rankdata(z))
  if a is not None:pcs.append(a)
  if b is not None:scs.append(b)
  bias.append(abs(float((x-x.mean()).mean())))
 for j in range(p.shape[1]):
  v=ok[:,j]
  if v.sum()<50:continue
  x,z=p[v,j],y[v,j];a=corr(x,z);b=corr(rankdata(x),rankdata(z))
  if a is not None:pa.append(a)
  if b is not None:sa.append(b)
 x,z=p[ok].astype(float),y[ok].astype(float)
 sx=float(x.std()) if len(x) else 0;sy=float(z.std()) if len(z) else 0
 return dict(intended_pairs=int(mask.sum()),measured_pairs=int(ok.sum()),
  missing_prediction_members=int((mask&~np.isfinite(p)).sum()),missing_label_members=int((mask&~np.isfinite(y)).sum()),
  avg_per_asset_pearson=avg(pa),avg_per_asset_spearman=avg(sa),per_asset_measurable=len(pa),
  cs_pearson=avg(pcs),cs_rank_ic=avg(scs),cs_rank_ic_anchors=len(scs),
  cs_rank_ir=float(np.mean(scs)/np.std(scs,ddof=1)) if len(scs)>1 and np.std(scs,ddof=1)>1e-12 else None,
  beta_y_on_prediction=float(np.mean((x-x.mean())*(z-z.mean()))/sx**2) if sx>0 else None,
  sigma_prediction_over_y=sx/sy if sy>0 else None,
  max_cross_sectional_demeaned_bias=max(bias) if bias else None)

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def run(root,out):
 if not (root/'MODEL_DONE.json').exists():raise ValueError('models not complete')
 sys.path.insert(0,str(root)+'_sources')
 from residual_model import aligned_labels,verify_training
 W=Path('/dev/shm/news2_2026-09-23');fp=W/'work/NEWS_FEATURES.npz';lp=Path('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz')
 pins={str(fp):'3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',str(lp):'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'}
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input drift '+p)
 with np.load(fp) as F,np.load(lp,allow_pickle=True) as T:
  a=F['anchors'];syms=F['symbols'];y=aligned_labels(a,syms,T['E_ts'],T['symbols'],T['y4s'])
  member=np.zeros(y.shape,bool);member[np.repeat(np.arange(len(a)),np.diff(F['off'])),F['m']]=True
 pred={};meta={}
 for label,p in [('fast',root/'models/fast/F10_OOF.npz'),('slow',root/'models/slow/F10_OOF.npz'),('NC42',W/'work/f10_s42/F10_OOF.npz'),('NC2027',W/'work/f10_s2027/F10_OOF.npz')]:
  tr=json.loads((p.parent/'TRAIN_RECEIPT.json').read_text())
  if sha(p)!=tr['pred_sha256']:raise ValueError('score drift '+label)
  if label in ('fast','slow'):verify_training(p.parent,tr,42)
  else:
   parent=Path(json.loads((Path(str(root)+'_sources')/'CONTRACT.json').read_text())['parent_root'])
   seed=label[2:]
   chain=json.loads((parent/f'receipts/ALLOC_CHAIN_inservice_shared_s{seed}.json').read_text())
   old=Path(chain['root'])/f'work/combo_s{seed}/TARGET_RECEIPT.json'
   if sha(old)!=chain['steps']['combo']['outputs']['TARGET_RECEIPT.json']:raise ValueError('reference combo receipt')
   oldpins=json.loads(old.read_text())['inputs']
   expected=[v for k,v in oldpins.items() if k.endswith('/F10_OOF.npz')]
   if expected!=[sha(p)]:raise ValueError('prediction differs from successful NC control')
  with np.load(p) as z:
   if not np.array_equal(z['E_ts'],a) or not np.array_equal(z['symbols'],syms):raise ValueError('score axes '+label)
   pred[label]=z['P'].astype(float)
  meta[label]={'path':str(p),'sha256':sha(p),'receipt_sha256':sha(p.parent/'TRAIN_RECEIPT.json')}
 common=member&np.isfinite(y)
 for p in pred.values():common&=np.isfinite(p)
 windows={'2023H2':('2023-07-01','2024-01-01'),'2024':('2024-01-01','2025-01-01'),'2025':('2025-01-01','2026-01-01'),'2026JanAug':('2026-01-01','2026-09-01'),'September_descriptive':('2026-09-01','2026-09-19')}
 result={}
 from horizon import targets
 yslow=targets(y)
 for label,(lo,hi) in windows.items():
  rows=(a>=calendar.timegm(time.strptime(lo,'%Y-%m-%d')))&(a<calendar.timegm(time.strptime(hi,'%Y-%m-%d')))
  result[label]={'population':'same intended members and same finite raw label / all four predictions','intended_members':int(member[rows].sum()),'common_measured_pairs':int(common[rows].sum()),'models':{}}
  for name,p in pred.items():
   r=metrics(p[rows],y[rows],common[rows]);r['own_member_finite_prediction_pairs']=int((member[rows]&np.isfinite(p[rows])).sum());r['holding_target_dense']=metrics(p[rows],yslow[rows],common[rows]);cleanrows=rows&(np.arange(len(a))%12==0);r['holding_target_clean_stride48h']=metrics(p[cleanrows],yslow[cleanrows],common[cleanrows]);result[label]['models'][name]=r
 print('diagnostics complete',flush=True)
 rec=dict(status='PREDICTION_DIAGNOSTICS_NOT_BOOK_DECISION',utc=time.strftime('%FT%TZ',time.gmtime()),source_sha256=sha(__file__),input_pins=pins,models=meta,results=result,
  caliber='raw uncut 4h return; stride=14400 equals horizon, clean=dense; holding-target supplementary has dense vs clean48h; member scoring not inventory attribution',python=sys.executable,numpy=np.__version__)
 with open(out,'x') as f:json.dump(rec,f,indent=2,allow_nan=False)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);v=ap.parse_args();run(v.root,v.out)

"""Diagnostic dual metrics only. Outcomes cannot choose model or affect book gates."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
import json,pathlib,hashlib,sys
from datetime import datetime,timezone
import numpy as np
from scipy.stats import rankdata
H=pathlib.Path(__file__).resolve().parent;C=json.loads((H/'CONTRACT.json').read_text());R=pathlib.Path(C['root']);NS=pathlib.Path('/dev/shm/news2_2026-09-23')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def corr(x,y):
 x=x-x.mean();y=y-y.mean();d=np.sqrt((x*x).sum()*(y*y).sum())
 return float((x*y).sum()/d) if d>0 else None
T=np.load('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz',allow_pickle=True)
F=np.load(NS/'work/NEWS_FEATURES.npz');a=F['anchors'];sy=F['symbols'];ix=np.searchsorted(T['E_ts'],a);assert np.array_equal(a,T['E_ts'][ix]);y=T['y4s'][ix]
stamp=lambda s:int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
periods={'pre2026':(stamp('2023-07-01'),stamp('2026-01-01')),'2026_H1':(stamp('2026-01-01'),stamp('2026-07-01')),'recent_primary':(stamp('2026-07-01'),stamp('2026-09-19'))}
out={'schema':'diagnostic_not_gate','source_sha256':sha(__file__),'python':sys.executable,'units':'raw score not calibrated as return; beta/sigma descriptive only','results':{}}
for seed in (42,2027):
 streams={'NC':NS/f'work/f10_s{seed}/F10_OOF.npz',**{k:R/f'models/{k}_s{seed}/F10_OOF.npz' for k in ('U','R180')}}
 loaded={k:np.load(p)['P'] for k,p in streams.items()};population=np.logical_and.reduce([np.isfinite(v) for v in loaded.values()])&np.isfinite(y)
 for kind,p in streams.items():
  P=loaded[kind];res={'score_sha256':sha(p),'periods':{}}
  for name,(lo,hi) in periods.items():
   rows=np.flatnonzero((a>=lo)&(a<hi));cs_p=[];cs_s=[];aps=[];ass=[];betas=[];sigmas=[]
   for i in rows:
    m=population[i]
    if m.sum()<50:continue
    xx=P[i,m].astype(float);yy=y[i,m].astype(float);v=corr(xx,yy);q=corr(rankdata(xx),rankdata(yy))
    if v is not None:cs_p.append(v)
    if q is not None:cs_s.append(q)
   for j in range(len(sy)):
    m=population[rows,j]
    if m.sum()<30:continue
    xx=P[rows[m],j].astype(float);yy=y[rows[m],j].astype(float);v=corr(xx,yy);q=corr(rankdata(xx),rankdata(yy))
    if v is not None:aps.append(v)
    if q is not None:ass.append(q)
    if np.std(xx)>0 and np.std(yy)>0:betas.append(float(np.cov(xx,yy,ddof=1)[0,1]/np.var(xx,ddof=1)));sigmas.append(float(np.std(xx)/np.std(yy)))
   mean=lambda z:float(np.mean(z)) if z else None
   res['periods'][name]={'anchors':len(cs_s),'pair_count':int(population[rows].sum()),'mean_xsec_pearson':mean(cs_p),'mean_xsec_spearman':mean(cs_s),'avg_per_asset_pearson':mean(aps),'avg_per_asset_spearman':mean(ass),'mean_beta':mean(betas),'mean_sigma_ratio':mean(sigmas),'nonoverlap':'4h target,4h anchors'}
  out['results'][f'{kind}_s{seed}']=res
with open(R/'receipts/SCORE_DIAGNOSTICS.json','x') as f:json.dump(out,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())

"""Descriptive comparison to old reconstructed log-price source, never silently splices."""
from pathlib import Path
import datetime as dt,hashlib,json,sys,time
import numpy as np

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def paired_returns(price,logp,observed):
 if price.shape!=logp.shape or price.shape!=observed.shape or price.ndim!=2 or observed.dtype!=bool:raise ValueError('paired shapes')
 valid=observed[:-1]&observed[1:]&np.isfinite(price[:-1])&np.isfinite(price[1:])&(price[:-1]>0)&(price[1:]>0)&np.isfinite(logp[:-1])&np.isfinite(logp[1:])
 a=np.full(valid.shape,np.nan);b=np.full(valid.shape,np.nan)
 a[valid]=price[1:][valid]/price[:-1][valid]-1;b[valid]=np.expm1(logp[1:][valid]-logp[:-1][valid])
 if not np.isfinite(a[valid]).all() or not np.isfinite(b[valid]).all():raise ValueError('nonfinite return')
 return a,b,valid
def stats(a):
 if not a.size:return {'n':0,'max':None,'p99':None,'median':None}
 return {'n':a.size,'max':float(a.max()),'p99':float(np.quantile(a,.99)),'median':float(np.median(a))}
def run(root):
 root=Path(root);cp=root/'PRICE_OVERLAP_CONTRACT.json';c=json.loads(cp.read_text());start=time.monotonic();pins={}
 if c['source_sha256']!=sha(__file__):raise ValueError('source identity')
 for k,v in c['inputs'].items():
  p=Path(v['path']);h=sha(p)
  if h!=v['sha256']:raise ValueError('input drift '+k)
  pins[k]={'path':str(p),'sha256':h}
 n=np.load(c['inputs']['recent_panel']['path'],allow_pickle=False);m=np.load(c['inputs']['old_meta']['path'],allow_pickle=False);old=np.load(c['inputs']['old_logprice']['path'],mmap_mode='r')
 sy=m['symbols'].astype(str).tolist();ns=n['symbols'].astype(str).tolist();t=n['ts'];g=m['grid']
 if len(set(sy))!=len(sy) or ns[:len(sy)]!=sy or old.shape!=(len(g),len(sy)) or np.any(np.diff(t)!=300) or np.any(np.diff(g)!=300):raise ValueError('axis/grid')
 mask=(t>=g[0])&(t<=g[-1]);tt=t[mask];oi=np.searchsorted(g,tt)
 if len(tt)<2 or not np.array_equal(g[oi],tt):raise ValueError('overlap axis')
 raw=n['close'][mask,:len(sy)];observed=n['observed'][mask,:len(sy)];logp=np.asarray(old[oi]);a,b,v=paired_returns(raw,logp,observed);delta=np.abs(a-b)
 unknown=(~observed)&np.isfinite(logp);raw_known_old_unknown=observed&~np.isfinite(logp)
 by_symbol=[]
 for j,s in enumerate(sy):by_symbol.append({'symbol':s,**stats(delta[:,j][v[:,j]]),'new_missing_old_finite':int(unknown[:,j].sum()),'new_observed_old_missing':int(raw_known_old_unknown[:,j].sum())})
 pairs=np.argwhere(v&(delta>1e-6));examples=[]
 for i,j in pairs[:20]:examples.append({'symbol':sy[j],'end_ts':int(tt[i+1]),'official_return':float(a[i,j]),'old_reconstructed_return':float(b[i,j])})
 result={'status':'DESCRIPTIVE_OVERLAP_NOT_EXACT_PRICE_CERTIFICATION','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-start,'source_sha256':sha(__file__),'contract_sha256':sha(cp),'inputs':pins,'python':sys.executable,'numpy':np.__version__,'first_close':int(tt[0]),'last_close':int(tt[-1]),'n_closes':len(tt),'n_symbols':len(sy),'absolute_return_difference':stats(delta[v]),'greater_1e_6':int((v&(delta>1e-6)).sum()),'greater_1e_5':int((v&(delta>1e-5)).sum()),'new_missing_old_finite':int(unknown.sum()),'new_observed_old_missing':int(raw_known_old_unknown.sum()),'by_symbol':by_symbol,'examples_above_1e_6':examples,'limits':['Old source is accumulated log prices from raw-return table, not exact venue close level','Every name/time retained; missing endpoints are not zero returns','No stitching, model input modification or PnL produced','Absence/frozen bars and historical eligibility are separate evidence obligations']}
 (root/'PRICE_OVERLAP.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print({k:v for k,v in result.items() if k not in ('by_symbol','inputs','examples_above_1e_6')})
if __name__=='__main__':run(sys.argv[1])

"""Read-only raw-price adapter for the four price-peer columns; no signal scores.

Missing source observations are never replaced by the cash engine's held marks.
All timestamps here denote bar closes.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import hashlib,json,sys,time,traceback,resource
import numpy as np
from peer_features import fit_graph,transform,NAMES

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def closed_returns(grid,logprice,first,last,badrow,badcol,*,extension_start_row=None):
 g=np.asarray(grid);p=np.asarray(logprice);fi=np.asarray(first);la=np.asarray(last);br=np.asarray(badrow);bc=np.asarray(badcol)
 if g.ndim!=1 or g.dtype.kind not in 'iu' or len(g)<49 or np.any(g%300) or np.any(np.diff(g)!=300):raise ValueError('5m grid')
 if p.ndim!=2 or len(p)!=len(g) or fi.shape!=(p.shape[1],) or la.shape!=fi.shape:raise ValueError('price axes')
 if any(x.dtype.kind not in 'iu' for x in (fi,la,br,bc)) or br.shape!=bc.shape or br.ndim!=1:raise ValueError('observation indices')
 if np.any(br<0) or np.any(br>=len(g)) or np.any(bc<0) or np.any(bc>=p.shape[1]):raise ValueError('bad index range')
 end=len(g) if extension_start_row is None else extension_start_row
 if type(end)is not int or not 49<=end<=len(g):raise ValueError('extension start')
 rows=np.flatnonzero((g%14400==0)&(np.arange(len(g))>=48));A=g[rows];out=np.full((len(A),p.shape[1]),np.nan)
 bad=np.zeros(out.shape,bool)
 # Closed 49-point windows: a missing exact 4h boundary poisons both adjacent intervals.
 for shift in (0,14400):
  t=((g[br]+14399)//14400)*14400
  if shift:t=np.where(g[br]%14400==0,t+shift,-1)
  ix=np.searchsorted(A,t);ok=(ix<len(A))&(ix>=0)
  ok &= A[np.minimum(ix,len(A)-1)]==t
  bad[ix[ok],bc[ok]]=True
 for k,j in enumerate(rows):
  block=p[j-48:j+1]
  old_observed=(fi<=j-48)&(la>=min(j,end-1))&(fi>=0)
  ok=(old_observed|(j-48>=end))&np.isfinite(block).all(0)&~bad[k]
  out[k,ok]=block[-1,ok]-block[0,ok]
 return A,out

def trailing_sum(x,n):
 x=np.asarray(x,float)
 if x.ndim!=2 or type(n)is not int or n<1:raise ValueError('rolling input')
 ok=np.isfinite(x);z=np.vstack([np.zeros(x.shape[1]),np.cumsum(np.where(ok,x,0),axis=0)])
 c=np.vstack([np.zeros(x.shape[1],int),np.cumsum(ok,axis=0)])
 y=np.full_like(x,np.nan);s=z[n:]-z[:-n];valid=c[n:]-c[:-n]==n;y[n-1:]=np.where(valid,s,np.nan);return y

def main(root,contract_path):
 started=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);C=json.loads(Path(contract_path).read_text());pins=C['inputs']
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input sha '+p)
 if sha(Path(__file__).with_name('peer_features.py'))!=C['peer_source_sha256']:raise ValueError('peer source')
 free=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))/2**20
 if free<8:raise MemoryError('less than 8GiB available')
 paths=C['paths'];meta=np.load(paths['meta']);sy=meta['symbols'];grid=meta['grid'];n=len(sy)
 price=np.load(paths['price'],mmap_mode='r');br=np.r_[meta['unavail_grid_row'],meta['gapfilled_grid_row'],meta['inlife_nan_grid_row']];bc=np.r_[meta['unavail_col'],meta['gapfilled_col'],meta['inlife_nan_col']]
 # These legacy metadata fields contain seconds, not row numbers, and stop at the
 # old boundary. Appended observations are governed by the bound extension receipt.
 receipt=json.loads(Path(paths['price_receipt']).read_text());old_rows=int(receipt['old_rows'])
 assert receipt['VERDICT']=='PASS' and old_rows+int(receipt['new_rows'])==len(grid)
 assert receipt['outputs']['raw']['sha256']==pins[paths['price']] and receipt['outputs']['meta']['sha256']==pins[paths['meta']]
 first=np.where(meta['first_fin']>=0,np.searchsorted(grid,meta['first_fin']),-1)
 last=np.where(meta['last_fin']>=0,np.searchsorted(grid,meta['last_fin'],side='right')-1,-1)
 A,r4=closed_returns(grid,price,first,last,br,bc,extension_start_row=old_rows);r24=trailing_sum(r4,6)
 tr=np.load(paths['trad']);assert np.array_equal(sy,tr['symbols']);ti=np.searchsorted(tr['anchor_ts'],A)
 assert np.all(ti<len(tr['anchor_ts'])) and np.array_equal(tr['anchor_ts'][ti],A)
 ax=np.load(paths['axes']);assert np.array_equal(sy,ax['symbols']);crypto=np.zeros(n,bool);crypto[ax['crypto_cols']]=True
 legal=(tr['state_W24H'][ti]==2)&crypto[None,:]&np.isfinite(r4)
 features=np.full((len(A),n,4),np.nan,np.float32);scale=np.full(r4.shape,np.nan,np.float32);beta=np.full_like(scale,np.nan);peers_count=np.zeros(r4.shape,np.int16)
 daily=[];last=None;nan=np.full(n,np.nan);begin=int(C['feature_start']);eligible_days=0
 for i,a in enumerate(A):
  if a<begin:continue
  if time.monotonic()-started>C['budget_seconds']:raise TimeoutError('panel budget')
  day=int(a//86400*86400)
  if day!=last:
   G=fit_graph(A,r4,legal,sy,day,**C['graph']);last=day;eligible_days+=1
   daily.append({'day':day,'eligible_names':int(G['eligible'].sum()),'names_with_peers':int((G['peers'][:,0]>=0).sum()),'last_history_ts':G['last_history_ts']})
   if eligible_days%60==0:print('graph_days',eligible_days,'elapsed',round(time.monotonic()-started,2),flush=True)
  v=transform(G,int(a),r4=r4[i],r24=r24[i],flow_delta=nan,qv_anomaly=nan,fund8=nan,ema8=nan,active=legal[i])
  features[i]=v['X'][:,:4];scale[i]=G['scale'];beta[i]=G['beta'];peers_count[i]=v['peer_count']
 # Frozen graph and transforms at two dates ignore all later raw returns/legality.
 future_controls=[]
 for d in (int(C['control_dates'][0]),int(C['control_dates'][1])):
  g0=fit_graph(A,r4,legal,sy,d,**C['graph']);mut=r4.copy();lm=legal.copy();mut[A>=d]=999.;lm[A>=d]=False;g1=fit_graph(A,mut,lm,sy,d,**C['graph'])
  assert all(np.array_equal(g0[k],g1[k],equal_nan=True) for k in ('beta','scale','peers','counts'));future_controls.append({'day':d,'future_poison_graph_equal':True})
 y=np.vstack([np.expm1(r4[1:]),np.full((1,n),np.nan)])
 output=root/'PRICE_PEERS.npz';np.savez_compressed(output,anchors=A,symbols=sy,X=features,r4=r4,r24=r24,scale=scale,beta=beta,legal=legal,peer_count=peers_count,y4_raw=y)
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input drift '+p)
 res={'status':'PRICE_PEER_PANEL_COMPLETE_NOT_SIGNAL_EVIDENCE','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'contract_sha256':sha(contract_path),'inputs':pins,'outputs':{output.name:sha(output)},'shape':list(features.shape),'columns':list(NAMES[:4]),'daily_coverage':daily,'controls':future_controls,'seconds':time.monotonic()-started,'peak_rss_gib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,'python':sys.executable,'numpy':np.__version__,'limitations':['Four price-peer columns only; flow/funding not silently imputed into this panel','Training/scoring members still to join by exact named axis','Label future returns are output targets only and never fed into graph','Price levels retain frozen NC scale; missing/held bars excluded']}
 (root/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print('PANEL COMPLETE',res['seconds'],flush=True)

if __name__=='__main__':
 try:main(*sys.argv[1:])
 except BaseException as e:
  r=Path(sys.argv[1]);r.mkdir(exist_ok=True);(r/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2)+'\n');raise

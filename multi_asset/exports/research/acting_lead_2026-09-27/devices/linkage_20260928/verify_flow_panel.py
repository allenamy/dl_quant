"""Independent direct-window check of stored flow and D10 units, no signal metric."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
import json,hashlib,sys,time
import numpy as np

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def main(root,cp):
 root=Path(root);C=json.loads(Path(cp).read_text());rr=json.loads((root/'RESULT.json').read_text());tt=json.loads((root/'TERMINAL.json').read_text());assert tt['rc']==0 and tt['result_sha256']==sha(root/'RESULT.json')
 assert rr['contract_sha256']==sha(cp)
 for n,h in rr['outputs'].items():assert sha(root/n)==h
 z=np.load(root/'FLOW_FUND_PEERS.npz');A=z['anchors'];own=z['own'];X=z['X'];PX=z['price'];legal=z['legal'];days=z['graph_days'];peers=z['peers'];sy=z['symbols']
 ax=np.load(C['paths']['old_axes']);ts=ax['ts'];cols=ax['crypto_cols'];nt=np.load(C['paths']['new_axes'])['ts'];old=np.load(C['paths']['old_cache'],mmap_mode='r');new=np.load(C['paths']['new_cache'],mmap_mode='r');colmap={int(j):i for i,j in enumerate(cols)}
 fz=np.load(C['paths']['fund_state']);F={k:fz[k] for k in ('ev_off','ft','rate','iv','ema')};checks=0;largest=0.;samples=[];cache={}
 def eq(a,b,tol=3e-6):
  nonlocal checks,largest
  a,b=np.asarray(a),np.asarray(b);assert np.array_equal(np.isnan(a),np.isnan(b))
  q=np.isfinite(a)&np.isfinite(b);err=float(np.max(np.abs(a[q]-b[q])/np.maximum(1,np.abs(b[q])))) if np.any(q) else 0
  assert err<=tol,(a,b,err);largest=max(largest,err);checks+=1
 def raw_pair(aa,j):
  dat,clock=(old,ts) if aa<=ts[-1] else (new,nt);e=int(np.searchsorted(clock,aa));assert clock[e]==aa;ci=colmap[int(j)]
  def avg(n,lag,ch):
   hi=e+1-lag;lo=hi-n
   if lo<0:return np.nan
   v=np.asarray(dat[lo:hi,ci,ch],float)
   if not np.isfinite(v).all() or (ch==6 and ((v<0)|(v>1)).any()) or (ch==3 and (v<0).any()):return np.nan
   return float(np.mean(v))
  return np.array([avg(48,0,6)-avg(288,48,6),avg(48,0,3)-avg(2016,48,3)])
 def normalized(aa,j):
  key=(int(aa),int(j))
  if key in cache:return cache[key]
  day=aa//86400*86400;use=np.flatnonzero((A>=day-360*14400)&(A<day)&legal[:,j]);hist=np.array([raw_pair(A[i],j) for i in use]);raw=raw_pair(aa,j);res=[]
  for k in range(2):
   q=hist[:,k];q=q[np.isfinite(q)]
   if len(q)<240:res.append(np.nan);continue
   mu=np.median(q);s=1.4826*np.median(np.abs(q-mu));res.append((raw[k]-mu)/s if s>1e-12 else np.nan)
  cache[key]=np.array(res);return cache[key]
 for date in ('2023-07-01T00:00','2026-01-01T00:00','2026-09-26T20:00'):
  aa=int(np.datetime64(date,'s').astype('int64'));i=np.searchsorted(A,aa);di=np.searchsorted(days,aa//86400*86400);assert A[i]==aa
  names=np.flatnonzero(np.isfinite(X[i]).all(1)&np.isfinite(own[i]).all(1))
  assert len(names)>=8;sel=names[np.linspace(0,len(names)-1,8,dtype=int)]
  for j in sel:
   o=normalized(aa,j);eq(own[i,j,6:],o)
   pp=peers[di,j];pp=pp[pp>=0];assert j not in pp and len(set(map(int,pp)))==len(pp);pp=pp[legal[i,pp]]
   pv=np.array([normalized(aa,k) for k in pp]);v=[]
   for k in range(2):
    w=pv[:,k];w=w[np.isfinite(w)];v.append(w.mean()-o[k] if len(w)>=8 else np.nan)
   eq(X[i,j,:2],v)
   ci=colmap[int(j)];b,e=F['ev_off'][ci:ci+2];ft=F['ft'][b:e];ix=b+np.searchsorted(ft,aa,side='right')-1
   assert ix>=b and 0<=aa-F['ft'][ix]<=43200
   rn=F['rate'][ix]*8/F['iv'][ix];eq(own[i,j,:4],[F['rate'][ix],F['ema'][ix],rn,max(-rn,0)])
   eq(X[i,j,2],max(-rn,0)*PX[i,j,0]);samples.append([int(aa),str(sy[j])])
 r={'status':'DIRECT_WINDOW_D10_UNIT_CHECK_PASS','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'result_sha256':sha(root/'RESULT.json'),'checks':checks,'max_scaled_difference':largest,'samples':samples,'tolerance':3e-6,'limits':['Direct means/medians vs cumulative float64, stored float32; not bitwise equality','Sampled 24 names/anchors and their peers, not every observation','Does not prove new alpha or cash benefit']}
 (root/'DIRECT_INPUT_CHECK.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

if __name__=='__main__':main(*sys.argv[1:])

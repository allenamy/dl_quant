"""No training, no portfolio change; join frozen OOF risk to frozen NC held cash."""
import hashlib,json,time,os,sys
from pathlib import Path
import numpy as np
from tail_held_cash import bins,align,group_cash

ROOT=Path('/dev/shm/tail_held_cash_20260929')
FILES={
 '/dev/shm/held_strength_cash_repair_20260928/ALIGNED.npz':'b47360d630f16f6351d048427a89e781372b7ce13dc17948a51f63c6d706a5da',
 '/dev/shm/held_strength_cash_repair_20260928/RESULT.json':'f1412bda64b2801acba56c41083f9330aba83cff265cd06b0e7e0445a2075c6d',
 '/dev/shm/tail_risk_20260928/PREDICTIONS.npz':'6227aaa2af203b110f227a47bc0139779d52cb7fec60da2a01a96bd241bc8a3f',
 '/dev/shm/tail_risk_20260928/RESULT.json':'ab1b7fe3a85901f60802361d731050e1fdb1631c9769b36db5abb35b4eef37c0'}
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def main():
 start=time.time();ROOT.mkdir(exist_ok=False)
 pins={p:sha(p) for p in FILES};assert pins==FILES,'input identity'
 sources={str(p):sha(p) for p in Path(__file__).parent.glob('*.py')}
 write(ROOT/'INPUTS.json',dict(inputs=pins,sources=sources,python=sys.executable,numpy=np.__version__,pid=os.getpid(),started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
 h=np.load(list(FILES)[0],allow_pickle=False);p=np.load(list(FILES)[2],allow_pickle=False)
 A=h['A'];S=h['symbols'];assert np.array_equal(S,p['symbols']) and len(set(S))==len(S)
 assert np.array_equal(A,np.arange(1789776000,1790467200,14400)), 'frozen 48 anchors'
 ii=align(p['anchors'],A);offs=p['off'];counts=p['count'];members=p['m'];P=p['pred'];Y=p['labels'];elig=p['eligible']
 assert len(offs)==len(counts)+1 and offs[0]==0 and offs[-1]==len(members) and np.array_equal(np.diff(offs),counts)
 assert P.shape==(len(members),6,2) and Y.shape==elig.shape==(len(members),2)
 rows=np.concatenate([np.arange(offs[i],offs[i+1]) for i in ii])
 assert np.isfinite(P[rows]).all() and ((P[rows]>=0)&(P[rows]<=1)).all()
 assert ((P[rows].sum(2))<=1.000001).all()
 data={'A':A,'symbols':S};results={}
 for seed,base in ((42,0),(2027,3)):
  prefix=f'{seed}_'; mv=h[prefix+'mv0'];q=h[prefix+'q0'];nav=h[prefix+'nav0']
  price=h[prefix+'price'];fund=h[prefix+'funding'];fee=h[prefix+'fee'];net=h[prefix+'net'];unknown=h[prefix+'unknown']
  assert np.max(np.abs(net-price-fund+fee))<1e-7 and ((q>0)==(mv>0)).all() and ((q<0)==(mv<0)).all()
  active=(q!=0)|(h[prefix+'q1']!=0)|(mv!=0)|(h[prefix+'mv1']!=0)|(price!=0)|(fund!=0)|(fee!=0)
  assert not (unknown&active).any(),'unknown active cash'
  direction=np.where(q>0,0,np.where(q<0,1,2))
  for k,x in dict(q=q,mv=mv,nav=nav,price=price,fund=fund,fee=fee,net=net).items():data[prefix+k]=x
  sd={}
  for mode,col in [('score2',base),('full90',base+1),('symmetric',base+1),('rotated',base+2)]:
   groups=np.full(mv.shape,-1,dtype=np.int8);pr=np.full(mv.shape,np.nan);yy=np.full(mv.shape,np.nan)
   up=np.full(mv.shape,np.nan);down=up.copy();yu=up.copy();yd=up.copy()
   for t,i in enumerate(ii):
    sl=slice(offs[i],offs[i+1]);m=members[sl]
    assert len(m)==len(set(m)) and np.issubdtype(m.dtype,np.integer) and ((m>=0)&(m<len(S))).all()
    up[t,m]=P[sl,col,0];down[t,m]=P[sl,col,1]
    yu[t,m]=np.where(elig[sl,0],Y[sl,0],np.nan);yd[t,m]=np.where(elig[sl,1],Y[sl,1],np.nan)
    if mode=='symmetric':
     v=np.minimum(up[t]+down[t],1);pr[t]=v;yy[t]=np.maximum(yu[t],yd[t]);b=bins(v)
    else:
     pr[t]=np.where(q[t]<0,up[t],down[t]);yy[t]=np.where(q[t]<0,yu[t],yd[t])
     # Quantiles are on the full scored population for each directional tail.
     b=np.where(q[t]<0,bins(up[t]),bins(down[t]))
    groups[t]=direction[t]*6+b
   rr=group_cash(groups,mv,price,fund,fee,nav)
   for r in rr:
    mask=groups==r['group'];valid=mask&np.isfinite(pr)&np.isfinite(yy);wg=np.abs(mv)
    den=float(wg[valid].sum());r['label_covered_initial_gross']=den
    r['missing_label_initial_gross']=float(wg[mask&~np.isfinite(yy)].sum())
    r['predicted_adverse_probability']=float(np.sum(wg[valid]*pr[valid])/den) if den else None
    r['realized_adverse_event_frequency']=float(np.sum(wg[valid]*yy[valid])/den) if den else None
   for key,x in [('price_usd',price),('fund_usd',fund),('fee_usd',fee),('net_usd',net)]:
    assert abs(sum(r[key] for r in rr)-float(x.sum()))<1e-7,(mode,key)
   sd[mode]=rr
   for k,x in dict(groups=groups,prob=pr,label=yy,up=up,down=down,up_label=yu,down_label=yd).items():data[f'{seed}_{mode}_{k}']=x
  results[str(seed)]=sd
 np.savez_compressed(ROOT/'ALIGNED.npz',**data)
 assert {p:sha(p) for p in FILES}==pins and {p:sha(p) for p in sources}==sources
 result=dict(status='DESCRIPTIVE_ONLY_NO_PROMOTION',scope='8 already observed days; NC simulated inventory, D10 risk features; execution seed 0; no policy counterfactual',inputs=pins,sources=sources,anchors=A.tolist(),group_order='direction(long,short,start_flat) x (q0,q1,q2,q3,q4,missing)',tables=results,elapsed_seconds=time.time()-start)
 write(ROOT/'RESULT.json',result)
 write(ROOT/'TERMINAL.json',dict(status='DONE',rc=0,outputs={p.name:sha(p) for p in ROOT.iterdir() if p.is_file()},inputs_rechecked=True))
 print(json.dumps({'status':result['status'],'elapsed_seconds':result['elapsed_seconds'],'result_sha256':sha(ROOT/'RESULT.json')}))
if __name__=='__main__':main()

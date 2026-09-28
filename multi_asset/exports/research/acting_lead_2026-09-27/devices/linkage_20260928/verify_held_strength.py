"""Independent raw-input read and scalar cash regroup; does not import main device."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
import json,hashlib,sys,time
import numpy as np
from scipy.stats import rankdata
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main(root,contract):
 root=Path(root);C=json.loads(Path(contract).read_text());r=json.loads((root/'RESULT.json').read_text());t=json.loads((root/'TERMINAL.json').read_text())
 assert t['rc']==0 and t['result_sha256']==sha(root/'RESULT.json') and r['contract_sha256']==sha(contract)
 for p,h in C['inputs'].items():assert sha(p)==h
 assert sha(root/'ALIGNED.npz')==r['outputs']['ALIGNED.npz']
 z=np.load(root/'ALIGNED.npz');A=z['A'];symbols=z['symbols'];assert np.array_equal(A,np.arange(1789776000,1790467200,14400));checks=0;worst=0.
 def eq(a,b,tol=1e-7):
  nonlocal checks,worst
  a,b=np.asarray(a),np.asarray(b);assert a.shape==b.shape and np.array_equal(np.isnan(a),np.isnan(b))
  u=np.isfinite(a);assert np.array_equal(u,np.isfinite(b))
  if a.dtype.kind=='b' or b.dtype.kind=='b':
   assert a.dtype.kind==b.dtype.kind and np.array_equal(a,b);d=0.
  else:d=float(np.max(np.abs(a[u]-b[u]))) if u.any() else 0.
  assert d<=tol,(d,tol);checks+=1;worst=max(worst,d)
 F=np.load(C['panel']);fi=[list(F['anchors']).index(a) for a in A];eq(z['own4'],F['own'][fi,:,4],0);eq(z['own24'],F['own'][fi,:,5],0)
 L=np.load(C['legs']);li=[list(L['E_ts']).index(a) for a in A];eq(z['NC_ZFD'],L['ZFD'][li],0);eq(z['NC_RN8'],L['RN8'][li],0)
 P=np.load(C['predictions']);pi=[list(P['anchors']).index(a) for a in A]
 for si,seed in enumerate(('42','2027')):
  cash=np.load(C['cash'][seed]);ci=[list(cash['A']).index(a) for a in A];cb=np.load(C['combo'][seed]);bi=[list(cb['E_ts']).index(a) for a in A]
  assert np.array_equal(cash['symbols'],symbols) and np.array_equal(cb['symbols'],symbols)
  for key in ['q0','q1','mv0','mv1','cash','price','funding','fee','net','nav0','unknown']:eq(z[seed+'_'+key],cash[key][ci],0)
  eq(z[seed+'_target'],cb['weights'][bi],0)
  for row,j in enumerate(pi):
   sl=slice(P['off'][j],P['off'][j+1]);names=P['m'][sl];b=P['pred'][sl,si*3];c=P['pred'][sl,si*3+1];ok=np.isfinite(b)&np.isfinite(c);dd=np.full(len(symbols),np.nan);dd[names[ok]]=(rankdata(c[ok])-rankdata(b[ok]))/(ok.sum()-1);eq(z[seed+'_rank_delta'][row],dd,0)
  q=z[seed+'_q0'];mv=z[seed+'_mv0'];nav=z[seed+'_nav0'];target=z[seed+'_target'];p=z[seed+'_price'];f=z[seed+'_funding'];fee=z[seed+'_fee'];directions={'long':q>0,'short':q<0,'flat':q==0}
  four=z['own4'];day=z['own24'];unknown=~(np.isfinite(four)&np.isfinite(day));valid=~unknown
  strength={'both_negative':valid&(four<0)&(day<0),'4h_negative_24h_nonnegative':valid&(four<0)&(day>=0),'4h_nonnegative_24h_negative':valid&(four>=0)&(day<0),'both_nonnegative':valid&(four>=0)&(day>=0),'unknown':unknown}
  def signs(x):return {'negative':np.isfinite(x)&(x<0),'nonnegative':np.isfinite(x)&(x>=0),'unknown':~np.isfinite(x)}
  d=z[seed+'_rank_delta'];spec={'strength':strength,'fund_rank':signs(z['NC_ZFD']),'fund_rate8':signs(z['NC_RN8']),'conditional_rank_shift':{'positive':np.isfinite(d)&(d>0),'nonpositive':np.isfinite(d)&(d<=0),'unavailable':~np.isfinite(d)},'score_membership':{'inside':z[seed+'_member'],'outside':~z[seed+'_member']}}
  for name,groups in spec.items():
   assert np.all(sum(v.astype(int) for v in groups.values())==1)
   for row in r['results'][seed][name]:
    u=directions[row['direction']]&groups[row['condition']];eq(row['cells'],u.sum(),0);eq(row['initial_gross_usd_sum'],np.abs(mv)[u].sum());eq(row['target_same_direction_gross_usd_sum'],np.abs(mv)[u&(q*target>0)].sum())
    for key,val in [('price',p),('funding',f),('fee',fee),('net',p+f-fee)]:
     total=sum(float(val[i][u[i]].sum()) for i in range(48));bps=sum(float(val[i][u[i]].sum()/nav[i]*1e4) for i in range(48))/8;eq(total,row[key+'_usd']);eq(bps,row[key+'_bps_per_day'])
     if key in ('price','net'):eq([sum(float(val[i][u[i]].sum()/nav[i]*1e4) for i in range(j,j+6)) for j in range(0,48,6)],row['daily_'+key+'_bps'])
 rec={'status':'INDEPENDENT_RAW_CASH_REGROUP_PASS','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'result_sha256':sha(root/'RESULT.json'),'aligned_sha256':sha(root/'ALIGNED.npz'),'checks':checks,'max_abs_difference':worst,'limits':['Does not independently reconstruct simulator fills or source features','No trading counterfactual or production parity']}
 (root/'INDEPENDENT_CHECK.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
if __name__=='__main__':main(*sys.argv[1:])

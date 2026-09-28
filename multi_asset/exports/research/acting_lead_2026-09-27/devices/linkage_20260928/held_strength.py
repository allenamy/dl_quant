"""Fixed ex-ante partitions of archived cash. Descriptive, NOT a counterfactual."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
import hashlib,json,sys,time,signal,resource
import numpy as np
from scipy.stats import rankdata

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def align(axis,wanted):
 a,w=np.asarray(axis),np.asarray(wanted)
 if a.ndim!=1 or w.ndim!=1 or a.dtype.kind not in 'iu' or w.dtype.kind not in 'iu' or not len(a) or np.any(np.diff(a)<=0) or np.any(a%14400) or np.any(w%14400):raise ValueError('integer ordered 4h axis')
 i=np.searchsorted(a,w)
 if np.any(i==len(a)) or not np.array_equal(a[i],w):raise ValueError('missing exact anchors')
 return i

def partition(x4,x24):
 a,b=np.asarray(x4),np.asarray(x24)
 if a.shape!=b.shape or np.isinf(a).any() or np.isinf(b).any():raise ValueError('strength shape/value')
 out=np.full(a.shape,4,int);ok=np.isfinite(a)&np.isfinite(b)
 out[ok]=2*(a[ok]>=0).astype(int)+(b[ok]>=0)
 return out

def rank_delta(base,candidate):
 a,b=np.asarray(base),np.asarray(candidate)
 if a.shape!=b.shape or a.ndim!=1 or len(a)<2 or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('rank population')
 return (rankdata(b)-rankdata(a))/(len(a)-1)

def aggregate(price,fund,fee,mv,nav,q,target,groups,n_groups):
 values=list(map(np.asarray,(price,fund,fee,mv,q,target)));g=np.asarray(groups);v=np.asarray(nav)
 if any(z.shape!=g.shape or not np.isfinite(z).all() for z in values) or g.ndim!=2 or v.shape!=(g.shape[0],) or not np.isfinite(v).all() or np.any(v<=0):raise ValueError('cash shape/nonfinite')
 if g.dtype.kind not in 'iu' or np.any(g<0) or np.any(g>=n_groups):raise ValueError('partition not exhaustive')
 p,f,e,m,q,t=values;result=[];days=len(v)/6
 for k in range(n_groups):
  u=g==k;gross=np.abs(m)*u
  row={'cells':int(u.sum()),'nonzero_initial_positions':int((u&(q!=0)).sum()),'initial_gross_usd_sum':float(gross.sum()),'target_same_direction_gross_usd_sum':float((gross*((q*t)>0)).sum()),'daily_price_bps':[], 'daily_net_bps':[]}
  for name,val in [('price',p),('funding',f),('fee',e),('net',p+f-e)]:
   row[name+'_usd']=float(val[u].sum());row[name+'_bps_per_day']=float(np.sum(val*u/v[:,None])*1e4/days)
  row['price_per_initial_notional_bps']=float(row['price_usd']/gross.sum()*1e4) if gross.sum()>0 else None
  ap=np.sum(p*u/v[:,None],axis=1)*1e4;an=np.sum((p+f-e)*u/v[:,None],axis=1)*1e4
  if len(v)%6==0:row['daily_price_bps']=ap.reshape(-1,6).sum(1).tolist();row['daily_net_bps']=an.reshape(-1,6).sum(1).tolist()
  result.append(row)
 for key,x in [('price',p),('funding',f),('fee',e),('net',p+f-e)]:
  if not np.isclose(sum(r[key+'_usd'] for r in result),x.sum(),atol=1e-7,rtol=1e-12):raise ValueError('partition cash identity')
 return result

def main(contract,out):
 started=time.monotonic();C=json.loads(Path(contract).read_text());out=Path(out);out.mkdir(exist_ok=False)
 signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('120s budget')));signal.alarm(120)
 if sha(__file__)!=C['source_sha256']:raise ValueError('source identity')
 for p,h in C['inputs'].items():
  if sha(p)!=h:raise ValueError('input drift '+p)
 panel=np.load(C['panel'],allow_pickle=False);pred=np.load(C['predictions'],allow_pickle=False);leg=np.load(C['legs'],allow_pickle=False)
 A=np.arange(C['start'],C['end_exclusive'],14400,dtype=np.int64);sy=panel['symbols'];fi=align(panel['anchors'],A);pi=align(pred['anchors'],A);li=align(leg['E_ts'],A)
 if len(A)!=48 or not np.array_equal(sy,pred['symbols']) or not np.array_equal(sy,leg['symbols']):raise ValueError('frozen window/symbols')
 own=panel['own'][fi];strength=partition(own[:,:,4],own[:,:,5]);zfd=leg['ZFD'][li];rn8=leg['RN8'][li]
 off=pred['off'];cols=pred['m'];P=pred['pred'];count=pred['count']
 if not np.array_equal(off,np.r_[0,np.cumsum(count)]):raise ValueError('ragged counts')
 common={'A':A,'symbols':sy,'own4':own[:,:,4],'own24':own[:,:,5],'strength_class':strength,'NC_ZFD':zfd,'NC_RN8':rn8};R={};checks=[]
 for si,seed in enumerate(('42','2027')):
  q=np.load(C['cash'][seed],allow_pickle=False);cb=np.load(C['combo'][seed],allow_pickle=False);ci=align(q['A'],A);bi=align(cb['E_ts'],A)
  if not np.array_equal(sy,q['symbols']) or not np.array_equal(sy,cb['symbols']) or not cb['trade_mask'][bi].all():raise ValueError('cash/target population or HOLD')
  data={k:q[k][ci] for k in ['q0','q1','mv0','nav0','price','funding','fee','net','unknown']}
  if data['unknown'].any() or not np.allclose(data['price']+data['funding']-data['fee'],data['net'],rtol=0,atol=1e-9):raise ValueError('cash unknown/identity')
  member=np.zeros(strength.shape,bool);delta=np.full(strength.shape,np.nan)
  for t,j in enumerate(pi):
   m=cols[off[j]:off[j+1]];v=P[off[j]:off[j+1],si*3:si*3+2]
   if len(np.unique(m))!=len(m) or np.any(m<0) or np.any(m>=len(sy)):raise ValueError('duplicate/outside member')
   if not np.array_equal(np.isfinite(v[:,0]),np.isfinite(v[:,1])):raise ValueError('unequal scoring population')
   ok=np.isfinite(v).all(1);member[t,m]=True
   if ok.sum()>=2:delta[t,m[ok]]=rank_delta(v[ok,0],v[ok,1])
  direction=np.where(data['q0']>0,0,np.where(data['q0']<0,1,2));target=cb['weights'][bi]
  signed=lambda a:np.where(np.isfinite(a),np.where(a<0,0,1),2)
  specs={'strength':(strength,5,['both_negative','4h_negative_24h_nonnegative','4h_nonnegative_24h_negative','both_nonnegative','unknown']),
   'fund_rank':(signed(zfd),3,['negative','nonnegative','unknown']),
   'fund_rate8':(signed(rn8),3,['negative','nonnegative','unknown']),
   'conditional_rank_shift':(np.where(np.isfinite(delta),np.where(delta>0,1,0),2),3,['nonpositive','positive','unavailable']),
   'score_membership':(member.astype(int),2,['outside','inside'])}
  R[seed]={}
  for name,(g,n,names) in specs.items():
   gg=direction*n+g;rs=aggregate(data['price'],data['funding'],data['fee'],data['mv0'],data['nav0'],data['q0'],target,gg,3*n)
   for k,row in enumerate(rs):row.update(direction=['long','short','flat'][k//n],condition=names[k%n])
   R[seed][name]=rs;checks.append({'seed':seed,'partition':name,'cash_closed':True})
  common.update({seed+'_'+k:v for k,v in data.items()});common[seed+'_target']=target;common[seed+'_rank_delta']=delta;common[seed+'_member']=member
  R[seed]['position_sign_changes']={'start_nonzero_end_opposite':int(((data['q0']*data['q1'])<0).sum()),'start_flat_end_nonzero':int(((data['q0']==0)&(data['q1']!=0)).sum())}
 np.savez_compressed(out/'ALIGNED.npz',**common)
 rec={'status':'DESCRIPTIVE_CASH_PARTITIONS_COMPLETE_NOT_CANDIDATE','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'contract_sha256':sha(contract),'inputs':C['inputs'],'start':C['start'],'end_exclusive':C['end_exclusive'],'anchors':len(A),'days':8,'checks':checks,'results':R,'outputs':{'ALIGNED.npz':sha(out/'ALIGNED.npz')},'seconds':time.monotonic()-started,'peak_rss_gib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,'limits':C['limits']}
 (out/'RESULT.json').write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n');(out/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(out/'RESULT.json')})+'\n');print(json.dumps({k:rec[k] for k in ['status','seconds','peak_rss_gib']}))

if __name__=='__main__':
 try:main(*sys.argv[1:])
 except BaseException as e:
  p=Path(sys.argv[2]);p.mkdir(exist_ok=True);(p/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e)})+'\n');raise

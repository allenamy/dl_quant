"""Independent verifier: original predictions/cash, tie counts, Decimal cash sums."""
import copy,hashlib,json,math
from decimal import Decimal
from pathlib import Path
import numpy as np
ROOT=Path('/dev/shm/tail_held_cash_20260929')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(result):
 for p,s in result['inputs'].items():assert sha(p)==s,('input',p)
 for p,s in result['sources'].items():assert sha(p)==s,('source',p)
 h=np.load('/dev/shm/held_strength_cash_repair_20260928/ALIGNED.npz',allow_pickle=False)
 p=np.load('/dev/shm/tail_risk_20260928/PREDICTIONS.npz',allow_pickle=False)
 z=np.load(ROOT/'ALIGNED.npz',allow_pickle=False);pred=p['pred'];ym=p['labels'];el=p['eligible'];off=p['off'];ms=p['m']
 assert np.array_equal(h['A'],z['A']) and np.array_equal(h['symbols'],p['symbols'])
 index={int(a):i for i,a in enumerate(p['anchors'])};n=0;maxerr=0.
 def same(x,y):
  nonlocal n,maxerr
  n+=1
  if y is None:assert x is None;return
  if isinstance(y,list):
   assert len(x)==len(y)
   for a,b in zip(x,y):same(a,b)
   return
  assert math.isfinite(x) and math.isfinite(y)
  d=abs(x-y);maxerr=max(maxerr,d);assert d<=1e-7,(x,y,d)
 for seed,offset in ((42,0),(2027,3)):
  px=f'{seed}_';mv=h[px+'mv0'];q=h[px+'q0'];nav=h[px+'nav0'];price=h[px+'price'];fund=h[px+'funding'];fee=h[px+'fee']
  for k,x in dict(q=q,mv=mv,nav=nav,price=price,fund=fund,fee=fee,net=h[px+'net']).items():assert np.array_equal(z[px+k],x)
  for mode,col in [('score2',offset),('full90',offset+1),('symmetric',offset+1),('rotated',offset+2)]:
   gs=np.zeros(q.shape,int);probs=np.full(q.shape,np.nan);labels=np.full(q.shape,np.nan)
   for t,a in enumerate(h['A']):
    i=index[int(a)];lo,hi=int(off[i]),int(off[i+1]);m=ms[lo:hi]
    assert len(set(m.tolist()))==len(m) and min(m)>=0 and max(m)<len(h['symbols'])
    full=np.full((q.shape[1],2),np.nan);full[m]=pred[lo:hi,col]
    ys=np.full((q.shape[1],2),np.nan);ys[m]=np.where(el[lo:hi],ym[lo:hi],np.nan)
    qs=[]
    for tail in (0,1):
     values=full.sum(1).clip(0,1) if mode=='symmetric' else full[:,tail]
     finite=np.isfinite(values);v=values[finite];qb=np.full(len(values),5,int)
     # Quantile midpoints from counts strictly smaller/equal, independent of rankdata.
     uniq,inv,cnt=np.unique(v,return_inverse=True,return_counts=True);before=np.cumsum(cnt)-cnt
     qb[finite]=np.floor((before[inv]+cnt[inv]/2)*5/len(v)).astype(int)
     qs.append(qb)
    for j in range(q.shape[1]):
     direction=0 if q[t,j]>0 else 1 if q[t,j]<0 else 2;tail=0 if direction==1 else 1
     gs[t,j]=direction*6+qs[tail][j]
     probs[t,j]=min(float(full[j].sum()),1.) if mode=='symmetric' else full[j,tail]
     labels[t,j]=np.max(ys[j]) if mode=='symmetric' else ys[j,tail]
   for k,v in [('groups',gs),('prob',probs),('label',labels)]:assert np.array_equal(v,z[f'{seed}_{mode}_{k}'],equal_nan=True),(mode,k)
   for rr in result['tables'][str(seed)][mode]:
    g=rr['group'];mask=gs==g;ij=list(zip(*np.nonzero(mask)))
    def total(a):return float(sum((Decimal(str(float(a[t,j]))) for t,j in ij),Decimal(0)))
    pv=total(price);fv=total(fund);cv=total(fee);gross=total(abs(mv));loss=total(np.maximum(-price,0));gain=total(np.maximum(price,0))
    for k,v in dict(price_usd=pv,fund_usd=fv,fee_usd=cv,net_usd=pv+fv-cv,gross_usd_sum=gross,price_gain_usd=gain,price_loss_usd=loss,cells=len(ij),positions=sum(mv[t,j]!=0 for t,j in ij)).items():same(rr[k],v)
    same(rr['price_per_initial_gross_bps'],pv/gross*1e4 if gross else None);same(rr['loss_per_initial_gross_bps'],loss/gross*1e4 if gross else None)
    pa=[];na=[]
    for t in range(len(nav)):
     jj=np.flatnonzero(mask[t]);pi=math.fsum(float(price[t,j]) for j in jj);fi=math.fsum(float(fund[t,j]) for j in jj);ci=math.fsum(float(fee[t,j]) for j in jj)
     pa.append(pi/float(nav[t])*1e4);na.append((pi+fi-ci)/float(nav[t])*1e4)
    same(rr['price_anchor_bps'],pa);same(rr['net_anchor_bps'],na)
    same(rr['price_daily_contribution_bps'],[sum(pa[t:t+6]) for t in range(0,48,6)])
    same(rr['net_daily_contribution_bps'],[sum(na[t:t+6]) for t in range(0,48,6)])
    valid=[(t,j) for t,j in ij if math.isfinite(probs[t,j]) and math.isfinite(labels[t,j])]
    den=math.fsum(abs(float(mv[t,j])) for t,j in valid)
    same(rr['label_covered_initial_gross'],den);same(rr['missing_label_initial_gross'],math.fsum(abs(float(mv[t,j])) for t,j in ij if not math.isfinite(labels[t,j])))
    same(rr['predicted_adverse_probability'],math.fsum(abs(float(mv[t,j]))*float(probs[t,j]) for t,j in valid)/den if den else None)
    same(rr['realized_adverse_event_frequency'],math.fsum(abs(float(mv[t,j]))*float(labels[t,j]) for t,j in valid)/den if den else None)
   for key,ar in [('price_usd',price),('fund_usd',fund),('fee_usd',fee),('net_usd',h[px+'net'])]:same(sum(r[key] for r in result['tables'][str(seed)][mode]),float(ar.sum()))
 return dict(checks=n,max_abs_error=maxerr)
def main():
 result=json.loads((ROOT/'RESULT.json').read_text());term=json.loads((ROOT/'TERMINAL.json').read_text())
 assert term['rc']==0 and term['inputs_rechecked'] is True
 for p,s in term['outputs'].items():assert sha(ROOT/p)==s
 v=verify(result);bad=copy.deepcopy(result);bad['tables']['42']['full90'][0]['price_usd']+=100
 rejected=False
 try:verify(bad)
 except AssertionError:rejected=True
 assert rejected
 v.update(status='PASS',result_sha256=sha(ROOT/'RESULT.json'),verifier_sha256=sha(__file__),real_output_plus_100_rejected=rejected)
 (ROOT/'VERIFY.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
if __name__=='__main__':main()

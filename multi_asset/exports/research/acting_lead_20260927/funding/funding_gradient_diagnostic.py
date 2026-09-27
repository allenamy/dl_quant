#!/usr/bin/env python3
# Frozen prereg db643ed57; stdout-only, one CPU thread, no remote writes.
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[k]='1'
import json,time,hashlib,resource,gc
import numpy as np
import torch
torch.set_num_threads(1);torch.set_num_interop_threads(1)
START=time.time()
UTILITY_SOURCE_SHA='66bc7c3e69af7aab7062b562674fb3bbe272fd9a28fc3ea9639143f4549420db'
def utility(score,z24,zfd,wl,tau,hard=False):
    z=(score-score.mean())/(score.std()+1e-8);n=len(z)
    rank=torch.argsort(torch.argsort(z)).float()/max(n-1,1)-.5 if hard else (torch.sigmoid((z[:,None]-z[None,:])/tau).sum(1)-.5)/max(n-1,1)-.5
    r=wl[0]*rank+wl[1]*z24+wl[2]*zfd;r=r-r.mean();u=r/(r.abs().sum()+1e-8);cap=2.5/n;u=cap*torch.tanh(u/cap)
    return u-u.mean()
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
paths={
 'p':('/dev/shm/news2_2026-09-23/work/f10_s42/F10_OOF.npz','2af48f7c84bfd5de2df83fa1266455ca718558a80ae68017de444b510a592d51'),
 'l':('/dev/shm/news2_2026-09-23/work/legs.npz','9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65'),
 'f':('/workspace/dlarch_2026-09-24/king_fam_2026-09-27/T_NET.npz','929ff9f6c68280f1994ffb3c34c0c53114d96ad034686183f9dfd9b09b5c7a5c'),
 'y':('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz','ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'),
 'd':('/workspace/d10_reread_2026-09-27/r2b_20260927T113701Z/r2/ledger_full_ms_ext_20260927T08.npz','76b777bf07d5b3630e9d4818b562cd798f1ca495af8af190c8f24421c9b538db'),
 'b':('/dev/shm/news2_2026-09-23/work/combo_s42/scaled_diagnostic.npz','f4630a20f796bce26590aedeadfc28791be7eeecee8c14789f418b5a08de4388')}
for p,h in paths.values():assert sha(p)==h,p
z={k:np.load(p,allow_pickle=False) for k,(p,h) in paths.items()}
A=z['p']['E_ts'];S=z['p']['symbols'];P=z['p']['P'];Y0=z['y']['y4s'];F0=z['f']['F'];TN=z['f']['T_net'];AF=z['f']['E_ts'];covered0=z['f']['covered']
assert np.array_equal(z['l']['E_ts'],A) and np.array_equal(z['l']['symbols'],S) and np.array_equal(z['f']['symbols'],S) and np.array_equal(z['y']['E_ts'],AF)
assert np.array_equal(z['b']['symbols'],S)
finite=np.isfinite(Y0)&np.isfinite(TN)&np.isfinite(F0)
identity=float(np.max(np.abs(TN[finite]+F0[finite]-Y0[finite])));assert identity<=2e-15,identity
del TN,finite
Y=np.full(P.shape,np.nan,np.float32);F=np.full(P.shape,np.nan,np.float32);cov=np.zeros(len(A),bool)
ij=np.searchsorted(A,AF);assert np.array_equal(A[ij],AF)
Y[ij]=Y0;cov[ij]=covered0
# Actual settlement cash uses each event rate and the strict millisecond half-open interval.
D=z['d'];assert np.array_equal(D['symbols'],S)
off=D['off'];ft=D['ft_ms'];rates=D['rate'];F64=np.zeros(P.shape,np.float64)
boundary_t=np.array([0,1,14400000,14400001]);boundary_r=np.array([1.,2.,4.,8.])
assert boundary_r[(boundary_t>0)&(boundary_t<=14400000)].sum()==6.
assert boundary_r[(boundary_t>=0)&(boundary_t<=14400000)].sum()!=6.
for j in range(len(S)):
 tm=ft[off[j]:off[j+1]];rt=rates[off[j]:off[j+1]]
 assert np.all(np.diff(tm)>0),(j,'duplicate or unsorted ms')
 cc=np.r_[0.,np.cumsum(rt)];lo=np.searchsorted(tm,A*1000,side='right');hi=np.searchsorted(tm,(A+14400)*1000,side='right')
 F64[:,j]=cc[hi]-cc[lo]
 for i in np.linspace(0,len(A)-1,8,dtype=int):
  direct=rt[(tm>A[i]*1000)&(tm<=(A[i]+14400)*1000)].sum()
  assert abs(F64[i,j]-direct)<2e-12,(i,j)
F[:]=F64.astype(np.float32)
legacy_delta=F64[ij]-F0
legacy_diff={'cells_abs_gt_1e_12':int((np.abs(legacy_delta[covered0])>1e-12).sum()),'max_abs_rate_delta':float(np.max(np.abs(legacy_delta[covered0]))),'d10_F_array_sha256':hashlib.sha256(F64.tobytes()).hexdigest(),'boundary_positive_and_red_pass':True,'independent_direct_sum_checks':8*len(S),'interval':'(A*1000,(A+14400)*1000]'}
del F64,legacy_delta,off,ft,rates,Y0,F0
WL=z['l']['WL'];Z24=z['l']['Z24'];ZFD=z['l']['ZFD'];ready=z['l']['ready']
fold=np.array([time.strftime('%Y',time.gmtime(int(a))) if a<1735689600 else time.strftime('%Y%m',time.gmtime(int(a))) for a in A])
C=[np.flatnonzero(np.isfinite(p)) for p in P]
choices=[];eligible={};excluded={}
for era,m in [('pre2026',A<1767225600),('2026',A>=1767225600)]:
 starts=[]
 for st in range(0,len(A)-119,48):
  ix=np.arange(st,st+120)
  if not m[ix].all() or len(set(fold[ix]))!=1 or not ready[ix].all() or not cov[ix].all() or min(map(len,C[st:st+120]))<50:continue
  held=set();good=True
  for i in ix:
   held.update(C[i]);h=list(held)
   if not (np.isfinite(Y[i,h]).all() and np.isfinite(F[i,h]).all()):good=False;break
  if good:starts.append(st)
 assert len(starts)>=4,(era,len(starts))
 chosen=[starts[j] for j in np.linspace(0,len(starts)-1,4,dtype=int)]
 eligible[era]={'candidate_starts':len(starts),'selected':[int(A[s]) for s in chosen]}
 choices += [(era,s) for s in chosen]
# All score observations, labels and held path are fixed. Gradients are w.r.t scores and alpha only.
def ag(v,qs,alpha,retain=True):
 g=torch.autograd.grad(v,qs+[alpha],retain_graph=retain,allow_unused=False)
 return torch.cat([a.reshape(-1) for a in g[:-1]]),float(g[-1])
def norm(v):return float(torch.linalg.vector_norm(v))
def ratio(a,b):return norm(a)/max(norm(b),1e-30)
def cosine(a,b):return float(a@b)/(max(norm(a)*norm(b),1e-30))
def stats(x):
 x=np.array(x,dtype=float)
 return {'mean':float(x.mean()),'median':float(np.median(x)),'p05':float(np.quantile(x,.05)),'p95':float(np.quantile(x,.95)),'min':float(x.min()),'max':float(x.max())}
def loss(net):return -net.mean()+.25*torch.topk(-net,max(1,int(np.ceil(.05*len(net))))).values.mean()
rows=[];receipts={}
for era,st in choices:
 ix=np.arange(st,st+120);total=sum(len(C[i])**2 for i in ix)
 if total>64000000:rows.append({'era':era,'start':int(A[st]),'status':'RESOURCE_UNAVAILABLE','sum_n_squared':total});continue
 rp='/dev/shm/news2_2026-09-23/work/f10_s42/'+fold[st]+'/FOLD_RECEIPT.json';rec=json.load(open(rp));assert rec['fold']==fold[st] and rec['seed']==42 and rec['curve'][-1]['epoch_index']==7
 receipts[rp]={'sha256':sha(rp),'elapsed_seconds':rec['elapsed_seconds'],'epoch_seconds':[q['seconds'] for q in rec['curve']]}
 alpha=torch.tensor(rec['curve'][-1]['alpha'],dtype=torch.float32,requires_grad=True)
 qs=[torch.tensor(P[i,C[i]],requires_grad=True) for i in ix]
 def path(qin,al):
  held=torch.zeros(P.shape[1]);prices=[];turns=[];carries=[];const=[];W=[]
  for k,i in enumerate(ix):
   c=C[i];u=utility(qin[k],torch.tensor(np.nan_to_num(Z24[i,c],nan=0.)),torch.tensor(np.nan_to_num(ZFD[i,c],nan=0.)),torch.tensor(WL[i]),.3)
   target=torch.zeros(P.shape[1]).scatter(0,torch.tensor(c),u);new=(1-al)*held+al*target
   prices.append(1e4*(new*torch.tensor(np.nan_to_num(Y[i],nan=0.))).sum());turns.append(3.52*torch.sqrt((new-held)**2+1e-12).sum());carries.append(1e4*(new*torch.tensor(np.nan_to_num(F[i],nan=0.))).sum());const.append(new.sum());W.append(new)
   held=new
  return [torch.stack(a)[24:] for a in (prices,turns,carries,const,W)]
 p,t,f,c,w=path(qs,alpha);n0=p-t;n1=n0-f;L0=loss(n0);L1=loss(n1)
 gp,ap=ag(-p.mean(),qs,alpha);gt,at=ag(t.mean(),qs,alpha);gf,af=ag(f.mean(),qs,alpha);g0,a0=ag(L0,qs,alpha);g1,a1=ag(L1,qs,alpha)
 gzero,az=ag(loss(n0-torch.zeros_like(f)),qs,alpha);assert torch.equal(gzero,g0) and az==a0 and float(loss(n0-torch.zeros_like(f)))==float(L0)
 gm,am=ag((-f).mean(),qs,alpha);assert torch.equal(gm,-gf) and am==-af
 gc_,ac=ag(c.mean(),qs,alpha);assert abs(float(c.mean()))<1e-5 and norm(gc_)<1e-5,(float(c.mean()),norm(gc_))
 # Finite difference in fixed score L2 units. This leaves every input and utility setting unchanged.
 delta=-1e-4*gf/max(norm(gf),1e-30);n=0;qstep=[]
 for q in qs:qstep.append(q.detach()+delta[n:n+len(q)]);n+=len(q)
 with torch.no_grad():fstep=float(path(qstep,alpha.detach())[2].mean())
 expected=-1e-4*norm(gf);observed=fstep-float(f.mean());fdrel=abs(observed-expected)/max(abs(expected),1e-30)
 eligible_targets=[]
 for i in ix[24:]:
  col=C[i];fv=F[i,col].astype(float);yv=Y[i,col].astype(float)
  eligible_targets.append(float(np.linalg.norm(fv-fv.mean())/max(np.linalg.norm(yv-yv.mean()),1e-30)))
 r={'era':era,'start':int(A[st]),'end':int(A[st+119]),'fold':fold[st],'status':'MEASURED','alpha':float(alpha),'n_symbols_min':min(len(C[i]) for i in ix),'n_symbols_max':max(len(C[i]) for i in ix),'sum_n_squared':total,
 'price_bps':stats(p.detach()),'turnover_bps':stats(t.detach()),'carry_paid_bps':stats(f.detach()),'loss0':float(L0),'loss1':float(L1),'loss_delta':float(L1-L0),
 'score_grad_norms':{'price':norm(gp),'turnover':norm(gt),'carry':norm(gf),'L0':norm(g0),'L1':norm(g1),'delta':norm(g1-g0)},
 'score_grad_ratios':{'carry_to_price':ratio(gf,gp),'carry_to_turnover':ratio(gf,gt),'loss_delta_to_L0':ratio(g1-g0,g0)},
 'score_grad_cosines':{'carry_price':cosine(gf,gp),'carry_L0':cosine(gf,g0),'L0_L1':cosine(g0,g1)},
 'alpha_derivatives':{'price':ap,'turnover':at,'carry':af,'L0':a0,'L1':a1},'weight_target_carry_price_ratio':stats(eligible_targets),
 'controls':{'zero_f_identity':True,'sign_flip_exact':True,'constant_f_abs_bps':abs(float(c.mean())),'constant_f_score_grad_norm':norm(gc_),'finite_difference_expected_bps':expected,'finite_difference_observed_bps':observed,'finite_difference_relative_error':fdrel,'finite_difference_pass':observed<0 and fdrel<=.05},
 'rss_max_kb_sofar':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 rows.append(r)
 del qs,p,t,f,c,w,gp,gt,gf,g0,g1,gzero,gm,gc_,L0,L1,n0,n1,alpha
 gc.collect()
# Same existing published book, no new strategy. Unknown held outcomes cannot be zero filled.
B=z['b']['weights'];AB=z['b']['E_ts'];idx=np.searchsorted(A,AB);assert np.array_equal(A[idx],AB)
book=[]
for j,i in enumerate(idx):
 if not cov[i]:continue
 held=B[j]!=0
 if not (np.isfinite(Y[i,held]).all() and np.isfinite(F[i,held]).all()):continue
 price=float(1e4*np.dot(B[j,held],Y[i,held]));carry=float(1e4*np.dot(B[j,held],F[i,held]));turn=float(3.52*np.abs(B[j]-(B[j-1] if j else 0)).sum())
 book.append([int(A[i]),price,carry,turn])
book=np.array(book);summ={}
for era,mask in [('pre2026',book[:,0]<1767225600),('2026',book[:,0]>=1767225600)]:summ[era]={'anchors':int(mask.sum()),'price_bps':stats(book[mask,1]),'carry_paid_bps':stats(book[mask,2]),'turnover_bps':stats(book[mask,3]),'mean_net_omitted_carry_bps':float(book[mask,2].mean())}
meas=[r for r in rows if r['status']=='MEASURED'];allcontrols=all(r['controls']['finite_difference_pass'] for r in meas)
medp=np.median([r['score_grad_ratios']['carry_to_price'] for r in meas]);medt=np.median([r['score_grad_ratios']['carry_to_turnover'] for r in meas])
out={'utc_started':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(START)),'utc_ended':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'prereg_commit':'db643ed57_with_D10_reading_before_run_revision','source_utility_sha':UTILITY_SOURCE_SHA,'inputs':paths,'unit':'bps on training utility nominal normalization, no GM=2; not NAV bps','identity_max_error':identity,'funding_truth':legacy_diff,'eligible':eligible,'fold_receipts':receipts,'spans':rows,'existing_book':summ,'all_controls_pass':allcontrols,'median_carry_to_price_score_gradient':float(medp),'median_carry_to_turnover_score_gradient':float(medt),'predicate':'LOCAL_DIRECTION_WORTH_TWO_ARM_TEST' if allcontrols and (medp>=.01 or medt>=.1) else 'NOT_ESTABLISHED','wall_seconds':time.time()-START,'rss_max_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limitations':['s42 only; OOF eval scores treated as independent local variables, not network-parameter gradients','D10 extended millisecond event F; frozen original covered window excludes September; interval state rules are irrelevant to settled cash sum','Existing-book turnover is 3.52 proxy for context, not cash certification','No sampling confidence or efficacy MDE from eight descriptive spans']}
print(json.dumps(out,indent=2,allow_nan=False))

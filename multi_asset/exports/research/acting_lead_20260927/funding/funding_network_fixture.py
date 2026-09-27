#!/usr/bin/env python3
"""Preregistered fixed-tape implementation fixture; no candidate/OOS inference."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import pathlib,json,hashlib,time,sys,resource,zipfile,struct,ast,copy,collections
import numpy as np
import torch
from torch import nn
T0=time.time();ROOT=pathlib.Path(__file__).resolve().parent
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
OUT=ROOT/'run';OUT.mkdir(exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def log(*v):print(time.strftime('%H:%M:%SZ',time.gmtime()),*v,flush=True)
def write(name,v):
 (OUT/name).write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.item() if hasattr(x,'item') else str(x)))
def checkpoint():
 assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=6*2**30,'RSS limit'
 assert time.time()-T0<900,'wall limit'
 assert torch.cuda.max_memory_allocated()<=8*2**30,'CUDA allocation limit'
inputs={
 'features':('/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz','3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8'),
 'legs':('/dev/shm/news2_2026-09-23/work/legs.npz','9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65'),
 'nc_model':('/dev/shm/news2_2026-09-23/work/f10_s42/202608/model.pt','9475cdb37c93c899878a18c05902dadfc06c5ac54d74df63750df3cd8198f5a3'),
 'nc_scores':('/dev/shm/news2_2026-09-23/work/f10_s42/202608/scores.npz','dc5ac3f31b33579e9a0ec01e3a8aa8af36b87d24727d6584deeb949a8c73bf1f'),
 'net_source':(str(ROOT/'news2_train_f10_source.py'),'66bc7c3e69af7aab7062b562674fb3bbe272fd9a28fc3ea9639143f4549420db')}
for k,(p,h) in inputs.items():assert sha(p)==h,(k,p)
for n in ('funding_real_cash_result.json','simlib.py','INPUT_MANIFEST.json','seed_02.json'):
 inputs[n]=(str(ROOT/n),sha(ROOT/n))
assert inputs['INPUT_MANIFEST.json'][1]=='59875e5a69db415f5ce20b35b888f2d49a31427fdde8b7b847a9645ee135a5ae'
log('input identities verified')
D=json.load(open(ROOT/'funding_real_cash_result.json'));R=json.load(open(ROOT/'seed_02.json'));W=R['windows'][:6]
assert D['verdict']=='FIXED_CANONICAL_PATH_CASH_PASS'
assert D['reference_sha']==sha(ROOT/'seed_02.json')
assert D['initial_state_sha']==R['initial_state_sha256']
# Canonical readers only; no second execution simulator.
import simlib as L
M=L.Mirror('/workspace/replay_exec_mirror_59875e5a');P=L.Panel(M);L.build_references(M,P);F=L.FundingBook(M)
tr=sorted(D['trade_log'],key=lambda v:v[0]);nav=D['initial_state']['nav0_usdt'];initial=D['initial_state']['positions_qty'];syms=sorted(set(initial)|{x[1] for x in tr})
tb=collections.defaultdict(list)
for j,x in enumerate(tr):tb[x[1]].append((j,x))
q0=lambda s,t:initial.get(s,0.)+sum(x[2] for _,x in tb[s] if x[0]<=t)
qminus=lambda s,t:initial.get(s,0.)+sum(x[2] for _,x in tb[s] if x[0]<t)
def px(s,t):
 v=P.px(s,L.floor_b(t));assert v is not None and np.isfinite(v) and v>0,(s,t,'missing price');return v
E=[]
for s in syms:
 for t in F.settlements(s,W[0]['t0'],W[-1]['t1']):
  E.append((t,s,px(s,t),F.rate[(s,int(t))],qminus(s,t)))
E.sort()
CP=np.zeros((6,len(tr)));CF=np.zeros_like(CP);CW=np.zeros_like(CP);base=[];errors=[]
for k,w in enumerate(W):
 p0,p1={},{}
 for s in syms:
  if q0(s,w['t0'])!=0 or any(w['t0']<x[0]<=w['t1'] for _,x in tb[s]):p0[s]=px(s,w['t0']);p1[s]=px(s,w['t1'])
 price=sum(q0(s,w['t0'])*(p1[s]-p0[s]) for s in p0)
 fee=0.;cash=sum(-q*p*r for t,s,p,r,q in E if w['t0']<t<=w['t1'])
 for j,x in enumerate(tr):
  t,s,dq,p=x[:4]
  if t<=w['t0']:CP[k,j]=px(s,w['t1'])-px(s,w['t0'])
  elif t<=w['t1']:CP[k,j]=px(s,w['t1'])-p;price+=dq*CP[k,j];fee+=x[6];CW[k,j]=x[6]/abs(dq)
  CF[k,j]=sum(-ep*r for et,es,ep,r,eq in E if es==s and max(t,w['t0'])<et<=w['t1'])
 err=[price-w['price_trade'],fee-w['fee'],cash-w['funding']];assert max(map(abs,err))<=1e-8,(k,err)
 base.append([price,fee,cash]);errors.append(err)
log('all-event cash/price/fee closed',len(E),'events',sum(q==0 for t,s,p,r,q in E),'zero quantity events')
# Uncompressed .npz members are mmap-ed in place. No full feature materialization.
def mmap_npy(p,name):
 with zipfile.ZipFile(p) as z:info=z.getinfo(name+'.npy');assert info.compress_type==zipfile.ZIP_STORED
 with open(p,'rb') as f:
  f.seek(info.header_offset);raw=f.read(30);fields=struct.unpack('<IHHHHHIIIHH',raw);f.seek(fields[-2]+fields[-1],1)
  ver=np.lib.format.read_magic(f);shape,order,dtype=(np.lib.format.read_array_header_1_0(f) if ver==(1,0) else np.lib.format.read_array_header_2_0(f));offset=f.tell()
 assert not order
 return np.memmap(p,mode='r',offset=offset,shape=shape,dtype=dtype)
fp=inputs['features'][0];a=mmap_npy(fp,'anchors');off=mmap_npy(fp,'off');symbols=np.array(mmap_npy(fp,'symbols'));mm=mmap_npy(fp,'m');X82=mmap_npy(fp,'X82');X89=mmap_npy(fp,'X89')
A=np.arange(R['run_start_anchor']+14400,R['run_start_anchor']+7*14400,14400);ii=np.searchsorted(a,A);assert np.array_equal(a[ii],A)
leg=np.load(inputs['legs'][0]);assert np.array_equal(leg['E_ts'],a) and np.array_equal(leg['symbols'],symbols)
X=[];C=[]
for i in ii:
 sl=slice(int(off[i]),int(off[i+1]));X.append(np.concatenate((X82[sl],X89[sl]),1).copy());C.append(np.array(mm[sl],dtype=np.int64));assert np.isfinite(X[-1]).all()
# AST definitions preserve the exact architecture and utility, without executing trainer side effects.
ns={'torch':torch,'nn':nn};tree=ast.parse(pathlib.Path(inputs['net_source'][0]).read_text());nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ('Net','utility')];assert len(nodes)==2
exec(compile(ast.Module(body=nodes,type_ignores=[]),inputs['net_source'][0],'exec'),ns);Net=ns['Net'];utility=ns['utility']
assert torch.cuda.is_available();dev='cuda';torch.cuda.set_per_process_memory_fraction(8*2**30/torch.cuda.get_device_properties(0).total_memory)
ck=torch.load(inputs['nc_model'][0],map_location='cpu',weights_only=False);mu=ck['mu'].to(dev);sd=ck['sd'].to(dev)
xx=[torch.tensor(v,device=dev) for v in X];cols=[torch.tensor(c,device=dev) for c in C];ww=len(symbols)
z24=[torch.tensor(np.nan_to_num(leg['Z24'][i,C[k]],nan=0.),device=dev) for k,i in enumerate(ii)];zfd=[torch.tensor(np.nan_to_num(leg['ZFD'][i,C[k]],nan=0.),device=dev) for k,i in enumerate(ii)];wl=[torch.tensor(leg['WL'][i],device=dev) for i in ii]
modelref=Net().to(dev);modelref.load_state_dict(ck['state_dict']);modelref.eval();ncs=np.load(inputs['nc_scores'][0]);refdiff=[]
with torch.no_grad():
 for k,A0 in enumerate(A):
  nr=int(np.flatnonzero(ncs['E_ts']==A0)[0]);v=modelref.f(torch.clamp((xx[k]-mu)/sd,-5,5)).squeeze(-1).cpu().numpy();refdiff.append(float(np.max(np.abs(v-ncs['P'][nr,C[k]]))))
assert max(refdiff)<2e-6,refdiff
del modelref
si={s:j for j,s in enumerate(symbols)};ai={int(t):k for k,t in enumerate(A)};coverage=[];share=collections.defaultdict(float)
for j,x in enumerate(tr):
 if x[8] in ai and x[1] in si and si[x[1]] in C[ai[x[8]]]:coverage.append(j);share[(x[8],x[1])]+=abs(x[2]*x[3])
jj=np.array(coverage);anchors=np.array([ai[tr[j][8]] for j in jj]);ss=np.array([si[tr[j][1]] for j in jj]);scale=np.array([nav/tr[j][3]*abs(tr[j][2]*tr[j][3])/share[(tr[j][8],tr[j][1])] for j in jj])
def tt(v):return torch.tensor(v,device=dev,dtype=torch.float64)
cp=tt(CP[:,jj]);cf=tt(CF[:,jj]);cw=tt(CW[:,jj]);b=tt(base);scale=tt(scale);dq=tt([tr[j][2] for j in jj]);ait=torch.tensor(anchors,device=dev);sit=torch.tensor(ss,device=dev)
torch.manual_seed(42);model0=Net().to(dev)
def weights(model):
 torch.manual_seed(20260927);model.train();held=torch.zeros(ww,device=dev);res=[]
 for k in range(6):
  score=model.f(torch.clamp((xx[k]-mu)/sd,-5,5)).squeeze(-1);u=utility(score,z24[k],zfd[k],wl[k],.5)
  target=torch.zeros(ww,device=dev).scatter(0,cols[k],u);held=(1-model.alpha())*held+model.alpha()*target;res.append(held)
 return torch.stack(res)
with torch.no_grad():wref=weights(model0).detach().clone()
def parts(model):
 d=scale*(weights(model)-wref)[ait,sit].double();p=b[:,0]+cp@d;fee=b[:,1]+cw@(torch.abs(dq+d)-torch.abs(dq));cash=b[:,2]+cf@d
 return p*1e4/nav,fee*1e4/nav,cash*1e4/nav,d

def loss(p,f,c):
 net=p-f+c;return -net.mean()+.25*torch.topk(-net,1).values.mean()
def flatgrad(v,model):return torch.cat([g.reshape(-1) for g in torch.autograd.grad(v,list(model.parameters()),retain_graph=True)])
def norm(v):return float(torch.linalg.vector_norm(v))
p,f,c,d=parts(model0);L0=loss(p,f,torch.zeros_like(c));L1=loss(p,f,c)
gp=flatgrad(-p.mean(),model0);gf=flatgrad(f.mean(),model0);gc=flatgrad(-c.mean(),model0);g0=flatgrad(L0,model0);g1=flatgrad(L1,model0)
assert norm(gc)>0
zero=flatgrad(loss(p,f,torch.zeros_like(c)),model0);assert torch.equal(zero,g0)
sign=flatgrad(c.mean(),model0);assert torch.equal(sign,-gc)
# Explicit pre-fill event control, using the first actual fill from the prior receipt.
chosen=D['linear_carry']['chosen_actual_fill'];j=next(j for j in jj if tr[j]==chosen);col=int(np.flatnonzero(jj==j)[0]);early=[e for e in E if e[1]==chosen[1] and int(chosen[8])<=e[0]<=chosen[0]];assert early
et,es,ep,er,eq=early[-1];correct=d[col]*0.;wrong=-d[col]*ep*er
pre_norm=norm(flatgrad(correct,model0));wrong_norm=norm(flatgrad(wrong,model0));assert pre_norm==0 and wrong_norm>0
# Linear cash FD at an actual fill, including zero-held future events absent from fund_log.
eps=1e-4;exact=float(cf[:,col].sum());pert=tt(np.zeros(len(jj)));pert[col]=eps
fd=float(((cf@pert).sum()-(cf@(-pert)).sum())/(2*eps));assert abs(fd-exact)<1e-12
initstate=copy.deepcopy(model0.state_dict())
def same(a,b):
 if isinstance(a,torch.Tensor):return torch.equal(a,b)
 if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
 if isinstance(a,(tuple,list)):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
 return a==b

def step(arm,zero=False):
 model=Net().to(dev);model.load_state_dict(initstate);opt=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4)
 pp,ff,cc,_=parts(model);ls=loss(pp,ff,torch.zeros_like(cc) if arm==0 or zero else cc);opt.zero_grad();ls.backward();gn=float(nn.utils.clip_grad_norm_(model.parameters(),1.));opt.step();checkpoint()
 return model,opt,{'loss_before':float(ls.detach()),'gradient_norm_before_clip':gn,'alpha_after':float(model.alpha().detach())}
# No extra candidate: instrument-only zero-carry duplicate state/optimizer equality.
z0,o0,_=step(0,True);z1,o1,_=step(1,True);assert same(z0.state_dict(),z1.state_dict()) and same(o0.state_dict(),o1.state_dict())
zero_identical=True;del z0,z1,o0,o1
models=[];opts=[];curves=[]
for arm in (0,1):
 m,o,r=step(arm);models.append(m);opts.append(o)
 with torch.no_grad():pp,ff,cc,_=parts(m);r.update(price_nav_bps=pp.cpu().tolist(),fee_nav_bps=ff.cpu().tolist(),cash_nav_bps=cc.cpu().tolist(),common_clock_loss_with_cash=float(loss(pp,ff,cc)))
 curves.append(r);torch.save({'state_dict':m.state_dict(),'label':'IMPLEMENTATION_FIXTURE_NOT_CANDIDATE','seed':42,'epoch_count':1,'optimizer_state':o.state_dict()},OUT/f'A{arm}_implementation.pt')
param_delta=torch.cat([(x-y).detach().reshape(-1) for x,y in zip(models[1].parameters(),models[0].parameters())]);checkpoint()
result={'verdict':'NETWORK_REACHABLE_CARRY_IMPLEMENTATION_PASS','prereg_commit':'53b61495f','utc_start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(T0)),'utc_end':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'inputs':inputs,'code_sha':sha(__file__),'windows':W,'baseline_cash_price_fee_errors_usd':errors,'all_funding_events':len(E),'zero_baseline_qty_funding_events':sum(q==0 for t,s,p,r,q in E),'feature_anchors':A.tolist(),'feature_members':[len(x) for x in C],'covered_rebalance_fills':len(jj),'all_fills':len(tr),'covered_notional':sum(abs(tr[j][2]*tr[j][3]) for j in jj),'total_notional':sum(abs(x[2]*x[3]) for x in tr),'nc_reference_max_score_difference':max(refdiff),'baseline_losses':{'A0':float(L0.detach()),'A1':float(L1.detach())},'gradient_norms':{'price':norm(gp),'fee':norm(gf),'carry':norm(gc),'A0':norm(g0),'A1':norm(g1),'A1_minus_A0':norm(g1-g0)},'carry_to_price_gradient_ratio':norm(gc)/norm(gp),'carry_to_fee_gradient_ratio':norm(gc)/max(norm(gf),1e-30),'controls':{'zero_carry_parameters_optimizer_bitwise_equal':zero_identical,'pre_fill_gradient_norm':pre_norm,'backdated_red_gradient_norm':wrong_norm,'carry_sign_exact':True,'cash_fd_derivative':fd,'cash_derivative':exact,'cash_fd_error':abs(fd-exact),'earlier_event':early[-1]},'arms':curves,'parameter_delta_l2':norm(param_delta),'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated(),'gpu_peak_reserved_bytes':torch.cuda.max_memory_reserved(),'rss_peak_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'wall_seconds':time.time()-T0,'limitations':['Six known NC OOF windows used for optimization; no OOS or candidate inference','Fixed executed tape local linearization, not actual fills from changed network policy','Both arms change original price-clock objective; A0 is not unchanged NC training','NC old service-consistent features, not D10 corrected candidate inputs','Frozen protective fills and initial inventory; no replanning or stop feedback','Parameter gradients local; no full canonical book efficacy result']}
write('RESULT.json',result);log(result['verdict'],result['gradient_norms'],result['wall_seconds'])

"""Two-anchor synthetic CPU parameter controls. No alpha or market-data evaluation."""
import ast,copy,hashlib,json,math,os,pathlib,signal,sys,time
N_ANCHORS=2;N_NAMES=80;FD_EPS=(1e-3,1e-4)
EVENTS=((1,0,8.,.005),(1440000,1,0,0.),(14400012,0,10.,.01),(15840000,0,9.,.03),(15840000,1,1,0.),(21600000,0,12.,-.02))
PINS={
 'oracle':('shared_parameter_cash_oracle.py','26b08644f091713641cfcd389d89e16e80dc906134042255ca31bdb25495fd66'),
 'net':('/workspace/dlarch_2026-09-24/f10d10_2026-09-27/vendor_news2_20260923/devices/news2_train_f10.py','66bc7c3e69af7aab7062b562674fb3bbe272fd9a28fc3ea9639143f4549420db'),
 'combo':('/workspace/dlarch_2026-09-24/chain/devices/combo_target.py','d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544'),
 'stage':('/dev/shm/news2_2026-09-23/vendor_live/fea171/combo_stage.py','fb5a94074583b328b949cd08767c031d9eb705fbdc23d6a371d9bd657b3ca4a8')}


def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def dump(p,v):
 with open(p,'x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())


def validate_events(events):
 keys=[]
 for ms,pri,_,_ in events:
  if not isinstance(ms,int) or pri not in (0,1):raise ValueError('bad event identity')
  if pri==0:keys.append(ms)
 if len(keys)!=len(set(keys)):raise ValueError('duplicate exact settlement cash')
 return sorted(events,key=lambda e:(e[0],e[1]))


def cash_tensor(T,q0,q1,initial=3.,rate_factor=1.,events=EVENTS):
 q=T.as_tensor(initial,dtype=T.float64).detach();rows=[]
 for ms,priority,p,r in validate_events(events):
  if priority==1:q=(q0,q1)[int(p)]
  else:rows.append((ms,-q*p*r*rate_factor))
 return rows


def parts(T,model,X,cash_rate_factor=1.):
 q=model.f(X).squeeze(-1);q0,q1=q[0],q[1];z=0*model.a
 price=T.stack((3.*(10.-8.)+(q0-3.)*(10.-8.2),q0*(11.-10.)+(q1-q0)*(11.-9.1)))+z
 fee=T.stack(((q0-3.).abs()*8.2*.0002,(q1-q0).abs()*9.1*.0002))+z
 rows=cash_tensor(T,q0,q1,rate_factor=cash_rate_factor)
 cash=T.stack((rows[0][1]+z,T.stack([v for _,v in rows[1:]]).sum()+z))
 return price/10.,fee/10.,cash/10.,q # 1e4/V0=0.1; all NAV bps


def loss(T,p,f,c,carry):
 u=p-f+c*carry;return -u.mean()+.25*T.topk(-u,1).values.mean()


def gradient(T,model,obj):
 return T.cat([g.reshape(-1) for g in T.autograd.grad(obj,tuple(model.parameters()),allow_unused=False)])


def tensor_tree_equal(T,a,b):
 if isinstance(a,T.Tensor):return isinstance(b,T.Tensor) and T.equal(a,b)
 if type(a)!=type(b):return False
 if isinstance(a,dict):return a.keys()==b.keys() and all(tensor_tree_equal(T,a[k],b[k]) for k in a)
 if isinstance(a,(list,tuple)):return len(a)==len(b) and all(tensor_tree_equal(T,x,y) for x,y in zip(a,b))
 return a==b


def tree_hash(T,v):
 h=hashlib.sha256()
 def visit(x):
  if isinstance(x,T.Tensor):h.update(str((x.dtype,tuple(x.shape))).encode());h.update(x.detach().cpu().contiguous().numpy().tobytes())
  elif isinstance(x,dict):
   for k in sorted(x,key=repr):h.update(repr(k).encode());visit(x[k])
  elif isinstance(x,(tuple,list)):
   for z in x:visit(z)
  else:h.update(repr(x).encode())
 visit(v);return h.hexdigest()


def original_classes(T,path):
 tree=ast.parse(pathlib.Path(path).read_text());ns={'torch':T,'nn':T.nn}
 node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Net')
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
 return ns['Net']


def original_step(N,combo,stage):
 from scipy.stats import rankdata
 kernel_nodes=[n for n in ast.parse(pathlib.Path(stage).read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('chain','exec_reshape')]
 assert len(kernel_nodes)==2
 def kernels():
  ns={'np':N};exec(compile(ast.Module(body=kernel_nodes,type_ignores=[]),str(stage),'exec'),ns);return ns
 step_node=next(n for n in ast.parse(pathlib.Path(combo).read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='step')
 ns={'np':N,'rankdata':rankdata,'source_kernels':kernels}
 exec(compile(ast.Module(body=[step_node],type_ignores=[]),str(combo),'exec'),ns)
 return ns['step']


def hard_step(T,king,score,fund,seats,rn8,members,qv,legal,params,kprev,fprev,policy,phi=.55):
 n=len(members);nw=len(kprev);ok=T.isfinite(score);zf=T.full_like(score,float('nan'));v=score[ok]
 ranks=(v[:,None]>v[None,:]).sum(1).double()+1.+((v[:,None]==v[None,:]).sum(1).double()-1.)/2.
 zf[ok]=ranks/max(len(v)-1,1)-.5
 w=T.stack((seats[0],seats[0]*0,seats[2]));w=w/w.sum() if float(w.sum())>1e-12 else T.tensor([.5,0.,.5],dtype=T.float64)
 z1=w[0]*T.nan_to_num(king)+w[2]*T.nan_to_num(fund);z2=w[0]*T.nan_to_num(zf)+w[2]*T.nan_to_num(fund)
 z1=T.where((z1<0)&T.isfinite(rn8)&(rn8<=-.001),0.,z1);z2=T.where((z2<0)&T.isfinite(rn8)&(rn8<=-.001),0.,z2)
 sel=T.isfinite(qv)&(qv>=params['qv4h_min'])
 def chain(z,h):
  v=T.where(sel,z,0.);v=T.where(sel,v-(v[sel].mean() if bool(sel.any()) else 0.),v);g=v.abs().sum()
  if float(g)<1e-9:return None
  v=v/g;cap=params['cap_mult']/max(int(sel.sum()),1);v=T.clamp(v,-cap,cap);g2=v.abs().sum()
  if float(g2)>1e-9:v=v/g2
  target=T.zeros(nw,dtype=T.float64).scatter(0,members,v);smv=h+params['alpha']*(target-h)
  smv=T.where((smv-h).abs()<params['band'],h,smv)
  keep=T.zeros(nw,dtype=T.bool);keep[members[sel]]=True;keep=keep&legal
  return T.where((~keep)&(smv.abs()>1e-12),0.,smv)
 kc=chain(z1,kprev);fc=chain(z2,fprev)
 if kc is None or fc is None:return {'accepted':False,'reason':'degenerate signal','kc':kprev.clone(),'fc':fprev.clone(),'raw':None,'executor_reshaped':None}
 raw=phi*kc+(1-phi)*fc;gross=float(raw.abs().sum());names=int((raw.abs()>1e-9).sum())
 coverage=380 if policy=='literal' else math.ceil(.95*n);minnames=150 if policy=='literal' else math.ceil(.375*n)
 reasons=[]
 if int(ok.sum())<coverage:reasons.append('F10 coverage')
 if not .4<=gross<=1.2:reasons.append('gross')
 if names<minnames:reasons.append('names')
 nz=raw.abs()>1e-12;o=raw.clone()
 if bool(nz.any()):
  o[nz]-=o[nz].mean();g1=o.abs().sum()
  if float(g1)>1e-9:o=o*(raw.abs().sum()/g1)
 return {'accepted':not reasons,'reason':','.join(reasons) if reasons else 'publish','kc':kc,'fc':fc,'raw':raw,'executor_reshaped':o}


def compare_hard(N,a,b):
 if a['accepted']!=b['accepted'] or a['reason']!=b['reason']:raise ValueError('publication decision differs')
 worst=0.
 for key in ('kc','fc','raw','executor_reshaped'):
  if (a[key] is None)!=(b[key] is None):raise ValueError('missing array differs')
  if a[key] is not None:
   err=float(N.max(N.abs(N.asarray(a[key])-N.asarray(b[key]))));worst=max(worst,err)
   if err>1e-12:raise ValueError('hard weights differ:'+key)
 return worst


def run(out):
 t0=time.monotonic();root=pathlib.Path(__file__).resolve().parent
 control=json.loads((out/'COMMAND.json').read_text());signal.setitimer(signal.ITIMER_REAL,max(.001,control['deadline_monotonic']-t0))
 os.environ['CUDA_VISIBLE_DEVICES']=''
 for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 pins={k:(str(root/p) if not p.startswith('/') else p,h) for k,(p,h) in PINS.items()}
 for k,(p,h) in pins.items():assert sha(p)==h,(k,'source drift')
 oracle=json.loads((root/'ROOT_SHARED_PARAMETER_CLOCK_20260927.json').read_text());assert oracle['source_sha256']==pins['oracle'][1]
 import torch as T
 import numpy as N
 T.set_num_threads(1);T.set_num_interop_threads(1);T.use_deterministic_algorithms(True)
 assert not T.cuda.is_initialized()
 theta=T.tensor(.7,dtype=T.float64,requires_grad=True)
 rows=cash_tensor(T,2*theta,-3*theta);dg=float(T.autograd.grad(T.stack([x for _,x in rows]).sum(),theta)[0])
 assert abs(dg-oracle['analytic_gradient'])<1e-9 and abs(dg-oracle['shared_theta_gradient'])<1e-9
 zero=T.tensor(0.,dtype=T.float64,requires_grad=True);dz=float(T.autograd.grad(T.stack([x for _,x in cash_tensor(T,2*zero,-3*zero)]).sum(),zero)[0]);assert abs(dz-dg)<1e-12
 old=T.tensor(1.4,dtype=T.float64,requires_grad=True);new=T.tensor(-2.1,dtype=T.float64,requires_grad=True)
 early=cash_tensor(T,old,new)[1][1]+0*new;de=T.autograd.grad(early,(old,new));assert abs(float(de[0])+.1)<1e-12 and float(de[1])==0
 assert abs(dg-oracle['wrong_drop_predecision_cash'])>.1 and abs(dg-oracle['wrong_charge_current_target'])>.1
 neg=T.tensor(.7,dtype=T.float64,requires_grad=True);dn=float(T.autograd.grad(T.stack([v for _,v in cash_tensor(T,2*neg,-3*neg,rate_factor=-1)]).sum(),neg)[0]);assert dn==-dg
 try:cash_tensor(T,old,new,events=EVENTS+(EVENTS[0],))
 except ValueError as e:duplicate=str(e)
 else:raise AssertionError('duplicate cash accepted')
 scalar={'gradient':dg,'zero_baseline_gradient':dz,'early_prior_gradient':float(de[0]),'early_current_gradient':float(de[1]),'reverse_gradient':dn,'duplicate_rejected':duplicate,'oracle_receipt_sha256':sha(root/'ROOT_SHARED_PARAMETER_CLOCK_20260927.json')}
 dump(out/'SCALAR_CONTROLS.json',scalar)
 Net=original_classes(T,pins['net'][0]);T.manual_seed(42);base=Net().double().eval();assert sum(p.numel() for p in base.parameters())==110082
 X=T.zeros((2,171),dtype=T.float64);X[:,0]=T.tensor([2.,-3.],dtype=T.float64)
 n=sum(p.numel() for p in base.parameters());direction=T.ones(n,dtype=T.float64)/math.sqrt(n)
 def objective(model,part):
  p,f,c,q=parts(T,model,X)
  return {'price':p.mean(),'fee':f.mean(),'carry':c.mean(),'A0':loss(T,p,f,c,0.),'A1':loss(T,p,f,c,1.)}[part]
 def shift(model,d):
  j=0
  with T.no_grad():
   for p in model.parameters():v=direction[j:j+p.numel()].reshape_as(p);p.add_(v*d);j+=p.numel()
 fd=[];norms={};gradients={}
 for part in ('price','fee','carry','A0','A1'):
  g=gradient(T,base,objective(base,part));gradients[part]=g;norms[part]=float(g.norm());ad=float(T.dot(g,direction))
  for eps in FD_EPS:
   plus=copy.deepcopy(base);minus=copy.deepcopy(base);shift(plus,eps);shift(minus,-eps)
   measured=float((objective(plus,part)-objective(minus,part))/(2*eps));error=abs(measured-ad)
   assert error<=1e-8+1e-5*abs(ad),(part,eps,error,ad,measured)
   fd.append({'part':part,'eps':eps,'autograd':ad,'finite_difference':measured,'absolute_error':error})
 gneg=gradient(T,base,-objective(base,'carry'));assert T.equal(gneg,-gradients['carry'])
 dump(out/'NETWORK_FD.json',{'parameter_count':n,'gradient_norms_NAV_bps_per_parameter':norms,'fd':fd,'carry_sign_exact':True,'mode':'float64 eval, synthetic quantities; not production rank/chain'})
 def update(carry,rate_factor=1.):
  model=copy.deepcopy(base).train();opt=T.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4);T.manual_seed(20260927)
  p,f,c,q=parts(T,model,X,cash_rate_factor=rate_factor);value=loss(T,p,f,c,carry);value.backward();grads={k:v.grad.detach().clone() for k,v in model.named_parameters()}
  T.nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
  return {'loss':value.detach(),'gradients':grads,'parameters':copy.deepcopy(model.state_dict()),'optimizer':copy.deepcopy(opt.state_dict()),'parts_before_NAV_bps':{'price':p.detach(),'fee':f.detach(),'carry':c.detach()}},model
 z0,_=update(0.,0.);z1,_=update(1.,0.)
 for field in ('loss','gradients','parameters','optimizer'):assert tensor_tree_equal(T,z0[field],z1[field]),('F0',field)
 a0,m0=update(0.);a1,m1=update(1.)
 delta=max(float((a0['parameters'][k]-a1['parameters'][k]).abs().max()) for k in a0['parameters'])
 one={'F0_bitwise':{k:True for k in ('loss','gradients','parameters','optimizer')},'F0_state_hashes':[tree_hash(T,z0),tree_hash(T,z1)],'A0_loss':float(a0['loss']),'A1_loss':float(a1['loss']),'max_parameter_difference':delta,'A0_parameter_sha':tree_hash(T,a0['parameters']),'A1_parameter_sha':tree_hash(T,a1['parameters']),'A0_optimizer_sha':tree_hash(T,a0['optimizer']),'A1_optimizer_sha':tree_hash(T,a1['optimizer']),'one_step_per_arm':1,'F0_control_steps':2,'no_alpha':True}
 dump(out/'ONE_STEP.json',one)
 refstep=original_step(N,pins['combo'][0],pins['stage'][0]);params={'qv4h_min':250000.,'cap_mult':2.5,'alpha':.1,'band':.00025}
 worst=0.;published=held=0;mutations=0;count=0
 for initial in ('zero','balanced'):
  for policy in ('literal','scaled_diagnostic'):
   kh=N.zeros(84);fh=N.zeros(84)
   if initial=='balanced':kh[:42]=1/84;kh[42:]=-1/84;fh[:42]=1/84;fh[42:]=-1/84
   kt=T.tensor(kh);ft=T.tensor(fh)
   for a in range(2):
    members=N.arange(2,82);king=N.linspace(-.5,.5,80);score=N.floor(N.arange(80)/3).astype(float);fund=N.linspace(.4,-.4,80);seats=N.array([.4,.2,.4]);rn8=N.zeros(80);rn8[:5]=-.002;qv=N.full(80,500000.);legal=N.ones(84,bool)
    if a==1:score[-5:]=N.nan;qv[-6:]=0.;legal[7]=False
    args=(king,score,fund,seats,rn8,members,qv,legal,params)
    ref=refstep(*args,kh,fh,policy)
    targs=tuple(T.tensor(x) if isinstance(x,N.ndarray) else x for x in args)
    got=hard_step(T,*targs,kt,ft,policy);arr={k:(v.detach().numpy() if isinstance(v,T.Tensor) else v) for k,v in got.items()}
    worst=max(worst,compare_hard(N,ref,arr));count+=1;published+=int(ref['accepted']);held+=int(not ref['accepted'])
    bad=hard_step(T,*targs,kt,ft,policy,phi=.5);bad={k:(v.detach().numpy() if isinstance(v,T.Tensor) else v) for k,v in bad.items()}
    try:compare_hard(N,ref,bad)
    except ValueError:mutations+=1
    kh=N.where(N.abs(ref['kc'])>1e-9,ref['kc'],0.);fh=N.where(N.abs(ref['fc'])>1e-9,ref['fc'],0.)
    kt=T.where(got['kc'].abs()>1e-9,got['kc'],0.);ft=T.where(got['fc'].abs()>1e-9,got['fc'],0.)
 assert published>0 and held>0 and mutations>0,(published,held,mutations)
 hard={'scope':'GIVEN_INPUT_STEP_FORWARD_PARITY_ONLY; no continuous evolve/HOLD execution inventory certification','cases':count,'max_abs_weight_error':worst,'published':published,'holds':held,'wrong_phi_rejected_cases':mutations,'hard_rank_has_no_claimed_derivative':True}
 dump(out/'HARD_FORWARD.json',hard)
 assert not T.cuda.is_initialized()
 result={'status':'NO_ALPHA_IMPLEMENTATION_ONLY_PASS','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_sha256':sha(__file__),'pins':pins,'scalar':scalar,'network_fd_controls':len(fd),'hard_forward':hard,'parameter_updates':'F0 two control steps plus A0/A1 one step each; all synthetic, no saved candidate','torch':T.__version__,'python':sys.version,'executable':sys.executable,'cuda_initialized':T.cuda.is_initialized(),'elapsed_seconds':time.monotonic()-t0}
 dump(out/'RESULT.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':run(pathlib.Path(sys.argv[1]))

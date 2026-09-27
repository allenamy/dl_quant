"""Explicit 90s follow-up allocation; original failed attempt preserved."""
import ast,copy,hashlib,importlib.util,json,os,pathlib,subprocess,sys,time
R=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding/cpu_parameter_sources_20260927');OUT=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding/cpu_parameter_control_20260927/f0_byte_followup_20260928')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):
 p=R/(name+'.py');s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
w=load('funding_cpu_parameter_controls');g=load('funding_cpu_parameter_guard')
assert sha(R/'funding_cpu_parameter_controls.py')=='31fcb2f35e3b14150e74ceef25b6c7ad62b8622591bdad52ce8b53dc0d69baa1'
deadline=json.loads((OUT.parent/'F0_FOLLOWUP_BUDGET_20260928.json').read_text())['deadline_monotonic']
if '--child' not in sys.argv:
 if time.monotonic()>=deadline:raise SystemExit('FOLLOWUP_DEADLINE_EXPIRED_NO_START')
 OUT.mkdir(exist_ok=False);os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 rss=sum(map(int,subprocess.check_output(['ps','-u',str(os.getuid()),'-o','rss='],text=True).split()))*1024
 gate={'free':g.public_free(),'uid_rss':rss,'followup_deadline_monotonic':deadline,'source_sha':sha(pathlib.Path(__file__))}
 g.write(OUT/'GATE.json',gate)
 if gate['free']<10*g.G or rss+2*g.G>30*g.G:raise SystemExit('RESOURCE_REFUSED_NO_RETRY')
 p=subprocess.Popen(['/workspace/venv/bin/python','-B',__file__,'--child'],env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'),start_new_session=True,stdout=open(OUT/'stdout.log','x'),stderr=open(OUT/'stderr.log','x'))
 peak=0;reason=None
 while p.poll() is None:
  peak=max(peak,g.memory(p.pid)+g.memory(os.getpid()))
  if time.monotonic()>=deadline:reason='FOLLOWUP_DEADLINE'
  elif peak>7*g.G//4:reason='SOFT_RSS_STOP'
  elif g.public_free()<8*g.G:reason='PUBLIC_SPARE'
  if reason:g.terminate(p);break
  time.sleep(.05)
 rc=p.wait();g.write(OUT/'TERMINAL.json',{'rc':rc,'reason':reason,'peak_rss':peak,'pid':p.pid,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'followup_deadline_monotonic':deadline,'no_retry':True});sys.exit(rc if not reason else 76)
import signal
signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import torch as T
T.set_num_threads(1);T.set_num_interop_threads(1);T.use_deterministic_algorithms(True)
assert not T.cuda.is_initialized();assert w.sha(w.PINS['net'][0])==w.PINS['net'][1]
Net=w.original_classes(T,w.PINS['net'][0]);T.manual_seed(42);base=Net().double().eval();X=T.zeros((2,171),dtype=T.float64);X[:,0]=T.tensor([2.,-3.],dtype=T.float64)
tree=ast.parse((R/'funding_cpu_parameter_controls.py').read_text());run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run');up=next(n for n in run.body if isinstance(n,ast.FunctionDef) and n.name=='update')
ns=dict(T=T,base=base,X=X,parts=w.parts,loss=w.loss,copy=copy);exec(compile(ast.Module(body=[up],type_ignores=[]),'frozen-update-AST','exec'),ns)
a,_=ns['update'](0.,0.);b,_=ns['update'](1.,0.)
diffs=[]
def compare(x,y,path):
 if isinstance(x,T.Tensor):
  xb=x.detach().contiguous().numpy().tobytes();yb=y.detach().contiguous().numpy().tobytes()
  if xb!=yb:
   mask=x.view(-1)!=y.view(-1);sz=(x.view(-1)==0)&(y.view(-1)==0)&(T.signbit(x.view(-1))!=T.signbit(y.view(-1)))
   diffs.append({'path':path,'shape':list(x.shape),'dtype':str(x.dtype),'sha0':hashlib.sha256(xb).hexdigest(),'sha1':hashlib.sha256(yb).hexdigest(),'numeric_differences':int(mask.sum()),'signed_zero_differences':int(sz.sum()),'max_abs_difference':float((x-y).abs().max()) if x.numel() else 0.})
 elif isinstance(x,dict):
  assert x.keys()==y.keys()
  for k in x:compare(x[k],y[k],path+'/'+str(k))
 elif isinstance(x,(list,tuple)):
  assert len(x)==len(y)
  for i,(u,v) in enumerate(zip(x,y)):compare(u,v,path+'/'+str(i))
 else:assert x==y,(path,x,y)
compare(a,b,'state');T.save({'A0':a,'A1':b},OUT/'EXACT_F0_STATES.pt')
result={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scope':'F0 byte locator only; original strict bitwise remains failed if any tensor differs','whole_hashes':[w.tree_hash(T,a),w.tree_hash(T,b)],'per_field':{k:[w.tree_hash(T,a[k]),w.tree_hash(T,b[k])] for k in a},'differences':diffs,'all_numeric_equal':w.tensor_tree_equal(T,a,b),'state_sha256':sha(OUT/'EXACT_F0_STATES.pt'),'cuda_initialized':T.cuda.is_initialized(),'source_sha256':sha(pathlib.Path(__file__))};g.write(OUT/'RESULT.json',result)

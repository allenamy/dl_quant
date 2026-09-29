"""One frozen conditional handoff cash pair; pooled fills, own inventory/stops."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import hashlib,io,json,signal,sys,time,traceback,zipfile,resource,shutil
from pathlib import Path
import numpy as np
from handoff_cash_contract import books,cash_metrics

BASE=Path('/dev/shm/recent_nc_cash_20260928');HAND=Path('/dev/shm/state_handoff_20260929');BR=Path('/dev/shm/executor_bridge_20260928_diagnostic_fixed_sources')
START=1790222400;SWITCH=1790236800;END=1790553600
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def save(p,r):Path(p).write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
def arrays(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def exact(a,b):
 if set(a)!=set(b) or any(a[k].dtype!=b[k].dtype or a[k].shape!=b[k].shape or a[k].tobytes()!=b[k].tobytes() for k in a):raise ValueError('control_arrays')
 return True
def main(root,contract):
 began=time.monotonic();root=Path(root);root.mkdir(exist_ok=False);C=json.loads(Path(contract).read_bytes())
 def timeout(*args):raise TimeoutError('budget_900_seconds')
 signal.signal(signal.SIGALRM,timeout);signal.alarm(900)
 resource.setrlimit(resource.RLIMIT_AS,(8<<30,8<<30))
 mem=int(Path('/sys/fs/cgroup/memory.max').read_text())-int(Path('/sys/fs/cgroup/memory.current').read_text());free=shutil.disk_usage('/dev/shm').free
 if mem<=10<<30 or free<=2<<30:raise RuntimeError('resource_refused')
 save(root/'START.json',{'utc':time.strftime('%FT%TZ',time.gmtime()),'pid':os.getpid(),'pgid':os.getpgid(0),'ticks':Path('/proc/self/stat').read_text().split()[21],'budget_seconds':900,'memory_available':mem,'shm_free':free,'address_space_cap_bytes':8<<30})
 pins=C['inputs']
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input_identity:'+p)
 for n,h in C['sources'].items():
  if sha(Path(__file__).parent/n)!=h:raise ValueError('source_identity:'+n)
 cfg=json.loads((BASE/'s42/CONFIG.json').read_text());engine=BASE/'engine';sys.path.insert(0,str(engine));import bt_driver_lib as DL
 checks=[]
 def check(name,ok,detail=None):
  checks.append({'name':name,'ok':bool(ok)})
  if not ok:raise ValueError('engine_gate:'+name)
 DL.verify_pins(cfg,check);ES,SL,BH,L2=DL.import_modules(cfg,str(engine));SL.install_readonly_guard()
 r=cfg['runs'][0];all_a=np.arange(DL.ts(cfg['window']['first_anchor']),DL.ts(cfg['window']['last_anchor'])+1,14400);sel=np.flatnonzero((all_a>=START)&(all_a<END))
 c=DL.load_context(cfg,ES,BH,L2,sel,[r],check,lambda *args:None);c.NAV0=100000.
 if c.GM!=2. or not np.array_equal(c.anchors,np.arange(START,END,14400)):raise ValueError('fixed_window_or_gross')
 hr=json.loads((HAND/'RESULT.json').read_text());hs=arrays(HAND/'STATES.npz')
 z=zipfile.ZipFile('/dev/shm/fetch_feature_alignment_20260928_inputs/PRODUCTION_INPUTS.zip');sy=json.loads(z.read('shadow_bundle/config.json'))['symbols_panel'];initial={}
 if sy!=c.SY:raise ValueError('axis')
 for k in ('kc','fc'):
  with np.load(io.BytesIO(z.read(f'fea171/state_H_{k}_{START}.npz')),allow_pickle=False) as f:
   if int(f['anchor'])!=START:raise ValueError('initial_clock')
   v=np.zeros(len(sy));v[f['idx'].astype(int)]=f['val'];initial[k]=v
 paired=books(hr['rows'],hs,initial,c.anchors)
 def run(label,seed,cell,book=None):
  rr=dict(r,cost_cell=cell);td=root/f'tmp_{label}';S=DL.make_sim(c,rr,seed,str(td),book=book);pre={};original=S._boundary
  def boundary(t,k):
   original(t,k)
   if int(t)==SWITCH:
    # Event queue and all inventory/risk state at the common seam.
    obj={key:getattr(S,key) for key in ('q','entry','pns','K','day_ref','last_eval','halt_until','rebal_gen','ev','seq','seed')}
    raw=BH.canon(obj);pre.update(sha256=hashlib.sha256(raw.encode()).hexdigest(),n_positions=len(S.q),equity=S.equity(int(t)))
  S._boundary=boundary;W=S.run();arr=DL.path_arrays(c,S,W);au=DL.path_summary(c,S,arr,rr,seed,time.monotonic()-began)['audits']
  if not DL.audits_clean(au) or not pre:raise ValueError('cash_or_seam_audit')
  shutil.rmtree(td)
  return arr,au,pre
 # Interface control before substituting any state or execution bridge.
 old,old_audit,_=run('control_default',0,None);echo,echo_audit,_=run('control_explicit',0,None,book=c.BOOKS[(r['arm'],r['book'])]);exact(old,echo)
 save(root/'CONTROL.json',{'status':'ALL_FIELDS_EXACT','fields':len(old),'anchors':len(old['A']),'audits':old_audit})
 sys.path.insert(0,str(BR));import executor_bridge as EB
 manifest=EB.verified_sources(BR)
 if sha(c.X.LG.__file__)!=manifest['current_legs.py.txt']['parent_sha256']:raise ValueError('bridge_legs_identity')
 EB.install_pure(c.X,BR)
 paths={};results={};common=[]
 for cell in (None,'fee_x1.25','slip_x1.5','fill_x0.9'):
  tag=cell or 'base';results[tag]=[]
  for seed in range(32):
   pair={};meta={};saved={}
   for arm in ('B','S'):
    label=f'{tag}_{arm}_{seed:02d}';arr,au,pre=run(label,seed,cell,book=paired[arm]);pair[arm]=arr;meta[arm]={'audits':au,'pre':pre}
    p=root/(label+'.npz');np.savez_compressed(p,**arr);paths[label]={'path':str(p),'sha256':sha(p)}
   if meta['B']['pre']!=meta['S']['pre']:raise ValueError('initial_inventory_not_equal')
   # Common first window economics and sampled NAV are also exactly identical.
   for k in ('nav0','nav1','fee','funding','price_trade','turnover'):
    if pair['B'][k][0].tobytes()!=pair['S'][k][0].tobytes():raise ValueError('common_window_not_equal')
   if pair['B']['nav5_main'][:49].tobytes()!=pair['S']['nav5_main'][:49].tobytes():raise ValueError('common_5m_not_equal')
   out={'execution_seed':seed,'common_initial_state':meta['B']['pre'],'arms':{arm:cash_metrics(p,SWITCH,END) for arm,p in pair.items()},'first_switch_window':{arm:cash_metrics(p,SWITCH,SWITCH+14400) for arm,p in pair.items()},'audits':{arm:meta[arm]['audits'] for arm in meta}}
   results[tag].append(out)
  print('CELL_DONE',tag,len(results[tag]),round(time.monotonic()-began,2),flush=True)
 summary={}
 for tag,rr in results.items():
  summary[tag]={}
  for key in ('compound','maxdd_5m','price_trade','funding','fee','turnover','halt_anchors','hold_anchors','n_stop_events','n_flatten_events','unk_held','unk_notional'):
   b=np.array([x['arms']['B'][key] for x in rr]);s=np.array([x['arms']['S'][key] for x in rr]);d=s-b
   summary[tag][key]={'B_mean':float(b.mean()),'S_mean':float(s.mean()),'paired_delta_mean':float(d.mean()),'paired_delta_min':float(d.min()),'paired_delta_max':float(d.max())}
  summary[tag]['priced_complete']=all(x['arms'][a]['priced_complete'] for x in rr for a in ('B','S'))
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('input_drift:'+p)
 for n,h in C['sources'].items():
  if sha(Path(__file__).parent/n)!=h:raise ValueError('source_drift:'+n)
 out={'utc':time.strftime('%FT%TZ',time.gmtime()),'status':'CONDITIONAL_HANDOFF_CASH_COMPLETE_NOT_LIVE_OR_RELEASE','contract_sha256':sha(contract),'inputs':pins,'sources':C['sources'],'controls':{'interface_exact':True,'common_seams':128,'gates':checks},'window':{'common_setup_start':START,'comparison_start':SWITCH,'end_exclusive':END},'paths':paths,'results':results,'summary':summary,'python':sys.executable,'numpy':np.__version__,'seconds':time.monotonic()-began,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':C['limits']}
 save(root/'RESULT.json',out);save(root/'TERMINAL.json',{'rc':0,'result_sha256':sha(root/'RESULT.json')});print(out['status'],flush=True)
if __name__=='__main__':
 try:main(*sys.argv[1:])
 except BaseException as e:
  p=Path(sys.argv[1]);p.mkdir(exist_ok=True);save(p/'TERMINAL.json',{'rc':1,'utc':time.strftime('%FT%TZ',time.gmtime()),'error':repr(e),'traceback':traceback.format_exc()});raise

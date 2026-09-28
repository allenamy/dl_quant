"""Owned GPU liquidity-population continuation -> two serial full combo cells -> matched U/NC readout."""
import os,sys,json,hashlib,pathlib,subprocess,time,signal,traceback,zipfile
H=pathlib.Path(__file__).resolve().parent;C=json.loads((H/'CONTRACT.json').read_text());R=pathlib.Path(C['root'])
PY='/workspace/venv/bin/python';ENV={'PATH':'/usr/bin:/bin','HOME':'/root'};CH=[];STEPS=[];START=time.monotonic()
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def write(p,x):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,'x') as f:json.dump(x,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
def stop_own():
 for p,f,*_ in CH:
  if p.poll() is None:
   if os.getpgid(p.pid)!=p.pid:raise RuntimeError('own PGID mismatch')
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
  f.close()
def launch(label,args):
 f=open(R/'logs'/f'{label}.log','x');p=subprocess.Popen(args,cwd=H,env=ENV,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 item=(p,f,label,time.monotonic());CH.append(item)
 write('processes/'+label+'.json',{'pid':p.pid,'pgid':os.getpgid(p.pid),'start_ticks':pathlib.Path(f'/proc/{p.pid}/stat').read_text().split()[21],'argv':args,'utc':time.strftime('%FT%TZ',time.gmtime())})
 return item

def resource():
 maximum=int(pathlib.Path('/sys/fs/cgroup/memory.max').read_text());current=int(pathlib.Path('/sys/fs/cgroup/memory.current').read_text())
 rss=0
 for p in pathlib.Path('/proc').glob('[0-9]*/status'):
  try:
   d=dict(x.split(':',1) for x in p.read_text().splitlines() if ':' in x)
   if int(d['Uid'].split()[0])==os.getuid():rss+=int(d.get('VmRSS','0 kB').split()[0])*1024
  except (OSError,KeyError,ProcessLookupError):continue
 return {'cgroup_headroom':maximum-current,'uid_rss':rss}

def wait(group,training=False):
 peak=0;observations=0
 while any(p.poll() is None for p,*_ in group):
  if time.time()> (C['training_deadline_epoch'] if training else C['deadline_epoch']):raise TimeoutError('frozen budget exhausted')
  if any(p.poll() not in (None,0) for p,*_ in group):raise RuntimeError('child failed')
  m=resource();peak=max(peak,m['uid_rss']);observations+=1
  if m['cgroup_headroom']<8*2**30 or m['uid_rss']>30*2**30:raise MemoryError('shared resource limit')
  if training:
   for p,*_ in group:
    if p.poll() is None:
     st=dict(x.split(':',1) for x in pathlib.Path(f'/proc/{p.pid}/status').read_text().splitlines() if ':' in x)
     if int(st.get('VmRSS','0 kB').split()[0])*1024>10*2**30:raise MemoryError('training RSS limit')
   gpu=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True,timeout=10)
   if max(int(x) for x in gpu.split())>12*1024:raise MemoryError('training GPU total limit')
  time.sleep(5)
 for p,f,label,t in group:
  f.flush();s={'label':label,'rc':p.returncode,'wall_seconds':time.monotonic()-t,'log_sha256':sha(R/'logs'/f'{label}.log'),'peak_total_uid_rss_bytes':peak,'resource_checks':observations};STEPS.append(s);write('steps/'+label+'.json',s)
  if p.returncode:raise RuntimeError(label+' failed')

def verify_uniform():
 p=pathlib.Path('/dev/shm/f10_recent_adapt_20260928_finish/receipts/ECONOMIC_FULL_BOOK.json')
 if sha(p)!='2b64ec6521c2951cb7061a2ccf67d5e1e7ed7bebd82c0506cfa87e411effcad8':raise ValueError('uniform economic receipt')
 eco=json.loads(p.read_text());out={str(p):sha(p)}
 for seed in (42,2027):
  root=pathlib.Path(f'/dev/shm/f10_recent_adapt_20260928_attempt2');tag=f'ADAPT_U_s{seed}X_scaled_rule_raw_UAFE'
  for f in eco['results'][f'U_s{seed}_vs_NC']['candidate_paths']:
   path=root/f'cells/U_s{seed}/runs/{tag}/PATH_{tag}_seed_{f["seed"]:02d}.npz'
   if sha(path)!=f['npz_sha256']:raise ValueError('U cash drift')
   out[str(path)]=sha(path)
  rp=root/f'models/U_s{seed}/TRAIN_RECEIPT.json';rec=json.loads(rp.read_text());out[str(rp)]=sha(rp)
  for path,h in rec['fold_artifacts'].items():
   if sha(path)!=h:raise ValueError('U training drift')
   out[path]=h
 return out

def main():
 if not __debug__:raise RuntimeError('optimized mode refused')
 R.mkdir(exist_ok=False)
 for n in ('logs','receipts','processes','steps','models','cells'):(R/n).mkdir()
 for n,h in C['copied_sources'].items():assert sha(H/n)==h,('source drift',n)
 assert sha(__file__)==C['runner_sha256']
 parent=pathlib.Path(C['parent_root'])
 for n,h in C['parent_receipts'].items():assert sha(parent/n)==h,('control receipt drift',n)
 assert json.loads((parent/'TERMINAL.json').read_text())['rc']==0
 from control_binding import verify_controls
 ext=verify_controls(parent)
 for seed in (42,2027):
  d=json.loads((parent/f'receipts/PAIRED_s{seed}.json').read_text())
  for f in d['ref']['facts']:
   p=pathlib.Path(d['ref']['dir'])/f"PATH_{d['ref']['tag']}_seed_{f['seed']:02d}.npz"
   assert sha(p)==f['npz_sha256'],str(p)
 uniform_before=verify_uniform()
 for seed in (42,2027):
  (R/f'cells/U_s{seed}').symlink_to(f'/dev/shm/f10_recent_adapt_20260928_attempt2/cells/U_s{seed}',target_is_directory=True)
  (R/f'models/U_s{seed}').symlink_to(f'/dev/shm/f10_recent_adapt_20260928_attempt2/models/U_s{seed}',target_is_directory=True)
 write('UNIFORM_CONTROL_IDENTITIES.json',uniform_before)
 write('ENGINE_IDENTITIES.json',json.loads((parent/'ENGINE_IDENTITIES.json').read_text()))
 gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],text=True,timeout=15).strip()
 assert not gpu,('GPU already owned',gpu)
 m=resource();assert m['cgroup_headroom']>=18*2**30 and m['uid_rss']+10*2**30<=30*2**30
 assert os.statvfs('/dev/shm').f_bavail*os.statvfs('/dev/shm').f_frsize>=8*2**30
 write('PREFLIGHT.json',{'utc':time.strftime('%FT%TZ',time.gmtime()),'contract_sha256':sha(H/'CONTRACT.json'),'controls':ext,'resources':m,'gpu_processes':gpu,'python':sys.executable,'env':ENV})
 wait([launch('unit_controls',[PY,'-B','-m','unittest','discover','-s',str(H),'-p','test_*.py','-v'])])
 wait([launch('train_adapt',[PY,'-B',str(H/'train_adapt.py')])],True)
 wait([launch('score_diagnostics',[PY,'-B',str(H/'score_diagnostics.py')])])
 for kind in ('LQ',):
  for seed in (42,2027):
   args=[PY,'-B',str(H/'alloc_chain_run.py'),'PATH,HOME,LC_CTYPE',str(R/'receipts'),'--seed',str(seed),'--rule','inservice','--mix','shared','--kind',kind,'--engine']
   wait([launch(f'{kind}_{seed}',args)])
 write('SIMULATION_TERMINAL.json',{'rc':0,'status':'SIMULATIONS_AUDITED','steps':STEPS,'utc':time.strftime('%FT%TZ',time.gmtime())})
 wait([launch('economic',[PY,'-B',str(H/'economic_readout.py'),'--root',str(R),'--out',str(R/'receipts/ECONOMIC_FULL_BOOK.json')])])
 from decision import decide
 write('receipts/BOOK_DECISION.json',decide(json.loads((R/'receipts/ECONOMIC_FULL_BOOK.json').read_text())))
 assert ext==verify_controls(parent)
 assert uniform_before==verify_uniform(),'uniform control changed'
 for n,h in C['copied_sources'].items():assert sha(H/n)==h,('end source drift',n)
 if time.time()>C['deadline_epoch']:raise TimeoutError('total budget')
if __name__=='__main__':
 rc=1;error=None
 try:main();rc=0
 except BaseException as e:error=repr(e);traceback.print_exc()
 finally:
  stop_own()
  if R.exists():write('TERMINAL.json',{'rc':rc,'status':'EXPLORATORY_COMPARISON_COMPLETE_NOT_RELEASE' if rc==0 else 'FAILED','error':error,'utc':time.strftime('%FT%TZ',time.gmtime()),'wall_seconds':time.monotonic()-START,'steps':STEPS,'production_changes':0,'GPU_training_requested':True,'completed_neural_fold_outputs':len(list((R/'models').glob('LQ_s*/*/FOLD_RECEIPT.json')))})
 sys.exit(rc)

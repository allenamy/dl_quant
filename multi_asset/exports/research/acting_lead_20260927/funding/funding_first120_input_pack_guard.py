"""One input-only materialization; no network or optimizer calls."""
import hashlib,json,os,pathlib,signal,subprocess,sys,time
G=2**30;DECLARED=2*G;SOFT=7*G//4;SPARE=8*G;WALL=300
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT.parent/'first120_input_pack_20260927'
RUNTIME='/workspace/venv/bin/python'


def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def write(p,v):
 with open(p,'x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())


def memory(pid):
 try:rows=pathlib.Path(f'/proc/{pid}/status').read_text().splitlines()
 except FileNotFoundError:return 0
 return max([int(x.split()[1])*1024 for x in rows if x.startswith(('VmRSS:','VmHWM:'))] or [0])


def public_free():return int(pathlib.Path('/sys/fs/cgroup/memory.max').read_text())-int(pathlib.Path('/sys/fs/cgroup/memory.current').read_text())


def terminate(p):
 if p.poll() is not None:return
 if os.getpgid(p.pid)!=p.pid:raise RuntimeError('private group identity changed')
 os.killpg(p.pid,signal.SIGTERM)
 try:p.wait(1)
 except subprocess.TimeoutExpired:
  if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
  p.wait(1)


def main():
 OUT.mkdir(exist_ok=False);t0=time.monotonic();p=None;reason=None;peak=0;gap=0.;last=t0;rc=None
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 def interrupted(sig,frame):raise InterruptedError(str(sig))
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 try:
  contract=json.loads((ROOT/'PACK_CONTRACT.json').read_text())
  for name,h in contract['source_sha256'].items():assert sha(ROOT/name)==h,(name,'identity')
  assert contract['rss_budget_bytes']==DECLARED and contract['software_stop_bytes']==SOFT and contract['wall_seconds']==WALL
  rss=sum(map(int,subprocess.check_output(['ps','-u',str(os.getuid()),'-o','rss='],text=True,timeout=2).split()))*1024
  s={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'guard_pid':os.getpid(),'free_bytes':public_free(),'same_uid_rss_bytes':rss,'declared_rss_bytes':DECLARED,'software_stop_bytes':SOFT,'spare_bytes':SPARE}
  s['pass']=s['free_bytes']>=DECLARED+SPARE and rss+DECLARED<=30*G;write(OUT/'PREFLIGHT.json',s)
  if not s['pass']:reason='RESOURCE_REFUSED';return 75
  probe=OUT/'owned_quota_probe'
  with open(probe,'xb') as f:f.write(bytes(65536));f.flush();os.fsync(f.fileno())
  assert probe.stat().st_size==65536;probe.unlink()
  cmd=[RUNTIME,'-B',str(ROOT/'funding_first120_input_pack.py'),str(OUT)]
  write(OUT/'COMMAND.json',{'argv':cmd,'deadline_monotonic':t0+WALL,'contract_sha256':sha(ROOT/'PACK_CONTRACT.json'),'source_sha256':contract['source_sha256'],'quota_probe_bytes':65536})
  with open(OUT/'stdout.log','x') as stdout,open(OUT/'stderr.log','x') as stderr:
   env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
   p=subprocess.Popen(cmd,env=env,start_new_session=True,cwd=ROOT,stdout=stdout,stderr=stderr)
   assert os.getpgid(p.pid)==p.pid
   write(OUT/'PID.json',{'guard_pid':os.getpid(),'worker_pid':p.pid,'worker_pgid':p.pid})
   while p.poll() is None:
    now=time.monotonic();gap=max(gap,now-last);last=now;peak=max(peak,memory(p.pid)+memory(os.getpid()))
    if peak>SOFT:reason='SOFT_RSS_STOP'
    elif now-t0>=WALL:reason='WALL_STOP'
    elif public_free()<SPARE:reason='PUBLIC_HEADROOM_STOP'
    if reason:terminate(p);break
    time.sleep(.05)
   rc=p.wait(1)
  if not reason:reason='COMPLETED' if rc==0 else 'WORKER_FAILED'
  return 0 if reason=='COMPLETED' else 76
 except BaseException as e:reason='GUARD_EXCEPTION:'+repr(e);return 76
 finally:
  if p is not None:terminate(p);rc=p.returncode
  write(OUT/'TERMINAL.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':reason,'returncode':rc,'pid':None if p is None else p.pid,'guard_source_sha256':sha(__file__),'wall_seconds':time.monotonic()-t0,'peak_own_rss_hwm_sum_bytes':peak,'max_monitor_gap_seconds':gap,'poll_seconds':.05,'rss_budget_bytes':DECLARED,'software_stop_bytes':SOFT,'wall_limit_seconds':WALL,'no_reschedule':True,'not_a_hard_memory_cap':True,'scope':'INPUT_PACK_ONLY_NO_FORWARD_NO_OPTIMIZER'})


if __name__=='__main__':sys.exit(main())

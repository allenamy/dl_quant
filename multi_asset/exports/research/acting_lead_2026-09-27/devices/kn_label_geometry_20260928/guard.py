"""One CPU metadata-only job; no retries or shared process intervention."""
import os,sys,pathlib,subprocess,time,json,signal,hashlib
ROOT=pathlib.Path(__file__).resolve().parent
OUT=pathlib.Path('/dev/shm/kn_label_geometry_20260928')
MEM=pathlib.Path('/sys/fs/cgroup');G=2**30

def put(name,d):
 with open(OUT/name,'x') as f:json.dump(d,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
def free():return int((MEM/'memory.max').read_text())-int((MEM/'memory.current').read_text())
def rss(pid):
 try:ls=pathlib.Path(f'/proc/{pid}/status').read_text().splitlines()
 except FileNotFoundError:return 0
 return max([int(l.split()[1])*1024 for l in ls if l.startswith(('VmRSS:','VmHWM:'))] or [0])
def stop(p):
 if p is None or p.poll() is not None:return
 if os.getpgid(p.pid)!=p.pid:raise RuntimeError('own PGID identity differs')
 os.killpg(p.pid,signal.SIGTERM)
 try:p.wait(timeout=1)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=1)
def main():
 start=time.monotonic();OUT.mkdir(exist_ok=False);p=None;why='NOT_STARTED';rc=None;peak=0
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 try:
  c=json.loads((ROOT/'CONTRACT.json').read_text())
  if c['wall_seconds']!=300 or c['rss_budget_bytes']!=2*G or c['output']!=str(OUT):raise ValueError('contract budget/path drift')
  for n,h in c['source_sha256'].items():
   if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise ValueError('source drift:'+n)
  uid=sum(map(int,subprocess.check_output(['ps','-u',str(os.getuid()),'-o','rss='],text=True,timeout=2).split()))*1024
  spare=free();put('PREFLIGHT.json',{'free_bytes':spare,'uid_rss':uid,'time':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'guard_pid':os.getpid()})
  if spare<10*G or uid+2*G>30*G:why='RESOURCE_REFUSED';return 75
  with open(OUT/'stdout.log','x') as out,open(OUT/'stderr.log','x') as err:
   env=dict(os.environ)
   for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[k]='1'
   cmd=['/workspace/venv/bin/python','-B',str(ROOT/'probe.py'),str(OUT)]
   put('COMMAND.json',{'argv':cmd,'source_sha256':c['source_sha256'],'contract_sha256':hashlib.sha256((ROOT/'CONTRACT.json').read_bytes()).hexdigest(),'GPU':False,'optimizer':False})
   subprocess.run([cmd[0],'-m','unittest','test_probe.py'],env=env,cwd=ROOT,stdout=out,stderr=err,check=True,timeout=15)
   p=subprocess.Popen(cmd,env=env,cwd=ROOT,stdout=out,stderr=err,start_new_session=True)
   put('PID.json',{'pid':p.pid,'pgid':os.getpgid(p.pid)})
   while p.poll() is None:
    peak=max(peak,rss(p.pid)+rss(os.getpid()))
    if peak>2*G:why='RSS_STOP';break
    if free()<8*G:why='PUBLIC_HEADROOM_STOP';break
    if time.monotonic()-start>300:why='WALL_STOP';break
    time.sleep(.1)
   stop(p);rc=p.wait(1)
  if rc==0 and why=='NOT_STARTED':
   r=json.loads((OUT/'RESULT.json').read_text());peak=max(peak,r['rss_peak_bytes']+rss(os.getpid()))
   if r['optimizer_updates']!=0 or r['features_body_loaded'] or r['gpu_imported']:raise ValueError('scope drift')
   why='DIAGNOSTIC_COMPLETED' if peak<=2*G else 'RSS_STOP'
  elif why=='NOT_STARTED':why='WORKER_FAILED'
  return 0 if why=='DIAGNOSTIC_COMPLETED' else 76
 except BaseException as e:why='EXCEPTION:'+repr(e);return 76
 finally:
  stop(p);put('TERMINAL.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':why,'rc':rc,'wall_seconds':time.monotonic()-start,'peak_own_rss_bytes':peak,'CPU':1,'GPU':False,'virtual_address_limit_worker_bytes':2*G,'rss_budget_bytes':2*G,'public_spare':8*G,'no_reschedule':True})
if __name__=='__main__':raise SystemExit(main())

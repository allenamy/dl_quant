#!/usr/bin/env python3
"""Own-PGID resource gate/watchdog; refuses occupied or undersized Pod."""
import os,pathlib,time,json,subprocess,signal,sys
R=pathlib.Path(__file__).resolve().parent;G=2**30
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
def snapshot():
 maxmem=int(pathlib.Path('/sys/fs/cgroup/memory.max').read_text());current=int(pathlib.Path('/sys/fs/cgroup/memory.current').read_text())
 rows=subprocess.check_output(['ps','-u',str(os.getuid()),'-o','rss='],text=True).split();rss=sum(int(x) for x in rows)*1024
 gpu=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip().split(',');used,util=map(lambda x:int(x.strip()),gpu)
 return {'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'memory_max':maxmem,'memory_current':current,'free_bytes':maxmem-current,'same_uid_rss_bytes':rss,'gpu_used_MiB':used,'gpu_util':util,'pass':maxmem-current>=14*G and rss+6*G<=30*G and used<=64 and util==0}
s=snapshot();(R/('RESOURCE_GATE_'+s['utc'].replace(':','')+'.json')).write_text(json.dumps(s,indent=2));(R/'RESOURCE_GATE.json').write_text(json.dumps(s,indent=2));print(json.dumps(s),flush=True)
if not s['pass']:sys.exit(75)
# Actual output filesystem quota, not df. Sole disposable file belongs to this task.
probe=R/'quota_probe.bin'
with open(probe,'wb') as f:
 for _ in range(16):f.write(b'\0'*(1<<20))
 f.flush();os.fsync(f.fileno())
assert probe.stat().st_size==16<<20;probe.unlink()
s['quota_probe_bytes']=16<<20;s['quota_probe_pass']=True
(R/'RESOURCE_GATE.json').write_text(json.dumps(s,indent=2))
bp=R/'BUDGET.json'
if bp.exists():budget=json.loads(bp.read_text())
else:
 budget={'first_start_unix':time.time(),'deadline_unix':time.time()+900};bp.write_text(json.dumps(budget,indent=2))
assert time.time()<budget['deadline_unix'],'original 15-minute budget exhausted'
t0=time.monotonic()
with open(R/'stdout.log','w') as out,open(R/'stderr.log','w') as err:
 p=subprocess.Popen([sys.executable,'-B',str(R/'funding_network_fixture.py')],stdout=out,stderr=err,start_new_session=True,cwd=R)
 reason=None;peakrss=0;peakgpu=0
 while p.poll() is None:
  time.sleep(1)
  try:
   rss=sum(int(line.split()[1]) for line in pathlib.Path(f'/proc/{p.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))*1024
  except FileNotFoundError:rss=0
  peakrss=max(peakrss,rss)
  grow=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],text=True).splitlines()
  gpumem=sum(int(line.split(',')[1].strip()) for line in grow if line.split(',')[0].strip()==str(p.pid))*2**20;peakgpu=max(peakgpu,gpumem)
  if rss>6*G:reason='RSS_LIMIT'
  elif gpumem>8*G:reason='GPU_LIMIT'
  elif time.time()>budget['deadline_unix']:reason='WALL_LIMIT'
  if reason:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   break
 rc=p.wait()
receipt={'gate':s,'pid':p.pid,'returncode':rc,'stop_reason':reason,'wall_seconds':time.monotonic()-t0,'peak_rss_observed_bytes':peakrss,'peak_gpu_process_bytes':peakgpu,'utc_end':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
(R/'GUARD_RESULT.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt));sys.exit(rc if not reason else 76)

"""Single separately reviewed first120 network instrument; default does not run."""
import argparse,hashlib,json,os,pathlib,signal,subprocess,sys,time
G=2**30;DECLARED_RSS=6*G;SOFT_STOP=11*G//2;PUBLIC_SPARE=8*G;UID_LIMIT=30*G;GPU_BUDGET=8*G;WALL_SECONDS=300
RUNTIME='/workspace/venv/bin/python'
ROOT=pathlib.Path(__file__).resolve().parent
OUTPUT=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding/normalized_network_fd_20260928')
MEMORY=pathlib.Path('/sys/fs/cgroup')

def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def verify_worker_output():
    # Called only after contract source hashes pass; this pinned worker imports stdlib only.
    import importlib.util
    path=(ROOT/'funding_first120_forward.py').resolve()
    spec=importlib.util.spec_from_file_location('funding_worker_output_preflight',path)
    worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    if pathlib.Path(worker.__file__).resolve()!=path:raise ValueError('worker import mismatch')
    if worker.OUTPUT!=OUTPUT:raise ValueError('guard/worker output mismatch')
    return str(path)

def write(path,value):
    with open(path,'x') as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())

def proc_memory(pid):
    try:lines=pathlib.Path(f'/proc/{pid}/status').read_text().splitlines()
    except FileNotFoundError:return 0,0
    d={v.split(':',1)[0]:int(v.split()[1])*1024 for v in lines if v.startswith(('VmRSS:','VmHWM:'))}
    return d.get('VmRSS',0),d.get('VmHWM',0)

def run_query(args):return subprocess.check_output(args,text=True,timeout=1.0)

def gpu_rows():
    return run_query(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'])

def owned_gpu_bytes(raw,pid):
    total=0
    for line in raw.splitlines():
        if not line.strip():continue
        a,b=line.split(',')
        p=int(a.strip());n=int(b.strip())
        if p==pid:total+=n*2**20
    return total

def snapshot():
    mm=int((MEMORY/'memory.max').read_text());mc=int((MEMORY/'memory.current').read_text())
    rss=sum(map(int,run_query(['ps','-u',str(os.getuid()),'-o','rss=']).split()))*1024
    lines=run_query(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits']).strip().splitlines()
    if len(lines)!=1:raise ValueError('requires exactly one known GPU')
    used,util=(int(x.strip()) for x in lines[0].split(','))
    rows=gpu_rows();pids=[]
    for row in rows.splitlines():
        if row.strip():
            a,b=row.split(',');pids.append(int(a));int(b)
    return {'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'memory_max':mm,'memory_current':mc,
            'free_bytes':mm-mc,'uid_rss_bytes':rss,'gpu_used_mib':used,'gpu_util':util,'compute_pids':pids}

def gate_reasons(s):
    reasons=[]
    if s['free_bytes']<DECLARED_RSS+PUBLIC_SPARE:reasons.append('HEADROOM')
    if s['uid_rss_bytes']+DECLARED_RSS>UID_LIMIT:reasons.append('UID_RSS')
    if s['gpu_used_mib']>64 or s['gpu_util']!=0 or s['compute_pids']:reasons.append('GPU_OCCUPIED')
    return reasons

def stop_reason(rss,gpu,elapsed,public_free):
    if rss>SOFT_STOP:return 'SOFT_RSS_STOP'
    if gpu>GPU_BUDGET:return 'GPU_STOP'
    if elapsed>=WALL_SECONDS:return 'WALL_STOP'
    if public_free<PUBLIC_SPARE:return 'PUBLIC_HEADROOM_STOP'
    return None

def terminate_owned(p):
    if p.poll() is not None:return
    if os.getpgid(p.pid)!=p.pid:raise RuntimeError('owned process group identity changed')
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=1)
    except subprocess.TimeoutExpired:
        if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
        p.wait(timeout=1)

def run_guard():
    t0=time.monotonic();OUTPUT.mkdir(exist_ok=False);p=None;rc=None;reason=None;peakrss=peakgpu=0;gap=0.;last=t0
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    def interrupted(sig,frame):raise InterruptedError(str(sig))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        contract=json.loads((ROOT/'FORWARD_CONTRACT.json').read_text())
        if contract['status']!='REVIEW_READY_RUN_NOT_STARTED':raise ValueError('contract scope')
        if contract['rss_budget_bytes']!=DECLARED_RSS or contract['wall_seconds']!=WALL_SECONDS:raise ValueError('budget changed')
        for n,h in contract['source_sha256'].items():
            if sha(ROOT/n)!=h:raise ValueError('source drift:'+n)
        verify_worker_output()
        s=snapshot();s['guard_pid']=os.getpid();s['reasons']=gate_reasons(s);write(OUTPUT/'PREFLIGHT.json',s)
        if s['reasons']:reason='RESOURCE_REFUSED';return 75
        probe=OUTPUT/'owned_quota_probe.bin'
        with open(probe,'xb') as f:f.write(bytes(65536));f.flush();os.fsync(f.fileno())
        if probe.stat().st_size!=65536:raise ValueError('quota probe')
        probe.unlink()
        cmd=[RUNTIME,'-B',str(ROOT/'funding_first120_forward.py'),'--worker',str(OUTPUT)]
        write(OUTPUT/'COMMAND.json',{'argv':cmd,'deadline_monotonic':t0+WALL_SECONDS,'source_sha256':contract['source_sha256'],'contract_sha256':sha(ROOT/'FORWARD_CONTRACT.json'),'optimizer_updates_allowed':0,'quota_probe_bytes':65536})
        with open(OUTPUT/'stdout.log','x') as stdout,open(OUTPUT/'stderr.log','x') as stderr:
            p=subprocess.Popen(cmd,start_new_session=True,cwd=ROOT,stdout=stdout,stderr=stderr)
            if os.getpgid(p.pid)!=p.pid:raise ValueError('private PGID absent')
            write(OUTPUT/'PID.json',{'guard_pid':os.getpid(),'worker_pid':p.pid,'worker_pgid':p.pid})
            next_gpu=0.
            while p.poll() is None:
                now=time.monotonic();gap=max(gap,now-last);last=now
                ar,ah=proc_memory(p.pid);br,bh=proc_memory(os.getpid());peakrss=max(peakrss,ar+br,ah+bh)
                if now>=next_gpu:
                    rows=gpu_rows();peakgpu=max(peakgpu,owned_gpu_bytes(rows,p.pid));next_gpu=now+.5
                    if any(int(x.split(',')[0])!=p.pid for x in rows.splitlines() if x.strip()):reason='OTHER_GPU_WORK_STARTED';break
                free=int((MEMORY/'memory.max').read_text())-int((MEMORY/'memory.current').read_text())
                reason=stop_reason(peakrss,peakgpu,now-t0,free)
                if reason:break
                time.sleep(.05)
            if reason:terminate_owned(p)
            rc=p.wait(1)
        if rc==0 and reason is None:
            r=json.loads((OUTPUT/'WORKER_RESULT.json').read_text())
            if r['optimizer_updates']!=0 or r['parameter_hash_before']!=r['parameter_hash_after']:raise ValueError('parameter identity changed')
            m=json.loads((OUTPUT/'WORKER_MEMORY.json').read_text());peakrss=max(peakrss,m['rss_high_water_bytes']+proc_memory(os.getpid())[1]);peakgpu=max(peakgpu,m['max_cuda_reserved_bytes'])
            reason=stop_reason(peakrss,peakgpu,time.monotonic()-t0,PUBLIC_SPARE) or 'FORWARD_MEASUREMENT_COMPLETED'
        elif reason is None:reason='WORKER_FAILED'
        return 0 if reason=='FORWARD_MEASUREMENT_COMPLETED' else 76
    except BaseException as e:reason='GUARD_EXCEPTION:'+repr(e);return 76
    finally:
        if p is not None:terminate_owned(p);rc=p.returncode
        write(OUTPUT/'TERMINAL.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':reason,'returncode':rc,'worker_pid':None if p is None else p.pid,'wall_seconds':time.monotonic()-t0,'peak_own_rss_hwm_sum_bytes':peakrss,'peak_gpu_observed_bytes':peakgpu,'max_monitor_gap_seconds':gap,'rss_poll_seconds':.05,'gpu_poll_seconds':.5,'query_timeout_seconds':1.,'rss_budget_bytes':DECLARED_RSS,'software_stop_bytes':SOFT_STOP,'public_spare_bytes':PUBLIC_SPARE,'gpu_budget_bytes':GPU_BUDGET,'not_a_hard_memory_cap':True,'no_reschedule':True,'optimizer_updates_allowed':0,'source_sha256':sha(__file__)})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');a=ap.parse_args()
    if a.run:raise SystemExit(run_guard())
    print(json.dumps({'status':'RUN_NOT_STARTED','rss_budget_bytes':DECLARED_RSS,'software_stop_bytes':SOFT_STOP,'public_spare_bytes':PUBLIC_SPARE,'gpu_budget_bytes':GPU_BUDGET,'wall_seconds':WALL_SECONDS,'output':str(OUTPUT),'scope':'await root review; no optimizer'}))
if __name__=='__main__':main()

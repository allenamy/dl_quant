#!/usr/bin/env python3
"""Standalone synthetic CUDA observation. No data, model files, optimizer, or simulation.

Software monitoring is not a Linux memory limit. Importing this module is inert.
The default CLI only prints the proposal; --run requires separate root authorization.
"""
import argparse
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

G=2**30
SHAPE=(120,829,171)
DECLARED_RSS=3*G
SOFT_STOP=5*G//2
PUBLIC_SPARE=8*G
UID_LIMIT=30*G
GPU_BUDGET=8*G
WALL_SECONDS=60
RUNTIME='/workspace/venv/bin/python'
OUTPUT=pathlib.Path('/workspace/codex_research/QNT-2026-0907/acting_lead_20260927/funding/cuda_shape_probe_20260927')
MEMORY=pathlib.Path('/sys/fs/cgroup')


def input_bytes():return SHAPE[0]*SHAPE[1]*SHAPE[2]*4


def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


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


def worker(out):
    # The only numerical inputs are fixed synthetic zeros and scalar constants.
    deadline=json.loads((out/'COMMAND.json').read_text())['deadline_monotonic']
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[key]='1'
    os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    import torch
    from torch import nn
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True);torch.manual_seed(42)
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
    prop=torch.cuda.get_device_properties(0)
    # Allocator cap leaves 1GiB for runtime outside the allocator; not a total GPU guarantee.
    torch.cuda.set_per_process_memory_fraction(7*G/prop.total_memory,0)
    model=nn.Module()
    model.f=nn.Sequential(nn.Linear(171,256),nn.GELU(),nn.Dropout(.1),nn.Linear(256,256),nn.GELU(),nn.Dropout(.1),nn.Linear(256,1))
    model.a=nn.Parameter(torch.tensor(-2.303))
    assert sum(p.numel() for p in model.parameters())==110082
    model=model.to('cuda').train()
    before={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
    x=torch.zeros(SHAPE,device='cuda',dtype=torch.float32)
    y=model.f(x).squeeze(-1)
    objective=y.square().mean()+model.a*0
    objective.backward();torch.cuda.synchronize()
    assert all(torch.isfinite(p.grad).all().item() for p in model.parameters())
    assert all(torch.equal(before[k],v.detach().cpu()) for k,v in model.state_dict().items())
    rss,hwm=proc_memory(os.getpid())
    result={'status':'SYNTHETIC_ONE_FORWARD_BACKWARD_COMPLETE','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'python':sys.version,'executable':sys.executable,'torch':torch.__version__,'cuda':torch.version.cuda,
            'gpu':prop.name,'shape':list(SHAPE),'dtype':'float32','input_bytes':input_bytes(),'parameter_count':110082,
            'optimizer_updates':0,'parameters_unchanged':True,'data_files_read':[],
            'max_cuda_allocated_bytes':torch.cuda.max_memory_allocated(),'max_cuda_reserved_bytes':torch.cuda.max_memory_reserved(),
            'rss_at_end_bytes':rss,'rss_high_water_bytes':hwm,'source_sha256':sha(__file__),
            'limits':'MLP only; excludes pairwise rank, recurrent book, event tensors, optimizer and data preprocessing; observed peak is not a hard upper bound'}
    write(out/'WORKER_RESULT.json',result)
    print(json.dumps(result),flush=True)


def terminate_owned(p):
    if p.poll() is not None:return
    if os.getpgid(p.pid)!=p.pid:raise RuntimeError('owned process group identity changed')
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=1)
    except subprocess.TimeoutExpired:
        if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
        p.wait(timeout=1)


def run_probe():
    t0=time.monotonic();out=OUTPUT
    out.mkdir(parents=False,exist_ok=False)  # One attempt; terminal failures are not retried in this root.
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    p=None;reason=None;rc=None;peakrss=peakgpu=0;max_gap=0.;last=time.monotonic()
    def interrupted(signum,frame):raise InterruptedError(f'guard_signal_{signum}')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        s=snapshot();s['reasons']=gate_reasons(s);write(out/'PREFLIGHT.json',s)
        if s['reasons']:reason='RESOURCE_REFUSED';return 75
        probe=out/'owned_quota_probe.bin'
        with open(probe,'xb') as f:f.write(bytes(65536));f.flush();os.fsync(f.fileno())
        assert probe.stat().st_size==65536;probe.unlink()
        command=[RUNTIME,'-B',str(pathlib.Path(__file__).resolve()),'--worker',str(out)]
        write(out/'COMMAND.json',{'argv':command,'source_sha256':sha(__file__),'declared_rss_bytes':DECLARED_RSS,
              'software_stop_bytes':SOFT_STOP,'public_spare_bytes':PUBLIC_SPARE,'gpu_budget_bytes':GPU_BUDGET,
              'wall_seconds':WALL_SECONDS,'deadline_monotonic':t0+WALL_SECONDS,'quota_probe_bytes':65536,'no_optimizer':True,'no_data_inputs':True})
        with open(out/'stdout.log','x') as stdout,open(out/'stderr.log','x') as stderr:
            p=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True,cwd=out)
            if os.getpgid(p.pid)!=p.pid:raise RuntimeError('child did not get a private process group')
            write(out/'PID.json',{'pid':p.pid,'pgid':p.pid,'guard_pid':os.getpid()})
            next_gpu=0.
            while p.poll() is None:
                now=time.monotonic();max_gap=max(max_gap,now-last);last=now
                ar,ah=proc_memory(p.pid);br,bh=proc_memory(os.getpid())
                peakrss=max(peakrss,ar+br,ah+bh)
                if now>=next_gpu:
                    rows=gpu_rows();peakgpu=max(peakgpu,owned_gpu_bytes(rows,p.pid));next_gpu=now+.5
                    strangers=[int(v.split(',')[0]) for v in rows.splitlines() if v.strip() and int(v.split(',')[0])!=p.pid]
                    if strangers:reason='OTHER_GPU_WORK_STARTED';break
                public_free=int((MEMORY/'memory.max').read_text())-int((MEMORY/'memory.current').read_text())
                reason=stop_reason(peakrss,peakgpu,time.monotonic()-t0,public_free)
                if reason:break
                time.sleep(.05)
            if reason:terminate_owned(p)
            rc=p.wait(timeout=1)
        if rc==0 and not reason:
            result=json.loads((out/'WORKER_RESULT.json').read_text())
            peakrss=max(peakrss,result['rss_high_water_bytes']+proc_memory(os.getpid())[1])
            peakgpu=max(peakgpu,result['max_cuda_reserved_bytes'])
            reason=stop_reason(peakrss,peakgpu,time.monotonic()-t0,PUBLIC_SPARE)
            if not reason:reason='OBSERVATION_COMPLETE'
        elif not reason:reason='WORKER_FAILED'
        return 0 if reason=='OBSERVATION_COMPLETE' else 76
    except BaseException as e:
        reason='GUARD_EXCEPTION:'+type(e).__name__+':'+str(e)
        return 76
    finally:
        if p is not None:
            terminate_owned(p);rc=p.returncode
        write(out/'TERMINAL.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':reason,'returncode':rc,
            'source_sha256':sha(__file__),'worker_pid':None if p is None else p.pid,'wall_seconds':time.monotonic()-t0,
            'peak_own_rss_highwater_sum_bytes':peakrss,'peak_gpu_observed_bytes':peakgpu,'max_monitor_gap_seconds':max_gap,
            'rss_poll_seconds':.05,'gpu_poll_seconds':.5,'query_timeout_seconds':1.,'optimizer_updates':0,
            'declared_rss_bytes':DECLARED_RSS,'software_stop_bytes':SOFT_STOP,'public_spare_bytes':PUBLIC_SPARE,
            'no_reschedule':True,'not_a_hard_memory_cap':True,'training_budget_automatically_changed':False})


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--worker',type=pathlib.Path)
    args=ap.parse_args()
    if args.worker is not None:
        if args.run or args.worker!=OUTPUT or not (OUTPUT/'COMMAND.json').exists():raise ValueError('invalid private worker invocation')
        worker(args.worker);return
    if args.run:raise SystemExit(run_probe())
    print(json.dumps({'mode':'PROPOSAL_ONLY','shape':SHAPE,'input_bytes':input_bytes(),'rss_declared_bytes':DECLARED_RSS,
          'rss_software_stop_bytes':SOFT_STOP,'gpu_budget_bytes':GPU_BUDGET,'public_spare_bytes':PUBLIC_SPARE,
          'wall_seconds':WALL_SECONDS,'output':str(OUTPUT),'runtime':RUNTIME,'source_sha256':sha(__file__)},indent=2))


if __name__=='__main__':main()

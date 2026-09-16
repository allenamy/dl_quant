"""Bounded source and IO checks for the four current strategy/mode paths."""
from pathlib import Path
import hashlib,json,os
import numpy as np

HERE=Path(__file__).resolve().parent
R=Path('/workspace/codex_research/QNT-2026-0907/causal_fullchain_20260914')
REMOTE=R/'integration/current_rule_mark_cash_audit_20260915'
RUNNER=R/'book/dynamic_frame_inputs_20260915/current_rule_mark_valuation_20260915'
BATCH=RUNNER/'formal1/batch'
NATIVE=RUNNER/'formal1/execution1'
MANIFEST=RUNNER/'formal1/MANIFEST.json'
EXECUTOR_SHA='514024be21f554101fe39dac273cee4137e4aafa0f88d9ed91c698299a3c0313'
READER_SHA='a193df4890abd0724f36dd768fb78d810dfbac1392bc42fdc88ecaa3abe69c33'
READER_LOCK_SHA='26904b4515d0d6cf0d60325fbb994152c08f9373a73def7688f49e1e849615ba'
FIRST=1735689600000;TERMINAL=1788220800000
from current_dispatch import SCENARIOS, scenario_identity
FACT_PARENT=R/'book/dynamic_frame_inputs_20260915/runner4/formal1/central3'
FACT_PARENT_INPUT_SHA='1a5f2b24cc4d8e0710c5a8bfebd0f396dd2ccd141a47b81669c4e90d5f9aaf65'

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,value):
    with Path(p).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def merge(pins,extra):
    for p,h in extra.items():
        need(p not in pins or pins[p]==h,'conflicting immutable source '+p);pins[p]=h
def pin(p,pins,expected=None):
    p=Path(p);h=sha(p);need(expected is None or h==expected,'source SHA '+str(p));merge(pins,{str(p):h});return p
def arrays(p,names=None):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in (names or z.files)}
def require_scenario(name):return scenario_identity(name)
def locate(axis,value):
    need(type(value)is int and axis.dtype==np.int64 and axis.ndim==1,'exact int64 clock')
    i=int(np.searchsorted(axis,value));need(i<len(axis) and int(axis[i])==value,'exact clock absent, no nearest/clip');return i
def select_applied(rows,status):
    need(status in ('COMPLETE_CONDITIONAL_PATH','UNMEASURABLE'),'closed path result required')
    if status=='UNMEASURABLE':
        need(rows and rows[-1].get('outcome')=='UNMEASURABLE','one terminal unknown row required');applied,blocked=rows[:-1],rows[-1]
    else:applied,blocked=rows,None
    need(all(r.get('outcome')=='APPLIED_RESEARCH_EVENT' for r in applied),'no skipped/partial/unknown economic rows')
    return applied,blocked
def verify_final_exit(x):
    need(type(x.get('actual_child_exit'))is int and x['actual_child_exit']==0 and x.get('changed_inputs')==[] and x.get('manifest_unchanged')is True,'actual int0 unchanged native batch required')
def runner_contract():
    # This source-bound file is written only after the original current runner
    # source/CLI are frozen. Absent contract means no runnable audit config.
    p=HERE/'RUNNER_CONTRACT.json';need(p.is_file(),'WAIT_CURRENT_RUNNER_SOURCE_CONTRACT')
    c=read(p);need(c['schema']=='FIXED_CURRENT_CASH_RUNNER_CONTRACT_1','fixed current runner contract schema')
    need(c['runner']==str(RUNNER) and c['manifest']==str(MANIFEST) and c['execution']==str(NATIVE) and c['batch']==str(BATCH),'fixed current namespaces')
    return c

def native_launch(pins):
    c=runner_contract();pin(HERE/'RUNNER_CONTRACT.json',pins)
    m=read(pin(MANIFEST,pins));l=read(pin(NATIVE/'LAUNCH.json',pins))
    dp=RUNNER/'formal1/DESCRIPTOR.json';desc=read(pin(dp,pins));dh=sha(dp)
    expected=[dh if x=='$DESCRIPTOR_SHA256' else x for x in c['argv_template']]
    need(m['argv']==l['argv']==expected and l['manifest_sha256']==sha(MANIFEST) and l['pins']==m['pins'] and l['launcher_sha256']==EXECUTOR_SHA,'current actual launch/manifest/argv identity')
    need(desc['schema']=='CURRENT_RULE_MARK_MAIN_DESCRIPTOR_1' and desc['source_sha256']==c['source_lock_sha256'] and desc['output']==str(BATCH),'current source-bound actual descriptor')
    need(m['pins'].get(str(dp))==dh and m['pins'].get(str(RUNNER/'SOURCE_LOCK.json'))==c['source_lock_sha256'],'current descriptor/source watched')
    lock=read(pin(RUNNER/'SOURCE_LOCK.json',pins,c['source_lock_sha256']))
    for p,h in c['required_sources'].items():
        need(m['pins'].get(p)==h,'fixed current entry source monitored '+p);pin(p,pins,h)
    pin(R/'integration/execute_manifest.py',pins,EXECUTOR_SHA)
    return m

def native_completion(pins):
    m=native_launch(pins);x=read(pin(NATIVE/'EXIT.json',pins));verify_final_exit(x)
    need(x['argv']==m['argv'] and x['manifest_sha256']==sha(MANIFEST) and x['launch_sha256']==sha(NATIVE/'LAUNCH.json'),'actual current native exit binding')
    for n in ('STDOUT','STDERR'):pin(NATIVE/(n+'.log'),pins,x[n.lower()+'_sha256'])
    return x

def resources():
    for n in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):need(os.environ.get(n)=='1','explicit CPU1 '+n)
    need(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CUDA hidden')
    used=int(Path('/sys/fs/cgroup/memory.current').read_text());maximum=int(Path('/sys/fs/cgroup/memory.max').read_text())
    need(maximum-used>=12*(1<<30),'at least12GiB cgroup headroom')
    return dict(current=used,maximum=maximum,headroom=maximum-used)

def funding_alignment(m,f,origin,terminal,public):
    ix=np.flatnonzero((m['event_ms']>=origin)&(m['event_ms']<terminal));n=len(ix)
    need(np.array_equal(f['source_row'],np.arange(n,dtype=np.int64)),'complete funding source row order/population')
    for a,b in [('event_ms','event_ms'),('asset','event_asset'),('rate','event_rate')]:
        need(np.array_equal(f[a],m[b][ix],equal_nan=True),'original funding field '+a)
    for k in ('rate','mark','interval_hours'):need(np.array_equal(f[k+'_known'],np.isfinite(f[k])),'explicit original known mask '+k)
    expected=m['event_close_mark'][ix].copy()
    kinds=np.where(np.isfinite(expected)&(expected>0),'CLOSE_PROXY','MISSING').astype('U16')
    seen=set()
    for k in range(n):
        key=(int(f['asset'][k]),int(f['event_ms'][k]))
        if key in public:
            rate,mark=public[key];need(f['rate'][k]==rate and key not in seen,'official exact mark original rate/time identity');seen.add(key);expected[k]=mark;kinds[k]='EXACT'
    need(seen==set(public),'all official exact marks retained exactly once')
    need(np.array_equal(f['mark'],expected,equal_nan=True),'original/public price identity')
    need(np.array_equal(f['mark_kind_names'][f['mark_kind_index']],kinds),'funding provenance category')
    raw=m['event_interval_h'][ix];same=(f['interval_hours']==raw)|(np.isnan(f['interval_hours'])&np.isnan(raw))
    return np.flatnonzero(~same).tolist()

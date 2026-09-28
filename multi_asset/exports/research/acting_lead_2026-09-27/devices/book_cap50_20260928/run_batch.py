"""One exploratory cap050 comparison; original algorithm/calibration unchanged.

Runs original-combo identities, full-axis seed-0 engine identities, then two
32-path candidate cells. Never trades, never edits reference files or resumes
production. Three-hour wall bound applies to this entire batch.
"""
import os, sys, json, hashlib, pathlib, subprocess, time, signal, traceback

HERE = pathlib.Path(__file__).resolve().parent
C = json.loads((HERE / 'CONTRACT.json').read_text())
ROOT = pathlib.Path(C['root'])
PY = '/workspace/venv/bin/python'
ENGINE = '/dev/shm/news2_2026-09-23/engine'
ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/root'}
CHILDREN = []
STEPS = []
START = time.monotonic()


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''): h.update(b)
    return h.hexdigest()


def write(name, obj):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'x') as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.flush(); os.fsync(f.fileno())


def stop_own():
    for p, f, *_ in CHILDREN:
        if p.poll() is None:
            if os.getpgid(p.pid) != p.pid: raise RuntimeError('own child PGID mismatch')
            os.killpg(p.pid, signal.SIGTERM)
            try: p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL); p.wait(timeout=3)
        f.close()


def launch(label, args, cwd):
    f = open(ROOT / 'logs' / (label + '.log'), 'x')
    p = subprocess.Popen(args, cwd=cwd, env=ENV, stdout=f,
                         stderr=subprocess.STDOUT, start_new_session=True)
    x = (p, f, label, time.monotonic())
    CHILDREN.append(x)
    write('processes/' + label + '.json', {'pid': p.pid, 'pgid': os.getpgid(p.pid),
          'start_ticks': pathlib.Path(f'/proc/{p.pid}/stat').read_text().split()[21],
          'argv': args, 'cwd': str(cwd), 'utc': time.strftime('%FT%TZ', time.gmtime())})
    return x


def wait_all(group):
    while any(p.poll() is None for p, *_ in group):
        if time.monotonic() - START > C['wall_seconds']: raise TimeoutError('batch 3h budget')
        if any(p.poll() not in (None, 0) for p, *_ in group):
            raise RuntimeError('child failed; stopping remaining batch')
        time.sleep(2)
    for p, f, label, t in group:
        f.flush()
        s = {'label': label, 'rc': p.returncode, 'wall_seconds': time.monotonic()-t,
             'log_sha256': sha(ROOT / 'logs' / (label + '.log'))}
        STEPS.append(s); write('steps/' + label + '.json', s)
        if p.returncode: raise RuntimeError(f'{label}: rc={p.returncode}')


def chain(seed, rule, engine=False):
    args = [PY, '-B', str(HERE / 'alloc_chain_run.py'), 'PATH,HOME,LC_CTYPE',
            str(ROOT/'receipts'), '--seed', str(seed), '--rule', rule, '--mix', 'shared']
    if engine: args.append('--engine')
    return args


def main():
    ROOT.mkdir(exist_ok=False)
    for d in ('logs', 'receipts', 'cells', 'processes', 'steps'): (ROOT/d).mkdir()
    for n,h in C['copied_sources'].items():
        if sha(HERE/n) != h: raise ValueError('source drift: '+n)
    if sha(__file__) != C['runner_sha256']: raise ValueError('runner drift')
    # All environment and source identities are collected before the first run.
    write('PREFLIGHT.json', {'utc': time.strftime('%FT%TZ',time.gmtime()),
           'contract_sha256': sha(HERE/'CONTRACT.json'), 'sources': C['copied_sources'],
           'python': sys.executable, 'env': ENV,
           'memory_current': pathlib.Path('/sys/fs/cgroup/memory.current').read_text().strip(),
           'memory_max': pathlib.Path('/sys/fs/cgroup/memory.max').read_text().strip()})
    wait_all([launch(f'identity_combo_s{s}',chain(s,'inservice'),HERE) for s in (42,2027)])
    identity = {}
    for s in (42,2027):
        p = ROOT/f'receipts/ALLOC_CHAIN_inservice_shared_s{s}.json'
        r = json.loads(p.read_text())
        if r['COMBO_VS_ARCHIVE'].get('ALL_IDENTICAL') is not True:
            raise ValueError('complete original combination parity failed')
        identity[str(s)]={'receipt':str(p),'sha256':sha(p)}
    write('COMBO_IDENTITIES.json',identity)
    probes=[]
    for s in (42,2027):
        arm=f'ALLOC_inservice_shared_s{s}X'; tag=arm+'|scaled|rule|raw|UAFE'
        cpath=ROOT/f'cells/inservice_shared_s{s}/configs/RUN_CONFIG_{arm}.json'
        cfg=json.loads(cpath.read_text())
        probes.append(launch(f'identity_engine_s{s}',[PY,'-B','bt_launch.py',
          'PATH,HOME,LC_CTYPE',str(cpath),'--smoke',cfg['window']['first_anchor'],
          str(cfg['window']['n_anchors']),'0',tag,'identity_fullaxis'],ENGINE))
    wait_all(probes)
    import numpy as np
    rows=[]
    for s in (42,2027):
        arm=f'ALLOC_inservice_shared_s{s}X'; tag=arm+'_scaled_rule_raw_UAFE'
        p=ROOT/f'cells/inservice_shared_s{s}/runs_smoke/identity_fullaxis/{tag}/PATH_{tag}_seed_00.npz'
        ref=pathlib.Path(f'/workspace/dlarch_2026-09-24/chain/ref_nc_s{s}X/runs/DLARCH_REF_NC_s{s}X_scaled_rule_raw_UAFE/PATH_DLARCH_REF_NC_s{s}X_scaled_rule_raw_UAFE_seed_00.npz')
        with np.load(p,allow_pickle=False) as a,np.load(ref,allow_pickle=False) as b:
            if sorted(a.files)!=sorted(b.files): raise ValueError('engine key mismatch')
            bad=[k for k in a.files if a[k].dtype!=b[k].dtype or a[k].shape!=b[k].shape or a[k].tobytes()!=b[k].tobytes()]
            if bad: raise ValueError('engine arrays differ '+str(bad))
        rows.append({'seed':s,'new':str(p),'new_sha256':sha(p),'reference':str(ref),
                     'reference_sha256':sha(ref),'all_arrays_bitwise':True})
    write('ENGINE_IDENTITIES.json',rows)
    wait_all([launch(f'candidate_cap050_s{s}',chain(s,'cap050',True),HERE) for s in (42,2027)])
    read=[]
    for s in (42,2027):
        at=f'ALLOC_cap050_shared_s{s}X_scaled_rule_raw_UAFE'
        rt=f'DLARCH_REF_NC_s{s}X_scaled_rule_raw_UAFE'
        read.append(launch(f'paired_read_s{s}',[PY,'-B',str(HERE/'alloc_read.py'),
          'PATH,HOME,LC_CTYPE',str(ROOT/f'cells/cap050_shared_s{s}/runs/{at}'),at,
          f'/workspace/dlarch_2026-09-24/chain/ref_nc_s{s}X/runs/{rt}',rt,
          str(ROOT/f'receipts/PAIRED_s{s}.json')],HERE))
    wait_all(read)
    for n,h in C['copied_sources'].items():
        if sha(HERE/n)!=h: raise ValueError('source changed during batch '+n)


if __name__=='__main__':
    status='FAILED';rc=1;error=None
    try: main();status='EXPLORATORY_COMPARISON_COMPLETE_NOT_RELEASE';rc=0
    except BaseException as e: error=repr(e);traceback.print_exc()
    finally:
        stop_own()
        if ROOT.exists():
            write('TERMINAL.json',{'utc':time.strftime('%FT%TZ',time.gmtime()),'status':status,
              'rc':rc,'error':error,'wall_seconds':time.monotonic()-START,'steps':STEPS,
              'production_changes':0,'new_model_training':False,'GPU_used':False,
              'warning':'exploratory risk comparison; no swap or equivalence claim'})
    sys.exit(rc)

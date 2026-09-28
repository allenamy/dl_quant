"""One inverse-risk comparison; immutable cap50 controls are reused.

Runs original-combo identities, full-axis seed-0 engine identities, then two
32-path candidate cells. Never trades, never edits reference files or resumes
production. Thirty-minute wall bound applies to this entire batch.
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
        if time.time() > C['deadline_epoch']: raise TimeoutError('registered absolute 30m budget')
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
    for d in ('logs','receipts','cells','processes','steps'): (ROOT/d).mkdir()
    for n,h in C['copied_sources'].items():
        if sha(HERE/n)!=h: raise ValueError('source drift '+n)
    if sha(__file__)!=C['runner_sha256']:raise ValueError('runner drift')
    parent=pathlib.Path(C['parent_root'])
    for n,h in C['parent_receipts'].items():
        if sha(parent/n)!=h:raise ValueError('parent receipt drift '+n)
    if json.loads((parent/'TERMINAL.json').read_text())['rc']!=0:
        raise ValueError('parent control batch not complete')
    for seed in (42,2027):
        d=json.loads((parent/f'receipts/PAIRED_s{seed}.json').read_text())
        for f in d['ref']['facts']:
            p=pathlib.Path(d['ref']['dir'])/f"PATH_{d['ref']['tag']}_seed_{f['seed']:02d}.npz"
            if sha(p)!=f['npz_sha256']:raise ValueError('reference path changed '+str(p))
    identity=json.loads((parent/'ENGINE_IDENTITIES.json').read_text())
    write('ENGINE_IDENTITIES.json',identity)
    write('PREFLIGHT.json',{'utc':time.strftime('%FT%TZ',time.gmtime()),
      'contract_sha256':sha(HERE/'CONTRACT.json'),'sources':C['copied_sources'],
      'parent_receipts':C['parent_receipts'],'reuse':'same kernels, inputs and reference paths; no claim of rerunning controls',
      'python':sys.executable,'env':ENV})
    import numpy as np
    import alloc_rules
    with np.load('/dev/shm/news2_2026-09-23/work/legs.npz',allow_pickle=False) as z:
        LR=z['LR'];WL=z['WL']
    checks=alloc_rules.causality_probe('invvol',LR,WL,[1000,4000,8000])
    write('CAUSALITY.json',{'checks':checks,'source_sha256':sha(HERE/'alloc_rules.py')})
    if not all(checks.values()):raise ValueError('future perturbation changed prior seat')
    wait_all([launch(f'candidate_invvol_s{s}',chain(s,'invvol',True),HERE) for s in (42,2027)])
    write('SIMULATION_TERMINAL.json',{'rc':0,'status':'SIMULATIONS_AUDITED',
      'utc':time.strftime('%FT%TZ',time.gmtime()),'steps':STEPS})
    wait_all([launch('economic_readout',[PY,'-B',str(HERE/'economic_readout.py'),
      '--root',str(ROOT),'--out',str(ROOT/'receipts/ECONOMIC_FULL_BOOK.json')],HERE)])
    for n,h in C['copied_sources'].items():
        if sha(HERE/n)!=h:raise ValueError('source changed during batch '+n)

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

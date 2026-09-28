"""Two deterministic holding-horizon controls; immutable cap50 controls are reused.

Revalidates archived combo and full-axis engine identities, then runs two
32-path candidate cells. Never trades, never edits reference files or resumes
production. Forty-five-minute wall bound applies to this entire batch.
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
        if time.time() > C['deadline_epoch']: raise TimeoutError('registered absolute 45m budget')
        if any(p.poll() not in (None, 0) for p, *_ in group):
            raise RuntimeError('child failed; stopping remaining batch')
        time.sleep(2)
    for p, f, label, t in group:
        f.flush()
        s = {'label': label, 'rc': p.returncode, 'wall_seconds': time.monotonic()-t,
             'log_sha256': sha(ROOT / 'logs' / (label + '.log'))}
        STEPS.append(s); write('steps/' + label + '.json', s)
        if p.returncode: raise RuntimeError(f'{label}: rc={p.returncode}')


def chain(kind, engine=False):
    args = [PY, '-B', str(HERE / 'alloc_chain_run.py'), 'PATH,HOME,LC_CTYPE',
            str(ROOT/'receipts'), '--seed', '42', '--rule', 'inservice', '--mix', 'shared', '--kind', kind]
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
    from control_binding import verify_controls
    external = verify_controls(parent)
    identity=json.loads((parent/'ENGINE_IDENTITIES.json').read_text())
    write('ENGINE_IDENTITIES.json',identity)
    write('PREFLIGHT.json',{'utc':time.strftime('%FT%TZ',time.gmtime()),
      'contract_sha256':sha(HERE/'CONTRACT.json'),'sources':C['copied_sources'],
      'parent_receipts':C['parent_receipts'],'reuse':'same kernels, inputs and reference paths; no claim of rerunning controls',
      'python':sys.executable,'env':ENV,'external_control_bindings':external})
    previous=pathlib.Path(C['wait_for_terminal'])
    while not previous.exists():
        if time.time()>C['deadline_epoch']:raise TimeoutError('previous batch not terminal')
        time.sleep(10)
    # Do not compete with the existing batch. Its finally block stops all its
    # own children BEFORE it writes terminal, including the failure path.
    while True:
        maximum=pathlib.Path('/sys/fs/cgroup/memory.max').read_text().strip()
        stats=dict(line.split() for line in pathlib.Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
        if maximum.isdigit() and (int(maximum)-int(stats['anon'])-int(stats['shmem']))>=24*2**30:break
        if time.time()>C['deadline_epoch']:raise TimeoutError('training memory headroom unavailable')
        time.sleep(10)
    if 'reuse_model_root' in C:
        # An interface retry reuses the sealed model bytes, never refits them.
        from residual_model import verify_training
        old=pathlib.Path(C['reuse_model_root'])
        for name,h in C['reuse_model_pins'].items():
            if sha(old/name)!=h:raise ValueError('sealed model reuse drift '+name)
        (ROOT/'models').mkdir()
        for kind in ('fast','slow'):
            src=old/'models'/kind
            rec=json.loads((src/'TRAIN_RECEIPT.json').read_text())
            if rec['target']!=kind:raise ValueError('model reuse target identity')
            verify_training(src,rec,42)
            (ROOT/'models'/kind).symlink_to(src,target_is_directory=True)
        write('MODEL_DONE.json',json.loads((old/'MODEL_DONE.json').read_text()))
        write('MODEL_REUSE.json',{'source_root':str(old),'pins':C['reuse_model_pins'],
              'refit':False,'reason':'only exact completed-training status admitted by combo reader'})
    else:
        wait_all([launch('train_models',[PY,'-B',str(HERE/'train_ridge.py')],HERE)])
    wait_all([launch(f'candidate_{k}',chain(k,True),HERE) for k in ('fast','slow')])
    write('SIMULATION_TERMINAL.json',{'rc':0,'status':'SIMULATIONS_AUDITED',
      'utc':time.strftime('%FT%TZ',time.gmtime()),'steps':STEPS})
    wait_all([launch('economic_readout',[PY,'-B',str(HERE/'economic_readout.py'),
      '--root',str(ROOT),'--out',str(ROOT/'receipts/ECONOMIC_FULL_BOOK.json')],HERE)])
    if verify_controls(parent)!=external:raise ValueError('external configuration changed during batch')
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
              'production_changes':0,'new_model_training':True, 'model_kind':'deterministic_Ridge_not_DL','GPU_used':False,
              'warning':'exploratory risk comparison; no swap or equivalence claim'})
    sys.exit(rc)

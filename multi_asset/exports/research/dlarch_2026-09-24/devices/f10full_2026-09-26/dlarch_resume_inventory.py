#!/usr/bin/env python3
"""dlarch_resume_inventory.py -- READ-ONLY inventory of every F10_FULL-program artefact after the
2026-09-26 11:14Z-16:58Z Mac migration (2 reboots + 1 sleep killed every local driver and waiter).

Written BEFORE anything is relaunched. It never trains, never deletes, never writes outside its --out.

For every piece it answers exactly one of: DONE (and a read-back check passed), PARTIAL, NEVER_STARTED.
"Done" is never taken from a marker alone: a marker says "finished", a claim says "someone is working",
and the absence of either says neither (absence_of_a_done_marker_is_not_absence_of_a_worker). So each
piece is judged from (a) the artefacts, re-hashed against the sha their own receipt recorded at write
time, (b) the log line the run itself printed, and (c) whether any process of a PGID dlarch recorded is
still alive -- read from the process table by PGID, never by name (pod2 is shared).

It deliberately does NOT print any book-layer or IC reading. Readings belong to the verdict devices;
this receipt is about completeness and integrity only.

usage: dlarch_resume_inventory.py <env-whitelist> <out.json>
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL)
assert not _x, f'env outside whitelist: {_x}'
OUT = sys.argv[2]

W = '/workspace/dlarch_2026-09-24'
ARM = 'G1_T0_nomask_frac1'
SEEDS = (42, 2027, 7)
NFOLD = 23
TRAINER_PIN = 'db6771e30fb7d1befcf9bb77f4c0504131fc0d491e02dc45bab15ed04e5d8e61'
SHUF_TRAINER_PIN = '526794e8dceefff2e35f290c6aadc99074edcc7a7468bda81aee15ab6a69af77'
CHAIN_RUN_PIN = '6345132f245433ad702f15cf8d374b126bc0827482e59e25200a6ee8760bf9e3'   # dlarch_chain_run.py @ 33c1b7d30


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jload(p):
    """Parse or report WHY not; a truncated receipt must read as broken, never as absent."""
    try:
        with open(p) as f:
            return json.load(f), None
    except Exception as e:                       # noqa: BLE001 -- the error IS the reading here
        return None, f'{type(e).__name__}: {e}'


def grep(path, pat):
    if not os.path.exists(path):
        return []
    rx = re.compile(pat)
    with open(path, errors='replace') as f:
        return [ln.rstrip('\n') for ln in f if rx.search(ln)]


inv = {'device': 'dlarch_resume_inventory.py', 'self_sha256': sha(os.path.abspath(__file__)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'scope': 'F10_FULL main arm x3 seeds, its book cells, NC reference cells, s2027 identity control '
                '(C1.7), control 1 shuffle arm (C1.11), leak spectra for C1.9 re-judge, verdict receipts',
       'readings_printed': False, 'pieces': {}}
P = inv['pieces']

# ── 1. training, per seed ─────────────────────────────────────────────────────────────────────────
main_log = f'{W}/f10full_2026-09-26/main.log'
for s in SEEDS:
    d = f'{W}/T3/{ARM}/f10_s{s}'
    folds = sorted(glob.glob(f'{d}/*/FOLD_RECEIPT.json'))
    tr, err = jload(f'{d}/TRAIN_RECEIPT.json')
    rb = {'fold_artifacts_rehashed': 0, 'fold_artifacts_mismatch': []}
    if tr:
        for pth, want in tr['fold_artifacts'].items():
            got = sha(pth) if os.path.exists(pth) else 'MISSING'
            rb['fold_artifacts_rehashed'] += 1
            if got != want:
                rb['fold_artifacts_mismatch'].append({'path': pth, 'want': want, 'got': got})
        oof = f'{d}/F10_OOF.npz'
        rb['oof_sha_recorded'] = tr.get('pred_sha256')
        rb['oof_sha_now'] = sha(oof) if os.path.exists(oof) else 'MISSING'
        rb['oof_readback_ok'] = rb['oof_sha_now'] == rb['oof_sha_recorded']
        trainer_srcs = {k: v for k, v in tr.get('sources', {}).items() if k.endswith('dlarch_train_f10.py')}
        rb['trainer_sources'] = trainer_srcs
        rb['trainer_is_pinned'] = list(trainer_srcs.values()) == [TRAINER_PIN]
    done_line = [ln for ln in grep(main_log, r'^DLARCH_TRAIN_DONE') if f'seed={s} ' in ln]
    lr, lerr = jload(f'{W}/f10full_2026-09-26/receipts/LAUNCH_MAIN_s{s}.json')
    ok = (len(folds) == NFOLD and tr is not None
          and tr.get('status') == 'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED'
          and len(tr.get('folds', [])) == NFOLD and not rb['fold_artifacts_mismatch']
          and rb.get('oof_readback_ok') and rb.get('trainer_is_pinned') and len(done_line) == 1
          and done_line[0].split('oof_sha=')[1][:16] == rb['oof_sha_now'][:16]
          and lr is not None and lr.get('ALL_GATES_PASS') is True)
    P[f'train_s{s}'] = {
        'dir': d, 'fold_receipts': len(folds), 'train_receipt_status': tr and tr.get('status'),
        'train_receipt_error': err, 'train_params_sha256': tr and tr.get('train_params_sha256'),
        'readback': rb, 'log_done_line': done_line, 'launch_gate_all_pass': lr and lr.get('ALL_GATES_PASS'),
        'launch_receipt_error': lerr,
        'STATE': 'DONE' if ok else ('PARTIAL' if folds else 'NEVER_STARTED')}

tp = {P[f'train_s{s}']['train_params_sha256'] for s in SEEDS}
inv['train_params_note'] = ('train_params_sha256 legitimately DIFFERS across seeds (seed is a recipe '
                            'parameter); asserted instead: every seed ran the SAME pinned trainer sha')
inv['train_params_sha256_per_seed'] = {str(s): P[f'train_s{s}']['train_params_sha256'] for s in SEEDS}
inv['all_seeds_same_trainer_sha'] = all(P[f'train_s{s}']['readback'].get('trainer_is_pinned') for s in SEEDS)
inv['main_log_all_seeds_done_line'] = grep(main_log, r'^F10FULL_MAIN_ALL_SEEDS_DONE')
inv['main_log_traceback_lines'] = len(grep(main_log, r'Traceback'))

# ── 2. book cells (engine + retain), per seed; and the three NC reference cells ──────────────────
def cell(tag_dir_glob, chain_json=None):
    ds = sorted(glob.glob(f'{W}/receipts/{tag_dir_glob}'))
    if not ds:
        return {'STATE': 'NEVER_STARTED', 'glob': tag_dir_glob}
    fs = glob.glob(f'{ds[0]}/RETAIN_*.json')
    r, err = jload(fs[0]) if fs else (None, 'no RETAIN_*.json in dir')
    o = {'dir': ds[0], 'retain_error': err}
    if r:
        ss = dict(r['small_series'])
        # two delivered T0 receipts (s42, s2027) record a path RELATIVE to W; resolve against W, not
        # against this process's cwd (the first run of this device read them as MISSING for that reason)
        ss['path'] = ss['path'] if os.path.isabs(ss['path']) else os.path.join(W, ss['path'])
        o['small_series_path_resolved'] = ss['path']
        o.update({'tag': r['tag'], 'control_tag': r['control_tag'],
                  'ALL_PRECONDITIONS_PASS': r['ALL_PRECONDITIONS_PASS'],
                  'retain_device_sha256': r['self_sha256'], 'frozen_judge_sha256': r['frozen_judge_sha256'],
                  'small_series_sha_recorded': ss['sha256'],
                  'small_series_sha_now': sha(ss['path']) if os.path.exists(ss['path']) else 'MISSING'})
        o['small_series_readback_ok'] = o['small_series_sha_now'] == o['small_series_sha_recorded']
    if chain_json:
        c, cerr = jload(chain_json)
        o['chain_receipt'] = chain_json
        o['chain_receipt_error'] = cerr
        o['chain_run_sha256'] = c and c.get('self_sha256')
        o['chain_run_is_pinned'] = bool(c) and c.get('self_sha256') == CHAIN_RUN_PIN
        o['chain_train_arm'] = c and c.get('train_arm')
        o['chain_seed'] = c and c.get('seed')
    good = bool(r) and r['ALL_PRECONDITIONS_PASS'] and o.get('small_series_readback_ok') and \
        (chain_json is None or o.get('chain_run_is_pinned'))
    o['STATE'] = 'DONE' if good else 'PARTIAL'
    return o


for s in SEEDS:
    P[f'cell_F10FULL_s{s}'] = cell(f'RETAIN_F10FULL_s{s}_2026-09-26.json',
                                   f'{W}/CHAIN/F10FULL_s{s}/CHAIN_{ARM}_s{s}.json')
    P[f'cell_F10FULL_s{s}']['driver_log_retain_line'] = [
        ln for ln in grep(f'{W}/CHAIN/f10full_cells_driver.log', r'DLARCH_CELL_RETAIN') if f'_s{s}_' in ln]
P['cell_REFNC_s42'] = cell('RETAIN_REFNC_s42_SELFCTL_2026-09-26.json')
P['cell_REFNC_s2027'] = cell('RETAIN_REFNC_s2027_2026-09-26.json')
P['cell_REFNC_s7'] = cell('RETAIN_REFNC_s7_2026-09-26.json')
for s in SEEDS:
    P[f'cell_T0_s{s}_reference_column'] = cell(f'RETAIN_s{s}_2026-09-25.json')
inv['cells_driver_done_line'] = grep(f'{W}/CHAIN/f10full_cells_driver.log', r' === F10FULL_CELLS_DRIVER_DONE ===$')
inv['open_cell_claims'] = sorted(glob.glob(f'{W}/CHAIN/.claim_*'))
inv['cell_retain_device_shas'] = sorted({P[k].get('retain_device_sha256') for k in P
                                         if k.startswith('cell_F10FULL') or k.startswith('cell_REFNC')})

# ── 3. C1.7 s2027 identity control ───────────────────────────────────────────────────────────────
idr = f'{W}/f10full_2026-09-26/receipts/S2027_IDENTITY_2026-09-26.json'
ilog = f'{W}/f10full_2026-09-26/s2027_identity.log'
r, err = jload(idr)
logged = [ln for ln in grep(ilog, r'^receipt=.*S2027_IDENTITY') if 'sha256=' in ln]
o = {'receipt': idr, 'error': err, 'log_lines': grep(ilog, r'DLARCH_IDENTITY=|S2027_IDENTITY_'),
     'receipt_sha_now': sha(idr) if os.path.exists(idr) else 'MISSING',
     'receipt_sha_logged_at_write': logged[-1].split('sha256=')[1] if logged else None}
o['readback_ok'] = o['receipt_sha_now'] == o['receipt_sha_logged_at_write']
if r:
    o['all_identical'] = r.get('all_identical')
    o['positive_control'] = r.get('positive_control')
o['STATE'] = 'DONE' if (r and o['readback_ok']) else ('PARTIAL' if os.path.exists(ilog) else 'NEVER_STARTED')
P['C1_7_s2027_identity'] = o

# ── 4. control 1 (shuffle-future) ────────────────────────────────────────────────────────────────
sd = f'{W}/f10full_shuffle_2026-09-26'
shuf_out = sorted(glob.glob(f'{W}/T3/*SHUFFLED*/**/*', recursive=True))
P['control1_shuffle'] = {
    'arm_dir': sd, 'trainer_sha_now': sha(f'{sd}/dlarch_train_f10.py'),
    'trainer_is_pinned': sha(f'{sd}/dlarch_train_f10.py') == SHUF_TRAINER_PIN,
    'py_files_in_arm_dir': sorted(os.path.basename(p) for p in glob.glob(f'{sd}/*.py') + glob.glob(f'{sd}/.*.py')),
    'shuffled_outputs_found': shuf_out,
    'logs_found': sorted(glob.glob(f'{sd}/*.log')) + sorted(glob.glob(f'{W}/*ctl1*.log')),
    'verdict_receipts_found': sorted(glob.glob(f'{W}/receipts/CTL1_VERDICT*')),
    'STATE': 'NEVER_STARTED' if not shuf_out else 'PARTIAL_OR_DONE_SEE_OUTPUTS'}

# ── 5. C1.9 re-judge inputs: per-seed leak spectra of F10_FULL ─────────────────────────────────
P['C1_9_spectra'] = {str(s): sorted(glob.glob(f'{W}/receipts/F10FULL_LEAK_s{s}_*')) for s in SEEDS}
P['C1_9_spectra']['NC'] = sorted(glob.glob(f'{W}/receipts/LEAK_NC_INSERVICE_*'))
P['C1_9_rejudge_receipts'] = sorted(glob.glob(f'{W}/receipts/*C1_9*') + glob.glob(f'{W}/receipts/*K_POS*'))

# ── 6. book-layer verdict ───────────────────────────────────────────────────────────────────────
P['F10FULL_verdict_receipts'] = sorted(glob.glob(f'{W}/receipts/*F10FULL*VERDICT*')
                                       + glob.glob(f'{W}/receipts/PAIRED_D_F10FULL*'))

# ── 7. liveness: every PGID dlarch recorded, read from the process table by PGID ───────────────
pg = {}
for f in sorted(glob.glob(f'{W}/*.pgid') + glob.glob(f'{W}/CHAIN/*.pgid') + glob.glob(f'{W}/*/*.pgid')):
    m = re.search(r'pgid=(\d+)', open(f).read())
    if m:
        pg[f] = int(m.group(1))
ps = subprocess.run(['ps', '-eo', 'pgid=,pid=,etime=,args='], capture_output=True, text=True, check=True).stdout
alive = {}
for f, g in pg.items():
    rows = [ln.strip()[:160] for ln in ps.splitlines() if ln.split() and ln.split()[0] == str(g)]
    alive[f] = {'pgid': g, 'n_alive': len(rows), 'rows': rows}
inv['recorded_pgids'] = alive
inv['any_recorded_pgid_alive'] = any(v['n_alive'] for v in alive.values())
q = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used', '--format=csv,noheader'],
                   capture_output=True, text=True)
inv['gpu_now'] = q.stdout.strip() or q.stderr.strip()

inv['summary'] = {k: (v['STATE'] if isinstance(v, dict) and 'STATE' in v else v) for k, v in P.items()}
with open(OUT, 'w') as f:
    json.dump(inv, f, indent=1, sort_keys=True, default=str)
with open(OUT) as f:                      # read back through the same reader before reporting a sha
    assert json.load(f)['self_sha256'] == inv['self_sha256']
print(json.dumps(inv['summary'], indent=1, default=str))
print('any_recorded_pgid_alive=%s gpu=%s' % (inv['any_recorded_pgid_alive'], inv['gpu_now']))
print('DLARCH_RESUME_INVENTORY out=%s sha256=%s' % (OUT, sha(OUT)))

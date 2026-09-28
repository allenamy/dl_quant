"""Continue a resource-stopped cash stage, one 4-worker cell at a time.

Frozen training, models, targets, execution configuration and decision unchanged.
The failed attempt is kept; only the missing R180 cells are newly assembled.
No GPU training is called. The original absolute deadline and memory guard stay.
"""
import json
import os
from pathlib import Path
import sys
import time
import traceback

import run_batch as B


def check_parent(old, expected_sha):
    terminal = old / 'TERMINAL.json'
    if B.sha(terminal) != expected_sha:
        raise ValueError('failed terminal identity changed')
    t = json.loads(terminal.read_text())
    if t['rc'] != 1 or t['error'] != "MemoryError('shared resource limit')" or t['completed_neural_fold_outputs'] != 92:
        raise ValueError('not the declared resource-only continuation')
    if json.loads((old / 'steps/train_adapt.json').read_text())['rc'] != 0:
        raise ValueError('training incomplete')
    for p in (old / 'processes').glob('*.json'):
        x = json.loads(p.read_text())
        proc = Path(f"/proc/{x['pid']}/stat")
        if proc.exists() and proc.read_text().split()[21] == str(x['start_ticks']):
            raise ValueError('parent owned process still alive')
    for seed in (42, 2027):
        for kind in ('U', 'R180'):
            d = old / f'models/{kind}_s{seed}'
            r = json.loads((d / 'TRAIN_RECEIPT.json').read_text())
            if len(r['folds']) != 23 or set(r['folds']) != set(r['expected_folds']):
                raise ValueError('training fold population')
            for p, h in {**r['inputs'], **r['sources'], **r['fold_artifacts']}.items():
                if B.sha(p) != h:
                    raise ValueError('training dependency changed: ' + p)
            if B.sha(d / 'F10_OOF.npz') != r['pred_sha256']:
                raise ValueError('prediction drift')


def validate_path_files(run_dir, tag, config_sha, clean):
    expected = {f'PATH_{tag}_seed_{k:02d}.npz' for k in range(32)}
    if {p.name for p in run_dir.glob('PATH_*.npz')} != expected:
        raise ValueError('cash path population incomplete')
    for k in range(32):
        stem = run_dir / f'PATH_{tag}_seed_{k:02d}'
        r = json.loads(Path(str(stem) + '.json').read_text())
        if r['seed'] != k or r['config_sha256'] != config_sha:
            raise ValueError('cash path identity')
        if r['npz_sha256'] != B.sha(str(stem) + '.npz') or not clean(r['audits']):
            raise ValueError('cash path hash or audit')


def audit_cells():
    engine = Path('/dev/shm/news2_2026-09-23/engine')
    # Gate code is itself pinned by the unchanged full-book reader.
    from economic_readout import STATS_SHA
    if B.sha(engine / 'news_stats.py') != STATS_SHA:
        raise ValueError('stats source drift')
    sys.path.insert(0, str(engine))
    import news_stats as S
    for f, h in S.DEV.items():
        if B.sha(engine / f) != h:
            raise ValueError('audit dependency drift')
    import bt_driver_lib as DL
    for kind in ('U', 'R180'):
        for seed in (42, 2027):
            cell = B.R / f'cells/{kind}_s{seed}'
            tag = f'ADAPT_{kind}_s{seed}X_scaled_rule_raw_UAFE'
            cfg = cell / f'configs/RUN_CONFIG_ADAPT_{kind}_s{seed}X.json'
            validate_path_files(cell / 'runs' / tag, tag, B.sha(cfg), DL.audits_clean)


def main():
    if not __debug__:
        raise RuntimeError('optimized assertions forbidden')
    old = Path(B.C['continuation_old_root'])
    if B.C['deadline_epoch'] != json.loads((old.with_name(old.name + '_sources') / 'CONTRACT.json').read_text())['deadline_epoch']:
        raise ValueError('deadline extension forbidden')
    for n, h in B.C['copied_sources'].items():
        if B.sha(B.H / n) != h:
            raise ValueError('continuation source drift: ' + n)
    check_parent(old, B.C['failed_terminal_sha256'])
    from control_binding import verify_controls
    controls = verify_controls(Path(B.C['parent_root']))
    B.R.mkdir(exist_ok=False)
    for n in ('logs', 'receipts', 'processes', 'steps', 'cells'):
        (B.R / n).mkdir()
    (B.R / 'models').symlink_to(old / 'models', target_is_directory=True)
    B.write('ENGINE_IDENTITIES.json', json.loads((old / 'ENGINE_IDENTITIES.json').read_text()))
    B.write('CONTINUATION_PREFLIGHT.json', {
        'old_root': str(old), 'old_terminal_sha256': B.C['failed_terminal_sha256'],
        'controls': controls, 'contract_sha256': B.sha(B.H / 'CONTRACT.json'),
        'source_sha256': B.sha(__file__), 'neural_training_repeated': False,
        'scheduler': 'one cell at a time; each unchanged config max_parallel=4',
        'deadline_epoch': B.C['deadline_epoch'], 'utc': time.strftime('%FT%TZ', time.gmtime())})
    # The same frozen run_batch guard is used with singleton launch groups.
    # U targets already exist. Preserve their configs and logs byte for byte.
    import alloc_chain_run as CH
    for seed in (42, 2027):
        cell = old / f'cells/U_s{seed}'
        cfg = cell / f'configs/RUN_CONFIG_ADAPT_U_s{seed}X.json'
        if B.sha(cfg) != B.C['u_config_sha256'][str(seed)]:
            raise ValueError('U execution config drift')
        (B.R / f'cells/U_s{seed}').symlink_to(cell, target_is_directory=True)
        gates = CH.engine_gate(str(cfg), poll=10, max_wait=max(1, B.C['deadline_epoch'] - time.time()))
        args = [B.PY, '-B', '/dev/shm/news2_2026-09-23/engine/bt_launch.py',
                'PATH,HOME,LC_CTYPE', str(cfg), '--resume', f'ADAPT_U_s{seed}X']
        B.wait([B.launch(f'resume_U_{seed}', args)])
        B.write(f'receipts/U_{seed}_RESUMED.json', {'config_sha256': B.sha(cfg), 'gates': gates,
            'source_target_root_unchanged': str(cell), 'engine_rc': 0})
    # Assemble and run the two missing cells with precisely the old sources.
    for seed in (42, 2027):
        args = [B.PY, '-B', str(B.H / 'alloc_chain_run.py'), 'PATH,HOME,LC_CTYPE',
                str(B.R / 'receipts'), '--seed', str(seed), '--rule', 'inservice',
                '--mix', 'shared', '--kind', 'R180', '--engine']
        B.wait([B.launch(f'R180_{seed}', args)])
    audit_cells()
    B.write('SIMULATION_TERMINAL.json', {'rc': 0, 'status': 'SIMULATIONS_AUDITED',
        'steps': B.STEPS, 'utc': time.strftime('%FT%TZ', time.gmtime()), 'previous_attempt_failed': str(old)})
    B.wait([B.launch('economic', [B.PY, '-B', str(B.H / 'economic_readout.py'),
           '--root', str(B.R), '--out', str(B.R / 'receipts/ECONOMIC_FULL_BOOK.json')])])
    from decision import decide
    B.write('receipts/BOOK_DECISION.json', decide(json.loads((B.R / 'receipts/ECONOMIC_FULL_BOOK.json').read_text())))
    if time.time() > B.C['deadline_epoch']:
        raise TimeoutError('original total budget exhausted')
    if controls != verify_controls(Path(B.C['parent_root'])):
        raise ValueError('control drift')
    for n, h in B.C['copied_sources'].items():
        if B.sha(B.H / n) != h:
            raise ValueError('source drift after run')


if __name__ == '__main__':
    rc, error = 1, None
    try:
        main(); rc = 0
    except BaseException as e:
        error = repr(e); traceback.print_exc()
    finally:
        B.stop_own()
        if B.R.exists():
            B.write('TERMINAL.json', {'rc': rc, 'status': 'CASH_CONTINUATION_COMPLETE_NOT_RELEASE' if rc == 0 else 'FAILED',
                'error': error, 'steps': B.STEPS, 'utc': time.strftime('%FT%TZ', time.gmtime()),
                'wall_seconds': time.monotonic() - B.START, 'training_repeated': False, 'production_changes': 0})
    raise SystemExit(rc)

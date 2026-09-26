#!/usr/bin/env python3
"""dlarch_f10full_launch.py -- the gate that certifies THE TRAINER THAT WILL RUN, then execs it.

WHY THIS EXISTS (measured 2026-09-26, not assumed):
`dlarch_t3_preflight.py` run against this arm's directory printed `all_ok=True n_paths=22` -- and its
receipt does not contain this directory's `dlarch_train_f10.py` at all. It checked
`/workspace/dlarch_2026-09-24/dlarch_train_f10.py` (4b74f2ce), the CANONICAL file, because the trainer
path it verifies is a KEY COPIED OUT OF A DELIVERED TRAIN_RECEIPT, not the file it was pointed at. So
pointing that device at any new arm directory certifies the wrong file and still says all_ok=True.
The preflight is pinned by a delivered receipt (receipts/T3_PREFLIGHT_2026-09-25.json), so its bytes
stay untouched and the gate moves here -- same shape as the news_p2_build wrapper (f406c901e).

CLASS SHAPE, not instance shape: this device does not hardcode "the f10full trainer". It asserts, for
whatever directory it is given, that
  (1) the trainer about to run hashes to the sha DECLARED on the command line (the prereg's pin), and
  (2) the preflight receipt either certified THAT VERY PATH, or the divergence is stated in this
      device's own receipt as an explicit, named residual -- it can never again be silent, and
  (3) the arm directory contains no .py file beyond the declared set, so a stray edited copy cannot
      be the thing that imports.
A green from this device is about the file that executes. It never trains and never deletes.

usage: dlarch_f10full_launch.py <env-whitelist> <arm-dir> <expect-trainer-sha256> <preflight.json>
                                <out-receipt.json> -- <trainer args ...>
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

WL = set(sys.argv[1].split(','))
SELF_SET = {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'}
_x = sorted(set(os.environ) - WL - SELF_SET)
assert not _x, f'env outside whitelist: {_x}'

ARM_DIR, EXPECT, PREFLIGHT, OUT = (pathlib.Path(sys.argv[2]), sys.argv[3],
                                   pathlib.Path(sys.argv[4]), pathlib.Path(sys.argv[5]))
assert sys.argv[6] == '--', 'trainer args must follow a bare --'
TRAINER_ARGS = sys.argv[7:]
assert len(EXPECT) == 64, 'the expected trainer sha must be the full 64 hex chars, not a prefix'

DECLARED_PY = {'dlarch_train_f10.py', 'dlarch_chain_torch.py', 'dlarch_safe_io.py'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(16 << 20), b''):
            h.update(b)
    return h.hexdigest()


trainer = ARM_DIR / 'dlarch_train_f10.py'
got = sha(trainer)
checks = []

# (1) the file that will execute hashes to the declared pin
checks.append({'check': 'trainer_sha_matches_declared_pin', 'path': str(trainer),
               'expected': EXPECT, 'got': got, 'pass': got == EXPECT})

# (2) did the preflight certify THIS path? Report the answer either way; never leave it implied.
pre = json.loads(PREFLIGHT.read_text())
pre_blob = json.dumps(pre)
pre_certified_this = str(trainer) in pre_blob
other_trainers = sorted({k for k in pre_blob.split('"')
                         if k.endswith('dlarch_train_f10.py') and k != str(trainer)})
checks.append({'check': 'preflight_certified_the_file_that_runs',
               'preflight': str(PREFLIGHT), 'preflight_all_ok': pre.get('all_ok'),
               'certified_this_path': pre_certified_this,
               'trainer_paths_it_DID_certify': other_trainers,
               'pass': True,      # informational by construction; (1) is the load-bearing gate
               'residual': None if pre_certified_this else (
                   'the preflight receipt certifies ' + ', '.join(other_trainers) + ' and NOT '
                   + str(trainer) + '. Its trainer path is copied from a delivered TRAIN_RECEIPT, so it '
                   'certifies the canonical file whatever directory it is pointed at. Coverage for the '
                   'file that runs comes from check (1) of this device, not from the preflight.')})

# (3) nothing else in the arm directory can be what imports
found_py = {p.name for p in ARM_DIR.glob('*.py')}
checks.append({'check': 'no_undeclared_py_in_arm_dir', 'declared': sorted(DECLARED_PY),
               'found': sorted(found_py), 'unexpected': sorted(found_py - DECLARED_PY),
               'missing': sorted(DECLARED_PY - found_py),
               'pass': found_py == DECLARED_PY})

# (4) the other two modules that the trainer imports from this directory, recorded by sha
mods = {n: sha(ARM_DIR / n) for n in sorted(DECLARED_PY) if (ARM_DIR / n).exists()}

rec = {'device': 'dlarch_f10full_launch.py', 'self_sha256': sha(os.path.abspath(__file__)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'arm_dir': str(ARM_DIR), 'trainer_args': TRAINER_ARGS,
       'arm_dir_module_sha256': mods, 'checks': checks,
       'ALL_GATES_PASS': all(c['pass'] for c in checks)}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(rec, indent=1, sort_keys=True))

for c in checks:
    print(('  PASS ' if c['pass'] else '  FAIL ') + c['check']
          + ('' if c.get('residual') is None else '\n        RESIDUAL: ' + c['residual']))
print('F10FULL_LAUNCH_GATE ALL_GATES_PASS=%s receipt=%s' % (rec['ALL_GATES_PASS'], OUT))
if not rec['ALL_GATES_PASS']:
    sys.exit('REFUSING TO TRAIN: a gate above is red')

os.execv(sys.executable, [sys.executable, str(trainer)] + TRAINER_ARGS)

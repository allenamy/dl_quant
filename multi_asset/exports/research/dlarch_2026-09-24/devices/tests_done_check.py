#!/usr/bin/env python3
"""tests_done_check.py -- the class test for lead item 6 ("existence read as completion" in the cell drivers).

Three parts, all must pass; the exit code is the verdict.
  A  BASELINE GREEN (run on pod2 with --baseline <W>): every delivered RETAIN directory under <W>/receipts
     must read COMPLETE, and the reference cell must read COMPLETE. A red here means the checker is wrong,
     not the data -- asserted first, because a checker that is red on everything would make every
     mutation below "pass" (baseline_green_assertion_catches_bugs_mutations_cannot).
  B  MUTATIONS (synthetic, in a temp dir): each shape a crashed / partial step can leave must read
     NOT_COMPLETE -- including the exact case the old `[ -d "$OUT" ]` accepted: the directory retain makes
     at its START, with nothing in it.
  C  STATIC, over every *.sh driver under this devices tree: (1) no completion target ($OUT, $REF) is
     tested with a bare -d / -f; (2) no failure marker contains a success marker as a substring (the old
     F10FULL_CELLS_DRIVER_DONE_WITH_MISSING matched any `grep F10FULL_CELLS_DRIVER_DONE`); (3) every
     retention call is followed by a done_check, so a failed retention cannot be counted as done.

usage: tests_done_check.py [--baseline <W>]
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DC = os.path.join(HERE, 'dlarch_done_check.py')
results = []


def check(name, ok, detail=''):
    results.append((name, bool(ok)))
    print(('  PASS ' if ok else '  FAIL ') + name + (f'  [{detail}]' if detail else ''))


def run(*a):
    cp = subprocess.run([sys.executable, '-B', DC, *a], capture_output=True, text=True)
    return cp.returncode, cp.stdout.strip()


# ── A. baseline ───────────────────────────────────────────────────────────────────────────────────
if '--baseline' in sys.argv:
    W = sys.argv[sys.argv.index('--baseline') + 1]
    dirs = sorted(d for d in glob.glob(f'{W}/receipts/RETAIN_*') if os.path.isdir(d))
    reds = [(d, run('retain', d, '--root', W)[1]) for d in dirs if run('retain', d, '--root', W)[0] != 0]
    check(f'A1 all {len(dirs)} delivered RETAIN dirs read COMPLETE', dirs and not reds, str(reds)[:300])
    ref = f'{W}/chain/ref_nc_s42X/runs/DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE'
    rc, out = run('cell', ref)
    check('A2 the reference cell reads COMPLETE', rc == 0, out)
    if not all(ok for _, ok in results):
        print('BASELINE RED -- the checker, not the data, is suspect; mutations below are not meaningful')
        sys.exit(1)

# ── B. mutations ─────────────────────────────────────────────────────────────────────────────────
with tempfile.TemporaryDirectory() as T:
    ser = os.path.join(T, 'SER_x.npz')
    open(ser, 'wb').write(b'series-bytes')
    good = {'ALL_PRECONDITIONS_PASS': True,
            'small_series': {'path': 'SER_x.npz', 'sha256': hashlib.sha256(b'series-bytes').hexdigest()}}

    def mk(name, body=None, raw=None, extra=0):
        d = os.path.join(T, name); os.makedirs(d)
        if raw is not None:
            open(os.path.join(d, 'RETAIN_a.json'), 'w').write(raw)
        elif body is not None:
            json.dump(body, open(os.path.join(d, 'RETAIN_a.json'), 'w'))
        for i in range(extra):
            json.dump(good, open(os.path.join(d, f'RETAIN_extra{i}.json'), 'w'))
        return d

    rc, out = run('retain', mk('ok', good), '--root', T)
    check('B0 a complete retention reads COMPLETE (relative small-series path resolved via --root)', rc == 0, out)
    rc, out = run('retain', mk('empty'), '--root', T)
    check('B1 the dir retain creates at START, still empty (what [ -d "$OUT" ] accepted) -> NOT_COMPLETE', rc == 1, out)
    rc, out = run('retain', mk('trunc', raw=json.dumps(good)[:25]), '--root', T)
    check('B2 truncated receipt -> NOT_COMPLETE', rc == 1, out)
    rc, out = run('retain', mk('prefail', {**good, 'ALL_PRECONDITIONS_PASS': False}), '--root', T)
    check('B3 preconditions failed -> NOT_COMPLETE', rc == 1, out)
    bad = json.loads(json.dumps(good)); bad['small_series']['sha256'] = '0' * 64
    rc, out = run('retain', mk('shamis', bad), '--root', T)
    check('B4 small-series sha mismatch -> NOT_COMPLETE', rc == 1, out)
    rc, out = run('retain', mk('two', good, extra=1), '--root', T)
    check('B5 two receipts in one dir -> NOT_COMPLETE', rc == 1, out)
    rc, out = run('retain', os.path.join(T, 'absent'), '--root', T)
    check('B6 no dir at all -> NOT_COMPLETE', rc == 1, out)
    for n, want in ((31, 1), (32, 0), (0, 1)):
        d = os.path.join(T, f'cell{n}'); os.makedirs(d)
        for i in range(n):
            open(os.path.join(d, f'PATH_{i:02d}.npz'), 'wb').close()
        open(os.path.join(d, 'AGG_x.npz'), 'wb').close()     # the aggregate must not be counted as a path
        rc, out = run('cell', d)
        check(f'B7 cell with {n} PATH npz (+1 AGG) -> {"COMPLETE" if want == 0 else "NOT_COMPLETE"}', rc == want, out)

# ── C. static, over every driver ─────────────────────────────────────────────────────────────────
drivers = sorted(glob.glob(os.path.join(HERE, '**', '*.sh'), recursive=True))
bare = []
for p in drivers:
    for i, ln in enumerate(open(p), 1):
        if re.search(r'\[\s*!?\s*-[def]\s+"\$(OUT|REF)"\s*\]', ln):
            bare.append(f'{os.path.relpath(p, HERE)}:{i}')
check(f'C1 no bare -d/-e/-f on a completion target ($OUT/$REF) in {len(drivers)} drivers', not bare, ', '.join(bare))
sub = []
for p in drivers:
    marks = set(re.findall(r'=== ([A-Z0-9_]+)', open(p).read()))
    ok_marks = {m for m in marks if m.endswith('_DONE')}
    for m in marks - ok_marks:
        for o in ok_marks:
            if o in m:
                sub.append(f'{os.path.relpath(p, HERE)}: {m} contains {o}')
check('C2 no failure marker contains a success marker as a substring', not sub, ', '.join(sub))
unchecked = []
for p in drivers:
    txt = open(p).read()
    for m in re.finditer(r'dlarch_cell_retain\.py', txt):
        tail = txt[m.end():m.end() + 1500]
        nxt = tail.find('dlarch_cell_retain.py')
        window = tail if nxt < 0 else tail[:nxt]
        if 'retain "$OUT"' not in window:
            unchecked.append(os.path.relpath(p, HERE))
check('C3 every retention call is followed by a content done_check', not unchecked, ', '.join(unchecked))

n_fail = sum(1 for _, ok in results if not ok)
print('TESTS_DONE_CHECK %s %d/%d' % ('PASS' if n_fail == 0 else 'FAIL', len(results) - n_fail, len(results)))
sys.exit(1 if n_fail else 0)

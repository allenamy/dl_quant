#!/usr/bin/env python3
"""Make --train-arm's validity DERIVED instead of a literal whitelist.

WHY: the list ("T0", "T3_clamp") has to be edited for every new arm, and the F10_FULL arm
(G1_T0_nomask_frac1) is the second time in two days that a new arm hit it. The list's real job is to
stop a TYPO from silently building a cell from a path that does not exist -- that job is done better by
requiring the arm's own TRAIN_RECEIPT.json to be there, which a typo can never satisfy. So the check
becomes class-shaped: tomorrow's arm needs no edit, and a misspelling still fails loudly and BY NAME.
Also fixes the `label` expression, which hardcoded "s<seed>" for T0 and "<arm>_s<seed>" otherwise -- with
a third arm that would have produced a cell named G1_T0_nomask_frac1_s42 for T0-family-looking output
while the arm is NOT T0; the name now always carries the arm unless the arm IS plain T0.
"""
import pathlib
import sys

P = pathlib.Path('/workspace/dlarch_2026-09-24/dlarch_chain_run.py')
s = P.read_text()
orig = s

OLD = '''    assert train_arm in ("T0", "T3_clamp"), f"unknown train arm {train_arm}"'''
NEW = '''    # DERIVED, not a literal list: an arm is valid iff the training it names actually produced a receipt
    # at the path this cell would read. A typo cannot satisfy that, so it still fails loudly and by name;
    # a NEW arm needs no edit here. (The literal list ("T0","T3_clamp") had to be edited for every arm,
    # and F10_FULL's G1_T0_nomask_frac1 was the second such edit in two days.)
    _cand = f"{BASE}/T3/{train_arm}/f10_s{seed}/TRAIN_RECEIPT.json"
    if not (parity or reference):
        assert os.path.isfile(_cand), (
            f"unknown train arm {train_arm!r}: no training receipt at {_cand}. "
            f"arms that HAVE a receipt for seed {seed}: "
            + ", ".join(sorted(os.path.basename(os.path.dirname(os.path.dirname(p)))
                               for p in glob.glob(f"{BASE}/T3/*/f10_s{seed}/TRAIN_RECEIPT.json")) or ["none"]))'''
assert s.count(OLD) == 1, 'the train_arm assert is not unique'
s = s.replace(OLD, NEW, 1)

OLDL = '''    label = "parity" if parity else (f"ref_nc_s{seed}X" if reference else f"{'s' if train_arm == 'T0' else train_arm + '_s'}{seed}")'''
NEWL = '''    label = "parity" if parity else (f"ref_nc_s{seed}X" if reference
                                     else (f"s{seed}" if train_arm == "T0" else f"{train_arm}_s{seed}"))'''
assert s.count(OLDL) == 1, 'the label expression is not unique'
s = s.replace(OLDL, NEWL, 1)

if 'import glob' not in s:
    # needed by the derived check's "arms that HAVE a receipt" list
    assert s.count('import os') >= 1
    i = s.index('\n', s.index('import os'))
    s = s[:i] + '\nimport glob' + s[i:]

assert s != orig
P.write_text(s)
print('PATCHED_OK')

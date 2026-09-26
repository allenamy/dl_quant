#!/usr/bin/env python3
"""dlarch_done_check.py -- the ONE place the cell drivers ask "is this step COMPLETE?", instead of asking
the shell "does this path exist?".

WHY (lead item 6, 2026-09-26). The three cell drivers skipped retention with `[ -d "$OUT" ]`. dlarch first
reported that as a wrong test operator ("-d on a .json path never fires") -- that was WRONG and is
retracted: dlarch_cell_retain.py treats --out as a DIRECTORY (os.makedirs, L104), so -d is the right
operator and the skip does fire. The real defect is one level up and is class-shaped: EXISTENCE WAS READ
AS COMPLETION. retain makes the directory at its START, so a retention that crashed after makedirs leaves
a directory that every later driver run reads as "already retained" and skips forever -- and the seed then
has no receipt while the driver still prints "all cells done". The same shape sits in `[ -d "$REF" ]`
(a reference cell directory exists from the moment chain_run creates it, long before its engine has
written 32 PATH files) and in the unchecked retention rc.

So completion is decided HERE, from the artefact's own content, never from a path's existence:
  retain <dir>   exactly one RETAIN_*.json that parses, ALL_PRECONDITIONS_PASS is True, and its recorded
                 small-series sha equals the file's sha (relative paths resolved against --root)
  cell <rundir>  exactly 32 PATH*.npz (the engine's own expected count, chain_run L444)
Exit 0 = complete; 1 = NOT complete (reason printed); 2 = usage. A driver that gets 1 must neither skip
nor count the step as done.

usage: dlarch_done_check.py retain <dir> [--root <W>]
       dlarch_done_check.py cell <rundir>
"""
import glob
import hashlib
import json
import os
import sys

N_PATHS = 32


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def retain(d, root):
    if not os.path.isdir(d):
        return False, f'no retention directory at {d}'
    fs = glob.glob(os.path.join(d, 'RETAIN_*.json'))
    if len(fs) != 1:
        return False, f'{len(fs)} RETAIN_*.json in {d} (need exactly 1)'
    try:
        r = json.load(open(fs[0]))
    except Exception as e:                                  # noqa: BLE001 -- the reason IS the output
        return False, f'receipt does not parse: {fs[0]}: {type(e).__name__}: {e}'
    if r.get('ALL_PRECONDITIONS_PASS') is not True:
        return False, f'ALL_PRECONDITIONS_PASS={r.get("ALL_PRECONDITIONS_PASS")!r}'
    ss = r.get('small_series') or {}
    p = ss.get('path', '')
    p = p if os.path.isabs(p) else os.path.join(root, p)
    if not os.path.exists(p):
        return False, f'small series missing at {p}'
    if sha(p) != ss.get('sha256'):
        return False, 'small series sha does not match the receipt'
    return True, f'complete: {os.path.basename(fs[0])}'


def cell(d):
    if not os.path.isdir(d):
        return False, f'no run directory at {d}'
    n = len(glob.glob(os.path.join(d, 'PATH*.npz')))
    return (n == N_PATHS), f'{n} PATH*.npz (need {N_PATHS})'


def main(argv):
    if len(argv) < 3 or argv[1] not in ('retain', 'cell'):
        print(__doc__.split('usage:')[1]); return 2
    root = argv[argv.index('--root') + 1] if '--root' in argv else os.getcwd()
    ok, why = retain(argv[2], root) if argv[1] == 'retain' else cell(argv[2])
    print(('DONE_CHECK COMPLETE ' if ok else 'DONE_CHECK NOT_COMPLETE ') + f'{argv[1]} {argv[2]}: {why}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))

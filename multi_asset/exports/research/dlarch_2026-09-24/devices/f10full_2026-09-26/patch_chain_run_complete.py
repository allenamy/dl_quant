#!/usr/bin/env python3
"""Add the COMPLETENESS half of the --train-arm check.

File existence is not completeness: merge_folds writes TRAIN_RECEIPT.json after EVERY fold, so the file
is present from fold 1 with status PARTIAL_FOLDS. Measured: the F10_FULL arm's receipt existed at 15/23
folds. Accepting it would build a book cell from a partially trained arm and give it a finished cell's
name -- a hole the literal whitelist also had, and one my derived check would otherwise have introduced.
"""
import pathlib
import sys

P = pathlib.Path('/workspace/dlarch_2026-09-24/dlarch_chain_run.py')
s = P.read_text()

OLD = """    if not (parity or reference):
        assert os.path.isfile(_cand), ("""
NEW = """    if not (parity or reference):
        # FILE EXISTENCE IS NOT COMPLETENESS. merge_folds writes TRAIN_RECEIPT.json after EVERY fold, so
        # this file is present from fold 1 with status PARTIAL_FOLDS (measured: the F10_FULL arm had one
        # at 15/23). Accepting it would build a book cell from a partially trained arm and label it like
        # a finished one -- a hole the literal whitelist also had. Both halves are checked below and the
        # refusal says WHICH one failed.
        assert os.path.isfile(_cand), ("""
if s.count(OLD) != 1:
    sys.exit('ABORT: existence-assert preamble not unique (%d)' % s.count(OLD))
s = s.replace(OLD, NEW, 1)

OLD2 = ('                               for p in glob.glob(f"{BASE}/T3/*/f10_s{seed}/TRAIN_RECEIPT.json"))'
        ' or ["none"]))')
NEW2 = OLD2 + """
        _st = json.load(open(_cand))
        assert _st.get("status") == "ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED", (
            f"train arm {train_arm!r} seed {seed} is NOT finished: status={_st.get('status')!r} with "
            f"{len(_st.get('folds') or [])} folds recorded. Refusing to build a book cell from a partial "
            f"training run -- it would carry a finished cell's name.")"""
if s.count(OLD2) != 1:
    sys.exit('ABORT: glob line not unique (%d)' % s.count(OLD2))
s = s.replace(OLD2, NEW2, 1)

P.write_text(s)
print('PATCHED_OK completeness check added')

"""Execute the real main() header gate, not a duplicate acceptance list."""
import ast
from pathlib import Path
import unittest

def gate(record, expected='abc'):
    tree=ast.parse(Path(__file__).with_name('alloc_combo.py').read_text())
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    node=next(n for n in ast.walk(main) if isinstance(n,ast.Assert) and "rec['status']" in ast.unparse(n))
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<real-main-header>','exec'),
         {'rec':record,'ident':{'/score':expected},'paths':[None,None,None,Path('/score')]})

class HeaderTest(unittest.TestCase):
    def test_horizon_training_complete_accepts(self):
        gate({'status':'HORIZON_LINEAR_FOLDS_COMPLETE_NOT_COMBO_CERTIFIED','pred_sha256':'abc'})

    def test_unknown_status_and_changed_scores_refuse(self):
        with self.assertRaises(AssertionError):gate({'status':'RUNNING','pred_sha256':'abc'})
        with self.assertRaises(AssertionError):gate({'status':'HORIZON_LINEAR_FOLDS_COMPLETE_NOT_COMBO_CERTIFIED','pred_sha256':'other'})

    def test_existing_f10_control_unchanged(self):
        gate({'status':'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED','pred_sha256':'abc'})

if __name__=='__main__':unittest.main()

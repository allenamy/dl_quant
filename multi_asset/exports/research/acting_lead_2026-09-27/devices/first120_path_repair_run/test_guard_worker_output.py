"""Reject a duplicated output-path contract before numerical worker entry."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import funding_first120_forward_guard as guard

class OutputContract(unittest.TestCase):
    def test_frozen_outputs_agree(self):
        p=Path(guard.__file__).parent/'funding_first120_forward.py'
        spec=importlib.util.spec_from_file_location('frozen_worker_output_test',p)
        w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
        self.assertEqual(guard.OUTPUT,w.OUTPUT)

    def test_mismatch_rejected_before_worker(self):
        old_root,old_output=guard.ROOT,guard.OUTPUT
        try:
            with tempfile.TemporaryDirectory() as td:
                guard.ROOT=Path(td);guard.OUTPUT=Path(td)/'expected'
                p=guard.ROOT/'funding_first120_forward.py'
                p.write_text("from pathlib import Path\nOUTPUT=Path('/wrong')\n")
                with self.assertRaisesRegex(ValueError,'output mismatch'):
                    guard.verify_worker_output()
                p.write_text("from pathlib import Path\nOUTPUT=Path("+repr(str(guard.OUTPUT))+")\n")
                self.assertEqual(guard.verify_worker_output(),str(p.resolve()))
        finally:
            guard.ROOT,guard.OUTPUT=old_root,old_output

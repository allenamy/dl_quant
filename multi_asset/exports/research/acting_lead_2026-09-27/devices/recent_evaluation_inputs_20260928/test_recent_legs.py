import unittest
import numpy as np
from recent_legs import seed_history, require_boundary, extract_loop,same_values_as_schema


class Controls(unittest.TestCase):
    def test_symbol_schema_preserves_identity(self):
        f={'symbols':np.array(['BTCUSDT','ETHUSDT'])}
        out=same_values_as_schema(f,{'symbols':np.dtype('<U15')})
        self.assertTrue(np.array_equal(out['symbols'],f['symbols']))
    def test_original_merged_arithmetic_dtype_preserved(self):
        f={'qvm':np.array([13.51],np.float32)}
        out=same_values_as_schema(f,{'qvm':np.dtype('float64')})
        self.assertEqual(out['qvm'].dtype,np.dtype('float64'))
        self.assertTrue(np.array_equal(out['qvm'],f['qvm']))

    def test_lossy_cast_refused(self):
        with self.assertRaises(ValueError):same_values_as_schema({'v':np.array([1.000000001])},{'v':np.dtype('float16')})
    def test_history_preserves_observed_order_and_zero(self):
        x=np.array([[np.nan]*3,[0.,2.,3.],[1.,4.,5.],[np.nan]*3])
        h=seed_history(x)
        self.assertEqual(h,dict(king=[0.,1.],rev24=[2.,4.],fund=[3.,5.]))

    def test_partial_unknown_rejected(self):
        with self.assertRaises(ValueError):seed_history(np.array([[1.,np.nan,3.]]))

    def test_inf_rejected(self):
        with self.assertRaises(ValueError):seed_history(np.array([[np.inf]*3]))

    def test_unclosed_tail_rejected(self):
        with self.assertRaises(ValueError):seed_history(np.array([[1.,2.,3.]]))

    def test_boundary_cannot_shift(self):
        with self.assertRaises(ValueError):require_boundary(np.array([0,14400]),np.array([28800,43200]))

    def test_boundary_cannot_skip(self):
        with self.assertRaises(ValueError):require_boundary(np.array([0,14400]),np.array([14400,43200]))

    def test_exact_boundary(self):
        require_boundary(np.array([0,14400]),np.array([14400,28800]))

    def test_only_original_loop_executes(self):
        src='def main():\n    forbidden()\n    for i in range(n):\n        out.append(i)\n    forbidden()\n'
        ns={'n':3,'out':[]};exec(extract_loop(src),ns);self.assertEqual(ns['out'],[0,1,2])

    def test_ambiguous_loop_refused(self):
        src='def main():\n    for i in range(n):\n        pass\n    for i in range(n):\n        pass\n'
        with self.assertRaises(ValueError):extract_loop(src)

if __name__=='__main__':unittest.main()

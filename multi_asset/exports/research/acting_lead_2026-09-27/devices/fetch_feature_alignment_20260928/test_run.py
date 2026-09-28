import unittest
import numpy as np
from run import selected_fetch,history_asof,ranks_equal
class Controls(unittest.TestCase):
    def test_exact_fetch(self):self.assertEqual(selected_fetch({'last_anchor':4,'fetch_syms':['A']},4,['A','B'])[1].tolist(),[True,False])
    def test_missing_refused(self):
        with self.assertRaises(ValueError):selected_fetch({'last_anchor':4},4,['A'])
    def test_future_refused(self):
        with self.assertRaises(ValueError):selected_fetch({'last_anchor':5,'fetch_syms':['A']},4,['A'])
    def test_unknown_refused(self):
        with self.assertRaises(ValueError):selected_fetch({'last_anchor':4,'fetch_syms':['Z']},4,['A'])
    def test_duplicate_refused(self):
        with self.assertRaises(ValueError):selected_fetch({'last_anchor':4,'fetch_syms':['A','A']},4,['A'])
    def test_backfill_unknown_refused(self):
        with self.assertRaises(ValueError):selected_fetch({'last_anchor':4,'fetch_syms':['A'],'nc_backfill_residual':['A']},4,['A'])
    def test_future_history_excluded(self):
        h={1:np.array([0]),2:np.array([1]),3:np.array([2])};self.assertEqual(list(history_asof(h,2)),[1,2]);a=history_asof(h,2);a[2][0]=7;self.assertEqual(h[2][0],1)
    def test_missing_history_refused(self):
        with self.assertRaises(ValueError):history_asof({},2)
    def test_small_score_reorder_refused(self):self.assertFalse(ranks_equal([0.,1e-10],[1e-10,0.]))
    def test_same_ranks(self):self.assertTrue(ranks_equal([0.,1.],[.01,.99]))
    def test_nan_refused(self):
        with self.assertRaises(ValueError):ranks_equal([np.nan],[0.])
    def test_tie_difference_refused(self):self.assertFalse(ranks_equal([0.,0.],[0.,1e-10]))
if __name__=='__main__':unittest.main()

import unittest
import numpy as np
from alignment import axes, sparse, compare, seat, model_status, check_anchor, raw_from_states

class AlignmentTests(unittest.TestCase):
    def test_axis_permutation_refused(self):
        with self.assertRaises(ValueError): axes(['A','B'],['B','A'])
    def test_axis_duplicates_refused(self):
        with self.assertRaises(ValueError): axes(['A','A'],['A','A'])
    def test_sparse_duplicate_refused(self):
        with self.assertRaises(ValueError): sparse([0,0],[1,2],2)
    def test_sparse_unknown_refused(self):
        with self.assertRaises(ValueError): sparse([2],[1],2)
    def test_sparse_nan_refused(self):
        with self.assertRaises(ValueError): sparse([0],[np.nan],2)
    def test_noninteger_index_refused(self):
        with self.assertRaises(ValueError): sparse([0.5],[1],2)
    def test_missing_name_is_counted(self):
        r=compare(sparse([0],[.1],2),sparse([1],[.1],2))
        self.assertEqual(r['n_different'],2); self.assertAlmostEqual(r['l1'],.2)
    def test_f32_rounding_separate(self):
        a=np.array([.1],float); b=a.astype(np.float32)
        r=compare(a,b);self.assertFalse(r['exact']);self.assertTrue(r['equal_after_f32_cast'])
    def test_comparison_nan_refused(self):
        with self.assertRaises(ValueError):compare([0],[np.nan])
    def test_anchor_mismatch_refused(self):
        with self.assertRaises(ValueError):check_anchor({'anchor_ts':14400},28800)
    def test_model_mismatch_separate(self):
        self.assertEqual(model_status({'booster_sha':'other','f10_sha':'b'},'a','b'),'DIFFERENT_MODEL')
    def test_missing_identity_unavailable(self):
        self.assertEqual(model_status({'booster_sha':'a'},'a','b'),'UNAVAILABLE_MODEL_IDENTITY')
    def test_seat_warmup_and_mask(self):
        w,m=seat({'king':[1,2],'rev24':[0,0],'fund':[0,0]},2)
        np.testing.assert_array_equal(w,[1,0,0]);np.testing.assert_array_equal(m,[1,0,0])
        w,m=seat({'king':[],'rev24':[],'fund':[]},2)
        np.testing.assert_allclose(m,[.5,0,.5])
    def test_seat_bad_population_refused(self):
        with self.assertRaises(ValueError):seat({'king':[1],'rev24':[],'fund':[]},2)
    def test_raw_not_reshape(self):
        raw=raw_from_states(np.array([.2,-.1]),np.array([.4,-.1]))
        np.testing.assert_allclose(raw,[.29,-.1]);self.assertNotEqual(float(raw.sum()),0)

if __name__=='__main__':unittest.main()

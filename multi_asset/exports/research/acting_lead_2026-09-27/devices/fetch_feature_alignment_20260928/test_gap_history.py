import unittest
import numpy as np
from gap_history import GAPS,remove_observed_holes

class HistoryControls(unittest.TestCase):
    def base(self):return {a:np.array([1,2]) for a in range(1790409600,1790524801,14400)}
    def test_before_gap_unchanged(self):
        h=self.base();out,removed=remove_observed_holes(h,1790409600)
        self.assertEqual(list(out),[1790409600]);self.assertEqual(removed,[])
    def test_only_elapsed_known_gaps(self):
        h=self.base();out,removed=remove_observed_holes(h,1790452800)
        self.assertEqual(removed,[1790424000,1790438400]);self.assertIn(1790452800,out);self.assertNotIn(1790481600,out);self.assertEqual(len(h),9)
    def test_all_three(self):
        h=self.base();out,removed=remove_observed_holes(h,1790524800)
        self.assertEqual(set(removed),GAPS);self.assertEqual(set(out),set(h)-GAPS)
    def test_control_already_missing_refused(self):
        h=self.base();del h[1790424000]
        with self.assertRaises(ValueError):remove_observed_holes(h,1790452800)
    def test_current_hole_refused(self):
        with self.assertRaises(ValueError):remove_observed_holes(self.base(),1790424000)
    def test_future_data_irrelevant(self):
        h=self.base();a=1790452800;out,_=remove_observed_holes(h,a);h[1790524800][:]=999;new,_=remove_observed_holes(h,a)
        for k in out:np.testing.assert_array_equal(out[k],new[k])

if __name__=='__main__':unittest.main()

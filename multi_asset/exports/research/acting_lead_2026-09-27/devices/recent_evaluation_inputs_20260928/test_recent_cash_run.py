import unittest
import numpy as np
from recent_cash_run import prefix_check,patch_ua_count

class Controls(unittest.TestCase):
    def test_exact_prefix(self):
        a={'A':np.array([0,14400]),'x':np.array([2.,np.nan]),'nav5_t0':np.array(0),'nav5_main':np.array([1.,2.,3.])}
        b={'A':np.array([0,14400,28800]),'x':np.array([2.,np.nan,4.]),'nav5_t0':np.array(0),'nav5_main':np.array([1.,2.,3.,4.])}
        self.assertEqual(prefix_check(a,b)['fields'],4)
    def test_changed_value_rejected(self):
        with self.assertRaisesRegex(ValueError,'x'):prefix_check({'A':np.array([0]),'x':np.array([1.])},{'A':np.array([0,14400]),'x':np.array([1.01,2.])})
    def test_missing_field(self):
        with self.assertRaises(ValueError):prefix_check({'A':np.array([0]),'x':np.array([1.])},{'A':np.array([0,14400])})
    def test_moved_time(self):
        with self.assertRaises(ValueError):prefix_check({'A':np.array([0])},{'A':np.array([14400])})
    def test_nonliteral_patch_refused(self):
        with self.assertRaises(ValueError):patch_ua_count('want_n={}',25)
    def test_patch_only_literal(self):
        s='    want_n = {"UNAVAILABLE_3084": 3084, "OLD_ZERO_PRICED_INLIFE_NAN": 24397}\n    used = []'
        self.assertEqual(patch_ua_count(s,4000),s.replace(': 3084,',': 4000,'))

if __name__=='__main__':unittest.main()

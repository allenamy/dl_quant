import unittest
import numpy as np
from recent_cash_readout import complete_days, per_name_cash

class Controls(unittest.TestCase):
    def test_days_compound(self):
        d,r=complete_days(np.arange(12)*14400,np.ones(12)*.01);np.testing.assert_allclose(r,(1.01**6-1));self.assertEqual(d.tolist(),[0,86400])
    def test_gap_refused(self):
        with self.assertRaises(ValueError):complete_days(np.array([0,14400,43200,57600,72000]),np.zeros(5))
    def test_duplicate_refused(self):
        with self.assertRaises(ValueError):complete_days(np.array([0,0,14400,28800,43200,57600,72000]),np.zeros(7))
    def test_nan_refused(self):
        with self.assertRaises(ValueError):complete_days(np.arange(6)*14400,np.r_[np.nan,np.zeros(5)])
    def test_per_name_identity(self):
        r=per_name_cash(np.array([100.,-50.]),np.array([125.,-60.]),np.array([20.,-5.]),np.array([1.,-2.]),np.array([.1,.2]));np.testing.assert_allclose(r['price'],[5,-5]);np.testing.assert_allclose(r['net'],[5.9,-7.2])
    def test_unknown_not_zero(self):
        with self.assertRaises(ValueError):per_name_cash(np.array([np.nan]),np.array([1.]),np.array([0.]),np.array([0.]),np.array([0.]))

if __name__=='__main__':unittest.main()

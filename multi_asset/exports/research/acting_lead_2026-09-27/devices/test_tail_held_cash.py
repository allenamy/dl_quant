import unittest
import numpy as np
from tail_held_cash import bins,group_cash,align

class Contract(unittest.TestCase):
 def test_equal_probabilities_not_split_by_name(self):
  np.testing.assert_array_equal(bins(np.ones(10)*.05),np.full(10,2))
 def test_missing_is_own_bin(self):
  self.assertEqual(bins(np.array([.1,.2,np.nan]))[-1],5)
 def test_increasing_probability_order(self):
  np.testing.assert_array_equal(bins(np.arange(10)/10),np.repeat(np.arange(5),2))
 def test_probability_outside_range(self):
  with self.assertRaises(ValueError):bins(np.array([.1,1.1]))
 def test_no_nearest_time(self):
  with self.assertRaises(ValueError):align(np.array([0,28800]),np.array([14400]))
 def test_noninteger_time(self):
  with self.assertRaises(ValueError):align(np.array([0.,14400.5]),np.array([0]))
 def fixture(self):
  return dict(groups=np.array([[0,1,5]]),mv=np.array([[100.,-200.,0.]]),price=np.array([[-10.,20.,-3.]]),fund=np.array([[1.,-2.,0.]]),fee=np.array([[.1,.2,.3]]),nav=np.array([1000.]))
 def test_flat_cash_retained(self):
  r=group_cash(**self.fixture());self.assertIsInstance(r,list);self.assertEqual(r[5]['price_usd'],-3.);self.assertEqual(r[5]['gross_usd_sum'],0.)
 def test_positive_negative_not_netted(self):
  p=self.fixture();p['groups'][:]=0;r=group_cash(**p);self.assertIsInstance(r,list);self.assertEqual(r[0]['price_loss_usd'],13.);self.assertEqual(r[0]['price_gain_usd'],20.);self.assertEqual(r[0]['price_usd'],7.)
 def test_nav_denominator(self):
  r=group_cash(**self.fixture());self.assertIsInstance(r,list);self.assertAlmostEqual(r[0]['price_anchor_bps'][0],-100.)
 def test_nonfinite_refused(self):
  p=self.fixture();p['price'][0,1]=np.nan
  with self.assertRaises(ValueError):group_cash(**p)
 def test_negative_nav_refused(self):
  p=self.fixture();p['nav'][:]=-1
  with self.assertRaises(ValueError):group_cash(**p)
 def test_unrecognized_group_refused(self):
  p=self.fixture();p['groups'][0,1]=18
  with self.assertRaises(ValueError):group_cash(**p)

if __name__=='__main__':unittest.main()

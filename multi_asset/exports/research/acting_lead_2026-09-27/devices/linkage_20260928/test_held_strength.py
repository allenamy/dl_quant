import unittest
import numpy as np
from held_strength import align, partition, aggregate, rank_delta

class Controls(unittest.TestCase):
 def test_exact_axis(self):
  np.testing.assert_array_equal(align(np.array([0,14400,28800]),np.array([14400,28800])),[1,2])
 def test_missing_axis(self):
  with self.assertRaises(ValueError):align(np.array([0,28800]),np.array([14400]))
 def test_fractional_axis(self):
  with self.assertRaises(ValueError):align(np.array([0.,14400.5]),np.array([0]))
 def test_unknown_distinct(self):
  p=partition(np.array([[1.,np.nan,-1,0]]),np.array([[1,1,-1,-1.]]))
  np.testing.assert_array_equal(p,[[3,4,0,2]])
 def test_rank_shift(self):
  d=rank_delta(np.array([0.,1,2]),np.array([1.,0,2]))
  np.testing.assert_allclose(d,[.5,-.5,0])
 def test_missing_rank(self):
  with self.assertRaises(ValueError):rank_delta(np.array([0.,np.nan]),np.array([1.,0]))
 def test_all_cash_included(self):
  p=np.array([[2.,-5.,7.]])
  q=np.array([[1.,-1.,0.]])
  r=aggregate(p,p*0,p*0,np.array([[10.,-20.,0.]]),np.array([100.]),q,np.array([[1.,-1.,0.]]),np.array([[0,1,4]]),5)
  self.assertEqual(sum(x['price_usd'] for x in r),4)
  self.assertEqual(r[4]['price_usd'],7)
 def test_missing_cash_refused(self):
  with self.assertRaises(ValueError):aggregate(np.array([[np.nan]]),np.zeros((1,1)),np.zeros((1,1)),np.zeros((1,1)),np.array([100.]),np.zeros((1,1)),np.zeros((1,1)),np.zeros((1,1),int),1)
 def test_partition_hole_refused(self):
  with self.assertRaises(ValueError):aggregate(np.ones((1,1)),np.zeros((1,1)),np.zeros((1,1)),np.zeros((1,1)),np.array([100.]),np.zeros((1,1)),np.zeros((1,1)),np.array([[-1]]),1)

if __name__=='__main__':unittest.main()

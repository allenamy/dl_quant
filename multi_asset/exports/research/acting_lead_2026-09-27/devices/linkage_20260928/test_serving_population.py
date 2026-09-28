import unittest
import numpy as np
from serving_population import support, compare

class Tests(unittest.TestCase):
 def test_40_days_midnight(self):
  a=14400*600;ts=np.arange(a-11519*300,a+1,300,dtype=np.int64)
  self.assertEqual(support(ts,a)['closed_before_day'],238)
 def test_40_days_08(self):
  a=14400*600+28800;ts=np.arange(a-11519*300,a+1,300,dtype=np.int64)
  self.assertEqual(support(ts,a//86400*86400)['closed_before_day'],236)
 def test_gap(self):
  with self.assertRaises(ValueError):support(np.array([0,300,900]),0)
 def test_unknown_not_zero(self):
  r=compare(np.array([0.,np.nan,1]),np.array([np.nan,0.,2]),np.array([True,True,True]))
  self.assertEqual(r['left_only'],1);self.assertEqual(r['right_only'],1);self.assertEqual(r['common'],1);self.assertEqual(r['changed'],1)
 def test_wrong_scope(self):
  with self.assertRaises(ValueError):compare(np.array([1]),np.array([1]),np.array([1]))
if __name__=='__main__':unittest.main()

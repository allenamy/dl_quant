import unittest
import numpy as np
from tail import contributions
class TailTests(unittest.TestCase):
 def test_additivity(self):
  a=np.array([3.,2,1,4]);b=np.array([1.,2,3,4]);y=np.array([-.1,-.01,.02,.3]);d,ic,n=contributions(a,b,y)
  self.assertEqual(sum(n),4);self.assertAlmostEqual(ic.sum(),.8);self.assertTrue(np.isfinite(d).all())
 def test_return_magnitude_not_rank(self):
  a=np.arange(40.);b=a[::-1].copy();y=np.arange(40.)/1000
  d,ic,n=contributions(a,b,y);y[-1]=100;d2,ic2,n2=contributions(a,b,y)
  np.testing.assert_array_equal(ic,ic2);self.assertNotEqual(d.sum(),d2.sum())
 def test_same_score_zero(self):
  a=np.arange(40.);d,ic,n=contributions(a,a,np.sin(a));np.testing.assert_array_equal(d,np.zeros(3));np.testing.assert_array_equal(ic,np.zeros(3))
 def test_unknown_refused(self):
  a=np.arange(20.);y=a.copy();y[1]=np.nan
  with self.assertRaises(ValueError):contributions(a,a,y)
 def test_constant_refused(self):
  a=np.arange(20.)
  with self.assertRaises(ValueError):contributions(a,a,np.ones(20))
if __name__=='__main__':unittest.main()

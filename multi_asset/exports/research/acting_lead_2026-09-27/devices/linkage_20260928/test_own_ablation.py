import unittest
import numpy as np
from own_ablation import own_designs

class Designs(unittest.TestCase):
 def test_dimensions_order_and_unknown_flag(self):
  x=np.ones((3,78));o=np.ones((3,8));o[0,2]=np.nan
  ds=own_designs(x,o)
  self.assertEqual([d.shape[1] for d in ds],[78,84,88,92,94])
  self.assertEqual(ds[1][0,78],0);self.assertEqual(ds[1][0,82],0)
  for d in ds[1:]:np.testing.assert_array_equal(d[:,:76],x[:,:76])
 def test_later_flow_not_in_fund_or_price(self):
  x=np.ones((3,78));o=np.ones((3,8));a=own_designs(x,o);o[:,6:]+=5;b=own_designs(x,o)
  for j in [0,1,2]:np.testing.assert_array_equal(a[j],b[j])
  self.assertFalse(np.array_equal(a[3],b[3]))
 def test_unknown_interaction_not_zero_fact(self):
  x=np.ones((3,78));o=np.ones((3,8));o[0,4]=np.nan;d=own_designs(x,o)[-1]
  np.testing.assert_array_equal(d[0,-2:],[0,0]);np.testing.assert_array_equal(d[1,-2:],[1,1])
 def test_no_infinite_input(self):
  x=np.ones((3,78));o=np.ones((3,8));o[0,4]=np.inf
  with self.assertRaises(ValueError):own_designs(x,o)

if __name__=='__main__':unittest.main()

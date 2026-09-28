import unittest
import numpy as np
from flow_ridge import add_own_interaction

class Controls(unittest.TestCase):
 def test_own_product_in_both_baselines(self):
  own=np.ones((2,8));own[:,3]=[.01,.02];own[:,4]=[3,-1]
  x=add_own_interaction(np.ones((2,100)),own)
  np.testing.assert_allclose(x[:,-2],[.03,-.02]);np.testing.assert_array_equal(x[:,-1],1);self.assertEqual(x.shape,(2,102))
 def test_unknown_product_explicit(self):
  own=np.ones((2,8));own[0,4]=np.nan;x=add_own_interaction(np.ones((2,100)),own)
  np.testing.assert_array_equal(x[0,-2:],[0,0])

if __name__=='__main__':unittest.main()

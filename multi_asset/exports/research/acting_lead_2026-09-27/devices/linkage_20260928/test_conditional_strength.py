import unittest
import numpy as np
from conditional_strength import score_ranks, conditional_design

class Conditional(unittest.TestCase):
 def test_scores_unknown_not_zero(self):
  v=score_ranks(np.array([4.,1.,np.nan,2.]));self.assertTrue(np.isnan(v[2]));np.testing.assert_array_equal(v[[0,1,3]],[.5,-.5,0])
 def test_design_own_only(self):
  x=np.ones((3,78));o=np.ones((3,8));s=np.ones((3,2));b,e=conditional_design(x,o,s);self.assertEqual(b.shape,(3,86));self.assertEqual(e.shape,(3,4));o[:,6:]=999;b2,e2=conditional_design(x,o,s);np.testing.assert_array_equal(b,b2);np.testing.assert_array_equal(e,e2)
 def test_missing_strength_marked(self):
  x=np.ones((3,78));o=np.ones((3,8));o[0,4]=np.nan;b,e=conditional_design(x,o,np.ones((3,2)));np.testing.assert_array_equal(e[0],[0,1,0,1])

if __name__=='__main__':unittest.main()

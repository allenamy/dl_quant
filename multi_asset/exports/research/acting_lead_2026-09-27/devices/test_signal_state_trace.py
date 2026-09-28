import unittest
import numpy as np
from signal_state_trace import trace_chain, rank_scores, trim_parts

class TraceTests(unittest.TestCase):
 def setUp(self):
  self.p={'cap_mult':2.,'alpha':.1,'band':0.,'qv4h_min':1.}
  self.m=np.arange(3);self.legal=np.ones(4,bool);self.q=np.ones(3)*2
 def tr(self,c,h=None,p=None,legal=None):
  return trace_chain(np.array(c,float),np.zeros((2,4)) if h is None else h,self.m,self.q,self.legal if legal is None else legal,p or self.p)
 def test_normalized(self):
  x=self.tr([[1,0,-1],[0,0,0]]);np.testing.assert_allclose(x.sum(0),[.05,0,-.05,0])
 def test_inherited_decay(self):
  h=np.array([[.2,0,-.2,0],[0,0,0,0]]);x=self.tr([[0,0,0],[1,0,-1]],h);np.testing.assert_allclose(x[0],[.18,0,-.18,0])
 def test_band_freezes_each_part(self):
  h=np.array([[.02,0,-.02,0],[.03,0,-.03,0]])
  p=dict(self.p,band=.2);np.testing.assert_array_equal(self.tr([[1,0,-1],[0,1,-1]],h,p),h)
 def test_exit_removes_all_parts(self):
  h=np.array([[.2,0,-.2,.1],[0,0,0,0]]);x=self.tr([[1,0,-1],[0,0,0]],h,legal=np.array([0,1,1,1],bool));np.testing.assert_array_equal(x[:,[0,3]],0)
 def test_cap_uses_common_factor(self):
  x=self.tr([[5,-1,-1],[0,-1,-2]],p=dict(self.p,cap_mult=.3,alpha=1.));np.testing.assert_allclose(x.sum(0),[1/3,-1/3,-1/3,0]);self.assertAlmostEqual(x[0,0],4/15)
 def test_cancellation_survives_shared_transform(self):
  x=self.tr([[2,1,-3],[-2,0,2]],p=dict(self.p,alpha=1));self.assertNotEqual(x[0,0],0);self.assertAlmostEqual(x.sum(0)[0],0)
 def test_zero_gross_refused(self):
  with self.assertRaisesRegex(ValueError,'degenerate'):self.tr([[1,1,1],[0,0,0]])
 def test_nonfinite_refused(self):
  with self.assertRaisesRegex(ValueError,'finite'):self.tr([[1,np.nan,-1],[0,0,0]])
 def test_duplicate_member_refused(self):
  with self.assertRaisesRegex(ValueError,'axis'):trace_chain(np.zeros((2,3)),np.zeros((2,4)),[0,0,2],self.q,self.legal,self.p)
 def test_trim_common_mask(self):
  c=np.array([[-1.,1.],[.5,-.5]]);np.testing.assert_array_equal(trim_parts(c,np.array([-.002,-.002])),[[0,1],[0,-.5]])
 def test_rank_ties_and_nan(self):
  np.testing.assert_allclose(rank_scores(np.array([2.,2.,4.,np.nan])),[.25,.25,1.,np.nan],equal_nan=True)
 def test_component_count_preserved(self):
  x=self.tr([[1,0,-1],[0,1,-1]]);self.assertEqual(x.shape,(2,4))
if __name__=='__main__':unittest.main()

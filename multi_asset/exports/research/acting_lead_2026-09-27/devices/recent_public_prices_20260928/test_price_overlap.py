import unittest
import numpy as np
try:import price_overlap as P
except ImportError:P=None
class Overlap(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(P,'price_overlap implementation required')
 def test_exact_known_returns(self):
  x=np.array([[100.],[110.],[99.]]);a,b,v=P.paired_returns(x,np.log(x),np.ones(x.shape,bool));self.assertTrue(v.all());np.testing.assert_allclose(a,b,rtol=0,atol=1e-14)
 def test_missing_endpoint_not_flat(self):
  x=np.array([[100.],[np.nan],[110.]]);a,b,v=P.paired_returns(x,np.log(x),np.isfinite(x));self.assertFalse(v.any());self.assertTrue(np.isnan(a).all())
 def test_unobserved_finite_price_refused_from_population(self):
  x=np.array([[100.],[110.]]);a,b,v=P.paired_returns(x,np.log(x),np.array([[False],[True]]));self.assertFalse(v.any())
 def test_log_not_level_difference(self):
  x=np.array([[100.],[110.]]);a,b,v=P.paired_returns(x,np.log(x)+10,np.ones(x.shape,bool));self.assertAlmostEqual(b[0,0],.1)
 def test_shape_mismatch_rejected(self):
  with self.assertRaises(ValueError):P.paired_returns(np.ones((2,1)),np.ones((3,1)),np.ones((2,1),bool))
if __name__=='__main__':unittest.main()

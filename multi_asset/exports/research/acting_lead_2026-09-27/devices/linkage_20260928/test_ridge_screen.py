import unittest
import numpy as np
from ridge_screen import fit_ridge,predict,month_masks,anchor_weights

class RidgeControls(unittest.TestCase):
 def test_train_scaling_and_known_linear_signal(self):
  x=np.arange(120,dtype=float).reshape(40,3);y=x[:,0]*.1+2;w=np.ones(40)/40;m=fit_ridge(x,y,w)
  self.assertGreater(np.corrcoef(y,predict(m,x))[0,1],.999)
  p=predict(m,x[:3]);predict(m,x[3:]*1e9);np.testing.assert_array_equal(p,predict(m,x[:3]))
 def test_future_and_purge_are_excluded(self):
  t=np.arange(0,400*86400,14400);M=365*86400;tr,te=month_masks(t,M,396*86400)
  self.assertFalse(tr[t+14400>=M-12*14400].any());self.assertFalse(tr[t>=M].any());self.assertTrue(te[t==M].all())
 def test_anchor_weight_equal_not_member_count(self):
  a=np.array([0,0,1,1,1,1]);w=anchor_weights(a)
  self.assertAlmostEqual(w[:2].sum(),w[2:].sum());self.assertAlmostEqual(w.sum(),1.)
 def test_nonfinite_refused(self):
  for y in ([1,np.nan],[1,np.inf]):
   with self.assertRaises(ValueError):fit_ridge(np.eye(2),np.array(y),np.ones(2)/2)
 def test_constant_column_allowed(self):
  x=np.column_stack((np.ones(10),np.arange(10)));m=fit_ridge(x,np.arange(10),np.ones(10)/10)
  self.assertTrue(np.isfinite(predict(m,x)).all())
 def test_negative_or_zero_weights_refused(self):
  for w in (np.array([1.,-1.]),np.array([0.,0.])):
   with self.assertRaises(ValueError):fit_ridge(np.eye(2),np.arange(2),w)
if __name__=='__main__':unittest.main()

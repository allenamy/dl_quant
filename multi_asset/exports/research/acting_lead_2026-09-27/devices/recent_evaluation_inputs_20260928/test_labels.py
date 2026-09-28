import unittest
import numpy as np
from labels import build_labels

class LabelTests(unittest.TestCase):
    def base(self):
        t=np.arange(0,14500,300,dtype=np.int64);p=np.ones((49,2));o=np.ones_like(p,dtype=bool);a=np.array([0],np.int64)
        return t,p,o,a
    def test_direct_raw_not_clipped(self):
        t,p,o,a=self.base();p[-1]=[1.75,.4];y,k=build_labels(t,p,o,a);np.testing.assert_array_equal(y,[[.75,-.6]]);self.assertTrue(k.all())
    def test_internal_missing_not_zero(self):
        t,p,o,a=self.base();o[20,0]=False;y,k=build_labels(t,p,o,a);self.assertTrue(np.isnan(y[0,0]));self.assertFalse(k[0,0]);self.assertTrue(k[0,1])
    def test_missing_start_not_backfilled(self):
        t,p,o,a=self.base();y,k=build_labels(t[1:],p[1:],o[1:],a);self.assertFalse(k.any());self.assertTrue(np.isnan(y).all())
    def test_includes_exact_end(self):
        t,p,o,a=self.base();o[-1,0]=False;y,k=build_labels(t,p,o,a);self.assertFalse(k[0,0]);self.assertTrue(k[0,1])
    def test_reject_fractional_axis(self):
        t,p,o,a=self.base()
        with self.assertRaises(ValueError):build_labels(t.astype(float)+.5,p,o,a)
    def test_reject_missing_grid(self):
        t,p,o,a=self.base()
        with self.assertRaises(ValueError):build_labels(np.delete(t,20),np.delete(p,20,0),np.delete(o,20,0),a)
    def test_nonpositive_nonfinite_unknown(self):
        for value in (0,-1,np.nan,np.inf):
            t,p,o,a=self.base();p[10,0]=value;y,k=build_labels(t,p,o,a);self.assertFalse(k[0,0]);self.assertTrue(np.isnan(y[0,0]))
    def test_end_outside_kept_unknown(self):
        t,p,o,a=self.base();y,k=build_labels(t,p,o,np.array([0,14400],np.int64));self.assertTrue(k[0].all());self.assertFalse(k[1].any())
    def test_future_outside_horizon_irrelevant(self):
        t,p,o,a=self.base();t=np.append(t,14700);p=np.vstack([p,[9999,.0001]]);o=np.vstack([o,[True,True]]);y,k=build_labels(t,p,o,a);np.testing.assert_array_equal(y,[[0,0]])
    def test_axis_order_and_population(self):
        t,p,o,a=self.base();p[-1]=[1.1,1.2];y,k=build_labels(t,p,o,a);z,h=build_labels(t,p[:,::-1],o[:,::-1],a);np.testing.assert_array_equal(y[:,::-1],z);np.testing.assert_array_equal(k[:,::-1],h)
    def test_refuse_bad_anchor(self):
        t,p,o,a=self.base()
        with self.assertRaises(ValueError):build_labels(t,p,o,np.array([1],np.int64))
if __name__=='__main__':unittest.main()

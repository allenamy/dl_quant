import unittest
import numpy as np
from price_panel import closed_returns, trailing_sum

class PriceControls(unittest.TestCase):
 def data(self):
  g=np.arange(145,dtype=np.int64)*300
  p=np.column_stack((g/1e6,g/2e6))
  return g,p,np.array([0,0]),np.array([144,144])
 def test_price_not_simple_sum(self):
  g,p,fi,la=self.data();a,r=closed_returns(g,p,fi,la,np.array([],int),np.array([],int))
  np.testing.assert_array_equal(a,[14400,28800,43200]);np.testing.assert_allclose(r[:,0],.0144)
  self.assertNotEqual(float(np.expm1(r[0,0])),float(r[0,0]))
 def test_endpoint_missing_invalidates_both_windows(self):
  g,p,fi,la=self.data();a,r=closed_returns(g,p,fi,la,np.array([48]),np.array([0]))
  self.assertTrue(np.isnan(r[:2,0]).all());self.assertTrue(np.isfinite(r[2,0]));self.assertTrue(np.isfinite(r[:,1]).all())
 def test_interior_gap_not_filled(self):
  g,p,fi,la=self.data();a,r=closed_returns(g,p,fi,la,np.array([30]),np.array([0]))
  self.assertTrue(np.isnan(r[0,0]));self.assertTrue(np.isfinite(r[1:,0]).all())
 def test_no_before_listing_or_after_delist(self):
  g,p,fi,la=self.data();fi[0]=1;la[1]=100;a,r=closed_returns(g,p,fi,la,np.array([],int),np.array([],int))
  self.assertTrue(np.isnan(r[0,0]));self.assertTrue(np.isnan(r[-1,1]))
 def test_nonfinite_price_inside_window(self):
  g,p,fi,la=self.data();p[31,0]=np.nan;a,r=closed_returns(g,p,fi,la,np.array([],int),np.array([],int))
  self.assertTrue(np.isnan(r[0,0]))
 def test_future_prices_do_not_change_past(self):
  g,p,fi,la=self.data();a,x=closed_returns(g,p,fi,la,np.array([],int),np.array([],int));p[97:]+=100
  a,y=closed_returns(g,p,fi,la,np.array([],int),np.array([],int));np.testing.assert_array_equal(x[:2],y[:2])
 def test_extension_uses_new_observations_but_keeps_old_boundary_unknown(self):
  g,p,fi,la=self.data();la[:]=[48,47]
  a,r=closed_returns(g,p,fi,la,np.array([],int),np.array([],int),extension_start_row=49)
  self.assertTrue(np.isfinite(r[:,0]).all());self.assertTrue(np.isnan(r[:2,1]).all());self.assertTrue(np.isfinite(r[2,1]))
 def test_rolling_unknown_and_current_endpoint(self):
  x=np.arange(10,dtype=float)[:,None];x[3]=np.nan;y=trailing_sum(x,3)
  self.assertTrue(np.isnan(y[:2]).all());self.assertTrue(np.isnan(y[3:6]).all());self.assertEqual(y[6,0],15.)
 def test_bad_axes_and_sparse_indices(self):
  g,p,fi,la=self.data()
  for gg,rr,cc in [(g+.5,np.array([],int),np.array([],int)),(g,np.array([145]),np.array([0])),(g,np.array([1]),np.array([2]))]:
   with self.assertRaises(ValueError):closed_returns(gg,p,fi,la,rr,cc)
if __name__=='__main__':unittest.main()

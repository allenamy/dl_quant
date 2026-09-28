import unittest
import numpy as np
from flow_funding import window_mean, fund_asof, baseline_inputs, peer_flows, past_mad

class Controls(unittest.TestCase):
 def test_window_current_closed_and_prior_separate(self):
  x=np.arange(20.)[:,None];end=np.array([7,10,19])
  np.testing.assert_array_equal(window_mean(x,end,3),[[6],[9],[18]])
  np.testing.assert_array_equal(window_mean(x,end-3,4),[[2.5],[5.5],[14.5]])
 def test_missing_not_zero_or_partial_average(self):
  x=np.ones((20,2));x[8,0]=np.nan
  y=window_mean(x,np.array([2,8,10,11]),3)
  self.assertTrue(np.isnan(y[1:3,0]).all());self.assertEqual(y[-1,0],1)
 def test_future_window_invariant(self):
  x=np.arange(20.)[:,None];a=window_mean(x,np.array([8]),5);x[9:]=-1e6
  np.testing.assert_array_equal(a,window_mean(x,np.array([8]),5))
 def test_short_window_unknown(self):
  self.assertTrue(np.isnan(window_mean(np.ones((8,1)),np.array([1]),3)).all())
 def test_fund_unit_ema_not_rescaled(self):
  o=fund_asof(np.array([3600,7200]),np.array([3600,7200]),np.array([-.02,-.002]),np.array([8.,1.]),np.array([-.01,-.0101]))
  np.testing.assert_array_equal(o[:,0],[-.02,-.016]);np.testing.assert_array_equal(o[:,1],[-.01,-.0101])
 def test_asof_future_refused_and_stale_unknown(self):
  with self.assertRaises(ValueError):fund_asof(np.array([3600]),np.array([3601]),np.array([.1]),np.array([8.]),np.array([.1]))
  o=fund_asof(np.array([50000]),np.array([0]),np.array([.1]),np.array([8.]),np.array([.1]))
  self.assertTrue(np.isnan(o).all())
 def test_bad_interval_unknown(self):
  for v in (0,np.nan,np.inf):
   self.assertTrue(np.isnan(fund_asof(np.array([0]),np.array([0]),np.array([.1]),np.array([v]),np.array([.1]))).all())
 def test_latest_fund_replaces_old_columns(self):
  old=np.ones((2,78));own=np.ones((2,8));price=np.ones((2,4))
  x=baseline_inputs(old,own,price);old[:,-2:]=999
  np.testing.assert_array_equal(x,baseline_inputs(old,own,price));self.assertEqual(x.shape,(2,100))
 def test_unknown_explicit_flags(self):
  old=np.ones((1,78));own=np.ones((1,8));p=np.ones((1,4));own[0,2]=np.nan
  x=baseline_inputs(old,own,p);self.assertEqual(x[0,78],0);self.assertEqual(x[0,86],0)
  own[0,2]=0;z=baseline_inputs(old,own,p);self.assertNotEqual(x[0,86],z[0,86])
 def test_peers_no_self_and_missing_population(self):
  peers=np.array([[1,2],[0,2],[0,1]]);active=np.array([True]*3);f=np.array([1.,2.,3.]);q=f*2
  z=peer_flows(peers,active,f,q,2);np.testing.assert_array_equal(z,[[1.5,3],[0,0],[-1.5,-3]])
  active[1]=False;self.assertTrue(np.isnan(peer_flows(peers,active,f,q,2)[0]).all())
 def test_invalid_peer_identity_refused(self):
  with self.assertRaises(ValueError):peer_flows(np.array([[0],[0]]),np.ones(2,bool),np.ones(2),np.ones(2),1)
 def test_mad_is_past_and_per_name(self):
  t=np.arange(12)*14400;x=np.column_stack((np.arange(12.),np.arange(12.)*10))
  mu,sc=past_mad(t,x,86400,min_obs=4,window=6)
  np.testing.assert_allclose(sc[1]/sc[0],10)
  x[6:]=999;mm,ss=past_mad(t,x,86400,min_obs=4,window=6)
  np.testing.assert_array_equal(mm,mu);np.testing.assert_array_equal(ss,sc)
 def test_mad_constant_or_short_unknown(self):
  t=np.arange(12)*14400;x=np.ones((12,2));x[:4,1]=np.nan
  mu,sc=past_mad(t,x,86400,min_obs=4,window=6);self.assertTrue(np.isnan(sc).all())

if __name__=='__main__':unittest.main()

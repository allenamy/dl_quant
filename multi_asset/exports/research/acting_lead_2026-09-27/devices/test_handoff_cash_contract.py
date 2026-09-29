import unittest
import numpy as np
from handoff_cash_contract import books,cash_metrics

class Books(unittest.TestCase):
 def setUp(self):
  self.a=np.array([0,14400,28800]);self.i={'kc':np.array([.2,-.1]),'fc':np.array([.1,-.2])}
  self.r=[{'anchor':a,'arms':{'B':{'accepted':a==14400},'S':{'accepted':a==14400}}} for a in (14400,28800,43200)]
  self.s={f'{arm}_{leg}_{a}':np.array([.12,-.08]) for arm in ('B','S') for leg in ('kc','fc') for a in (14400,28800,43200)}
 def test_raw_not_reshaped(self):
  v=books(self.r,self.s,self.i,self.a);self.assertIsInstance(v,dict)
  np.testing.assert_allclose(v['B'][0][0],[.155,-.145]);np.testing.assert_allclose(v['B'][0][1],[.12,-.08])
 def test_hold_not_zero_trade(self):
  v=books(self.r,self.s,self.i,self.a);self.assertIsInstance(v,dict)
  np.testing.assert_array_equal(v['B'][1],[True,True,False])
 def test_common_inventory_target(self):
  v=books(self.r,self.s,self.i,self.a);self.assertIsInstance(v,dict)
  np.testing.assert_array_equal(v['B'][0][0],v['S'][0][0])
 def test_future_row_ignored(self):
  v=books(self.r,self.s,self.i,self.a);self.assertIsInstance(v,dict)
  self.s['B_kc_43200'][0]=np.nan
  z=books(self.r,self.s,self.i,self.a);np.testing.assert_array_equal(v['B'][0],z['B'][0])
 def test_gap_refused(self):
  with self.assertRaises(ValueError):books(self.r,self.s,self.i,self.a[[0,2]])
 def test_missing_population(self):
  with self.assertRaises(ValueError):books(self.r[1:],self.s,self.i,self.a)

class Cash(unittest.TestCase):
 def fixture(self):
  p={'A':np.array([0,14400]),'nav0':np.array([100.,110.]),'nav1':np.array([110.,99.]),'navm0':np.array([100.,110.]),'navm1':np.array([110.,99.]),'price_trade':np.array([11.,-10.]),'funding':np.array([0.,0.]),'fee':np.array([1.,1.]),'transfer':np.zeros(2),'turnover':np.array([20.,30.]),'nav5_t0':np.array(0),'nav5_main':np.r_[np.linspace(100,110,49),np.linspace(110,99,49)[1:]],'status':np.array([0,0])}
  for k in ('unk_held','unk_notional','n_stop_events','n_flatten_events'):p[k]=np.zeros(2)
  return p
 def test_compound_not_sum(self):
  r=cash_metrics(self.fixture(),0,28800);self.assertIsInstance(r,dict);self.assertAlmostEqual(r['compound'],-.01)
 def test_first_setup_excluded(self):
  r=cash_metrics(self.fixture(),14400,28800);self.assertIsInstance(r,dict);self.assertAlmostEqual(r['compound'],-.1);self.assertEqual(r['fee'],1.)
 def test_bad_identity_refused(self):
  p=self.fixture();p['price_trade'][1]+=.1
  with self.assertRaises(ValueError):cash_metrics(p,0,28800)
 def test_missing_endpoint_refused(self):
  p=self.fixture();p['nav5_main']=p['nav5_main'][:-1]
  with self.assertRaises(ValueError):cash_metrics(p,0,28800)
 def test_unknown_not_certified(self):
  p=self.fixture();p['unk_held'][1]=1;r=cash_metrics(p,0,28800);self.assertIsInstance(r,dict);self.assertFalse(r['priced_complete'])
 def test_nonfinite_refused(self):
  p=self.fixture();p['nav1'][1]=np.nan
  with self.assertRaises(ValueError):cash_metrics(p,0,28800)
if __name__=='__main__':unittest.main()

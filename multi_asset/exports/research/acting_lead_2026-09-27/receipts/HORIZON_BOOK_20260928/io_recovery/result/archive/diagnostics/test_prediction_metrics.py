import unittest
import numpy as np
from prediction_metrics import metrics

class PredictionMetricsTest(unittest.TestCase):
 def test_perfect_raw_calibration(self):
  r=np.random.default_rng(472);p=r.normal(size=(80,7));y=2*p
  m=metrics(p,y,np.ones(p.shape,bool))
  for k in ('avg_per_asset_pearson','avg_per_asset_spearman','cs_rank_ic','cs_pearson'):
   self.assertAlmostEqual(m[k],1.)
  self.assertAlmostEqual(m['beta_y_on_prediction'],2.)
  self.assertAlmostEqual(m['sigma_prediction_over_y'],.5)
  self.assertLess(m['max_cross_sectional_demeaned_bias'],1e-14)
 def test_constant_is_unmeasurable(self):
  m=metrics(np.ones((80,7)),np.arange(560).reshape(80,7),np.ones((80,7),bool))
  self.assertIsNone(m['avg_per_asset_pearson']);self.assertIsNone(m['cs_rank_ic']);self.assertIsNone(m['beta_y_on_prediction'])
 def test_population_and_unknown_reported(self):
  r=np.random.default_rng(472);p=r.normal(size=(80,7));y=p.copy();mask=np.ones(p.shape,bool)
  p[0,0]=np.nan;y[0,1]=np.nan;mask[0,2]=False
  m=metrics(p,y,mask)
  self.assertEqual(m['missing_prediction_members'],1);self.assertEqual(m['missing_label_members'],1)
  self.assertEqual(m['measured_pairs'],557);self.assertEqual(m['intended_pairs'],559)
 def test_shape_refused(self):
  with self.assertRaises(ValueError):metrics(np.ones((10,3)),np.ones((9,3)),np.ones((10,3),bool))

if __name__=='__main__':unittest.main()

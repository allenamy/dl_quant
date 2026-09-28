"""Meaningful controls for evidence-only, non-destructive label repair."""
import copy, importlib.util, unittest
from pathlib import Path
import numpy as np

class Controls(unittest.TestCase):
 def setUp(self):
  p=Path(__file__).with_name('label_overlay.py')
  self.assertTrue(p.exists(),'label overlay implementation is missing')
  spec=importlib.util.spec_from_file_location('overlay',p);self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
  self.a=np.array([14400,28800],dtype=np.int64);self.s=np.array(['AUSDT','BUSDT']);self.y=np.array([[np.nan,.2],[np.nan,np.nan]],np.float32)
  self.rows=[{'anchor':14400,'symbol':'AUSDT','status':'OBSERVED','n_closes':49,'missing_ts':[],'y4s':.123},{'anchor':28800,'symbol':'BUSDT','status':'UNAVAILABLE','n_closes':48,'missing_ts':[29100],'y4s':None}]
 def apply(self,rows=None,y=None):return self.m.patch_labels(self.a,self.s,self.y if y is None else y,self.rows if rows is None else rows)
 def test_only_proven_nan_changes(self):
  before=self.y.tobytes();out,ix=self.apply();self.assertEqual(before,self.y.tobytes());self.assertEqual(ix,[(0,0)]);self.assertEqual(out[0,0],np.float32(.123));self.assertEqual(out[0,1].tobytes(),self.y[0,1].tobytes());self.assertTrue(np.isnan(out[1]).all())
 def test_existing_value_refused(self):
  y=self.y.copy();y[0,0]=0
  with self.assertRaises(ValueError):self.apply(y=y)
 def test_inf_source_not_treated_as_nan(self):
  y=self.y.copy();y[0,0]=np.inf
  with self.assertRaises(ValueError):self.apply(y=y)
 def test_duplicate_refused(self):
  with self.assertRaises(ValueError):self.apply(self.rows+[self.rows[0]])
 def test_partial_observed_refused(self):
  r=copy.deepcopy(self.rows);r[0]['n_closes']=48
  with self.assertRaises(ValueError):self.apply(r)
 def test_unknown_not_implicit_zero(self):
  r=copy.deepcopy(self.rows);r[1]['y4s']=0
  with self.assertRaises(ValueError):self.apply(r)
 def test_wrong_identity_refused(self):
  for k,v in [('anchor',14400.5),('symbol','CUSDT')]:
   r=copy.deepcopy(self.rows);r[0][k]=v
   with self.assertRaises(ValueError):self.apply(r)
 def test_nonfinite_or_impossible_return_refused(self):
  for v in [float('nan'),float('inf'),-1.0,1e100,True]:
   r=copy.deepcopy(self.rows);r[0]['y4s']=v
   with self.assertRaises(ValueError):self.apply(r)
 def test_axes_refused(self):
  for a,s in [(self.a[::-1],self.s),(self.a,np.array(['AUSDT','AUSDT']))]:
   with self.assertRaises(ValueError):self.m.patch_labels(a,s,self.y,self.rows)

if __name__=='__main__':unittest.main()

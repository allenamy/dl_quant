import unittest, ast, pathlib, tempfile
import numpy as np
try: import channel_parity as C
except ImportError: C=None

class ChannelContract(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(C,'channel_parity implementation is required')
 def row(self,t,c=100):return [str(t*1000),'99','102','98',str(c),'5',str(t*1000+299999),'500','10','2','200','0']
 def functions(self):
  return lambda r:(float(r[4]),[np.nan,.04,.5,np.log1p(500),np.log1p(10),np.log(50),.4]), lambda c:[np.nan if not np.isfinite(x) else min(max(x,l),h) for x,(l,h) in zip(c,[(-.3,.3),(0,.5),(0,1),(0,25),(0,20),(-5,15),(0,1)])]
 def test_requires_implementation(self):self.assertTrue(callable(C.make_rows))
 def test_gap_not_return_across_missing_bar(self):
  t,p,c,v=C.make_rows([self.row(0),self.row(300,101),self.row(900,102)],*self.functions())
  np.testing.assert_array_equal(t,[300,600,1200]);self.assertFalse(v[0]);self.assertTrue(v[1]);self.assertFalse(v[2]);self.assertTrue(np.isnan(c[2,0]));self.assertEqual(c[1,0],np.float16(.01))
 def test_return_clip_keeps_raw_price(self):
  t,p,c,v=C.make_rows([self.row(0),self.row(300,150)],*self.functions());self.assertEqual(p[1],150);self.assertEqual(c[1,0],np.float16(.3))
 def test_duplicate_or_backwards_refused(self):
  for rows in ([self.row(0),self.row(0)],[self.row(300),self.row(0)]):
   with self.assertRaises(ValueError):C.make_rows(rows,*self.functions())
 def test_nan_masks_are_not_zero(self):
  a=np.array([[1,np.nan],[np.nan,1]],np.float16);b=np.array([[1,0],[2,3]],np.float16)
  r=C.compare(a,b,np.ones(a.shape,bool));self.assertEqual(r['both_finite'],2);self.assertEqual(r['value_differences'],1);self.assertEqual(r['left_missing_right_finite'],2)
 def test_first_return_exclusion_does_not_remove_other_channels(self):
  a=np.array([[np.nan,1]],np.float16);b=np.array([[2,2]],np.float16);m=np.array([[False,True]])
  r=C.compare(a,b,m);self.assertEqual(r['population'],1);self.assertEqual(r['value_differences'],1)
 def test_unknown_axis_refused(self):
  with self.assertRaises(ValueError):C.validate_axis(['A','A'],['A','A'],2)
  with self.assertRaises(ValueError):C.validate_axis(['A','B'],['B','A'],2)
 def test_ast_exec_excludes_top_level_side_effects(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'p.py';p.write_text('raise RuntimeError("never execute")\nCHN_CLIPS=[(-.3,.3)]\ndef bars_to_channels(r):\n return float(r[4]), [np.nan]\ndef clipch(x):\n return x\n')
   f,g=C.extract_functions(p);self.assertEqual(f(self.row(0))[0],100)
 def test_future_row_changes_do_not_change_past_features(self):
  a=[self.row(0),self.row(300,101),self.row(600,99)];b=a[:2]+[self.row(600,150)]
  x=C.make_rows(a,*self.functions())[2];y=C.make_rows(b,*self.functions())[2]
  np.testing.assert_array_equal(x[:2],y[:2]);self.assertNotEqual(x[2,0],y[2,0])
if __name__=='__main__':unittest.main()

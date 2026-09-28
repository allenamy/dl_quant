import unittest
from inventory_contract import window_contract, exact_axis
class Test(unittest.TestCase):
 def test_end_is_after_last_anchor(self):
  self.assertEqual(window_contract([0,14400,28800],0,2,43200,0)['label_end'],43200)
  with self.assertRaisesRegex(ValueError,'label'):window_contract([0,14400,28800],0,2,28800,0)
 def test_prefix_not_invented(self):
  r=window_contract([0,14400,28800],0,2,43200,14400)
  self.assertEqual(r['prefix_status'],'UNSUPPORTED_COMMON_ORIGIN')
  self.assertFalse(r['has_measured_inventory'])
 def test_post_origin_still_not_built(self):
  self.assertEqual(window_contract([0,14400,28800],1,2,43200,0)['prefix_status'],'NOT_BUILT')
 def test_bad_axis(self):
  for axis in ([0,14400,28800.5],[0,14401,28800],[14400,0,28800]):
   with self.assertRaises(ValueError):window_contract(axis,0,2,43200,0)
 def test_exact_axis_no_intersection(self):
  exact_axis([0,1],[0,1]);
  for b in ([1,0],[0],[0,1,2]):
   with self.assertRaises(ValueError):exact_axis([0,1],b)
if __name__=='__main__':unittest.main()

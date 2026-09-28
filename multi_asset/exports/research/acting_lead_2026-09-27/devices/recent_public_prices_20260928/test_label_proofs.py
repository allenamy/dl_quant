import unittest,math
from label_proofs import label_from_closes
class ProofTests(unittest.TestCase):
 def test_all_49(self):
  p={14400+i*300:100+i for i in range(49)};r=label_from_closes(p,14400)
  self.assertEqual(r['status'],'OBSERVED');self.assertAlmostEqual(r['y4s'],.48)
 def test_missing_endpoint(self):
  p={14400+i*300:100 for i in range(1,49)};r=label_from_closes(p,14400);self.assertIsNone(r['y4s']);self.assertEqual(r['n_closes'],48)
 def test_missing_middle(self):
  p={14400+i*300:100 for i in range(49) if i!=12};self.assertIsNone(label_from_closes(p,14400)['y4s'])
 def test_nonfinite(self):
  p={14400+i*300:100 for i in range(49)};p[14700]=float('nan')
  with self.assertRaises(ValueError):label_from_closes(p,14400)
 def test_bad_axis(self):
  with self.assertRaises(ValueError):label_from_closes({},14400.5)
if __name__=='__main__':unittest.main()

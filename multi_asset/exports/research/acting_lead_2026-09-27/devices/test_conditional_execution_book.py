import unittest
from conditional_execution_book import compare
class Controls(unittest.TestCase):
 def test_empty(self):
  with self.assertRaises(ValueError):compare({}, {},False)
 def test_nonfinite(self):
  with self.assertRaises(ValueError):compare({'a':float('nan')},{'a':1.},False)
 def test_halt_not_trade(self):
  r=compare({'a':2.},{'a':2.},True);self.assertTrue(r['conditional_target_match']);self.assertFalse(r['execution_claim']);self.assertTrue(r['opening_halted'])
 def test_population(self):self.assertFalse(compare({'a':0.,'b':1.},{'a':0.},False)['conditional_target_match'])
 def test_change_detected(self):self.assertFalse(compare({'a':2.000002},{'a':2.},False)['conditional_target_match'])
if __name__=='__main__':unittest.main()

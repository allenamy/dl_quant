import unittest
import numpy as np
import label_contract as C
class Reproduction(unittest.TestCase):
 def test_exists(self):self.assertTrue(callable(getattr(C,'assert_reproduction',None)))
 def test_exact(self):
  C.assert_reproduction('a','a',[1,2],[1,2],np.array([1.,np.nan],np.float32),np.array([1.,np.nan],np.float32))
 def test_state(self):
  with self.assertRaises(ValueError):C.assert_reproduction('a','b',[1],[1],np.array([1.]),np.array([1.]))
 def test_sample(self):
  with self.assertRaises(ValueError):C.assert_reproduction('a','a',[1],[2],np.array([1.]),np.array([1.]))
 def test_score(self):
  with self.assertRaises(ValueError):C.assert_reproduction('a','a',[1],[1],np.array([1.]),np.array([1.00000001]))
 def test_population(self):
  with self.assertRaises(ValueError):C.assert_reproduction('a','a',[1],[1],np.array([np.nan]),np.array([0.]))
if __name__=='__main__':unittest.main()

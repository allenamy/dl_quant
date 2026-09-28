import unittest
import numpy as np
try:
 from label_contract import validate_overlay, needs_refit
except ImportError:
 validate_overlay=needs_refit=None
class Tests(unittest.TestCase):
 def test_validator_exists(self):self.assertIsNotNone(validate_overlay, "overlay identity validation required before reuse")
 @unittest.skipIf(validate_overlay is None,"not implemented")
 def test_fill_only(self):self.assertEqual(validate_overlay(np.array([1.,np.nan],np.float32),np.array([1.,2.],np.float32)),1)
 @unittest.skipIf(validate_overlay is None,"not implemented")
 def test_finite_change(self):
  with self.assertRaises(ValueError):validate_overlay(np.array([1.,np.nan]),np.array([2.,3.]))
 @unittest.skipIf(validate_overlay is None,"not implemented")
 def test_no_loss(self):
  with self.assertRaises(ValueError):validate_overlay(np.array([1.,np.nan]),np.array([np.nan,3.]))
 @unittest.skipIf(validate_overlay is None,"not implemented")
 def test_dtype_change(self):
  with self.assertRaises(ValueError):validate_overlay(np.array([1.],np.float32),np.array([1.],np.float64))
 @unittest.skipIf(validate_overlay is None,"not implemented")
 def test_inf(self):
  with self.assertRaises(ValueError):validate_overlay(np.array([np.nan]),np.array([np.inf]))
 @unittest.skipIf(needs_refit is None,"not implemented")
 def test_windows(self):
  self.assertFalse(needs_refit([[1,2],[3,4]],[[1,2],[3,4]]));self.assertTrue(needs_refit([[1,2]],[[1,2],[3,4]]))
 @unittest.skipIf(needs_refit is None,"not implemented")
 def test_not_count_only(self):self.assertTrue(needs_refit([[1,2]],[[3,4]]))
if __name__=="__main__":unittest.main()

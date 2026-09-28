import unittest
import executor_bridge as E
class DriverTests(unittest.TestCase):
 def test_one_declared_injection_only(self):
  src='before\n    c.BOOKS = {}; c.target_info = {}; c.PIT_by_tag = {}\nafter\n';out=E.patch_driver(src)
  self.assertEqual(out.replace('    if "executor_semantic_bridge" in CFG:\n        import executor_bridge\n        executor_bridge.install(c, CFG, check)\n',''),src)
 def test_changed_and_double_source_refused(self):
  with self.assertRaises(ValueError):E.patch_driver('missing')
  src='    c.BOOKS = {}; c.target_info = {}; c.PIT_by_tag = {}'
  with self.assertRaises(ValueError):E.patch_driver(src+'\n'+src)
if __name__=='__main__':unittest.main()

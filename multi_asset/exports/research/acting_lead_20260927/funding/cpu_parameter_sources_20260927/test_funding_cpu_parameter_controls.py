"""Contract tests without loading Torch or executing market/engine code."""
import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).with_name('funding_cpu_parameter_controls.py')
s=importlib.util.spec_from_file_location('cpu_parameter_controls',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class Tests(unittest.TestCase):
 def test_duplicate_funding_rejected(self):
  e=list(m.EVENTS)
  with self.assertRaises(ValueError):m.validate_events(e+[e[0]])
 def test_exact_priority(self):
  seq=m.validate_events(m.EVENTS)
  simultaneous=[x for x in seq if x[0]==15840000]
  self.assertEqual([x[1] for x in simultaneous],[0,1])
 def test_frozen_inputs(self):
  self.assertEqual(m.N_NAMES,80);self.assertEqual(m.N_ANCHORS,2)
  self.assertEqual(m.FD_EPS,(1e-3,1e-4))
 def test_no_entry_on_import(self):self.assertNotIn('torch',m.__dict__)

if __name__=='__main__':unittest.main()

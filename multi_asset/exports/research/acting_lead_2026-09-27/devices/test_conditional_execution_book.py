import unittest
from conditional_execution_book import compare, withheld_names
class Controls(unittest.TestCase):
 def test_venue_list_applies_before_report_disposition(self):
  p={'universe':{'tradable':['A']},'untradable_names':{'popped':[]}}
  self.assertEqual(withheld_names(p,{'held_exit':['C']},{'A':1,'B':2}),{'B','C'})
 def test_empty_venue_population_not_ignored(self):
  p={'universe':{'tradable':[]},'untradable_names':{}}
  self.assertEqual(withheld_names(p,{}, {'A':1}),{'A'})
 def test_missing_venue_population_not_assumed(self):
  with self.assertRaises(ValueError):withheld_names({'universe':{},'untradable_names':{}},{},{'A':1})
 def test_empty(self):
  with self.assertRaises(ValueError):compare({}, {},False)
 def test_nonfinite(self):
  with self.assertRaises(ValueError):compare({'a':float('nan')},{'a':1.},False)
 def test_halt_not_trade(self):
  r=compare({'a':2.},{'a':2.},True);self.assertTrue(r['conditional_target_match']);self.assertFalse(r['execution_claim']);self.assertTrue(r['opening_halted'])
 def test_population(self):self.assertFalse(compare({'a':0.,'b':1.},{'a':0.},False)['conditional_target_match'])
 def test_change_detected(self):self.assertFalse(compare({'a':2.000002},{'a':2.},False)['conditional_target_match'])
if __name__=='__main__':unittest.main()

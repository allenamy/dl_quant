import unittest
from conditional_execution_book import compare, withheld_names, recorded_restrictions
class Controls(unittest.TestCase):
 def test_venue_list_applies_before_report_disposition(self):
  p={'universe':{'tradable':['A']},'untradable_names':{'popped':[]}}
  self.assertEqual(withheld_names(p,{'held_exit':['C']},{'A':1,'B':2}),{'B','C'})
 def test_empty_venue_population_not_ignored(self):
  p={'universe':{'tradable':[]},'untradable_names':{}}
  self.assertEqual(withheld_names(p,{}, {'A':1}),{'A'})
 def test_missing_venue_population_not_assumed(self):
  with self.assertRaises(ValueError):withheld_names({'universe':{},'untradable_names':{}},{},{'A':1})
 def test_full_pop_reconciles_display_prefix(self):
  names=['N%02d'%i for i in range(14)]
  phase={'untradable_names':{'popped':names[:12]},'untradable_disposition':{'popped':14,'reduced':0}}
  self.assertEqual(recorded_restrictions(phase,{'popped_names':names,'n_popped':14}),set(names))
 def test_full_pop_conflict_refused(self):
  with self.assertRaises(ValueError):recorded_restrictions({'untradable_names':{'popped':['X']},'untradable_disposition':{'popped':1}},{'popped_names':['Y'],'n_popped':1})
 def test_other_class_truncation_not_ignored(self):
  with self.assertRaises(ValueError):recorded_restrictions({'untradable_names':{'add_blocked':['X']},'untradable_disposition':{'add_blocked':2}},{'popped_names':[],'n_popped':0})
 def test_empty(self):
  with self.assertRaises(ValueError):compare({}, {},False)
 def test_nonfinite(self):
  with self.assertRaises(ValueError):compare({'a':float('nan')},{'a':1.},False)
 def test_halt_not_trade(self):
  r=compare({'a':2.},{'a':2.},True);self.assertTrue(r['conditional_target_match']);self.assertFalse(r['execution_claim']);self.assertTrue(r['opening_halted'])
 def test_population(self):self.assertFalse(compare({'a':0.,'b':1.},{'a':0.},False)['conditional_target_match'])
 def test_change_detected(self):self.assertFalse(compare({'a':2.000002},{'a':2.},False)['conditional_target_match'])
if __name__=='__main__':unittest.main()

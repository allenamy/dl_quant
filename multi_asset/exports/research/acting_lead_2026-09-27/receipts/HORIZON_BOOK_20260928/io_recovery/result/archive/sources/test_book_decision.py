import copy,unittest
from book_decision import decide

class BookDecisionTest(unittest.TestCase):
 def setUp(self):
  self.d={'status':'EXPLORATORY_NOT_RELEASE','results':{k:{'results':{w:{'paired_daily_bps':1.,'ci95_bps':[-1.,2.]} for w in ('2023H2','2024','2025','pre2026','2026_JanAug','Sep01_18_descriptive')}} for k in ('slow_vs_fast','slow_vs_NC42','slow_vs_NC2027')}}
 def test_all_required_comparisons_not_one_best(self):
  self.assertTrue(decide(self.d)['followup_DL_condition_met'])
  self.d['results']['slow_vs_NC2027']['results']['pre2026']['paired_daily_bps']=-.1
  self.assertFalse(decide(self.d)['followup_DL_condition_met'])
 def test_annual_harm_blocks_even_pooled_positive(self):
  self.d['results']['slow_vs_fast']['results']['2025']['ci95_bps']=[-3.,-.1]
  self.assertFalse(decide(self.d)['followup_DL_condition_met'])
 def test_unknown_refused(self):
  self.d['results']['slow_vs_fast']['results']['pre2026']['paired_daily_bps']=float('nan')
  with self.assertRaises(ValueError):decide(self.d)
 def test_recent_deterioration_not_hidden_by_positive_long_windows(self):
  self.d['results']['slow_vs_NC42']['results']['Sep01_18_descriptive']['paired_daily_bps']=-2.
  v=decide(self.d);self.assertTrue(v['followup_DL_condition_met']);self.assertTrue(v['recent_deterioration']['slow_vs_NC42']);self.assertFalse(v['release_authorized'])

if __name__=='__main__':unittest.main()

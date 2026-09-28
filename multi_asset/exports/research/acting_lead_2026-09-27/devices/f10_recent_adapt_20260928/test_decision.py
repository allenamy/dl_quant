import unittest,copy
from decision import decide

def rows():
 out={}
 for seed in (42,2027):
  def window():return {'paired_daily_bps':2.,'fee125_paired_daily_bps':1.5,'paired_metric_difference':{'return_compound':{'mean':.01},'maxdd_5m':{'mean':0.},'worst_day':{'mean':0.},'days_below_minus4pct':{'mean':0.}}}
  out[f'R180_s{seed}_vs_NC']={'results':{w:window() for w in ['recent_primary','Sep01_18_descriptive','2023H2','2024','2025','2026_H1']}}
  out[f'R180_s{seed}_vs_U']={'results':{'recent_primary':window()}}
 return {'results':out}
class Tests(unittest.TestCase):
 def test_green(self):self.assertEqual(decide(rows())['status'],'ADVANCE_TO_FORWARD_RESEARCH_NOT_RELEASE')
 def test_old_mean_not_primary(self):
  r=rows();r['results']['R180_s42_vs_NC']['results']['2024']['paired_daily_bps']=-5
  self.assertEqual(decide(r)['status'],'ADVANCE_TO_FORWARD_RESEARCH_NOT_RELEASE')
 def test_recent_loss(self):
  r=rows();r['results']['R180_s42_vs_NC']['results']['Sep01_18_descriptive']['paired_metric_difference']['return_compound']['mean']=-.001
  self.assertEqual(decide(r)['status'],'CRITERION_NOT_MET')
 def test_old_tail(self):
  r=rows();r['results']['R180_s2027_vs_NC']['results']['2024']['paired_metric_difference']['maxdd_5m']['mean']=-.06
  self.assertEqual(decide(r)['status'],'CRITERION_NOT_MET')
 def test_unknown(self):
  r=rows();r['results']['R180_s42_vs_NC']['results']['recent_primary']['paired_daily_bps']=float('nan')
  with self.assertRaises(ValueError):decide(r)
if __name__=='__main__':unittest.main()

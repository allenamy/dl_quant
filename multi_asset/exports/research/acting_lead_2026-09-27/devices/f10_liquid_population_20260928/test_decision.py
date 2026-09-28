import unittest
from decision import decide

def fixture():
    r={'results':{}}
    for seed in (42,2027):
        windows={}
        for w in ('recent_primary','Sep01_18_descriptive','2023H2','2024','2025','2026_H1'):
            windows[w]={'paired_daily_bps':1.,'fee125_paired_daily_bps':.5,'paired_metric_difference':{k:{'mean':0.} for k in ('return_compound','maxdd_5m','days_below_minus4pct')}}
        r['results'][f'LQ_s{seed}_vs_NC']={'results':windows}
        r['results'][f'LQ_s{seed}_vs_U']={'results':{'recent_primary':{'paired_daily_bps':1.}}}
    return r

class GateControls(unittest.TestCase):
    def test_positive_control(self):self.assertEqual(decide(fixture())['passed'],20)
    def test_ic_cannot_override_one_seed_economic_failure(self):
        r=fixture();r['results']['LQ_s2027_vs_NC']['results']['recent_primary']['paired_daily_bps']=-.1;self.assertEqual(decide(r)['status'],'CRITERION_NOT_MET')
    def test_nan_refused(self):
        r=fixture();r['results']['LQ_s42_vs_U']['results']['recent_primary']['paired_daily_bps']=float('nan')
        with self.assertRaises(ValueError):decide(r)
    def test_recent_tail_refused(self):
        r=fixture();r['results']['LQ_s42_vs_NC']['results']['recent_primary']['paired_metric_difference']['days_below_minus4pct']['mean']=.1;self.assertEqual(decide(r)['status'],'CRITERION_NOT_MET')
    def test_old_average_not_gate_but_tail_is(self):
        r=fixture();x=r['results']['LQ_s42_vs_NC']['results']['2024'];x['paired_daily_bps']=-100;self.assertEqual(decide(r)['passed'],20);x['paired_metric_difference']['maxdd_5m']['mean']=-.021;self.assertEqual(decide(r)['passed'],19)

if __name__=='__main__':unittest.main()

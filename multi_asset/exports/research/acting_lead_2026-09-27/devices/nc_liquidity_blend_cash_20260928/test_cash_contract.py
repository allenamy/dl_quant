import json,tempfile,unittest
from pathlib import Path
import numpy as np
from cash_contract import sha,verify_record,stress_r,decide


class Contract(unittest.TestCase):
    def test_decision_both_seeds_both_windows_stress(self):
        r={'results':{s:{'results':{w:{'paired_daily_bps':1.,'extra5bps_candidate_only_paired_daily_bps':.1} for w in ('pre2026','2026_JanAug')}} for s in ('42','2027')}}
        self.assertEqual(decide(r)['status'],'FOLLOWUP_COST_AND_FORWARD_VALIDATION_ONLY')
        r['results']['2027']['results']['pre2026']['extra5bps_candidate_only_paired_daily_bps']=-.01
        self.assertEqual(decide(r)['status'],'FOLLOWUP_CRITERION_NOT_MET')
        r['results']['2027']['results']['pre2026']['extra5bps_candidate_only_paired_daily_bps']=float('nan')
        with self.assertRaises(ValueError):decide(r)

    def test_stress_units_and_missing(self):
        np.testing.assert_allclose(stress_r(np.array([.001]),np.array([.1])),[.0009])
        for tau in (np.array([np.nan]),np.array([-1.])):
            with self.assertRaises(ValueError):stress_r(np.array([.001]),tau)

    def test_bound_material_mutations(self):
        for bucket in ('inputs','sources','outputs'):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);data=root/'data';data.write_text('original')
                r={'status':'TARGET_IDENTITY_AND_SUPPORT_COMPLETE_NOT_ECONOMIC_VALIDATION',
                   'baseline_fund_score_LR_seat_and_all_combo_arrays_exact':True,
                   'seat_future_mutations':{'1':True},'inputs':{},'sources':{},'outputs':{}}
                r[bucket][str(data)]=sha(data);p=root/'RESULT.json';p.write_text(json.dumps(r));pin=sha(p)
                self.assertEqual(verify_record(p,pin),r)
                data.write_text('mutated')
                with self.assertRaises(ValueError):verify_record(p,pin)
                data.write_text('original');p.write_text('{}')
                with self.assertRaises(ValueError):verify_record(p,pin)


if __name__=='__main__':unittest.main()

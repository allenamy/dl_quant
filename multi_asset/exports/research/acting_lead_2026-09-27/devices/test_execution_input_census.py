import importlib.util,unittest
from pathlib import Path

P=Path(__file__).with_name('execution_input_census.py')
sp=importlib.util.spec_from_file_location('census',P) if P.exists() else None
M=importlib.util.module_from_spec(sp) if sp else None
if sp:sp.loader.exec_module(M)

class CensusControls(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(M,'decision-input census not implemented')
    def test_blind_fields_not_retained(self):
        r=M.order_record({'symbol':'X','chase_arm':'x','requote_arm':'y','terminal_reason':'skipped_no_chase_arm','fee':10,'target_w':.2,'request_ledger':[{'client_id':'A-X-1','quantity':2,'arm_profit':50}]})
        self.assertEqual(r,{'symbol':'X','target_w':.2,'request_ledger':[{'client_id':'A-X-1'}]})
    def test_finite_missing_not_zero(self):
        self.assertFalse(M.finite(None));self.assertFalse(M.finite(float('nan')));self.assertFalse(M.finite(True));self.assertTrue(M.finite(0.))
    def test_empty_population_not_complete(self):
        r=M.order_coverage([]);self.assertFalse(r['complete_plan_fields']);self.assertEqual(r['rows'],0)
    def test_missing_fields_counted(self):
        r=M.order_coverage([{'symbol':'X','prev_w':0.,'target_w':1.,'mid_at_anchor':2.,'reduce_only':False,'side':'BUY','request_ledger':[]}])
        self.assertTrue(r['complete_plan_fields']);self.assertEqual(r['request_entries'],0);self.assertEqual(r['request_quantity_missing'],0)
    def test_unknown_quantity_not_certified(self):
        r=M.order_coverage([{'symbol':'X','prev_w':float('nan'),'target_w':1.,'mid_at_anchor':2.,'request_ledger':[{'client_id':'A-X-1','qty':None}]}])
        self.assertFalse(r['complete_plan_fields']);self.assertEqual(r['missing_plan_fields']['prev_w'],1);self.assertEqual(r['request_quantity_missing'],1)
    def test_parent_nominal_mismatch_not_matched_by_wall_time(self):
        a=[{'anchor_ts':1001,'rebalance_id':'A1001','external_book':{'nominal_ts':2000}}]
        self.assertEqual(M.anchor_candidates(a,1000),[])
    def test_duplicate_rid_ambiguous(self):
        a={'anchor_ts':1001,'rebalance_id':'A1001','external_book':{'nominal_ts':1000}}
        self.assertEqual(len(M.anchor_candidates([a,a],1000)),2)
    def test_fixed_population_with_prior_context(self):
        rows=[{'anchor_ts':x} for x in [1790222399,1790222400,1790559999,1790568000,None]]
        self.assertEqual([r['anchor_ts'] for r in M.population_context(rows)],[1790222400,1790559999])
    def test_explicit_null_request_ledger_retained_and_counted(self):
        r=M.order_record({'symbol':'X','request_ledger':None})
        self.assertIsNone(r['request_ledger'])
        self.assertEqual(M.order_coverage([r])['request_ledger_null'],1)
        self.assertEqual(M.order_coverage([r])['request_entries'],0)
    def test_malformed_request_population_not_dropped(self):
        for ledger in ({},[None]):
            with self.assertRaises(ValueError):M.order_record({'request_ledger':ledger})
    def test_phase_parse_not_silent(self):
        with self.assertRaises(ValueError):M.phases('2026-09-28T00:24:00Z phase_A: {broken}')
        self.assertEqual(M.phases('2026-09-28T00:24:00Z other: not-json'),[])

if __name__=='__main__':unittest.main()

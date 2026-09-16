"""Only new valuation-boundary checks; no execution Engine or cash rerun."""
import unittest,json,copy
from pathlib import Path
import mark_facts as m

class MarkFactsTests(unittest.TestCase):
    def setUp(self):
        self.blobs={n:(Path(__file__).resolve().parents[1]/'aergo_public_price_probe_20260915'/n).read_bytes() for n in m.SOURCE_HASHES}
        self.f=m.MarkFacts(self.blobs)
        self.positions={m.SYMBOL:dict(active=True,instrument_id=m.GENERATION)}
    def test_real_four_exact_closes_only(self):
        for key,want in m.TARGETS.items():
            original={m.SYMBOL:None,'BTCUSDT':65000.}
            got=self.f.prices(*key,original,self.positions)
            self.assertEqual(got,{m.SYMBOL:float(want),'BTCUSDT':65000.})
            self.assertIsNone(original[m.SYMBOL])
        self.f.finish(m.CLOSE)
    def test_original_body_tamper(self):
        self.blobs['markPriceKlines.body']+=b' '
        with self.assertRaisesRegex(ValueError,'source bytes'):m.MarkFacts(self.blobs)
    def test_future_and_non_target_unchanged(self):
        p={m.SYMBOL:None}
        self.assertIs(self.f.prices('NAV_SNAPSHOT',1784852400001,p,self.positions),p)
        self.assertIs(self.f.prices('DAY',1784851200000,p,self.positions),p)
    def test_trade_observations_never_admitted(self):
        for kind in ('ATTEMPT','RISK_ATTEMPT','FUNDING','CLOSE'):
            with self.assertRaisesRegex(ValueError,'valuation event only'):
                self.f.prices(kind,1784852400000,{m.SYMBOL:None},self.positions)
    def test_existing_price_cannot_be_replaced(self):
        with self.assertRaisesRegex(ValueError,'original missing'):
            self.f.prices('NAV_SNAPSHOT',1784852400000,{m.SYMBOL:.02},self.positions)
    def test_wrong_or_inactive_generation(self):
        for p in (dict(active=False,instrument_id=m.GENERATION),dict(active=True,instrument_id='wrong')):
            with self.assertRaisesRegex(ValueError,'active original generation'):
                self.f.prices('READBACK',1784854500000,{m.SYMBOL:None},{m.SYMBOL:p})
    def test_duplicate_or_missing_target(self):
        self.f.prices('NAV_SNAPSHOT',1784852400000,{m.SYMBOL:None},self.positions)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            self.f.prices('NAV_SNAPSHOT',1784852400000,{m.SYMBOL:None},self.positions)
        with self.assertRaisesRegex(ValueError,'complete accepted valuation'):
            self.f.finish(m.CLOSE)
    def test_unknown_prefix_does_not_claim_future_marks(self):
        self.f.finish(1784851200000)
        self.assertEqual(self.f.summary()['applied_valuation_events'],0)
    def test_real_prefix_aggregate_and_changed_cash(self):
        here=Path(__file__).resolve().parents[1]/'current_rule_e60_cash_audit_20260915'
        source=here/'formal1/nohalt_current_main/audit1/DAILY_AGGREGATES.json'
        if not source.exists():source=here/'completed/nohalt_current_main/audit1/DAILY_AGGREGATES.json'
        raw=source.read_bytes();rows=json.loads(raw)
        self.assertEqual(m.compare_prefix(rows,raw)['daily_nodes'],570)
        changed=copy.deepcopy(rows);changed[2]['independent_cash']+=1
        with self.assertRaisesRegex(ValueError,'economic quantities unchanged'):m.compare_prefix(changed,raw)

if __name__=='__main__':unittest.main()

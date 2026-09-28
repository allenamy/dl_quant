import json
from pathlib import Path
import tempfile
import unittest
from reconcile_notice_audit import audit


class QuantityEvidence(unittest.TestCase):
    def fixture(self, root, end=12, conflict=False):
        live = Path(root)
        for day in ('20260927', '20260928'):
            p = live / 'state/live/pilot_log' / day
            p.mkdir(parents=True)
            (p/'position_readback.jsonl').write_text('')
            (p/'fills.jsonl').write_text('')
        p = live/'state/live/pilot_log/20260928'
        times = [1790556372.0, 1790570848.0]
        pos = [dict(anchor_ts=t-60, read_ts=t, symbol='A', venue_position_qty=q,
                    venue_position_notional=q*100) for t,q in zip(times,[10,end])]
        (p/'position_readback.jsonl').write_text('\n'.join(map(json.dumps,pos)))
        fill = dict(symbol='A',trade_id=77,fill_ts=1790569500.0,side='buy',fill_px=100,fill_notional=200)
        other = dict(fill,fill_notional=300) if conflict else fill
        (p/'fills.jsonl').write_text('\n'.join(map(json.dumps,[fill,other])))
        lines=[]
        for x in pos:
            lines.append('2026-09-28T04:47:00Z phase_C: '+json.dumps(dict(
                position_readback_rows=1,book_observation=dict(anchor_ts=x['anchor_ts'],verdict='OBSERVED',n_rows=1))))
        (live/'state/anchor_runs.log').write_text('\n'.join(lines))
        return live

    def test_repeated_markout_does_not_double_quantity(self):
        with tempfile.TemporaryDirectory() as t:
            d=audit(self.fixture(t))
            self.assertEqual(d['repeat_fill_rows_collapsed'],1)
            self.assertEqual(d['intervals'][0]['unique_fills'],1)
            self.assertEqual(d['intervals'][0]['n_quantity_residuals'],0)

    def test_unknown_extra_contract_is_detected(self):
        with tempfile.TemporaryDirectory() as t:
            d=audit(self.fixture(t,end=13))
            self.assertEqual(d['intervals'][0]['n_quantity_residuals'],1)
            self.assertEqual(d['intervals'][0]['max_abs_residual_usdt'],100)

    def test_conflicting_repeat_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,'conflicting same-trade'):
                audit(self.fixture(t,conflict=True))

    def test_nonfinite_quantity_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,'nonfinite'):
                audit(self.fixture(t,end=float('nan')))


if __name__=='__main__':
    unittest.main()

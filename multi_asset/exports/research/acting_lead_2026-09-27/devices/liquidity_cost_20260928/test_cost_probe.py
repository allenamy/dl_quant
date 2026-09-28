import unittest, tempfile, json, contextlib, io
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np
from cost_probe import finite, project, reference, measure, quartiles, run


class CostProbeTest(unittest.TestCase):
    def test_blind_projection(self):
        self.assertEqual(project({'symbol':'X','chase_arm':'A','requote_p':.2}, {'symbol'}), {'symbol':'X'})

    def test_nonfinite_unknown(self):
        self.assertIsNone(finite(float('nan')))
        self.assertIsNone(finite(float('inf')))
        self.assertIsNone(finite(None))
        self.assertIsNone(finite(True))

    def test_conflicting_reference(self):
        self.assertEqual(reference([{'mid_at_anchor':10}, {'mid_at_anchor':11}])[1], 'reference_conflict')
        self.assertEqual(reference([{'mid_at_anchor':10}, {'mid_at_anchor':10}]), (10.0, None))

    def test_missing_not_zero(self):
        self.assertEqual(reference([{'mid_at_anchor':None}])[1], 'reference_unknown')

    def test_cost_side(self):
        self.assertAlmostEqual(measure(101,100,'buy'),.01)
        self.assertAlmostEqual(measure(101,100,'sell'),-.01)
        with self.assertRaises(ValueError):measure(101,100,'unknown')

    def test_quartile_full_population_and_ties(self):
        self.assertEqual(quartiles([1,2,3,4,5,6,7,8]).tolist(), [0,0,1,1,2,2,3,3])
        self.assertEqual(quartiles([1,1,1,1]).tolist(), [2,2,2,2])

    def test_quartile_missing_refused(self):
        with self.assertRaises(ValueError):quartiles([1,float('nan')])

    def test_actual_entry_same_id_two_symbols_and_mark_append(self):
        reader=Path(__file__).resolve().parents[5]/'live/pilot_journal/tools/fills_reader.py'
        # Locate the canonical reader relative to this repository's multi_asset tree.
        reader=next(p/'multi_asset/exports/live/pilot_journal/tools/fills_reader.py'
                    for p in Path(__file__).resolve().parents
                    if (p/'multi_asset/exports/live/pilot_journal/tools/fills_reader.py').exists())
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);a=1787702400;rid='A'+str(a+1440);base=datetime(2026,8,26,tzinfo=timezone.utc)
            orders=[];fills=[]
            for sym in ('A','D'):
                orders.append(dict(rebalance_id=rid,symbol=sym,order_type='maker',attempt_idx=1,mid_at_anchor=100,submit_ts=a+1440))
                f=dict(rebalance_id=rid,symbol=sym,order_type='maker',attempt_idx=1,trade_id=7,
                    fill_ts=a+1441,fill_px=101,fill_notional=101,side='buy',anchor_ts=a+1440,
                    commission=0,commission_asset='USDT',mid_at_fill_plus_60s=None)
                fills.extend([f,dict(f,supersedes_trade_id=7,mid_at_fill_plus_60s=100,mark_ts_actual=a+1501)])
            for i in range(24):
                d=root/'state/live/pilot_log'/(base+timedelta(days=i)).strftime('%Y%m%d');d.mkdir(parents=True)
                for k,rows in [('orders',orders if i==0 else []),('fills',fills if i==0 else [])]:
                    (d/(k+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
            p=root/'liq.npz';np.savez(p,anchors=[a],symbols=['A','B','C','D'],off=[0,4],m=[0,1,2,3],qvm=[1,2,3,4])
            with contextlib.redirect_stdout(io.StringIO()):run(root,p,reader,root/'out')
            r=json.loads((root/'out/COST_PROBE.json').read_text())
            self.assertEqual(r['raw_fill_rows'],4);self.assertEqual(r['scheduled_fills'],2)
            self.assertEqual(r['scheduled_notional_usdt'],202)
            self.assertAlmostEqual(r['segments']['all']['decision']['quartiles'][0]['cost_bps'],100)
            self.assertEqual(r['segments']['all']['mark60']['quartiles'][0]['notional_coverage'],1)


if __name__=='__main__':unittest.main()

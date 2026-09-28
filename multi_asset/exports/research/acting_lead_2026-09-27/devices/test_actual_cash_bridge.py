import unittest, copy
import actual_cash_bridge as B
import actual_cash_income_diagnostic as I
import json

def fill(tid=1,symbol='AAA',side='BUY',ts=15,amount=20):
 return dict(trade_id=tid,symbol=symbol,side=side,fill_ts=ts,fill_notional=amount,fill_px=10,commission=.01,commission_asset='USDT')
def row(q,read=10,symbol='AAA'):
 return dict(anchor_ts=1,symbol=symbol,source=B.SOURCE,read_ts=read,venue_position_qty=q,venue_position_notional=q*10)
def snapshot(q,ts):return {'read_ts':ts,'positions':{'AAA':{'qty':q,'notional':q*10}}}
class BridgeTests(unittest.TestCase):
 def test_markout_only_once(self):
  a=fill();b=dict(a,supersedes_trade_id=1,mark_ts_actual=70)
  self.assertEqual(len(B.trades([a,b])),1)
 def test_cross_symbol_id(self):self.assertEqual(len(B.trades([fill(),fill(symbol='BBB')])),2)
 def test_missing_fee_not_zero(self):
  a=fill();a['commission']=None
  with self.assertRaises(ValueError):B.trades([a])
 def test_nan_rejected(self):
  with self.assertRaises(ValueError):B.trades([fill(amount=float('nan'))])
 def test_duplicate_conflict(self):
  with self.assertRaises(ValueError):B.trades([fill(),fill(amount=21)])
 def test_missing_id(self):
  with self.assertRaises(ValueError):B.trades([fill(tid=None)])
 def test_bad_side(self):
  with self.assertRaises(ValueError):B.trades([fill(side='unknown')])
 def test_full_snapshot(self):
  o={'verdict':'OBSERVED','n_rows':1,'anchor_ts':1}
  self.assertEqual(B.snapshot([row(2)],o)['positions']['AAA']['qty'],2)
 def test_missing_is_not_empty(self):
  with self.assertRaises(ValueError):B.snapshot([],{'verdict':'OBSERVED','n_rows':1,'anchor_ts':1})
 def test_conflicting_snapshot(self):
  with self.assertRaises(ValueError):B.snapshot([row(2),row(3)],{'verdict':'OBSERVED','n_rows':2,'anchor_ts':1})
 def test_no_snapshot_clustering(self):
  with self.assertRaises(ValueError):B.snapshot([row(2),row(3,read=15,symbol='BBB')],{'verdict':'OBSERVED','n_rows':2,'anchor_ts':1})
 def test_half_open_and_identity(self):
  t=B.trades([fill(tid=1,ts=10),fill(tid=2,ts=20),fill(tid=3,ts=21)])
  w=B.window(snapshot(1,10),snapshot(3,20),t)
  self.assertEqual(w['quantity_verdict'],'CONSISTENT');self.assertEqual(w['fills'],1);self.assertEqual(w['price_trade_cash_usdt'],0)
 def test_missing_fill_fails_and_suppresses_cash(self):
  w=B.window(snapshot(1,10),snapshot(3,20),[])
  self.assertEqual(w['quantity_verdict'],'INCONSISTENT');self.assertIsNone(w['price_trade_cash_usdt'])
 def test_fee_assets_separate(self):
  f=fill();g=fill(tid=2);g['commission_asset']='BNB'
  w=B.window(snapshot(1,10),snapshot(5,20),B.trades([f,g]))
  self.assertEqual(w['fees_native'],{'USDT':.01,'BNB':.01});self.assertEqual(w['full_cash_verdict'],'UNAVAILABLE_INDEPENDENT_INCOME_AND_USD_VALUATION')
class IncomeTests(unittest.TestCase):
 def raw(self,**kw):return dict(tranId=1,type='COMMISSION',symbol='AAA',income=-.01,asset='USDT',time=15000,**kw)
 def test_exact_duplicate_is_once(self):
  r=self.raw();self.assertEqual(len(I.rows((json.dumps(r)+'\n'+json.dumps(r)).encode())),1)
 def test_conflict_refused(self):
  r=self.raw();s=dict(r,income=-.02)
  with self.assertRaises(ValueError):I.rows((json.dumps(r)+'\n'+json.dumps(s)).encode())
 def test_cross_asset_separate(self):
  r=self.raw();s=dict(r,asset='BNB')
  self.assertEqual(len(I.rows((json.dumps(r)+'\n'+json.dumps(s)).encode())),2)
 def test_nonfinite_refused(self):
  r=dict(self.raw(),income=float('nan'))
  with self.assertRaises(ValueError):I.rows(json.dumps(r).encode())
 def test_truncated_json_refused(self):
  with self.assertRaises(ValueError):I.rows(b'{')
if __name__=='__main__':unittest.main()

import unittest,copy
import recovery_order_bridge as R

def row():
 q=dict(client_id='F-test',order_id=123,qty=-2.,state='confirmed',terminal=True,confirmed_qty=-2.,confirmed_notional=-20.,confirmed_qty_final=True,confirmed_notional_final=True,trade_qty={'11':2.},trade_quote={'11':20.},settled_by=R.SETTLED)
 return dict(symbol='AAA',side='SELL',order_type='topup_taker',request_ledger=[q],first_fill_ts=11.,last_fill_ts=12.,filled_qty=-2.,filled_known_qty=-2.,filled_notional=-20.,filled_known_notional=-20.,filled_unknown_qty=None,filled_unknown_residual=None,avg_fill_px=10.,fee_paid=.01,fee_all_usdt=True,fee_assets=['USDT'],fee_source='/fapi/v1/userTrades, 1 child fill(s), topup_taker')
def summary():return dict(symbol='AAA',client_id='F-test',side='SELL',filled_notional=-20.,avg_fill_px=10.,first_fill_ts=11.,last_fill_ts=12.)
class TestBridge(unittest.TestCase):
 def check(self,r):return R.aggregate([r],[summary()],10,20,set())
 def test_full_control(self):
  z=self.check(row());self.assertEqual(z['qty']['AAA'],-2);self.assertEqual(z['quote']['AAA'],-20);self.assertEqual(z['fee_usdt'],.01)
 def test_terminal_required(self):
  r=row();r['request_ledger'][0]['terminal']=False
  with self.assertRaises(ValueError):self.check(r)
 def test_final_quantity_required(self):
  r=row();r['request_ledger'][0]['confirmed_qty_final']=False
  with self.assertRaises(ValueError):self.check(r)
 def test_nonfinite(self):
  r=row();r['request_ledger'][0]['trade_quote']['11']=float('nan')
  with self.assertRaises(ValueError):self.check(r)
 def test_conflicting_duplicate(self):
  a=row();b=copy.deepcopy(a);b['request_ledger'][0]['confirmed_notional']=-21
  with self.assertRaises(ValueError):R.aggregate([a,b],[summary()],10,20,set())
 def test_exact_duplicate_once(self):
  a=row();b=copy.deepcopy(a);z=R.aggregate([a,b],[summary(),summary()],10,20,set());self.assertEqual(z['qty']['AAA'],-2);self.assertEqual(z['fee_usdt'],.01)
 def test_unknown_qty_reject(self):
  r=row();r['filled_unknown_qty']=.1
  with self.assertRaises(ValueError):self.check(r)
 def test_crossing_time(self):
  r=row();r['first_fill_ts']=10
  with self.assertRaises(ValueError):self.check(r)
 def test_existing_fill_overlap(self):
  with self.assertRaises(ValueError):R.aggregate([row()],[summary()],10,20,{('AAA','11')})
 def test_wrong_side(self):
  r=row();r['side']='BUY'
  with self.assertRaises(ValueError):self.check(r)
 def test_modified_known_amount(self):
  r=row();r['filled_known_notional']=-19
  with self.assertRaises(ValueError):self.check(r)
 def test_inconsistent_flag(self):
  r=row();r['request_ledger'][0]['inconsistent']='amount conflict'
  with self.assertRaises(ValueError):self.check(r)
 def test_summary_mismatch(self):
  s=summary();s['filled_notional']=-19
  with self.assertRaises(ValueError):R.aggregate([row()],[s],10,20,set())
 def test_summary_timestamp_exact(self):
  r=row();s=summary();r['first_fill_ts']=s['first_fill_ts']=1790498811.;r['last_fill_ts']=s['last_fill_ts']=1790498812.
  s['first_fill_ts']+=.05
  with self.assertRaises(ValueError):R.aggregate([r],[s],1790498810,1790498820,set())
 def test_boolean_unknown_refused(self):
  r=row();r['filled_unknown_qty']=False
  with self.assertRaises(ValueError):self.check(r)
 def test_multicurrency_unknown(self):
  r=row();r['fee_all_usdt']=False;r['fee_assets']=['USDT','BNB']
  with self.assertRaises(ValueError):self.check(r)
if __name__=='__main__':unittest.main()

import hashlib,json,unittest,numpy as np
from tests_book_lifecycle import fixture,event,run
from book_engine import replay_book
from book_engine_lifecycle import load_book_lifecycle,replay_book_lifecycle,ORDER

class LifecycleTerminalTests(unittest.TestCase):
 def test_terminal_excluded_event_consumed_once_after_json_restart(self):
  life=fixture(price=100,fee=0);ev=[event(1400)]
  first=run([1000,1400],[[100],[100]],[[1],[1]],life,ev,rebalance=np.array([True,False]),terminal_exclusive_ms=1400)
  self.assertEqual(first['state']['funding_prefix_count'],0)
  tail=run([2000],[[100]],[[0]],life,ev,initial_state=json.loads(json.dumps(first['state'])))
  full=run([1000,1400,2000],[[100],[100],[100]],[[1],[1],[0]],life,ev,rebalance=np.array([True,False,True]))
  self.assertEqual(tail['state'],full['state']);self.assertAlmostEqual(tail['research_proxy_net'],-1)
 def test_exact_T_lifecycle_close_waits_for_next_segment(self):
  life=fixture(price=110,fee=0)
  first=run([1000,1500],[[100],[105]],[[1],[1]],life,[],rebalance=np.array([True,False]),terminal_exclusive_ms=1500)
  self.assertEqual(first['state']['settlement_event_count'],0);self.assertEqual(first['q_after'][-1,0],1)
  tail=run([2000],[[np.nan]],[[0]],life,[],initial_state=json.loads(json.dumps(first['state'])))
  self.assertEqual(tail['state']['settlement_event_count'],1);self.assertAlmostEqual(tail['research_proxy_net'],10)
 def test_empty_lifecycle_preserves_original_cash_math(self):
  cal=json.dumps({'schema':'contract-lifecycle-1','symbols':{},'sources':{},'unlisted_symbol_policy':'LEGACY_CONTINUITY_UNAUDITED'}).encode();h=hashlib.sha256(cal).hexdigest();reg=json.dumps({'schema':'lifecycle-registry-1','calendar_sha256':h,'events':[]}).encode()
  life=load_book_lifecycle(np.array(['X']),cal,h,reg,hashlib.sha256(reg).hexdigest(),lambda p:None)
  kw=dict(initial_capital=100.,fee_bps=3.52,new_risk_allowed=np.ones((3,1),bool),funding_events=[event(1500)],funding_coverage=np.ones((3,1),bool),execution_observed_activity=np.ones((3,1),bool))
  args=(np.array([1000,2000,3000]),np.array([[100.],[110.],[105.]]),np.array([[1.],[-1.],[0.]]))
  old=replay_book(*args,**kw);new=replay_book_lifecycle(*args,**kw,lifecycle=life,same_ms_order=ORDER)
  for key in ['q_after','equity_proxy','cash_proxy','price_pnl','fee','funding_proxy','trade_cash']:np.testing.assert_allclose(new[key],old[key])
  self.assertAlmostEqual(new['research_proxy_net'],old['research_proxy_net'])
if __name__=='__main__':unittest.main(verbosity=2)

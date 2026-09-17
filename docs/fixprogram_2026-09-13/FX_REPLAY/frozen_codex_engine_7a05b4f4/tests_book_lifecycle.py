import hashlib,json,unittest
import numpy as np
try:
 from book_engine_lifecycle import load_book_lifecycle,replay_book_lifecycle
except ImportError:
 from book_engine import replay_book
 def load_book_lifecycle(*a,**k):return None
 def replay_book_lifecycle(*a,**k):
  for n in ['lifecycle','terminal_exclusive_ms','funding_coverage_at','same_ms_order']:k.pop(n,None)
  return replay_book(*a,**k)

def fixture(symbols=('X',),price=None,fee=None,opened=False):
 texts={};entries={};sources={};facts=[]
 for sym in symbols:
  close_id=sym+'close';texts[close_id+'.txt']=close_id.encode();sources[close_id]={'url':'https://www.binance.com/en/support/announcement/detail/'+close_id,'text_path':close_id+'.txt','text_sha256':hashlib.sha256(close_id.encode()).hexdigest(),'published_at_ms':500}
  transitions=[{'kind':'CLOSE','instrument_id':sym+'#old','underlying':'old','announced_at_ms':500,'effective_ms':1500,'source_id':close_id}]
  if opened:
   key=sym+'open';texts[key+'.txt']=key.encode();sources[key]={'url':'https://www.binance.com/en/support/announcement/detail/'+key,'text_path':key+'.txt','text_sha256':hashlib.sha256(key.encode()).hexdigest(),'published_at_ms':2000};transitions.append({'kind':'OPEN','instrument_id':sym+'#new','underlying':'new','announced_at_ms':2000,'effective_ms':2500,'source_id':key})
  entries[sym]={'initial_generation':{'instrument_id':sym+'#old','underlying':'old','birth_ms':None,'birth_evidence':'UNKNOWN'},'transitions':transitions}
  facts.append({'event_id':close_id,'instrument_id':sym+'#old','symbol':sym,'effective_ms':1500,'published_ms':500,'time_evidence':'OFFICIAL_SCHEDULED','settlement_price':price,'fee_rate':fee,'value_evidence':'EXACT' if price is not None and fee is not None else 'UNKNOWN','source_path':close_id+'.txt','source_url':sources[close_id]['url'],'source_sha256':sources[close_id]['text_sha256']})
 cal=json.dumps({'schema':'contract-lifecycle-1','unlisted_symbol_policy':'LEGACY_CONTINUITY_UNAUDITED','symbols':entries,'sources':sources}).encode();reg=json.dumps({'schema':'lifecycle-registry-1','calendar_sha256':hashlib.sha256(cal).hexdigest(),'events':facts}).encode()
 return load_book_lifecycle(np.array(symbols),cal,hashlib.sha256(cal).hexdigest(),reg,hashlib.sha256(reg).hexdigest(),lambda p:texts[p])
def event(t,asset=0,rate=.01):return {'event_ms':t,'asset':asset,'rate':rate,'mark':100.,'mark_kind':'EXACT','kind':'Regular','interval_hours':8.}
def run(t,p,w,life,events=(),**kw):
 p=np.array(p,float);return replay_book_lifecycle(np.array(t,np.int64),p,np.array(w,float),initial_capital=100.,fee_bps=0.,new_risk_allowed=np.ones(p.shape,bool),funding_events=list(events),funding_coverage=kw.pop('funding_coverage',np.ones(p.shape,bool)),execution_observed_activity=np.ones(p.shape,bool),lifecycle=life,same_ms_order='funding_close_open_rebalance',**kw)
class BookLifecycleTests(unittest.TestCase):
 def test_unknown_settlement_zero_old_inventory_not_future_funding(self):
  r=run([1000,2000],[[100],[np.nan]],[[1],[0]],fixture(),[event(1800)])
  self.assertEqual(r['q_after'][-1,0],0);self.assertEqual(r['state']['total_funding_proxy'],0);self.assertIsNone(r['research_proxy_net']);self.assertEqual(len(r['state']['settlement_claims']),1)
 def test_known_settlement_funding_then_close_cash_identity(self):
  r=run([1000,2000],[[100],[np.nan]],[[1],[0]],fixture(price=110,fee=.01),[event(1500)])
  self.assertAlmostEqual(r['research_proxy_net'],7.9);self.assertLess(r['max_cash_identity_error'],1e-12)
 def test_same_ms_multiple_names_batch_order(self):
  r=run([1000,2000],[[100,100],[np.nan,np.nan]],[[.5,.5],[0,0]],fixture(('X','Y'),100,0),[event(1500,0),event(1500,1)])
  self.assertAlmostEqual(r['research_proxy_net'],-1);self.assertEqual(r['state']['settlement_event_count'],2)
 def test_new_generation_does_not_reuse_old_quantity(self):
  r=run([1000,2000,3000],[[100],[np.nan],[20]],[[1],[0],[1]],fixture(opened=True),[event(2800)])
  self.assertEqual(r['q_after'][:,0].tolist(),[1,0,5]);self.assertEqual(r['state']['instrument_ids'],['X#new']);self.assertEqual(r['state']['settlement_claims'][0]['instrument_id'],'X#old')
 def test_restart_during_old_generation_matches_full(self):
  life=fixture(opened=True);full=run([1000,2000,3000],[[100],[np.nan],[20]],[[1],[0],[1]],life,[event(1800)])
  first=run([1000],[[100]],[[1]],life,[]);tail=run([2000,3000],[[np.nan],[20]],[[0],[1]],life,[event(1800)],initial_state=json.loads(json.dumps(first['state'])))
  self.assertEqual(full['state'],tail['state'])
 def test_terminal_left_limit_excludes_exact_T(self):
  life=fixture(price=100,fee=0)
  r=run([1000,1400],[[100],[100]],[[1],[1]],life,[event(1399),event(1400)],rebalance=np.array([True,False]),terminal_exclusive_ms=1400)
  self.assertEqual(r['state']['total_funding_proxy'],-1);self.assertAlmostEqual(r['research_proxy_net'],-1)
 def test_first_instant_funding_before_initial_trade_is_zero(self):
  r=run([1000,1400],[[100],[100]],[[1],[1]],fixture(),[event(1000)],rebalance=np.array([True,False]));self.assertEqual(r['state']['total_funding_proxy'],0)
 def test_prior_unknown_funding_remains_after_known_close(self):
  r=run([1000,2000],[[100],[100]],[[1],[0]],fixture(price=100,fee=0),funding_coverage=np.array([[True],[False]]));self.assertIsNone(r['research_proxy_net']);self.assertGreater(r['state']['missing_funding_coverage_cells'],0)
 def test_coverage_is_clipped_at_termination(self):
  calls=[]
  def cover(j,start,stop):calls.append((j,start,stop));return stop<=1501
  r=run([1000,2000],[[100],[100]],[[1],[0]],fixture(price=100,fee=0),funding_coverage=np.array([[True],[False]]),funding_coverage_at=cover);self.assertEqual(r['research_proxy_net'],0);self.assertIn((0,1001,1501),calls)
if __name__=='__main__':unittest.main(verbosity=2)

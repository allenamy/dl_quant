"""Order-level recovery cash supplement. Pooled, offline after capture, no invented trade time."""
import argparse,collections,hashlib,json,math,sys,time
from pathlib import Path
import actual_cash_bridge as B
SETTLED='userTrades child fills joined on orderId (de-duplicated by trade id)'
START=1790498804.639903;END=1790512741.643611
PARENT=Path('/Users/haosiyu/.codex/tmp/actual_cash_bridge_20260928')
ORDER_KEYS=('symbol','side','order_type','client_id','submit_ts','submit_ts_source','first_fill_ts','last_fill_ts','filled_qty','filled_known_qty','filled_notional','filled_known_notional','filled_unknown_qty','filled_unknown_residual','avg_fill_px','fee_paid','fee_all_usdt','fee_assets','fee_source','filled_notional_source','request_ledger','terminal_reason','flatten_error')
REQ_KEYS=('client_id','order_id','qty','state','status','terminal','confirmed_qty','confirmed_notional','confirmed_qty_final','confirmed_notional_final','trade_qty','trade_quote','settled_by','inconsistent')
def valid(v):return type(v) in (int,float) and math.isfinite(v)
def eq(a,b):return valid(a) and valid(b) and abs(a-b)<=max(1e-9,1e-10*max(abs(a),abs(b)))
def demand(ok,why):
 if not ok:raise ValueError(why)
def unique(items,key):
 out={}
 for x in items:
  k=key(x)
  if k in out:demand(out[k]==x,'conflicting_duplicate')
  out[k]=x
 return list(out.values())
def aggregate(rows,summaries,t0,t1,existing_trade_ids):
 demand(t1>t0,'bad_window')
 summaries=unique(summaries,lambda r:(r.get('symbol'),r.get('client_id')))
 sm={(r.get('symbol'),r.get('client_id')):r for r in summaries}
 demand(sm and all(isinstance(k[0],str) and k[0] and isinstance(k[1],str) and k[1] for k in sm),'summary_identity')
 # Duplicate copies of one request-bearing row are idempotent; different copies fail.
 rows=unique(rows,lambda r:(r.get('symbol'),tuple(q.get('client_id') for q in (r.get('request_ledger') or []))))
 seen_oids=set();seen_cids=set();children={};seen_summaries=set();fees=[]
 for row in rows:
  s=row.get('symbol');side=str(row.get('side','')).upper();demand(side in ('BUY','SELL'),'row_side');sign=1 if side=='BUY' else -1
  first,last=row.get('first_fill_ts'),row.get('last_fill_ts')
  demand(valid(first) and valid(last) and t0<first<=last<=t1,'fill_envelope_crosses_window')
  reqs=row.get('request_ledger');demand(isinstance(reqs,list) and bool(reqs),'missing_requests')
  demand(all(v is None or (valid(v) and v==0) for v in (row.get('filled_unknown_qty'),row.get('filled_unknown_residual'))),'row_unknown_residual')
  qsum=[];nsum=[]
  for q in reqs:
   demand(isinstance(q.get('client_id'),str) and q['client_id'] and type(q.get('order_id')) is int and q['order_id']>0,'request_identity')
   cid=(s,q['client_id']);oid=(s,q['order_id'])
   demand(cid not in seen_cids and oid not in seen_oids,'request_identity_reused');seen_cids.add(cid);seen_oids.add(oid)
   demand(q.get('terminal') is True and q.get('state')=='confirmed' and q.get('confirmed_qty_final') is True and q.get('confirmed_notional_final') is True,'request_final_evidence')
   demand(not q.get('inconsistent') and q.get('settled_by')==SETTLED,'request_settlement_provenance')
   for k in ('qty','confirmed_qty','confirmed_notional'):demand(valid(q.get(k)),'request_nonfinite_'+k)
   demand(sign*q['qty']>0 and sign*q['confirmed_qty']>0 and sign*q['confirmed_notional']>0,'request_side')
   demand(abs(q['confirmed_qty'])<=abs(q['qty'])+1e-8,'confirmed_exceeds_requested')
   tq=q.get('trade_qty');tn=q.get('trade_quote');demand(isinstance(tq,dict) and tq and isinstance(tn,dict) and set(tq)==set(tn),'child_population')
   demand(all(isinstance(t,str) and t.isdecimal() and valid(tq[t]) and tq[t]>0 and valid(tn[t]) and tn[t]>0 for t in tq),'child_nonfinite_or_synthetic_identity')
   qv=sign*math.fsum(tq.values());nv=sign*math.fsum(tn.values())
   demand(eq(qv,q['confirmed_qty']) and eq(nv,q['confirmed_notional']),'child_totals_disagree')
   demand(cid in sm,'missing_summary');summary=sm[cid];seen_summaries.add(cid)
   demand(str(summary.get('side','')).upper()==side and eq(summary.get('filled_notional'),nv) and eq(summary.get('avg_fill_px'),abs(nv/qv)),'summary_amount_or_side')
   demand(summary.get('first_fill_ts')==first and summary.get('last_fill_ts')==last,'summary_time')
   for tid in tq:
    k=(s,tid);demand(k not in existing_trade_ids,'overlap_existing_fills');demand(k not in children,'child_reused_across_orders')
    children[k]={'symbol':s,'trade_id':tid,'order_id':q['order_id'],'client_id':q['client_id'],'qty':sign*tq[tid],'quote':sign*tn[tid],'first_possible_ts':first,'last_possible_ts':last,'exact_fill_ts':None}
   qsum.append(qv);nsum.append(nv)
  qq,nn=math.fsum(qsum),math.fsum(nsum)
  for k,val in [('filled_qty',qq),('filled_known_qty',qq),('filled_notional',nn),('filled_known_notional',nn),('avg_fill_px',abs(nn/qq))]:demand(eq(row.get(k),val),'row_total_'+k)
  demand(row.get('fee_all_usdt') is True and row.get('fee_assets')==['USDT'] and valid(row.get('fee_paid')),'fee_currency_unknown')
  demand(str(row.get('fee_source','')).startswith('/fapi/v1/userTrades,'),'fee_not_from_children');fees.append(row['fee_paid'])
 demand(seen_summaries==set(sm),'summary_population_not_closed')
 qs=collections.defaultdict(list);ns=collections.defaultdict(list)
 for c in children.values():qs[c['symbol']].append(c['qty']);ns[c['symbol']].append(c['quote'])
 return {'rows':len(rows),'summaries':len(sm),'requests':len(seen_oids),'children':list(children.values()),'qty':{s:math.fsum(v) for s,v in qs.items()},'quote':{s:math.fsum(v) for s,v in ns.items()},'fee_usdt':math.fsum(fees)}
def capture(root):
 demand(3600<=time.time()%14400<13200,'outside_quiet')
 sys.path.insert(0,str(Path(__file__).parents[2]/'common'))
 from venue_quiet_window import quiet_window_status
 quiet=quiet_window_status();demand(quiet['open'] and not quiet['override'] and not quiet.get('anchor_in_progress') and not quiet.get('stale_start'),'quiet_unverified')
 root.mkdir(exist_ok=False)
 p=Path.home()/'dl_quant_live/state/live/pilot_log/20260927/orders.jsonl';raw=p.read_bytes();(root/'orders_original.jsonl').write_bytes(raw)
 rs=B.strict_jl(raw);out=[]
 for r in rs:
  d={k:r[k] for k in ORDER_KEYS if k in r}
  if isinstance(d.get('request_ledger'),list):d['request_ledger']=[{k:q[k] for k in REQ_KEYS if k in q} for q in d['request_ledger']]
  out.append(d)
 B.put(root/'ORDERS.json',out)
 B.put(root/'CAPTURE.json',{'utc':time.strftime('%FT%TZ',time.gmtime()),'quiet':quiet,'source_path':str(p),'source_sha256':B.sha(raw),'orders_sha256':B.sha((root/'ORDERS.json').read_bytes()),'device_sha256':B.sha(Path(__file__).read_bytes())})
 print(json.dumps({'capture':str(root),'raw_bytes':len(raw)}))
def main(root):
 cap=json.loads((root/'CAPTURE.json').read_text());raw=(root/'ORDERS.json').read_bytes();demand(B.sha(raw)==cap['orders_sha256'],'orders_changed')
 parent_raw=(PARENT/'RESULT.json').read_bytes();demand(B.sha(parent_raw)=='7ccc360d2b0d6597a617850fa23d064f4b48f728ec47d44afd5b36e5e6e6b5b1','parent_result_changed')
 parent=json.loads(parent_raw);w=next(w for w in parent['windows'] if w['from']==START and w['to']==END)
 data_raw=(PARENT/'INPUT.json').read_bytes();demand(B.sha(data_raw)==parent['input_sha256'],'parent_input_changed');data=json.loads(data_raw);basefills=B.trades(data['fills']);demand(w['fills']==0,'local_fills_population_nonempty')
 allrows=json.loads(raw)
 # Use fill-envelope intersection: a crossing record is selected and then rejected, never silently dropped.
 summaries=[r for r in allrows if r.get('order_type')=='protective_flatten' and valid(r.get('first_fill_ts')) and valid(r.get('last_fill_ts')) and r['last_fill_ts']>START and r['first_fill_ts']<=END]
 wanted={(r.get('symbol'),r.get('client_id')) for r in summaries}
 rows=[r for r in allrows if r.get('order_type')=='topup_taker' and any((r.get('symbol'),q.get('client_id')) in wanted for q in (r.get('request_ledger') or []))]
 agg=aggregate(rows,summaries,START,END,{(t['symbol'],t['trade_id']) for t in basefills})
 def snap(anchor):
  a=next(s['execution_anchor'] for s in parent['snapshots'] if s['anchor']==anchor);obs=data['observations'][str(a)];demand(len(obs)==1,'phase_C_identity')
  return B.snapshot([r for r in data['readbacks'] if r.get('anchor_ts')==a and r.get('source')==B.SOURCE],obs[0]['observation'])
 a,b=snap(w['anchor_from']),snap(w['anchor_to']);bad=[];cash=[];errmax=0.
 for s in sorted(set(a['positions'])|set(b['positions'])|set(agg['qty'])):
  x=a['positions'].get(s,{'qty':0.,'notional':0.});y=b['positions'].get(s,{'qty':0.,'notional':0.});q=agg['qty'].get(s,0.)
  e=x['qty']+q-y['qty'];marks=[abs(z['notional']/z['qty']) for z in (x,y) if z['qty']]
  if not marks and q:marks=[abs(agg['quote'][s]/q)]
  ev=abs(e)*max(marks) if marks else (0. if e==0 else None)
  if ev is None or ev>.01:bad.append({'symbol':s,'residual_qty':e,'residual_equiv_usdt':ev})
  if ev is not None:errmax=max(errmax,ev)
  cash.append(y['notional']-x['notional']-agg['quote'].get(s,0.))
 income_raw=(PARENT/'income_diagnostic/RESULT.json').read_bytes();inc=json.loads(income_raw);iw=next(x for x in inc['windows'] if x['from']==START and x['to']==END)
 commission=math.fsum(x['amount'] for x in iw['income_native'] if x['type']=='COMMISSION' and x['asset']=='USDT')
 result={'utc':time.strftime('%FT%TZ',time.gmtime()),'from':START,'to':END,'parent_result_sha256':B.sha(parent_raw),'income_result_sha256':B.sha(income_raw),'orders_sha256':B.sha(raw),'device_sha256':B.sha(Path(__file__).read_bytes()),
  'aggregate':agg,'original_quantity_failures':len(w['quantity_failures']),'supplement_quantity_verdict':'INCONSISTENT' if bad else 'ORDER_IDENTITY_CONSISTENT','quantity_failures':bad,'max_quantity_residual_equiv_usdt':errmax,
  'price_trade_cash_usdt':None if bad else math.fsum(cash),'commission_native_comparison':{'USDT_income':commission,'USDT_request_rows':agg['fee_usdt'],'sum_should_zero':commission+agg['fee_usdt']},
  'full_cash_verdict':'UNAVAILABLE_INCOME_COMPLETENESS_AND_USD_VALUATION','limits':['order ledger child-identity quantities and amounts, not original signed API payload','exact individual child execution time absent; use whole bounded envelope only','do not inject a synthetic timestamp into a continuous simulator','original baseline retained; no production ledger write','no CFG04/06 arm outcomes','does not close old-executor or STG gaps; does not measure flatten action cost']}
 B.put(root/'RESULT.json',result)
 print(json.dumps({k:result[k] for k in ('supplement_quantity_verdict','original_quantity_failures','max_quantity_residual_equiv_usdt','price_trade_cash_usdt','commission_native_comparison')}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['capture','analyze']);p.add_argument('root',type=Path);a=p.parse_args();(capture if a.mode=='capture' else main)(a.root)

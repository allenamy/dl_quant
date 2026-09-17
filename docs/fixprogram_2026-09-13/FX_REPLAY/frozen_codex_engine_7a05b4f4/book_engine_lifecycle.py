"""Version 4 research ledger with source-bound instrument termination batches.

Frozen v3 stays unchanged. Events retain exact milliseconds. At equal times the
explicit research order is funding, close, open, then ordinary rebalance.
"""
import copy,hashlib,json,math
import numpy as np
from book_engine import _events,_finite,_funding_prefix_step,FUNDING_PREFIX_SEED
from funding_generation import validate_calendar
from lifecycle_events import load_registry,new_state,settle,restore as restore_settlement,canonical
CONTRACT='full-position-cash-20260914-v4-lifecycle'
ORDER='funding_close_open_rebalance'

class BookLifecycle:
 def __init__(self,symbols,calendar_sha,registry_sha,registry,initial,events,calendar_payload):
  self.symbols=tuple(symbols);self.calendar_sha=calendar_sha;self.registry_sha=registry_sha
  self.registry=registry;self.initial=tuple(initial);self.events=tuple(events)
  self.calendar_payload=calendar_payload

def load_book_lifecycle(symbols,calendar_body,calendar_sha256,registry_body,registry_sha256,source_reader):
 sy=np.asarray(symbols)
 if sy.ndim!=1 or sy.dtype.kind not in 'US' or len(set(sy.tolist()))!=len(sy):raise ValueError('lifecycle exact symbol axis')
 if hashlib.sha256(calendar_body).hexdigest()!=calendar_sha256:raise ValueError('calendar SHA binding')
 calendar=json.loads(calendar_body);validate_calendar(calendar,source_reader=source_reader)
 if json.loads(registry_body).get('calendar_sha256')!=calendar_sha256:raise ValueError('cash registry calendar SHA binding')
 registry=load_registry(registry_body,registry_sha256,source_reader);initial=[str(s)+'#legacy-unaudited' for s in sy];events=[];close_by_id={}
 for payload in registry.payloads.values():
  event=json.loads(payload);ix=np.flatnonzero(sy==event['symbol'])
  if len(ix)!=1:raise ValueError('settlement registry symbol outside book axis')
  j=int(ix[0]);close_by_id[event['instrument_id']]=event
  if event['symbol'] not in calendar['symbols']:initial[j]=event['instrument_id']
  events.append((event['effective_ms'],1,j,'CLOSE',event))
 for name,entry in calendar['symbols'].items():
  ix=np.flatnonzero(sy==name)
  if len(ix)!=1:raise ValueError('calendar symbol outside book axis')
  j=int(ix[0]);initial[j]=entry['initial_generation']['instrument_id']
  for event in entry['transitions']:
   if event['kind']=='CLOSE':
    fact=close_by_id.get(event['instrument_id'])
    if fact is None or fact['effective_ms']!=event['effective_ms'] or fact['symbol']!=name:raise ValueError('calendar close must bind an explicit cash registry fact')
   else:events.append((event['effective_ms'],2,j,'OPEN',event))
 events.sort(key=lambda r:(r[0],r[1],r[2]))
 current=list(initial);inactive=[False]*len(sy)
 for when,priority,j,kind,event in events:
  if kind=='CLOSE':
   if current[j]!=event['instrument_id'] or inactive[j]:raise ValueError('lifecycle cash instrument sequence')
   inactive[j]=True
  else:
   if not inactive[j]:raise ValueError('generation opened without prior termination')
   current[j]=event['instrument_id'];inactive[j]=False
 return BookLifecycle(sy.tolist(),calendar_sha256,registry_sha256,registry,initial,events,canonical(calendar))

def replay_book_lifecycle(ts_ms,prices,weights,*,initial_capital,fee_bps,new_risk_allowed,funding_events,funding_coverage,lifecycle,same_ms_order,initial_state=None,pit_unknown=None,rebalance=None,execution_observed_activity=None,terminal_exclusive_ms=None,funding_coverage_at=None,valuation_left_limit=None):
 if not isinstance(lifecycle,BookLifecycle) or same_ms_order!=ORDER:raise ValueError('source-bound lifecycle and explicit same-ms research order required')
 t=np.asarray(ts_ms);p=np.asarray(prices,float);w=np.asarray(weights,float);allow=np.asarray(new_risk_allowed);cover=np.asarray(funding_coverage)
 if t.ndim!=1 or t.dtype.kind not in 'iu' or not len(t) or (t<0).any() or (t>np.iinfo(np.int64).max-1).any():raise ValueError('cash clock')
 t=t.astype(np.int64)
 if (np.diff(t)<=0).any() or p.ndim!=2 or len(p)!=len(t) or w.shape!=p.shape or allow.shape!=p.shape or cover.shape!=p.shape or allow.dtype.kind!='b' or cover.dtype.kind!='b' or p.shape[1]!=len(lifecycle.symbols):raise ValueError('cash axes')
 if not math.isfinite(initial_capital) or initial_capital<=0 or not math.isfinite(fee_bps) or fee_bps<0:raise ValueError('capital/fee contract')
 _finite(w,'target weights');n=p.shape[1]
 unknown=np.zeros(p.shape,bool) if pit_unknown is None else np.asarray(pit_unknown)
 trading=np.ones(len(t),bool) if rebalance is None else np.asarray(rebalance)
 activity=np.ones(p.shape,bool) if execution_observed_activity is None else np.asarray(execution_observed_activity)
 if unknown.shape!=p.shape or unknown.dtype.kind!='b' or activity.shape!=p.shape or activity.dtype.kind!='b' or trading.shape!=(len(t),) or trading.dtype.kind!='b':raise ValueError('execution/PIT axes')
 if terminal_exclusive_ms is not None and (type(terminal_exclusive_ms) is not int or terminal_exclusive_ms!=int(t[-1]) or trading[-1]):raise ValueError('terminal left limit must be final nontrading valuation')
 left_limit=np.zeros(len(t),bool) if valuation_left_limit is None else np.asarray(valuation_left_limit)
 if left_limit.shape!=(len(t),) or left_limit.dtype.kind!='b' or (left_limit&trading).any():raise ValueError('left-limit snapshots must be boolean nontrading rows')
 left_limit=left_limit.copy()
 if terminal_exclusive_ms is not None:left_limit[-1]=True
 if funding_coverage_at is not None and not callable(funding_coverage_at):raise ValueError('coverage callback')
 events=_events(funding_events,n);lives=lifecycle.events
 keys=('unpriced_holding_cells','missing_funding_coverage_cells','unpriced_funding_events','proxy_mark_events','unverified_interval_events')
 if initial_state is None:
  q=np.zeros(n);cash=float(initial_capital);last=np.full(n,np.nan);last_ts=None;prior_equity=float(initial_capital);state={k:0 for k in keys}
  totals={k:0. for k in ['total_fees','total_funding_proxy','total_trade_cash','total_settlement_cash','blocked_new_risk_notional','unknown_pit_notional_time']};blocked_price=blocked_exec=rows_done=0
  ids=list(lifecycle.initial);inactive=np.zeros(n,bool);settlement_records=[];life_ix=0;prefix_count=0;prefix_sha=FUNDING_PREFIX_SEED;consumed_exclusive=0
 else:
  s=initial_state
  if s.get('contract')!=CONTRACT or s.get('calendar_sha256')!=lifecycle.calendar_sha or s.get('registry_sha256')!=lifecycle.registry_sha or s.get('same_ms_order')!=ORDER:raise ValueError('lifecycle restart binding requires_replay')
  if s.get('initial_capital')!=initial_capital or s.get('fee_bps')!=fee_bps:raise ValueError('restart capital/fee mismatch')
  q=np.asarray(s['q'],float);last=np.array([np.nan if x is None else x for x in s['last_prices']]);cash=float(s['cash_proxy']);last_ts=s['last_ts_ms'];prior_equity=s['last_equity_proxy'];state={k:int(s[k]) for k in keys}
  if q.shape!=(n,) or last.shape!=(n,) or type(last_ts) is not int or last_ts>=int(t[0]) or any(v<0 for v in state.values()):raise ValueError('restart axes/counts')
  _finite(q,'restart q');_finite(cash,'restart cash');totals={k:float(s[k]) for k in ['total_fees','total_funding_proxy','total_trade_cash','total_settlement_cash','blocked_new_risk_notional','unknown_pit_notional_time']};_finite(np.array(list(totals.values())),'restart totals')
  blocked_price=int(s['blocked_price_trade_cells']);blocked_exec=int(s['blocked_execution_trade_cells']);rows_done=int(s['rows_done']);ids=list(s['instrument_ids']);inactive=np.asarray(s['inactive'],bool)
  consumed_exclusive=s['event_consumed_exclusive_ms'];life_ix=s['lifecycle_prefix_count'];prefix_count=s['funding_prefix_count'];prefix_sha=s['funding_prefix_sha256']
  if type(consumed_exclusive) is not int or consumed_exclusive not in (last_ts,last_ts+1) or type(life_ix) is not int or type(prefix_count) is not int or prefix_count<0 or not isinstance(prefix_sha,str) or len(prefix_sha)!=64 or any(x not in '0123456789abcdef' for x in prefix_sha):raise ValueError('restart event prefix requires_replay')
  if prefix_count==0 and prefix_sha!=FUNDING_PREFIX_SEED:raise ValueError('restart empty funding prefix requires_replay')
  expected_ids=list(lifecycle.initial);expected_inactive=np.zeros(n,bool);expected_count=0
  for when,priority,j,kind,event in lives:
   if when>=consumed_exclusive:break
   expected_count+=1
   if kind=='CLOSE':expected_inactive[j]=True
   else:expected_ids[j]=event['instrument_id'];expected_inactive[j]=False
  if life_ix!=expected_count or ids!=expected_ids or inactive.shape!=(n,) or not np.array_equal(inactive,expected_inactive) or (inactive&(q!=0)).any():raise ValueError('restart lifecycle population requires_replay')
  expected_closes=[row for row in lives[:life_ix] if row[3]=='CLOSE']
  if len(s['settlement_records'])!=len(expected_closes) or s.get('settlement_event_count')!=len(expected_closes):raise ValueError('restart settlement receipt count requires_replay')
  settlement_records=[]
  for part,row in zip(s['settlement_records'],expected_closes):
   when,priority,j,kind,event=row;event_id=event['event_id']
   if not isinstance(part,dict) or not isinstance(part.get('processed_settlements'),dict) or set(part['processed_settlements'])!={event_id}:raise ValueError('restart settlement prefix order binding requires_replay')
   receipt=part['processed_settlements'][event_id]
   if not isinstance(receipt,dict) or canonical(receipt.get('event'))!=lifecycle.registry.payloads[event_id] or receipt.get('registry_sha256')!=lifecycle.registry_sha:raise ValueError('restart settlement fixed registry binding requires_replay')
   rebuilt=settle(new_state(0.,{event['instrument_id']:receipt['quantity_before']}),event,lifecycle.registry,asof_ms=when)
   if canonical(part)!=canonical(rebuilt):raise ValueError('restart settlement cash/claim receipt binding requires_replay')
   settlement_records.append(rebuilt)
  expected_claims=[c for r in settlement_records for c in r['claims']]
  if canonical(expected_claims)!=canonical(s['settlement_claims']):raise ValueError('restart settlement claims require replay')
 historical=FUNDING_PREFIX_SEED;event_ix=0
 while event_ix<len(events) and events[event_ix][0]<consumed_exclusive:
  historical=_funding_prefix_step(historical,events[event_ix]);event_ix+=1
 if event_ix and (event_ix!=prefix_count or historical!=prefix_sha):raise ValueError('historical funding changed_or_incomplete requires_replay')
 output={k:[] for k in ['q_after','cash_proxy','equity_proxy','price_pnl','funding_proxy','fee','turnover_notional','trade_cash','gross_notional','accounting_complete','settlement_cash','settlement_fee','other_cash_complete','valuation_complete','execution_complete','endpoint_complete','settlement_claim_count']};issues=[];max_error=0.
 for i,stamp_value in enumerate(t):
  stamp=int(stamp_value);limit=stamp if left_limit[i] else stamp+1
  before=q.copy();closed_stop=np.full(n,limit,np.int64);settlement_cash=settlement_fee=settlement_pl=0.;settlement_pl_known=True;fund=0.;event_missing=False
  while True:
   ft=events[event_ix][0] if event_ix<len(events) else limit;lt=lives[life_ix][0] if life_ix<len(lives) else limit
   if min(ft,lt)>=limit:break
   if ft<=lt:
    row=events[event_ix];et,j,rate,mark,mk,kind,iv=row;event_ix+=1;prefix_sha=_funding_prefix_step(prefix_sha,row);prefix_count+=1
    if q[j]==0:continue
    if iv is None:state['unverified_interval_events']+=1
    if not math.isfinite(rate) or not math.isfinite(mark) or mark<=0 or mk=='MISSING':
     state['unpriced_funding_events']+=1;event_missing=True;issues.append({'row':i,'ts_ms':int(et),'kind':'unpriced_funding','assets':[j]});continue
    flow=-q[j]*mark*rate;_finite(flow,'funding cash');fund+=flow
    if mk=='CLOSE_PROXY':state['proxy_mark_events']+=1
   else:
    when,priority,j,kind,event=lives[life_ix];life_ix+=1
    if kind=='OPEN':
     if q[j]!=0 or not inactive[j]:raise ValueError('new generation cannot inherit old inventory')
     ids[j]=event['instrument_id'];inactive[j]=False
    else:
     if ids[j]!=event['instrument_id'] or inactive[j]:raise ValueError('settlement must close stored old instrument identity')
     held_qty=float(q[j]);part=settle(new_state(0.,{ids[j]:held_qty}),event,lifecycle.registry,asof_ms=when);settlement_records.append(part)
     flow=part['known_cash'];settlement_cash+=flow
     if held_qty!=0:
      closed_stop[j]=when+1
      if event['value_evidence']=='EXACT':
       settlement_fee+=abs(held_qty)*event['settlement_price']*event['fee_rate']
       if np.isfinite(last[j]) and last[j]>0:settlement_pl+=held_qty*(event['settlement_price']-last[j])
       else:settlement_pl_known=False
      else:
       settlement_pl_known=False;issues.append({'row':i,'ts_ms':int(when),'kind':'unresolved_forced_settlement','assets':[j],'instrument_id':ids[j],'quantity':held_qty,'last_sampled_mark':float(last[j]) if np.isfinite(last[j]) else None})
     q[j]=0.;inactive[j]=True
  _finite(np.array([fund,settlement_cash,settlement_fee,settlement_pl]),'event batch aggregate')
  need_cover=before!=0;covered=cover[i].copy()
  if funding_coverage_at is not None:
   for j in np.flatnonzero(need_cover):
    answer=funding_coverage_at(int(j),int(consumed_exclusive),int(closed_stop[j]))
    if type(answer) not in (bool,np.bool_):raise ValueError('coverage callback must return explicit boolean')
    covered[j]=answer
  unknown_cover=need_cover&~covered;state['missing_funding_coverage_cells']+=int(unknown_cover.sum())
  if unknown_cover.any():issues.append({'row':i,'ts_ms':stamp,'kind':'missing_funding_coverage','assets':np.flatnonzero(unknown_cover).tolist()})
  prev=q.copy();held=prev!=0;valid=np.isfinite(p[i])&(p[i]>0);missing=held&~valid;state['unpriced_holding_cells']+=int(missing.sum())
  if missing.any():issues.append({'row':i,'ts_ms':stamp,'kind':'unpriced_holding','assets':np.flatnonzero(missing).tolist()})
  with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
   usd=w[i]*initial_capital;desired=prev.copy();np.divide(usd,p[i],out=desired,where=valid)
  _finite(usd,'notional');_finite(desired,'desired quantity');blocked_price+=int(((~valid)&((prev!=0)|(usd!=0))&trading[i]&~inactive).sum())
  unrestricted=desired.copy();same=np.sign(desired)==np.sign(prev);reduce=np.where(same,np.sign(prev)*np.minimum(np.abs(prev),np.abs(desired)),0.)
  permitted=allow[i]&~inactive;desired=np.where(permitted,desired,reduce);desired=np.where(valid,desired,prev)
  if not trading[i]:desired=prev.copy();unrestricted=prev.copy()
  risk_desired=desired.copy();blocked_activity=(desired!=prev)&~activity[i];blocked_exec+=int(blocked_activity.sum())
  if blocked_activity.any():issues.append({'row':i,'ts_ms':stamp,'kind':'unobservable_execution','assets':np.flatnonzero(blocked_activity).tolist()})
  desired=np.where(blocked_activity,prev,desired)
  with np.errstate(over='ignore',invalid='ignore'):
   blocked=float(np.where(valid,np.abs(unrestricted-risk_desired)*p[i],0.).sum());dq=desired-prev;notional=np.zeros(n);np.multiply(dq,p[i],out=notional,where=dq!=0)
  _finite(blocked,'blocked notional');_finite(notional,'trade notional');turn=float(np.abs(notional).sum());trade_fee=turn*fee_bps/1e4;fee=trade_fee+settlement_fee;trade_cash=-float(notional.sum())
  _finite(np.array([turn,fee,trade_cash]),'trade cash');cash+=trade_cash+fund+settlement_cash-trade_fee;_finite(cash,'cash balance');q=desired
  with np.errstate(over='ignore',invalid='ignore'):
   marks=np.zeros(n);np.multiply(q,p[i],out=marks,where=q!=0)
  value_known=bool(np.isfinite(marks).all());eq=float(cash+marks.sum()) if value_known else None
  if eq is not None:_finite(eq,'equity')
  price_known=settlement_pl_known and bool((~held|(valid&np.isfinite(last)&(last>0))).all())
  if price_known:
   with np.errstate(over='ignore',invalid='ignore'):pl=float(np.where(held,prev*(p[i]-last),0.).sum())+settlement_pl
   _finite(pl,'price pnl')
  else:pl=np.nan
  if last_ts is None:pl=0.
  if eq is not None and prior_equity is not None and np.isfinite(pl) and not event_missing:
   err=abs(eq-prior_equity-pl-fund+fee);max_error=max(max_error,err)
   if err>1e-9*max(initial_capital,abs(eq),abs(prior_equity),1):raise ValueError('lifecycle cash/share identity mismatch')
  with np.errstate(over='ignore',invalid='ignore'):gross=float(np.abs(marks).sum()) if value_known else np.nan;un=float(np.where(unknown[i]&valid,np.abs(marks),0.).sum())
  _finite(un,'unknown PIT notional')
  totals['blocked_new_risk_notional']+=blocked;totals['unknown_pit_notional_time']+=un;totals['total_fees']+=fee;totals['total_funding_proxy']+=fund;totals['total_trade_cash']+=trade_cash;totals['total_settlement_cash']+=settlement_cash;rows_done+=1
  claims=[c for part in settlement_records for c in part['claims']]
  complete=not claims and not any(state[k] for k in ('unpriced_holding_cells','missing_funding_coverage_cells','unpriced_funding_events')) and value_known and blocked_price==0 and blocked_exec==0
  other_cash_complete=state['missing_funding_coverage_cells']==0 and state['unpriced_funding_events']==0
  endpoint_complete=other_cash_complete and value_known and not claims
  values=[q.copy(),cash,np.nan if eq is None else eq,pl,np.nan if event_missing else fund,fee,turn,trade_cash,gross,complete,settlement_cash,settlement_fee,other_cash_complete,value_known,blocked_price==0 and blocked_exec==0,endpoint_complete,len(claims)]
  for key,value in zip(output,values):output[key].append(value)
  last=p[i].copy();last_ts=stamp;prior_equity=eq;consumed_exclusive=limit
 claims=[c for part in settlement_records for c in part['claims']]
 state.update(contract=CONTRACT,calendar_sha256=lifecycle.calendar_sha,registry_sha256=lifecycle.registry_sha,same_ms_order=ORDER,
  funding_prefix_count=prefix_count,funding_prefix_sha256=prefix_sha,lifecycle_prefix_count=life_ix,event_consumed_exclusive_ms=consumed_exclusive,
  instrument_ids=ids,inactive=inactive.tolist(),settlement_records=settlement_records,settlement_claims=claims,settlement_event_count=len(settlement_records),
  initial_capital=float(initial_capital),fee_bps=float(fee_bps),q=q.tolist(),last_prices=[float(x) if math.isfinite(x) else None for x in last],cash_proxy=float(cash),last_ts_ms=last_ts,last_equity_proxy=prior_equity,
  blocked_price_trade_cells=blocked_price,blocked_execution_trade_cells=blocked_exec,rows_done=rows_done,**totals)
 endpoint=prior_equity is not None and not claims and not state['missing_funding_coverage_cells'] and not state['unpriced_funding_events'];path=not state['unpriced_holding_cells'];execution=blocked_price==0 and blocked_exec==0
 endpoint_net=prior_equity-initial_capital if endpoint else None
 result={k:np.asarray(v) for k,v in output.items()};result.update(contract=CONTRACT,research_proxy_net=endpoint_net if execution else None,realized_simulation_endpoint_net=endpoint_net,endpoint_cash_complete=bool(endpoint),valuation_path_complete=bool(path),execution_counterfactual_complete=bool(execution),certified_cash_net=None,max_cash_identity_error=float(max_error),blocked_new_risk_notional=float(totals['blocked_new_risk_notional']),blocked_price_trade_cells=blocked_price,blocked_execution_trade_cells=blocked_exec,execution_activity_input_provided=execution_observed_activity is not None,issues=issues,state=state,scope='Source-bound announced lifecycle with explicit same-ms ordering assumption; close-proxy marks, fill and fee proxies; no venue-cash/PIT certification')
 return result

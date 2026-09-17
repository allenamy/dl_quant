"""Research share/cash ledger. Full held inventory is independent of entry masks.

Fixed initial-capital notional targets. Settlement precedes rebalance at the
same millisecond. Missing held prices or funding coverage persist as unresolved
history, including after restart. No exchange/PIT/fill certification is implied.
"""
import math,hashlib,json
import numpy as np
CONTRACT='full-position-cash-20260914-v3'
FUNDING_PREFIX_SEED=hashlib.sha256(b'full-position-funding-prefix-v1\n').hexdigest()

def _funding_prefix_step(previous,event):
 row=[None if isinstance(x,float) and math.isnan(x) else x for x in event]
 body=json.dumps(row,separators=(',',':'),allow_nan=False).encode()
 return hashlib.sha256(bytes.fromhex(previous)+body).hexdigest()

def _finite(x,name):
 if not np.isfinite(x).all():raise ValueError(name+' overflow/nonfinite')
 return x

def _events(rows,n):
 facts={}
 for row in rows:
  if not isinstance(row,dict):raise ValueError('funding event must be a mapping')
  t=row.get('event_ms');s=row.get('asset');iv=row.get('interval_hours')
  if isinstance(t,(bool,np.bool_)) or not isinstance(t,(int,np.integer)) or t<0 or isinstance(s,(bool,np.bool_)) or not isinstance(s,(int,np.integer)) or not 0<=s<n:raise ValueError('invalid funding time/asset')
  kind=row.get('kind');mk=row.get('mark_kind');rate=float(row.get('rate',np.nan));mark=float(row.get('mark',np.nan))
  if kind not in ('Regular','Special') or mk not in ('EXACT','CLOSE_PROXY','MISSING'):raise ValueError('invalid funding identity')
  if iv is not None and (isinstance(iv,(bool,np.bool_)) or not math.isfinite(iv) or iv<=0):raise ValueError('invalid funding interval')
  if math.isinf(rate) or math.isinf(mark):raise ValueError('invalid funding value')
  val=(int(t),int(s),rate,mark,mk,kind,None if iv is None else float(iv))
  key=(int(t),int(s),kind)
  if key in facts:
   old=facts[key]
   if any((a!=b and not (isinstance(a,float) and isinstance(b,float) and math.isnan(a) and math.isnan(b))) for a,b in zip(old,val)):raise ValueError('conflicting funding event')
  else:facts[key]=val
 return sorted(facts.values(),key=lambda r:(r[0],r[1],r[5]))

def replay_book(ts_ms,prices,weights,*,initial_capital,fee_bps,new_risk_allowed,funding_events,funding_coverage,initial_state=None,pit_unknown=None,rebalance=None,execution_observed_activity=None):
 t=np.asarray(ts_ms);p=np.asarray(prices,float);w=np.asarray(weights,float);allow=np.asarray(new_risk_allowed);cover=np.asarray(funding_coverage)
 if t.ndim!=1 or t.dtype.kind not in 'iu' or (t<0).any() or (t>np.iinfo(np.int64).max).any():raise ValueError('invalid cash clock')
 t=t.astype(np.int64)
 if not len(t) or (np.diff(t)<=0).any() or p.ndim!=2 or w.shape!=p.shape or len(p)!=len(t) or allow.shape!=p.shape or cover.shape!=p.shape or allow.dtype.kind!='b' or cover.dtype.kind!='b':raise ValueError('cash axes invalid')
 if not math.isfinite(initial_capital) or initial_capital<=0 or not math.isfinite(fee_bps) or fee_bps<0:raise ValueError('invalid capital/fee contract')
 _finite(w,'target weights')
 unknown=np.zeros(p.shape,bool) if pit_unknown is None else np.asarray(pit_unknown)
 if unknown.shape!=p.shape or unknown.dtype.kind!='b':raise ValueError('invalid PIT unknown axes')
 trading=np.ones(len(t),bool) if rebalance is None else np.asarray(rebalance)
 if trading.shape!=(len(t),) or trading.dtype.kind!='b':raise ValueError('rebalance must be explicit boolean clock')
 execution_activity=np.ones(p.shape,bool) if execution_observed_activity is None else np.asarray(execution_observed_activity)
 if execution_activity.shape!=p.shape or execution_activity.dtype.kind!='b':raise ValueError('invalid execution activity axes')
 n=p.shape[1];events=_events(funding_events,n)
 keys=('unpriced_holding_cells','missing_funding_coverage_cells','unpriced_funding_events','proxy_mark_events','unverified_interval_events')
 if initial_state is None:
  q=np.zeros(n);cash=float(initial_capital);last=np.full(n,np.nan);last_ts=None;state={k:0 for k in keys};prior_equity=float(initial_capital);total_fees=0.;total_funding=0.;total_trade_cash=0.;blocked_total=0.;blocked_price_total=0;blocked_execution_total=0;unknown_total=0.;rows_done=0
  funding_prefix_count=0;funding_prefix_sha256=FUNDING_PREFIX_SEED
 else:
  if initial_state.get('contract')!=CONTRACT:raise ValueError('restart contract requires_replay')
  if initial_state.get('initial_capital')!=initial_capital or initial_state.get('fee_bps')!=fee_bps:raise ValueError('restart contract mismatch')
  funding_prefix_count=initial_state.get('funding_prefix_count');funding_prefix_sha256=initial_state.get('funding_prefix_sha256')
  if type(funding_prefix_count) is not int or funding_prefix_count<0 or not isinstance(funding_prefix_sha256,str) or len(funding_prefix_sha256)!=64 or any(x not in '0123456789abcdef' for x in funding_prefix_sha256) or (funding_prefix_count==0 and funding_prefix_sha256!=FUNDING_PREFIX_SEED):raise ValueError('restart funding prefix requires_replay')
  q=np.asarray(initial_state['q'],float);last=np.asarray([np.nan if x is None else x for x in initial_state['last_prices']],float);cash=float(initial_state['cash_proxy']);last_ts=initial_state['last_ts_ms']
  if q.shape!=(n,) or last.shape!=(n,) or not isinstance(last_ts,int) or last_ts>=int(t[0]):raise ValueError('restart axis/clock mismatch')
  _finite(q,'restart quantity');_finite(cash,'restart cash')
  state={k:int(initial_state[k]) for k in keys}
  if any(v<0 for v in state.values()):raise ValueError('invalid restart counts')
  prior_equity=initial_state['last_equity_proxy'];total_fees=initial_state['total_fees'];total_funding=initial_state['total_funding_proxy'];total_trade_cash=initial_state['total_trade_cash'];blocked_total=initial_state['blocked_new_risk_notional'];blocked_price_total=initial_state['blocked_price_trade_cells'];blocked_execution_total=initial_state['blocked_execution_trade_cells'];unknown_total=initial_state['unknown_pit_notional_time'];rows_done=initial_state['rows_done']
 Q=[];cash_rows=[];equity=[];fee_rows=[];fund_rows=[];price_rows=[];turnover_rows=[];trade_cash_rows=[];gross_rows=[];complete_rows=[];issues=[];max_error=0.;event_ix=0
 # A restart accepts a future-only append, or the entire historical event
 # prefix with the same canonical payload. Unseen old facts require replay.
 historical_sha256=FUNDING_PREFIX_SEED
 while event_ix<len(events) and last_ts is not None and events[event_ix][0]<=last_ts:
  historical_sha256=_funding_prefix_step(historical_sha256,events[event_ix]);event_ix+=1
 if event_ix and (event_ix!=funding_prefix_count or historical_sha256!=funding_prefix_sha256):raise ValueError('historical funding changed_or_incomplete requires_replay')
 for i,stamp in enumerate(t):
  prev=q.copy();valid=np.isfinite(p[i])&(p[i]>0);held=prev!=0
  missing=held&~valid;state['unpriced_holding_cells']+=int(missing.sum());state['missing_funding_coverage_cells']+=int((held&~cover[i]).sum())
  if missing.any():issues.append({'row':i,'ts_ms':int(stamp),'kind':'unpriced_holding','assets':np.flatnonzero(missing).tolist()})
  if (held&~cover[i]).any():issues.append({'row':i,'ts_ms':int(stamp),'kind':'missing_funding_coverage','assets':np.flatnonzero(held&~cover[i]).tolist()})
  fund=0.;event_missing=False
  while event_ix<len(events) and events[event_ix][0]<=stamp:
   event=events[event_ix];et,s,rate,mark,mk,kind,iv=event;event_ix+=1
   funding_prefix_sha256=_funding_prefix_step(funding_prefix_sha256,event);funding_prefix_count+=1
   # With a zero initial inventory, earlier events are economically inactive.
   if prev[s]==0:continue
   if iv is None:state['unverified_interval_events']+=1
   if not math.isfinite(rate) or not math.isfinite(mark) or mark<=0 or mk=='MISSING':
    state['unpriced_funding_events']+=1;event_missing=True;issues.append({'row':i,'ts_ms':int(et),'kind':'unpriced_funding','assets':[s]});continue
   with np.errstate(over='ignore',invalid='ignore'):flow=-prev[s]*mark*rate
   _finite(flow,'funding cash');fund+=flow
   if mk=='CLOSE_PROXY':state['proxy_mark_events']+=1
  _finite(fund,'funding aggregate')
  with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
   usd=w[i]*initial_capital;desired=prev.copy();np.divide(usd,p[i],out=desired,where=valid)
  _finite(usd,'target notional');_finite(desired,'target quantity')
  # Missing price cannot erase inventory or create a trade; its target stays pending.
  blocked_price=(~valid)&((prev!=0)|(usd!=0))&trading[i];blocked_price_total+=int(blocked_price.sum())
  unrestricted=desired.copy();same=np.sign(desired)==np.sign(prev);reduce=np.where(same,np.sign(prev)*np.minimum(np.abs(prev),np.abs(desired)),0.)
  desired=np.where(allow[i],desired,reduce);desired=np.where(valid,desired,prev)
  if not trading[i]:desired=prev.copy();unrestricted=prev.copy()
  risk_desired=desired.copy();blocked_execution=(desired!=prev)&~execution_activity[i];blocked_execution_total+=int(blocked_execution.sum())
  if blocked_execution.any():issues.append({'row':i,'ts_ms':int(stamp),'kind':'unobservable_execution','assets':np.flatnonzero(blocked_execution).tolist()})
  desired=np.where(blocked_execution,prev,desired)
  with np.errstate(over='ignore',invalid='ignore'):
   blocked=np.where(valid,np.abs(unrestricted-risk_desired)*p[i],0.).sum();dq=desired-prev;notional=np.zeros(n);np.multiply(dq,p[i],out=notional,where=dq!=0)
  _finite(blocked,'blocked notional');_finite(notional,'trade notional');turn=float(np.abs(notional).sum());fee=turn*fee_bps/1e4;trade_cash=-float(notional.sum())
  _finite(np.array([turn,fee,trade_cash]),'cash flows')
  cash+=trade_cash+fund-fee;_finite(cash,'cash balance');q=desired
  with np.errstate(over='ignore',invalid='ignore'):
   marks=np.zeros(n);np.multiply(q,p[i],out=marks,where=q!=0)
  value_known=bool(np.isfinite(marks).all());eq=float(cash+marks.sum()) if value_known else None
  if eq is not None:_finite(eq,'equity')
  price_known=bool((~held|(valid&np.isfinite(last)&(last>0))).all())
  if price_known:
   with np.errstate(over='ignore',invalid='ignore'):pl=float(np.where(held,prev*(p[i]-last),0.).sum())
   _finite(pl,'price pnl')
  else:pl=np.nan
  if last_ts is None:pl=0.
  if eq is not None and prior_equity is not None and np.isfinite(pl) and not event_missing:
   err=abs(eq-prior_equity-pl-fund+fee);max_error=max(max_error,err)
   if err>1e-9*max(initial_capital,abs(eq),abs(prior_equity),1):raise ValueError('cash/share identity mismatch')
  with np.errstate(over='ignore',invalid='ignore'):gross=float(np.abs(marks).sum()) if value_known else np.nan;un=float(np.where(unknown[i]&valid,np.abs(marks),0.).sum())
  _finite(un,'unknown PIT notional')
  blocked_total+=blocked;unknown_total+=un;total_fees+=fee;total_funding+=fund;total_trade_cash+=trade_cash;rows_done+=1
  complete=not any(state[k] for k in ('unpriced_holding_cells','missing_funding_coverage_cells','unpriced_funding_events')) and value_known and blocked_price_total==0 and blocked_execution_total==0
  Q.append(q.copy());cash_rows.append(cash);equity.append(np.nan if eq is None else eq);fee_rows.append(fee);fund_rows.append(np.nan if event_missing else fund);price_rows.append(pl);turnover_rows.append(turn);trade_cash_rows.append(trade_cash);gross_rows.append(gross);complete_rows.append(complete)
  last=p[i].copy();last_ts=int(stamp);prior_equity=eq
 state.update(contract=CONTRACT,funding_prefix_count=funding_prefix_count,funding_prefix_sha256=funding_prefix_sha256,initial_capital=float(initial_capital),fee_bps=float(fee_bps),q=q.tolist(),last_prices=[float(x) if math.isfinite(x) else None for x in last],cash_proxy=float(cash),last_ts_ms=last_ts,last_equity_proxy=prior_equity,total_fees=float(total_fees),total_funding_proxy=float(total_funding),total_trade_cash=float(total_trade_cash),blocked_new_risk_notional=float(blocked_total),blocked_price_trade_cells=int(blocked_price_total),blocked_execution_trade_cells=int(blocked_execution_total),unknown_pit_notional_time=float(unknown_total),rows_done=int(rows_done))
 endpoint_complete=prior_equity is not None and not state['missing_funding_coverage_cells'] and not state['unpriced_funding_events']
 path_complete=not state['unpriced_holding_cells']
 execution_complete=blocked_price_total==0 and blocked_execution_total==0
 endpoint_net=prior_equity-initial_capital if endpoint_complete else None
 net=endpoint_net if execution_complete else None
 return {'contract':CONTRACT,'q_after':np.asarray(Q),'cash_proxy':np.asarray(cash_rows),'equity_proxy':np.asarray(equity),'price_pnl':np.asarray(price_rows),'funding_proxy':np.asarray(fund_rows),'fee':np.asarray(fee_rows),'turnover_notional':np.asarray(turnover_rows),'trade_cash':np.asarray(trade_cash_rows),'gross_notional':np.asarray(gross_rows),'accounting_complete':np.asarray(complete_rows),'research_proxy_net':net,'realized_simulation_endpoint_net':endpoint_net,'endpoint_cash_complete':bool(endpoint_complete),'valuation_path_complete':bool(path_complete),'execution_counterfactual_complete':bool(execution_complete),'certified_cash_net':None,'max_cash_identity_error':float(max_error),'blocked_new_risk_notional':float(blocked_total),'blocked_price_trade_cells':int(blocked_price_total),'blocked_execution_trade_cells':int(blocked_execution_total),'execution_activity_input_provided':execution_observed_activity is not None,'issues':issues,'state':state,'scope':'fixed-notional research execution/fee scenario; close-proxy funding remains explicit; no exchange-PIT/fill certification'}

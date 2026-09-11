#!/usr/bin/env python3
"""WHY is the modelled carry too pessimistic?  Test the persistence assumption directly.
The producer forecasts the next window's rate with the LAST OBSERVED rate (shadow_loop_v3 L411,528).
On 4h-interval names a 4h anchor window contains exactly one settlement, so the forecast error is
purely rate persistence.  Predicted_paid = -notional_at_settlement * rate_prev ; Actual = funding_paid.
READ-ONLY."""
import json, glob, collections, datetime, statistics as stt
LOG='/Users/haosiyu/dl_quant_live/state/live/pilot_log'; H4=14400
COMBO0=1787716800
F=[]
for f in sorted(glob.glob(LOG+'/*/funding.jsonl')):
    for l in open(f):
        if l.strip(): F.append(json.loads(l))
F.sort(key=lambda r:(r['symbol'], r['settlement_ts']))
prev={}
out=[]
for r in F:
    s=r['symbol']; p=prev.get(s)
    iv=r.get('funding_interval_h') or 8.0
    if p is not None and 0 < r['settlement_ts']-p['settlement_ts'] <= 2*iv*3600 and (p.get('funding_interval_h') or 8.0)==iv:
        r['_rprev']=p['funding_rate']
    prev[s]=r
    out.append(r)
def rep(tag, sel, ivsel):
    rs=[r for r in out if '_rprev' in r and sel(r['settlement_ts']) and ivsel(r.get('funding_interval_h'))]
    if not rs: print(tag,'empty'); return
    act=sum(r['funding_paid'] for r in rs)
    pred=sum(-r['position_notional_at_settlement']*r['_rprev'] for r in rs)
    # decompose: same-sign persistence on the deep-negative tail vs the bulk
    def sub(f):
        a=sum(r['funding_paid'] for r in f); p=sum(-r['position_notional_at_settlement']*r['_rprev'] for r in f)
        return len(f),p,a
    deep=[r for r in rs if r['_rprev']*(8.0/(r.get('funding_interval_h') or 8.0))<=-0.0010]
    hi  =[r for r in rs if r['_rprev']*(8.0/(r.get('funding_interval_h') or 8.0))>= 0.0010]
    mid =[r for r in rs if -0.0010<r['_rprev']*(8.0/(r.get('funding_interval_h') or 8.0))<0.0010]
    print('%-34s n=%6d  predicted_paid %9.1f  actual_paid %9.1f  actual/predicted %5.2f'%(tag,len(rs),pred,act,act/pred if pred else float('nan')))
    for nm,f in (('  prev rn8<=-10bp (deep neg)',deep),('  prev |rn8|<10bp (bulk)',mid),('  prev rn8>=+10bp (deep pos)',hi)):
        n,p,a=sub(f)
        print('   %-32s n=%6d  pred %9.1f  act %9.1f  ratio %5.2f'%(nm,n,p,a,a/p if p else float('nan')))
    # rate-level persistence (unweighted): mean |rate| this vs prev, on deep names
    if deep:
        pr=[abs(r['_rprev']*(8.0/(r.get('funding_interval_h') or 8.0))) for r in deep]
        cu=[abs(r['funding_rate']*(8.0/(r.get('funding_interval_h') or 8.0))) for r in deep]
        print('   deep-neg names: mean |rn8| prev %.5f -> now %.5f  (shrink %.2f);  median prev %.5f -> now %.5f'
              %(stt.mean(pr),stt.mean(cu),stt.mean(cu)/stt.mean(pr),stt.median(pr),stt.median(cu)))
print('=== persistence test: last-observed-rate forecast vs what the venue actually charged ===')
for tag,sel in (('ALL',lambda t:True),('combo era',lambda t:t>COMBO0)):
    print('--',tag)
    rep('  4h-interval names only', sel, lambda h: h==4)
    rep('  8h-interval names only', sel, lambda h: h==8)
    rep('  1h-interval names only', sel, lambda h: h==1)

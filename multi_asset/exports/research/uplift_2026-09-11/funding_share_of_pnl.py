#!/usr/bin/env python3
"""Funding as a share of the live P&L, flow-adjusted, per day.  READ-ONLY.
day return r_d = (nav_end - nav_prev - external_flow) / nav_prev  (last daily_nav row of the day)
funding drag f_d = FUNDING_FEE_of_day / nav_prev   (venue income ledger, same row)"""
import json, glob, os, datetime, statistics as stt
LOG='/Users/haosiyu/dl_quant_live/state/live/pilot_log'
days=sorted(os.listdir(LOG))
out=[]
for d in days:
    p=LOG+'/'+d+'/daily_nav.jsonl'
    if not os.path.exists(p): continue
    rs=[json.loads(l) for l in open(p) if l.strip()]
    if not rs: continue
    r=rs[-1]
    prev=r.get('prev_nav'); nav=r.get('nav'); fl=r.get('external_flow_usdt') or 0.0
    if not prev: continue
    fee=r['realised_by_type'].get('FUNDING_FEE',0.0)
    com=r['realised_by_type'].get('COMMISSION',0.0)
    rp =r['realised_by_type'].get('REALIZED_PNL',0.0)
    out.append(dict(day=d,prev=prev,nav=nav,flow=fl,ret=(nav-prev-fl)/prev,fund=fee/prev,
                    fee_usdt=fee,com=com,rp=rp,tg=r.get('target_gross'),pol=r.get('sizing_policy'),
                    unreal=r.get('unrealised_pnl')))
def block(tag,sel):
    rs=[o for o in out if sel(o['day'])]
    if not rs: return
    cr=1.0; cf=1.0
    for o in rs: cr*=1+o['ret']; cf*=1+o['fund']
    print('%-24s days=%2d  cum_ret %+7.3f%%  cum_funding_drag %+7.3f%%  funding share of loss %s  mean ret %+.4f%%/d  mean fund %+.4f%%/d'
          %(tag,len(rs),(cr-1)*100,(cf-1)*100,('%.0f%%'%(100*(cf-1)/(cr-1)) if cr<1 else 'n/a (period positive)'),
            100*stt.mean([o['ret'] for o in rs]),100*stt.mean([o['fund'] for o in rs])))
print('day        prev_nav     nav    flow    ret%%    fund%%   fund_USDT  target_gross  policy')
for o in out:
    print('%s %9.0f %9.0f %8.0f %+7.3f %+7.3f %10.2f %12.0f  %s'%(o['day'],o['prev'],o['nav'],o['flow'],100*o['ret'],100*o['fund'],o['fee_usdt'],o['tg'] or 0,o['pol']))
print()
block('whole period',lambda d:True)
block('combo era 08-26+',lambda d:d>='20260826')
block('post-deposit 09-03+',lambda d:d>='20260903')
block('post-FTRIM 09-03+',lambda d:d>='20260903')
block('pre-combo 08-01..08-25',lambda d:d<'20260826')

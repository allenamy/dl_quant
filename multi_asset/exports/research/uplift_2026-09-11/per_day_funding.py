#!/usr/bin/env python3
"""Per-day funding table: total, long/short split, interval split, FTRIM-band share.  READ-ONLY."""
import json, glob, os, collections, datetime, csv
LOG='/Users/haosiyu/dl_quant_live/state/live/pilot_log'; H4=14400
OUT='/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11'
def bucket(ts): return int((ts-1)//H4)*H4
G={}
for f in sorted(glob.glob(LOG+'/*/anchors.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); b=int(r['anchor_ts']//H4)*H4; g=r.get('realized_gross') or 0.0
        if b not in G or g>G[b]: G[b]=g
D=collections.defaultdict(lambda: collections.defaultdict(float))
ANCH=collections.defaultdict(set)
for f in sorted(glob.glob(LOG+'/*/funding.jsonl')):
    day=os.path.basename(os.path.dirname(f))
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); iv=r.get('funding_interval_h') or 8.0
        rn8=r['funding_rate']*(8.0/iv); n=r['position_notional_at_settlement']; p=r['funding_paid']
        d=D[day]; d['paid']+=p; d['rows']+=1
        (d.__setitem__('paid_L',d['paid_L']+p) if n>0 else d.__setitem__('paid_S',d['paid_S']+p))
        d['iv%d'%(iv if iv in (1,4,8) else 0)]+=p
        if rn8<=-0.0010 and n<0: d['band_short']+=p; d['band_notl']+=-n
        d['notl']+=abs(n)
        ANCH[day].add(bucket(r['settlement_ts']))
rows=[]
for day in sorted(D):
    d=D[day]; gs=sum(G.get(b,0) or 0 for b in ANCH[day]); na=len(ANCH[day])
    rows.append(dict(day=day,anchors=na,gross_sum=round(gs,0),funding_usdt=round(d['paid'],2),
        long_usdt=round(d['paid_L'],2),short_usdt=round(d['paid_S'],2),
        iv1=round(d['iv1'],2),iv4=round(d['iv4'],2),iv8=round(d['iv8'],2),
        band_short_usdt=round(d['band_short'],2),band_short_notl_share=round(d['band_notl']/d['notl'],4) if d['notl'] else 0,
        cost_bps_of_gross_per_anchor=round(-d['paid']/gs*1e4,4) if gs else None,
        short_cost_bps=round(-d['paid_S']/gs*1e4,4) if gs else None,
        long_cost_bps=round(-d['paid_L']/gs*1e4,4) if gs else None))
with open(OUT+'/per_day_funding.csv','w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('day       anch  gross_sum  funding  long   short   iv1    iv4    iv8   band_short  band_notl%  cost_bps/anchor (short/long)')
for r in rows:
    print('%s %4d %10.0f %8.1f %7.1f %7.1f %6.1f %7.1f %6.1f %10.1f %9.2f%%  %7s (%s/%s)'%(
        r['day'],r['anchors'],r['gross_sum'],r['funding_usdt'],r['long_usdt'],r['short_usdt'],
        r['iv1'],r['iv4'],r['iv8'],r['band_short_usdt'],100*r['band_short_notl_share'],
        r['cost_bps_of_gross_per_anchor'],r['short_cost_bps'],r['long_cost_bps']))
print('\nwrote',OUT+'/per_day_funding.csv')

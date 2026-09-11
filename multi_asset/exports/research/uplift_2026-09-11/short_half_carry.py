#!/usr/bin/env python3
"""Cross-check DIAG_live_giveback_root_cause_2026-09-09 §1 'S|pos_lo = 66% of the loss'
against the CARRY ledger: is that bucket a carry bucket at all?  READ-ONLY."""
import json, glob, collections, datetime
LOG='/Users/haosiyu/dl_quant_live/state/live/pilot_log'; H4=14400
A0=1787716800; A1=int(datetime.datetime(2026,9,9,4,0,tzinfo=datetime.timezone.utc).timestamp())  # DIAG window
def bucket(ts): return int((ts-1)//H4)*H4
F=[]
for f in sorted(glob.glob(LOG+'/*/funding.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); iv=r.get('funding_interval_h') or 8.0
        r['_rn8']=r['funding_rate']*(8.0/iv); r['_b']=bucket(r['settlement_ts']); F.append(r)
G={}
for f in sorted(glob.glob(LOG+'/*/anchors.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); b=int(r['anchor_ts']//H4)*H4; g=r.get('realized_gross') or 0.0
        if b not in G or g>G[b]: G[b]=g
def buck(r):
    s = 'S' if r['position_notional_at_settlement']<0 else 'L'
    x = r['_rn8']
    if x<=-0.0010: k='deepneg'
    elif x<0:      k='neg'
    elif x<0.0005: k='pos_lo'
    else:          k='pos_hi'
    return s+'|'+k
for tag,lo,hi in (('DIAG window 08-26 04Z..09-09 04Z',A0,A1),('combo era 08-26 04Z..09-11',A0,10**11)):
    rs=[r for r in F if lo<=r['_b']<=hi]
    bs=sorted({r['_b'] for r in rs}); gs=sum(G.get(b,0) or 0 for b in bs)
    tot=sum(r['funding_paid'] for r in rs)
    print('\n%s  anchors %d  funding total %.1f USDT  (%.3f bps of gross/anchor)'%(tag,len(bs),tot,-tot/gs*1e4))
    agg=collections.defaultdict(lambda:[0.0,0.0,0])
    for r in rs:
        a=agg[buck(r)]; a[0]+=r['funding_paid']; a[1]+=abs(r['position_notional_at_settlement']); a[2]+=1
    print('   bucket        funding_USDT   settled_notional  share_of_notional  bps_of_gross/anchor')
    for k in sorted(agg, key=lambda k: agg[k][0]):
        p,n,c=agg[k]
        print('   %-12s %+12.1f %16.0f %16.2f%% %+16.4f'%(k,p,n,100*n/sum(v[1] for v in agg.values()),-p/gs*1e4))

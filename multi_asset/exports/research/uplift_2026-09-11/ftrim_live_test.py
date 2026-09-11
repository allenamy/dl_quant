#!/usr/bin/env python3
"""Does FTRIM actually cut the carry drag on live data?  READ-ONLY.
Control for regime by comparing OUR notional share in the rn8<=-10bp band against the
unweighted NAME-COUNT share of band names among the same settlements (market availability)."""
import json, glob, collections, datetime, statistics as stt
LOG='/Users/haosiyu/dl_quant_live/state/live/pilot_log'; H4=14400
FT0=1788350400   # 2026-09-02 12:00Z first FTRIM anchor (PREREG_deploy_ftrim §9)
COMBO0=1787716800
def bucket(ts): return int((ts-1)//H4)*H4
F=[]
for f in sorted(glob.glob(LOG+'/*/funding.jsonl')):
    for l in open(f):
        if l.strip():
            r=json.loads(l); iv=r.get('funding_interval_h') or 8.0
            r['_rn8']=r['funding_rate']*(8.0/iv); r['_b']=bucket(r['settlement_ts'])
            F.append(r)
A={}
for f in sorted(glob.glob(LOG+'/*/anchors.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); b=int(r['anchor_ts']//H4)*H4; g=r.get('realized_gross') or 0.0
        if b not in A or g>A[b]: A[b]=g
ks=sorted(k for k in A if A[k])
def gross_at(b):
    if A.get(b): return A[b]
    p=[k for k in ks if k<=b]; return A[p[-1]] if p else None
TH=-0.0010
def block(tag, sel):
    rs=[r for r in F if sel(r['_b'])]
    if not rs: return
    bs=sorted({r['_b'] for r in rs}); g=sum(gross_at(b) or 0 for b in bs)
    band=[r for r in rs if r['_rn8']<=TH]
    bshort=[r for r in band if r['position_notional_at_settlement']<0]
    N=len(rs); NT=sum(abs(r['position_notional_at_settlement']) for r in rs)
    print('%-26s anchors %3d  settlements %6d  settled-notional %10.0f' % (tag,len(bs),N,NT))
    print('   band rn8<=-10bp/8h : name-count share %5.2f%%   OUR notional share %5.2f%%   tilt(notional/count) %5.2f'
          % (100*len(band)/N, 100*sum(abs(r['position_notional_at_settlement']) for r in band)/NT,
             (sum(abs(r['position_notional_at_settlement']) for r in band)/NT)/(len(band)/N)))
    print('   band SHORT side    : name-count share %5.2f%%   OUR notional share %5.2f%%   tilt %5.2f   paid %8.1f USDT  %+7.4f bps_of_gross/anchor'
          % (100*len(bshort)/N, 100*sum(abs(r['position_notional_at_settlement']) for r in bshort)/NT,
             (sum(abs(r['position_notional_at_settlement']) for r in bshort)/NT)/max(len(bshort)/N,1e-12),
             sum(r['funding_paid'] for r in bshort), sum(r['funding_paid'] for r in bshort)/g*1e4))
    # what fraction of band settlements are we SHORT vs LONG (directional tilt inside the band)
    bl=[r for r in band if r['position_notional_at_settlement']>0]
    print('   inside band        : short notional %9.0f  long notional %9.0f  short/(short+long) %5.1f%%'
          % (sum(-r['position_notional_at_settlement'] for r in bshort),
             sum(r['position_notional_at_settlement'] for r in bl),
             100*sum(-r['position_notional_at_settlement'] for r in bshort)/max(1e-9,sum(abs(r['position_notional_at_settlement']) for r in band))))
print('=== FTRIM band exposure, regime-controlled ===')
block('combo pre-FTRIM', lambda b: COMBO0<=b<FT0)
block('post-FTRIM', lambda b: b>=FT0)
block('post-FTRIM first half', lambda b: FT0<=b<FT0+22*H4)
block('post-FTRIM second half', lambda b: b>=FT0+22*H4)

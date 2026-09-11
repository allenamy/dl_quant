#!/usr/bin/env python3
"""Funding paid by rate decile and by side, plus per-name concentration.  READ-ONLY."""
import json, glob, collections, datetime, statistics as st
LOG='/Users/haosiyu/dl_quant_live/state/live/pilot_log'; H4=14400
COMBO0=1787716800
def bucket(ts): return int((ts-1)//H4)*H4
F=[]
for f in sorted(glob.glob(LOG+'/*/funding.jsonl')):
    for l in open(f):
        if l.strip(): F.append(json.loads(l))
A={}
for f in sorted(glob.glob(LOG+'/*/anchors.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); b=int(r['anchor_ts']//H4)*H4; g=r.get('realized_gross') or 0.0
        if b not in A or g>A[b]: A[b]=g
ks=sorted(k for k in A if A[k])
def gross_at(b):
    if A.get(b): return A[b]
    p=[k for k in ks if k<=b]
    return A[p[-1]] if p else None

def run(tag, sel):
    rows=[r for r in F if sel(bucket(r['settlement_ts']))]
    if not rows: return
    bs=sorted({bucket(r['settlement_ts']) for r in rows})
    gsum=sum(gross_at(b) or 0 for b in bs); nA=len(bs)
    tot=sum(r['funding_paid'] for r in rows)
    print('\n### %s   anchors=%d  funding_total=%.1f USDT  mean bps_of_gross/anchor=%+.3f'%(tag,nA,tot,tot/gsum*1e4))
    # rate normalised to an 8h-equivalent (the FTRIM rn8 caliber)
    for r in rows:
        iv=r.get('funding_interval_h') or 8.0
        r['_rn8']=r['funding_rate']*(8.0/iv)
    for side,pick in (('LONG',lambda r:r['position_notional_at_settlement']>0),
                      ('SHORT',lambda r:r['position_notional_at_settlement']<=0)):
        sub=[r for r in rows if pick(r)]
        sub.sort(key=lambda r:r['_rn8'])
        # notional-weighted deciles
        W=[abs(r['position_notional_at_settlement']) for r in sub]; TW=sum(W)
        print('  %s  settled-notional %.0f  paid %.1f USDT  bps_of_gross/anchor %+.4f'
              %(side,TW,sum(r['funding_paid'] for r in sub),sum(r['funding_paid'] for r in sub)/gsum*1e4))
        print('     dec   rn8_range(bp/8h)      notional      paid_USDT   bps_of_gross/anchor  share_of_side_paid')
        c=0.0; d=0; start=0; sp=sum(r['funding_paid'] for r in sub)
        edges=[TW*(i+1)/10 for i in range(10)]
        acc=0.0; di=0; chunk=[]
        for r in sub:
            chunk.append(r); acc+=abs(r['position_notional_at_settlement'])
            if acc>=edges[di] or r is sub[-1]:
                p=sum(x['funding_paid'] for x in chunk); nn=sum(abs(x['position_notional_at_settlement']) for x in chunk)
                print('     %2d   %8.2f..%8.2f  %12.0f  %+12.1f     %+8.4f        %6.1f%%'
                      %(di+1,chunk[0]['_rn8']*1e4,chunk[-1]['_rn8']*1e4,nn,p,p/gsum*1e4,100*p/sp if sp else 0))
                chunk=[]; di=min(di+1,9)
    # per-name concentration
    byn=collections.Counter()
    for r in rows: byn[r['symbol']]+=r['funding_paid']
    worst=sorted(byn.items(), key=lambda kv: kv[1])[:15]
    print('  worst 15 names by funding paid: '+', '.join('%s %.1f'%(s,v) for s,v in worst))
    print('  top-15 share of total funding paid: %.1f%%'%(100*sum(v for _,v in worst)/tot))
    # how much of the drag is short-in-negative-rate
    sneg=sum(r['funding_paid'] for r in rows if r['position_notional_at_settlement']<=0 and r['_rn8']<0)
    lpos=sum(r['funding_paid'] for r in rows if r['position_notional_at_settlement']>0 and r['_rn8']>0)
    print('  short-in-negative-rate paid %.1f USDT (%.0f%% of total)   long-in-positive-rate paid %.1f USDT (%.0f%%)'
          %(sneg,100*sneg/tot,lpos,100*lpos/tot))
    s10=sum(r['funding_paid'] for r in rows if r['position_notional_at_settlement']<=0 and r['_rn8']<=-0.0010)
    n10=sum(abs(r['position_notional_at_settlement']) for r in rows if r['position_notional_at_settlement']<=0 and r['_rn8']<=-0.0010)
    print('  FTRIM-band settlements (short & rn8<=-10bp/8h): paid %.1f USDT (%.0f%% of total), notional %.0f (%.2f%% of settled), bps_of_gross/anchor %+.4f'
          %(s10,100*s10/tot,n10,100*n10/sum(abs(r['position_notional_at_settlement']) for r in rows),s10/gsum*1e4))

run('ALL 08-01..09-11', lambda b: True)
run('COMBO ERA 08-26 04Z+', lambda b: b>=COMBO0)
FT0=int(datetime.datetime(2026,9,2,12,0,tzinfo=datetime.timezone.utc).timestamp())
run('POST-FTRIM (>=09-02 12Z)', lambda b: b>=FT0)
run('COMBO PRE-FTRIM (08-26 04Z..09-02 12Z)', lambda b: COMBO0<=b<FT0)

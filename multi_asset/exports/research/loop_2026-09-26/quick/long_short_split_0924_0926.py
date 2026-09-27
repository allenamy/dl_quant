#!/usr/bin/env python3
"""ESTIMATE (lead, 2026-09-27 00:3xZ, user question "no rally but losses keep growing"): price-only P&L of the HELD book split
long / short per readback interval, 09-24 00Z .. 09-26 20Z. Positions = executor post-anchor readbacks (venue notional, pooled,
blind-safe); returns = producer rolling cache channel 0 (5m ret, float16, compounded; clipped bars not restored). Funding and
fees EXCLUDED. Not certified — the certified device is integ's layered_book; this is a first read to direct work."""
import numpy as np, json, glob, time, collections
cfg=json.load(open('/Users/haosiyu/wide_shadow/shadow_bundle/config.json')); syms=[str(s) for s in cfg['symbols_panel']]
z=np.load('/Users/haosiyu/wide_shadow/state/rolling.npz'); ts=z['ts']; r5=z['data'][:,:,0].astype(np.float64)
col={s:j for j,s in enumerate(syms)}; snaps=collections.defaultdict(dict)
for f in sorted(glob.glob('/Users/haosiyu/dl_quant_live/state/live/pilot_log/2026092[3-7]/position_readback.jsonl')):
    for l in open(f):
        r=json.loads(l)
        if r.get('source','').endswith('post_anchor'): snaps[round(r['read_ts'])][r['symbol']]=float(r['venue_position_notional'] or 0)
keys=sorted(k for k in snaps if k>=1790208000-3600); tot=collections.defaultdict(lambda:[0.0,0.0])
for a,b in zip(keys[:-1],keys[1:]):
    m=(ts>a)&(ts<=b)
    if m.sum()<10: continue
    R=np.nanprod(1+np.nan_to_num(r5[m]),axis=0)-1; L=S=0.0
    for s,n in snaps[a].items():
        j=col.get(s)
        if j is None: continue
        if n>0: L+=n*R[j]
        elif n<0: S+=n*R[j]
    ew=np.nanmean(R[[col[s] for s in snaps[a] if s in col]])
    d=time.strftime('%m-%d',time.gmtime(a)); tot[d][0]+=L; tot[d][1]+=S
    print(time.strftime('%m-%d %H:%MZ',time.gmtime(a)),'->',time.strftime('%m-%d %H:%MZ',time.gmtime(b)),'long %+7.0f short %+7.0f net %+7.0f BTC %+.2f%% EW(held names) %+.2f%%'%(L,S,L+S,100*R[col['BTCUSDT']],100*ew))
for d,(L,S) in tot.items(): print('DAY',d,'long %+.0f short %+.0f net %+.0f'%(L,S,L+S))

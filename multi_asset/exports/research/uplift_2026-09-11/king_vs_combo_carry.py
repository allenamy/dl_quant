#!/usr/bin/env python3
"""★ The producer's logged carry_bps/gross_bps/net_bps describe the KING book (shadow_loop_v3:
z = w3[0]*king + w3[1]*rev24 + w3[2]*fund, NO FTRIM, gross_pos), not the deployed COMBO book
(combo_stage.py: rev24 masked + FTRIM + phi 0.45).  This script measures the carry exposure of
both target vectors on the SAME rate table, plus the actually-held book.  READ-ONLY.

carry exposure, bps of gross per anchor = 1e4 * sum_j( wnorm_j * rate_last_j * 4/iv_j ),  sum|wnorm| = 1
(the producer's own formula, shadow_loop_v3.py L527-528, renormalised to unit gross)."""
import json, glob, bisect, collections, datetime, statistics as stt
LOG='/Users/haosiyu/dl_quant_live/state/live/pilot_log'; WS='/Users/haosiyu/wide_shadow/state'
H4=14400; FT0=1788350400; COMBO0=1787716800
# rate table from the venue funding ledger (only names we have held, which is what matters for carry)
RT=collections.defaultdict(list)
for f in sorted(glob.glob(LOG+'/*/funding.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); RT[r['symbol']].append((r['settlement_ts'], r['funding_rate'], r.get('funding_interval_h') or 8.0))
for s in RT: RT[s].sort()
def rate_at(s,t):
    a=RT.get(s)
    if not a: return None
    i=bisect.bisect_right(a,(t,1e9,1e9))-1
    if i<0: return None
    ft,rt,iv=a[i]
    if t-ft > 12*3600: return None
    return rt*(4.0/(iv if iv>0 else 8.0))
def carry_bps(w,t):
    g=sum(abs(v) for v in w.values())
    num=0.0; covw=0.0
    for s,v in w.items():
        r=rate_at(s,t)
        if r is None: continue
        covw+=abs(v); num+=v*r
    return 1e4*num/g, covw/g
# held book from position_readback (post_anchor read)
HB=collections.defaultdict(dict)
for f in sorted(glob.glob(LOG+'/*/position_readback.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); b=int(r['anchor_ts']//H4)*H4
        n=r.get('venue_position_notional') or 0.0
        if n: HB[b][r['symbol']]=HB[b].get(r['symbol'],0.0)+n
# producer log
SIG={}
for l in open('/Users/haosiyu/wide_shadow/shadow_log.jsonl'):
    if not l.strip(): continue
    r=json.loads(l)
    if r.get('e')=='signal': SIG[int(r['anchor_ts'])]=r
# realized funding per anchor + gross
PAID=collections.defaultdict(float)
for f in sorted(glob.glob(LOG+'/*/funding.jsonl')):
    for l in open(f):
        if l.strip():
            r=json.loads(l); PAID[int((r['settlement_ts']-1)//H4)*H4]+=r['funding_paid']
G={}
for f in sorted(glob.glob(LOG+'/*/anchors.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); b=int(r['anchor_ts']//H4)*H4; g=r.get('realized_gross') or 0.0
        if b not in G or g>G[b]: G[b]=g
rows=[]
for p in sorted(glob.glob(WS+'/target_combo/*.json')):
    A=int(p.split('/')[-1][:-5])
    kp=WS+'/target_live_king/%d.json'%A
    if not __import__('os').path.exists(kp): continue
    cw=json.load(open(p))['weights']; kw=json.load(open(kp))['weights']
    ck,ccov=carry_bps(cw,A); kk,kcov=carry_bps(kw,A)
    hb=HB.get(A,{}); hk,hcov=(carry_bps(hb,A) if hb else (None,0))
    sg=SIG.get(A)
    rows.append(dict(A=A,t=datetime.datetime.utcfromtimestamp(A).strftime('%m-%d %HZ'),
        combo=ck,king=kk,held=hk,ccov=ccov,kcov=kcov,hcov=hcov,
        prod=(sg['carry_bps']/sg['gross_pos']) if sg else None,
        real=(-PAID[A]/G[A]*1e4) if G.get(A) and A in PAID else None))
def rep(tag,sel):
    rs=[r for r in rows if sel(r['A'])]
    ok=[r for r in rs if r['combo'] is not None and r['king'] is not None]
    if not ok: print(tag,'empty'); return
    f=lambda k: stt.mean([r[k] for r in ok if r[k] is not None])
    nn=lambda k: sum(1 for r in ok if r[k] is not None)
    print('%-22s n=%3d | carry cost bps of gross/anchor:  KING target %6.3f (cov %.2f) | COMBO target %6.3f (cov %.2f) | HELD book %6.3f (cov %.2f, n=%d) | producer-logged %6.3f | REALIZED %6.3f (n=%d)'
          %(tag,len(ok),-f('king'),f('kcov'),-f('combo'),f('ccov'),-f('held'),f('hcov'),nn('held'),f('prod'),f('real'),nn('real')))
print('=== carry exposure of the KING (logged) vs COMBO (deployed) vs HELD book, same rate table ===')
rep('combo era all',lambda a:a>=COMBO0)
rep('combo pre-FTRIM',lambda a:COMBO0<=a<FT0)
rep('post-FTRIM',lambda a:a>=FT0)
json.dump(rows,open('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/king_vs_combo_carry.json','w'),indent=1)

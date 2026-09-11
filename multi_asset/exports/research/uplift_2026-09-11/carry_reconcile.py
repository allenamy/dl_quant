#!/usr/bin/env python3
"""Reconcile the producer's modelled carry_bps against realized venue funding, per anchor.
Producer:  carry = sum_j( sm_j * rate_last_j * 4/iv_j ) * 1e4 , sum|sm| = gross_pos  (shadow_loop_v3 L527-528)
           => bps of GROSS = carry / gross_pos
Realized:  sum of venue FUNDING_FEE in (A, A+4h] / realized_gross * 1e4     (sign: paid<0)
Comparable quantity: model_cost_bps_of_gross  vs  realized_cost_bps_of_gross = -paid/gross*1e4
READ-ONLY."""
import json, glob, collections, datetime, statistics as stt, math
LOG='/Users/haosiyu/dl_quant_live/state/live/pilot_log'; H4=14400
COMBO0=1787716800; FT0=1788350400
def bucket(ts): return int((ts-1)//H4)*H4
PAID=collections.defaultdict(float)
for f in sorted(glob.glob(LOG+'/*/funding.jsonl')):
    for l in open(f):
        if l.strip():
            r=json.loads(l); PAID[bucket(r['settlement_ts'])]+=r['funding_paid']
G={}
for f in sorted(glob.glob(LOG+'/*/anchors.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); b=int(r['anchor_ts']//H4)*H4; g=r.get('realized_gross') or 0.0
        if b not in G or g>G[b]: G[b]=g
SIG={}
for l in open('/Users/haosiyu/wide_shadow/shadow_log.jsonl'):
    if not l.strip(): continue
    r=json.loads(l)
    if r.get('e')=='signal': SIG[int(r['anchor_ts'])]=r
rows=[]
for b in sorted(set(PAID)&set(SIG)):
    g=G.get(b)
    if not g: continue
    s=SIG[b]
    model=s['carry_bps']/s['gross_pos']          # cost, bps of gross (positive = cost)
    real=-PAID[b]/g*1e4                          # cost, bps of gross (positive = cost)
    rows.append((b,model,real,s['carry_bps'],s['gross_pos'],g,PAID[b]))
def rep(tag,sel):
    rs=[r for r in rows if sel(r[0])]
    if len(rs)<3: print(tag,'n<3'); return
    M=[r[1] for r in rs]; R=[r[2] for r in rs]
    mm=stt.mean(M); mr=stt.mean(R)
    n=len(rs)
    d=[a-b for a,b in zip(M,R)]
    sd=stt.pstdev(d); se=sd/math.sqrt(n)
    mu_m=stt.mean(M); mu_r=stt.mean(R)
    cov=sum((a-mu_m)*(b-mu_r) for a,b in zip(M,R))/n
    c=cov/(stt.pstdev(M)*stt.pstdev(R)+1e-12)
    beta=cov/(stt.pstdev(M)**2+1e-12)
    print('%-26s n=%3d  model %6.3f  realized %6.3f  model-real %+6.3f (se %.3f, t %+5.2f)  ratio %5.2f  corr %5.2f  beta(real~model) %5.2f'
          %(tag,n,mm,mr,mm-mr,se,(mm-mr)/se if se else 0,mm/mr if mr else float('nan'),c,beta))
print('=== producer modelled carry vs realized venue funding (both = COST in bps of gross per anchor) ===')
rep('ALL',lambda b:True)
rep('pre-combo',lambda b:b<COMBO0)
rep('combo era',lambda b:b>=COMBO0)
rep('combo pre-FTRIM',lambda b:COMBO0<=b<FT0)
rep('post-FTRIM',lambda b:b>=FT0)
json.dump([{'anchor':r[0],'t':datetime.datetime.utcfromtimestamp(r[0]).strftime('%m-%d %HZ'),
            'model_cost_bps_gross':round(r[1],4),'real_cost_bps_gross':round(r[2],4),
            'carry_bps_raw':r[3],'gross_pos':r[4],'realized_gross':r[5],'funding_paid':round(r[6],3)} for r in rows],
          open('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/carry_reconcile.json','w'),indent=1)

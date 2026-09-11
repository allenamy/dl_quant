#!/usr/bin/env python3
"""LIVE version of RESULT_king_window_ftrim_cap §2.2: does the price of the FTRIM-excluded names
pay back the carry they would have cost?   Sleeve = equal-notional SHORT in the names FTRIM zeroed
at anchor A (list from wide_shadow/state/target_combo/<A>.json ['ftrim']['names_kc']).
Prices = mid_at_anchor_vector from the live anchors ledger (offline; no venue call).
Per unit of sleeve notional, bps over the 4h window (A, A+4h]:
   price_bps  = -mean_j( mid_j(A+4h)/mid_j(A) - 1 ) * 1e4       (short => minus the return)
   carry_bps  = -mean_j( rn8_j * 4/8 ) * 1e4  as a COST          (rn8 from the ftrim record itself)
   total_bps  = price_bps - carry_bps          (>0 => holding the short would have PAID => FTRIM hurts)
READ-ONLY."""
import json, glob, os, statistics as stt, datetime, collections
LOG='/Users/haosiyu/dl_quant_live/state/live/pilot_log'; H4=14400
MID={}
for f in sorted(glob.glob(LOG+'/*/anchors.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r=json.loads(l); b=int(r['anchor_ts']//H4)*H4
        mv=r.get('mid_at_anchor_vector')
        if mv:
            d=json.loads(mv) if isinstance(mv,str) else mv
            if b not in MID or len(d)>len(MID[b]): MID[b]=d
rows=[]; miss=collections.Counter()
for p in sorted(glob.glob('/Users/haosiyu/wide_shadow/state/target_combo/*.json')):
    A=int(os.path.basename(p)[:-5])
    d=json.load(open(p))
    ft=d.get('ftrim')
    if not ft or not ft.get('names_kc'): continue
    m0=MID.get(A); m1=MID.get(A+H4)
    if not m0 or not m1: miss['no_mid']+=1; continue
    pr=[]; ca=[]; nn=0
    for s,rn8 in ft['names_kc'].items():
        if s in m0 and s in m1 and m0[s]>0:
            pr.append(-(m1[s]/m0[s]-1.0)*1e4)      # short return, bps
            ca.append(-rn8*0.5*1e4)                 # cost of the short, bps (rn8<0 => positive cost)
            nn+=1
        else: miss['no_price_'+s]+=1
    if nn==0: continue
    w=json.load(open('/Users/haosiyu/wide_shadow/state/target_live/%d.json'%A))['weights'] if os.path.exists('/Users/haosiyu/wide_shadow/state/target_live/%d.json'%A) else {}
    rows.append(dict(A=A,t=datetime.datetime.utcfromtimestamp(A).strftime('%m-%d %HZ'),n=nn,ntot=len(ft['names_kc']),
                     price=stt.mean(pr),carry=stt.mean(ca),total=stt.mean(pr)-stt.mean(ca),
                     resid_gross=sum(abs(w.get(s,0.0)) for s in ft['names_kc'])))
P=[r['price'] for r in rows]; C=[r['carry'] for r in rows]; T=[r['total'] for r in rows]
import math
def ci(x):
    m=stt.mean(x); s=stt.pstdev(x)/math.sqrt(len(x)); return m, m-1.96*s, m+1.96*s
print('FTRIM sleeve, live, %d anchors (%s .. %s), names/anchor mean %.1f (priced %.1f)'
      %(len(rows),rows[0]['t'],rows[-1]['t'],stt.mean([r['ntot'] for r in rows]),stt.mean([r['n'] for r in rows])))
for nm,x in (('short price return (bps per unit sleeve notional, per anchor)',P),
             ('carry cost of the short (bps per unit, per anchor)',C),
             ('TOTAL of holding the short (price - carry)',T)):
    m,lo,hi=ci(x); print('  %-58s %+8.3f  CI95 [%+7.3f, %+7.3f]  (sd %.2f)'%(nm,m,lo,hi,stt.pstdev(x)))
print('  compensation ratio  price/carry = %.3f'%(stt.mean(P)/stt.mean(C)))
print('  residual FTRIM-name gross still in the deployed book: mean %.4f of gross-norm (%.2f%%), max %.2f%%'
      %(stt.mean([r['resid_gross'] for r in rows]),100*stt.mean([r['resid_gross'] for r in rows])/0.86,
        100*max(r['resid_gross'] for r in rows)/0.86))
print('  coverage misses:', dict(list(miss.items())[:6]), 'total misses', sum(miss.values()))
print()
print('anchor      n  price_bps  carry_bps  total_bps  resid_gross')
for r in rows: print('%s %3d  %+9.2f  %+9.2f  %+9.2f   %8.4f'%(r['t'],r['n'],r['price'],r['carry'],r['total'],r['resid_gross']))
json.dump(rows,open('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/ftrim_sleeve_live.json','w'),indent=1)

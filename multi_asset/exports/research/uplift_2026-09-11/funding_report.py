#!/usr/bin/env python3
"""Per-anchor / per-day funding audit + reconciliation against the producer's carry_bps.
READ-ONLY.  Writes only under exports/research/uplift_2026-09-11/."""
import json, glob, os, collections, datetime, math, statistics as st

LOG = '/Users/haosiyu/dl_quant_live/state/live/pilot_log'
H4 = 14400
OUT = '/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11'

COMBO0 = 1787716800  # 2026-08-26 04:00Z  (combo in service)
DEP0   = int(datetime.datetime(2026, 9, 3, 0, 0, tzinfo=datetime.timezone.utc).timestamp())
L3D0   = int(datetime.datetime(2026, 9, 8, 20, 0, tzinfo=datetime.timezone.utc).timestamp())

def bucket(ts): return int((ts - 1) // H4) * H4
def fmt(b): return datetime.datetime.utcfromtimestamp(b).strftime('%Y-%m-%d %HZ')

# ---- load ----
F = []
for f in sorted(glob.glob(LOG + '/*/funding.jsonl')):
    for l in open(f):
        if l.strip(): F.append(json.loads(l))
A = {}
for f in sorted(glob.glob(LOG + '/*/anchors.jsonl')):
    for l in open(f):
        if not l.strip(): continue
        r = json.loads(l); b = int(r['anchor_ts'] // H4) * H4
        g = r.get('realized_gross') or 0.0
        if b not in A or g > (A[b]['gross'] or 0): A[b] = {'gross': g, 'regime': r.get('regime_at_anchor')}
ks = sorted(k for k in A if A[k]['gross'])
def gross_at(b):
    if b in A and A[b]['gross']: return A[b]['gross'], 'realized'
    p = [k for k in ks if k <= b]
    if p: return A[p[-1]]['gross'], 'carried'
    return None, 'none'

# producer score / signal
SIG = {}; SCORE = {}
for l in open('/Users/haosiyu/wide_shadow/shadow_log.jsonl'):
    if not l.strip(): continue
    r = json.loads(l)
    if r.get('e') == 'signal': SIG[int(r['anchor_ts'])] = r
    elif r.get('e') == 'score': SCORE[int(r['anchor_ts'])] = r

# ---- per anchor aggregation ----
P = collections.defaultdict(lambda: collections.defaultdict(float))
for r in F:
    b = bucket(r['settlement_ts']); n = r['position_notional_at_settlement']; p = r['funding_paid']
    iv = r.get('funding_interval_h'); d = P[b]
    d['paid'] += p; d['rows'] += 1
    if n > 0: d['paid_L'] += p; d['notl_L'] += n
    else:     d['paid_S'] += p; d['notl_S'] += -n
    k = 'iv%s' % (iv if iv in (1, 4, 8) else 'X')
    d['paid_' + k] += p; d['notl_' + k] += abs(n)

def era(b):
    if b < COMBO0: return 'pre'
    return 'combo'

rowsout = []
for b in sorted(P):
    g, src = gross_at(b)
    d = P[b]
    sg = SIG.get(b); sc = SCORE.get(b)
    rowsout.append(dict(anchor=b, t=fmt(b), gross=g, gross_src=src,
                        paid=d['paid'], paid_L=d['paid_L'], paid_S=d['paid_S'],
                        notl_L=d['notl_L'], notl_S=d['notl_S'], rows=int(d['rows']),
                        paid_iv1=d['paid_iv1'], paid_iv4=d['paid_iv4'], paid_iv8=d['paid_iv8'],
                        notl_iv1=d['notl_iv1'], notl_iv4=d['notl_iv4'], notl_iv8=d['notl_iv8'],
                        bps=(d['paid'] / g * 1e4) if g else None,
                        bps_L=(d['paid_L'] / g * 1e4) if g else None,
                        bps_S=(d['paid_S'] / g * 1e4) if g else None,
                        carry_bps_paper=(sg or {}).get('carry_bps'),
                        gross_pos=(sg or {}).get('gross_pos'),
                        net_bps_paper=(sc or {}).get('net_bps'),
                        gross_bps_paper=(sc or {}).get('gross_bps'),
                        cost_bps_paper=(sc or {}).get('cost_bps'),
                        regime=A.get(b, {}).get('regime')))
json.dump(rowsout, open(OUT + '/per_anchor_funding.json', 'w'), indent=1)

def summ(sel, name):
    rs = [r for r in rowsout if sel(r) and r['bps'] is not None]
    if not rs: print(name, 'EMPTY'); return
    n = len(rs)
    m = lambda k: st.mean([r[k] for r in rs if r[k] is not None])
    tot = sum(r['paid'] for r in rs)
    print('%-14s n=%3d  funding_total=%9.1f USDT   bps_of_gross/anchor: all %+7.3f  long %+7.3f  short %+7.3f   (sd %.3f)'
          % (name, n, tot, m('bps'), m('bps_L'), m('bps_S'),
             st.pstdev([r['bps'] for r in rs])))
    # per-interval, as bps of the notional in that interval class (exposure-normalised) and bps of total gross
    for k in ('iv1', 'iv4', 'iv8'):
        pd = sum(r['paid_' + k] for r in rs); nl = sum(r['notl_' + k] for r in rs)
        gl = sum(r['gross'] for r in rs)
        print('    %-4s paid %8.1f USDT  settled-notional %12.0f  bps_of_settled %+7.3f  bps_of_gross/anchor %+7.4f'
              % (k, pd, nl, (pd / nl * 1e4) if nl else 0.0, (pd / gl * 1e4) if gl else 0.0))
    # producer carry
    cb = [r['carry_bps_paper'] for r in rs if r['carry_bps_paper'] is not None]
    gp = [r['gross_pos'] for r in rs if r['gross_pos'] is not None]
    if cb:
        print('    producer carry_bps mean %+7.3f (weight-units, sum|w|=%.3f)  => bps_of_gross %+7.3f   realized %+7.3f   model_minus_real %+7.3f'
              % (st.mean(cb), st.mean(gp), st.mean(cb) / st.mean(gp),
                 m('bps'), st.mean(cb) / st.mean(gp) - (-m('bps'))))
    return rs

print('=== FUNDING PAID AS BPS OF GROSS PER ANCHOR (negative = we paid) ===')
summ(lambda r: True, 'ALL')
summ(lambda r: r['anchor'] < COMBO0, 'pre-combo')
summ(lambda r: r['anchor'] >= COMBO0, 'combo era')
summ(lambda r: r['anchor'] >= DEP0, '09-03+')
summ(lambda r: r['anchor'] >= L3D0, 'last 3d')

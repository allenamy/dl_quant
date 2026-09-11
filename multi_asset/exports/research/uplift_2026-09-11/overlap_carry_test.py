#!/usr/bin/env python3
"""Anchor-paired test: replay (backtest) modelled carry vs LIVE realized venue funding,
on the 29 anchors both instruments cover (2026-08-26 04Z .. 08-30 20Z), same book form
(w10_health LEGS=101 PHI=0.45 MEMBERS_TOPN=829 UMASK m1, FTRIM off == the live book then).
Replay series pulled from pod2 artifact w10_ablation_series_NOFTRIM_M1_UPIT_log_s42_ccal.npz
(column 'carry' = sum(sm*rate*4/iv)*1e4, 'gross_total' = sum|sm|)."""
import json, glob, collections, datetime, math, statistics as stt
LOG='/Users/haosiyu/dl_quant_live/state/live/pilot_log'; H4=14400
R=json.load(open('/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/replay_carry_overlap.json'))
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
for tag,label in (('NOFTRIM_M1_UPIT_log_s42_ccal','replay NO-FTRIM (== live book form in this window)'),
                  ('M1_UPIT_log_s42_ccal','replay WITH-FTRIM (counterfactual, not live then)')):
    pairs=[]
    for t,c,g in R[tag]:
        if G.get(t) and t in PAID:
            pairs.append((t, c/g, -PAID[t]/G[t]*1e4))
    m=[p[1] for p in pairs]; l=[p[2] for p in pairs]; d=[a-b for a,b in zip(m,l)]
    se=stt.pstdev(d)/math.sqrt(len(d))
    print('%-52s n=%2d  model %6.3f  live-realized %6.3f  model-live %+6.3f (se %.3f, t %+5.2f)  ratio %.3f'
          %(label,len(pairs),stt.mean(m),stt.mean(l),stt.mean(d),se,stt.mean(d)/se,stt.mean(m)/stt.mean(l)))

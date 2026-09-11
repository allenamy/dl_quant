import json,os,collections,datetime
base='/Users/haosiyu/dl_quant_live/state/live/pilot_log'
days=[d for d in sorted(os.listdir(base)) if d>='20260826']
# anchors: grid_anchor -> realized_gross, bnb mid
anch={}
for d in sorted(os.listdir(base)):
    p=f'{base}/{d}/anchors.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        ln=ln.strip()
        if not ln: continue
        try: r=json.loads(ln)
        except: continue
        ats=r.get('anchor_ts')
        if ats is None: continue
        g=int(round(float(ats)/14400.0))*14400
        mv=r.get('mid_at_anchor_vector')
        bnb=None
        if isinstance(mv,str):
            try: bnb=json.loads(mv).get('BNBUSDT')
            except: pass
        elif isinstance(mv,dict): bnb=mv.get('BNBUSDT')
        anch[g]=dict(gross=float(r.get('realized_gross') or 0), bnb=bnb, tgt=float(r.get('target_gross') or 0), rid=r.get('rebalance_id'), skipped=r.get('n_names_skipped'))
rows=collections.defaultdict(lambda: dict(raw_u=0.0,raw_b=0.0,raw_n=0.0,dd_u=0.0,dd_b=0.0,dd_n=0.0))
seen=set()
for d in days:
    p=f'{base}/{d}/fills.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        ln=ln.strip()
        if not ln: continue
        try: r=json.loads(ln)
        except: continue
        ats=r.get('anchor_ts')
        if ats is None: continue
        g=int(round(float(ats)/14400.0))*14400
        c=float(r.get('commission') or 0); a=r.get('commission_asset'); n=abs(float(r.get('fill_notional') or 0))
        t=rows[g]
        t['raw_n']+=n
        if a=='USDT': t['raw_u']+=c
        else: t['raw_b']+=c
        tid=r['trade_id']
        if tid in seen: continue
        seen.add(tid)
        t['dd_n']+=n
        if a=='USDT': t['dd_u']+=c
        else: t['dd_b']+=c
CE=1787716800; END=1789084800
out=[]
for g in sorted(rows):
    if g<CE or g>END: continue
    a=anch.get(g)
    if not a or a['gross']<=0: continue
    bnb=a['bnb'] or 0
    t=rows[g]
    out.append(dict(A=g,utc=datetime.datetime.utcfromtimestamp(g).strftime('%Y-%m-%dT%H:%MZ'),gross=a['gross'],
        raw_fee=t['raw_u']+t['raw_b']*bnb, dd_fee=t['dd_u']+t['dd_b']*bnb,
        raw_to=t['raw_n'], dd_to=t['dd_n'], bnb=bnb, skipped=a['skipped'], tgt=a['tgt']))
json.dump(out,open(os.path.dirname(os.path.abspath(__file__))+'/r6_fee.json','w'),indent=1)
def m(x): return sum(x)/len(x)
def med(x): s=sorted(x); return s[len(s)//2]
print('anchors',len(out))
for k in ('raw','dd'):
    fee=[r[f'{k}_fee']/r['gross']*1e4 for r in out]
    to=[r[f'{k}_to']/r['gross'] for r in out]
    rate=[r[f'{k}_fee']/r[f'{k}_to']*1e4 for r in out if r[f'{k}_to']>0]
    print(f"{k}: fee_bps_of_gross mean {m(fee):.4f}  turnover/gross mean {m(to)*100:.2f}% median {med(to)*100:.2f}%  fee rate bps/unit-traded {m(rate):.3f}")
print('total fee USD raw',round(sum(r['raw_fee'] for r in out),1),'dedup',round(sum(r['dd_fee'] for r in out),1))
print('total traded notional raw',round(sum(r['raw_to'] for r in out),0),'dedup',round(sum(r['dd_to'] for r in out),0))

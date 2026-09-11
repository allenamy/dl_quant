import json,os,collections,datetime,math
base='/Users/haosiyu/dl_quant_live/state/live/pilot_log'
def grid(t): return int(round(float(t)/14400.0))*14400
# anchors
A={}
for d in sorted(os.listdir(base)):
    p=f'{base}/{d}/anchors.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        ln=ln.strip()
        if not ln: continue
        try: r=json.loads(ln)
        except: continue
        if r.get('anchor_ts') is None: continue
        g=grid(r['anchor_ts'])
        mv=r.get('mid_at_anchor_vector'); mids={}
        if isinstance(mv,str):
            try: mids=json.loads(mv)
            except: mids={}
        elif isinstance(mv,dict): mids=mv
        A[g]=dict(gross=float(r.get('realized_gross') or 0),mids=mids,skipped=r.get('n_names_skipped'),ts=float(r['anchor_ts']))
# positions
POS=collections.defaultdict(dict)
for d in sorted(os.listdir(base)):
    p=f'{base}/{d}/position_readback.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        ln=ln.strip()
        if not ln: continue
        try: r=json.loads(ln)
        except: continue
        if r.get('anchor_ts') is None: continue
        g=grid(r['anchor_ts'])
        q=r.get('venue_position_qty')
        if q is None: continue
        POS[g][r['symbol']]=(float(q), float(r.get('venue_position_notional') or 0))
# funding deduped
FUND=collections.defaultdict(float); seenf=set()
for d in sorted(os.listdir(base)):
    p=f'{base}/{d}/funding.jsonl'
    if not os.path.exists(p): continue
    for ln in open(p):
        ln=ln.strip()
        if not ln: continue
        try: r=json.loads(ln)
        except: continue
        k=(r['symbol'],r['settlement_ts'])
        if k in seenf: continue
        seenf.add(k)
        FUND[r['settlement_ts']]+= -float(r.get('funding_paid') or 0)   # P&L sign: paid>0 = we pay
rows=[]
gs=sorted(A)
for i,g in enumerate(gs[:-1]):
    g2=gs[i+1]
    if g2-g!=14400: continue
    m1=A[g]['mids']; m2=A[g2]['mids']; pos=POS.get(g)
    if not pos or not m1 or not m2: continue
    pnl=0.0; cov=0.0; unc=0.0
    for s,(q,notl) in pos.items():
        if abs(notl)<1e-9: continue
        p1=m1.get(s); p2=m2.get(s)
        if p1 and p2:
            pnl+=q*(p2-p1); cov+=abs(notl)
        else: unc+=abs(notl)
    fd=sum(v for t,v in FUND.items() if g < t <= g2)
    gr=A[g]['gross'] or cov
    if gr<=0: continue
    rows.append(dict(A=g,utc=datetime.datetime.utcfromtimestamp(g).strftime('%Y-%m-%dT%H:%MZ'),
        gross=gr,cov=cov,unc=unc,price=pnl,fund=fd,
        price_bps=pnl/gr*1e4,fund_bps=fd/gr*1e4))
json.dump(rows,open(os.path.dirname(os.path.abspath(__file__))+'/r6_live.json','w'),indent=1)
CE=1787716800; END=1789084800
ce=[r for r in rows if CE<=r['A']<=END]
def m(x): return sum(x)/len(x)
def sd(x):
    mu=m(x); return (sum((a-mu)**2 for a in x)/(len(x)-1))**.5
def t(x): return m(x)/(sd(x)/len(x)**.5)
print('combo-era anchors',len(ce))
pb=[r['price_bps'] for r in ce]; fb=[r['fund_bps'] for r in ce]
print(f"price bps mean {m(pb):.4f} sd {sd(pb):.3f} t {t(pb):.2f}")
print(f"fund  bps mean {m(fb):.4f} sd {sd(fb):.3f} t {t(fb):.2f}")
print(f"net (price+fund) {m(pb)+m(fb):.4f}")
print('USD price',round(sum(r['price'] for r in ce),1),'USD fund',round(sum(r['fund'] for r in ce),1),'sum',round(sum(r['price']+r['fund'] for r in ce),1))
print('uncovered gross frac mean', round(m([r['unc']/(r['cov']+r['unc']) for r in ce]),5))
# dollar-weighted bps
print('DOLLAR-WEIGHTED bps/anchor:', round(sum(r['price']+r['fund'] for r in ce)/sum(r['gross'] for r in ce)*1e4*len(ce)/len(ce),4))
print('  (= sum pnl / sum gross *1e4) =', round(sum(r['price']+r['fund'] for r in ce)/sum(r['gross'] for r in ce)*1e4,4))

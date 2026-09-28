"""Frozen post-snapshot static-target benchmark; not a tradeable strategy backtest."""
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import actual_cash_bridge as B

PINS={'INPUT.json':'6639dac23e92b9caaa40f952cc8026ee2a6db87b923c6451cb8600eba185e16e',
      'RESULT.json':'7ccc360d2b0d6597a617850fa23d064f4b48f728ec47d44afd5b36e5e6e6b5b1'}
CENSUS='013971851550b68371f196ba5f2b604f3b0b66c9a4b4e2b1c8fa01d09779d8dc'

def finite(x):
    if type(x) not in (float,int) or not math.isfinite(x):raise ValueError('nonfinite')
    return x

def known_target(rows,gross,logged_ts,start_ts):
    if finite(logged_ts)>finite(start_ts):raise ValueError('target_not_known_at_start')
    if finite(gross)<=0 or not rows:raise ValueError('gross_or_population')
    targets={}
    for row in rows:
        s=row['symbol'];v=finite(row['target_w'])*gross
        if s in targets and targets[s]!=v:raise ValueError('conflicting_target')
        targets[s]=v
    return targets

def decompose(start,end,fills,target,halted):
    if type(halted) is not bool:raise ValueError('halt_unknown')
    finite(target)
    for p in (start,end):
        q,n=finite(p['qty']),finite(p['notional'])
        if (q==0)!=(n==0) or (q and n/q<=0):raise ValueError('position_units')
    for f in fills:
        q,n=finite(f['qty']),finite(f['quote'])
        if (q==0)!=(n==0) or (q and n/q<=0):raise ValueError('trade_units')
    q0,q1=start['qty'],end['qty'];p0=start['notional']/q0 if q0 else None;p1=end['notional']/q1 if q1 else None
    qtysum=math.fsum(f['qty'] for f in fills);quote=math.fsum(f['quote'] for f in fills)
    ref=max([p for p in (p0,p1) if p is not None]+[abs(f['quote']/f['qty']) for f in fills if f['qty']]+[0])
    if abs(q0+qtysum-q1)*ref>.01:raise ValueError('quantity_not_closed')
    result={'actual':end['notional']-start['notional']-quote,'benchmark':None,'alignment':None,'trading':None,
            'start_qty':q0,'end_qty':q1,'start_mark':p0,'end_mark':p1,'target_notional':target,'halted_start':halted,
            'start_actual_gross':abs(start['notional']),'end_actual_gross':abs(end['notional']),
            'target_gross':abs(target),'verdict':'UNPRICED','reasons':[]}
    if not halted and target and p0 is None:result['reasons'].append('start_mark_missing_for_target')
    qb=q0 if halted else target/p0 if p0 is not None else 0
    if p1 is None and (q0 or qb or fills):result['reasons'].append('end_mark_missing')
    if result['reasons']:return result
    benchmark=qb*(p1-p0) if qb else 0
    start_hold=q0*(p1-p0) if q0 else 0
    trading=math.fsum(f['qty']*p1-f['quote'] for f in fills) if fills else 0
    err=result['actual']-math.fsum([benchmark,start_hold-benchmark,trading])
    if abs(err)>1e-7:raise ValueError('decomposition_identity')
    result.update(verdict='PRICED',benchmark=benchmark,alignment=start_hold-benchmark,trading=trading,identity_error=err)
    return result

def summary(pieces):
    yes=[p for p in pieces if p['verdict']=='PRICED'];no=[p for p in pieces if p['verdict']!='PRICED']
    r={'n':len(pieces),'priced':len(yes),'unpriced':len(no),'actual_total':math.fsum(p['actual'] for p in pieces),
       'priced_actual':math.fsum(p['actual'] for p in yes),'unpriced_actual':math.fsum(p['actual'] for p in no),
       'reasons':dict(collections.Counter(x for p in no for x in p['reasons']))}
    for key in ('benchmark','alignment','trading'):
        r['priced_'+key]=math.fsum(p[key] for p in yes);r['complete_'+key]=None if no else r['priced_'+key]
    for key in ('start_actual_gross','end_actual_gross','target_gross'):
        r[key]=math.fsum(p[key] for p in pieces);r['unpriced_'+key]=math.fsum(p[key] for p in no)
    return r

def analyze(parent,census,out):
    raw={n:(parent/n).read_bytes() for n in PINS}
    for n,sha in PINS.items():
        if B.sha(raw[n])!=sha:raise ValueError('parent_identity')
    cr=(census/'RESULT.json').read_bytes()
    if B.sha(cr)!=CENSUS:raise ValueError('census_identity')
    meta=json.loads(cr)
    for name,sha in meta['outputs'].items():
        if B.sha((census/name).read_bytes())!=sha:raise ValueError('census_output_identity:'+name)
    data=json.loads(raw['INPUT.json']);cash=json.loads(raw['RESULT.json']);fills=B.trades(data['fills']);snapshots={}
    anchors=[x for p in census.glob('*_anchors.json') for x in json.loads(p.read_bytes())]
    orders=[x for p in census.glob('*_orders.json') for x in json.loads(p.read_bytes())];phases=json.loads((census/'PHASES.json').read_bytes())
    targets={}
    for row in data['census_rows']:
        a=row['execution_anchor'];obs=data['observations'][str(a)]
        if len(obs)!=1:raise ValueError('observation_identity')
        sn=B.snapshot([x for x in data['readbacks'] if x.get('anchor_ts')==a and x.get('source')==B.SOURCE],obs[0]['observation'])
        snapshots[row['anchor']]=sn;rid=row['rid']
        ar=[x for x in anchors if x['rebalance_id']==rid];pa=[x for x in phases if x['phase']=='A' and x['data'].get('rebalance_id')==rid]
        if len(ar)!=1 or len(pa)!=1 or ar[0]['anchor_ts']!=a:raise ValueError('decision_identity')
        stamp=datetime.datetime.fromisoformat(pa[0]['logged_utc'].replace('Z','+00:00')).timestamp()
        target=known_target([x for x in orders if x['rebalance_id']==rid],ar[0]['target_gross'],stamp,sn['read_ts'])
        if type(row['opening_halted']) is not bool:raise ValueError('halt_status')
        targets[row['anchor']]={'notionals':target,'halted':row['opening_halted'],'known_at':stamp}
    windows=[];groups=collections.defaultdict(list)
    for w in cash['windows']:
        if w['quantity_verdict']!='CONSISTENT':continue
        a,b=snapshots[w['anchor_from']],snapshots[w['anchor_to']];t=targets[w['anchor_from']]
        fs=[f for f in fills if w['from']<f['ts']<=w['to']]
        names=set(a['positions'])|set(b['positions'])|set(t['notionals'])|{f['symbol'] for f in fs};zero={'qty':0,'notional':0}
        pieces=[dict(symbol=s,**decompose(a['positions'].get(s,zero),b['positions'].get(s,zero),
                [f for f in fs if f['symbol']==s],t['notionals'].get(s,0),t['halted'])) for s in sorted(names)]
        total=summary(pieces)
        if abs(total['actual_total']-w['price_trade_cash_usdt'])>1e-8:raise ValueError('cash_population_identity')
        period='recovery_three' if w['anchor_from']>=1790510400 else 'pre_double_executor_thirteen';groups[period].extend(pieces)
        windows.append({'anchor_from':w['anchor_from'],'anchor_to':w['anchor_to'],'from':w['from'],'to':w['to'],
             'decision_known_at':t['known_at'],'halted_start':t['halted'],'period':period,'summary':total,'pieces':pieces})
    if len(windows)!=16:raise ValueError('window_population')
    result={'utc':time.strftime('%FT%TZ',time.gmtime()),'scope':'posthoc static post-snapshot known-target zero-cost benchmark; no new strategy or execution quality claim',
      'parent_pins':PINS,'census_sha256':CENSUS,'source_sha256':B.sha(Path(__file__).read_bytes()),
      'parent_device_sha256':B.sha(Path(B.__file__).read_bytes()),'windows':windows,'summary':{g:summary(p) for g,p in groups.items()},
      'limits':['benchmark changes only at start, actual policy changes inside interval',
                'zero-cost theoretical rebalance at account mark, not actual execution price',
                'complete window decomposition null if any required mark missing; excluded actual money retained',
                'no baseline funding or fees imputed; no full USD NAV, no Sharpe, no candidate verdict']}
    out.mkdir(exist_ok=False);B.put(out/'RESULT.json',result)
    print(json.dumps({'summary':result['summary'],'sha256':B.sha((out/'RESULT.json').read_bytes())},indent=2))

if __name__=='__main__':analyze(*map(Path,sys.argv[1:]))

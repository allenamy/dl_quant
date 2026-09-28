"""Independent raw-input Decimal verification; no analyzer imports."""
from collections import defaultdict
from decimal import Decimal as D
import datetime
import hashlib
import json
from pathlib import Path
import sys

def run(parent,census,result_path,out):
    r=json.loads(result_path.read_bytes());d=json.loads((parent/'INPUT.json').read_bytes())
    for name,sha in r['parent_pins'].items():assert hashlib.sha256((parent/name).read_bytes()).hexdigest()==sha
    assert hashlib.sha256((census/'RESULT.json').read_bytes()).hexdigest()==r['census_sha256']
    cm=json.loads((census/'RESULT.json').read_bytes())
    for name,sha in cm['outputs'].items():assert hashlib.sha256((census/name).read_bytes()).hexdigest()==sha
    orders=[x for p in census.glob('*_orders.json') for x in json.loads(p.read_bytes())]
    anchors=[x for p in census.glob('*_anchors.json') for x in json.loads(p.read_bytes())]
    phase=json.loads((census/'PHASES.json').read_bytes());canonical={}
    for f in d['fills']:
        key=(f['symbol'],str(f['trade_id']));fields=tuple(f[k] for k in ('side','fill_ts','fill_notional','fill_px'))
        assert key not in canonical or canonical[key]==fields;canonical[key]=fields
    checks=0;maxerr=0
    def check(a,b):
        nonlocal checks,maxerr
        e=abs(float(a)-float(b));maxerr=max(maxerr,e);checks+=1;assert e<1e-7,(a,b,e)
    for window in r['windows']:
        snaps=[];contexts=[]
        for key in ('anchor_from','anchor_to'):
            c=next(x for x in cm['rows'] if x['anchor']==window[key]);contexts.append(c)
            snaps.append({x['symbol']:x for x in d['readbacks'] if x['anchor_ts']==c['execution_anchor'] and x['source']=='fapi/v3/account@post_anchor'})
        c=contexts[0];ar=next(x for x in anchors if x['rebalance_id']==c['rid']);pp=next(x for x in phase if x['phase']=='A' and x['data'].get('rebalance_id')==c['rid'])
        assert datetime.datetime.fromisoformat(pp['logged_utc'].replace('Z','+00:00')).timestamp()==window['decision_known_at']<=window['from']
        targets={}
        for x in orders:
            if x['rebalance_id']!=c['rid']:continue
            t=D(str(x['target_w']))*D(str(ar['target_gross']))
            assert x['symbol'] not in targets or t==targets[x['symbol']];targets[x['symbol']]=t
        byname=defaultdict(list)
        for (s,tid),(side,ts,quote,price) in canonical.items():
            if window['from']<ts<=window['to']:
                v=D(str(quote))*(1 if side.upper()=='BUY' else -1);byname[s].append((v/D(str(price)),v))
        actual=D(0);components=defaultdict(lambda:D(0));unpriced=D(0)
        for piece in window['pieces']:
            s=piece['symbol'];a=snaps[0].get(s,{});b=snaps[1].get(s,{})
            q0=D(str(a.get('venue_position_qty',0)));q1=D(str(b.get('venue_position_qty',0)))
            n0=D(str(a.get('venue_position_notional',0)));n1=D(str(b.get('venue_position_notional',0)))
            p0=n0/q0 if q0 else None;p1=n1/q1 if q1 else None;t=targets.get(s,D(0))
            value=n1-n0-sum((quote for qty,quote in byname[s]),D(0));check(value,piece['actual']);actual+=value
            check(t,piece['target_notional']);assert piece['halted_start']==c['opening_halted']
            reasons=[]
            if not c['opening_halted'] and t and p0 is None:reasons.append('start_mark_missing_for_target')
            qb=q0 if c['opening_halted'] else t/p0 if p0 is not None else D(0)
            if p1 is None and (q0 or qb or byname[s]):reasons.append('end_mark_missing')
            assert reasons==piece['reasons'];checks+=1
            if reasons:
                assert piece['verdict']=='UNPRICED' and piece['benchmark'] is None;unpriced+=value;continue
            benchmark=qb*(p1-p0) if qb else D(0);held=q0*(p1-p0) if q0 else D(0)
            trading=sum((qty*p1-quote for qty,quote in byname[s]),D(0))
            for key,val in [('benchmark',benchmark),('alignment',held-benchmark),('trading',trading)]:
                check(val,piece[key]);components[key]+=val
            check(value,held+trading)
        check(actual,window['summary']['actual_total']);check(unpriced,window['summary']['unpriced_actual'])
        for key,val in components.items():check(val,window['summary']['priced_'+key])
    receipt={'verdict':'PASS','checks':checks,'max_arithmetic_delta':maxerr,
       'result_sha256':hashlib.sha256(result_path.read_bytes()).hexdigest(),
       'verify_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'method':'raw source target population, original fills, decision timestamp, Decimal endpoints and decomposition; no analyzer imports'}
    out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':run(*map(Path,sys.argv[1:]))

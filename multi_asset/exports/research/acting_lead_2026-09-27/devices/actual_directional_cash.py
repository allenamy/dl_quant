"""Post-hoc pooled direction decomposition; no strategy, venue, or live dependencies."""
import collections
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import actual_cash_bridge as B
import actual_cash_income_diagnostic as I

PINS = {
    'INPUT.json': '6639dac23e92b9caaa40f952cc8026ee2a6db87b923c6451cb8600eba185e16e',
    'RESULT.json': '7ccc360d2b0d6597a617850fa23d064f4b48f728ec47d44afd5b36e5e6e6b5b1',
    'income_diagnostic/income.jsonl': 'd743a9df51022fc3082441658aa5abde5a844bc31619d0875707195bc770bbc8',
}


def decimal(v):
    if type(v) not in (float, int) or not math.isfinite(v):
        raise ValueError('nonfinite_numeric')
    return Decimal(str(v))


def classify(start_qty, fills, reference_price):
    q = decimal(start_qty)
    px = decimal(reference_price)
    if px <= 0:
        if q == 0 and not fills:
            return 'FLAT'
        raise ValueError('reference_price')
    tol = Decimal('.01') / px
    def sign(v):
        return 1 if v > tol else -1 if v < -tol else 0
    seen = {sign(q)} - {0}
    possible = set(seen)
    groups = collections.defaultdict(list)
    for f in fills:
        decimal(f['ts'])
        groups[f['ts']].append(decimal(f['qty']))
    for ts in sorted(groups):
        quantities = groups[ts]
        low = q + sum((x for x in quantities if x < 0), Decimal(0))
        high = q + sum((x for x in quantities if x > 0), Decimal(0))
        possible.update({sign(low), sign(high)} - {0})
        q += sum(quantities, Decimal(0))
        seen.update({sign(q)} - {0})
    if len(seen) == 2:
        return 'CONFIRMED_FLIP'
    if len(possible) == 2:
        return 'INTRATIMESTAMP_AMBIGUOUS'
    return {frozenset(): 'FLAT', frozenset({1}): 'LONG_ONLY',
            frozenset({-1}): 'SHORT_ONLY'}[frozenset(possible)]


def sums(rows, key):
    d = collections.defaultdict(list)
    for row in rows:
        decimal(row[key])
        if not isinstance(row['asset'], str) or not row['asset']:
            raise ValueError('asset_missing')
        d[row['asset']].append(row[key])
    return {k: math.fsum(v) for k,v in sorted(d.items())}


def component(symbol, start, end, fills, income):
    for p in (start,end):
        for v in p.values(): decimal(v)
        if (p['qty'] == 0) != (p['notional'] == 0): raise ValueError('endpoint_units')
        if p['qty'] and p['notional']/p['qty'] <= 0: raise ValueError('endpoint_mark')
    marks = [p['notional']/p['qty'] for p in (start,end) if p['qty']]
    for f in fills:
        q, n = decimal(f['qty']), decimal(f['quote'])
        if (q == 0) != (n == 0) or (q and n/q <= 0): raise ValueError('fill_units')
        if q: marks.append(float(n/q))
    ref = max(marks, default=0)
    tail = decimal(start['qty']) + sum((decimal(f['qty']) for f in fills),Decimal(0))
    error = float(abs(tail-decimal(end['qty'])))*ref
    if error > .01: raise ValueError('quantity_not_closed')
    category = classify(start['qty'], fills, ref)
    if category == 'FLAT' and not fills and not start['qty'] and not end['qty'] and income:
        category = 'NO_OBSERVED_POSITION'
    return dict(symbol=symbol, category=category, start_qty=start['qty'], end_qty=end['qty'],
                fills=len(fills), reference_price=ref, residual_equiv_usdt=error,
                price_trade_cash_usdt=end['notional']-start['notional']-math.fsum(f['quote'] for f in fills),
                fees_native=sums(fills,'fee'), recorded_funding_native=sums(income,'income'))


def aggregate(rows):
    r={'name_windows':len(rows),'price_trade_cash_usdt':math.fsum(x['price_trade_cash_usdt'] for x in rows)}
    for key in ('fees_native','recorded_funding_native'):
        assets=set().union(*(set(x[key]) for x in rows)) if rows else set()
        r[key]={a:math.fsum(x[key].get(a,0) for x in rows) for a in sorted(assets)}
    return r


def analyze(root, out):
    raw={}
    for name, pin in PINS.items():
        raw[name]=(root/name).read_bytes()
        if hashlib.sha256(raw[name]).hexdigest()!=pin: raise ValueError('input_changed:'+name)
    data=json.loads(raw['INPUT.json']); parent=json.loads(raw['RESULT.json'])
    fills=B.trades(data['fills']); incomes=I.rows(raw['income_diagnostic/income.jsonl'])
    snapshots={}
    for r in data['census_rows']:
        a=r['execution_anchor']; obs=data['observations'][str(a)]
        if len(obs)!=1: raise ValueError('observation_identity')
        snapshots[r['anchor']]=B.snapshot([x for x in data['readbacks'] if x.get('anchor_ts')==a and x.get('source')==B.SOURCE],obs[0]['observation'])
    windows=[]; grouped=collections.defaultdict(list)
    for w in parent['windows']:
        if w['quantity_verdict']!='CONSISTENT': continue
        a,b=snapshots[w['anchor_from']],snapshots[w['anchor_to']]
        reproduced=B.window(a,b,fills)
        if any(reproduced[k]!=w[k] for k in reproduced): raise ValueError('parent_reproduction')
        fs=[f for f in fills if w['from']<f['ts']<=w['to']]
        inc=[r for r in incomes if r['type']=='FUNDING_FEE' and w['from']<r['time']/1000<=w['to']]
        if any(not isinstance(r.get('symbol'),str) or not r['symbol'] for r in inc): raise ValueError('funding_symbol')
        names=set(a['positions'])|set(b['positions'])|{f['symbol'] for f in fs}|{r['symbol'] for r in inc}
        zero={'qty':0,'notional':0}
        pieces=[component(s,a['positions'].get(s,zero),b['positions'].get(s,zero),
                          [f for f in fs if f['symbol']==s],[r for r in inc if r['symbol']==s]) for s in sorted(names)]
        total=aggregate(pieces)
        if abs(total['price_trade_cash_usdt']-w['price_trade_cash_usdt'])>1e-9: raise ValueError('cash_identity')
        for key,expected in [('fees_native',w['fees_native']),('recorded_funding_native',sums(inc,'income'))]:
            if set(total[key])!=set(expected) or any(abs(total[key][k]-expected[k])>1e-9 for k in expected): raise ValueError(key+'_identity')
        period='recovery_three' if w['anchor_from']>=1790510400 else 'pre_double_executor_thirteen'
        grouped[period].extend(pieces)
        windows.append({'anchor_from':w['anchor_from'],'anchor_to':w['anchor_to'],'from':w['from'],'to':w['to'],
                        'period':period,'total':total,'pieces':pieces})
    if len(windows)!=16 or collections.Counter(w['period'] for w in windows)!={'pre_double_executor_thirteen':13,'recovery_three':3}:
        raise ValueError('scope_changed')
    summary={}
    for period,pieces in grouped.items():
        by_category={c:aggregate([r for r in pieces if r['category']==c]) for c in sorted({r['category'] for r in pieces})}
        symbols={s:aggregate([r for r in pieces if r['symbol']==s]) for s in sorted({r['symbol'] for r in pieces})}
        summary[period]={'total':aggregate(pieces),'by_category':by_category,
                         'descriptive_worst_price_names':sorted([dict(symbol=s,**v) for s,v in symbols.items()],key=lambda r:r['price_trade_cash_usdt'])[:15]}
    out.mkdir(exist_ok=False)
    result={'utc':time.strftime('%FT%TZ',time.gmtime()),'scope':'sixteen_quantity_closed_windows_posthoc_direction_diagnosis',
            'input_sha256':PINS,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'dependency_sha256':{str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(B.__file__),Path(I.__file__),B.FR_PATH)},
            'windows':windows,'summary':summary,'limits':['native USDT cash, not USD NAV return',
            'three quantity-inconsistent windows excluded unchanged','funding only recorded income, completeness uncertified',
            'actual position direction does not identify King/F10/funding model legs','post-hoc descriptive groups, not causal attribution or actionable candidate']}
    B.put(out/'RESULT.json',result)
    print(json.dumps({'summary':{p:{'total':v['total'],'by_category':v['by_category']} for p,v in summary.items()},'result_sha256':B.sha((out/'RESULT.json').read_bytes())},indent=2))


if __name__=='__main__': analyze(Path(sys.argv[1]),Path(sys.argv[2]))

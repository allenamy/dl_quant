"""Independent raw-row Decimal arithmetic; does not import analyzer or parent reader."""
from collections import defaultdict
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import sys


def run(parent, result_path, out):
    source=json.loads((parent/'INPUT.json').read_text()); result=json.loads(result_path.read_text())
    for name,sha in result['input_sha256'].items():
        assert hashlib.sha256((parent/name).read_bytes()).hexdigest()==sha, name
    canonical={}
    for row in source['fills']:
        key=(row['symbol'],str(row['trade_id']))
        fields=tuple(row[k] for k in ('side','fill_ts','fill_notional','fill_px','commission','commission_asset'))
        assert key not in canonical or fields==canonical[key]
        canonical[key]=fields
    income={}
    for line in (parent/'income_diagnostic/income.jsonl').read_text().splitlines():
        row=json.loads(line)
        k=(str(row['tranId']),row['type'],row.get('symbol'),row['asset'],row['time'])
        assert k not in income or row==income[k]
        income[k]=row
    checks=0;maxerr=0
    def check(a,b):
        nonlocal checks,maxerr
        err=abs(float(a)-float(b));maxerr=max(maxerr,err);checks+=1
        assert err<1e-8,(a,b,err)
    for window in result['windows']:
        endpoints=[]
        for key in ('anchor_from','anchor_to'):
            execution=next(r['execution_anchor'] for r in source['census_rows'] if r['anchor']==window[key])
            rr=[r for r in source['readbacks'] if r['anchor_ts']==execution and r['source']=='fapi/v3/account@post_anchor']
            assert len({r['read_ts'] for r in rr})==1
            endpoints.append({r['symbol']:r for r in rr})
        total=D(0)
        for piece in window['pieces']:
            s=piece['symbol'];a=endpoints[0].get(s,{});b=endpoints[1].get(s,{})
            cash=D(str(b.get('venue_position_notional',0)))-D(str(a.get('venue_position_notional',0)))
            fees=defaultdict(lambda:D(0)); groups=defaultdict(list)
            q=D(str(a.get('venue_position_qty',0)));certain=[q];bounds=[q]
            for (symbol,_),f in canonical.items():
                side,ts,quote,price,fee,asset=f
                if symbol!=s or not window['from']<ts<=window['to']:continue
                signed=D(str(quote))*(1 if side.upper()=='BUY' else -1)
                cash-=signed;fees[asset]+=D(str(fee));groups[ts].append(signed/D(str(price)))
            for ts,changes in sorted(groups.items()):
                bounds.extend([q+sum((x for x in changes if x<0),D(0)),q+sum((x for x in changes if x>0),D(0))])
                q+=sum(changes,D(0));certain.append(q)
            ref=D(str(piece['reference_price']));tol=D('.01')/ref if ref else D(0)
            if min(certain)<-tol and max(certain)>tol:category='CONFIRMED_FLIP'
            elif min(bounds)<-tol and max(bounds)>tol:category='INTRATIMESTAMP_AMBIGUOUS'
            elif max(bounds)>tol:category='LONG_ONLY'
            elif min(bounds)<-tol:category='SHORT_ONLY'
            else:category='FLAT'
            fund=defaultdict(lambda:D(0))
            for row in income.values():
                if row['type']=='FUNDING_FEE' and row.get('symbol')==s and window['from']<row['time']/1000<=window['to']:
                    fund[row['asset']]+=D(str(row['income']))
            if category=='FLAT' and not groups and fund:category='NO_OBSERVED_POSITION'
            assert category==piece['category'],(s,category,piece['category']);checks+=1
            check(cash,piece['price_trade_cash_usdt']);total+=cash
            for observed,expected in ((fees,piece['fees_native']),(fund,piece['recorded_funding_native'])):
                assert set(observed)==set(expected)
                for asset in observed:check(observed[asset],expected[asset])
        check(total,window['total']['price_trade_cash_usdt'])
    receipt={'checks':checks,'max_arithmetic_delta':maxerr,'result_sha256':hashlib.sha256(result_path.read_bytes()).hexdigest(),
             'verify_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'verdict':'PASS','method':'raw canonical trade/income Decimal arithmetic and grouped quantity min/max; no analyzer imports'}
    out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__': run(*map(Path,sys.argv[1:]))

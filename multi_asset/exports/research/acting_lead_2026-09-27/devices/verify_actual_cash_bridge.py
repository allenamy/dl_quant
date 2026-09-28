"""Independent Decimal recomputation from captured original bytes; no bridge import."""
import collections,hashlib,json,math,re,sys
from decimal import Decimal as D
from pathlib import Path
r=Path(sys.argv[1]);res=json.loads((r/'RESULT.json').read_text());cap=json.loads((r/'CAPTURE.json').read_text());checks=0;maxdiff=D(0)
def check(v,why):
 global checks
 checks+=1
 if not v:raise AssertionError(why)
for p,m in cap['source_files'].items():check(hashlib.sha256((r/m['snapshot']).read_bytes()).hexdigest()==m['sha256'],'raw SHA '+p)
raw=r/'raw';fills={};rb=collections.defaultdict(dict)
for p in sorted(raw.glob('*_fills.jsonl')):
 for l in p.read_text().splitlines():
  f=json.loads(l);k=(f['symbol'],str(f['trade_id']))
  if k in fills:
   for field in ('side','fill_ts','fill_notional','fill_px','commission','commission_asset'):check(f[field]==fills[k][field],'raw duplicate conflict')
  fills[k]=f
for p in sorted(raw.glob('*_position_readback.jsonl')):
 for l in p.read_text().splitlines():
  x=json.loads(l)
  if x['source']!='fapi/v3/account@post_anchor':continue
  k=x['read_ts'];s=x['symbol'];check(s not in rb[k],'duplicate raw snapshot');rb[k][s]=x
for w in res['windows']:
 if w['quantity_verdict']=='UNAVAILABLE_ENDPOINT':continue
 a,b=rb[w['from']],rb[w['to']];fs=[f for f in fills.values() if w['from']<f['fill_ts']<=w['to']]
 check(len(fs)==w['fills'],'fill population')
 q=collections.defaultdict(lambda:D(0));cash=collections.defaultdict(lambda:D(0));fees=collections.defaultdict(lambda:D(0));price=collections.defaultdict(list)
 for f in fs:
  s=f['symbol'];px=D(str(f['fill_px']));signed=D(str(f['fill_notional']))*(1 if f['side'].upper()=='BUY' else -1)
  q[s]+=signed/px;cash[s]+=signed;fees[f['commission_asset']]+=D(str(f['commission']));price[s].append(px)
 bad=set();components=D(0)
 for s in set(a)|set(b)|set(q):
  qa=D(str(a.get(s,{}).get('venue_position_qty',0)));qb=D(str(b.get(s,{}).get('venue_position_qty',0)))
  na=D(str(a.get(s,{}).get('venue_position_notional',0)));nb=D(str(b.get(s,{}).get('venue_position_notional',0)))
  pp=[abs(n/qq) for n,qq in [(na,qa),(nb,qb)] if qq] or price[s]
  err=abs(qa+q[s]-qb)*(max(pp) if pp else D(0))
  if err>D('.01'):bad.add(s)
  components+=nb-na-cash[s]
 check(bad=={x['symbol'] for x in w['quantity_failures']},'residual population')
 check(bool(bad)==(w['quantity_verdict']=='INCONSISTENT'),'quantity verdict')
 if not bad:
  dd=abs(components-D(str(w['price_trade_cash_usdt'])));check(dd<D('0.00000001'),'cash arithmetic');maxdiff=max(maxdiff,dd)
 else:check(w['price_trade_cash_usdt'] is None,'unknown cash not zero')
 for asset,fee in fees.items():
  dd=abs(fee-D(str(w['fees_native'][asset])));check(dd<D('0.00000001'),'fee arithmetic');maxdiff=max(maxdiff,dd)
 check(w['full_cash_verdict']=='UNAVAILABLE_INDEPENDENT_INCOME_AND_USD_VALUATION','cash cannot graduate')
out={'verdict':'INDEPENDENT_RAW_DECIMAL_PASS','checks':checks,'max_arithmetic_diff':str(maxdiff),'fills_unique':len(fills),'self_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'result_sha256':hashlib.sha256((r/'RESULT.json').read_bytes()).hexdigest(),'scope':'source bytes, duplicates, all 19 quantity and priced-window/fee arithmetic; no independent income certification'}
(r/'VERIFY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

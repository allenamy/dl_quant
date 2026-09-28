"""Supplement with already archived guard-twin native income; explicitly not completeness certified."""
import collections,hashlib,json,math,sys,time
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def rows(raw):
    seen={}
    for l in raw.splitlines():
        if not l.strip():continue
        r=json.loads(l)
        if not isinstance(r,dict) or any(r.get(k) in (None,'') for k in ('tranId','type','asset','time')):raise ValueError('income_schema')
        if type(r.get('income')) not in (float,int) or not math.isfinite(r['income']) or type(r['time']) is not int:raise ValueError('income_numeric')
        k=(str(r['tranId']),r['type'],r.get('symbol'),r['asset'],r['time'])
        if k in seen and r!=seen[k]:raise ValueError('income_identity_conflict')
        seen[k]=r
    return list(seen.values())
def main():
    root=Path(sys.argv[1]);out=root/'income_diagnostic';out.mkdir(exist_ok=False)
    if not 3600<=time.time()%14400<13200:raise ValueError('outside_quiet_window')
    sys.path.insert(0,str(Path(__file__).parents[2]/'common'))
    from venue_quiet_window import quiet_window_status
    quiet=quiet_window_status()
    if not quiet['open'] or quiet['override'] or quiet.get('anchor_in_progress') or quiet.get('stale_start'):raise ValueError('quiet_unverified')
    p=Path.home()/'guard_twin/state/income.jsonl';raw=p.read_bytes();(out/'income.jsonl').write_bytes(raw)
    src=Path.home()/'guard_twin/guard_twin.py';sb=src.read_bytes();(out/'collector.py').write_bytes(sb)
    allr=rows(raw);result=json.loads((root/'RESULT.json').read_text());windows=[]
    for w in result['windows']:
        if 'from' not in w:continue
        inc=[r for r in allr if w['from']<r['time']/1000<=w['to']];v=collections.defaultdict(list);c=collections.Counter()
        for r in inc:v[(r['type'],r['asset'])].append(r['income']);c[(r['type'],r['asset'])]+=1
        totals=[{'type':k[0],'asset':k[1],'n':c[k],'amount':math.fsum(x)} for k,x in sorted(v.items())]
        fee_diffs={a:math.fsum(v.get(('COMMISSION',a),[]))+f for a,f in w['fees_native'].items()}
        windows.append({'from':w['from'],'to':w['to'],'quantity_verdict':w['quantity_verdict'],'income_native':totals,
          'recorded_commission_plus_local_fee_native':fee_diffs,'completeness':'UNAVAILABLE_NO_REQUEST_PAGES',
          'stg_settlement_records':[r for r in inc if r.get('symbol')=='STGUSDT' and r['type']=='DELIVERED_SETTELMENT']})
    d={'utc':time.strftime('%FT%TZ',time.gmtime()),'quiet':quiet,'self_sha256':sha(Path(__file__).read_bytes()),'income_path':str(p),'income_sha256':sha(raw),'income_bytes':len(raw),'collector_sha256':sha(sb),
       'parent_result_sha256':sha((root/'RESULT.json').read_bytes()),'windows':windows,'limits':['pooled observed income only; not full income/transfer certification',
       'collector lacks per-query completion receipt; same-ms saturation advances by 1 and 200-page cap is not fail-closed',
       'no USD conversion, no NAV residual arithmetic, no portfolio total or Sharpe','REALIZED_PNL is closed holding profit, not cost caused by flatten action',
       'income lacks tradeId so cannot use it to synthesize exact missing quantity or execution price']}
    (out/'RESULT.json').write_text(json.dumps(d,indent=2,allow_nan=False)+'\n');print(json.dumps({'windows':len(windows),'income_sha256':d['income_sha256'],'result_sha256':sha((out/'RESULT.json').read_bytes())}))
if __name__=='__main__':main()

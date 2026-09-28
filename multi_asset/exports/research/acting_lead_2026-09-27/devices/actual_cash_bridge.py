"""Fixed twenty-anchor pooled actual-fill/quantity bridge. No network or arm outcomes."""
import argparse,collections,hashlib,importlib.util,json,math,re,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
SOURCE='fapi/v3/account@post_anchor'
FILL_KEYS=('trade_id','symbol','side','order_type','fill_ts','fill_notional','fill_px','commission','commission_asset','supersedes_trade_id','anchor_ts','rebalance_id')
RB_KEYS=('anchor_ts','symbol','source','read_ts','venue_position_qty','venue_position_notional')
CENSUS=Path('/Users/haosiyu/.codex/tmp/execution_input_census_20260928_run3')
FR_PATH=ROOT/'multi_asset/exports/live/pilot_journal/tools/fills_reader.py'
spec=importlib.util.spec_from_file_location('bridge_FR',FR_PATH);FR=importlib.util.module_from_spec(spec);spec.loader.exec_module(FR)
def sha(b):return hashlib.sha256(b).hexdigest()
def finite(v):return type(v) in (int,float) and math.isfinite(v)
def strict_jl(b):
    rs=[json.loads(l) for l in b.splitlines() if l.strip()]
    if any(not isinstance(r,dict) for r in rs):raise ValueError('non_object_jsonl')
    return rs
def put(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def trades(rows):
    # Check raw inputs before canonical reader (which otherwise permits missing fields).
    seen={}
    for r in rows:
        if not isinstance(r.get('symbol'),str) or not r['symbol'] or r.get('trade_id') in (None,''):raise ValueError('missing_trade_identity')
        if str(r.get('side','')).upper() not in ('BUY','SELL'):raise ValueError('unknown_trade_side')
        for k in ('fill_ts','fill_notional','fill_px','commission'):
            if not finite(r.get(k)):raise ValueError('nonfinite_trade_'+k)
        if r['fill_px']<=0 or r['fill_notional']<0:raise ValueError('invalid_trade_price_or_notional')
        if not isinstance(r.get('commission_asset'),str) or not r['commission_asset']:raise ValueError('unknown_fee_asset')
        key=(r['symbol'],str(r['trade_id']))
        # Normalize identity type before FR so numeric/string ids cannot split a fill.
        for k in ('side','fill_ts','fill_notional','fill_px','commission','commission_asset'):
            if key in seen and seen[key][k]!=r[k]:raise ValueError('conflicting_trade_'+k)
        seen[key]=r
    normalized=[dict(r,trade_id=str(r['trade_id'])) for r in rows]
    out=[]
    for r in FR.collapse_supersedes(normalized):
        sign=1 if r['side'].upper()=='BUY' else -1
        out.append({'ts':r['fill_ts'],'symbol':r['symbol'],'trade_id':str(r['trade_id']),'qty':sign*r['fill_notional']/r['fill_px'],
                    'quote':sign*r['fill_notional'],'fee':r['commission'],'asset':r['commission_asset']})
    return sorted(out,key=lambda r:(r['ts'],r['symbol'],r['trade_id']))
def snapshot(rows,obs):
    if obs.get('verdict')!='OBSERVED':raise ValueError('not_positive_complete_observation')
    if not rows or type(obs.get('n_rows')) is not int or len(rows)!=obs['n_rows']:raise ValueError('snapshot_population_count')
    if any(r.get('source')!=SOURCE or r.get('anchor_ts')!=obs.get('anchor_ts') for r in rows):raise ValueError('snapshot_owner')
    if any(not finite(r.get(k)) for r in rows for k in ('read_ts','venue_position_qty','venue_position_notional')):raise ValueError('snapshot_nonfinite')
    times={r['read_ts'] for r in rows}
    if len(times)!=1:raise ValueError('snapshot_call_identity')
    if len({r.get('symbol') for r in rows})!=len(rows):raise ValueError('snapshot_duplicate_symbol')
    p={}
    for r in rows:
        q,n=r['venue_position_qty'],r['venue_position_notional']
        if (q==0)!=(n==0) or (q and n/q<=0):raise ValueError('snapshot_mark_invalid')
        p[r['symbol']]={'qty':q,'notional':n}
    return {'read_ts':next(iter(times)),'positions':p}
def window(a,b,ts):
    t0,t1=a['read_ts'],b['read_ts']
    if t1<=t0:raise ValueError('nonpositive_time_window')
    fs=[r for r in ts if t0<r['ts']<=t1];qs=collections.defaultdict(list);cs=collections.defaultdict(list);fees=collections.defaultdict(list)
    for f in fs:qs[f['symbol']].append(f['qty']);cs[f['symbol']].append(f['quote']);fees[f['asset']].append(f['fee'])
    names=set(a['positions'])|set(b['positions'])|set(qs);bad=[];components=[];maxerr=0.0
    for s in sorted(names):
        p=a['positions'].get(s,{'qty':0,'notional':0});q=b['positions'].get(s,{'qty':0,'notional':0})
        err=p['qty']+math.fsum(qs[s])-q['qty']
        marks=[abs(z['notional']/z['qty']) for z in (p,q) if z['qty']]
        # Flat at both endpoints: fill-price reference needed for nonzero residual.
        if not marks:marks=[abs(f['quote']/f['qty']) for f in fs if f['symbol']==s and f['qty']]
        equivalent=abs(err)*max(marks) if marks else (0.0 if err==0 else None)
        if equivalent is None or equivalent>.01:bad.append({'symbol':s,'residual_qty':err,'residual_equiv_usdt':equivalent})
        if equivalent is not None:maxerr=max(maxerr,equivalent)
        components.append(q['notional']-p['notional']-math.fsum(cs[s]))
    return {'from':t0,'to':t1,'fills':len(fs),'fill_notional_usdt':math.fsum(abs(f['quote']) for f in fs),
      'quantity_verdict':'INCONSISTENT' if bad else 'CONSISTENT','quantity_failures':bad,'max_quantity_residual_equiv_usdt':maxerr,
      'price_trade_cash_usdt':None if bad else math.fsum(components),'fees_native':{k:math.fsum(v) for k,v in sorted(fees.items())},
      'full_cash_verdict':'UNAVAILABLE_INDEPENDENT_INCOME_AND_USD_VALUATION'}
def capture(out):
    if not 3600<=time.time()%14400<13200:raise ValueError('outside_quiet_window')
    sys.path.insert(0,str(Path(__file__).parents[2]/'common'))
    from venue_quiet_window import quiet_window_status
    quiet=quiet_window_status()
    if not quiet['open'] or quiet['override'] or quiet.get('anchor_in_progress') or quiet.get('stale_start'):raise ValueError('quiet_not_verified')
    out.mkdir(exist_ok=False);rawdir=out/'raw';rawdir.mkdir();sources={}
    def read(p,name):
        b=p.read_bytes();(rawdir/name).write_bytes(b);sources[str(p)]={'sha256':sha(b),'bytes':len(b),'snapshot':'raw/'+name};return b
    census=json.loads(read(CENSUS/'RESULT.json','CENSUS_RESULT.json'))
    if sha((CENSUS/'RESULT.json').read_bytes())!='013971851550b68371f196ba5f2b604f3b0b66c9a4b4e2b1c8fa01d09779d8dc':raise ValueError('census_changed')
    rows=census['rows'];anchors=[r['anchor'] for r in rows]
    if len(rows)!=20 or anchors[0]!=1790236800 or anchors[-1]!=1790553600:raise ValueError('scope_changed')
    pilot=Path.home()/'dl_quant_live/state/live/pilot_log';allf=[];allr=[];nav=[]
    for day in sorted({time.strftime('%Y%m%d',time.gmtime(a)) for a in anchors}):
        for stem,keys,target in [('fills',FILL_KEYS,allf),('position_readback',RB_KEYS,allr),('daily_nav',None,nav)]:
            rr=strict_jl(read(pilot/day/(stem+'.jsonl'),day+'_'+stem+'.jsonl'))
            target.extend({k:r[k] for k in keys if k in r} for r in rr) if keys else target.extend(rr)
    log=read(Path.home()/'dl_quant_live/state/anchor_runs.log','anchor_runs.log').decode();obs=collections.defaultdict(list)
    for line in log.splitlines():
        m=re.match(r'^(\S+) phase_C: (.*)$',line)
        if m:
            d=json.loads(m[2]);ob=d.get('book_observation',{});a=ob.get('anchor_ts')
            if a is not None:obs[a].append({'logged_utc':m[1],'observation':ob})
    # Do not persist arm tags or order-routing outcomes into analysis input.
    put(out/'INPUT.json',{'census_rows':rows,'fills':allf,'readbacks':allr,'observations':dict(obs),'daily_nav':nav})
    put(out/'CAPTURE.json',{'utc':time.strftime('%FT%TZ',time.gmtime()),'quiet':quiet,'source_files':sources,'input_sha256':sha((out/'INPUT.json').read_bytes()),'device_sha256':sha(Path(__file__).read_bytes())})
    print(json.dumps({'capture':str(out),'sources':len(sources),'input_sha256':sha((out/'INPUT.json').read_bytes())}))
def analyze(root):
    cap=json.loads((root/'CAPTURE.json').read_text());raw=(root/'INPUT.json').read_bytes()
    if sha(raw)!=cap['input_sha256']:raise ValueError('input_identity')
    d=json.loads(raw);t=trades(d['fills']);snaps=[]
    for r in d['census_rows']:
        a=r['execution_anchor'];oo=d['observations'].get(str(a),[]);out={'anchor':r['anchor'],'execution_anchor':a,'opening_halted':r['opening_halted']}
        rr=[x for x in d['readbacks'] if x.get('anchor_ts')==a and x.get('source')==SOURCE]
        try:
            if len(oo)!=1:raise ValueError('phase_C_not_unique')
            s=snapshot(rr,oo[0]['observation']);out.update(snapshot=s,status='COMPLETE')
            ns=[n for n in d['daily_nav'] if n.get('nav_ts')==s['read_ts']]
            out['matching_nav_rows']=len(ns)
        except ValueError as e:out.update(status='UNAVAILABLE',reason=str(e))
        snaps.append(out)
    windows=[]
    for a,b in zip(snaps,snaps[1:]):
        w={'anchor_from':a['anchor'],'anchor_to':b['anchor'],'grid_gap_anchors':(b['anchor']-a['anchor'])//14400-1,'halted_endpoints':[a['opening_halted'],b['opening_halted']]}
        if a['status']!='COMPLETE' or b['status']!='COMPLETE':w.update(quantity_verdict='UNAVAILABLE_ENDPOINT',price_trade_cash_usdt=None)
        else:w.update(window(a['snapshot'],b['snapshot'],t))
        windows.append(w)
    public_snaps=[{k:v for k,v in s.items() if k!='snapshot'} for s in snaps]
    result={'utc':time.strftime('%FT%TZ',time.gmtime()),'scope':'fixed_twenty_actual_snapshots_pooled_only_no_strategy_return',
      'device_sha256':sha(Path(__file__).read_bytes()),'fills_reader_sha256':sha(FR_PATH.read_bytes()),'input_sha256':sha(raw),'capture_sha256':sha((root/'CAPTURE.json').read_bytes()),
      'raw_fill_rows':len(d['fills']),'collapsed_fills_all_captured_days':len(t),'snapshots':public_snaps,'windows':windows,
      'summary':dict(collections.Counter(w['quantity_verdict'] for w in windows)),
      'limits':['quantity derived from signed quote/price, not raw venue quantity','no independent income/transfer or USD valuation coverage certification',
       'complete snapshots conditional on writer book_observation and row count; source account payload not archived here','fill side comparison pooled; no CFG04/06 outcomes',
       'no flatten counterfactual/action cost, no portfolio return or Sharpe','no source changes to production or venue queries']}
    put(root/'RESULT.json',result);print(json.dumps({'summary':result['summary'],'snapshots':len(snaps),'result_sha256':sha((root/'RESULT.json').read_bytes())}))
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['capture','analyze']);p.add_argument('root',type=Path);a=p.parse_args();(capture if a.mode=='capture' else analyze)(a.root)
if __name__=='__main__':main()

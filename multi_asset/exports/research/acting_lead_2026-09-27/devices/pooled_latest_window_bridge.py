"""Fixed pooled account window, no network, no arm fields, no implicit absent position zero."""
import argparse, collections, hashlib, json, math, pathlib

def price_component(n0,n1,executions):
    return n1-n0-sum((1 if side=='buy' else -1)*notional for side,px,notional in executions)

def run(day,start,end):
    paths={n:day/(n+'.jsonl') for n in ['position_readback','fills','daily_nav']}
    raw={n:p.read_bytes() for n,p in paths.items()}
    source={n:{'path':str(paths[n]),'sha256':hashlib.sha256(b).hexdigest()} for n,b in raw.items()}
    nav={r['nav_ts']:r for r in map(json.loads,raw['daily_nav'].splitlines())}
    if start not in nav or end not in nav or start>=end:raise ValueError('exact NAV endpoint missing')
    ns=[nav[start],nav[end]]
    if any(r['realised_truncated'] or r['external_flow_usdt']!=0 for r in ns):raise ValueError('flow/truncated endpoint')
    snap={start:{},end:{}}
    for r in map(json.loads,raw['position_readback'].splitlines()):
        t=r['read_ts']
        if t not in snap:continue
        sym=r['symbol']
        if sym in snap[t] and snap[t][sym]!=r:raise ValueError('conflicting exact snapshot')
        for k in ['venue_position_qty','venue_position_notional']:
            if not math.isfinite(r[k]):raise ValueError('nonfinite account')
        snap[t][sym]=r
    fills={};duplicates=0
    for r in map(json.loads,raw['fills'].splitlines()):
        if not start<float(r['fill_ts'])<=end:continue
        tid=r['trade_id']
        if isinstance(tid,bool) or not (isinstance(tid,int) or isinstance(tid,str) and tid.isdigit()):raise ValueError('trade identity malformed')
        key=(r['symbol'],int(tid));v=tuple(r[k] for k in ['side','fill_ts','fill_px','fill_notional'])
        if key in fills:
            duplicates+=1
            if fills[key]!=v:raise ValueError('conflicting duplicate execution')
        else:fills[key]=v
    by_symbol=collections.defaultdict(list)
    for (sym,tid),(side,ts,px,n) in fills.items():
        if side not in ['buy','sell'] or not math.isfinite(n) or n<0 or not math.isfinite(px) or px<=0:raise ValueError('execution malformed')
        by_symbol[sym].append((side,px,n))
    rows=[];unresolved=[]
    for sym in sorted(set(snap[start])&set(snap[end])):
        a,b=snap[start][sym],snap[end][sym];q0,q1=a['venue_position_qty'],b['venue_position_qty'];ex=by_symbol[sym]
        dq=sum((1 if side=='buy' else -1)*n/px for side,px,n in ex)
        gap=q1-q0-dq;tol=1e-8*max(1,abs(q0),abs(q1))
        if abs(gap)>tol:unresolved.append({'symbol':sym,'gap':gap,'tolerance':tol});continue
        rows.append({'symbol':sym,'initial_side':'long' if q0>0 else 'short' if q0<0 else 'flat',
                     'price_pnl_usdt':price_component(a['venue_position_notional'],b['venue_position_notional'],ex),
                     'initial_gross':abs(a['venue_position_notional']),'final_gross':abs(b['venue_position_notional']),
                     'q0':q0,'q1':q1,'n_trades':len(ex),'qty_gap':gap,'qty_tolerance':tol,'endpoint_sign_flip':q0*q1<0})
    group={}
    for side in ['long','short','flat']:
        z=[r for r in rows if r['initial_side']==side]
        group[side]={'n':len(z),'price_pnl_usdt':sum(r['price_pnl_usdt'] for r in z),
                     'initial_gross':sum(r['initial_gross'] for r in z),'negative_n':sum(r['price_pnl_usdt']<0 for r in z)}
    a,b=ns;delta={k:b[k]-a[k] for k in ['nav','realised_pnl','unrealised_pnl']}
    delta['income_components']={k:b['realised_by_type'][k]-a['realised_by_type'][k] for k in b['realised_by_type']}
    delta['unexplained_currency_or_cash_bridge']=delta['nav']-delta['realised_pnl']-delta['unrealised_pnl']
    total_price=sum(r['price_pnl_usdt'] for r in rows)
    delta['income_price_plus_unrealised']=delta['income_components']['REALIZED_PNL']+delta['unrealised_pnl']
    for n,p in paths.items():
        if hashlib.sha256(p.read_bytes()).hexdigest()!=source[n]['sha256']:raise ValueError('source grew during read')
    return {'scope':'pooled real fills plus identical-call account endpoints; common observed symbols only; no cost/leg causal attribution',
            'sources':source,'read_ts':[start,end],'snapshot_counts':[len(snap[start]),len(snap[end])],
            'unique_fills':len(fills),'duplicates_collapsed':duplicates,'conflicting_duplicates':0,'rows':rows,'group':group,'unresolved':unresolved,
            'unpaired_names':sorted(set(snap[start])^set(snap[end])),'initial_gross_coverage':sum(r['initial_gross'] for r in rows)/sum(abs(r['venue_position_notional']) for r in snap[start].values()),
            'final_gross_coverage':sum(r['final_gross'] for r in rows)/sum(abs(r['venue_position_notional']) for r in snap[end].values()),
            'nav_bridge':delta,'common_price_pnl_usdt':total_price,'price_outside_common_population':delta['income_price_plus_unrealised']-total_price,
            'endpoint_sign_flips':sum(r['endpoint_sign_flip'] for r in rows),'missing_is_not_zero':True,
            'qty_tolerance':'1e-8 * max(1,abs(q0),abs(q1)); arithmetic closure not exchange-lot gate'}

if __name__=='__main__':
    # Hand-computed self-financing checks; buying extra quantity cannot itself create PnL.
    assert price_component(20,36,[('buy',11,11)])==5
    assert price_component(-20,-12,[('buy',11,11)])==-3
    assert price_component(20,24,[('buy',10,10),('sell',11,11)])==5
    ap=argparse.ArgumentParser();ap.add_argument('--day',type=pathlib.Path,required=True);ap.add_argument('--start',type=float,required=True);ap.add_argument('--end',type=float,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args()
    r=run(a.day,a.start,a.end);r['device_sha256']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    with a.out.open('x') as f:json.dump(r,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:r[k] for k in ['snapshot_counts','unique_fills','duplicates_collapsed','group','unresolved','unpaired_names','initial_gross_coverage','final_gross_coverage','nav_bridge','common_price_pnl_usdt','price_outside_common_population','endpoint_sign_flips']}))

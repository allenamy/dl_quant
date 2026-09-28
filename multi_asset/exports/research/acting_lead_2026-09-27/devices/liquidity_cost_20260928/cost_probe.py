"""Historical, pooled-only cost diagnostic. Strict reads, no live imports/APIs."""
import argparse, collections, hashlib, importlib.util, json, math, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

ORDER_KEYS={'rebalance_id','symbol','order_type','attempt_idx','mid_at_anchor','submit_ts'}
FILL_KEYS={'rebalance_id','symbol','order_type','attempt_idx','trade_id','supersedes_trade_id',
           'fill_ts','fill_px','fill_notional','side','anchor_ts','commission','commission_asset',
           'mid_at_fill_plus_60s','mark_ts_actual','mark_lag_s','mark_window_s','mark_status','backfilled_utc'}


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()


def project(row,keys):return {k:v for k,v in row.items() if k in keys}


def finite(v):
    if isinstance(v,bool) or v is None:return None
    try:x=float(v)
    except (ValueError,TypeError):return None
    return x if math.isfinite(x) else None


def reference(rows):
    vals=[finite(r.get('mid_at_anchor')) for r in rows]
    if not vals or any(v is None or v<=0 for v in vals):return None,'reference_unknown'
    if len(set(vals))!=1:return None,'reference_conflict'
    return vals[0],None


def measure(px,ref,side):
    if side not in ('buy','sell') or not all(finite(v) is not None and v>0 for v in (px,ref)):
        raise ValueError('invalid cost fields')
    return (px/ref-1)*(1 if side=='buy' else -1)


def quartiles(q):
    q=np.asarray(q,float)
    if not len(q) or not np.isfinite(q).all():raise ValueError('qvm unavailable')
    return np.minimum(3,np.floor(4*(rankdata(q)-.5)/len(q))).astype(int)


def key(row):
    return tuple(row.get(k) for k in ('rebalance_id','symbol','order_type','attempt_idx'))


def bootstrap(daily,block):
    # Fixed calendar day blocks; paired buckets keep their common day draws.
    a=np.asarray(daily,float);n=len(a);rng=np.random.default_rng(20260928);vals=[]
    for _ in range(2000):
        starts=rng.integers(0,n,size=math.ceil(n/block))
        ix=((starts[:,None]+np.arange(block))%n).ravel()[:n];s=a[ix].sum(0)
        if s[0,1]>0 and s[3,1]>0:vals.append((s[0,0]/s[0,1]-s[3,0]/s[3,1])*1e4)
    complete=len(vals)==2000
    return {'block_days':block,'draws':len(vals),'requested_draws':2000,
            'status':'COMPLETE' if complete else 'UNAVAILABLE_MISSING_BUCKET_RESAMPLES',
            'ci95_bps':np.quantile(vals,[.025,.975]).tolist() if complete else None}


def run(live,liquidity,reader,out):
    src={str(liquidity):sha(liquidity),str(reader):sha(reader),str(Path(__file__).resolve()):sha(__file__)}
    spec=importlib.util.spec_from_file_location('canonical_fills_reader',reader)
    fr=importlib.util.module_from_spec(spec);spec.loader.exec_module(fr)
    z=np.load(liquidity,allow_pickle=False);axis=z['anchors'];syms=list(map(str,z['symbols']));off=z['off']
    if np.any(np.diff(axis)!=14400):raise ValueError('liquidity axis gap')
    groups={}
    for i,t in enumerate(axis):
        m=z['m'][off[i]:off[i+1]].astype(int);q=z['qvm'][off[i]:off[i+1]]
        if len(set(m))!=len(m) or np.any(m<0) or np.any(m>=len(syms)):raise ValueError('member axis')
        groups[int(t)]={syms[j]:int(g) for j,g in zip(m,quartiles(q))}
    first=datetime(2026,8,26,tzinfo=timezone.utc);dates=[first+timedelta(days=i) for i in range(24)]
    orders=collections.defaultdict(list);raw=[]
    for dt in dates:
        d=live/'state/live/pilot_log'/dt.strftime('%Y%m%d')
        for name,keys in [('orders',ORDER_KEYS),('fills',FILL_KEYS)]:
            p=d/(name+'.jsonl');b=p.read_bytes();src[str(p)]=hashlib.sha256(b).hexdigest()
            for line in b.splitlines():
                if not line.strip():continue
                row=project(json.loads(line),keys)
                if name=='orders':orders[key(row)].append(row)
                else:raw.append(row)
    # Supersede financial unknowns must not overwrite known values silently.
    seen={}
    for row in raw:
        k=(row.get('symbol'),row.get('trade_id'))
        if k[1] is None:raise ValueError('missing trade identity; cannot certify collapsed population')
        money=tuple(row.get(f) for f in ('fill_ts','fill_px','fill_notional','side','rebalance_id','attempt_idx','order_type'))
        if k in seen and seen[k]!=money:raise ValueError('duplicate trade financial conflict')
        seen[k]=money
    fills=fr.collapse_supersedes(raw);daily={s:np.zeros((24,4,3)) for s in ('decision','mark60')}
    population=np.zeros((24,4,2));missing=collections.Counter();unmeasured=collections.defaultdict(float)
    total_n=0;total_not=0.;joined_n=0;joined_not=0.
    for f in fills:
        rid=str(f.get('rebalance_id') or '')
        if not rid.startswith('A'):continue
        dec=finite(rid[1:]);ts=finite(f.get('fill_ts'));notional=finite(f.get('fill_notional'));px=finite(f.get('fill_px'))
        if any(v is None for v in (dec,ts,notional,px)) or notional<=0 or px<=0:raise ValueError('unmeasurable trade')
        day=int((dec-first.timestamp())//86400)
        if not 0<=day<24:continue
        total_n+=1;total_not+=notional
        anchor=int(dec)//14400*14400;g=groups.get(anchor,{}).get(f.get('symbol'))
        if g is None:missing['outside_qvm_population']+=1;unmeasured['outside_qvm_population']+=notional;continue
        joined_n+=1;joined_not+=notional;population[day,g]+=[notional,1]
        rs=orders.get(key(f),[]);ref,err=reference(rs)
        submits=[finite(r.get('submit_ts')) for r in rs]
        known=[x for x in submits if x is not None]
        if ts<dec or (known and min(known)>ts):err='fill_before_decision_or_submit'
        if err:missing[err]+=1;unmeasured[err]+=notional
        else:daily['decision'][day,g]+=[measure(px,ref,f['side'])*notional,notional,1]
        mark=finite(f.get('mid_at_fill_plus_60s'));mts=finite(f.get('mark_ts_actual'))
        # 60s mark tolerates up to 60s lateness, never an earlier endpoint.
        if mark is not None and mark>0 and mts is not None and 60<=mts-ts<=120:
            daily['mark60'][day,g]+=[measure(px,mark,f['side'])*notional,notional,1]
        else:missing['mark_unavailable_or_not_60_to_120s']+=1;unmeasured['mark_unavailable_or_not_60_to_120s']+=notional
    result={'utc':datetime.now(timezone.utc).isoformat(),'sources':src,'pooled_only':True,
        'raw_fill_rows':len(raw),'unique_fills_all_rids':len(fills),'scheduled_fills':total_n,
        'scheduled_notional_usdt':total_not,'qvm_joined_fills':joined_n,'qvm_joined_notional_usdt':joined_not,
        'missing_counts':dict(missing),'missing_notional':dict(unmeasured),'segments':{}}
    for label,sl in [('calibration_0826_0910',slice(0,16)),('history_diagnostic_0911_0918',slice(16,24)),('all',slice(0,24))]:
        pop=population[sl].sum(0);tab={}
        for metric,a in daily.items():
            s=a[sl].sum(0);q=[]
            for i in range(4):
                q.append({'quartile':i,'population_fills':int(pop[i,1]),'population_notional_usdt':float(pop[i,0]),
                    'population_days':int((population[sl,i,0]>0).sum()),
                    'measured_fills':int(s[i,2]),'measured_notional_usdt':float(s[i,1]),
                    'notional_coverage':float(s[i,1]/pop[i,0]) if pop[i,0] else None,
                    'cost_bps':float(s[i,0]/s[i,1]*1e4) if s[i,1] else None})
            tab[metric]={'quartiles':q,'low_minus_high_bps':q[0]['cost_bps']-q[3]['cost_bps'] if s[0,1] and s[3,1] else None,
                         'bootstrap':[bootstrap(a[sl],b) for b in (1,3)]}
        result['segments'][label]=tab
    result['limits']=['Filled population only; no unfilled-request identification or causal market-impact claim.',
        'qvm groups are seven-day mean log quote volume, not Amihud bins.',
        'Historical diagnostics, not fresh holdout or strategy performance.',
        'Mark60 endpoint frozen to [fill+60,fill+120] seconds; missing separately recorded.',
        'Executor decision mid has no independent quote timestamp; freshness not certified.',
        'No fees/BNB conversion in this diagnostic; no strategy approval.']
    out.mkdir(exist_ok=False)
    (out/'COST_PROBE.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    np.savez_compressed(out/'DAILY_POOLED.npz',population=population,**daily)
    print(json.dumps({k:result[k] for k in ('scheduled_fills','qvm_joined_fills','missing_counts','segments')}))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('live','liquidity','reader','out'):p.add_argument('--'+k,required=True,type=Path)
    a=p.parse_args();run(a.live,a.liquidity,a.reader,a.out)

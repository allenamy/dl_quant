"""Independent arithmetic/population checks of completed recent cash outputs.

Reads raw engine arrays directly, never imports the reporting implementation.
Attribution buckets use start-of-window position sign, not an alpha-leg label.
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
from pathlib import Path
import hashlib, json, sys, time
import numpy as np

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def read(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def main(root,out):
    root=Path(root);term=json.loads((root/'TERMINAL.json').read_text())
    assert term['rc']==0 and term['result_sha256']==sha(root/'RESULT.json')
    result=json.loads((root/'RESULT.json').read_text())
    for n,h in result['outputs'].items():assert sha(root/n)==h
    econ=json.loads((root/'ECONOMIC.json').read_text());daily=read(root/'DAILY_PATHS.npz')
    checks=0;largest=0.;pins={};grouped={}
    def eq(x,y,label,atol=1e-8):
        nonlocal checks,largest
        x,y=np.asarray(x,dtype=float),np.asarray(y,dtype=float)
        assert x.shape==y.shape and np.isfinite(x).all() and np.isfinite(y).all(),label
        err=float(np.max(np.abs(x-y)));largest=max(largest,err)
        assert np.allclose(x,y,rtol=0,atol=atol),(label,err)
        checks+=1
    def timestamp(s):return int(np.datetime64(s.removesuffix('Z'),'s').astype('int64'))
    for sd in (42,2027):
        paths=sorted(p for p in econ['inputs'] if p.endswith('.npz') and f'/s{sd}/' in p)
        assert len(paths)==32
        for number,p in enumerate(paths):
            assert p.endswith(f'_seed_{number:02d}.npz')
            assert sha(p)==econ['inputs'][p];pins[p]=sha(p);z=read(p)
            A=z['A'];assert np.all(np.diff(A)==14400) and np.all(A%14400==0)
            r=z['navm1']/z['navm0']-1
            eq(r,(z['price_trade']+z['funding']-z['fee']-z['unk_excluded']*(z['unk_price']+z['unk_funding']))/z['nav0'],'main accounting',1e-10)
            for name,row in econ['results'][str(sd)].items():
                lo,hi=map(timestamp,(row['start'],row['end_exclusive']));ix=np.flatnonzero((A>=lo)&(A<hi))
                eq(A[ix],np.arange(lo,hi,14400),'complete anchors',0)
                days=np.arange(lo,hi,86400);rr=r[ix].reshape(-1,6);d=np.expm1(np.log1p(rr).sum(axis=1))
                j0=(lo-int(z['nav5_t0']))//300;j1=(hi-int(z['nav5_t0']))//300;n=z['nav5_main'][j0:j1+1]
                assert len(n)==len(ix)*48+1 and np.isfinite(n).all() and (n>0).all()
                vals={'n_days':len(days),'compound':np.expm1(np.log1p(d).sum()),'daily_mean_bps':d.mean()*1e4,
                      'sharpe_daily_descriptive':d.mean()/d.std(ddof=1)*np.sqrt(365),
                      'maxdd_5m':(n/np.maximum.accumulate(n)-1).min(),
                      'price_bps_per_day':np.sum(z['price_trade'][ix]/z['nav0'][ix])*1e4/len(days),
                      'funding_bps_per_day':np.sum(z['funding'][ix]/z['nav0'][ix])*1e4/len(days),
                      'fee_bps_per_day':np.sum(z['fee'][ix]/z['nav0'][ix])*1e4/len(days),
                      'turnover_nav_per_day':np.sum(z['turnover'][ix]/z['nav0'][ix])/len(days),
                      'unknown_held_sum':z['unk_held'][ix].sum(),'unknown_notional_sum':z['unk_notional'][ix].sum(),
                      'unknown_excluded_price_fund_sum':(z['unk_price'][ix]+z['unk_funding'][ix]).sum(),
                      'stopped_events':z['n_stop_events'][ix].sum(),'flatten_events':z['n_flatten_events'][ix].sum(),
                      'halt_anchors':(z['status'][ix]==1).sum(),'hold_anchors':(z['status'][ix]==2).sum(),
                      'cash_identity_max_usd':np.abs((z['nav1']-z['nav0'])-(z['price_trade']+z['funding']-z['fee']+z['transfer']))[ix].max()}
                for key,value in vals.items():eq(value,row['paths'][number][key],f'{sd}/{number}/{name}/{key}')
                eq(vals['compound'],n[-1]/n[0]-1,'window NAV endpoints')
                if name=='september27':
                    eq(days,daily['dates'],'daily axis',0);eq(d,daily[f's{sd}_p{number}'],'daily values')
            if number==0:
                q=read(root/f'PER_NAME_s{sd}_p0.npz');assert len(q['A'])==54 and len(set(q['symbols']))==len(q['symbols'])
                eq(q['A'],np.arange(timestamp('2026-09-19T00:00:00Z'),timestamp('2026-09-28T00:00:00Z'),14400),'attribution population',0)
                ix=np.searchsorted(A,q['A']);eq(q['nav0'],z['nav0'][ix],'attribution denominator')
                eq(q['price'],q['mv1']-q['mv0']-q['cash'],'per-name price',1e-6)
                eq(q['net'],q['price']+q['funding']-q['fee'],'per-name net',1e-6)
                for key,ref in [('price','price_trade'),('funding','funding'),('fee','fee')]:eq(q[key].sum(axis=1),z[ref][ix],key,1e-6)
                eq(q['q1'][:-1],q['q0'][1:],'continuous quantity',0)
                bp={key:q[key]/q['nav0'][:,None]*1e4 for key in ('price','funding','fee','net')}
                masks={'start_long':q['mv0']>0,'start_short':q['mv0']<0,'start_flat':q['mv0']==0}
                groups={g:{k:float(np.where(m,v,0).sum()/9) for k,v in bp.items()} for g,m in masks.items()}
                for k,v in bp.items():eq(sum(g[k] for g in groups.values()),v.sum()/9,'group identity')
                per=bp['net'].sum(axis=0);order=np.argsort(per)
                byday={str(np.datetime64(int(day),'s')):{k:float(v[q['A']//86400==day//86400].sum()) for k,v in bp.items()} for day in np.unique(q['A']//86400*86400)}
                def item(j):return {'symbol':str(q['symbols'][j]),**{k:float(v[:,j].sum()) for k,v in bp.items()},'start_short_anchors':int(masks['start_short'][:,j].sum()),'start_long_anchors':int(masks['start_long'][:,j].sum())}
                grouped[str(sd)]={'denominator':'each anchor opening simulated NAV; arithmetic contributions, not compounded return','groups_bps_per_day':groups,'daily_bps':byday,'worst10_bps_sum':[item(j) for j in order[:10]],'best10_bps_sum':[item(j) for j in order[-10:][::-1]],'nonzero_unknown_name_anchors':int(np.sum(q['unknown']&(np.abs(q['mv0'])>0))),'whole_path_attribution_trace_sha256':sha(root/f'TRACE_s{sd}.json')}
        # Aggregation is independently checked against its path population.
        for name,row in econ['results'][str(sd)].items():
            for key,agg in row['metrics'].items():
                a=np.array([r[key] for r in row['paths']])
                for op,value in [('mean',a.mean()),('min',a.min()),('max',a.max())]:eq(value,agg[op],name+'/'+key+'/'+op)
    rec={'status':'PASS','utc':time.strftime('%FT%TZ',time.gmtime()),'source_sha256':sha(__file__),'readout_result_sha256':sha(root/'RESULT.json'),'economic_sha256':sha(root/'ECONOMIC.json'),'paths':pins,'checks':checks,'max_abs_difference':largest,'attribution':grouped,'limitations':['No new simulator or venue validation: arithmetic/population check of fixed NC outputs','Two observational execution-seed-zero traces, not a 64-path attribution distribution','Start sign is not funding/King/F10 signal ownership','Recent windows already observed: exploratory diagnosis, not validation of a new rule']}
    Path(out).write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in rec.items() if k not in ('paths','attribution')},indent=2))

if __name__=='__main__':main(*sys.argv[1:])

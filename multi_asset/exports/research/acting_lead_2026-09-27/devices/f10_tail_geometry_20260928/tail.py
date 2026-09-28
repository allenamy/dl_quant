"""Outcome-tail accounting of IC/PnL divergence. Future bins are not trading features."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
from pathlib import Path
from datetime import datetime,timezone
import sys,json,time,hashlib,resource,signal,traceback
import numpy as np
from scipy.stats import rankdata

def contributions(old,new,y):
    old,new,y=map(lambda x:np.asarray(x,float),(old,new,y))
    if old.ndim!=1 or old.shape!=new.shape or old.shape!=y.shape or len(y)<4 or not np.isfinite(np.stack([old,new,y])).all():raise ValueError('population/finite')
    ranks=[rankdata(x) for x in (old,new,y)];center=[x-x.mean() for x in ranks]
    if any(x@x<=0 for x in center):raise ValueError('undefined correlation')
    unit=[]
    for r in ranks[:2]:
        z=r/max(len(y)-1,1)-.5;z-=z.mean();unit.append(z/np.abs(z).sum())
    dp=(unit[1]-unit[0])*y*1e4
    norms=[x/np.sqrt(x@x) for x in center];di=(norms[1]-norms[0])*norms[2]
    order=np.argsort(y,kind='stable');k=int(np.ceil(.05*len(y)));bins=(order[:k],order[k:-k],order[-k:])
    return np.array([dp[b].sum() for b in bins]),np.array([di[b].sum() for b in bins]),[len(b) for b in bins]

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def run():
    start=time.monotonic();h=Path(__file__).resolve().parent;c=json.loads((h/'CONTRACT.json').read_text());root=Path(c['output_root'])
    root.mkdir(exist_ok=False);resource.setrlimit(resource.RLIMIT_AS,(3*2**30,3*2**30));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    signal.signal(signal.SIGALRM,lambda *a:(_ for _ in ()).throw(TimeoutError('frozen 180s budget')));signal.alarm(c['runtime_limit_seconds'])
    parent=Path('/dev/shm/f10_stage_diagnostic_20260928_attempt2/results');rp=parent/'RESULT.json';d=json.loads(rp.read_text())
    if sha(rp)!=c['parent_result_sha256']:raise ValueError('parent identity')
    ap=parent/'STAGE_ARRAYS.npz'
    if sha(ap)!=d['arrays_sha256']:raise ValueError('stage arrays')
    pins={str(rp):sha(rp),str(ap):sha(ap)}
    for p,v in d['inputs'].items():
        if sha(p)!=v:raise ValueError('parent input drift '+p)
        pins[p]=v
    F=np.load('/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz');off=F['off'];members=F['m'];axis=F['anchors'];sy=F['symbols']
    T=np.load('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz',allow_pickle=True)
    s=np.load(ap);all_a=s['anchors'];recent=all_a>=int(datetime(2026,7,1,tzinfo=timezone.utc).timestamp());a=all_a[recent];ii=np.searchsorted(axis,a);ti=np.searchsorted(T['E_ts'],a)
    if not np.array_equal(axis[ii],a) or not np.array_equal(T['E_ts'][ti],a) or not np.array_equal(sy,T['symbols']):raise ValueError('axes')
    target=T['y4s'][ti].astype(float);result={};arrays={'anchors':a};maxerr=0
    for seed in (42,2027):
        pred={}
        for kind in ('NC','U','R180'):
            match=[p for p in d['inputs'] if p.endswith(f'work/f10_s{seed}/F10_OOF.npz') and ((kind=='NC' and f'ref_nc_s{seed}X' in p) or (kind!='NC' and f'cells/{kind}_s{seed}/' in p))]
            if len(match)!=1:raise ValueError('prediction source')
            z=np.load(match[0]);
            if not np.array_equal(z['E_ts'],axis) or not np.array_equal(z['symbols'],sy):raise ValueError('prediction axes')
            pred[kind]=z['P'][ii]
        n=f'NC_s{seed}'
        for kind in ('U','R180'):
            k=f'{kind}_s{seed}';use=s[n+'_trade'][recent]&s[k+'_trade'][recent]&~np.any(s[n+'_unknown_exposure'][recent]|s[k+'_unknown_exposure'][recent],axis=1)
            v=np.full((2,3,len(a)),np.nan);counts=[]
            for t,i in enumerate(ii):
                if not use[t]:continue
                m=members[off[i]:off[i+1]];p,ic,nb=contributions(pred['NC'][t,m],pred[kind][t,m],target[t,m]);v[:,:,t]=[p,ic];counts.append(nb)
                expected=s[k+'_natural'][0,recent][t]-s[n+'_natural'][0,recent][t];err=abs(float(p.sum()-expected));maxerr=max(maxerr,err)
                if err>1e-11:raise ValueError('parent rank price identity')
            arrays[k+'_contributions']=v;arrays[k+'_used']=use
            out={}
            for w,period in [('recent_primary',np.ones(len(a),bool)),('september',a>=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp()))]:
                take=use&period;vv=v[:,:,take]
                if not take.any() or not np.isfinite(vv).all():raise ValueError('unmeasured period')
                out[w]={'anchors':int(take.sum()),'price_bps_per_anchor_by_bin':vv[0].mean(1).tolist(),'global_rank_ic_delta_contribution_by_bin':vv[1].mean(1).tolist(),'price_total':float(vv[0].sum(0).mean()),'global_rank_ic_delta':float(vv[1].sum(0).mean())}
            result[f'{kind}_minus_NC_s{seed}']=out
    np.savez_compressed(root/'TAIL_ARRAYS.npz',**arrays)
    for p,v in pins.items():
        if sha(p)!=v:raise ValueError('input changed during diagnostic')
    rec={'status':'OUTCOME_TAIL_DESCRIPTIVE_NOT_CAUSAL_POLICY','utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(__file__),'contract_sha256':sha(h/'CONTRACT.json'),'inputs':pins,'results':result,'bins':['bottom_5pct_outcome','middle_90pct','top_5pct_outcome'],'parent_price_max_abs_error':maxerr,'arrays_sha256':sha(root/'TAIL_ARRAYS.npz'),'limits':c['limits'],'seconds':time.monotonic()-start}
    (root/'RESULT.json').write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n');print({k:rec[k] for k in ('status','results','parent_price_max_abs_error','seconds')},flush=True)
    (root/'TERMINAL.json').write_text(json.dumps({'rc':0,'utc':rec['utc'],'result_sha256':sha(root/'RESULT.json')},indent=2)+'\n')

if __name__=='__main__':
    try:run()
    except BaseException as e:
        c=json.loads(Path(__file__).with_name('CONTRACT.json').read_text());r=Path(c['output_root'])
        if r.exists():(r/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e)},indent=2)+'\n')
        raise

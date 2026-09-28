"""Descriptive additive split, not a trading policy or new profitability test."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
from pathlib import Path
from datetime import datetime, timezone
import json, time, hashlib, resource, signal
import numpy as np
from scipy.stats import rankdata

PARTS = ['add_long', 'remove_long', 'add_short', 'remove_short']

def split_weights(old, new, y):
    a,b,y=[np.asarray(x,dtype=float) for x in (old,new,y)]
    if a.ndim!=1 or not a.size or a.shape!=b.shape or a.shape!=y.shape or not np.isfinite(np.stack([a,b,y])).all():
        raise ValueError('population/finite')
    dl=np.maximum(b,0)-np.maximum(a,0)
    ds=np.maximum(-b,0)-np.maximum(-a,0)
    return np.array([np.maximum(dl,0),np.minimum(dl,0),-np.maximum(ds,0),-np.minimum(ds,0)])*y*1e4

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for x in iter(lambda:f.read(4<<20),b''):h.update(x)
    return h.hexdigest()

def unit(p):
    r=rankdata(p);z=r/max(len(r)-1,1)-.5;z-=z.mean()
    if not np.isfinite(p).all() or np.abs(z).sum()==0:raise ValueError('undefined rank book')
    return z/np.abs(z).sum()

def run():
    start=time.monotonic();src=Path(__file__).parent;c=json.loads((src/'CONTRACT.json').read_text());root=Path(c['output_root']);root.mkdir(exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(3*2**30,3*2**30));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    signal.signal(signal.SIGALRM,lambda *a:(_ for _ in ()).throw(TimeoutError('120s diagnostic budget')));signal.alarm(120)
    tp=Path(c['tail_result']);
    if sha(tp)!=c['tail_sha256']:raise ValueError('tail parent changed')
    old_result=json.loads(tp.read_text());pins={str(tp):sha(tp),**old_result['inputs']}
    ta=tp.with_name('TAIL_ARRAYS.npz');pins[str(ta)]=old_result['arrays_sha256']
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input drift '+p)
    fpath=next(p for p in pins if p.endswith('work/NEWS_FEATURES.npz'));F=np.load(fpath);off=F['off'];members=F['m'];axis=F['anchors'];symbols=F['symbols']
    target_path=next(p for p in pins if p.endswith('/dlw_targets.npz'));T=np.load(target_path,allow_pickle=True);ts=T['E_ts'];sy=T['symbols'];raw_y=T['y4s']
    prev=np.load(ta);anchors=prev['anchors'];fi=np.searchsorted(axis,anchors);ti=np.searchsorted(ts,anchors)
    if not np.array_equal(axis[fi],anchors) or not np.array_equal(ts[ti],anchors) or not np.array_equal(symbols,sy):raise ValueError('axis identity')
    result={};arrays={'anchors':anchors};raw_checks=[];maximum=0.
    sep=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp())
    for seed in (42,2027):
        predictions={}
        for arm in ('NC','U','R180'):
            paths=[p for p in pins if p.endswith(f'work/f10_s{seed}/F10_OOF.npz') and ((arm=='NC' and f'ref_nc_s{seed}X' in p) or (arm!='NC' and f'cells/{arm}_s{seed}/' in p))]
            if len(paths)!=1:raise ValueError('prediction identity')
            P=np.load(paths[0])
            if not np.array_equal(P['E_ts'],axis) or not np.array_equal(P['symbols'],symbols):raise ValueError('prediction axes')
            predictions[arm]=P['P'][fi]
        for arm in ('U','R180'):
            k=f'{arm}_s{seed}';use=prev[k+'_used'];v=np.full((len(anchors),3,4),np.nan);pos=np.zeros((len(anchors),2),int)
            for j,i in enumerate(fi):
                if not use[j]:continue
                m=members[off[i]:off[i+1]];y=raw_y[ti[j],m].astype(float);a=unit(predictions['NC'][j,m]);b=unit(predictions[arm][j,m]);z=split_weights(a,b,y)
                order=np.argsort(y,kind='stable');n=int(np.ceil(.05*len(m)));bins=[order[:n],order[n:-n],order[-n:]]
                v[j]=np.array([z[:,idx].sum(1) for idx in bins]);expected=prev[k+'_contributions'][0,:,j]
                err=float(np.max(np.abs(v[j].sum(1)-expected)));maximum=max(maximum,err)
                if err>1e-11:raise ValueError('parent price split identity')
                pos[j]=[int((y[bins[2]]>0).sum()),len(bins[2])]
                if j%30==0:raw_checks.append({'pair':k,'anchor':int(anchors[j]),'old':a.tolist(),'new':b.tolist(),'y':y.tolist(),'bins':[idx.tolist() for idx in bins],'parts_bps':v[j].tolist()})
            arrays[k+'_parts']=v;arrays[k+'_used']=use;out={}
            for win,take in [('recent_primary',use),('september',use&(anchors>=sep))]:
                avg=v[take].mean(0);parent=old_result['results'][f'{arm}_minus_NC_s{seed}'][win]
                if int(take.sum())!=parent['anchors'] or not np.allclose(avg.sum(1),parent['price_bps_per_anchor_by_bin'],rtol=0,atol=1e-11):raise ValueError('aggregate population identity')
                out[win]={'anchors':int(take.sum()),'parts_bps_per_anchor':avg.tolist(),'top_bin_positive_price_cells':int(pos[take,0].sum()),'top_bin_all_cells':int(pos[take,1].sum())}
            result[k]=out
    np.savez_compressed(root/'SPLIT_ARRAYS.npz',**arrays)
    (root/'RAW_CHECKS.json').write_text(json.dumps(raw_checks,allow_nan=False)+'\n')
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input drift after '+p)
    rec={'status':'DESCRIPTIVE_SPLIT_ONLY','utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(__file__),'contract_sha256':sha(src/'CONTRACT.json'),'inputs':pins,'parts':PARTS,'results':result,'parent_max_error':maximum,'raw_checks':len(raw_checks),'arrays_sha256':sha(root/'SPLIT_ARRAYS.npz'),'raw_sha256':sha(root/'RAW_CHECKS.json'),'seconds':time.monotonic()-start,'python':__import__('sys').executable,'numpy':np.__version__,'limits':c['limits']}
    (root/'RESULT.json').write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n');(root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n');print(json.dumps({k:rec[k] for k in ('status','results','parent_max_error','raw_checks','seconds')}))

if __name__=='__main__':
    try:run()
    except BaseException as e:
        c=json.loads(Path(__file__).with_name('CONTRACT.json').read_text());r=Path(c['output_root'])
        if r.exists():(r/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e)})+'\n')
        raise

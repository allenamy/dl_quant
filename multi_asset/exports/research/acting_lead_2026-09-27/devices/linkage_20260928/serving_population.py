"""One-day serving-population diagnostic. No labels, scores, fitting or live writes."""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
from pathlib import Path
import hashlib, json, sys, time, traceback, resource
import numpy as np
from peer_features import fit_graph, transform, loo_market

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def support(ts, day):
    t=np.asarray(ts)
    if t.ndim!=1 or t.dtype.kind not in 'iu' or len(t)<49 or np.any(t%300) or np.any(np.diff(t)!=300):
        raise ValueError('exact 5m axis required')
    if isinstance(day,bool) or not isinstance(day,(int,np.integer)) or day%86400:
        raise ValueError('UTC day required')
    endpoints=t[(np.arange(len(t))>=48)&(t%14400==0)&(t<day)]
    return {'closed_before_day':len(endpoints),'first':int(endpoints[0]) if len(endpoints) else None,
            'last':int(endpoints[-1]) if len(endpoints) else None,
            'scope':'upper bound assuming every observed 5m row finite for each name'}

def compare(left,right,scope):
    a,b,s=np.asarray(left),np.asarray(right),np.asarray(scope)
    if a.shape!=b.shape or a.shape!=s.shape or s.dtype.kind!='b' or a.dtype.kind not in 'ifu' or b.dtype.kind not in 'ifu':
        raise ValueError('comparison axes/types')
    if np.isinf(a[s]).any() or np.isinf(b[s]).any():raise ValueError('infinite comparison')
    x,y=np.isfinite(a)&s,np.isfinite(b)&s;both=x&y;d=np.abs(a[both]-b[both])
    return {'population':int(s.sum()),'common':int(both.sum()),'left_only':int((x&~y).sum()),
            'right_only':int((y&~x).sum()),'neither':int((s&~x&~y).sum()),
            'changed':int(np.count_nonzero(d)),
            'abs_delta_p50':float(np.median(d)) if len(d) else None,
            'abs_delta_p95':float(np.quantile(d,.95)) if len(d) else None,
            'abs_delta_max':float(d.max()) if len(d) else None}

def own(G,r4,r24,active):
    m4=loo_market(r4,np.isfinite(r4)&active,G['min_market'])
    m24=loo_market(r24,np.isfinite(r24)&active,G['min_market'])
    return np.column_stack(((r4-G['beta']*m4)/G['scale'],
                            (r24-G['beta']*m24)/(G['scale']*np.sqrt(6))))

def main(root,contract_path):
    started=time.monotonic();root=Path(root);root.mkdir(exist_ok=False)
    C=json.loads(Path(contract_path).read_text());pins=C['inputs']
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input sha '+p)
    if sha(__file__)!=C['source_sha256']:raise ValueError('source sha')
    if sha(Path(__file__).with_name('peer_features.py'))!=C['peer_source_sha256']:raise ValueError('peer source sha')
    snap=json.loads(Path(C['snapshot']).read_text());A=int(C['day']);cache=support(np.array(snap['ts']),A)
    if int(snap['anchor'])//86400*86400!=A:raise ValueError('snapshot day')
    z=np.load(C['panel']);t=z['anchors'];sy=z['symbols'];r=z['r4'];legal=z['legal'];r24=z['r24']
    ix=np.flatnonzero(t==A)
    if len(ix)!=1:raise ValueError('exact diagnostic anchor')
    i=int(ix[0]);fetch=list(snap['fetch_names'])
    if len(set(fetch))!=len(fetch):raise ValueError('duplicate fetch name')
    fm=np.isin(sy,fetch);lf=legal&fm[None,:];scope=legal[i]&fm
    # This is a present-day sensitivity, not a reconstruction of historical fetch lists.
    g=fit_graph(t,r,legal,sy,A,**C['graph']);f=fit_graph(t,r,lf,sy,A,**C['graph'])
    nan=np.full(len(sy),np.nan)
    def tx(G,l):
        return transform(G,A,r4=r[i],r24=r24[i],flow_delta=nan,qv_anomaly=nan,
                         fund8=nan,ema8=nan,active=l)['X'][:,:4]
    x,xf=tx(g,legal[i]),tx(f,lf[i]);o,of=own(g,r[i],r24[i],legal[i]),own(f,r[i],r24[i],lf[i])
    controls={}
    for key,now,saved in [('beta',g['beta'].astype(np.float32),z['beta'][i]),
                          ('scale',g['scale'].astype(np.float32),z['scale'][i]),
                          ('X',x.astype(np.float32),z['X'][i])]:
        controls['saved_'+key+'_exact']=bool(np.array_equal(now,saved,equal_nan=True))
        if not controls['saved_'+key+'_exact']:raise ValueError('saved panel not reproduced '+key)
    use=(t>=cache['first'])&(t<=cache['last'])
    try:fit_graph(t[use],r[use],lf[use],sy,A,**C['graph'])
    except ValueError as e:
        if str(e)!='history coverage':raise
        controls['actual_cache_history_refused']=True
    else:raise AssertionError('under-covered graph unexpectedly accepted')
    if use.sum()!=cache['closed_before_day']:raise ValueError('cache/panel endpoint mismatch')
    # Poison observations at and after day: the graph must ignore all of them.
    rp=r.copy();lp=lf.copy();rp[t>=A]=999.;lp[t>=A]=False
    fp=fit_graph(t,rp,lp,sy,A,**C['graph'])
    controls['future_poison_graph_exact']=all(np.array_equal(f[k],fp[k],equal_nan=True) for k in ('beta','scale','peers','counts'))
    if not controls['future_poison_graph_exact']:raise ValueError('future graph leak')
    intersection=[]
    for j in np.flatnonzero(scope&g['eligible']&f['eligible']):
        p=set(g['peers'][j]);q=set(f['peers'][j]);p.discard(-1);q.discard(-1)
        if len(p) and len(q):intersection.append(len(p&q)/len(p|q))
    differences={k:compare(a,b,scope) for k,a,b in [('beta',g['beta'],f['beta']),('scale',g['scale'],f['scale'])]}
    for j,k in enumerate(('own_residual4h','own_residual24h')):differences[k]=compare(o[:,j],of[:,j],scope)
    for j,k in enumerate(('peer_residual4h','peer_residual24h','own_minus_peer24h','peer_up_breadth')):differences[k]=compare(x[:,j],xf[:,j],scope)
    arr=root/'COMPARISON.npz'
    np.savez_compressed(arr,symbols=sy,scope=scope,full_active=legal[i],fetch_active=lf[i],
                        beta_full=g['beta'],beta_fetch=f['beta'],scale_full=g['scale'],scale_fetch=f['scale'],
                        peers_full=g['peers'],peers_fetch=f['peers'],own_full=o,own_fetch=of,X_full=x,X_fetch=xf)
    for p,h in pins.items():
        if sha(p)!=h:raise ValueError('input drift '+p)
    result={'status':'DIAGNOSTIC_COMPLETE_NOT_STRATEGY_EVIDENCE','utc':time.strftime('%FT%TZ',time.gmtime()),
            'source_sha256':sha(__file__),'contract_sha256':sha(contract_path),'inputs':pins,
            'day':A,'snapshot_anchor':snap['anchor'],'cache_support':cache,'required_min_obs':C['graph']['min_obs'],
            'fetch_count':len(fetch),'fetch_outside_research_axis':sorted(set(fetch)-set(map(str,sy))),
            'active_full':int(legal[i].sum()),'active_fetch':int(lf[i].sum()),
            'eligible_full':int(g['eligible'].sum()),'eligible_fetch':int(f['eligible'].sum()),
            'differences':differences,'peer_jaccard_median':float(np.median(intersection)) if intersection else None,
            'controls':controls,'seconds':time.monotonic()-started,
            'peak_rss_gib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,
            'outputs':{'COMPARISON.npz':sha(arr)},'python':sys.executable,'numpy':np.__version__,
            'limits':C['limits']}
    if result['seconds']>C['budget_seconds']:raise TimeoutError('diagnostic budget')
    (root/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (root/'TERMINAL.json').write_text(json.dumps({'rc':0,'result_sha256':sha(root/'RESULT.json')})+'\n')
    print(json.dumps({'status':result['status'],'seconds':result['seconds'],'cache':cache,'active':[result['active_full'],result['active_fetch']]}),flush=True)

if __name__=='__main__':
    try:main(*sys.argv[1:])
    except BaseException as e:
        root=Path(sys.argv[1]);root.mkdir(exist_ok=True)
        (root/'TERMINAL.json').write_text(json.dumps({'rc':1,'error':repr(e),'traceback':traceback.format_exc()},indent=2)+'\n')
        raise
